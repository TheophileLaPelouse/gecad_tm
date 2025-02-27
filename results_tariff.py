from prices_tubacer import TE, TE_new, TP, TP_new
from prices_porto_motor import TE_pm_2024, TP_pm_2024
from prices import treat_data
from opti import build_model, calculate_price
import datetime as dt
import calendar as cal
from pyomo.opt import SolverFactory
import os
import pandas as pd

Values = {}

Values['Tubacer'] = {}
Values['Porto Motor'] = {}
Values['Narontec'] = {}
Values['TMG'] = {}
Values['Family'] = {}

Values['Tubacer']['TE'] = TE
Values['Tubacer']['TP'] = TP
Values['Tubacer']['original'] = [120, 130, 130, 130, 130, 195]
Values['Narontec']['TE'] = TE_pm_2024
Values['Narontec']['TP'] = TP_pm_2024
Values['Narontec']['original'] = [35, 35, 35, 35, 35, 35]
Values['Porto Motor']['TE'] = TE_pm_2024
Values['Porto Motor']['TP'] = TP_pm_2024
Values['Porto Motor']['original'] = [35, 35, 35, 35, 35, 35]
Values['TMG']['TE'] = TE
Values['TMG']['TP'] = TP

Values['Tubacer']['2024'] = {}
Values['Porto Motor']['2024'] = {}
Values['Porto Motor']['2023'] = {}
Values['Narontec']['2024'] = {}
Values['Narontec']['2023'] = {}
Values['TMG']['2024'] = {}

#Tubacer
# Eautocons, Econs, full_time, deltat = treat_data(name="TUBACER")
# dico = Values['Tubacer']['2024']
# dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat

#Porto Motor
pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
pm2023_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2023.xlsx')
#%%
Eautocons, Econs, full_time, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
dico = Values['Porto Motor']['2024'] 
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]

# Eautocons, Econs, full_time, deltat = treat_data(path=pm2023_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
#                                                  format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
# dico = Values['Porto Motor']['2023']
# dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]

#%%Narontec
# na2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '3_NARONTEC', 'Narontec_2024_hourly.xlsx')
# na2023_path = os.path.join(os.path.dirname(__file__), 'Datasets', '3_NARONTEC', 'Narontec_2023_hourly.xlsx')

# dico = Values['Narontec']['2024']
# Eautocons, Econs, full_time, deltat = treat_data(path=na2024_path, prod_col=-1, cons_col='Consumo kWh', 
#                                                  date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
#                                                  one_time_col=False, sheet_name=0)
# dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat

# dico = Values['Narontec']['2023']
# Eautocons, Econs, full_time, deltat = treat_data(path=na2023_path, prod_col=-1, cons_col="PLANT CONSUMPTION", 
#                                                  date_cole='DATE', time_col='TIME', format="%d/%m/%Y %H:%M:%S", 
#                                                  one_time_col=False, first_index=1, sheet_name=0)
# dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat


#TMG
#Family 

#%%
def produce_results(full_date, TE, TP, Econs, Eprod, deltat, original):
    
    model, Time_in_month, Nbdays_year = build_model(full_date, definer=2, TE=TE, TP=TP, Econs=Econs, Eautocons=Eprod, deltat=deltat)
    solver = SolverFactory('ipopt')
    # solver.options['print_timing_statistics'] = 'yes'

    for p in range(6) : 
        model.Pprev[p].value = original[p]
    original_price = model.obj()

    res, pena = calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays_year, Time_in_month, deltat, printation=True, sep_pena=True)

    pena_ori = pena()
    results = solver.solve(model, tee=False)

    res, pena = calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays_year, Time_in_month, deltat, printation=True, sep_pena=True)
    pena_opti=pena()

    opti = [model.Pprev[p].value for p in model.period]
    price = model.obj()
    decrease = (original_price - price)/original_price

    def last_day(any_day):
        next_month = any_day.replace(day=28) + dt.timedelta(days=4)
        if any_day.month == 11 :
            return dt.datetime(2024, 11, 20, 23, 59)
        return (next_month - dt.timedelta(days=next_month.day)).replace(hour=23, minute = 59)

    months = range(1, 12) # We don't have data for december
    Tframe = {}

    Origin = []
    Opti = []
    Conso = []
    Prod = []
    Compare = []
    Pena_original =[]
    Pena_opti = []
    results = pd.DataFrame(columns=['Month', 'Original', 'Optimized', 'Pena_origin', 'Pena_opti', 'Consumption', 'Production'])

    for month in months :
        Tframe[month] = (dt.datetime(2024, month, 1, 0, 0), last_day(dt.datetime(2024, month, 1, 0, 0)))
        small, Time_in_month, Nbdays= build_model(Tframe[month], TE=TE, TP=TP, deltat=deltat, Econs=Econs, Eautocons=Eprod)
        Nbdays += 1
        for p in range(6) : 
            small.Pprev[p].value = original[p]
        print("\nMonth %d original" % month)
        res, pena = calculate_price(small.Pprev, small.Pcons, small.Econs, small.Eautocons, small.TP, small.TE, small.TEauto, small.Time, small.tep, small.Kp, Nbdays, Time_in_month, deltat, printation=True, sep_pena=True)
        Origin.append(small.obj())
        Pena_original.append(pena())
        for p in range(6) : 
            small.Pprev[p].value = opti[p]
        print("\nMonth %d opti" % month)
        res, pena = calculate_price(small.Pprev, small.Pcons, small.Econs, small.Eautocons, small.TP, small.TE, small.TEauto, small.Time, small.tep, small.Kp, Nbdays, Time_in_month, deltat, printation=True, sep_pena=True)
        Opti.append(small.obj())
        Pena_opti.append(pena())
        Conso.append(sum([Econs[t] for t in Time_in_month[month]]))
        Prod.append(sum([Eautocons[t] for t in Time_in_month[month]]))
        Compare.append((Origin[-1] - Opti[-1])/Origin[-1])

    results['Month'] = [cal.month_name[month] for month in months]
    results['Original'] = Origin
    results['Optimized'] = Opti
    results['Consumption'] = Conso
    results['Production'] = Prod
    results['Compare'] = Compare
    results['Pena_origin'] = Pena_original
    results['Pena_opti'] = Pena_opti
    results.loc['Total'] = results.sum(numeric_only=True)
    results.loc['Total', 'Month'] = 'Total'
    results.loc['Total', 'Compare'] = (results.loc['Total', 'Original'] - results.loc['Total', 'Optimized'])/results.loc['Total', 'Original']

    # csv_path = 'Results/csv/opti_simple.csv'

    # if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results')) : 
    #     os.mkdir(os.path.join(os.path.dirname(__file__), 'Results'))
    # if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results/csv')) :
    #     os.mkdir(os.path.join(os.path.dirname(__file__), 'Results/csv'))
        
    # results = results.round(3)

    # results.to_csv(csv_path, sep=';', index=False)
    
    return results, decrease, model

for comp in Values : 
    print()
    print(comp)
    TE_comp = Values[comp]['TE']    
    TP_comp = Values[comp]['TP']
    original = Values[comp]['original']
    for year in Values[comp] :
        if year.isnumeric() : 
            print()
            print(year)
            Eautocons = Values[comp][year]['Eautocons']
            Econs = Values[comp][year]['Econs']
            full_time = Values[comp][year]['full_time']
            deltat = Values[comp][year]['deltat']
            results, decrease, model = produce_results(full_time, TE_comp, TP_comp, Econs, Eautocons, deltat, original)
            print(results)
            print()
            print(comp, year, decrease)
            
            
            
        