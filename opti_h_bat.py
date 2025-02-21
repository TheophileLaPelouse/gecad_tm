
import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
import matplotlib.pyplot as plt
import pandas as pd

#%%
from prices import define_time, Econs, Eautocons, TEauto, tep, Kp, period_hours, full_date, define_time2, series2lists
from representative_days import create_data, gen_new_data
from heuristic_battery import create_profile

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

# For the moment, for the battery we will take values that looks ok, but with not so many reasearch behind.

# Emax = 30 # kwh
# Emin = 0.2*Emax*0
charge_rate = 0.5 
Effc = 0.95 # Efficiency, we count the conversion losses, do we need to lessen the losses if come from PV ? Maybe
Effd = 0.95 # order of magnitude, need to be looked into.

#%% representative days 

path_repr = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'best_repr.csv')
if not os.path.exists(path_repr) :
    raise ValueError('You must run opti.search_best_repr first')
    
df = pd.read_csv(path_repr, sep=';', parse_dates=['full_date'])

Econs_repr = series2lists(df['Econs'])
Eprod_repr = series2lists(df['Eprod'])
full_date_repr = [df['full_date'][k] for k in range(len(df['full_date']))]

#%% Values with battery

def create_Eprod(CB, Effc=0.95, Effd=0.95, charge_rate=0.5, decharge_rate=0.5, Eprod=Eautocons, Econs=Econs, full_date=full_date) : 
    SOC, Pd, Pc = create_profile(Econs, CB, Effc, Effd, charge_rate, decharge_rate, full_date)
    Eprod_new = Eprod[:]
    for k in range(len(Pd)) :
        Eprod_new[k] += Pd[k] - Pc[k]
        # print(Pc[k], Pd[k])
    return Eprod_new, SOC, Pd, Pc
        

#%% Model construction
def calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, selling, opti = True) :
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
            # Se += TE[m][p]*(Econs[t]-Eautocons[t])
            Se += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2
            if selling :
                Se -= TE[m][p]*((Econs[t]-Eautocons[t]) - abs(Econs[t]-Eautocons[t]))/2/2
            Se_p[p] += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2
            # Seauto += TEauto[p]*Eautocons[t]
            Spena_P[p] += ((Pcons[t] - Pprev[p] + abs(Pcons[t] - Pprev[p]))/2)**2 
            
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
    return Se + Seauto + Spena + Sp

def battery_price(Cb, nbdays, bat_price=359/10+0.019) :
    # investment = 359 $/kwh/year, maintenance = 0.019$/kwh/year, lifetime = 9 years
    return Cb*bat_price*nbdays/365


def build_model(timeframe, CB, definer=1, charge_rate=0.5, decharge_rate=0.5, Effc=0.95, Effd=0.95, Econs=Econs, Eprod=Eautocons, TP=TP, TE=TE, TEauto=TEauto, tep=tep, Kp=Kp, period_hours=period_hours, bat_price=359/10+0.019, selling=False) :
    Pcons = [val/0.25 for val in Econs]
    if definer == 1 :
        Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
        Nbdays += 1
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    elif definer == 2 :
        Time, Nbdays, Time_in_month = define_time2(timeframe, period_hours)
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    else : 
        raise ValueError("definer must be 1 or 2")
    
    model = pyo.ConcreteModel()
    
    model.period = pyo.RangeSet(0, len(TP)-1)
    model.month = pyo.RangeSet(0, 10)
    model.time = pyo.RangeSet(timerange[0], timerange[1])
    
    model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=[120, 130, 130, 130, 130, 190])
    # model.P_minus_P = pyo.Var(model.period, model.time, domain=pyo.NonNegativeReals, initialize = 0)
    
    model.Pcons = pyo.Param(model.time, initialize={t: Pcons[t] for t in model.time})
    model.Econs = pyo.Param(model.time, initialize={t: Econs[t] for t in model.time})
    model.Eautocons = pyo.Param(model.time, initialize={t: Eprod[t] for t in model.time})
    model.TP = pyo.Param(model.period, initialize={p: TP[p] for p in model.period})
    model.TE = pyo.Param(model.month, initialize={(m): TE[m] for m in model.month})
    model.TEauto = pyo.Param(model.period, initialize={p: TEauto[p] for p in model.period})
    model.Time = pyo.Param(model.period, initialize={p: Time[p] for p in model.period}, mutable=True)
    model.tep = pyo.Param(initialize=tep)
    model.Kp = pyo.Param(model.period, initialize={p : Kp[p] for p in model.period})
    model.CB = pyo.Param(initialize=CB)
    
    # model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.P_minus_P, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays))
    model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays, Time_in_month, selling)
                              + battery_price(model.CB, Nbdays, bat_price))
    
    def Pprev_rule(model, p) : 
        if p == model.period.last() :
            return model.Pprev[p] >= 0
        return model.Pprev[p] <= model.Pprev[p+1]
    model.Pprev_con = pyo.Constraint(model.period, rule=Pprev_rule)
    
    model.Pprev_con1 = pyo.Constraint(expr=model.Pprev[0] >= 0)
    
    return model, Time_in_month, Nbdays


#%%
timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))

Eprod2, SOC, Pd, Pc = create_Eprod(68)
model_norm, Time_in_month, Nbdays = build_model(timeframe, 0, bat_price=0, Eprod=Eautocons, selling=True)
solver = SolverFactory('ipopt')
solver.options['print_timing_statistics'] = 'yes'


model_bat, Time_in_month, Nbdays = build_model(timeframe, 30, bat_price=0, Eprod=Eprod2, selling=True)
#%%
results = solver.solve(model_norm, tee=True)
results = solver.solve(model_bat, tee=True)

print("model_bat", model_bat.obj(), "model_norm", model_norm.obj())

#%% battery size study with price = 0

Values = {}
solver = SolverFactory('ipopt')
for k in range(10) : 
    Eprod2, SOC, Pd, Pc = create_Eprod(k*10)
    model_bat, Time_in_month, Nbdays = build_model(timeframe, 10*k, bat_price=0, Eprod=Eprod2, selling=True)
    solver.solve(model_bat)
    Values[10*k] = model_bat.obj()
    
plt.plot([val for val in Values.keys()], [val for val in Values.values()])
plt.show()

#%% 
    