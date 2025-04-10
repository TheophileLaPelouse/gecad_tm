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
import numpy as np


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
    print(obj0, res, bat_price, Cb)
    return (invest/cash_flow)
    
def plot_recov_vs_price(Res) : 
    Cb_prices = [val for val in Res]
    sorted(Cb_prices)
    print(Cb_prices)
    ress = [Res[val]['res'] for val in Cb_prices]
    Cbs = [Res[val]['Cb'] for val in Cb_prices]
    objs = [Res[val]['obj'] for val in Cb_prices]
    if Cbs[-1] > 0.1 : 
        print("Nope we need a 0 reference for the battery")
        return
    recov_times = [recov_time(objs[-1], ress[k], int(float(Cb_prices[k])), Cbs[k]) for k in range(len(Cb_prices))]
    to_plot = [[], []]
    Cb = Cbs[0]
    k = 0
    while Cb > 1 : 
        to_plot[0].append(int(float(Cb_prices[k])))
        to_plot[1].append(recov_times[k])
        k += 1
        Cb = Cbs[k]
    fig, ax = plt.subplots()
    ax.plot(to_plot[0], to_plot[1], '+', markersize=20)
    list_annote = [0, 4, 8, 13]
    for k in range(len(Cbs)) :
        if k in list_annote:
            x, y = to_plot[0][k], to_plot[1][k] 
            print(x, y)
            ax.annotate(f'$Cb = {round(Cbs[k], 2)}$', xy=(x,y))
    ax.set_xlabel('Battery installation price (€/kWh)')
    ax.set_ylabel('Recovery time (years)')
    ax.set_xlim(140, 320)
    # ax.set_title('Recovery time depending on the battery price')
    fig.subplots_adjust(bottom=0.13)
    plt.show()
    return fig
    
def plot_Cb_vs_price(Res, markersize=20) : 
    Cb_prices = [val for val in Res]
    sorted(Cb_prices)
    print(Cb_prices)
    ress = [Res[val]['res'] for val in Cb_prices]
    Cbs = [Res[val]['Cb'] for val in Cb_prices]
    objs = [Res[val]['obj'] for val in Cb_prices]
    Cb_prices = [int(float(val)) for val in Cb_prices]
    fig, ax = plt.subplots()
    ax.plot(Cb_prices, Cbs, '+', markersize=markersize)
    ax.set_xlabel('Battery installation price (€/kWh)')
    ax.set_ylabel('Battery capacity (kWh)')
    fig.subplots_adjust(bottom=0.13)
    # ax.set_title('Battery capacity depending on the battery price')
    plt.show()
    return fig
    
def plot_obj_vs_price(Res) : 
    Cb_prices = [val for val in Res]
    sorted(Cb_prices)
    print(Cb_prices)
    ress = [Res[val]['res'] for val in Cb_prices]
    Cbs = [Res[val]['Cb'] for val in Cb_prices]
    objs = [Res[val]['obj'] for val in Cb_prices]
    Cb_prices = [int(float(val)) for val in Cb_prices]
    fig, ax = plt.subplots()
    ax.plot(Cb_prices, objs)
    ax.set_xlabel('Battery price')
    ax.set_ylabel('Objective value')
    # ax.set_title('Objective value depending on the battery price')
    plt.show()
    return fig
    
def plot_decrease_vs_price(Res, markersize=20) : 
    Cb_prices = [val for val in Res]
    sorted(Cb_prices)
    print(Cb_prices)
    ress = [Res[val]['res'] for val in Cb_prices]
    Cbs = [Res[val]['Cb'] for val in Cb_prices]
    objs = [Res[val]['obj'] for val in Cb_prices]
    Cb_prices = [int(float(val)) for val in Cb_prices]
    if Cbs[-1] > 0.1 : 
        print("Nope we need a 0 reference for the battery")
        return
    dcrs = [(objs[-1]-obj)/objs[-1]*100 for obj in objs]
    fig, ax = plt.subplots()
    ax.plot(Cb_prices, dcrs, '+', markersize=markersize)
    list_annote = [0, 5, 10, 18]
    for k in range(len(Cbs)) :
        if k in list_annote:
            x, y = Cb_prices[k], dcrs[k] 
            print(x, y)
            ax.annotate(f'$Cb = {round(Cbs[k], 2)}$', xy=(x,y))
    ax.set_xlabel('Battery installation price (€/kWh)')
    ax.set_ylabel('Decrease of annual cost (%)')
    ax.set_xlim(130, 380)
    ax.set_ylim(-0.3, 6.5)
    fig.subplots_adjust(bottom=0.13)
    # ax.set_title('Objective value depending on the battery price')
    plt.show()
    return fig

def pena_charge_and_discharge(Pc, Pd, time=None, coef=1) : 
    if coef == 'tot' : 
        return 0
    if Pd is None :
        return coef*sum(p for p in Pc)
    else : 
        if time is None :
            return coef*sum(Pc[t]*Pd[t] for t in range(len(Pc)))
        else : 
            return coef*sum(Pc[t]*Pd[t] for t in time)
    
#%%

path_results_bat_price = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_bat_price_Tub.json')
with open(path_results_bat_price) as f: 
    Res = json.load(f)
    
path_results_bat_price = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_bat_price_pm.json')
with open(path_results_bat_price) as f: 
    Res_pm = json.load(f)

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

ratios = []
for k in range(len(Cbs)) : 
    pena = pena_charge_and_discharge(Pcs[k], Pds[k])
    ratio = pena/objs[k]
    ratios.append(ratio)

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

#%% plot time results

path_time = 'Results/csv/time.json'
with open(path_time) as f : 
    time_results = json.load(f)
n = len(time_results)
deltas = [1+k*0.5 for k in range(n)]

# On vérifie si on a une tendance polynomiale
p = np.polyfit(range(n), time_results, 2)
f = lambda x : p[0]*x**2 + p[1]*x + p[2]

fig, ax = plt.subplots()
ax.plot(deltas, time_results, '+', label="Model optimization time results", markersize=15)
plt.plot(deltas, [f(k) for k in range(n)], '--',linewidth=3 ,label=f"$y={round(p[0], 2)}x^2 + {round(p[1], 2)}x + {round(p[0], 2)}$")
ax.set_xlabel("Number of days")
ax.set_ylabel("Time taken to solve (seconds)")
ax.legend()

#%% (example that does not work for now bug so not the right values)

path_250_tub = 'Results/csv/250_tub.json'
with open(path_250_tub) as f : 
    d = json.load(f)
Cbs_bis = [val for val in d]
sorted(Cbs_bis)
plt.rcParams['font.size'] = 25
fig, ax = plt.subplots()
ax.plot(Cbs_bis, [d[Cb] for Cb in Cbs_bis], '+', markersize=30)
ax.plot(Res['250']['Cb'], Res['250']['obj'], '.')
ax.set_xlabel('Battery size (kwh)')
ax.set_ylabel('Optimal objective function value')

#%% proof that it works

price_250 = '250'
path_results_bat_proof_250 = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_diff_bat_pm.json')
with open(path_results_bat_proof_250) as f: 
    Res2_pm_250 = json.load(f)

Cbs_250 = []
for val in Res2_pm_250: 
    if val != 'original': 
        Cbs_250.append(val)

Cbs_to_plot_250 = [float(val) for val in Cbs_250]

# Load results for price = 150
price_150 = '150'
path_results_bat_proof_150 = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'results_diff_bat_pm_150.json')
with open(path_results_bat_proof_150) as f: 
    Res2_pm_150 = json.load(f)

Cbs_150 = []
for val in Res2_pm_150: 
    if val != 'original': 
        Cbs_150.append(val)

Cbs_to_plot_150 = [float(val) for val in Cbs_150]

font_size = 30
marker_size = 20
# Create the subplots

fig, ax1 = plt.subplots()
ax1.plot(Cbs_to_plot_250, [Res2_pm_250[cb] for cb in Cbs_250], '+', markersize=marker_size)
ax1.plot(Res[price_250]['Cb'], Res[price_250]['obj'], 'o', label='Optimization result', markersize=marker_size)
ax1.set_title('$InvestCost = 250€/kWh$', fontsize=font_size)
ax1.set_xlabel('Battery size (kWh)', fontsize=font_size)
ax1.set_ylabel('Objective function value', fontsize=font_size)
ax1.legend(fontsize=font_size, loc='upper center')
fig.subplots_adjust(bottom=0.13)
# plt.tight_layout()
plt.show()

# Create the second figure for price = 150
fig2, ax2 = plt.subplots()
ax2.plot(Cbs_to_plot_150, [Res2_pm_150[cb] for cb in Cbs_150], 'x', markersize=marker_size)
ax2.plot(Res[price_150]['Cb'], Res[price_150]['obj'], 'o', label='Optimization result', markersize=marker_size)
ax2.set_title('$InvestCost = 150€/kWh$', fontsize=font_size)
ax2.set_xlabel('Battery size (kWh)', fontsize=font_size)
ax2.set_ylabel('Objective function value', fontsize=font_size)
ax2.legend(fontsize=font_size, loc='upper center')
fig2.subplots_adjust(bottom=0.13)
# plt.tight_layout()
plt.show()