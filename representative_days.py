import pandas as pd 
import datetime as dt 

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

def create_index(day, full_date) : 
    return range(search_dico(full_date, day, 'fin'), search_dico(full_date, day + dt.timedelta(hours = 23, minutes = 59), 'debut')+1)

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
    
    
#%% Create the days 

Econs_new = []
Eprod_new = []
full_date_new = []
days = []
for m in months :
    Days, _ = select_days2(m, TE, Econs, Eprod, period_hours, full_date, [], [0.05, 0.25, 0.5, 0.75, 0.95])
    for key in Days :
        Econs_new += Days[key]['Econs']
        Eprod_new += Days[key]['Eprod']
        full_date_new += [full_date[k] for k in create_index(Days[key]['day'], full_date)[:-1]]
        days.append(Days[key]['day']) # For verification sake

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