#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 16:15:53 2025

@author: theophilemounier
"""

import json 
import os 
from prices import treat_data, increase_deltat
from representative_days import separate_days
from prices_porto_motor import TE_pm_2024, TP_pm_2024
import matplotlib.pyplot as plt
import datetime as dt


#%% utility function

def recov_time(obj0, res, bat_price, Cb) : 
    """
    Compute recovery time

    Parameters
    ----------
    obj0 : float
        Objective value results for Cb=0.
    res : float
        Objective value results minus battery price.
    bat_price : float
        batterie price per kWh.
    Cb : float
        battery capacity.

    Returns
    -------
    float
        Recovery time.

    """
    cash_flow = obj0 - res
    invest = bat_price*Cb 
    return (invest/cash_flow)
    
def ploat_recov_vs_price() : 
#%%

path_results_bat_price = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_bat_price_Tub.json')
with open(path_results_bat_price) as f: 
    Res = json.load(f)
    
    
Cb_prices = [val for val in Res]
sorted(Cb_prices)
objs = [Res[val]['obj'] for val in Cb_prices]
ress = [Res[val]['res'] for val in Cb_prices]
Cbs = [Res[val]['Cb'] for val in Cb_prices]
Pcs = [Res[val]['Pc'] for val in Cb_prices]
Pds = [Res[val]['Pd'] for val in Cb_prices]
Ebat = [Res[val]['Ebat'] for val in Cb_prices]
# for k in range(len(Cb_prices)) :
for k in range(1) :
    Pc = Pcs[k]
    Pd = Pcs[k]
    for t in range(len(Pc[:100])) : 
        print('t, Ebat[-1], Ebat[+1], Pc, Pd', t, Ebat[k][-1], Ebat[k][-1] + (0.95*Pc[t] - Pd[t]/0.95)*4, Pc[t], Pd[t])
        Ebat[k].append(Ebat[k][-1] + (0.95*Pc[t] - Pd[t]/0.95)*4)

#%% 

pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
Eautocons, Econs, full_time, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
deltat = deltat[0]
Eprod, Econs, full_date, deltat = increase_deltat(3, Eautocons, Econs, full_time, deltat)

#%%
Eprod, Econs, full_date, deltat = treat_data()

#%%

nb_hours=72
delta = dt.timedelta(hours=nb_hours) - dt.timedelta(minutes=1)
Days = separate_days(Econs, Eprod, full_date, TE=TE_pm_2024, bat=Ebat[0], delta=delta)
mean_Econs = [0 for k in range(len(Days[0]['Econs']))]
mean_Eprod = [0 for k in range(len(Days[0]['Eprod']))]
mean_Ebat = [0 for k in range(len(Days[0]['Ebat']))]
nb_val = [0 for k in range(len(Days[0]['Econs']))]
for i in range(len(Days)) : 
    for t in range(len(Days[i]['Econs'])) : 
        # print(i, len(Days[i]['Econs']))
        # print(t, len(mean_Econs))
        mean_Econs[t] += Days[i]['Econs'][t]
        mean_Eprod[t] += Days[i]['Eprod'][t]
        mean_Ebat[t] += Days[i]['Ebat'][t]
        nb_val[t] += 1
for t in range(len(Days[0]['Econs'])) :
    print(t)
    mean_Econs[t] /= nb_val[t]
    mean_Eprod[t] /= nb_val[t]
    mean_Ebat[t] /= nb_val[t]
    
    
fig, ax = plt.subplots()
t = list(range(len(mean_Econs)))
t = [val*nb_hours/len(mean_Econs) for val in t]
# mean_Econs = [val/(24/len(mean_Econs)) for val in mean_Econs]
# mean_Eprod = [val/(24/len(mean_Eprod)) for val in mean_Eprod]
# mean_Ebat = [val/(24/len(mean_Ebat)) for val in mean_Ebat]
ax.plot(t, mean_Eprod, label='Mean Production')
ax.plot(t, mean_Econs, label='Mean Consumption')
ax.plot(t, mean_Ebat, label='Mean battery')
ax.plot(t, [0.2*Cbs[0] for val in t], '--', color="black")
ax.plot(t, [Cbs[0] for val in t], '--', color="black")
ax.legend()

#%% Recovery time depending on the price 

