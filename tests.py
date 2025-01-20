#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 10:47:46 2025

@author: theophilemounier
"""

import pandas as pd 
import datetime as dt

df_csv = pd.read_csv('Raw dataset/2_INV_INYECCION0/09_September.csv', sep=';', decimal= ',')

df_excel = pd.read_excel('Raw dataset/Tubacer instalation 2.xlsx', decimal=',')

df_treated = pd.read_excel('dados_espanha_xlsx.xlsx', sheet_name='All')

#%%


timeframe = (dt.datetime(2024, 8, 31, 23, 59), dt.datetime(2024, 9, 29, 23, 59))

aug_excel = df_excel.loc[(df_excel['Date'] > timeframe[0]) & (df_excel['Date'] < timeframe[1])]

aug_treated = df_treated.loc[(df_treated['DATE'] > timeframe[0]) & (df_treated['DATE'] < timeframe[1])]

#%%

sum_pv1 = df_csv['Einv_tot'].sum()
sum_pv2 = aug_excel['Energía Total PV (kWh)'].sum()
sum_pv_treated = aug_treated['TUBACER PV'].sum()

sum_plant = df_csv['EcRST'].sum()
sum_network = df_csv['EpRST'].sum()
sum_plant_treated = aug_treated['TUBACER KWh'].sum()

print('plant', sum_plant, 'plant treated', sum_plant_treated, 'network', sum_network, 'pv1', sum_pv1, 'pv2', sum_pv2, 'PV treated', sum_pv_treated)
print('plant - network', sum_plant - sum_network)
print()
print('plant - 2 installations', sum_plant - sum_pv1 - sum_pv2) # I think we forgot the second installation
print('plant - 1 installations', sum_plant - sum_pv1)
print('plant_treated - PV treated', sum_plant_treated - sum_pv_treated)
# -> but that does not explain why 

#%%

columns = df_csv.columns

for col in columns : 
    if df_csv[col].dtype == 'float64':
        print(col, df_csv[col].sum())
        
#%% Recreate good data

import os

def time_dif(t1, t2) : 
    return (int(t2.split(':')[1]) - int(t1.split(':')[1])) % 60

new_data = 'new_data.csv'
recap = 'monthly_recap.csv'

csv_folder = 'Raw dataset/2_INV_INYECCION0'
csvs = {}

for file in os.listdir(csv_folder):
    if file.endswith('csv') : 
        try : 
            month = int(file.split('_')[0])
            csvs[month] = os.path.join(csv_folder, file)
        except :
            pass

new_df = pd.DataFrame(columns=['date', 'Ec', 'Epv', 'Ec-Epv'])
recap_df = pd.DataFrame(columns=['Month', 'Ec', 'Epv', 'Ec-Epv'])

def combine_data(month, csv_file, df_excel, new_df) : 
    if month > 1 : 
        timeframe = (dt.datetime(2024, month-1, 31, 23, 59), dt.datetime(2024, month, 30, 23, 59))
    elif month == 1 : 
        timeframe = (dt.datetime(2023, 12, 31, 23, 59), dt.datetime(2024, 1, 30, 23, 59))
    month_excel = df_excel.loc[(df_excel['Date'] > timeframe[0]) & (df_excel['Date'] < timeframe[1])]
    csv = pd.read_csv(csvs[month], sep=';', decimal= ',')
    
    Ecs_csv = []
    Epvs_csv = []
    Ecs_excel = []
    Epvs_excel = []
    # We will have 15 minutes sample, in the csv we have 10 minutes sample, in the excel we have 5 or 15.
    # For the csv we will take 3 sample, and cut the one in the middle in two
    for k in csv.index :  
        if k % 3 == 0 : 
            Ecs_csv.append(csv['EcRST'][k])
            Epvs_csv.append(csv['Einv_tot'][k])
        elif k % 3 == 1 : 
            Ecs_csv[-1] += csv['EcRST'][k]/2
            Epvs_csv[-1] += csv['Einv_tot'][k]/2
            Ecs_csv.append(csv['EcRST'][k]/2)
            Epvs_csv.append(csv['Einv_tot'][k]/2)
        elif k % 3 == 2 : 
            Ecs_csv[-1] += csv['EcRST'][k]
            Epvs_csv[-1] += csv['Einv_tot'][k]
    
    # for k in month_excel.index :
    #     if 
    
    
        