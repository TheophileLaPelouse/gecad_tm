
import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 

#%%
from prices import define_time, Pcons, Econs, Eautocons, TEauto, tep, Kp, period_hours

TP = [0.066889, 0.040255, 0.031037, 0.025345, 0.004733, 0.002652]
TE = [
      [0.176631, 0.170670, 0, 0, 0, 0.125919], 
      [0.126656, 0.131860, 0, 0, 0, 0.092685], 
      [0, 0.126656, 0.131860, 0, 0, 0.073864], # March is not in the invoices so the figures are based on february
      [0, 0, 0, 0.066662, 0.079025, 0.073864], 
      [0, 0, 0, 0.079119, 0.094265, 0.097955], 
      [0, 0, 0.124591, 0.143611, 0, 0.138129], 
      [0.150950, 0.179345, 0, 0, 0, 0.148744], 
      [0, 0, 0.165865, 0.181045, 0, 0.169511], 
      [0, 0, 0.145440, 0.167703, 0, 0.150691], 
      [0, 0, 0, 0.137424, 0.169721, 0.133218], 
      [0, 0.195679, 0.210640, 0, 0, 0.172424]
      ]

#%% Model construction

def calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = True) :
    # For it to be faster, we could rewrite this function in a C code and import it 
    # -> it should speed up the evaluation of the objective function
    # Here optimization is fast so not necessary
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    Spena_P = [0.00001 for k in range(6)]
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays
        if opti :  
            time_table = Time[p].value 
        else :
            time_table = Time[p]
        for t in time_table: 
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            Se += TE[m][p]*(Econs[t]-Eautocons[t])
            Se_p[p] += TE[m][p]*(Econs[t]-Eautocons[t])
            Seauto += TEauto[p]*Eautocons[t]
            Spena_P[p] += ((Pcons[t] - Pprev[p] + abs(Pcons[t] - Pprev[p]))/2)**2 
            
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
    return Se + Seauto + Spena + Sp


timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 30, 23, 59))
# timeframe =(dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 3, 23, 59))


Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
Nbdays += 1
timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))

model = pyo.ConcreteModel()

model.period = pyo.RangeSet(0, len(TP)-1)
model.month = pyo.RangeSet(0, 10)
model.time = pyo.RangeSet(timerange[0], timerange[1])

model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=max(Pcons))
# model.P_minus_P = pyo.Var(model.period, model.time, domain=pyo.NonNegativeReals, initialize = 0)

model.Pcons = pyo.Param(model.time, initialize={t: Pcons[t] for t in model.time})
model.Econs = pyo.Param(model.time, initialize={t: Econs[t] for t in model.time})
model.Eautocons = pyo.Param(model.time, initialize={t: Eautocons[t] for t in model.time})
model.TP = pyo.Param(model.period, initialize={p: TP[p] for p in model.period})
model.TE = pyo.Param(model.month, initialize={(m): TE[m] for m in model.month})
model.TEauto = pyo.Param(model.period, initialize={p: TEauto[p] for p in model.period})
model.Time = pyo.Param(model.period, initialize={p: Time[p] for p in model.period}, mutable=True)
model.tep = pyo.Param(initialize=tep)
model.Kp = pyo.Param(model.period, initialize={p : Kp[p] for p in model.period})

# model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.P_minus_P, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays))
model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays, Time_in_month))

def Pprev_rule(model, p) : 
    if p == model.period.last() :
        return model.Pprev[p] >= 0
    return model.Pprev[p] <= model.Pprev[p+1]
model.Pprev_con = pyo.Constraint(model.period, rule=Pprev_rule)

model.Pprev_con1 = pyo.Constraint(expr=model.Pprev[0] >= 0)


#%% Solver 

solver = SolverFactory('ipopt')
# solver.options['print_level'] = 
solver.options['print_timing_statistics'] = 'yes'
results = solver.solve(model, tee=True)
# model.display()


#%% Show results
"""
On veut récupérer le résultat d'optimisation donc les valeurs de Pprev, On veut le prix total et la comparaison avec le prix actuel, 
et on veut un récapitulatif mois par mois, avec total conso, total prod, prix, et comparaison avec le prix actuel 
"""

opti = [model.Pprev[p].value for p in model.period]
original = [120, 120, 120, 120, 120, 190]
price = model.obj()

original_price = calculate_price(original, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = False)
decrease = (original_price - price)/original_price

def last_day(any_day):
    next_month = any_day.replace(day=28) + dt.timedelta(days=4)
    if any_day.month == 11 :
        return dt.datetime(2024, 11, 20, 23, 59)
    return (next_month - dt.timedelta(days=next_month.day)).replace(hour=23, minute = 59)

months = range(1, 12) # We don't have data for december
Tframe = {}

Origin = []
Opti = []
Conso = []
Prod = []
Compare = []
results = pd.DataFrame(columns=['Month', 'Original', 'Optimized', 'Consumption', 'Production'])

for month in months :
    Tframe[month] = (dt.datetime(2024, month, 1, 0, 0), last_day(dt.datetime(2024, month, 1, 0, 0)))
    Time, Nbdays, Time_in_month = define_time(Tframe[month], period_hours)
    Nbdays += 1
    Opti.append(calculate_price(opti, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = False))
    Origin.append(calculate_price(original, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = False))
    Conso.append(sum([sum(Econs[t] for t in T) for T in Time]))
    Prod.append(sum([sum(Eautocons[t] for t in T) for T in Time]))
    Compare.append((Origin[-1] - Opti[-1])/Origin[-1])

results['Month'] = [cal.month_name[month] for month in months]
results['Original'] = Origin
results['Optimized'] = Opti
results['Consumption'] = Conso
results['Production'] = Prod
results['Compare'] = Compare
results.loc['Total'] = results.sum(numeric_only=True)
results.loc['Total', 'Month'] = 'Total'
results.loc['Total', 'Compare'] = (results.loc['Total', 'Original'] - results.loc['Total', 'Optimized'])/results.loc['Total', 'Original']

csv_path = 'Results/csv/opti_simple.csv'

if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results')) : 
    os.mkdir(os.path.join(os.path.dirname(__file__), 'Results'))
if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results/csv')) :
    os.mkdir(os.path.join(os.path.dirname(__file__), 'Results/csv'))
    
results = results.round(2)

results.to_csv(csv_path, sep=';', index=False)

#%% Verification 

Times = {}
All_nbdays = {}
for month in months : 
    Time, Nbdays, _ = define_time(Tframe[month], period_hours)
    Nbdays += 1
    Times[month] = Time
    All_nbdays[month] = Nbdays

timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))
# timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 3, 31, 23, 59))


Time, Nbdays, _ = define_time(timeframe, period_hours)
Nbdays += 1

# Verifying that Times and Time contains the same values 
Time_reconstructed = [[] for k in range(6)]
for month in months : 
    for p in range(6) : 
        Time_reconstructed[p] += Times[month][p]
        
print(Time == Time_reconstructed)
        
