#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 11:42:45 2025

@author: theophilemounier
"""

import pandas as pd 

df = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Curvas_carga_portomotor_2024.xlsx")

# df2 = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Narontec_2024_hourly.xlsx")

df_ori = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/dados_espanha_xlsx.xlsx")

df_pm = pd.read_excel("/Users/theophilemounier/Desktop/github/gecad_tm/Datasets/2_PORTOMOTOR/Porto Motor_2024.xlsx", sheet_name=None)
