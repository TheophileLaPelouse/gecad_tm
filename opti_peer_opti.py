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

def pena_charge_and_discharge(Pc, Pd, time=None, coef=0.1) : 
    """
    Convex if Pc and Pd are positive
    """
    Pc = [val for val in Pc]
    Pd = [val for val in Pd]
    if coef == 'tot' : # If you don't want this penalization cost in the model
        return 0
    if Pd is None : # For testing purpose
        return coef*sum(p for p in Pc)
    else : # Normal usage 
        if time is None : # If used outside of the optimization or for other values than Pc and Pd
            return coef*sum(Pc[t]*Pd[t] for t in range(len(Pc)))
        else : # Optimization normal usage
            return coef*sum(Pc[t]*Pd[t] for t in time)

def battery_price(Cb, nbdays, bat_price=359, i=0.1, n=10, eps=0.002) :
    # i = discount rate
    # n lifetime
    # eps = service coefficient 
    # investment = 359 $/kwh/year, maintenance = 0.019$/kwh/year, lifetime = 9 years
    bat_price=bat_price*((i*(1+i)**n)/((1+i)**n-1))+bat_price*eps
    return Cb*bat_price*nbdays/365

def calc_tot_price(Price_peer, Prosumers, model) : 
    """
    Compute the total price of the electricity, it should be noted that the function computing each prices
    are defined in the opti_peer_prosumers.py file. For now there is no peer-to-peer and selling price.
    """
    Se = 0 
    S_peer = 0 # We need to discuss about how this work in general 
    Sp = 0
    # nb_peer = len(model.Epeer_out) + 1
    S_pena = 0.0000001
    Time_ref = Prosumers[0]['Time_ref']    
    
    for k in model.peer : 
        for t in model.time : 
            Se += Prosumers[k]['TE'](t, Time_ref) * model.Egrid_plus[k, t]
            # Se += Prosumers[k]['TEsell'](t, Time_ref) * model.Egrid_minus[k, t]
        
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
    """
    Builds a Pyomo optimization model for peer-to-peer energy trading, 
    battery sizing and management and contracted power optimization.

    The model is convex ensuring the convergence using IPOPT solver.
    You can use the kwargs to set the parameters of the model and use the model the way you want.

    Parameters:
    ----------
    Prosumers : list of dict
        Dictionnary defined in opti_peer_prosumers.py but redefined as a list for fixed indexing.
        An other value should be used to rememeber the index of the prosumer in the list.

    **kwargs : dict
        Optional keyword arguments to customize the model:
        - 'bat_param': list or float
            Initial battery capacities for each peer. If a list, it should have one value per peer.
            If a float, the same value is applied to all peers.
        - 'Pcontr': list or None
            Contracted power values for each peer and period. It should be a 2D list 
            where each sublist corresponds to a peer and contains values for each period.
        - 'no_battery': bool
            If True, disables battery usage by setting battery capacity and charge/discharge power to zero.
        - 'no_peer': bool
            If True, disables peer-to-peer energy exchanges by setting all peer exchange variables to zero.
        - 'bat_price': float
            Cost of battery capacity per kWh (default: 359).
        - 'coef': float
            Coefficient for penalizing battery charge and discharge (default: 1).

    Returns:
    -------
    mod : pyomo.ConcreteModel
        A Pyomo ConcreteModel object representing the optimization problem.
    """
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
    mod.nbdays = nbdays
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
    
    mod.Pc = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Pd = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.SOC = pyo.Var(mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Epeer_out = pyo.Var(mod.peer, mod.peer, mod.time, domain=pyo.NonNegativeReals)
    mod.Epeer_in = pyo.Var(mod.peer, mod.peer, mod.time, domain=pyo.NonNegativeReals)
    
    Cbs = kwargs.get('bat_param')
    if isinstance(Cbs, list) : 
        mod.Cb = pyo.Var(mod.peer, domain=pyo.NonNegativeReals, initialize={k : Cbs[k] for k in mod.peer})
    elif isinstance(Cbs, (float, int)) :
        mod.Cb = pyo.Var(mod.peer, domain=pyo.NonNegativeReals, initialize={k : Cbs for k in mod.peer})
    else : 
        mod.Cb = pyo.Var(mod.peer, domain=pyo.NonNegativeReals)
    
    Pcontr_param = kwargs.get('Pcontr')
    if isinstance(Pcontr_param, list) :
        mod.Pcontr = pyo.Var(mod.peer, mod.period, domain=pyo.NonNegativeReals, 
            initialize={(peer, p) : Pcontr_param[peer][p] for peer in mod.peer for p in mod.period})
    else : 
        mod.Pcontr = pyo.Var(mod.peer, mod.period, domain=pyo.NonNegativeReals)

    flag_bat = 1
    flag_peer = 1
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
            (mod.Egrid_plus[peer, t] - mod.Egrid_minus[peer, t])/mod.deltat - mod.Pcontr[peer, p]
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
    print("bonjour, no_battery", kwargs.get('no_battery'))
    if kwargs.get('no_battery') : 
        flag_bat = 0
        def no_bat_con(mod, peer) : 
            return mod.Cb[peer] == 0
        mod.no_bat = pyo.Constraint(mod.peer, rule=no_bat_con)
        def no_power_charge(mod, peer, time) : 
            return mod.Pc[peer, time] == 0
        def no_power_discharge(mod, peer, time) : 
            return mod.Pd[peer, time] == 0
        mod.no_bat_c = pyo.Constraint(mod.peer, mod.time, rule=no_power_charge)
        mod.no_bat_d = pyo.Constraint(mod.peer, mod.time, rule=no_power_discharge)
        
    else :
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
    # r, U = kwargs.get('r', 10), kwargs.get('U', 1000)
    # def loss_con(mod, peer1, peer2, t) : 
    #     return (mod.Epeer_out[peer1, peer2, t] == 
    #         loss(Prosumers[peer1]['dist'][peer2], mod.Epeer_in[peer2, peer1, t], mod.deltat, U, r) 
    #         + mod.Epeer_in[peer2, peer1, t]
    #     ) # Not linear as the losses are not linear
    # mod.loss_con = pyo.Constraint(mod.peer, mod.peer, mod.time, rule=loss_con)
    # Exchange are done threw the grid lines so, losses can not be counted here but in the grid results.
    
    if kwargs.get('no_peer') :
        flag_peer = 0
        def no_peer_con(mod, peer1, peer2, t) : 
            return mod.Epeer_out[peer1, peer2, t] == 0
        mod.no_peer = pyo.Constraint(mod.peer, mod.peer, mod.time, rule=no_peer_con)
                    
        
    # else : 
    def peer_out_in(mod, peer1, peer2, t) : 
        return mod.Epeer_out[peer1, peer2, t] == mod.Epeer_in[peer2, peer1, t]
    mod.peer_out_in = pyo.Constraint(mod.peer, mod.peer, mod.time, rule=peer_out_in)
    
    def peer_auto_peer(mod, peer, t) : 
        return mod.Epeer_out[peer, peer, t] == 0
    mod.peer_auto_peer = pyo.Constraint(mod.peer, mod.time, rule=peer_auto_peer)

    def peer_transfer_limit(mod, peer, t) :
        return sum(mod.Epeer_out[peer, peer2, t] for peer2 in mod.peer) <= ((mod.Eprod[peer, t] - mod.Eload[peer, t]) + abs(mod.Eprod[peer, t] - mod.Eload[peer, t]))/2
    mod.peer_transfer_limit = pyo.Constraint(mod.peer, mod.time, rule=peer_transfer_limit)

    # Maybe some maximum peer exchange thing, but for know no more constraint

    mod.obj = pyo.Objective(expr=calc_tot_price(Price_peer, Prosumers, mod)
                            + flag_bat*sum(battery_price(mod.Cb[peer], nbdays, bat_price=kwargs.get('bat_price', 359)) for peer in mod.peer)
                            + flag_bat*sum(pena_charge_and_discharge(mod.Pc[peer, :], mod.Pd[peer, :], coef=kwargs.get('coef', 1), time=mod.time) for peer in mod.peer)
                            )

    return mod

def solve(model, **kwargs) :
    # Function to solve the model using ipopt
    # The list of the options are described on the IPOPT documentation, almost all of them are useable using pyomo.
    solver = SolverFactory('gurobi')
    # solver = SolverFactory('ipopt')
    # if kwargs.get('printation') :
    #     solver.options['print_level'] = kwargs.get('print_level', 7)
    #     solver.options['print_timing_statistics'] = 'yes'
    # solver.options['max_iter'] = kwargs.get('max_iter', 3000)
    # if kwargs.get('tol') : 
    #     solver.options['tol'] = kwargs.get('tol')
    # solver.options['acceptable_tol'] = 1e-6
    # solver.options['hsllib'] = '/usr/local/lib/libcoinhsl.dylib' # Depends on the installation
    # solver.options['nlp_scaling_method'] = 'none'
    # solver.options['linear_solver'] = 'ma97' # The most efficient for me
    import time 
    t1 =  time.time()
    results = solver.solve(model, tee=kwargs.get('printation', True))
    t2 = time.time()
    return solver, results, t2-t1

def create_sub_prosumers(Prosumers_tot, beg, end) : 
    sub_prosumer = []
    for key in Prosumers_tot : 
        sub_prosumer.append({})
        for k in Prosumers_tot[key] : 
            if isinstance(Prosumers_tot[key][k], list) and k != 'bat_parameters': 
                sub_prosumer[-1][k] = Prosumers_tot[key][k][beg:end]
            else : 
                sub_prosumer[-1][k] = Prosumers_tot[key][k]
    return sub_prosumer

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
                
    Prosumers_1m = create_sub_prosumers(Prosumers_tot, 96, 96*2)
    for k in range(len(index_prosumers)) : 
        Prosumers_1m[k]['bat_parameters'][4] = 0.5
    kwargs = {'coef' : 1, 
              'bat_price' : 100, 
              # 'no_battery' : True, 
              # 'no_peer' : True
              }

    in_use = Prosumers_1m
    
    #%%
    mod = build_model(in_use, **kwargs)
    #%%
    solve(mod, max_iter=5000, printation=True)
    #%% fix Results
    Results = {}
    for k in range(len(in_use)) : 
        val = in_use[k]
        key = index_prosumers[k]
        Results[key] = {}
        Results[key]['full_date'] = val['full_date']
        Results[key]['Time_ref'] = val['Time_ref']
        for t in mod.time : 
            Results[key]['Egrid_plus'] = [mod.Egrid_plus[k, t].value for t in mod.time]
            Results[key]['Egrid_minus'] = [mod.Egrid_minus[k, t].value for t in mod.time]
            Results[key]['SOC'] = [mod.SOC[k, t].value for t in mod.time]
            Results[key]['Epeer_out'] = [sum([mod.Epeer_out[k, peer2, t].value for peer2 in mod.peer]) for t in mod.time]
            Results[key]['Epeer_in'] = [sum([mod.Epeer_in[k, peer2, t].value for peer2 in mod.peer]) for t in mod.time]
            Results[key]['Pcontr'] = [mod.Pcontr[k, t].value for t in mod.period]
            Results[key]['Ppena_plus'] = [[mod.Ppena_plus[k, t, p].value for p in mod.period] for t in mod.time]
            Results[key]['Ppena_minus'] = [[mod.Ppena_minus[k, t, p].value for p in mod.period] for t in mod.time]
            Results[key]['Pc'] = [mod.Pc[k, t].value for t in mod.time]
            Results[key]['Pd'] = [mod.Pd[k, t].value for t in mod.time]
            Results[key]['Cb'] = mod.Cb[k].value
            Results[key]['Eload'] = [mod.Eload[k, t] for t in mod.time]
            Results[key]['Eprod'] = [mod.Eprod[k, t] for t in mod.time]
    #%% plot results
    for key in Results : 
        Eload_day = [[]]
        Eprod_day = [[]]
        SOC_day = [[]]
        E_peer_out_day = [[]]
        E_peer_in_day = [[]]
        current_day = Results[key]['full_date'][0].date()
        for t in mod.time : 
            if Results[key]['full_date'][t].date() != current_day : 
                Eload_day.append([])
                Eprod_day.append([])
                SOC_day.append([])
                E_peer_out_day.append([])
                E_peer_in_day.append([])
                current_day = Results[key]['full_date'][t].date()
            Eload_day[-1].append(Results[key]['Eload'][t])
            Eprod_day[-1].append(Results[key]['Eprod'][t])
            SOC_day[-1].append(Results[key]['SOC'][t])
            E_peer_out_day[-1].append(Results[key]['Epeer_out'][t])
            E_peer_in_day[-1].append(Results[key]['Epeer_in'][t])
        
        mean_val = {'Eload' : [], 'Eprod' : [], 'SOC' : [], 'Epeer_out' : [], 'Epeer_in' : []}
        nb_hours_max = max(len(Eload_day[k]) for k in range(len(Eload_day)))
        valid_days = [k for k in range(len(Eload_day)) if len(Eload_day[k]) == nb_hours_max]
        nb_days = len(valid_days)
        for k in range(nb_hours_max) : 
            mean_val['Eload'].append(sum(Eload_day[i][k] for i in valid_days)/nb_days)
            mean_val['Eprod'].append(sum(Eprod_day[i][k] for i in valid_days)/nb_days)
            mean_val['SOC'].append(sum(SOC_day[i][k] for i in valid_days)/nb_days)
            mean_val['Epeer_out'].append(sum(E_peer_out_day[i][k] for i in valid_days)/nb_days)
            mean_val['Epeer_in'].append(sum(E_peer_in_day[i][k] for i in valid_days)/nb_days)
        

        # Plotting
        fig, ax = plt.subplots()
        hours = range(len(mean_val['Eload']))
        ax.plot(hours, mean_val['Eload'], '-o', label='Eload')
        ax.plot(hours, mean_val['Eprod'], '-x', label='Eprod')
        ax.plot(hours, mean_val['SOC'], '--o', label='SOC')
        ax.plot(hours, mean_val['Epeer_out'], '--x', label='Epeer_out')
        ax.plot(hours, mean_val['Epeer_in'], '--+', label='Epeer_in')
        ax.legend()
        ax.set_xlabel('Time')
        ax.set_ylabel('Value')
        ax.set_title('Mean values for ' + key)
    plt.show()


    