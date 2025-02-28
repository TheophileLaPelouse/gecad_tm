#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 11:42:45 2025

@author: theophilemounier
"""

import pandas as pd 

# df = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Curvas_carga_portomotor_2024.xlsx")

# # df2 = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Narontec_2024_hourly.xlsx")

# df_ori = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/dados_espanha_xlsx.xlsx")

# df_pm = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Datasets/2_PORTOMOTOR/Porto Motor_2024.xlsx", sheet_name=None)

df_na3 = pd.read_excel("Datasets/3_NARONTEC/Narontec_2023_hourly.xlsx", decimal=',', skiprows=[1])

df_na4 = pd.read_excel("Datasets/3_NARONTEC/Narontec_2024_hourly.xlsx", decimal=',')

df_na2 = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Datasets/3_NARONTEC/Curvas_carga_Narontec_2024.xlsx", decimal=',')