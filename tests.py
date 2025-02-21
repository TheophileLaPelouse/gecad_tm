#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 10:47:46 2025

@author: theophilemounier
"""

# Model* init_model(double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, double discharge_rate, double **TE, double *TP, int indexPprev[2], int Nbdays, double *Kp, double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, size_t n_tot_time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) {
#     printf("Econs: %p, first value: %f\n", Econs, Econs[0]);
#     printf("Eprod: %p, first value: %f\n", Eprod, Eprod[0]);
#     printf("indexPb: %p, first value: %d\n", indexPb, indexPb[0]);
#     printf("TE: %p, first value: %f\n", TE, TE[0][0]);
#     printf("TP: %p, first value: %f\n", TP, TP[0]);
#     printf("indexPprev: %p, first value: %d\n", indexPprev, indexPprev[0]);
#     printf("Kp: %p, first value: %f\n", Kp, Kp[0]);
#     printf("SOC: %p, first value: %f\n", SOC, SOC[0]);
#     printf("tot_time: %p, first value: %zu\n", tot_time, tot_time[0]);
#     printf("time_month: %p, first value: %zu\n", time_month, time_month[0][0][0]);
#     printf("n_time_month: %p, first value: %zu\n", n_time_month, n_time_month[0][0]);
#     printf("months: %p, first value: %d\n", months, months[0]);
#     printf("periods: %p, first value: %d\n", periods, periods[0]);
    
#     Model *model = (Model*)malloc(sizeof(Model));
#     if (model == NULL) {
#         fprintf(stderr, "Failed to allocate memory for model\n");
#         return NULL;
#     }
#     printf("Model\n");
#     model->Econs = Econs;
#     printf("Model Econs\n");
#     model->Eprod = Eprod;
#     printf("Model Eprod\n");
#     memcpy(model->indexPb, indexPb, 2 * sizeof(int));
#     printf("Model indexPb\n");
#     model->deltat = deltat;
#     printf("Model deltat\n");
#     model->charge_rate = charge_rate;
#     printf("Model charge_rate\n");
#     model->discharge_rate = discharge_rate;
#     printf("Model discharge_rate\n");
#     model->TE = TE;
#     printf("Model TE\n");
#     model->TP = TP;
#     printf("Model TP\n");
#     memcpy(model->indexPprev, indexPprev, 2 * sizeof(int));
#     printf("Model indexPprev\n");
#     model->Nbdays = Nbdays;
#     printf("Model Nbdays\n");
#     model->Kp = Kp;
#     printf("Model Kp\n");
#     model->tep = tep;
#     printf("Model tep\n");
#     model->indexCb = indexCb;
#     printf("Model indexCb\n");
#     model->TB = TB;
#     printf("Model TB\n");
#     model->batterie_life = batterie_life;
#     printf("Model batterie_life\n");
#     model->TBm = TBm;
#     printf("Model TBm\n");
#     model->SOC = SOC;
#     printf("Model SOC\n");
#     model->tot_time = tot_time;
#     printf("Model tot_time\n");
#     model->n_tot_time = n_tot_time;
#     printf("Model n_tot_time\n");
#     model->time_month = time_month;
#     printf("Model time_month\n");
#     model->n_time_month = n_time_month;
#     printf("Model n_time_month\n");
#     model->months = months;
#     printf("Model months\n");
#     model->n_m = n_m;
#     printf("Model n_m\n");
#     model->periods = periods;
#     printf("Model periods\n");
#     model->n_p = n_p;
#     printf("Model n_p\n");
#     return model;
# }
import ctypes
import pandas
import os 
path = os.path.join(os.path.dirname(__file__), 'C/libmodel.so')
lib = ctypes.CDLL(path)
lib.init_model.argtypes = [
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_double),  # Econs
    ctypes.POINTER(ctypes.c_double),  # Eprod
    ctypes.POINTER(ctypes.c_int),     # indexPb
    ctypes.c_double,                  # deltat
    ctypes.c_double,                  # charge_rate
    ctypes.c_double,                  # discharge_rate
    ctypes.c_double,                  # Effc
    ctypes.c_double,                  # Effd
    ctypes.POINTER(ctypes.POINTER(ctypes.c_double)),  # TE
    ctypes.POINTER(ctypes.c_double),  # TP
    ctypes.POINTER(ctypes.c_int),     # indexPprev
    ctypes.c_int,                     # Nbdays
    ctypes.POINTER(ctypes.c_double),  # Kp
    ctypes.c_double,                  # tep
    ctypes.c_int,                     # indexCb
    ctypes.c_double,                  # TB
    ctypes.c_double,                  # batterie_life
    ctypes.c_double,                  # TBm
    ctypes.POINTER(ctypes.c_double),  # SOC
    ctypes.POINTER(ctypes.c_size_t),  # tot_time
    ctypes.c_size_t,                  # n_tot_time
    ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t))),  # time_month
    ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)),  # n_time_month
    ctypes.POINTER(ctypes.c_int),     # months
    ctypes.c_int,                     # n_m
    ctypes.POINTER(ctypes.c_int),     # periods
    ctypes.c_int                      # n_p
]

class Model(ctypes.Structure):
    _fields_ = [
        ("Var_size", ctypes.c_size_t),
        ("Econs", ctypes.POINTER(ctypes.c_double)),
        ("Eprod", ctypes.POINTER(ctypes.c_double)),
        ("indexPb", ctypes.c_int * 2),
        ("deltat", ctypes.c_double),
        ("charge_rate", ctypes.c_double),
        ("discharge_rate", ctypes.c_double),
        ("effc", ctypes.c_double),
        ("effd", ctypes.c_double),
        ("TE", ctypes.POINTER(ctypes.POINTER(ctypes.c_double))),
        ("TP", ctypes.POINTER(ctypes.c_double)),
        ("indexPprev", ctypes.c_int * 2),
        ("Nbdays", ctypes.c_int),
        ("Kp", ctypes.POINTER(ctypes.c_double)),
        ("tep", ctypes.c_double),
        ("indexCb", ctypes.c_int),
        ("TB", ctypes.c_double),
        ("batterie_life", ctypes.c_double),
        ("TBm", ctypes.c_double),
        ("SOC", ctypes.POINTER(ctypes.c_double)),
        ("tot_time", ctypes.POINTER(ctypes.c_size_t)),
        ("n_tot_time", ctypes.c_size_t),
        ("time_month", ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)))),
        ("n_time_month", ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t))),
        ("months", ctypes.POINTER(ctypes.c_int)),
        ("n_m", ctypes.c_int),
        ("periods", ctypes.POINTER(ctypes.c_int)),
        ("n_p", ctypes.c_int)
    ]
    
class Individual(ctypes.Structure):
    _fields_ = [
        ("mod", ctypes.POINTER(Model)),
        ("var", ctypes.POINTER(ctypes.c_double)),
        ("fitness", ctypes.c_double), 
        ("list_obj", ctypes.POINTER(ctypes.c_double))
    ]

lib.init_model.restype = ctypes.POINTER(Model)    

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

# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 4, 0, 59))
timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 30, 23, 59))
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
# 
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

opti_bounds = [[0, 0] for k in range(Var_size)]
for k in range(*indexPb) : 
    opti_bounds[k] = [-1, 1]
opti_bounds[indexCb] = [0.0001, 1000]
for k in range(*indexPprev) : 
    opti_bounds[k] = [0, 500]
    
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
TB = 0
TBm = 0.019
TBm = 0
batterie_life = 10
months = range(1, 13)
periods = range(6)

Eprod = Eautocons
SOC = [0 for k in range(len(Econs))]
n_tot_time = len(tot_time)
time = Time
n_m = 12
n_p = 6


time_month_conversion = (ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)) * len(time_month))(*[
                            (ctypes.POINTER(ctypes.c_size_t) * len(time_month[month]))(*[
                                (ctypes.c_size_t * len(time_month[month][period]))(*time_month[month][period])
                                for period in range(len(time_month[month]))
                            ])
                            for month in range(len(time_month))
                        ])


model = lib.init_model(Var_size, 
                       (ctypes.c_double * len(Econs))(*Econs), 
                        (ctypes.c_double * len(Eprod))(*Eprod), 
                        (ctypes.c_int * 2)(*indexPb), 
                        deltat,
                        charge_rate,
                        discharge_rate, 
                        Effc, 
                        Effd,
                        (ctypes.POINTER(ctypes.c_double) * len(TE))(*[ (ctypes.c_double * len(TE[i]))(*TE[i]) for i in range(len(TE))]), 
                        (ctypes.c_double * len(TP))(*TP),
                        (ctypes.c_int * 2)(*indexPprev),
                        Nbdays,
                        (ctypes.c_double * 6)(*Kp),
                        tep, 
                        indexCb,
                        TB, 
                        batterie_life, 
                        TBm, 
                        (ctypes.c_double * len(SOC))(*SOC),
                        (ctypes.c_size_t * len(tot_time))(*tot_time),
                        n_tot_time, 
                        time_month_conversion,
                        (ctypes.POINTER(ctypes.c_size_t) * len(n_time_month))(*[(ctypes.c_size_t * len(n_time_month[i]))(*n_time_month[i]) for i in range(len(n_time_month))]),
                        (ctypes.c_int * len(months))(*months),
                        n_m, 
                        (ctypes.c_int * len(periods))(*periods),
                        n_p)
print(model)
print('success1')


lib.run_comp.argtypes = [
    ctypes.c_int, # code
    ctypes.POINTER(ctypes.POINTER(ctypes.c_double)), # opti_bounds
    ctypes.c_int, # nb_pop
    ctypes.c_int, # nb_gen
    ctypes.c_double, # pl
    ctypes.c_double, # pq
    ctypes.c_double, # mutation_rate
    ctypes.c_int, # last_element
    ctypes.c_double, # threshold
    ctypes.c_double, # fac
    ctypes.c_double, # min
    ctypes.c_double, # max
    ctypes.c_size_t, # Var_size
    ctypes.POINTER(ctypes.c_double), # Econs
    ctypes.POINTER(ctypes.c_double), # Eprod
    ctypes.POINTER(ctypes.c_int), # indexPb
    ctypes.c_double, # deltat
    ctypes.c_double, # charge_rate
    ctypes.c_double, # discharge_rate
    ctypes.c_double, # effc
    ctypes.c_double, # effd
    ctypes.POINTER(ctypes.POINTER(ctypes.c_double)), # TE
    ctypes.POINTER(ctypes.c_double), # TP
    ctypes.POINTER(ctypes.c_int), # indexPprev
    ctypes.c_int, # Nbdays
    ctypes.POINTER(ctypes.c_double), # Kp
    ctypes.c_double, # tep
    ctypes.c_int, # indexCb
    ctypes.c_double, # TB
    ctypes.c_double, # batterie_life
    ctypes.c_double, # TBm
    ctypes.POINTER(ctypes.c_double), # SOC
    ctypes.POINTER(ctypes.c_size_t), # tot_time
    ctypes.c_size_t, # n_tot_time
    ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t))), # time_month
    ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)), # n_time_month
    ctypes.POINTER(ctypes.c_int), # months
    ctypes.c_int, # n_m
    ctypes.POINTER(ctypes.c_int), # periods
    ctypes.c_int # n_p
]

# lib.run_comp.restype = ctypes.POINTER(Individual)
lib.run_comp.restype = ctypes.c_void_p
#%%

# Individual* run_comp(
#     double opti_bounds[][2], int nb_pop, int nb_gen, double pl, double pq, double mutation_rate, int last_element, double threshold, double fac,
#     size_t Var_size, double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, 
#     double discharge_rate, double **TE, double *TP, int indexPprev[2], int Nbdays, double *Kp, 
#     double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, 
#     size_t n_tot_time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) {
    
#     Model *model = init_model(Var_size, Econs, Eprod, indexPb, deltat, charge_rate, discharge_rate, TE, TP, indexPprev, Nbdays, Kp, tep, indexCb, TB, batterie_life, TBm, SOC, tot_time, n_tot_time, time_month, n_time_month, months, n_m, periods, n_p);
#     printf("Model Econs avant : %f\n", model->Econs[0]);
#     for (int i = 0; i < Var_size; i++) {
#         printf("opti_bounds[%d][0]: %f, opti_bounds[%d][1]: %f\n", i, opti_bounds[i][0], i, opti_bounds[i][1]);
#     }
#     Individual best_indiv = GA(model, opti_bounds, nb_pop, nb_gen, pl, pq, mutation_rate, last_element, threshold, fac);
#     printf("Model Econs après : %f\n", model->Econs[0]);
#     Individual *best_indiv_ptr = (Individual *)malloc(sizeof(Individual));
#     if (best_indiv_ptr == NULL) {
#         fprintf(stderr, "Failed to allocate memory for best_indiv_ptr\n");
#         return NULL;
#     }
#     *best_indiv_ptr = best_indiv;
#     // free_model(model);
#     return best_indiv_ptr;
# }

import sys 

nb_pop = 20
nb_gen = 1    
pl = 0.0001
pq = 0.0001
mutation_rate = 0.2 
last_element = 10
threshold = 1e-05
fac = 1  
args = [1, nb_pop, nb_gen, pl, pq, mutation_rate, last_element, threshold, fac, 1/1000, 1/10]

for k in range(1, len(sys.argv)) : 
    args[k-1] = sys.argv[k]
    
print(args)
    
test = lib.run_comp(
    int(args[0]),
    (ctypes.POINTER(ctypes.c_double)*Var_size) (*[(ctypes.c_double*2) (*opti_bounds[i]) for i in range(Var_size)]), 
    int(args[1]), 
    int(args[2]), 
    float(args[3]), 
    float(args[4]),
    float(args[5]), 
    int(args[6]), 
    float(args[7]),
    float(args[8]),
    float(args[9]),
    float(args[10]),
    Var_size, 
    (ctypes.c_double * len(Econs))(*Econs), 
    (ctypes.c_double * len(Eprod))(*Eprod), 
    (ctypes.c_int * 2)(*indexPb), 
    deltat,
    charge_rate, 
    discharge_rate, 
    Effc, 
    Effd,
    (ctypes.POINTER(ctypes.c_double) * len(TE))(*[ (ctypes.c_double * len(TE[i]))(*TE[i]) for i in range(len(TE))]), 
    (ctypes.c_double * len(TP))(*TP),
    (ctypes.c_int * 2)(*indexPprev),
    Nbdays,
    (ctypes.c_double * 6)(*Kp),
    tep, 
    indexCb,
    TB, 
    batterie_life, 
    TBm, 
    (ctypes.c_double * len(SOC))(*SOC),
    (ctypes.c_size_t * len(tot_time))(*tot_time),
    n_tot_time, 
    time_month_conversion,
    (ctypes.POINTER(ctypes.c_size_t) * len(n_time_month))(*[(ctypes.c_size_t * len(n_time_month[i]))(*n_time_month[i]) for i in range(len(n_time_month))]),
    (ctypes.c_int * len(months))(*months),
    n_m, 
    (ctypes.c_int * len(periods))(*periods),
    n_p)

print(test)
print("success2")                      

if int(args[0]) == 1 or int(args[0]) == 2 :
    print('Et du coup pourquoi on fait rien ici ?')
    df = pandas.read_csv('results_c.dat', sep=' ') # It is too much to call pandas for this 
    df['Fitness'].plot()

    import matplotlib.pyplot as plt 
    # plt.plot(to_plot)
    plt.show()

# python tests.py 100 100  0.01 0.01
