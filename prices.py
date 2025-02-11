#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 13 11:37:06 2025

@author: theophilemounier
"""

"""
Kp : Rapport de prix par période horaire p, 
calculé comme le quotient entre le terme de puissance de la période p par 
rapport au terme de puissance de la période 1 du péage correspondant.
In english : Kp: Price ratio per hourly period p, calculated as the quotient between the power term of period p with respect to the power term of period 1 of the corresponding toll.

All the values defined in the spanish law are in the file prix2024.csv

We are using the regulation 6.1 

In case you don't know, "#%%" is used to define cells like in a notebook that can be run independently.

"""

import pandas as pd 
import matplotlib.pyplot as plt

#%% Defining DF a dictionnary of dataframes with values from prix2024.csv
year = '2024'
prix = "prix"+year+".csv"
with open(prix) as f : 
    lines = f.readlines()
    
d_lines = {}
deb = 0
fin = 0
current_name = ''
for line in lines : 
    if line.startswith('---'):
        if deb < fin : 
            d_lines[current_name] = (deb, fin)
        deb = fin + 1
        fin += 1
        current_name = line[3:].strip()
    else : 
        fin += 1
        
if deb < fin : 
    d_lines[current_name] = (deb, fin)
            
nb_lines = len(lines)
        
DF = {}

for key in d_lines :
    to_skip = list(range(d_lines[key][0])) + list(range(d_lines[key][1], nb_lines))
    DF[key] = pd.read_csv(prix, skiprows=to_skip, sep=' ', index_col=0)

#%%read excel

df = pd.read_excel('dados_espanha_xlsx.xlsx', sheet_name='All')

#%% Function to calculate the price
    
def calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays) :
    """calculate the electricity price

    Args:
        Pprev (list): List of the power contracted for each period
        Pcons (list): List of actual power used during each quarter
        Econs (list): List of energy load during each quarter
        Eautocons (list): List of energy produced during each quarter
        TP (list): List of the prices for the power of each period
        TE (list): List of the prices for the energy from the grid of each period
        TEauto (list): List of the prices for the energy produced locally
        Time (list of list): List of the index of the quarters in each period
        tep (float): Price for the penalties
        Kp (list): List of the Kp for each period
        Nbdays (list): Number of days of the considered timeframe
    """
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    Spena_P = [0 for k in range(6)]
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays
        for t in Time[p] : 
            Se += TE[p]*(Econs[t]-Eautocons[t])
            Se_p[p] += TE[p]*(Econs[t]-Eautocons[t])
            Seauto += TEauto[p]*Eautocons[t]
            if Pcons[t] > Pprev[p] : 
                if p == 5 :
                    print(Pcons[t], Pprev[p], t, p)
                Spena_P[p] += (Pcons[t] - Pprev[p])**2  
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
        
    return({'Total' : Se + Seauto + Spena + Sp,
            'Energy from grid' : Se, 
            'Energy auto-consume' : Seauto, 
            'Power' : Sp, 
            'Penalisation' : Spena, 
            'details' : 
                {'Energy from grid' : {'P%d' % (k+1) : Se_p[k] for k in range(6)}, 
                 'Penalisation' : {'P%d' % (k+1) : Spena_P[k] for k in range(6)}}
            })
# Maybe I should do this function in C or CPython to go faster in the pyomo optmization
        
#%% data

def series2lists(s, type_ = float, factor = 1) :
    L = []
    for val in s : 
        if type_ == float : 
            if isinstance(val, str) : 
                val = val.replace(',', '.')
            L.append(float(val)*factor)
        else : 
            L.append(val)
        
    return L

Pprev = [120, 130, 130, 130, 130, 195]
Econs = series2lists(df['TUBACER KWh'])
Eautocons = series2lists(df['TUBACER PV'])
step = 0.25 # 15 minutes
Pcons = series2lists(df['TUBACER KWh']-df['TUBACER PV'], factor = 1/step)
TP = series2lists(DF['P'].loc[6.1], factor = 1/365) # For TE and TP we also will calculate using the prices from the invoice 
TE = series2lists(DF['E'].loc[6.1])
TEauto = series2lists(DF['Eauto'].loc['NT2']) # Maybe this should not be taken into account (it represents in total only 6€)
tep = series2lists(DF['penaltie'].loc[6.1])[0]
Kp = series2lists(DF['Kp'].loc[6.1])

Date = df['DATE'].dropna()
index = Date.index
full_date = []
for k in index : 
    full_date.append(pd.Timestamp.combine(df['DATE'][k].date(), df['TIME'][k]))

#%% Agenda 
import datetime as dt
import xml.etree.ElementTree as ET
cal = ET.parse('stop_working2024.xml') # XML that contains the none working days in Spain (official document)
root = cal.getroot()
texto_elements = root.findall('.//texto')
month_list = {'Enero' : 1, 'Febrero' : 2, 'Marzo' : 3, 'Abril' : 4, 'Mayo' : 5, 'Junio' : 6, 'Julio' : 7, 'Agosto' : 8, 'Septiembre' : 9, 'Octubre' : 10, 'Noviembre' : 11, 'Diciembre' : 12}
current_month = 0
None_working_days = []
if texto_elements : 
    cal_text = texto_elements[-1]
    p_elements = cal_text.findall('.//p')
    flag_cal = False
    k = 0 
    n = len(p_elements)
    while k < n : 
        p = p_elements[k].text 
        if p.startswith('Calendario') : 
            flag_cal = True
        
        if flag_cal :
            date = p.split(':')[0].strip()
            if date in month_list : 
                current_month = month_list[date]    
            elif date.startswith('Día') : 
                date = int(date.split()[1])
                None_working_days.append(dt.datetime(int(year), current_month, date))
        k += 1
    
period_hours = [[[(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [], [], [(0, 8)]], 
              [[(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [], [], [(0, 8)]],
              [[], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [], [(0, 8)]],
              [[], [], [], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [(0, 8)]],
              [[], [], [], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [(0, 8)]],
              [[], [], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [(0, 8)]],
              [[(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [], [], [(0, 8)]],
              [[], [], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [(0, 8)]],
              [[], [], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [(0, 8)]],
              [[], [], [], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [(0, 8)]],
              [[], [(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [], [(0, 8)]],
              [[(9, 14), (18, 22)], [(8, 9), (14, 18), (22, 24)], [], [], [], [(0, 8)]]
              ]
"""
period_hours is built as such :
period_hours[number of the month (1 to 12) - 1][number of the period (0 to 5)] is a list of the time interval for the corresponding period.
"""


def in_period(l, val) : 
    flag = False 
    for tup in l : 
        if val >= tup[0] and val < tup[1] : 
            flag = True
            break 
    return flag

# Building the table Time looking at the period
# As we had a dataframe at the first, and as we never changed the index, the index of the table for the date correspond to the one in the others table 
# such as the table for the energy and for the power.
timeframe = (dt.datetime(2024, 8, 31, 23, 59), dt.datetime(2024, 9, 30, 23, 59))

def define_time(timeframe, period_hours, full_date = full_date) : 
    Time = [[] for k in range(6)]
    Time_in_month = [set() for k in range(12)]
    P = 0
    for k in range(len(full_date)) : 
        date = full_date[k]    
        if date >= timeframe[0] and date <= timeframe[1] : 
            if date.weekday() >= 5 or date in None_working_days : 
                P = 5
            else : 
                month = date.month
                time = date.hour + date.minute/60
                j = 0
                while not period_hours[month-1][j] or not in_period(period_hours[month-1][j], time) : 
                    j += 1
                P = j
            Time[P].append(k)
            Time_in_month[date.month - 1].add(k)
    delta = timeframe[1] - timeframe[0]
    Nbdays = delta.days
    return Time, Nbdays, Time_in_month

Time, Nbdays, _ = define_time(timeframe, period_hours)

        
#%% Compute    

# Using the cost from the official documents (prix2024.csv) but there are probably not the paid prices (they are way lower than the prices in the invoice)
# result1 = calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays)


# Using values from the invoice 
# TP = [0.066889, 0.040255, 0.031037, 0.025345, 0.004733, 0.002652]
# TE = [0, 0, 0.145440, 0.167703, 0, 0.150691] # The 0 values are none important as the periods does not exist during the month of september.
# result2 = calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays)

# Power : OK
# Penalties : A bit on P6 => 6€ too much and not the same repartition between P3 and P4
# Energy : 3 300 instead of 2 700 -> on the excel there is a total of 22 000kWh used as it is only 18 000 on the invoice.

# Just to see the total of energy in each period.
# TE = [1, 1, 1, 1, 1, 1]
# result3 = calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays)

#%% utils

def last_day(any_day):
    next_month = any_day.replace(day=28) + dt.timedelta(days=4)
    if any_day.month == 11 :
        return dt.datetime(2024, 11, 20, 23, 59)
    return (next_month - dt.timedelta(days=next_month.day)).replace(hour=23, minute = 59)

def search_dico(l, val, deb_or_fin = 'deb') : 
    deb = 0
    fin = len(l) - 1
    while fin - deb > 1 : 
        mid = (deb + fin)//2
        if l[mid] == val : 
            return mid 
        elif l[mid] > val : 
            fin = mid
        else : 
            deb = mid
    # If we want to stop the fist inferior or equal values we put 'deb' otherwise we put 'fin' (superior or equal)
    if deb_or_fin == 'deb' : 
        return deb
    else :
        return fin
    
    
def define_time2(days, period_hours) : 
    Time = [[] for k in range(6)]
    Time_in_month = [set() for k in range(12)]
    P = 0
    days.sort(key = lambda x : x.month)
    n = len(days)
    c = 1
    previous_date = days[0].date()
    for k in range(n) : 
        date = days[k]
        if date.date() != previous_date : 
            c += 1
            previous_date = date.date()
        if date.weekday() >= 5 or date in None_working_days : 
            P = 5
        else :
            month = date.month
            time = date.hour + date.minute/60
            j = 0
            while not period_hours[month-1][j] or not in_period(period_hours[month-1][j], time) : 
                j += 1
            P = j
        Time[P].append(k)
        Time_in_month[date.month - 1].add(k)
    Nbdays = c
    return Time, Nbdays, Time_in_month