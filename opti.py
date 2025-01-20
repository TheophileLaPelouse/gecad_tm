from prices import define_time, Pcons, Econs, Eautocons, TEauto, tep, Kp, period_hours

TP = [0.066889, 0.040255, 0.031037, 0.025345, 0.004733, 0.002652]
TE = [0, 0, 0.145440, 0.167703, 0, 0.150691] 

import datetime as dt
import pyomo.environ as pyo
from pyomo.opt import SolverFactory

#%% Model construction

def calculate_price(Pprev, Pcons, P_minus_P, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays) :
    # For it to be faster, we could rewrite this function in a C code and import it 
    # -> it will probably greatly speed of the evaluation of the objective function
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    Spena_P = [0.00001 for k in range(6)]
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays
        for t in Time[p].value : 
            Se += TE[p]*(Econs[t]-Eautocons[t])
            Se_p[p] += TE[p]*(Econs[t]-Eautocons[t])
            Seauto += TEauto[p]*Eautocons[t]
            Spena_P[p] += ((Pcons[t] - Pprev[p] + abs(Pcons[t] - Pprev[p]))/2)**2
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
    return Se + Seauto + Spena + Sp


timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))

Time, Nbdays = define_time(timeframe, period_hours)
timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))

model = pyo.ConcreteModel()

model.period = pyo.RangeSet(0, len(TP)-1)
model.time = pyo.RangeSet(timerange[0], timerange[1])

model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=max(Pcons))
# model.P_minus_P = pyo.Var(model.period, model.time, domain=pyo.NonNegativeReals, initialize = 0)

model.Pcons = pyo.Param(model.time, initialize={t: Pcons[t] for t in model.time})
model.Econs = pyo.Param(model.time, initialize={t: Econs[t] for t in model.time})
model.Eautocons = pyo.Param(model.time, initialize={t: Eautocons[t] for t in model.time})
model.TP = pyo.Param(model.period, initialize={p: TP[p] for p in model.period})
model.TE = pyo.Param(model.period, initialize={p: TE[p] for p in model.period})
model.TEauto = pyo.Param(model.period, initialize={p: TEauto[p] for p in model.period})
model.Time = pyo.Param(model.period, initialize={p: Time[p] for p in model.period}, mutable=True)
model.tep = pyo.Param(initialize=tep)
model.Kp = pyo.Param(model.period, initialize={p : Kp[p] for p in model.period})

# model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.P_minus_P, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays))
model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons,0, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays))

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
