
import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
from numpy.random import rand
import matplotlib.pyplot as plt 
import pandas as pd

#%%
from prices import define_time, Econs, Eautocons, TEauto, tep, Kp, period_hours, full_date, define_time2
from representative_days import create_data, gen_new_data

# Pcons_new = [val/0.25 for val in Econs_new]
# Pprod_new = [val/0.25 for val in Eprod_new]

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

#%% Model construction

def calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = True) :
    # For it to be faster, we could rewrite this function in a C code and import it 
    # -> it should speed up the evaluation of the objective function
    # Here optimization is fast so not necessary
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    Spena_P = [0.00001 for k in range(6)]
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays
        if opti :  
            time_table = Time[p].value 
        else :
            time_table = Time[p]
        for t in time_table: 
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            # Se += TE[m][p]*(Econs[t]-Eautocons[t])
            Se += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2
            Se_p[p] += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2
            # Seauto += TEauto[p]*Eautocons[t]
            Spena_P[p] += ((Pcons[t] - Pprev[p] + abs(Pcons[t] - Pprev[p]))/2)**2 
            
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
    return Se + Seauto + Spena + Sp


timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 30, 23, 59))
# timeframe =(dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 1, 30, 23, 59))
def build_model(timeframe, definer=1, charge_rate=0.5, decharge_rate=0.5, Effc=0.95, Effd=0.95, Econs=Econs, Eautocons=Eautocons, TP=TP, TE=TE, TEauto=TEauto, tep=tep, Kp=Kp, period_hours=period_hours) :
    Pcons = [val/0.25 for val in Econs]
    if definer == 1 :
        Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
        Nbdays += 1
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    elif definer == 2 :
        Time, Nbdays, Time_in_month = define_time2(timeframe, period_hours)
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    else : 
        raise ValueError("definer must be 1 or 2")
    
    model = pyo.ConcreteModel()
    
    model.period = pyo.RangeSet(0, len(TP)-1)
    model.month = pyo.RangeSet(0, 10)
    model.time = pyo.RangeSet(timerange[0], timerange[1])
    
    model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=[120, 130, 130, 130, 130, 190])
    # model.P_minus_P = pyo.Var(model.period, model.time, domain=pyo.NonNegativeReals, initialize = 0)
    
    model.Pcons = pyo.Param(model.time, initialize={t: Pcons[t] for t in model.time})
    model.Econs = pyo.Param(model.time, initialize={t: Econs[t] for t in model.time})
    model.Eautocons = pyo.Param(model.time, initialize={t: Eautocons[t] for t in model.time})
    model.TP = pyo.Param(model.period, initialize={p: TP[p] for p in model.period})
    model.TE = pyo.Param(model.month, initialize={(m): TE[m] for m in model.month})
    model.TEauto = pyo.Param(model.period, initialize={p: TEauto[p] for p in model.period})
    model.Time = pyo.Param(model.period, initialize={p: Time[p] for p in model.period}, mutable=True)
    model.tep = pyo.Param(initialize=tep)
    model.Kp = pyo.Param(model.period, initialize={p : Kp[p] for p in model.period})
    
    # model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.P_minus_P, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays))
    model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays, Time_in_month))
    
    def Pprev_rule(model, p) : 
        if p == model.period.last() :
            return model.Pprev[p] >= 0
        return model.Pprev[p] <= model.Pprev[p+1]
    model.Pprev_con = pyo.Constraint(model.period, rule=Pprev_rule)
    
    model.Pprev_con1 = pyo.Constraint(expr=model.Pprev[0] >= 0)
    
    return model, Time_in_month, Nbdays


#%% Compare days choices 

def test_method(number_rand=10, number_coef=10, n_init=5) : 
    """
    We will observe two things to test the interest of the methods.
    
    First we will look at how far the optimal objective function will be from the reference model.
    Second we will look at the diminution of the objective function compared to the diminution in the reference model.
    """
    
    results_test_rand = {'quantile': [], 'kmean_max': [], 'kmean_barycenter': [], 'reference': [], 'dim_quantile': [], 'dim_kmean_max': [], 'dim_kmean_barycenter': [], 'dim_reference': []}
    results_test_coef = {'quantile': [], 'kmean_max': [], 'kmean_barycenter': [], 'reference': [], 'dim_quantile': [], 'dim_kmean_max': [], 'dim_kmean_barycenter': [], 'dim_reference': []}
    model_year, Time_in_month, Nbdays = build_model(timeframe)
    no_obj_ref = model_year.obj()
    solver = SolverFactory('ipopt')
    results_ref = solver.solve(model_year, tee=True)
    obj_ref = model_year.obj()
    dim_ref = (no_obj_ref - obj_ref)/no_obj_ref
    for k in range(number_rand + number_coef) :
        if k < number_rand : 
            Econs_test, Eprod_test = gen_new_data(Econs, Eautocons, coef_rand=10)
        else : 
            r = rand()
            coef = 0.5+r*1.5
            Econs_test, Eprod_test = gen_new_data(Econs, Eautocons, coef_rand=0, coef_Econs=coef, coef_Eprod=coef)
        Econs_new1, Eprod_new1, full_date_new1, days1 = create_data(method="quantile", Econs=Econs_test, Eprod=Eprod_test)
        Econs_new2, Eprod_new2, full_date_new2, days2 = create_data(method="year", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test, forced_timeframe=timeframe)
        Econs_new3, Eprod_new3, full_date_new3, days3 = create_data(method="kmean_barycenter", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test)
        
        model1, Time_in_month1, Nbdays1 = build_model(full_date_new1, definer=2, Econs=Econs_new1, Eautocons=Eprod_new1)
        model2, Time_in_month2, Nbdays2 = build_model(full_date_new2, definer=2, Econs=Econs_new2, Eautocons=Eprod_new2)
        model3, Time_in_month3, Nbdays3 = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3)
        
        no_obj1 = model1.obj()
        no_obj2 = model2.obj()
        no_obj3 = model3.obj()
        
        try : 
            results1 = solver.solve(model1, tee=True)
            results2 = solver.solve(model2, tee=True)
            results3 = solver.solve(model3, tee=True)
            
            dim1 = (no_obj1 - model1.obj())/no_obj1
            dim2 = (no_obj2 - model2.obj())/no_obj2
            dim3 = (no_obj3 - model3.obj())/no_obj3
            
            # print('Objective value for reference model : ', model_year.obj())
            # print('Objective value for model 1 : ', model1.obj()*Nbdays/Nbdays1, (model1.obj()*Nbdays/Nbdays1-model_year.obj())/model_year.obj())
            # print('Objective value for model 2 : ', model2.obj()*Nbdays/Nbdays2, (model2.obj()*Nbdays/Nbdays2-model_year.obj())/model_year.obj())
            # print('Objective value for model 3 : ', model3.obj()*Nbdays/Nbdays3, (model3.obj()*Nbdays/Nbdays3-model_year.obj())/model_year.obj())
            if k < number_rand : 
                results_test_rand['quantile'].append((model1.obj()*Nbdays/Nbdays1, (model1.obj()*Nbdays/Nbdays1-model_year.obj())/model_year.obj()))
                results_test_rand['kmean_max'].append((model2.obj()*Nbdays/Nbdays2, (model2.obj()*Nbdays/Nbdays2-model_year.obj())/model_year.obj()))
                results_test_rand['kmean_barycenter'].append((model3.obj()*Nbdays/Nbdays3, (model3.obj()*Nbdays/Nbdays3-model_year.obj())/model_year.obj()))
                results_test_rand['reference'].append((model_year.obj(), 0))
                
                results_test_rand['dim_quantile'].append((dim1, abs(dim1-dim_ref)/dim_ref))
                results_test_rand['dim_kmean_max'].append((dim2, abs(dim2-dim_ref)/dim_ref))
                results_test_rand['dim_kmean_barycenter'].append((dim3, abs(dim3-dim_ref)/dim_ref))
                results_test_rand['dim_reference'].append((dim_ref, 0))
            else : 
                results_test_coef['quantile'].append((model1.obj()*Nbdays/Nbdays1, (model1.obj()*Nbdays/Nbdays1-model_year.obj())/model_year.obj()))
                results_test_coef['kmean_max'].append((model2.obj()*Nbdays/Nbdays2, (model2.obj()*Nbdays/Nbdays2-model_year.obj())/model_year.obj()))
                results_test_coef['kmean_barycenter'].append((model3.obj()*Nbdays/Nbdays3, (model3.obj()*Nbdays/Nbdays3-model_year.obj())/model_year.obj()))
                results_test_coef['reference'].append((model_year.obj(), 0))
                
                results_test_coef['dim_quantile'].append((dim1, abs(dim1-dim_ref)/dim_ref))
                results_test_coef['dim_kmean_max'].append((dim2, abs(dim2-dim_ref)/dim_ref))
                results_test_coef['dim_kmean_barycenter'].append((dim3, abs(dim3-dim_ref)/dim_ref))
                results_test_coef['dim_reference'].append((dim_ref, 0))
                
        except :
            print("ça a raté une fois")
    # And to finish, with the original data
    Econs_test=Econs 
    Eprod_test=Eautocons
    
    Econs_new1, Eprod_new1, full_date_new1, days1 = create_data(method="quantile", Econs=Econs_test, Eprod=Eprod_test)
    Econs_new2, Eprod_new2, full_date_new2, days2 = create_data(method="kmean_max", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test)
    Econs_new3, Eprod_new3, full_date_new3, days3 = create_data(method="kmean_barycenter", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test)
    
    model1, Time_in_month1, Nbdays1 = build_model(full_date_new1, definer=2, Econs=Econs_new1, Eautocons=Eprod_new1)
    model2, Time_in_month2, Nbdays2 = build_model(full_date_new2, definer=2, Econs=Econs_new2, Eautocons=Eprod_new2)
    model3, Time_in_month3, Nbdays3 = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3)
    model_year, Time_in_month, Nbdays = build_model(timeframe, Econs=Econs_test, Eautocons=Eprod_test)
    results_test_rand['reference'].append((model_year.obj(), 0))
    results_test_rand['quantile'].append((model1.obj()*Nbdays/Nbdays1, (model1.obj()*Nbdays/Nbdays1-model_year.obj())/model_year.obj()))
    results_test_rand['kmean_max'].append((model2.obj()*Nbdays/Nbdays2, (model2.obj()*Nbdays/Nbdays2-model_year.obj())/model_year.obj()))
    results_test_rand['kmean_barycenter'].append((model3.obj()*Nbdays/Nbdays3, (model3.obj()*Nbdays/Nbdays3-model_year.obj())/model_year.obj()))
    
    
    FIG = []
    for val in results_test_coef : 
        re = [abs(results_test_coef[val][k][1]) for k in range(len(results_test_coef[val]))]
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
        ax.plot(re, '+', label=val)
        ax.set_thetagrids(())
        ax.plot([0 for k in range(len(re))], 'o', label='reference')
        ax.set_title('test coef %s' % val)
        FIG.append((fig, ax))
        
    for val in results_test_rand : 
        # print(results_test_rand[val][k])
        re = [abs(results_test_rand[val][k][1]) for k in range(len(results_test_rand[val]))]
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
        ax.set_thetagrids(())
        ax.plot(re, '+')
        ax.plot([0 for k in range(len(re))], 'o', label='reference')
        ax.set_title('test rand %s' % val)
        
    plt.show()
    return results_test_coef, results_test_rand, FIG

def search_best_repr(wanted=50, path='Results/csv/best_repr.csv') : 
    Econs_save = []
    Eprod_save = []
    full_date_save = []
    score = 1
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
    model_year, Time_in_month, Nbdays = build_model(timeframe)
    obj_max_ref = model_year.obj()
    solver = SolverFactory('ipopt')
    results_ref = solver.solve(model_year, tee=True)
    obj_ref = model_year.obj()
    
    for k in range(20) : 
        Econs_new3, Eprod_new3, full_date_new3, days3 = create_data(method="year", n_init=1, nb_days=36, forced_timeframe=timeframe, wanted=wanted)
        model3, Time_in_month3, Nbdays3 = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3)
        score_max = abs(model3.obj()-obj_max_ref)/obj_max_ref
        results3 = solver.solve(model3, tee=True)
        obj3 = model3.obj()*Nbdays/Nbdays3
        score_min = abs(obj3-obj_ref)/obj_ref
        score_min_max = score_min*score_max
        current_ratios = [model3.Pprev[p].value/model_year.Pprev[p].value for p in range(6)]
        mean_ratio = sum(current_ratios)/len(current_ratios)
        if abs(mean_ratio-1) < score : 
            score = abs(mean_ratio-1)
            Econs_save = Econs_new3[:]
            Eprod_save = Eprod_new3[:]
            full_date_save = full_date_new3[:]
            score_min_save = score_min 
            score_max_save = score_max
            ratios = current_ratios[:]
            
    
    df = pd.DataFrame(columns=['Econs', 'Eprod', 'full_date'], index=range(len(Econs_save)))
    df['Econs'] = Econs_save
    df['Eprod'] = Eprod_save
    df['full_date'] = full_date_save
    df.to_csv(path, sep=';', index=False)
    return Econs_save, Eprod_save, full_date_save, score_min_save, score_max_save, score, ratios

def search_opti_wanted() :
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
    model_year, Time_in_month, Nbdays = build_model(timeframe)
    solver = SolverFactory('ipopt')
    results_ref = solver.solve(model_year, tee=True)
    obj_ref = model_year.obj()
    score = 0.01
    Finals = []
    for k in range(5) : 
        Econs_new3, Eprod_new3, full_date_new3, days3 = create_data(method="year", n_init=1, nb_days=36, forced_timeframe=timeframe)
        model3, Time_in_month3, Nbdays3 = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3)
        try : 
            results3 = solver.solve(model3, tee=True)
        except : 
            pass
        obj3 = model3.obj()*Nbdays/Nbdays3
        if abs(obj3-obj_ref)/obj_ref < score : 
            score = abs(obj3-obj_ref)/obj_ref
    final_score=score 
    Finals.append(final_score)
    c = 1
    nb_cluster = 36
    while final_score < 0.02 and 50-5*c >= 12: 
        score = 1
        print()
        print(Finals)
        if 50-5*c < nb_cluster : 
            nb_cluster -= 12
        print(nb_cluster, c)
        print()
        for k in range(5) : 
            try : 
                Econs_new3, Eprod_new3, full_date_new3, days3 = create_data(method="year", n_init=1, nb_days=nb_cluster, forced_timeframe=timeframe, wanted=50-5*c)
            except Exception as e:
                print(f"Error occurred: {e}")
                print(f"Parameters: n_init=1, nb_days={nb_cluster}, forced_timeframe={timeframe}, wanted={50-5*c}")
                raise
                
            model3, Time_in_month3, Nbdays3 = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3)
            try : 
                results3 = solver.solve(model3, tee=True)
            except : 
                pass
            obj3 = model3.obj()*Nbdays/Nbdays3
            if abs(obj3-obj_ref)/obj_ref < score : 
                score = abs(obj3-obj_ref)/obj_ref
            final_score = score
        Finals.append(final_score)
        c += 1
        print(50-5*c)
    return Finals
        
    
#%% Simple solve over the year 

timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
model_year, Time_in_month, Nbdays_year = build_model(timeframe)
solver = SolverFactory('ipopt')
solver.options['print_timing_statistics'] = 'yes'
results = solver.solve(model_year, tee=True)

#%% Solver 
TE_test = [[0 for k in range(6)] for i in range(11)]
TE_test=TE 
timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
# model, Time_in_month, Nbdays = build_model(full_date_new, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new) 
Econs_test, Eprod_test = gen_new_data(Econs, Eautocons, coef_rand=0)
Econs_new2, Eprod_new2, full_date_new2, days2 = create_data(method="year", n_init=1, forced_timeframe=timeframe, nb_days=36)

model_year, Time_in_month, Nbdays_year = build_model(timeframe, Econs=Econs_test, Eautocons=Eprod_test, TE=TE_test)
# model = model_year
model, Time_in_month, Nbdays = build_model(full_date_new2, definer=2, Econs=Econs_new2, Eautocons=Eprod_new2, TE=TE_test)
noopti = model.obj()
noopti_year = model_year.obj()
solver = SolverFactory('ipopt')
# solver.options['print_level'] = 
solver.options['print_timing_statistics'] = 'yes'
results = solver.solve(model, tee=True)
# print(model.obj())
results_year = solver.solve(model_year, tee=True)
# model.display()


#%% Show results
"""
On veut récupérer le résultat d'optimisation donc les valeurs de Pprev, On veut le prix total et la comparaison avec le prix actuel, 
et on veut un récapitulatif mois par mois, avec total conso, total prod, prix, et comparaison avec le prix actuel 
"""

opti = [model.Pprev[p].value for p in model.period]
original = [120, 120, 120, 120, 120, 190]
price = model.obj()

original_price = calculate_price(original, Pcons, Econs, Eautocons, TP, TE, TEauto, model.Time, tep, Kp, Nbdays, Time_in_month, opti = True)
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
results = pd.DataFrame(columns=['Month', 'Original', 'Optimized', 'Consumption', 'Production'])

for month in months :
    Tframe[month] = (dt.datetime(2024, month, 1, 0, 0), last_day(dt.datetime(2024, month, 1, 0, 0)))
    Time, Nbdays, Time_in_month = define_time(Tframe[month], period_hours)
    Nbdays += 1
    Opti.append(calculate_price(opti, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = False))
    Origin.append(calculate_price(original, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = False))
    Conso.append(sum([sum(Econs[t] for t in T) for T in Time]))
    Prod.append(sum([sum(Eautocons[t] for t in T) for T in Time]))
    Compare.append((Origin[-1] - Opti[-1])/Origin[-1])

results['Month'] = [cal.month_name[month] for month in months]
results['Original'] = Origin
results['Optimized'] = Opti
results['Consumption'] = Conso
results['Production'] = Prod
results['Compare'] = Compare
results.loc['Total'] = results.sum(numeric_only=True)
results.loc['Total', 'Month'] = 'Total'
results.loc['Total', 'Compare'] = (results.loc['Total', 'Original'] - results.loc['Total', 'Optimized'])/results.loc['Total', 'Original']

csv_path = 'Results/csv/opti_simple.csv'

if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results')) : 
    os.mkdir(os.path.join(os.path.dirname(__file__), 'Results'))
if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results/csv')) :
    os.mkdir(os.path.join(os.path.dirname(__file__), 'Results/csv'))
    
results = results.round(2)

results.to_csv(csv_path, sep=';', index=False)

#%% Verification 

Times = {}
All_nbdays = {}
for month in months : 
    Time, Nbdays, _ = define_time(Tframe[month], period_hours)
    Nbdays += 1
    Times[month] = Time
    All_nbdays[month] = Nbdays

timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))
# timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 3, 31, 23, 59))


Time, Nbdays, _ = define_time(timeframe, period_hours)
Nbdays += 1

# Verifying that Times and Time contains the same values 
Time_reconstructed = [[] for k in range(6)]
for month in months : 
    for p in range(6) : 
        Time_reconstructed[p] += Times[month][p]
        
print(Time == Time_reconstructed)
        
