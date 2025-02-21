
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

#%% Model construction
def calculate_price(model, deltat, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, selling, opti = True) :
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Spena_P = [0.00001 for k in range(6)]
    for p in range(len(TP)) :
        Sp += TP[p]*model.Pprev[p]*Nbdays
        if opti :  
            time_table = Time[p].value 
        else :
            time_table = Time[p]
        for t in time_table: 
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            Se += TE[m][p]*model.Egrid_plus[t]
            if selling :
                Se -= TE[m][p]*model.Egrid_minus[t]/2
            # Se += TE[m][p]*model.Egrid_minus[t]
            # Seauto += TEauto[p]*(Eautocons[t]-Pc[t]*deltat)
            # Pgrid = (Egrid_plus[t]+Egrid_minus[t])/deltat
            # Pgrid = Pcons[t] - Pd[t] - Eautocons[t]/deltat + Pc[t]
            # Spena_P[p] += ((Pgrid - Pprev[p] + abs(Pgrid - Pprev[p]))/2)**2 
            Spena_P[p] += (model.Pplus[t, p])**2
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
        
    return Se + Seauto + Spena + Sp

def battery_price(Cb, nbdays, bat_price=359/10+0.019) :
    # investment = 359 $/kwh/year, maintenance = 0.019$/kwh/year, lifetime = 9 years
    return Cb*bat_price*nbdays/365
    # return 0
    
def pena_charge_and_discharge(Pc, Pd, time=None, coef=0.1) : 
    if Pd is None :
        return coef*sum(p for p in Pc)
    else : 
        if time is None :
            return coef*sum(Pc[t]*Pd[t] for t in range(len(Pc)))
        else : 
            return coef*sum(Pc[t]*Pd[t] for t in time)

# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 4, 0, 59))
timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))

def build_model(timeframe, pena=0.1, definer=1, charge_rate=0.5, decharge_rate=0.5, Effc=0.95, Effd=0.95, Econs=Econs, Eautocons=Eautocons, TP=TP, TE=TE, TEauto=TEauto, tep=tep, Kp=Kp, period_hours=period_hours, without_bat = False, bat_price=359/10+0.019, selling=False) :
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
    
    model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=max(Pcons))
    
    # Battery
    model.Pc = pyo.Var(model.time, domain=pyo.NonNegativeReals, initialize=0)
    model.Pd = pyo.Var(model.time, domain=pyo.NonNegativeReals, initialize=0)
    # model.notPc_Pd = pyo.Var(model.time, domain=pyo.NonNegativeReals, initialize=0)
    model.E = pyo.Var(model.time, domain=pyo.NonNegativeReals)
    model.Cb = pyo.Var(domain = pyo.NonNegativeReals)
    
    # For it to be linear
    model.Egrid_plus = pyo.Var(model.time, domain=pyo.NonNegativeReals)
    model.Egrid_minus = pyo.Var(model.time, domain=pyo.NonNegativeReals)
    
    model.Pcons = pyo.Param(model.time, initialize={t: Pcons[t] for t in model.time})
    model.Econs = pyo.Param(model.time, initialize={t: Econs[t] for t in model.time})
    model.Eautocons = pyo.Param(model.time, initialize={t: Eautocons[t] for t in model.time})
    model.TP = pyo.Param(model.period, initialize={p: TP[p] for p in model.period})
    model.TE = pyo.Param(model.month, initialize={(m): TE[m] for m in model.month})
    model.TEauto = pyo.Param(model.period, initialize={p: TEauto[p] for p in model.period})
    model.Time = pyo.Param(model.period, initialize={p: Time[p] for p in model.period}, mutable=True)
    model.tep = pyo.Param(initialize=tep)
    model.Kp = pyo.Param(model.period, initialize={p : Kp[p] for p in model.period})
    model.deltat = pyo.Param(initialize=0.25)
    
    def Pprev_rule(model, p) : 
        if p == model.period.last() :
            return model.Pprev[p] >= 0
        return model.Pprev[p] <= model.Pprev[p+1]
    model.Pprev_con = pyo.Constraint(model.period, rule=Pprev_rule)
    
    model.Pprev_con1 = pyo.Constraint(expr=model.Pprev[0] >= 0)
    
    # Battery constraints
    def max_rule(model, t) : 
        return model.E[t] <= model.Cb
    def min_rule(model, t) : 
        return model.E[t] >= 0.2*model.Cb
    model.capacity_con_max = pyo.Constraint(model.time, rule=max_rule)
    model.capacity_con_min = pyo.Constraint(model.time, rule=min_rule)
    
    def max_pow_rule(model, t) : 
        return model.Pc[t] <= charge_rate*model.Cb
    def min_pow_rule(model, t) :
        return model.Pd[t] <= decharge_rate*model.Cb
    model.pow_con_max = pyo.Constraint(model.time, rule=max_pow_rule)
    model.pow_con_min = pyo.Constraint(model.time, rule=min_pow_rule)
    
    def battery_rule(model, t) : 
        if t == model.time.first() : 
            # return model.E[t] == (0.2*model.Cb + model.Cb)/2
            return model.E[t] == 0.2*model.Cb
            # return model.E[t] == 5
        return model.E[t] == model.E[t-1] + (Effc*model.Pc[t] - model.Pd[t]/Effd)*model.deltat
    model.battery_con = pyo.Constraint(model.time, rule=battery_rule)
    
    def Egrid_rule(model, t) : 
        return model.Egrid_plus[t] - model.Egrid_minus[t] == model.Econs[t] + (model.Pc[t]-model.Pd[t])*model.deltat - Eautocons[t]
    model.grid_con = pyo.Constraint(model.time, rule=Egrid_rule)

    model.Pminus = pyo.Var(model.time, model.period, domain=pyo.NonNegativeReals)
    model.Pplus = pyo.Var(model.time, model.period, domain=pyo.NonNegativeReals)
    
    def Pgrid_rule_naive(model, t, p) : 
        return model.Pplus[t, p] - model.Pminus[t, p] == (model.Econs[t]-Eautocons[t])/model.deltat  + (model.Pc[t]-model.Pd[t]) - model.Pprev[p]
    # = model.Egrid_plus[t]/model.deltat - model.Egrid_minus[t]/model.deltat - Pprev[p]
    model.grid_con_naive = pyo.Constraint(model.time, model.period, rule=Pgrid_rule_naive)
    
    # def charge_discharge_rule(model, t) : 
    #     return(model.notPc_Pd[t] == model.Pc*model.Pd[t])
    
    if without_bat : 
        model.no_bat = pyo.Constraint(expr=model.Cb==0)
    
    model.obj = pyo.Objective(expr=calculate_price(model, model.deltat, model.TP, model.TE, model.TEauto, 
                                                   model.Time, model.tep, model.Kp, Nbdays, Time_in_month, selling) 
                              + battery_price(model.Cb, Nbdays, bat_price=bat_price)
                              + pena_charge_and_discharge(model.Pc, model.Pd, time=model.time, coef=pena)
                              , sense=pyo.minimize
                              )
    return model


#%% Solver 

def solve(model, print_level = 7) :
    solver = SolverFactory('ipopt')
    solver.options['print_level'] = print_level
    solver.options['tol'] = 1e-4
    solver.options['acceptable_tol'] = 1e-4
    solver.options['max_iter'] = 3000
    solver.options['print_timing_statistics'] = 'yes'
    solver.options['hsllib'] = '/usr/local/lib/libcoinhsl.dylib'
    # solver.options['nlp_scaling_method'] = 'none'
    solver.options['linear_solver'] = 'ma97'
    results = solver.solve(model, tee=True)
    return solver, results
# model.display()

#%% Penalization variable test

Pena2test = [0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.05, 0.1, 0.2, 0.5, 1, 10, 100]
res = []
for coef in Pena2test : 
    model = build_model(timeframe, pena=coef)
    solver, results = solve(model)
    Pc = [model.Pc[t].value for t in model.time.data()]
    Pd = [model.Pd[t].value for t in model.time.data()]
    res.append((model.obj(), pena_charge_and_discharge(Pc, Pd, coef=1)))
    
# -> Choix de coefficients dans les calculs = 0.000001 car représente 1/100000 fois la valeur donc on peut dire que c'est négligeable

#%% Plot batterie usage 
timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 30, 23, 59))
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
# model = build_model(timeframe, without_bat=True)
model = build_model(timeframe, pena=0.000001)
# full_date_new_simple = []
# filled_days = set()
# for date in full_date_new : 
#     if date.date() not in filled_days :
#         c = 0
#         filled_days.add(date.date())
#     if c < 2 : 
#         full_date_new_simple.append(date)
#     c += 1
        

# model = build_model(full_date_new, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new) 
# model = build_model(full_date_new_simple, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new)  # N'a pas vraiment de sens mais c'est du test
# model = build_model(full_date_repr, definer=2, Econs=Econs_repr, Eautocons=Eprod_repr, pena=0.000001, selling=False)

#%% Simple test
solver, results = solve(model)
Pprev = [model.Pprev[k].value for k in range(6)]
Pc = [model.Pc[k].value for k in model.time]
Pd = [model.Pd[k].value for k in model.time]
Cb = model.Cb.value


#%% Bat_price influence 
obj = []
bat = []
pena_violation = []
price = []
for k in range(1) : 
    bat_price = (359/10+0.019-1)*(k+1)/10 + 1
    price.append(bat_price)
    model = build_model(full_date_repr, definer=2, Econs=Econs_repr, Eautocons=Eprod_repr, pena=0, bat_price=bat_price)
    solver, results = solve(model)
    obj.append(model.obj())
    bat.append(model.Cb.value)
    Pc = [model.Pc[t].value for t in model.time.data()]
    Pd = [model.Pd[t].value for t in model.time.data()]
    pena_violation.append(pena_charge_and_discharge(Pc, Pd, coef=1))
    
def save_values(path = 'Results/csv/bat_price.csv') :
    df = pd.DataFrame(columns=['Batterie size (kwh)', 'Objective function', 'Battery price'])
    df['Batterie size (kwh)'] = bat 
    df['Objective function'] = obj 
    df['Battery price'] = bat 
    df.to_csv(path, sep=';')
    
# save_values(path='Results/csv/bat_price_pena.csv')

#%%
solver, results = solve(model)
real_time = [full_date[k] for k in model.time]

result_E = [model.E[t].value for t in model.time]
Econs_timeframe = [model.Econs[t] for t in model.time]
Eprod_timeframe = [model.Eautocons[t] for t in model.time]

fig = plt.figure()
plt.plot(real_time, result_E, label='Battery Energy')
plt.plot(real_time, Econs_timeframe, label='Energy Consumption')
plt.plot(real_time, Eprod_timeframe, label='Energy Production')
plt.legend()
plt.plot()

result_Pc = [model.Pc[t].value for t in model.time]
result_Pd = [model.Pd[t].value for t in model.time]
result_Pc_Pd = [model.Pc[t].value - model.Pd[t].value for t in model.time]
Pcons_timeframe = [model.Pcons[t] for t in model.time]
Pprod_timeframe = [model.Eautocons[t]/0.25 for t in model.time]

fig2 = plt.figure()
# plt.plot(real_time, result_Pc, label='Charge Power')
# plt.plot(real_time, result_Pd, label='Decharge Power')
plt.plot(real_time, result_Pc_Pd, label='charge + decharge power')
plt.plot(real_time, Pcons_timeframe, label='Power Consumption')
plt.plot(real_time, Pprod_timeframe, label='Power Production')
plt.legend()
plt.plot()

#%% Test temps de calcul
# import time
# t0 = dt.datetime(2024, 4, 1, 0, 0)
# t1 = t0+dt.timedelta(hours=24)
# times = []
# n = 30
# for k in range(n) : 
#     tic = time.time()
#     t1 += dt.timedelta(hours = 12)
#     model = build_model((t0, t1))
#     solver, results = solve(model, 0)
#     times.append(time.time()-tic)
    
# #%%
# import numpy as np

# # On vérifie si on a une tendance polynomiale
# p = np.polyfit(range(n), times, 2)
# f = lambda x : p[0]*x**2 + p[1]*x + p[2]
# plt.plot(range(n), times)
# plt.plot(range(n), [f(k) for k in range(n)])

#%% Test representative days month per month

compare = []
for k in range(1, 12) :
    timerange = (dt.datetime(2024, k, 1, 0, 0), dt.datetime(2024, k, cal.monthrange(2024, k)[1], 23, 59))
    model1 = build_model(timerange, definer=1)
    solver, results = solve(model1)
    standard_obj = model1.obj()
    
    repr_days = []
    
    i = 0
    while full_date_new[i].month != k : 
        i+=1
    while full_date_new[i].month == k : 
        repr_days.append(full_date_new[i])
        i += 1 
        
    model2 = build_model(repr_days, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new) 
    solver2, results2 = solve(model2)
    repr_obj = model2.obj()
    compare.append((standard_obj, repr_obj))
    