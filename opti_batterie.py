
import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
import matplotlib.pyplot as plt

#%%
from prices import define_time, Econs, Eautocons, TEauto, tep, Kp, period_hours, full_date, define_time2
from representative_days import Econs_new, Eprod_new, full_date_new, days

Pcons_new = [val/0.25 for val in Econs_new]
Pprod_new = [val/0.25 for val in Eprod_new]

Pcons = [val/0.25 for val in Econs]
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

#%% Model construction
def calculate_price(model, deltat, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = True) :
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
            # Se += TE[m][p]*model.Egrid_minus[t]
            # Seauto += TEauto[p]*(Eautocons[t]-Pc[t]*deltat)
            # Pgrid = (Egrid_plus[t]+Egrid_minus[t])/deltat
            # Pgrid = Pcons[t] - Pd[t] - Eautocons[t]/deltat + Pc[t]
            # Spena_P[p] += ((Pgrid - Pprev[p] + abs(Pgrid - Pprev[p]))/2)**2 
            Spena_P[p] += (model.Pplus[t, p])**2
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
        
    return Se + Seauto + Spena + Sp

def battery_price(Cb, nbdays) :
    # investment = 359 $/kwh/year, maintenance = 0.019$/kwh/year, lifetime = 9 years
    return (Cb*359/9+Cb*0.019)*nbdays/365
    # return 0

timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
# timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 3, 31, 23, 59))

def build_model(timeframe, definer=1, charge_rate=0.5, decharge_rate=0.5, Effc=0.95, Effd=0.95, Econs=Econs, Eautocons=Eautocons, Pcons=Pcons, TP=TP, TE=TE, TEauto=TEauto, tep=tep, Kp=Kp, period_hours=period_hours) :

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
            return model.E[t] == (0.2*model.Cb + model.Cb)/2
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
    
    
    
    model.obj = pyo.Objective(expr=calculate_price(model, model.deltat, model.TP, model.TE, model.TEauto, 
                                                   model.Time, model.tep, model.Kp, Nbdays, Time_in_month) + battery_price(model.Cb, Nbdays), sense=pyo.minimize)
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

#%% Plot batterie usage 
# model = build_model(timeframe)
model = build_model(full_date_new, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new) 

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
    