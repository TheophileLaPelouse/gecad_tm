"""
Optimization of with peer and batteries

Create the optimization model and then use the two previous files to load the parameters of the opti framework to do tests

Optimization model : 
Same as before with just the battery but adding peer2peer exchange.
For this need to considerate every prosumers and contract so different way of treating the thing, using the dico defined in opti_peer_prosumers.py

Optimization framework : 
- run the optimization model with representative days 
- run use the battery as parameters and Pcontracted to compute optimization over small intervals
- Compute by putting everything into a big model.
"""
import datetime as dt
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
import matplotlib.pyplot as plt
import pandas as pd
import json
from opti_peer_repr_days import get_repr_data
from opti_peer_prosumers import *
#%% Model definition

nb_peer = 4
Price_peer = [[0 for p in range(6)] for k in range(nb_peer)]

# For the moment for a first approximation we will use a default lineic resistance value equal to 10 Ohm/km and a tension of 1000V
# In the future maybe do the same as the price, one function for each peer-to-peer connection
def loss(dist, E, deltat, U, r) : 
    R = r*dist 
    # P = E/deltat 
    # I = P/U
    # Ploss = RI2
    # Eloss = R(E/U)^2/deltat
    return R*(E/U)**2/deltat

def battery_price(Cb, nbdays, bat_price=359, i=0.1, n=10, eps=0.002) :
    # i = discount rate
    # n lifetime
    # eps = service coefficient 
    # investment = 359 $/kwh/year, maintenance = 0.019$/kwh/year, lifetime = 9 years
    bat_price=bat_price*((i*(1+i)**n)/((1+i)**n-1))+bat_price*eps
    return Cb*bat_price*nbdays/365

def calc_tot_price(Price_peer, Prosumers, model) : 
    Se = 0 
    S_peer = 0 # We need to discuss about how this work in general 
    Sp = 0
    # nb_peer = len(model.Epeer_out) + 1
    S_pena = 0.0000001
    Time_ref = Prosumers[0]['Time_ref']    
    
    for k in model.peer : 
        for t in model.time : 
            Se += Prosumers[k]['TE'](t, Time_ref) * model.Egrid_plus[k, t]
        
        Pgrid = [val/model.deltat for val in model.Egrid_plus[k, :]]
        Pcontr_peer = [val for val in model.Pcontr[k, :]]
        for p in model.period : 
            Sp += Prosumers[k]['TP'](p) * model.Pcontr[k, p]
            for m in model.month : 
                S_pena += Prosumers[k]['TPena'](p, m, Pgrid, Pcontr_peer, Time_ref)
    
        # for kbis in range(nb_peer) : 
        #     if k != kbis : 
        #         for t in model.time : 
        #             S_peer += Price_peer[]
        
    return Se + S_peer + Sp + S_pena 

def build_model(Prosumers, **kwargs) : 
    mod = pyo.ConcreteModel()

    Time_ref = Prosumers[0]['Time_ref']
    nbdays = len(Time_ref)/96
    max_month = max(Time_ref, key=lambda x : x[1])[1]
    # Sets
    mod.time = pyo.RangeSet(0, len(Time_ref)-1)
    mod.month = pyo.RangeSet(1, max_month)
    mod.period = pyo.RangeSet(0, 5)
    mod.peer = pyo.RangeSet(0, len(Prosumers) - 1)


    # Parameters 
    mod.deltat = 0.25
    mod.Eload = pyo.Param(mod.peer, mod.time, 
        initialize= {(k, t) : Prosumers[k]['load'][t] for t in mod.time for k in mod.peer})
    mod.Eprod = pyo.Param(mod.peer, mod.time, 
        initialize= {(k,t) : Prosumers[k]['prod'][t] for t in mod.time for k in mod.peer})

    # Variables 
    mod.Egrid_plus = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Egrid_minus = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Ppena_plus = pyo.Var(mod.peer, mod.time, mod.period, domain=pyo.NonNegativeReals)
    mod.Ppena_minus = pyo.Var(mod.peer, mod.time, mod.period, domain=pyo.NonNegativeReals)
    mod.Pcontr = pyo.Var(mod.peer, mod.period, domain=pyo.NonNegativeReals)
    mod.Pc = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Pd = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.SOC = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Epeer_out = pyo.Var(mod.peer, mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Epeer_in = pyo.Var(mod.peer, mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Cb = pyo.Var(mod.peer, domain=pyo.NonNegativeReals)
    
    # Contraints 
    # Energy balance 
    def balance(mod, peer, time) : 
        return (mod.Egrid_plus[peer, time] - mod.Egrid_minus[peer, time] == 
            mod.Eload[peer, time] - mod.Eprod[peer, time] 
            + sum(mod.Epeer_out[peer, peer2, time] - mod.Epeer_in[peer, peer2, time] for peer2 in mod.peer) 
            + (mod.Pc[peer, time] - mod.Pd[peer, time])*mod.deltat
            )
    mod.balance_con = pyo.Constraint(mod.peer, mod.time, rule=balance)

    def pena_cons(mod, peer, t, p) :
        return (mod.Ppena_plus[peer, t, p] - mod.Ppena_minus[peer, t, p] ==
            (mod.Egrid_plus[peer, t] + mod.Egrid_minus[peer, t])/mod.deltat - mod.Pcontr[peer, p]
        )

    mod.pena_cons = pyo.Constraint(mod.peer, mod.time, mod.period, rule=pena_cons)

    # Contracted power 
    def Pcontr_rule(model, peer, p) : 
        if p == mod.period.last() :
            return mod.Pcontr[peer, p] >= 0
        return mod.Pcontr[peer, p] <= mod.Pcontr[peer, p+1]
    if not kwargs.get('Pcontr') :
        mod.Pcontr_con = pyo.Constraint(mod.peer, mod.period, rule=Pcontr_rule)

    # Battery
    # bat_parameters : [eff_ch, eff_dch, soc_min, soc_max, soc_init, rate_ch, rate_dch, last_val]
    def max_rule(mod, peer, t) : 
        return mod.SOC[peer, t] <= mod.Cb[peer]
    def min_rule(mod, peer, t) : 
        return mod.SOC[peer, t] >= Prosumers[peer]['bat_parameters'][2]*mod.Cb[peer]
    mod.capacity_con_max = pyo.Constraint(mod.peer, mod.time, rule=max_rule)
    mod.capacity_con_min = pyo.Constraint(mod.peer, mod.time, rule=min_rule)
    
    def max_pow_rule(mod, peer, t) : 
        return mod.Pc[peer, t] <= Prosumers[peer]['bat_parameters'][5]*mod.Cb[peer]
    def min_pow_rule(mod, peer, t) :
        return mod.Pd[peer, t] <= Prosumers[peer]['bat_parameters'][6]*mod.Cb[peer]
    mod.pow_con_max = pyo.Constraint(mod.peer, mod.time, rule=max_pow_rule)
    mod.pow_con_min = pyo.Constraint(mod.peer, mod.time, rule=min_pow_rule)
    
    def battery_rule(mod, peer, t) : 
        if t == mod.time.first() : 
            # return mod.E[t] == (0.2*mod.Cb + mod.Cb)/2
            return mod.SOC[peer, t] == Prosumers[peer]['bat_parameters'][4]*mod.Cb[peer]
            # return mod.E[t] == 5
        return (mod.SOC[peer, t] == mod.SOC[peer, t-1] + 
            (Prosumers[peer]['bat_parameters'][0]*mod.Pc[peer, t] 
            - mod.Pd[peer, t]/Prosumers[peer]['bat_parameters'][1])*mod.deltat
        )
    mod.battery_con = pyo.Constraint(mod.peer, mod.time, rule=battery_rule)
    

    def battery_last_val(mod, peer) : 
        return (mod.SOC[peer, mod.time.at(-1)]>=Prosumers[peer]['bat_parameters'][6]*mod.Cb[peer])
    mod.battery_last_val = pyo.Constraint(mod.peer, rule=battery_last_val) # for remaining good when optimizing over small intervals
    

    # Peer
    r, U = kwargs.get('r', 10), kwargs.get('U', 1000)
    def loss_con(mod, peer1, peer2, t) : 
        return (mod.Epeer_out[peer1, peer2, t] == 
            loss(Prosumers[peer1]['dist'][peer2], mod.Epeer_in[peer2, peer1, t], mod.deltat, U, r) 
            + mod.Epeer_in[peer2, peer1, t]
        ) # Not linear as the losses are not linear
    mod.loss_con = pyo.Constraint(mod.peer, mod.peer, mod.time, rule=loss_con)

    # def peer_transfer_limit(mod, peer, t) : Not needed as it should not be optimal to do this
    #     return sum(mod.Epeer_in[peer][peer2][t] for peer2 in model.peer) <= max(0, model.Eprod[peer, t] - model.Eload[peer, t])

    # Maybe some maximum peer exchange thing, but for know no more constraint

    mod.obj = pyo.Objective(expr=calc_tot_price(Price_peer, Prosumers, mod)
                            + sum(battery_price(mod.Cb[peer], nbdays) for peer in mod.peer))

    return mod

def solve(model, print_level = 7, printation=True, tol=None) :
    # Function to solve the model using ipopt
    # The list of the options are described on the IPOPT documentation, almost all of them are useable using pyomo.
    solver = SolverFactory('ipopt')
    if printation :
        solver.options['print_level'] = print_level
        solver.options['print_timing_statistics'] = 'yes'
    solver.options['max_iter'] = 3000
    if tol : 
        solver.options['tol'] = tol
    # solver.options['acceptable_tol'] = 1e-6
    solver.options['hsllib'] = '/usr/local/lib/libcoinhsl.dylib' # Depends on the installation
    # solver.options['nlp_scaling_method'] = 'none'
    solver.options['linear_solver'] = 'ma97' # The most efficient for me
    results = solver.solve(model, tee=printation)
    return solver, results

#%% load representative days results 
if __name__ == '__main__' : 

    path_index = os.path.join(os.path.dirname(__file__), 'Results/csv/index_prosumers.json')
    path_repr = os.path.join(os.path.dirname(__file__), 'Results/csv/Prosumers_repr.pkl')
    path_tot = os.path.join(os.path.dirname(__file__), 'Results/csv/Prosumers_dico.pkl')
    with open(path_index) as f : 
        index_prosumers = json.load(f)
    Prosumers_tot = load_prosumers(path_tot)
    Prosumers_repr = load_prosumers(path_repr)
    
    # Copy the function that were not saved 
    for k in range(len(index_prosumers)) : 
        comp = index_prosumers[k]
        for key, val in Prosumers_tot[comp].items() : 
            if callable(val) :
                Prosumers_repr[k][key] = val
    #%%
    mod = build_model(Prosumers_repr)
    #%%
    solve(mod)
