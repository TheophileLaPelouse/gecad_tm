"""
Caracterisation of the prosumers and the prosumer groups

The goal here is to produce a container with for each prosumer the following dictionnary:
{
    TE : f(t) function that computes the energy cost depending on t a value between 0 and 29I09UI4309U corresponding to the time interval studied
    TP : f(p) function that computes the power cost depending on the period p 
    Time_ref : [(p, m), ...] Time_ref[t] = (p, m) where p is the period and m the month for time t
    TPena : f(p, m, pgrid, pcont) function that computes the penalisation cost depending on the period, the month and the list of pgrid (only the penalizated affected one) and pcontracted
    load : equivalent to Econs before
    prod : equivalent to Eprod (or Eautocons) before
    dist : [dist1, dist2, ..., distn] the distances to the other prosumers for computing the loss
    bat_parameters : [eff_ch, eff_dch, soc_min, soc_max, soc_init, rate_ch, rate_dch] the battery parameters
    (maybe) V : voltage
    (maybe) constraints : Other constraints defined in a str ?
    
}

We will also need a function
Loss(dist1, dist2, power, (maybe) voltage) that computes the loss depending on the distance and the power (and maybe voltage)

"""

from prices_tubacer import TE, TE_new, TP, TP_new
from prices_porto_motor import TE_pm_2024, TP_pm_2024
from prices_TMG import TE_TMG, TP_TMG
from prices import treat_data, define_time, define_time2
from opti import build_model, calculate_price, period_hours
import datetime as dt
import calendar as cal
from pyomo.opt import SolverFactory
import os
import pandas as pd

def compute_energy_price(TE, t, Time_ref) : 
    p, m = Time_ref[t]
    return TE[m][p]

def compute_power_price(TP, p) : 
    return TP[p]

def compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref) : 
    s = 0.0000000001
    Time, Nbdays, Time_in_month = define_time2(timeframe, period_hours)
    for t in range(len(Time_ref)) :
        p, m = Time_ref[t] 
        if p == period and m == month : 
            s += (pgrid[t] - pcont[p]) ** 2
    return Kp[period]*tep*s**0.5

def full_date_treatment(full_date, deltat) :
    Time, Nbdays, Time_in_month = define_time2(full_date, deltat)
    Time_ref = [None for k in range(len(full_date))]
    for p in Time_ref : 
        for t in Time[p] :
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            Time_ref[t] = (p, m)
            
    return Time_ref
        
def make_dico_tub(nb_prosumers=4) :
    Eprod, Econs, full_date, deltat = treat_data(name="TUBACER")
    Time_ref = full_date_treatment(full_date, deltat)
    dists = [0 for k in range(nb_prosumers-1)]
    bat_parameters = [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5]
    
    dico = {
        "TE" : lambda t: compute_energy_price(TE, t, Time_ref),
        "TP" : lambda p: compute_power_price(TP, p),
        "TPena" : lambda period, month, pgrid, pcont: compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref),
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eprod,
        "dist" : dists,
        "bat_parameters" : bat_parameters,
    }
    
    return dico
    
def make_dico_PM(nb_prosumers=4) :
    pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
    Time_ref = full_date_treatment(full_time, deltat[0])
    
    dico = {
        "TE" : lambda t: compute_energy_price(TE_pm_2024, t, Time_ref),
        "TP" : lambda p: compute_power_price(TP_pm_2024, p),
        "TPena" : lambda period, month, pgrid, pcont: compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref),
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eautocons,
        "dist" : [0 for k in range(nb_prosumers-1)],
        "bat_parameters" : [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5],
    }
    return dico 

def make_dico_TMG(nb_prosumers=4) :
    tmg_path = os.path.join(os.path.dirname(__file__), 'Datasets', '4_TMG', 'Curvas_TMG_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=tmg_path, prod_col=-1, cons_col='Consumo kWh', 
                                                 date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
                                                 one_time_col=False, sheet_name=0)
    deltat = deltat[0]
    Time_ref = full_date_treatment(full_time, deltat)
    dico = {
        "TE" : lambda t: compute_energy_price(TE_TMG, t, Time_ref),
        "TP" : lambda p: compute_power_price(TP_TMG, p),
        "TPena" : lambda period, month, pgrid, pcont: compute_penalization_price(period, month, tep, Kp, pgrid, pcont, Time_ref),
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eautocons,
        "dist" : [0 for k in range(nb_prosumers-1)],
        "bat_parameters" : [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5],
    }
    
    return dico

def make_dico_Nar(nb_prosumers=4) : 
    na2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '3_NARONTEC', 'Curvas_carga_Narontec_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=na2024_path, prod_col=-1, cons_col='Consumo kWh', 
                                                 date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
                                                 one_time_col=False, sheet_name=0)
    deltat = deltat[0]
    Time_ref = full_date_treatment(full_time, deltat)
    dico = {
        "TE" : lambda t: compute_energy_price(TE_Nar, t, Time_ref),
        "TP" : lambda p: 0,
        "TPena" : lambda period, month, pgrid, pcont: 0,
        "Time_ref" : Time_ref,
        "load" : Econs,
        "prod" : Eautocons,
        "dist" : [0 for k in range(nb_prosumers-1)],
        "bat_parameters" : [0.95, 0.95, 0.2, 1, 0.5, 0.5, 0.5],
    }
    
    
    
def make_dico() : 
    
    Prosumers = {
        "TUBACER" : make_dico_tub(),
        "Porto_Motor" : make_dico_PM(),
        "TMG" : make_dico_TMG()
    }
    n_min = None
    for key in Prosumers : 
        if n_min is None : 
            n_min = len(Prosumers[key]["load"])
        if len(Prosumers[key]["load"]) < n_min : 
            n_min = len(Prosumers[key]["load"])
    
    for key in Prosumers :
        Prosumers[key]["load"] = Prosumers[key]["load"][:n_min]
        Prosumers[key]["prod"] = Prosumers[key]["prod"][:n_min]
        Prosumers[key]["Time_ref"] = Prosumers[key]["Time_ref"][:n_min]
        
    return Prosumers
    
#%%
Prosumers = make_dico()    
# What we need to verify is if the time for the values corresponds, mainly because of the change in hour.

    