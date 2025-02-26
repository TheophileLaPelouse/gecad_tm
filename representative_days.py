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

from prices import define_time, Econs, Eautocons as Eprod, TEauto, tep, Kp, period_hours, full_date, last_day, search_dico

Pcons = [val/0.25 for val in Econs]
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

#%%

months = range(1, 12) # No december for the moment 

# For each month, we will take 3 representative days, one that represents the mediane in term of power output 
# One that represents the day with the highest power output and one that represents the day with the lowest power output.
# Warning, maybe we should add some representative days specifically in the none working days.

def create_index(day, full_date, delta = dt.timedelta(hours = 23, minutes = 59)) : 
    return range(search_dico(full_date, day, 'fin'), search_dico(full_date, day + delta, 'debut')+1)

def select_days(month, TE, Econs, Eprod, period_hours, full_date, deltat = dt.timedelta(minutes=15), during_day_stat = None) : 
    if month != 11 : 
        timeframe = (dt.datetime(2024, month, 1, 0, 0), last_day(dt.datetime(2024, month, 1, 0, 0)))
    else :
        timeframe = (dt.datetime(2024, month, 1, 0, 0), dt.datetime(2024, month, 21, 23, 59))
    # Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
    d = timeframe[0]
    
    mediane_day = {'Econs' : [], 'Eprod' : [], 'sum_Econs' : 0, 'sum_Eprod' : 0, 'sum_Econs_Eprod' : 0, 'day' : None}
    max_day = {'Econs' : [], 'Eprod' : [], 'sum_Econs' : 0, 'sum_Eprod' : 0, 'sum_Econs_Eprod' : 0, 'day' : None}
    min_day = {'Econs' : [], 'Eprod' : [], 'sum_Econs' : 0, 'sum_Eprod' : 0, 'sum_Econs_Eprod' : 1000000000, 'day' : None}
    Econs_month = []
    Eprod_month = []
    Ecp_month = []
    days = []
    while d < timeframe[1] : 
        index = create_index(d, full_date)
        sum_Econs = sum([Econs[k] for k in index]) # I verified, it is really faster with the brackets
        sum_Eprod = sum([Eprod[k] for k in index])
        sum_Econs_Eprod = sum_Econs - sum_Eprod
        
        during_day_stat_values = {}
        
        k = search_dico(Ecp_month, sum_Econs_Eprod, 'fin')
        if days :
            Ecp_month = Ecp_month[:k] + [sum_Econs_Eprod] + Ecp_month[k:]
            days = days[:k] + [d] + days[k:]
            Econs_month = Econs_month[:k] + [sum_Econs] + Econs_month[k:]
            Eprod_month = Eprod_month[:k] + [sum_Eprod] + Eprod_month[k:]
            
        else :
            days.append(d)
            Econs_month.append(sum_Econs)
            Eprod_month.append(sum_Eprod)
            Ecp_month.append(sum_Econs_Eprod)
        
        if sum_Econs_Eprod > max_day['sum_Econs_Eprod'] : 
            max_day['sum_Econs'] = sum_Econs
            max_day['sum_Eprod'] = sum_Eprod
            max_day['sum_Econs_Eprod'] = sum_Econs_Eprod
            max_day['day'] = d
        
        if sum_Econs_Eprod < min_day['sum_Econs_Eprod'] :
            min_day['sum_Econs'] = sum_Econs
            min_day['sum_Eprod'] = sum_Eprod
            min_day['sum_Econs_Eprod'] = sum_Econs_Eprod
            min_day['day'] = d
            
        if during_day_stat is not None : 
            for k in index :
                during_day_stat_values = during_day_stat(k, month, TE, Econs, Eprod, period_hours, full_date, deltat, during_day_stat_values)
                
        d += dt.timedelta(days=1)
        
    med = len(Ecp_month)//2
    index = create_index(days[med], full_date)
    print(mediane_day)
    mediane_day['sum_Econs'] = Econs_month[med]
    mediane_day['sum_Eprod'] = Eprod_month[med]
    mediane_day['sum_Econs_Eprod'] = Ecp_month[med]
    mediane_day['day'] = days[med]
    mediane_day['Econs'] = [Econs[k] for k in index]
    mediane_day['Eprod'] = [Eprod[k] for k in index]
    
    index = create_index(max_day['day'], full_date)
    max_day['Econs'] = [Econs[k] for k in index]
    max_day['Eprod'] = [Eprod[k] for k in index]

    index = create_index(min_day['day'], full_date)
    min_day['Econs'] = [Econs[k] for k in index]
    min_day['Eprod'] = [Eprod[k] for k in index]
    
    return mediane_day, max_day, min_day, during_day_stat_values

# Same function but now list of condition to build several representative days 

def select_days2(month, TE, Econs, Eprod, period_hours, full_date, list_of_cond, list_frac, deltat = dt.timedelta(minutes=15), during_day_stat = None) :
    # Conditions should be written as such "sum_Econs > name_of_the_value"
    Days = {}
    for cond in list_of_cond :
        args = cond.split(' ')
        # check if the condition is well written
        flag = True 
        if len(args) != 3 : 
            flag = False
        elif args[0] not in [p + '_' + q for p in ['sum', 'max', 'min', 'mean', 'prod'] for q in ['Econs', 'Eprod', 'Econs_Eprod']] : 
            flag = False
        elif args[1] not in ['>', '<', '>=', '<=', '=='] : 
            flag = False
        if not flag : 
            print('The condition ' + cond + ' is not well written')
        else :
            Days[args[2]] = {'Econs' : [], 'Eprod' : [], 'sum_Econs' : 0, 'sum_Eprod' : 0, 'sum_Econs_Eprod' : 0, 'frac' : 1, 'day' : None, 'cond' : cond}
            if args[1] in ['<', '<='] : 
                Days[args[2]]['sum_Econs_Eprod'] = 1000000000 # We can add some zero if needed
                Days[args[2]]['sum_Econs'] = 1000000000
                Days[args[2]]['sum_Eprod'] = 1000000000
    
    for frac in list_frac : 
        Days[str(frac)] = {'Econs' : [], 'Eprod' : [], 'sum_Econs' : 0, 'sum_Eprod' : 0, 'frac' : 1, 'sum_Econs_Eprod' : 0, 'day' : None}
        
    if month != 11 : 
        timeframe = (dt.datetime(2024, month, 1, 0, 0), last_day(dt.datetime(2024, month, 1, 0, 0)))
    else :
        timeframe = (dt.datetime(2024, month, 1, 0, 0), dt.datetime(2024, month, 21, 23, 59))
    # Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
    d = timeframe[0]
        
    Econs_month = []
    Eprod_month = []
    Ecp_month = []
    Efrac_month = []
    days = []

    while d < timeframe[1] : 
        index = create_index(d, full_date)
        sum_Econs = sum([Econs[k] for k in index]) # I verified, it is really faster with the brackets
        sum_Eprod = sum([Eprod[k] for k in index])
        sum_Econs_Eprod = sum_Econs - sum_Eprod
        
        during_day_stat_values = {}
        
        k = search_dico(Efrac_month, sum_Eprod/sum_Econs, 'fin')
        if days :
            Efrac_month = Efrac_month[:k] + [sum_Eprod/sum_Econs] + Efrac_month[k:]
            Ecp_month = Ecp_month[:k] + [sum_Econs_Eprod] + Ecp_month[k:]
            days = days[:k] + [d] + days[k:]
            Econs_month = Econs_month[:k] + [sum_Econs] + Econs_month[k:]
            Eprod_month = Eprod_month[:k] + [sum_Eprod] + Eprod_month[k:]
            
        else :
            days.append(d)
            Efrac_month.append(sum_Eprod/sum_Econs)
            Econs_month.append(sum_Econs)
            Eprod_month.append(sum_Eprod)
            Ecp_month.append(sum_Econs_Eprod)
        
        for key in Days.keys() :
            if not key.replace('.', '').isnumeric() : # Not the fractions
                args = Days[key]['cond'].split(' ')
                # print(args[0] + args[1] + 'Days[key]["%s"]' % args[0])
                # print(eval(args[0]), eval(args[1]), eval(args[2]))
                if eval(args[0] + args[1] + 'Days[key]["%s"]' % args[0]) : 
                    Days[key]['sum_Econs'] = sum_Econs
                    Days[key]['sum_Eprod'] = sum_Eprod
                    Days[key]['sum_Econs_Eprod'] = sum_Econs_Eprod
                    Days[key]['frac'] = sum_Eprod/sum_Econs
                    Days[key]['day'] = d
                
        if during_day_stat is not None : 
            for k in index :
                during_day_stat_values = during_day_stat(k, month, TE, Econs, Eprod, period_hours, full_date, deltat, during_day_stat_values)
                
        d += dt.timedelta(days=1)
    
    for frac in list_frac : 
        med = int(len(Ecp_month)*frac)
        # index = create_index(days[med], full_date)[:-1]
        print(days[med])
        print(index)
        print()
        Days[str(frac)]['sum_Econs'] = Econs_month[med]
        Days[str(frac)]['sum_Eprod'] = Eprod_month[med]
        Days[str(frac)]['sum_Econs_Eprod'] = Ecp_month[med]
        Days[str(frac)]['day'] = days[med]
        # Days[str(frac)]['Econs'] = [Econs[k] for k in index]
        # Days[str(frac)]['Eprod'] = [Eprod[k] for k in index]
    
    for key in Days :
        # print(Days[key])
        index = create_index(Days[key]['day'], full_date)[:-1]
        Days[key]['Econs'] = [Econs[k] for k in index]
        Days[key]['Eprod'] = [Eprod[k] for k in index]
        
    return Days, during_day_stat_values
    
def separate_days(Econs, Eprod, full_date, TE = TE, period_hours=period_hours, delta=dt.timedelta(hours=23, minutes=59)) : 
    if TE is not None : 
        if period_hours is None : 
            raise ValueError('Faut avoir des périodes pour les prix par contre')
            
    n = len(full_date)
    previous_date = full_date[0]
    Days = [{'Econs': [], 'Eprod': [], 'Econs_norm' : [], 'Eprod_norm' : [], 'date': [], 'price': [], 'payed': [], 'Etot': [], 'day_number' : 0}]
    for k in range(n) : 
        date = full_date[k]
        if date - previous_date > delta :
            Days.append({'Econs': [], 'Eprod': [], 'Econs_norm' : [], 'Eprod_norm' : [], 'date': [], 'price': [], 'payed': [], 'Etot': [], 'day_number' : k})
            previous_date = date
        Days[-1]['Econs'].append(Econs[k])
        Days[-1]['Eprod'].append(Eprod[k])
        Days[-1]['date'].append(date)
        
        month = date.month
        p = 0
        for val in period_hours[month-1] : 
            flag = False
            for tup in val :
                if date.hour >= tup[0] and date.hour < tup[1] : 
                    flag = True
            if flag : 
                break
            p += 1
        Days[-1]['price'].append(TE[month-1][p])
        Days[-1]['payed'].append((Econs[k] - Eprod[k])*TE[month-1][p])
        Days[-1]['Etot'].append(Econs[k] - Eprod[k])
        
    for day in Days : 
        day['sum_Etot'] = sum([abs(day['Etot'][k]) for k in range(len(day['Etot']))])
        day['min_Etot'] = min(day['Etot'])
        day['max_Etot'] = max(day['Etot'])
        day['min_Econs'] = min(day['Econs'])
        day['max_Econs'] = max(day['Econs'])
        day['min_Eprod'] = min(day['Eprod'])
        day['max_Eprod'] = max(day['Eprod'])
        day['Econs_norm'] = [val/max(day['max_Econs'], abs(day['min_Econs'])) for val in day['Econs']]
        for val in day['Eprod'] :   
            if max(day['max_Eprod'], abs(day['min_Eprod'])) == 0 :
                day['Eprod_norm'].append(0)
            else : 
                day['Eprod_norm'].append(val/max(day['max_Eprod'], abs(day['min_Eprod'])))
    
    return Days


def calculate_ratio(k_day, Days) : 
    sum_Econs = sum(Days[k_day]['Econs'])
    sum_Eprod = sum(Days[k_day]['Eprod'])
    return sum_Eprod/sum_Econs
    
def create_clusters(Days, nb_cluster, metric="dtw", max_iter = 100, tol=1e-06, n_init = 10) : 
    # For running test
    ts_Etot = [Days[k]['Etot'] for k in range(len(Days))]
    
    # ts = np.zeros((len(ts_val), len(ts_val[0]['date']), 2))
    # for k in range(len(ts_val)) : 
    #     for i in range(len(ts_val[0]['date'])) :
    #         print(k, i, ts_val[k])
    #         ts[k, i, 0] = ts_val[k]['Econs'][i]
    #         ts[k, i, 1] = ts_val[k]['Eprod'][i]
    
    formatted = to_time_series_dataset(ts_Etot)
    # formatted=to_time_series_dataset(ts)
    km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
    # km = KernelKMeans(n_clusters=nb_cluster, max_iter=max_iter, tol=tol, n_init=n_init)
    # km = KShape(n_clusters=nb_cluster, max_iter=max_iter, tol=tol, n_init=n_init)
    clusters = km.fit_predict(formatted)
    silhouette = silhouette_score(formatted, clusters)
    
    days_by_clusters = [[] for k in range(nb_cluster)]
    for k in range(len(clusters)) : 
        days_by_clusters[clusters[k]].append(k)
        
    results = [{'ratios' : [], 'dtws' : [], 'dtws_norm' : [], 'max_dif' : []} for k in range(nb_cluster)]
    c = 0
    for days in days_by_clusters : 
        fig, ax = plt.subplots()
        result = results[c]
        formatted_in_cluster = formatted[days]
        bar = dtw_barycenter_averaging(formatted_in_cluster)
        Etotmax = max([max(abs(formatted[day])) for day in days])
        for day in days :
            result['ratios'].append(calculate_ratio(day, Days))
            result['dtws'].append(dtw(bar[:, 0], Days[day]['Etot']))
            result['dtws_norm'].append(dtw(bar/Etotmax, formatted[day]/Etotmax))
            result['max_dif'].append(max(abs(bar-formatted[day])/Etotmax))
            
            ax.plot(range(len(Days[day]['Etot'])), Days[day]['Etot'])
        ax.plot(range(len(bar[:, 0])), bar[:, 0], linewidth=2, color='red', label='Cluster 1 Barycenter')
        ax.set_title('%d    %s' % (c, str(days)))
        result['bar'] = bar
        result['plot'] = (fig, ax)
        c +=1
        
    plt.show()
        
    return days_by_clusters, results, silhouette, km

def create_clusters_2D(Days, nb_cluster, metric="dtw", max_iter = 100, tol=1e-06, n_init = 10, no_plot=False, norm=False) : 
    # For running test    
    ts = np.zeros((len(Days), len(Days[0]['date']), 2))
    for k in range(len(Days)) : 
        for i in range(len(Days[0]['date'])) :
            if not norm :
                ts[k, i, 0] = Days[k]['Econs'][i]
                ts[k, i, 1] = Days[k]['Eprod'][i]
            else : 
                ts[k, i, 0] = Days[k]['Econs_norm'][i]
                ts[k, i, 1] = Days[k]['Eprod_norm'][i]
    
    formatted=to_time_series_dataset(ts)
    km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
    # km = KernelKMeans(n_clusters=nb_cluster, max_iter=max_iter, tol=tol, n_init=n_init)
    # km = KShape(n_clusters=nb_cluster, max_iter=max_iter, tol=tol, n_init=n_init)
    clusters = km.fit_predict(formatted)
    silhouette_mean = silhouette_score(formatted, clusters)
    # silhouette_all = silhouette_samples(formatted, clusters)
    
    days_by_clusters = [[] for k in range(nb_cluster)]
    for k in range(len(clusters)) : 
        days_by_clusters[clusters[k]].append(k)
        
    results = [{'ratios' : []} for k in range(nb_cluster)]
    if not no_plot :
        c = 0
        for days in days_by_clusters : 
            fig1, ax1 = plt.subplots()
            fig2, ax2 = plt.subplots()
            result = results[c]
            formatted_in_cluster = formatted[days]
            bar = dtw_barycenter_averaging(formatted_in_cluster)
            # Etotmax = max([max(abs(formatted[day])) for day in days])
            for day in days :
                result['ratios'].append(calculate_ratio(day, Days))
                ax1.plot(range(len(Days[day]['Etot'])), Days[day]['Econs_norm'])
                ax2.plot(range(len(Days[day]['Etot'])), Days[day]['Eprod_norm'])
            ax1.plot(range(len(bar[:, 0])), bar[:, 0], linewidth=2, color='red', label='Cluster Barycenter')
            ax1.set_title('cons %d    %s' % (c, str(days)))
            ax2.plot(range(len(bar[:, 1])), bar[:, 1], linewidth=2, color='red', label='Cluster Barycenter')
            ax2.set_title('prod %d    %s' % (c, str(days)))
            result['bar'] = bar
            result['plot'] = (fig1, ax1, fig2, ax2)
            c +=1
        
        plt.show()
        
    return days_by_clusters, results, silhouette_mean, km

def generate_typical_kmean(Days, nb_cluster, method='max', metric="dtw", max_iter = 100, tol=1e-06, n_init = 5, wanted=50) : 
    # For the optimization
    
    if method == 'max' :
        ts_Etot = [Days[k]['Etot'] for k in range(len(Days))]
        formatted = to_time_series_dataset(ts_Etot)
        km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
        clusters = km.fit_predict(formatted)
        silhouette = silhouette_score(formatted, clusters)
        days_by_clusters = [[] for k in range(nb_cluster)]
        for k in range(len(clusters)) : 
            days_by_clusters[clusters[k]].append(k)
            
        days_result = []
        for days in days_by_clusters : 
            chosen = max(days, key=lambda x : Days[x]['sum_Etot'])
            days_result.append(chosen)
        return days_result
    
    elif method == 'barycenter' : 
        # We need to take the 2D version of the data
        ts = np.zeros((len(Days), len(Days[0]['date']), 2))
        for k in range(len(Days)) : 
            for i in range(len(Days[0]['date'])) :
                ts[k, i, 0] = Days[k]['Econs'][i]
                ts[k, i, 1] = Days[k]['Eprod'][i]
        km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
        clusters = km.fit_predict(ts)
        silhouette = silhouette_score(ts, clusters)
        days_by_clusters = [[] for k in range(nb_cluster)]
        for k in range(len(clusters)) : 
            days_by_clusters[clusters[k]].append(k)
        new_Econs = []
        new_Eprod = []
        number_of_representative = []
        print("len", len(days_by_clusters))
        for days in days_by_clusters : 
            formatted_in_cluster = ts[days]
            bar = dtw_barycenter_averaging(formatted_in_cluster)
            # cluster_centers_
            new_Econs.append(bar[:, 0])
            new_Eprod.append(bar[:, 1])
            number_of_representative.append(len(days))
        return new_Econs, new_Eprod, number_of_representative
    
    elif method=="random" : 
        ts = np.zeros((len(Days), len(Days[0]['date']), 2))
        for k in range(len(Days)) : 
            for i in range(len(Days[0]['date'])) :
                ts[k, i, 0] = Days[k]['Econs'][i]
                ts[k, i, 1] = Days[k]['Eprod'][i]
        km = TimeSeriesKMeans(n_clusters=nb_cluster, metric=metric, max_iter=max_iter, tol=tol, n_init=n_init)
        clusters = km.fit_predict(ts)
        days_by_clusters = [[] for k in range(nb_cluster)]
        for k in range(len(clusters)) : 
            days_by_clusters[clusters[k]].append(k)
        
        nb_days = len(Days)
        cluster_prob = [len(val)/nb_days for val in days_by_clusters]
        Nb_chosen_clust = [int(val*wanted) + int(random()<(val*wanted-int(val*wanted))) for val in cluster_prob]
        
        chosen = []
        for k in range(len(Nb_chosen_clust)) : 
            chosen += list(np.random.choice(days_by_clusters[k], size=Nb_chosen_clust[k], replace=False))
        return chosen
    
    # elif method==""
            
        

def create_data(method="quantile", months=range(1, 10), n_init=1, Econs=Econs, Eprod=Eprod, TE=TE, period_hours=period_hours, full_date=full_date, forced_timeframe=None, nb_days=5, wanted=50) : 
    Econs_new = []
    Eprod_new = []
    full_date_new = []
    days = []
    nb_repr = []
    if method == "complete_random" : 
        if forced_timeframe is None : 
            timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 10, 31, 0, 0))
        else : timeframe = forced_timeframe
        index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
        Econs_m = [Econs[k] for k in index]
        Eprod_m = [Eprod[k] for k in index]
        full_date_m = [full_date[k] for k in index]

        cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
        chosen = np.random.choice(range(len(cluster_Days)), size=nb_days, replace=False)
        for day in chosen : 
            Econs_new += cluster_Days[day]['Econs']
            Eprod_new += cluster_Days[day]['Eprod']
            full_date_new += cluster_Days[day]['date']
            days.append(cluster_Days[day]['date'][0].date())
        
    if method == "year" : 
        if forced_timeframe is None : 
            timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 10, 31, 0, 0))
        else : timeframe = forced_timeframe
        index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
        Econs_m = [Econs[k] for k in index]
        Eprod_m = [Eprod[k] for k in index]
        full_date_m = [full_date[k] for k in index]

        cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
        chosen = generate_typical_kmean(cluster_Days, nb_days, method="random", tol=1e-08, n_init=n_init, metric="dtw", wanted=wanted)
        print('chosen', len(chosen))
        for day in chosen : 
            Econs_new += cluster_Days[day]['Econs']
            Eprod_new += cluster_Days[day]['Eprod']
            full_date_new += cluster_Days[day]['date']
            days.append(cluster_Days[day]['date'][0].date())
    if method=="year_barycenter" : 
        if forced_timeframe is None : 
            timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 10, 31, 0, 0))
        else : timeframe = forced_timeframe
        index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
        Econs_m = [Econs[k] for k in index]
        Eprod_m = [Eprod[k] for k in index]
        full_date_m = [full_date[k] for k in index]
        cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
        Econs_val, Eprod_val, nb_repr = generate_typical_kmean(cluster_Days, nb_days, method="barycenter", tol=1e-08, n_init=n_init, metric="dtw")
        random_day = np.random.choice(range(len(cluster_Days)), replace=False, size=nb_days)
        for k in range(nb_days) : 
            Econs_new += list(Econs_val[k])
            Eprod_new += list(Eprod_val[k])
            # print(random_day[k])
            # print(len(cluster_Days))
            full_date_new += cluster_Days[random_day[k]]['date']
            
            days.append(cluster_Days[random_day[k]]['date'][0].date())
    for m in months :
        if method == "quantile" :
            Days, _ = select_days2(m, TE, Econs, Eprod, period_hours, full_date, [], [0.05, 0.25, 0.5, 0.75, 0.95])
            for key in Days :
                Econs_new += Days[key]['Econs']
                Eprod_new += Days[key]['Eprod']
                full_date_new += [full_date[k] for k in create_index(Days[key]['day'], full_date)[:-1]]
                days.append(Days[key]['day']) # For verification sake
        elif method == "kmean_max" : 
            if forced_timeframe is None : 
                timeframe = (dt.datetime(2024, m, 4, 0, 0), last_day(dt.datetime(2024, m, 4, 0, 0)))
            else : timeframe = forced_timeframe
            index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
            Econs_m = [Econs[k] for k in index]
            Eprod_m = [Eprod[k] for k in index]
            full_date_m = [full_date[k] for k in index]
            cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
            chosen_days = generate_typical_kmean(cluster_Days, nb_days, tol=1e-08, n_init=n_init, metric="dtw")
            for day in chosen_days :
                Econs_new += cluster_Days[day]['Econs']
                Eprod_new += cluster_Days[day]['Eprod']
                full_date_new += cluster_Days[day]['date']
                days.append(cluster_Days[day]['date'][0].date())
        elif method == "kmean_barycenter" :
            if forced_timeframe is None : 
                timeframe = (dt.datetime(2024, m, 4, 0, 0), last_day(dt.datetime(2024, m, 4, 0, 0)))
            else : timeframe = forced_timeframe
            index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
            Econs_m = [Econs[k] for k in index]
            Eprod_m = [Eprod[k] for k in index]
            full_date_m = [full_date[k] for k in index]
            cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
            Econs_val, Eprod_val, nb_repr = generate_typical_kmean(cluster_Days, nb_days, method="barycenter", tol=1e-08, n_init=n_init, metric="dtw")
            random_day = np.random.choice(range(len(cluster_Days)), replace=False, size=5)
            for k in range(5) : 
                Econs_new += list(Econs_val[k])
                Eprod_new += list(Eprod_val[k])
                # print(random_day[k])
                # print(len(cluster_Days))
                full_date_new += cluster_Days[random_day[k]]['date']
                
                days.append(cluster_Days[random_day[k]]['date'][0].date())
                
    
            
    return Econs_new, Eprod_new, full_date_new, days, nb_repr


def gen_new_data(Econs, Eprod, coef_rand=1, coef_Econs = 1, coef_Eprod = 1, offset=0) : 
    # The objective of this function is to add some noise to the data to change the values a bit
    # This should not change too much the shape of the data
    Econs_new = []
    Eprod_new = []
    for k in range(len(Econs)) : 
        Econs_new.append(Econs[k]*coef_Econs + coef_rand*np.random.normal() + offset)
        Eprod_new.append(Eprod[k]*coef_Eprod + coef_rand*np.random.normal() + offset)
    return Econs_new, Eprod_new
    
#%% Create the days 

# Econs_new = []
# Eprod_new = []
# full_date_new = []
# days = []
# for m in months :
#     Days, _ = select_days2(m, TE, Econs, Eprod, period_hours, full_date, [], [0.05, 0.25, 0.5, 0.75, 0.95])
#     for key in Days :
#         Econs_new += Days[key]['Econs']
#         Eprod_new += Days[key]['Eprod']
#         full_date_new += [full_date[k] for k in create_index(Days[key]['day'], full_date)[:-1]]
#         days.append(Days[key]['day']) # For verification sake
if __name__ == '__main__' : 
    
    Econs_new1, Eprod_new1, full_date_new1, days1 = create_data(method="quantile")
    Econs_new2, Eprod_new2, full_date_new2, days2 = create_data(method="kmean_max")
    Econs_new3, Eprod_new3, full_date_new3, days3 = create_data(method="kmean_barycenter")
    

#%% tslearn tests

if __name__ == '__main__' :

    from tslearn.utils import to_time_series_dataset
    from tslearn.clustering import TimeSeriesCentroidBasedClusteringMixin, TimeSeriesKMeans
    
    ts_val = separate_days(Econs, Eprod, full_date)
    ts = np.zeros((len(ts_val)-1, len(ts_val[0]['date']), 2))
    for k in range(len(ts_val)-1) : 
        for i in range(len(ts_val[0]['date'])) :
            ts[k, i, 0] = ts_val[k]['Econs'][i]
            ts[k, i, 1] = ts_val[k]['Eprod'][i]
    
    formatted = to_time_series_dataset(ts)
    
    km = TimeSeriesKMeans(n_clusters=25, metric="dtw")
    # test = km.fit(formatted)
    clusters = km.fit_predict(formatted)
    days_in_1 = []
    for k in range(len(clusters)) : 
        if clusters[k] == 1 : 
            days_in_1.append(k)
            
    formatted_in_cluster1 = formatted[days_in_1]
    
    from tslearn.barycenters import dtw_barycenter_averaging
    bar = dtw_barycenter_averaging(formatted_in_cluster1)
 
#%% Plot cluster 1 results

# if __name__ == '__main__' :
#     import matplotlib.pyplot as plt 
#     plt.figure()
#     for k in range(0, len(days_in_1), 5) : 
#         plt.plot(range(96), formatted_in_cluster1[k, :, 0])
#     plt.plot(range(96), bar[:, 0], linewidth=2, color='red', label='Cluster 1 Barycenter')
#     plt.legend()
#     plt.show()
    
#%% Test cluster on one month
if __name__ == '__main__' :
    month= 8
    # timeframe = (dt.datetime(2024, month, 4, 0, 0), last_day(dt.datetime(2024, month, 4, 0, 0)))
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 6, 30, 23, 59))
    index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
    Econs_m = [Econs[k] for k in index]
    Eprod_m = [Eprod[k] for k in index]
    full_date_m = [full_date[k] for k in index]
    
    cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
    # days_by_clusters, results_clus, silhouette, km = create_clusters(cluster_Days, 8, tol=1e-08, n_init=10, metric="dtw")
    
    # print('\nLes Ratios : ')
    # for k in range(len(results_clus)) : 
    #     print(results_clus[k]['ratios'])
        
    # print('\nLes distances : ')
    # for k in range(len(results_clus)) : 
    #     print(results_clus[k]['dtws_norm'])
        
    # print('\nLes max dif : ')
    # for k in range(len(results_clus)) : 
    #     print(results_clus[k]['max_dif'])
        
    days_by_clusters, results_clus, silhouette, km = create_clusters_2D(cluster_Days, 35, tol=1e-08, n_init=10, metric="dtw", norm=True)

#%% Test cluster year        
if __name__ == '__main__' : 
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 10, 30, 23, 59))
    index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
    Econs_m = [Econs[k] for k in index]
    Eprod_m = [Eprod[k] for k in index]
    full_date_m = [full_date[k] for k in index]
    cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
    S = []
    for k in range(1, 2) :
        days_by_clusters, results_clus, silhouette, km = create_clusters_2D(cluster_Days, 5*k, tol=1e-08, n_init=1, metric="dtw", no_plot=True)
        S.append(silhouette)
        
        
    nb_days = (timeframe[1]-timeframe[0]).days + 1
    cluster_prob = [len(val)/nb_days for val in days_by_clusters]
    wanted = 50
    Nb_chosen_clust = [int(val*wanted) + int(random()<(val*wanted-int(val*wanted))) for val in cluster_prob]
    chosen = []
    for k in range(len(Nb_chosen_clust)) : 
        chosen += list(np.random.choice(days_by_clusters[k], size=Nb_chosen_clust[k], replace=False))
        
#%% Test cluster max days
if __name__ == '__main__' :
    month= 8
    timeframe = (dt.datetime(2024, month, 4, 0, 0), last_day(dt.datetime(2024, month, 4, 0, 0)))
    index = create_index(timeframe[0], full_date, timeframe[1]-timeframe[0])[:-1]
    Econs_m = [Econs[k] for k in index]
    Eprod_m = [Eprod[k] for k in index]
    full_date_m = [full_date[k] for k in index]
    
    cluster_Days = separate_days(Econs_m, Eprod_m, full_date_m)
    chosen_days = generate_typical_kmean(cluster_Days, 5, tol=1e-08, n_init=10, metric="dtw")
    
    plt.figure()
    for day in chosen_days : 
        plt.plot(cluster_Days[day]['Etot'])
    plt.title("Max days with k mean")
        
    Days, _ = select_days2(month, TE, Econs, Eprod, period_hours, full_date, [], [0.05, 0.25, 0.5, 0.75, 0.95])
    plt.figure()
    for day in Days : 
        plt.plot([Days[day]['Econs'][k] - Days[day]['Eprod'][k] for k in range(len(Days[day]['Eprod']))])
    plt.title("quantiles choice")
    
    Econs_barys, Eprod_barys = generate_typical_kmean(cluster_Days, 5, method='barycenter', tol=1e-08, n_init=10, metric="dtw")
    plt.figure()
    for k in range(len(Econs_barys)) :
        plt.plot(Econs_barys[k]-Eprod_barys[k])
    plt.title("Barycenters k mean")
        
    plt.show()

#%%

if __name__ == '__main__' : 
    import matplotlib.pyplot as plt
    # mediane_day, max_day, min_day, during_day_stat_values = select_days(1, TE[0], Econs, Eprod, period_hours, full_date)
    
    # fig, ax = plt.subplots()
    # ax.plot(mediane_day['Econs'], label='Econs')
    # ax.plot(mediane_day['Eprod'], label='Eprod')
    # ax.legend()
    
    # fig2, ax2 = plt.subplots()
    # ax2.plot(max_day['Econs'], label='Econs')
    # ax2.plot(max_day['Eprod'], label='Eprod')
    # ax2.legend()
    
    # fig3, ax3 = plt.subplots()
    # ax3.plot(min_day['Econs'], label='Econs')
    # ax3.plot(min_day['Eprod'], label='Eprod')
    # ax3.legend()
    
    # conds = ['sum_Econs > max_cons', 'sum_Econs < min_cons', 'sum_Eprod > max_prod', 'sum_Eprod < min_prod', 'sum_Econs_Eprod > max_Econs_Eprod', 'sum_Econs_Eprod < min_Econs_Eprod']
    # frac = [1/4, 1/2,3/4, 9/10]
    # Days, during_day_stat_values = select_days2(4, TE[0], Econs, Eprod, period_hours, full_date, conds, frac, during_day_stat = None)
    
    # plts = []
    # for key in Days : 
    #     fig, ax = plt.subplots()
    #     ax.plot(Days[key]['Econs'], label='Econs')
    #     ax.plot(Days[key]['Eprod'], label='Eprod')
    #     Days[key]['Econs_Eprod'] = [Days[key]['Econs'][k] - Days[key]['Eprod'][k] for k in range(len(Days[key]['Eprod']))]
    #     ax.plot(Days[key]['Econs_Eprod'], label='Econs - Eprod')
    #     ax.legend()
    #     ax.set_title(key)
    #     plts.append(fig)
    #     plts.append((fig, ax))
    
    # plt.show()
    
    # Verify if the days created have the good indices
    
    flag = True 
    i0 = 0
    for d in days : 
        index = create_index(d, full_date)[:-1]
        Econs_day = [Econs[k] for k in index]
        Eprod_day = [Eprod[k] for k in index]
        full_date_day = [full_date[k] for k in index]
        
        # index_new = create_index(d, full_date_new) This array is not sorted so it does not work at all
        i1 = i0
        n = len(full_date_new)
        while i1 <n and full_date_new[i1].date() == full_date_new[i0].date() : 
            i1+=1
        index_new = range(i0, i1)
        i0 = i1
        Econs_day_new = [Econs_new[k] for k in index_new]
        Eprod_day_new = [Eprod_new[k] for k in index_new]
        full_date_day_new = [full_date_new[k] for k in index_new]
        
        flag_econs = Econs_day_new == Econs_day
        flag_eprod = Eprod_day_new == Eprod_day
        flag_date = full_date_day_new == full_date_day
        
        if not (flag_econs and flag_eprod and flag_date):
            print(d, 'Pas bon du tout tout ça')
            if not flag_econs:
                print('Econs mismatch')
            if not flag_eprod:
                print('Eprod mismatch')
            if not flag_date:
                print('Date mismatch')
            break
        
    print("YOUPI")