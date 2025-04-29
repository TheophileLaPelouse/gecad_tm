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

from representative_days import separate_days, create_index
from opti_peer_prosumers import * # I know it is ugly but it is for importing all the compute_price function needed to load the pickle save 
# For explicit import we could  put all the useful functions in a class so it is easier to import 

def create_clusters(Prosumers, full_date, nb_cluster, metric="dtw", max_iter = 100, tol=1e-06, n_init = 10, no_plot=False, norm=False): 
    All_days = []
    index_prosumers = []
    for key in Prosumers : 
        All_days.append(separate_days(Prosumers[key]['load'], Prosumers[key]['prod'], full_date))
        index_prosumers.append(key)
    
    nb_prosumers = len(All_days)
    nb_time_day = len(All_days[0][0]['date'])
    nb_days = len(All_days[0])
    ts = np.zeros((nb_days, nb_time_day, 2*nb_prosumers))
    
    to_rm = []
    for k in range(nb_prosumers) : 
        for d in range(nb_days) : 
            for i in range(nb_time_day) :
                try : 
                    ts[d, i, 2*k] = All_days[k][d]['Econs'][i]
                    ts[d, i, 2*k+1] = All_days[k][d]['Eprod'][i]
                except IndexError : 
                    to_rm.append(k)
    
    ts = np.delete(ts, to_rm, axis=0)
    ts = to_time_series_dataset(ts)
    km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
    clusters = km.fit_predict(ts)
    silhouette_mean = silhouette_score(ts, clusters)
    
    days_by_clusters = [[] for k in range(nb_cluster)]
    for k in range(len(clusters)) : 
        days_by_clusters[clusters[k]].append(k)
        
    # We can something to plot if needed here 
    return days_by_clusters, silhouette_mean, All_days, index_prosumers

def Choose_max_repr(days_by_clusters, All_days, index_prosumers) : 
    days_result = []
    for days in days_by_clusters : 
        maxi = -9999999999
        for k in range(len(days)) : 
            s = sum(sum(All_days[i][days[k]]['Etot']) for i in range(len(index_prosumers)))
            if s > maxi : 
                day_max = k 
                maxi = s 
        days_result.append(days[day_max])
    return days_result

def Retrieve_optimization_list(day_results, All_days, Prosumers, index_prosumers) : 
    Prosumers_repr = []
    for k in index_prosumers : 
        Prosumers_repr.append({})
        for key in Prosumers[k] : 
            if key not in ['load', 'prod', 'full_date', 'Time_ref'] :  
                Prosumers_repr[-1][key] = Prosumers[k][key]
                # Will not change so we can do simple = and not create copies
    
    for day in day_results : 
        key = index_prosumers[0]
        timeframe = [All_days[0][day]['date'][0], All_days[0][day]['date'][-1]]
        index = create_index(timeframe[0], Prosumers[key]['full_date'], timeframe[1]-timeframe[0])[:-1]
        for key in Prosumers : 
            key_index = 0
            while index_prosumers[key_index] != key and key_index < len(index_prosumers): 
                key_index += 1
            for i in index : 
                for key2 in ['load', 'prod', 'full_date', 'Time_ref'] : 
                    if not Prosumers_repr[key_index].get(key2) : 
                        Prosumers_repr[key_index][key2] = []
                    Prosumers_repr[key_index][key2].append(Prosumers[key][key2][i])
    return Prosumers_repr
                    
def get_repr_data() : 
    Prosumers, _ = make_dico()
    full_date = Prosumers[list(Prosumers.keys())[0]]['full_date']
    nb_cluster = 60
    days_by_clusters, silhouette_mean, All_days, index_prosumers = create_clusters(Prosumers, full_date, nb_cluster)
    day_results = Choose_max_repr(days_by_clusters, All_days, index_prosumers)
    Prosumers_repr = Retrieve_optimization_list(day_results, All_days, Prosumers, index_prosumers)
    return Prosumers_repr
            
#%%
if __name__=='__main__' : 
    import json
    path_load = os.path.join(os.path.dirname(__file__), 'Results/csv/Prosumers_dico.pkl')
    Prosumers = load_prosumers(path_load)
    full_date = Prosumers[list(Prosumers.keys())[0]]['full_date']
    nb_cluster = 60
    days_by_clusters, silhouette_mean, All_days, index_prosumers = create_clusters(Prosumers, full_date, nb_cluster)
    day_results = Choose_max_repr(days_by_clusters, All_days, index_prosumers)
    Prosumers_repr = Retrieve_optimization_list(day_results, All_days, Prosumers, index_prosumers)
    path_save = os.path.join(os.path.dirname(__file__), 'Results/csv/Prosumers_repr.pkl')
    save_prosumers(Prosumers_repr, path_save)
    path_index = os.path.join(os.path.dirname(__file__), 'Results/csv/index_prosumers.json')
    with open(path_index, 'w') as f : 
        json.dump(index_prosumers, f)
    
    