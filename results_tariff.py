from prices_tubacer import TE, TE_new, TP, TP_new
from prices_porto_motor import TE_pm_2024, TP_pm_2024
from prices_TMG import TE_TMG, TP_TMG
from prices import treat_data, define_time, define_time2
from opti import build_model, calculate_price, period_hours
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
Values['TMG']['TE'] = TE_TMG
Values['TMG']['TP'] = TP_TMG
Values['TMG']['original'] = [155, 155, 155, 155, 155, 195]

Values['Tubacer']['2024'] = {}
Values['Porto Motor']['2024'] = {}
Values['Porto Motor']['2023'] = {}
Values['Narontec']['2024'] = {}
Values['Narontec']['2023'] = {}
Values['TMG']['2024'] = {}

""" 
Eautocons or Eprod is the produced energy 
Econs is the consumed energy
full_time is a list of datetime objects 
-> All should be indexed over a same index, so Eprod[0] = produced energy at full_time[0] (and same with Econs)
See the docstring of the function treat_data for more information
"""

#Tubacer
Eautocons, Econs, full_time, deltat = treat_data(name="TUBACER")
dico = Values['Tubacer']['2024']
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat

#Porto Motor
pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
pm2023_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2023.xlsx')
#%%
Eautocons, Econs, full_time, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
dico = Values['Porto Motor']['2024'] 
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]

Eautocons, Econs, full_time, deltat = treat_data(path=pm2023_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
dico = Values['Porto Motor']['2023']
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]

#%%Narontec
na2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '3_NARONTEC', 'Curvas_carga_Narontec_2024.xlsx')
na2023_path = os.path.join(os.path.dirname(__file__), 'Datasets', '3_NARONTEC', 'Narontec_2023_hourly.xlsx')

dico = Values['Narontec']['2024']

Eautocons, Econs, full_time, deltat = treat_data(path=na2024_path, prod_col=-1, cons_col='Consumo kWh', 
                                                 date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
                                                 one_time_col=False, sheet_name=0)
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]

dico = Values['Narontec']['2023']
Eautocons, Econs, full_time, deltat = treat_data(path=na2023_path, prod_col=-1, cons_col="PLANT CONSUMPTION", 
                                                 date_col='DATE', time_col='TIME', format="%d/%m/%Y 00:%H:%M", 
                                                 one_time_col=False, first_index=1, sheet_name=0, fac=1)
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]


#TMG
tmg_path = os.path.join(os.path.dirname(__file__), 'Datasets', '4_TMG', 'Curvas_TMG_2024.xlsx')
dico = Values['TMG']['2024']
Eautocons, Econs, full_time, deltat = treat_data(path=tmg_path, prod_col=-1, cons_col='Consumo kWh', 
                                                 date_col='Fecha', time_col='Hora', format="%d/%m/%Y %H", 
                                                 one_time_col=False, sheet_name=0)
dico['Eautocons'], dico['Econs'], dico['full_time'], dico['deltat'] = Eautocons, Econs, full_time, deltat[0]


#Family 

#%%
def produce_results(full_date, TE, TP, Econs, Eprod, deltat, original, opti_prev):
    
    model, Time_in_month, Nbdays_year = build_model(full_date, definer=2, TE=TE, TP=TP, Econs=Econs, Eautocons=Eprod, deltat=deltat)
    solver = SolverFactory('ipopt')
    # solver.options['print_timing_statistics'] = 'yes'

    for p in range(6) : 
        model.Pprev[p].value = original[p]
    original_price = model.obj()

    res, pena, _, _ = calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays_year, Time_in_month, deltat, printation=True, sep_pena=True)

    pena_ori = pena()
    results = solver.solve(model, tee=False)

    res, pena, _, _ = calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays_year, Time_in_month, deltat, printation=True, sep_pena=True)
    pena_opti=pena()

    opti = [model.Pprev[p].value for p in model.period]
    price = model.obj()
    decrease = (original_price - price)/original_price
    if opti_prev == [] : 
        opti_prev = original[:]
    def last_day(any_day, last_time):
        next_month = any_day.replace(day=28) + dt.timedelta(days=4)
        if any_day.month == last_time.month :
            return last_time
        return (next_month - dt.timedelta(days=next_month.day)).replace(hour=23, minute = 59)
    
    first_month = full_date[0].month
    last_month = full_date[-1].month
    last_time = full_date[-1]
    year = full_date[0].year
    months = range(first_month, last_month) # We don't have data for december
    Tframe = {}

    Origin = []
    Opti = []
    Opti_prev = []
    Conso = []
    Prod = []
    Compare = []
    Pena_original =[]
    Pena_opti = []
    Power_original = []
    Power_opti = []
    results = pd.DataFrame(columns=['Month', 'Original', 'Optimized', 'Oldptimized', 'Pena_origin', 'Pena_opti', 'Consumption', 'Production', 'Compare', 'Compare old'])

    for month in months :
        Tframe[month] = (dt.datetime(year, month, 1, 0, 0), last_day(dt.datetime(year, month, 1, 0, 0), last_time))
        print("Tframe", Tframe[month])
        small, Time_in_month, Nbdays= build_model(Tframe[month], full_date=full_date, TE=TE, TP=TP, deltat=deltat, Econs=Econs, Eautocons=Eprod)
        Nbdays += 1
        for p in range(6) : 
            small.Pprev[p].value = original[p]
        print("\nMonth %d original" % month)
        res, pena, _, sp = calculate_price(small.Pprev, small.Pcons, small.Econs, small.Eautocons, small.TP, small.TE, small.TEauto, small.Time, small.tep, small.Kp, Nbdays, Time_in_month, deltat, printation=True, sep_pena=True)
        Origin.append(small.obj())
        Pena_original.append(pena())
        Power_original.append(sp() if sp is not isinstance(sp, float) else sp)
        for p in range(6) : 
            small.Pprev[p].value = opti[p]
        print("\nMonth %d opti" % month)
        res, pena, _, sp = calculate_price(small.Pprev, small.Pcons, small.Econs, small.Eautocons, small.TP, small.TE, small.TEauto, small.Time, small.tep, small.Kp, Nbdays, Time_in_month, deltat, printation=True, sep_pena=True)
        Opti.append(small.obj())
        Pena_opti.append(pena())
        Power_opti.append(sp() if sp is not isinstance(sp, float) else sp)
        for p in range(6) : 
            small.Pprev[p].value = opti_prev[p]
        Opti_prev.append(small.obj())
        Conso.append(sum([Econs[t] for t in Time_in_month[month]]))
        Prod.append(sum([Eautocons[t] for t in Time_in_month[month]]))
        Compare.append((Origin[-1] - Opti[-1])/Origin[-1])

    results['Month'] = [cal.month_name[month] for month in months]
    results['Original'] = Origin
    results['Optimized'] = Opti
    results['Oldptimized'] = Opti_prev
    results['Consumption'] = Conso
    results['Production'] = Prod
    results['Compare'] = Compare
    results['Pena_origin'] = Pena_original
    results['Pena_opti'] = Pena_opti
    results['Power_origin'] = Power_original
    results['Power_opti'] = Power_opti
    results.loc['Total'] = results.sum(numeric_only=True)
    results.loc['Total', 'Month'] = 'Total'
    results.loc['Total', 'Compare'] = (results.loc['Total', 'Original'] - results.loc['Total', 'Optimized'])/results.loc['Total', 'Original']
    results.loc['Total', 'Compare old'] = (results.loc['Total', 'Oldptimized'] - results.loc['Total', 'Optimized'])/results.loc['Total', 'Oldptimized']
    # csv_path = 'Results/csv/opti_simple.csv'

    # if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results')) : 
    #     os.mkdir(os.path.join(os.path.dirname(__file__), 'Results'))
    # if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results/csv')) :
    #     os.mkdir(os.path.join(os.path.dirname(__file__), 'Results/csv'))
        
    # results = results.round(3)

    # results.to_csv(csv_path, sep=';', index=False)
    
    return results, decrease, model


def compute(comp, year, opti_prev=[]) : 
    # try : 
    Eautocons = Values[comp][year]['Eautocons']
    Econs = Values[comp][year]['Econs']
    full_time = Values[comp][year]['full_time']
    deltat = Values[comp][year]['deltat']
    results, decrease, model = produce_results(full_time, TE_comp, TP_comp, Econs, Eautocons, deltat, original, opti_prev)
    print(results)
    print()
    print(comp, year, decrease)
    Values[comp][year]['result'] = results
    # except Exception as e :
    #     print()
    #     print(e)
    #     print()
    #     print("On a bugué sur %s %s" % (comp, year))
    return model

for comp in Values : 
    print()
    print(comp)
    if Values[comp] : 
        TE_comp = Values[comp]['TE']    
        TP_comp = Values[comp]['TP']
        original = Values[comp]['original']
        if '2023' in Values[comp] : 
            mod = compute(comp, '2023')
            opti_prev = [mod.Pprev[p].value for p in range(6)]
            Values[comp]['2023']['Pprev'] = opti_prev[:]
            mod2 = compute(comp, '2024', opti_prev = opti_prev)
            opti = [mod2.Pprev[p].value for p in range(6)]
            Values[comp]['2024']['Pprev'] = opti[:]
        else : 
            mod = compute(comp, '2024', opti_prev = [])
            opti = [mod.Pprev[p].value for p in range(6)]
            Values[comp]['2024']['Pprev'] = opti[:]
                    
#%% Save results 

path = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'Pcontracted_opti.csv')

with open(path, 'w') :
    print("clean up file %s" % path)
    
for comp in Values :
    for year in Values[comp] :
        if year.isnumeric() : 
            results = Values[comp][year].get('result')
            if results is not None: 
                results['Compare'] = 100*results['Compare']
                results['Compare old'] = 100*results['Compare old']
                results = results.round(1)
                with open(path, 'a') as f : 
                    f.write(comp + ' ' + year + '\n')
                results.to_csv(path, mode='a', sep=';', index=False)
                with open(path, 'a') as f : 
                    f.write('\n\n')
            
#%%
path = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'Pcontracted_values.csv')
with open(path, 'w') :
    print("clean up file %s" % path)
for comp in Values : 
    for year in Values[comp] : 
        if year.isnumeric() : 
            with open(path, 'a') as f :
                f.write(comp + ' ' + year + '\n')
                for p in range(6) : 
                    f.write(f'P{p+1} {Values[comp][year]["Pprev"][p]:.1f}\n')
                f.write('\n\n')
            
#%%

data = {}
for comp in Values : 
    if Values[comp] : 
        data[comp] = {}
        data[comp]['Optimal (kW)'] = Values[comp]['2024']['Pprev'][:]
        data[comp]['Original (kW)'] = Values[comp]['original'][:]
        diffs = []
        for k in range(6) :
            diff = -Values[comp]['original'][k] +Values[comp]['2024']['Pprev'][k]
            if diff > 0 : 
                diffs.append(f'+{diff:.1f}')
            else :
                diffs.append(f'{diff:.1f}')
        data[comp]['Difference (kW)'] = diffs
    
columns_sup = [comp for comp in Values]
columns_inf = ['Optimal (kW)', 'Original (kW)', 'Difference (kW)']
dfs = []
for comp in data : 
    columns = pd.MultiIndex.from_product([[comp], columns_inf])
    df = pd.DataFrame(columns=columns)
    for col in columns : 
        if data.get(col[0]) :
            df[col] = data[comp][col[1]]
    df.index = [f'P{k+1}' for k in range(6)]
    dfs.append(df)
# columns = pd.MultiIndex.from_product([columns_sup, columns_inf])
# index = [f'P{k+1}' for k in range(6)]
# df = pd.DataFrame(columns=columns)

# for col in columns : 
#     if data.get(col[0]) : 
#         df[col] = data[col[0]][col[1]]
    
# df.index = index

# styled_df = df.style.format(precision=1).set_caption("Contracted Power Comparison").set_table_styles(overwrite=False)

# Convert the styled DataFrame to LaTeX
# latex_table = styled_df.to_latex(hrules=True)

# Write the LaTeX table to a file
Styler = {
    }
with open('output_table.tex', 'w') as f:
    c = 0
    for df in dfs : 
        if not c :
            styled_df = df.style.format(precision=1).set_caption("Contracted Power Comparison").set_table_styles(Styler, overwrite=False)
            c += 1
        else :
            styled_df = df.style.format(precision=1).set_table_styles(Styler, overwrite=False)
        latex_table = styled_df.to_latex(column_format="|c|c|c|c|", position='center')
        f.write(latex_table+"\n")

#%% Latex table for costs

columns = ['Company', 'Original cost (€)', 'Optimized cost (€)', 'Decrease (%)']
data = {}
data['Company'] = ['Tubacer 2024', 'Porto Motor 2024', 'Porto Motor 2023', 'Narontec 2024', 'Narontec 2023', 'TMG 2024']
data['Original cost (€)'] = [Values['Tubacer']['2024']['result'].loc['Total', 'Original'], 
                             Values['Porto Motor']['2024']['result'].loc['Total', 'Original'], 
                             Values['Porto Motor']['2023']['result'].loc['Total', 'Original'],
                             Values['Narontec']['2024']['result'].loc['Total', 'Original'], 
                             Values['Narontec']['2023']['result'].loc['Total', 'Original'], 
                             Values['TMG']['2024']['result'].loc['Total', 'Original'], 
                             ]
data['Optimized cost (€)'] = [Values['Tubacer']['2024']['result'].loc['Total', 'Optimized'],
                              Values['Porto Motor']['2024']['result'].loc['Total', 'Optimized'],
                              Values['Porto Motor']['2023']['result'].loc['Total', 'Optimized'],
                              Values['Narontec']['2024']['result'].loc['Total', 'Optimized'],
                              Values['Narontec']['2023']['result'].loc['Total', 'Optimized'],
                              Values['TMG']['2024']['result'].loc['Total', 'Optimized']
                              ]
data['Decrease (%)'] = [Values['Tubacer']['2024']['result'].loc['Total', 'Compare'],
                        Values['Porto Motor']['2024']['result'].loc['Total', 'Compare'],
                        Values['Porto Motor']['2023']['result'].loc['Total', 'Compare'],
                        Values['Narontec']['2024']['result'].loc['Total', 'Compare'],
                        Values['Narontec']['2023']['result'].loc['Total', 'Compare'],
                        Values['TMG']['2024']['result'].loc['Total', 'Compare']
                        ]

df = pd.DataFrame(data=data, columns=columns)
df['Decrease (%)'] = df['Decrease (%)']*100
df['Decrease (%)'] = df['Decrease (%)'].round(2).map('{:,.2f}'.format)
df['Original cost (€)'] = df['Original cost (€)'].round(-1).map('{:,.0f}'.format)
df['Optimized cost (€)'] = df['Optimized cost (€)'].round(-1).map('{:,.0f}'.format)
styled_df = df.style.set_caption("Total cost comparison").set_table_styles(Styler, overwrite=False)
latex_table = styled_df.to_latex(column_format="|c|c|c|c|", position='center')
with open('output_table_costs.tex', 'w') as f:
    f.write(latex_table)

#%% Plot mean load and PV 

from representative_days import separate_days

for comp in Values : 
    if Values[comp] :  
        for year in Values[comp] : 
            if year.isnumeric() : 
                Eautocons = Values[comp][year]['Eautocons']
                Econs = Values[comp][year]['Econs']
                full_time = Values[comp][year]['full_time']
                TE_comp = Values[comp]['TE']    
                # TP_comp = Values[comp]['TP']
                Days = separate_days(Econs, Eautocons, full_time, TE=TE_comp)
                mean_Econs = [0 for k in range(len(Days[0]['Econs']))]
                mean_Eprod = [0 for k in range(len(Days[0]['Eprod']))]
                nb_val = [0 for k in range(len(Days[0]['Econs']))]
                print(comp, year)
                for i in range(len(Days)) : 
                    for t in range(len(Days[i]['Econs'])) : 
                        print(i, len(Days[i]['Econs']))
                        print(t, len(mean_Econs))
                        mean_Econs[t] += Days[i]['Econs'][t]
                        mean_Eprod[t] += Days[i]['Eprod'][t]
                        nb_val[t] += 1
                for t in range(len(Days[0]['Econs'])) :
                    mean_Econs[t] /= nb_val[t]
                    mean_Eprod[t] /= nb_val[t]
                Values[comp][year]['mean_Econs'] = mean_Econs
                Values[comp][year]['mean_Eprod'] = mean_Eprod
                                    
        


            
        