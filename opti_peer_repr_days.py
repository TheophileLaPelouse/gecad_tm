"""
Generate representative days for peer prosumers

Try to use the same methods as before but using the load and prod of the differents prosumers.
Need to separate dico in opti_peer_prosumers.py into day by day one 
and then do the same as before with more dimensions.

"""


import pandas as pd 
import datetime as dt 
from tslearn.utils import to_time_series_dataset
from tslearn.clustering import TimeSeriesKMeans, silhouette_score, KernelKMeans, KShape
from tslearn.barycenters import dtw_barycenter_averaging
from tslearn.metrics import dtw
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import silhouette_samples
from random import random
import os

from representative_days import separate_days
from opti_peer_prosumers import Prosumers

def create_clusters(Prosumers, full_date, nb_cluster, metric="dtw", max_iter = 100, tol=1e-06, n_init = 10, no_plot=False, norm=False): 
    All_days = []
    for key in Prosumers : 
        All_days.append(separate_days(Prosumers[key]['load'], Prosumers[key]['prod'], full_date))
    
    nb_prosumers = len(All_days)
    nb_time_day = len(All_days[0][0]['date'])
    nb_days = len(All_days[0])
    ts = np.zeros((nb_days, nb_time_day, 2*nb_prosumers))
    
    to_rm = []
    for k in range(nb_prosumers) : 
        for d in range(nb_days) : 
            for i in range(nb_time_day) :
                try : 
                    ts[d, i, 2*k] = All_days[k][d]['load'][i]
                    ts[d, i, 2*k+1] = All_days[k][d]['prod'][i]
                except IndexError : 
                    to_rm.append(k)
    
    ts = np.delete(ts, to_rm, axis=0)
    ts = to_time_series_dataset(ts)
    km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
    clusters = km.fit_predict(formatted)
    silhouette_mean = silhouette_score(formatted, clusters)
    
    days_by_clusters = [[] for k in range(nb_cluster)]
    for k in range(len(clusters)) : 
        days_by_clusters[clusters[k]].append(k)
        
    # We can something to plot if needed here 
    return days_by_clusters