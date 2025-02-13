#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 10:47:46 2025

@author: theophilemounier
"""

# Model init_model(double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, double discharge_rate, double **TE, double *TP, int indexPprev[2], int Nbdays, double Kp, double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, size_t n_tot_time, size_t *time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) {
#     Model model;
#     model.Econs = Econs;
#     model.Eprod = Eprod;
#     memcpy(model.indexPb, indexPb, 2 * sizeof(int));
#     model.deltat = deltat;
#     model.charge_rate = charge_rate;
#     model.discharge_rate = discharge_rate;
#     model.TE = TE;
#     model.TP = TP;
#     memcpy(model.indexPprev, indexPprev, 2 * sizeof(int));
#     model.Nbdays = Nbdays;
#     model.Kp = Kp;
#     model.tep = tep;
#     model.indexCb = indexCb;
#     model.TB = TB;
#     model.batterie_life = batterie_life;
#     model.TBm = TBm;
#     model.SOC = SOC;
#     model.tot_time = tot_time;
#     model.n_tot_time = n_tot_time;
#     model.time = time;
#     model.time_month = time_month;
#     model.n_time_month = n_time_month;
#     model.months = months;
#     model.n_m = n_m;
#     model.periods = periods;
#     model.n_p = n_p;
#     return model;
# }
import ctypes

lib = ctypes.CDLL('./libmodel.so')
lib.init_model.argtypes = [ctypes.POINTER(ctypes.c_double), 
                            ctypes.POINTER(ctypes.c_double),
                            ctypes.POINTER(ctypes.c_int),
                            ctypes.c_double,
                            ctypes.c_double,
                            ctypes.c_double,
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_double)),
                            ctypes.POINTER(ctypes.c_double),
                            ctypes.POINTER(ctypes.c_int),
                            ctypes.c_int,
                            ctypes.c_double,
                            ctypes.c_double,
                            ctypes.c_int,
                            ctypes.c_double,
                            ctypes.c_double,
                            ctypes.POINTER(ctypes.c_double),
                            ctypes.POINTER(ctypes.c_size_t),
                            ctypes.POINTER(ctypes.c_size_t),
                            ctypes.POINTER(ctypes.c_size_t),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)),
                            ctypes.POINTER(ctypes.c_int),
                            ctypes.c_int,
                            ctypes.POINTER(ctypes.c_int),
                            ctypes.c_int]

from prices import define_time, Econs, Eautocons, TEauto, tep, Kp, period_hours, full_date, define_time2
import datetime as dt 
import numpy as np

TP = [0.066889, 0.040255, 0.031037, 0.025345, 0.004733, 0.002652]
TE = [
      [0.176631, 0.170670, 0, 0, 0, 0.125919], 
      [0.126656, 0.131860, 0, 0, 0, 0.092685], 
      [0, 0.126656, 0.131860, 0, 0, 0.073864], # March is not in the invoices so the figures are based on february
      [0, 0, 0, 0.066662, 0.079025, 0.073864], 
      [0, 0, 0, 0.079119, 0.094265, 0.097955], 
      [0, 0, 0.124591, 0.143611, 0, 0.138129], 
      [0.150950, 0.179345, 0, 0, 0, 0.148744], 
      [0, 0, 0.165865, 0.181045, 0, 0.169511], 
      [0, 0, 0.145440, 0.167703, 0, 0.150691], 
      [0, 0, 0, 0.137424, 0.169721, 0.133218], 
      [0, 0.195679, 0.210640, 0, 0, 0.172424]
      ]

timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 4, 0, 59))


Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
Nbdays += 1
Econs = Econs[timerange[0]:timerange[1]+1]
Eautocons = Eautocons[timerange[0]:timerange[1]+1]
Pb = np.zeros(len(Econs))
Cb = 0
Pprev = np.zeros(6)
Var_size = len(Pb) + 1 + len(Pprev)
indexPb = [0, len(Pb)]
indexCb = len(Pb)
indexPprev = [indexCb+1, indexCb+1+len(Pprev)]
deltat = 0.25
tot_time = range(timerange[1]-timerange[0]+1)  
for p in range(6) : 
    for k in range(len(Time[p])) :
        Time[p][k] -= timerange[0]
        
for month in range(12) : 
    new = set()
    while Time_in_month[month] : 
        val = Time_in_month[month].pop()
        val -= timerange[0]
        new.add(val)
    Time_in_month[month] = new.copy()    
    
time_month = [[[t for t in Time[p] if t in Time_in_month[month]] for p in range(6)] for month in range(12)]
n_time_month = [[len(time_month[month][p]) for p in range(6)] for month in range(12)]
        
charge_rate = 0.5 
discharge_rate = 0.5
Effc = 0.95 # Efficiency, we count the conversion losses, do we need to lessen the losses if come from PV ? Maybe
Effd = 0.95 # order of magnitude, need to be looked into.

TB = 359
TBm = 0.019
batterie_life = 10
months = range(1, 13)
periods = range(6)

Eprod = Eautocons
SOC = [0 for k in range(len(Econs))]
n_tot_time = len(tot_time)
time = Time
n_m = 12
n_p = 6


model = lib.init_model(Econs, Eprod, indexPb, deltat, charge_rate, discharge_rate, TE, TP, indexPprev, Nbdays, Kp, tep, indexCb, TB, batterie_life, TBm, SOC, tot_time, n_tot_time, time, time_month, n_time_month, months, n_m, periods,n_p)
                        
