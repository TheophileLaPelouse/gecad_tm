"""
Caracterisation of the prosumers and the prosumer groups

The goal here is to produce a container with for each prosumer the following dictionnary:
{
    TE : f(t) function that computes the energy cost depending on t a value between 0 and 29I09UI4309U corresponding to the time interval studied
    TP : f(p) function that computes the power cost depending on the period p 
    Time_ref : [(p, m), ...] Time_ref[t] = (p, m) where p is the period and m the month for time t
    full_date : [date1, ...]
    TPena : f(p, m, pgrid, pcont) function that computes the penalisation cost depending on the period, the month and the list of pgrid (only the penalizated affected one) and pcontracted
    load : equivalent to Econs before
    prod : equivalent to Eprod (or Eautocons) before
    dist : [dist1, dist2, ..., distn] the distances to the other prosumers for computing the loss
    bat_parameters : [eff_ch, eff_dch, soc_min, soc_max, soc_init, rate_ch, rate_dch, last_val] the battery parameters
    (maybe) V : voltage
    (maybe) constraints : Other constraints defined in a str ?
    
}

We will also need a function
Loss(dist1, dist2, power, (maybe) voltage) that computes the loss depending on the distance and the power (and maybe voltage)

"""

from prices_tubacer import TE, TE_new, TP, TP_new
from prices_porto_motor import TE_pm_2024, TP_pm_2024
from prices_TMG import TE_TMG, TP_TMG
from prices import treat_data, define_time, define_time2, tep, Kp, increase_deltat, reduce_deltat
from representative_days import separate_days
from opti import build_model, calculate_price, period_hours
import datetime as dt
import calendar as cal
from pyomo.opt import SolverFactory
import os
import pandas as pd
import pickle
from copy import deepcopy

#%%

def compute_energy_price(TE, t, Time_ref) : 
    p, m = Time_ref[t]
    return TE[m][p]

def compute_power_price(TP, p) : 
    return TP[p]

def compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref) : 
    s = 0.0000000001
    for t in range(len(Time_ref)) :
        p, m = Time_ref[t] 
        if p == period and m == month : 
            s += (pgrid[t] - pcont[p]) ** 2
    return Kp[period]*tep*s**0.5

def full_date_treatment(full_date, period_hours) :
    Time, Nbdays, Time_in_month = define_time2(full_date, period_hours)
    Time_ref = [None for k in range(len(full_date))]
    for p in range(len(Time)) : 
        for t in Time[p] :
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            Time_ref[t] = (p, m)
            
    return Time_ref
        

def compute_energy_price_tub(t, Time_ref) : 
    return compute_energy_price(TE, t, Time_ref)
def compute_power_price_tub(p) : 
    return compute_power_price(TP, p)
def compute_penalization_price_tub(period, month, pgrid, pcont, Time_ref) : 
    return compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref)
def make_dico_tub(nb_prosumers=4) :
    Eprod, Econs, full_date, deltat = treat_data(name="TUBACER")
    Time_ref = full_date_treatment(full_date, period_hours)
    dists = [0 for k in range(nb_prosumers-1)]
    bat_parameters = [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5]
    
    dico = {
        "TE" : compute_energy_price_tub,
        
        "TP" : compute_power_price_tub,
        "TPena" : compute_penalization_price_tub,
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eprod,
        "full_date" : full_date,
        "dist" : dists,
        "bat_parameters" : bat_parameters,
    }
    
    return dico
    

def compute_energy_price_pm(t, Time_ref) : 
    return compute_energy_price(TE_pm_2024, t, Time_ref)
def compute_power_price_pm(p) : 
    return compute_power_price(TP_pm_2024, p)
def compute_penalization_price_pm(period, month, pgrid, pcont, Time_ref) : 
    return compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref)
def make_dico_PM(nb_prosumers=4) :
    pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
    
    Eprod, Econs, full_date, deltat = increase_deltat(3, Eautocons, Econs, full_time, deltat[0])

    Time_ref = full_date_treatment(full_date, period_hours)
    
    dico = {
        "TE" : compute_energy_price_pm,
        "TP" : compute_power_price_pm,
        "TPena" : compute_penalization_price_pm,
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eprod,
        "full_date" : full_date,
        "dist" : [0 for k in range(nb_prosumers-1)],
        "bat_parameters" : [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5, 0.45],
    }
    return dico 


def compute_energy_price_tmg(t, Time_ref) : 
    return compute_energy_price(TE_TMG, t, Time_ref)
def compute_power_price_tmg(p) : 
    return compute_power_price(TP_TMG, p)
def compute_penalization_price_tmg(period, month, pgrid, pcont, Time_ref) : 
    return compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref)
def make_dico_TMG(nb_prosumers=4) :
    tmg_path = os.path.join(os.path.dirname(__file__), 'Datasets', '4_TMG', 'Curvas_TMG_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=tmg_path, prod_col=-1, cons_col='Consumo kWh', 
                                                 date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
                                                 one_time_col=False, sheet_name=0)
    Eprod, Econs, full_time, deltat = reduce_deltat(4, Eautocons, Econs, full_time, deltat[0])
    
    Time_ref = full_date_treatment(full_time, period_hours)
    dico = {
        "TE" : compute_energy_price_tmg,
        "TP" : compute_power_price_tmg,
        "TPena" : compute_penalization_price_tmg,
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eprod,
        "full_date" : full_time,
        "dist" : [0 for k in range(nb_prosumers-1)],
        "bat_parameters" : [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5, 0.45],
    }
    
    return dico

def make_dico_Nar(nb_prosumers=4) : 
    na2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '3_NARONTEC', 'Curvas_carga_Narontec_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=na2024_path, prod_col=-1, cons_col='Consumo kWh', 
                                                 date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
                                                 one_time_col=False, sheet_name=0)
    deltat = deltat[0]
    Time_ref = full_date_treatment(full_time, period_hours)
    dico = {
        "TE" : lambda t: compute_energy_price(TE_Nar, t, Time_ref),
        "TP" : lambda p: 0,
        "TPena" : lambda period, month, pgrid, pcont: 0,
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eautocons,
        "dist" : [0 for k in range(nb_prosumers-1)],
        "bat_parameters" : [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5, 0.45],
    }
    
    

def make_dico() : 
    
    Prosumers = {
        "TUBACER" : make_dico_tub(),
        "Porto_Motor" : make_dico_PM(),
        "TMG" : make_dico_TMG()
    }
    
    # We want to have an exact correspondance for each date in the lists of each producer
    index = {key : [] for key in Prosumers}
    current_indice = {key : 0 for key in Prosumers}
    full_date_sets = {key : set(Prosumers[key]['full_date']) for key in Prosumers}

    full_date_gen = []
    first_date = min([val for val in [Prosumers[key]['full_date'][0] for key in Prosumers]])
    last_date = max([val for val in [Prosumers[key]['full_date'][-1] for key in Prosumers]])
    deltat = dt.timedelta(minutes = 15)
    
    date = first_date
    # We go through each possible dares and uses them if they are present for each consumers 
    while date < last_date :
        # print('date', date)
        flag = True
        for key in Prosumers : 
            # print('key', key)
            if not date in full_date_sets[key] : 
                flag = False
            else :     
                for_print = current_indice[key]
                while Prosumers[key]['full_date'][current_indice[key]] != date :
                    # if current_indice[key] - for_print < 50 :
                        # print('current_indice date', Prosumers[key]['full_date'][current_indice[key]])
                    current_indice[key] += 1 
                    # This should work because list in the right order with the same time interval
                    # if not working it is a data problem
        
        if flag : 
            for key in Prosumers : 
                index[key].append(current_indice[key])
            full_date_gen.append(date)
        
        date += dt.timedelta(minutes=15)
    
    for key in Prosumers :
        print(key)
        Prosumers[key]["load"] = [Prosumers[key]["load"][i] for i in index[key]] 
        Prosumers[key]["prod"] = [Prosumers[key]["prod"][i] for i in index[key]] 
        Prosumers[key]["Time_ref"] = [Prosumers[key]["Time_ref"][i] for i in index[key]] # Should not be general because period can depend on the consumer
        Prosumers[key]["full_date"] = full_date_gen
        
    return Prosumers, index
    
def load_prosumers(path) :
    with open(path, 'rb') as f : 
        Prosumers = pickle.load(f)
    return Prosumers 

def save_prosumers(Prosumers, path) : 
    if isinstance(Prosumers, dict) :
        to_save = deepcopy(Prosumers)
        for key in Prosumers : 
            to_save[key]['full_date'] = [val.to_pydatetime() for val in to_save[key]['full_date']]
    else : 
        to_save = []
        for dico in Prosumers : 
            dico_to_save = {k : v for k, v in dico.items() if not callable(v)} # remove the functions 
            to_save.append(dico_to_save)
    try : 
        with open(path, 'wb') as f : 
            pickle.dump(to_save, f, pickle.HIGHEST_PROTOCOL)
    except Exception as e : 
        print(e)
#%%

# What we need to verify is if the time for the values corresponds, mainly because of the change in hour.

if __name__ == '__main__' : 
    Prosumers, index = make_dico() 
    
    path = os.path.join(os.path.dirname(__file__), 'Results/csv/Prosumers_dico.pkl')
    save_prosumers(Prosumers, path)
    
#%% Just some plotting 
if __name__ == '__main__' : 
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Separate days for Tubacer
    days = separate_days(Prosumers["TUBACER"]["load"], Prosumers["TUBACER"]["prod"], Prosumers["TUBACER"]["full_date"])
    
    # Plot production profile for 5 days
    plt.figure(figsize=(12, 12))
    field = 'Eprod'
    Title = 'Production'
    days.sort(key=lambda x : sum(val for val in x[field]))
    I = [len(days)//4, 3*len(days)//4, len(days)-10, len(days)-1]
    # I = range(200,201)
    for i in I:
        hours = np.linspace(0, 24, len(days[i][field]))
        # plt.plot(hours, days[i]['Eprod'], label=f'Day {i+1}')
        plt.plot(hours, days[i][field], label=f'Day {i+1}', linewidth=2, linestyle='--', marker='o')
    
    plt.title(Title)
    plt.xlabel("Time")
    plt.ylabel(Title + " (kWh)")
    plt.legend()
    plt.grid()
    plt.show()