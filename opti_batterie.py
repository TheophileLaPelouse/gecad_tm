
import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
import matplotlib.pyplot as plt
import pandas as pd
import json
plt.rcParams['font.size'] = 12

#%%
from prices import define_time, Econs, Eautocons, TEauto, tep, Kp, period_hours, full_date, define_time2, series2lists, treat_data, increase_deltat
from representative_days import create_data, gen_new_data, separate_days
from opti import build_model as build_model_without_bat

from prices_tubacer import TE, TP 
from prices_porto_motor import TE_pm_2024, TP_pm_2024

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

path_repr_div = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'best_repr.csv')
if not os.path.exists(path_repr) :
    raise ValueError('You must run opti.search_best_repr first')
    
df = pd.read_csv(path_repr, sep=';', parse_dates=['full_date'])
Econs_repr_div = series2lists(df['Econs'])
Eprod_repr_div = series2lists(df['Eprod'])
full_date_repr_div = [df['full_date'][k] for k in range(len(df['full_date']))]


path_repr_pm = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'best_repr_TM_max.csv')
if not os.path.exists(path_repr_pm) :
    raise ValueError('You must run opti.search_best_repr first')
    
df = pd.read_csv(path_repr_pm, sep=';', parse_dates=['full_date'])
Econs_repr_pm = series2lists(df['Econs'])
Eprod_repr_pm = series2lists(df['Eprod'])
full_date_repr_pm = [df['full_date'][k] for k in range(len(df['full_date']))]


#%% Model construction
def calculate_price(model, deltat, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, selling, opti = True, printation=False) :
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Spena_P = [[0.000000000001 for k in range(6)] for m in range(12)] # Should be different than 0 because of differentiation of the square root 
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
            # if printation :
            #     print("Buying price", t, TE[m][p]*model.Egrid_plus[t]())
            if selling :
                Se -= TE[m][p]*model.Egrid_minus[t]/2
            # Se += TE[m][p]*model.Egrid_minus[t]
            # Seauto += TEauto[p]*(Eautocons[t]-Pc[t]*deltat)
            # Pgrid = (Egrid_plus[t]+Egrid_minus[t])/deltat
            # Pgrid = Pcons[t] - Pd[t] - Eautocons[t]/deltat + Pc[t]
            # Spena_P[p] += ((Pgrid - Pprev[p] + abs(Pgrid - Pprev[p]))/2)**2 
            Spena_P[m][p] += (model.Pplus[t, p])**2
        
        for m in range(12) : 
            Spena_P[m][p] = Spena_P[m][p]**(1/2)
        Spena += Kp[p]*tep*sum(Spena_P[m][p] for m in range(12))
        # if printation :
        #     if isinstance(Spena_P[p], float) : 
        #         print("Spena_P", Spena_P[p])
        #         print("Spena[p]", p, Kp[p]*tep*Spena_P[p])
        #     else : 
        #         print("Spena_P", Spena_P[p])
        #         print("Spena[p]", p, (Kp[p]*tep*Spena_P[p]()))
    if printation : 
        print("Se", Se())
        print("Seauto", Seauto)
        print("Spena", Spena())
        print("Sp", Sp())
        print("TE", [TE[val] for val in TE])
    return Se + Seauto + Spena + Sp

def battery_price(Cb, nbdays, bat_price=359, i=0.1, n=10, eps=0.002) :
    # i = discount rate
    # n lifetime
    # eps = service coefficient 
    # investment = 359 $/kwh/year, maintenance = 0.019$/kwh/year, lifetime = 9 years
    bat_price=bat_price*((i*(1+i)**n)/((1+i)**n-1))+bat_price*eps
    return Cb*bat_price*nbdays/365
    # return 0
    
def pena_charge_and_discharge(Pc, Pd, time=None, coef=0.1) : 
    if coef == 'tot' : 
        return 0
    if Pd is None :
        return coef*sum(p for p in Pc)
    else : 
        if time is None :
            return coef*sum(Pc[t]*Pd[t] for t in range(len(Pc)))
        else : 
            return coef*sum(Pc[t]*Pd[t] for t in time)

# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 4, 0, 59))
timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))

def build_model(timeframe, full_date=full_date, SOC0=0.2, pena=0.1, definer=1, charge_rate=0.5, decharge_rate=0.5, Effc=0.95, Effd=0.95, Econs=Econs, Eautocons=Eautocons, TP=TP, TE=TE, TEauto=TEauto, tep=tep, Kp=Kp, period_hours=period_hours, without_bat = False, bat_price=359, selling=False, Cb_param=None, Pprev=None) :
    Pcons = [val/0.25 for val in Econs]
    if definer == 1 :
        Time, Nbdays, Time_in_month = define_time(timeframe, period_hours, full_date)
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
    
    if Pprev is None :
        model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=max(Pcons))
    else :
        model.Pprev=pyo.Param(model.period, domain=pyo.NonNegativeReals, initialize={p:Pprev[p] for p in model.period})
    # Battery
    model.Pc = pyo.Var(model.time, domain=pyo.NonNegativeReals, initialize=0)
    model.Pd = pyo.Var(model.time, domain=pyo.NonNegativeReals, initialize=0)
    # model.notPc_Pd = pyo.Var(model.time, domain=pyo.NonNegativeReals, initialize=0)
    model.E = pyo.Var(model.time, domain=pyo.NonNegativeReals)
    if Cb_param is not None : 
        model.Cb = pyo.Param(domain=pyo.NonNegativeReals, initialize=Cb_param)
    else : 
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
    if not Pprev :
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
            return model.E[t] == SOC0*model.Cb
            # return model.E[t] == 5
        return model.E[t] == model.E[t-1] + (Effc*model.Pc[t] - model.Pd[t]/Effd)*model.deltat
    model.battery_con = pyo.Constraint(model.time, rule=battery_rule)
    
    model.batteruy_last_val = pyo.Constraint(expr=(model.E[model.time.at(-1)]>=0.45*model.Cb))
    
    def Egrid_rule(model, t) : 
        return model.Egrid_plus[t] - model.Egrid_minus[t] == model.Econs[t] + (model.Pc[t]-model.Pd[t])*model.deltat - Eautocons[t]
    model.grid_con = pyo.Constraint(model.time, rule=Egrid_rule)
    
    def Egrid_mult_rule(model, t) : 
        return model.Egrid_plus[t]*model.Egrid_minus[t] == 0
    # model.grid_mult_con = pyo.Constraint(model.time, rule=Egrid_mult_rule)
    
    model.Pminus = pyo.Var(model.time, model.period, domain=pyo.NonNegativeReals)
    model.Pplus = pyo.Var(model.time, model.period, domain=pyo.NonNegativeReals)
    
    def Pgrid_rule_naive(model, t, p) : 
        return model.Pplus[t, p] - model.Pminus[t, p] == (model.Econs[t]-Eautocons[t])/model.deltat  + (model.Pc[t]-model.Pd[t]) - model.Pprev[p]
    # = model.Egrid_plus[t]/model.deltat - model.Egrid_minus[t]/model.deltat - Pprev[p]
    model.grid_con_naive = pyo.Constraint(model.time, model.period, rule=Pgrid_rule_naive)
    
    def Pgrid_mult_rule(model, t, p) :
        return model.Pplus[t, p]*model.Pminus[t, p]==0
    # model.Pgrid_con = pyo.Constraint(model.time, model.period, rule=Pgrid_mult_rule)
    
    if pena=='tot' : 
        def charge_discharge_rule(model, t) : 
            return(model.Pc[t]*model.Pd[t]==0)
        model.notPC_Pd = pyo.Constraint(model.time, rule=charge_discharge_rule)
    
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

def solve(model, print_level = 7, printation=True, tol=None) :
    solver = SolverFactory('ipopt')
    if printation :
        solver.options['print_level'] = print_level
        solver.options['print_timing_statistics'] = 'yes'
    solver.options['max_iter'] = 3000
    if tol : 
        solver.options['tol'] = tol
    # solver.options['acceptable_tol'] = 1e-6
    solver.options['hsllib'] = '/usr/local/lib/libcoinhsl.dylib'
    # solver.options['nlp_scaling_method'] = 'none'
    solver.options['linear_solver'] = 'ma97'
    results = solver.solve(model, tee=printation)
    return solver, results
# model.display()

#%% Penalization variable test
timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 4, 0, 59))
Pena2test = [0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.05, 0.1, 0.2, 0.5, 1, 10, 100]
res = []
for coef in Pena2test : 
    model = build_model(timeframe, pena=coef)
    solver, results = solve(model)
    Pc = [model.Pc[t].value for t in model.time.data()]
    Pd = [model.Pd[t].value for t in model.time.data()]
    res.append((model.obj(), pena_charge_and_discharge(Pc, Pd, coef=1)))

#%% Plot batterie usage 
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 30, 23, 59))
timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
# model = build_model(timeframe, without_bat=True)
model = build_model(timeframe, pena=0.000001)
Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)

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
res = calculate_price(model, model.deltat, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays, Time_in_month, False, printation=False)


#%%
def charge_profile(Cb, Pprev, Eautocons, Econs, full_date, TE, TP, bat_price=359) :

    Days = separate_days(Econs, Eautocons, full_date, delta=dt.timedelta(days=2, hours=23, minutes=59))
    # timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))
    Pc = []
    Pd = []
    Ebat = []
    lastE = 0.2
    Ec = 0
    for k in range(0, len(Days)) : 
        # Should be fast
        print()
        print(k)
        print('Cb', Cb)
        print('lastE', lastE)
        print('sumPd', sum(Pd))
        print('sumPc', sum(Pc))
        
        small = build_model(Days[k]['date'], SOC0=lastE, definer=2, Econs=Days[k]['Econs'], Eautocons=Days[k]['Eprod'], Cb_param=Cb, Pprev=Pprev, TE=TE, TP=TP, bat_price=bat_price, pena=10)
        Ec = Ec + sum(small.Econs[t] for t in small.time)
        print('sum Econs', Ec)
        print(small.Cb)
        try : 
            solve(small, printation=False)
        except : 
            print("ça a loupé")
            small = build_model(Days[k]['date'], SOC0=lastE, definer=2, Econs=Days[k]['Econs'], Eautocons=Days[k]['Eprod'], Cb_param=Cb, Pprev=Pprev, TE=TE, TP=TP, bat_price=bat_price, pena=0.1)
            solve(small, printation=True)
        print('pena price', pena_charge_and_discharge([small.Pc[i].value for i in small.time], [small.Pd[i].value for i in small.time], coef=1))
        print('Cb2', small.Cb.value)
        Pc += [small.Pc[i].value for i in small.time]
        Pd += [small.Pd[i].value for i in small.time]
        Ebat += [small.E[i].value for i in small.time]
        if Cb == 0 : 
            lastE = 0
        else  :
            lastE = (small.E[small.time.at(-1)]/Cb)()
        
    return Days, Pc, Pd, Ebat

def create_big(Pc, Pd, Ebat, Cb, Pprev, Eautocons, Econs, full_date, TE, TP, bat_price=359) : 
    timeframe = (full_date[0], full_date[-1])
    big = build_model(timeframe, Econs=Econs, Eautocons=Eprod, TE=TE, TP=TP, bat_price=bat_price)
    for p in big.period : 
        big.Pprev[p].value = Pprev[p]
    
    big.Cb.value=Cb
    for t in big.time :
        big.Pc[t].value = Pc[t]
        big.Pd[t].value = Pd[t]
        big.E[t].value = Ebat[t]
        Egrid = big.Econs[t] + (big.Pc[t]-big.Pd[t])*big.deltat - Eautocons[t]
        Egrid = Egrid()
        big.Egrid_plus[t].value = Egrid*(Egrid>0)
        big.Egrid_minus[t].value = -Egrid*(Egrid<0)
        
        for p in big.period : 
            Pplus = (big.Econs[t]-Eautocons[t])/big.deltat  + (big.Pc[t]-big.Pd[t]) - big.Pprev[p]
            Pplus = Pplus()
            big.Pplus[t, p].value = Pplus*(Pplus>0)
            big.Pminus[t, p].value = -Pplus*(Pplus<0)
    
    Time, Nbdays, Time_in_month = define_time2(full_date, period_hours)
    res = calculate_price(big, big.deltat, big.TP, big.TE, big.TEauto, big.Time, big.tep, big.Kp, 323, Time_in_month, False, printation=True)()
    
    return big, res

Eprod=Eautocons
#%% 
# Eautocons, Econs, full_date, deltat = treat_data()
pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
Eautocons_pm, Econs_pm, full_time_pm, deltat_pm = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
deltat_pm = deltat_pm[0]
Eprod_pm, Econs_pm, full_date_pm, deltat_pm = increase_deltat(3, Eautocons_pm, Econs_pm, full_time_pm, deltat_pm)
#%% Part 1
import time
t = time.time()
bat_price=250
model = build_model(full_date_repr_div, definer=2, Econs=Econs_repr_div, Eautocons=Eprod_repr_div, pena=0.000001, selling=False, bat_price=bat_price)

# model = build_model(full_date_repr_pm, definer=2, Econs=Econs_repr_pm, Eautocons=Eprod_repr_pm, TE=TE_pm_2024, TP=TP_pm_2024, pena=0.001, selling=False, bat_price=bat_price)

solver, results = solve(model, print_level=7)
Cb=model.Cb.value
Pprev = [model.Pprev[p].value for p in range(6)]
#%% Part 2
# Cb=0
Days, Pc, Pd, Ebat = charge_profile(model, Cb, Pprev, Eprod, Econs, full_date, TE_pm_2024, TP_pm_2024, bat_price=bat_price)  
#%% Part 3
big, res = create_big(Pc, Pd, Ebat, Cb, Pprev, Eprod, Econs, full_date, TE_pm_2024, TP_pm_2024, bat_price=bat_price)
t2 = time.time()

#%% Bat values test Tub
model = build_model(full_date_repr_div, definer=2, Econs=Econs_repr_div, Eautocons=Eprod_repr_div, pena=0.000001, selling=False, bat_price=bat_price)
solver, results = solve(model, print_level=7)

Cb=model.Cb.value
Pprev = [model.Pprev[p].value for p in range(6)]
Res = {}
Cbs = [0, 10, 15, 16.1, 20, 25, 30, 40, 50]
for Cb in Cbs : 
    Days, Pc, Pd, Ebat = charge_profile(Cb, Pprev, Eprod, Econs, full_date, TE, TP, bat_price=250) 
    big, res = create_big(Pc, Pd, Ebat, Cb, Pprev, Eprod, Econs, full_date, TE, TP, bat_price=250) 
    Res[Cb] = big.obj()
    
fig, ax = plt.subplots()
ax.plot(Cbs, [Res[Cb] for Cb in Cbs], '+')
ax.set_xlabel('Battery size (kwh)')
ax.set_ylabel('Optimal objective function value')

path=os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_diff_bat_tub.json')
with open(path, "w") as f : 
    f.write(json.dumps(Res))
# Tubacer 
# Res = {0: 38684.487053163524,
#  10: 42976.06675500966,
#  20: 42353.28243364232,
#  30: 41884.32594734423,
#  40: 41563.33716281605,
#  50: 41363.64479026753,
#  60: 41266.219793633536,
#  70: 41247.34650072234}

# PM opti : 5743.539192368027, Cb=10.550895667461326
# {0: 8582.358261079064,
#  10: 8212.369599695057,
#  20: 8389.374759788827,
#  30: 8284.293013731369,
#  40: 8616.13115398514,
#  50: 9160.322028795279,
#  60: 9434.322018770821,
#  70: 9710.286782811387}
#%% Bat values test PM

model = build_model(full_date_repr_pm, definer=2, Econs=Econs_repr_pm, Eautocons=Eprod_repr_pm, TE=TE_pm_2024, TP=TP_pm_2024, pena=0.001, selling=False, bat_price=bat_price)
solver, results = solve(model, print_level=7)
Cb=model.Cb.value
Pprev = [model.Pprev[p].value for p in range(6)]

Res_pm = {}
Cbs = [0, 10, 15, 16.1, 20, 25, 30, 40, 50]
for Cb in Cbs : 
    Days, Pc, Pd, Ebat = charge_profile(Cb, Pprev, Eprod_pm, Econs_pm, full_date_pm, TE_pm_2024, TP_pm_2024, bat_price=250) 
    big, res = create_big(Pc, Pd, Ebat, Cb, Pprev, Eprod_pm, Econs_pm, full_date_pm, TE_pm_2024, TP_pm_2024, bat_price=250) 
    Res[Cb] = big.obj()
    
fig, ax = plt.subplots()
ax.plot(Cbs, [Res[cb] for cb in Cbs], '+')
ax.set_xlabel('Battery size (kwh)')
ax.set_ylabel('Optimal objective function value')

path=os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_diff_bat_pm.json')
with open(path, "w") as f : 
    f.write(json.dumps(Res))
#%% Test with varying prices 

Results_bat_price = {}
Cbs_prices = [k for k in range(150, 360, 10)]
Eprod=Eautocons
for price in Cbs_prices[:] : 
    try : 
        model = build_model(full_date_repr_div, definer=2, Econs=Econs_repr_div, Eautocons=Eprod_repr_div, pena=0.000001, selling=True, bat_price=price+0.01)
        solver, results = solve(model, print_level=7)
    except : 
        try : 
            price+=0.001
            model = build_model(full_date_repr_div, definer=2, Econs=Econs_repr_div, Eautocons=Eprod_repr_div, pena=0.000001, selling=True, bat_price=price+0.01)
            solver, results = solve(model, print_level=7)
        except : 
            Results_bat_price[price] = 'Not working'
    Cb=model.Cb.value
    Pprev = [model.Pprev[p].value for p in range(6)]
    
    Days, Pc, Pd, Ebat = charge_profile(model, Cb, Pprev, Eprod, Econs, full_date, TE, TP, bat_price=price)  
    big, res = create_big(Pc, Pd, Ebat, Cb, Pprev, Eprod, Econs, full_date, TE, TP, bat_price= price) 
    
    Results_bat_price[price] = {'obj':big.obj(), 'res':res, 'Cb':Cb, 'Pc':Pc, 'Pd':Pd, 'Ebat' : Ebat}

    path=os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_bat_price_tub_selling.json')
    with open(path, "w") as f : 
        f.write(json.dumps(Results_bat_price))
    
#%% same for PM
    
Results_bat_price_pm = {}
Cbs_prices = [k for k in range(150, 360, 10)]
# Eprod=Eautocons
for price in Cbs_prices[:] : 
    try : 
        model = build_model(full_date_repr_pm, definer=2, Econs=Econs_repr_pm, Eautocons=Eprod_repr_pm, pena=0.000001, selling=True, bat_price=price+0.01)
        solver, results = solve(model, print_level=7)
    except : 
        try : 
            price += 0.001
            model = build_model(full_date_repr_pm, definer=2, Econs=Econs_repr_pm, Eautocons=Eprod_repr_pm, pena=0.000001, selling=True, bat_price=price+0.01)
            solver, results = solve(model, print_level=7)
        except : 
            Results_bat_price_pm[price] = 'Not working'
    Cb=model.Cb.value
    Pprev = [model.Pprev[p].value for p in range(6)]
    
    Days, Pc, Pd, Ebat = charge_profile(model, Cb, Pprev, Eprod_pm, Econs_pm, full_date_pm, TE_pm_2024, TP_pm_2024, bat_price=price)  
    big, res = create_big(Pc, Pd, Ebat, Cb, Pprev, Eprod_pm, Econs_pm, full_date_pm, TE_pm_2024, TP_pm_2024, bat_price= price) 
    
    Results_bat_price_pm[price] = {'obj':big.obj(), 'res':res, 'Cb':Cb, 'Pc':Pc, 'Pd':Pd, 'Ebat' : Ebat}

    path=os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_bat_price_pm_selling.json')
    with open(path, "w") as f : 
        f.write(json.dumps(Results_bat_price))

#%% Final part reuse simple model to determine Pprev

Eprod_bat = [big.Eautocons[t] for t in big.time]
for k in range(len(Eprod_bat)) : 
    Eprod_bat[k] += (big.Pd[k].value - big.Pc[k].value)*big.deltat

Eautocons, Econs, full_time, deltat = treat_data()
assert full_time == full_date
big2, Time_in_month, Nbdays = build_model_without_bat(full_date, definer=2, Eautocons=Eprod_bat, Econs=Econs)
for p in big.period : 
    big2.Pprev[p].value = Pprev[p]
    
before = big2.obj()
# solver = SolverFactory('ipopt')
# solver.options['print_timing_statistics'] = 'yes'
# results = solver.solve(big2, tee=True)

solve(big2, tol=1e-16)
new_Pprev = [big2.Pprev[k].value for k in range(6)]
obj = big2.obj()

for p in big.period : 
    big.Pprev[p].value = new_Pprev[p]
res2 = calculate_price(big, big.deltat, big.TP, big.TE, big.TEauto, big.Time, big.tep, big.Kp, 323, Time_in_month, False, printation=False)

# Not working well and anyway does not seem useful before =38808, obj = 38783 (-30€ < -0.1%)

#%% Bat_price influence 
# obj = []
# bat = []
# pena_violation = []
# price = []
# for k in range(1) : 
#     bat_price = (359/10+0.019-1)*(k+1)/10 + 1
#     price.append(bat_price)
#     model = build_model(full_date_repr, definer=2, Econs=Econs_repr, Eautocons=Eprod_repr, pena=0, bat_price=bat_price)
#     solver, results = solve(model)
#     obj.append(model.obj())
#     bat.append(model.Cb.value)
#     Pc = [model.Pc[t].value for t in model.time.data()]
#     Pd = [model.Pd[t].value for t in model.time.data()]
#     pena_violation.append(pena_charge_and_discharge(Pc, Pd, coef=1))
    
# def save_values(path = 'Results/csv/bat_price.csv') :
#     df = pd.DataFrame(columns=['Batterie size (kwh)', 'Objective function', 'Battery price'])
#     df['Batterie size (kwh)'] = bat 
#     df['Objective function'] = obj 
#     df['Battery price'] = bat 
#     df.to_csv(path, sep=';')
    
# save_values(path='Results/csv/bat_price_pena.csv')

#%%
# solver, results = solve(model)
# real_time = [full_date[k] for k in model.time]

# result_E = [model.E[t].value for t in model.time]
# Econs_timeframe = [model.Econs[t] for t in model.time]
# Eprod_timeframe = [model.Eautocons[t] for t in model.time]

# fig = plt.figure()
# plt.plot(real_time, result_E, label='Battery Energy')
# plt.plot(real_time, Econs_timeframe, label='Energy Consumption')
# plt.plot(real_time, Eprod_timeframe, label='Energy Production')
# plt.legend()
# plt.plot()

# result_Pc = [model.Pc[t].value for t in model.time]
# result_Pd = [model.Pd[t].value for t in model.time]
# result_Pc_Pd = [model.Pc[t].value - model.Pd[t].value for t in model.time]
# Pcons_timeframe = [model.Pcons[t] for t in model.time]
# Pprod_timeframe = [model.Eautocons[t]/0.25 for t in model.time]

# fig2 = plt.figure()
# # plt.plot(real_time, result_Pc, label='Charge Power')
# # plt.plot(real_time, result_Pd, label='Decharge Power')
# plt.plot(real_time, result_Pc_Pd, label='charge + decharge power')
# plt.plot(real_time, Pcons_timeframe, label='Power Consumption')
# plt.plot(real_time, Pprod_timeframe, label='Power Production')
# plt.legend()
# plt.plot()

#%% Test temps de calcul
import time
t0 = dt.datetime(2024, 4, 1, 0, 0)
t1 = t0+dt.timedelta(hours=24)
n = 70
timeframes = [(t0, t0 + dt.timedelta(hours = 24) + k*dt.timedelta(hours = 12)) for k in range(n)]
times = []

for timeframe in timeframes[:] : 
    tic = time.time()
    t1 += dt.timedelta(hours = 12)
    model = build_model(timeframe, pena=0.0001)
    solver, results = solve(model)
    # try : solver, results = solve(model)
    # except : 
    #     model = build_model(timeframe, pena=0.0001)
    #     solve(model)
        
    times.append(time.time()-tic)
    
with open(os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'time.json'), 'w') as f:
    f.write(json.dumps(times))
    
#%%
import numpy as np

# On vérifie si on a une tendance polynomiale
p = np.polyfit(range(n), times, 2)
f = lambda x : p[0]*x**2 + p[1]*x + p[2]
plt.plot(range(n), times, '+')
plt.plot(range(n), [f(k) for k in range(n)])

#%% Test representative days month per month

# compare = []
# for k in range(1, 12) :
#     timerange = (dt.datetime(2024, k, 1, 0, 0), dt.datetime(2024, k, cal.monthrange(2024, k)[1], 23, 59))
#     model1 = build_model(timerange, definer=1)
#     solver, results = solve(model1)
#     standard_obj = model1.obj()
    
#     repr_days = []
    
#     i = 0
#     while full_date_new[i].month != k : 
#         i+=1
#     while full_date_new[i].month == k : 
#         repr_days.append(full_date_new[i])
#         i += 1 
        
#     model2 = build_model(repr_days, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new) 
#     solver2, results2 = solve(model2)
#     repr_obj = model2.obj()
#     compare.append((standard_obj, repr_obj))
    
    
