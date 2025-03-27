"""
This file is written as a python Notebook (but can be imported in other files), each cells are delimited 
by the #%% symbole, then a title explains what the cell does.
"""




import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
from numpy.random import rand
import matplotlib.pyplot as plt 
import pandas as pd
# Define the font size for the plots
plt.rcParams['font.size'] = 20

#%% import values and function from the data treatment 
from prices import define_time, treat_data, TEauto, tep, Kp, period_hours, Eautocons, Econs, full_date, deltat, define_time2, series2lists, increase_deltat
from representative_days import create_data, gen_new_data
from prices_tubacer import TE, TE_new, TP, TP_new
from prices_porto_motor import TE_pm_2024, TP_pm_2024
# full_time = full_date

#%% load representative days 

if __name__ == '__main__' :
    
    path_repr = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'best_repr.csv')
    if not os.path.exists(path_repr) :
        raise ValueError('You must run opti.search_best_repr first')
        
    df = pd.read_csv(path_repr, sep=';', parse_dates=['full_date'])
    
    Econs_repr = series2lists(df['Econs'])
    Eprod_repr = series2lists(df['Eprod'])
    full_date_repr = [df['full_date'][k] for k in range(len(df['full_date']))]
    
    path_repr_div = os.path.join(os.path.dirname(__file__), 'Results', 'csv', 'best_repr.csv')
    if not os.path.exists(path_repr) :
        raise ValueError('You must run opti.search_best_repr first')
        
    df = pd.read_csv(path_repr, sep=';', parse_dates=['full_date'])
    Econs_repr_div = series2lists(df['Econs'])
    Eprod_repr_div = series2lists(df['Eprod'])
    full_date_repr_div = [df['full_date'][k] for k in range(len(df['full_date']))]

#%% Model construction

# Objective function of the problem, can also be called outside of the optimisation if we want to print stuff or evaluate a model in its current step
def calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, deltat, opti = True, printation=False, sep_pena=False) :

    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    # Initialize the penalization at a bit more than 0 because square not differentiable 2 times in 0
    Spena_P = [[0.000000001 for k in range(6)] for i in range(12)]
    
    # Sum over p
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays # Power cost
        # print("power", TP[p], Pprev[p](), Nbdays, (TP[p]*Pprev[p]*Nbdays)())
        if opti :  
            time_table = Time[p].value 
        else :
            time_table = Time[p]
        # Sum over t, separating the months 
        for t in time_table: 
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            # Se += TE[m][p]*(Econs[t]-Eautocons[t])
            Se += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2 # Energy cost
            Se_p[p] += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2
            # Seauto += TEauto[p]*Eautocons[t]
            
            # The penalisation cost is separated for each month
            Spena_P[m][p] += ((Pcons[t]-Eautocons[t]/deltat - Pprev[p] + abs(Pcons[t]-Eautocons[t]/deltat - Pprev[p]))/2)**2 
            
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        # if printation :print("Spena_p", Kp[p], tep, (Spena_P[p])(), (Kp[p]*tep*Spena_P[p])())
        
        # Compute penalization final parts
        for m in range(12) : 
            Spena_P[m][p] = Spena_P[m][p]**(1/2)
        Spena += Kp[p]*tep*sum(Spena_P[m][p] for m in range(12))
    if printation : 
        print("Se", Se)
        print("Seauto", Seauto)
        print("Spena", Spena())
        print("Sp",Sp, Sp())
    if sep_pena :
        # For showing results
        return (Se + Seauto + Spena + Sp), Spena, Se, Sp
    return Se + Seauto + Spena + Sp

# Function for calculating objective function using representative days that can represent several days 
def biased_prices(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, nb_repr, Time_in_month, deltat, opti = True, printation=False) :
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    Spena_P = [[0.000000001 for k in range(6)] for i in range(12)]
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays
        # print("power", TP[p], Pprev[p](), Nbdays, (TP[p]*Pprev[p]*Nbdays)())
        if opti :  
            time_table = Time[p].value 
        else :
            time_table = Time[p]
        for t in time_table: 
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            # Se += TE[m][p]*(Econs[t]-Eautocons[t])
            Se += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2*nb_repr[t]
            Se_p[p] += TE[m][p]*((Econs[t]-Eautocons[t]) + abs(Econs[t]-Eautocons[t]))/2*nb_repr[t]
            # Seauto += TEauto[p]*Eautocons[t]
            Spena_P[m][p] += (((Pcons[t]-Eautocons[t]/deltat - Pprev[p] + abs(Pcons[t]-Eautocons[t]/deltat - Pprev[p]))/2)*nb_repr[t])**2 
            
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        for m in range(12) : 
            Spena_P[m][p] = Spena_P[m][p]**(1/2)
        if printation :print("Spena_p", Kp[p], tep, (Spena_P[p])(), (Kp[p]*tep*Spena_P[p])())
        Spena += Kp[p]*tep*sum(Spena_P[m][p] for m in range(12))
    if printation : 
        print("Se", Se)
        print("Seauto", Seauto)
        print("Spena", Spena())
        print("Sp", Sp())
    return Se + Seauto + Spena + Sp

timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 20, 23, 59))
# timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 30, 23, 59))
# timeframe =(dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 1, 30, 23, 59))

# Function that defines the optimization model
def build_model(timeframe, full_date=full_date, definer=1, Econs=Econs, Eautocons=Eautocons, TP=TP, TE=TE, TEauto=TEauto, tep=tep, Kp=Kp, period_hours=period_hours, deltat=deltat, biased=False, nb_repr=[], Nbdays_forced=None) :
    Pcons = [val/deltat for val in Econs]
    # Defining the time variable that will be needed 
    if definer == 1 :
        Time, Nbdays, Time_in_month = define_time(timeframe, period_hours, full_date=full_date)
        Nbdays += 1
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    elif definer == 2 :
        Time, Nbdays, Time_in_month = define_time2(timeframe, period_hours)
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    else : 
        raise ValueError("definer must be 1 or 2")
        
    if Nbdays_forced : 
        Nbdays = Nbdays_forced
    model = pyo.ConcreteModel()
    
    # Defining the set for indexing
    model.period = pyo.RangeSet(0, len(TP)-1)
    month0 = timeframe[0].month -1
    month1 = timeframe[-1].month - 1
    model.month = pyo.RangeSet(month0, month1)
    model.time = pyo.RangeSet(timerange[0], timerange[1])
    
    # Contracted values variables 
    model.Pprev = pyo.Var(model.period, domain=pyo.NonNegativeReals, initialize=[120, 130, 130, 130, 130, 195])
    # model.P_minus_P = pyo.Var(model.period, model.time, domain=pyo.NonNegativeReals, initialize = 0)
    
    # Parameters 
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
    
    # Objective function 
    if biased and nb_repr: 
        model.obj = pyo.Objective(expr=biased_prices(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays, nb_repr, Time_in_month, deltat))
    else :    
        if biased : print("You forgot the nb_repr list")
        model.obj = pyo.Objective(expr=calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays, Time_in_month, deltat))
    
    # Constraints, the constraints is defined using the Pprev_rule function as a rule.
    def Pprev_rule(model, p) : 
        if p == model.period.last() :
            return model.Pprev[p] >= 0
        return model.Pprev[p] <= model.Pprev[p+1]
    model.Pprev_con = pyo.Constraint(model.period, rule=Pprev_rule)
    
    model.Pprev_con1 = pyo.Constraint(expr=model.Pprev[0] >= 0)
    
    return model, Time_in_month, Nbdays


#%% Compare days choices (typical days related)

def test_method(number_rand=10, number_coef=10, n_init=5, Econs=Econs, Eautocons=Eautocons) : 
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
        Econs_new1, Eprod_new1, full_date_new1, days1, nb_repr1 = create_data(method="quantile", Econs=Econs_test, Eprod=Eprod_test)
        Econs_new2, Eprod_new2, full_date_new2, days2, nb_repr2 = create_data(method="year", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test, forced_timeframe=timeframe)
        Econs_new3, Eprod_new3, full_date_new3, days3, nb_repr3 = create_data(method="kmean_barycenter", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test)
        
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
    
    Econs_new1, Eprod_new1, full_date_new1, days1, nb_repr1 = create_data(method="quantile", Econs=Econs_test, Eprod=Eprod_test)
    Econs_new2, Eprod_new2, full_date_new2, days2, nb_repr2 = create_data(method="kmean_max", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test)
    Econs_new3, Eprod_new3, full_date_new3, days3, nb_repr3 = create_data(method="kmean_barycenter", n_init=n_init, Econs=Econs_test, Eprod=Eprod_test)
    
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

def search_best_repr(Econs, Eprod, TE, TP, wanted=50, path='Results/csv/best_repr.csv') : 
    Econs_save = []
    Eprod_save = []
    full_date_save = []
    score = 1
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
    model_year, Time_in_month, Nbdays = build_model(timeframe, Econs=Econs, Eautocons=Eautocons, TE=TE, TP=TP)
    obj_max_ref = model_year.obj()
    solver = SolverFactory('ipopt')
    results_ref = solver.solve(model_year, tee=True)
    obj_ref = model_year.obj()
    
    for k in range(20) : 
        Econs_new3, Eprod_new3, full_date_new3, days3, nb_repr3 = create_data(method="kmean_max", n_init=1, nb_days=5, forced_timeframe=timeframe, wanted=wanted, Econs=Econs, Eprod=Eprod)
        model3, Time_in_month3, Nbdays3 = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3, TE=TE, TP=TP)
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

def new_test(wanted=50, path="Results/csv/best_repr_div.csv", Econs=Econs, Eprod=Eautocons) :
    timeframe=(dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 11, 0, 1))
    def gen_random_cliped(before) : 
        r = 200*(rand()+0.2)
        if r < before : 
            return before 
        return r
        
    Pprev = [[0, 0, 0, 0, 0, 0] for k in range(20)]
    for k in range(20) :
        for p in range(6) : 
            if p == 0 :
                Pprev[k][p] = gen_random_cliped(0)
            else :
                Pprev[k][p] = gen_random_cliped(Pprev[k][p-1])
                
    model_year, _, Nbdays_year = build_model(timeframe)
    scores = []
    min_score = 1
    for k in range(1) : 
        Econs_new3, Eprod_new3, full_date_new3, days3, nb_repr = create_data(method="quantile", n_init=1, nb_days=35, forced_timeframe=timeframe, wanted=wanted, Econs=Econs, Eprod=Eprod)
        model, _, Nbdays = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3)
        current = []
        
        for i in range(20) : 
            for p in range(6) : 
                model.Pprev[p].value = Pprev[i][p]
                model_year.Pprev[p].value = Pprev[i][p]
            obj_year = model_year.obj()
            obj = model.obj()
            obj = obj*Nbdays_year/Nbdays
            current.append(abs(obj-obj_year)/obj_year)
        current_score = sum(current)/len(current)
        if current_score < min_score : 
            Econs_min, Eprod_min, full_date_min, days_min = Econs_new3[:], Eprod_new3[:], full_date_new3[:], days3[:]
        scores.append(sum(current)/len(current))
        
    df = pd.DataFrame(columns=['Econs', 'Eprod', 'full_date'], index=range(len(Econs_min)))
    df['Econs'] = Econs_min
    df['Eprod'] = Eprod_min
    df['full_date'] = full_date_min
    df.to_csv(path, sep=';', index=False)
    return scores

#%% Simple solve over the year 

if __name__ == '__main__' :
    timeframe = (dt.datetime(2023, 1, 1, 0, 0), dt.datetime(2023, 11, 10, 23, 59))
    # timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
    # model_year, Time_in_month, Nbdays_year = build_model(full_time, definer=2, TE=TE_pm_2024, TP=TP_pm_2024)
    model_year, Time_in_month, Nbdays_year = build_model(timeframe, full_date=full_date, Econs=Econs, Eautocons=Eautocons, deltat=deltat, TE=TE_pm_2024, TP=TP_pm_2024)
    res0 = model_year.obj()
    solver = SolverFactory('ipopt')
    solver.options['print_timing_statistics'] = 'yes'
    results = solver.solve(model_year, tee=True)
    Pprev = [model_year.Pprev[k].value for k in range(6)]
    res = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, printation=True)

#%% Define Porto motor values
if __name__=='__main__' : 
    pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2023.xlsx')
    Eautocons, Econs, full_date, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                     format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
    deltat = deltat[0]
    # Eautocons, Econs, full_date, deltat = increase_deltat(3, Eautocons, Econs, full_date, deltat)
#%% Solver 
if __name__ == '__main__' :
    TE_test = [[0 for k in range(6)] for i in range(11)]
    TE_test=TE 
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
    # model, Time_in_month, Nbdays = build_model(full_date_new, definer=2, Econs=Econs_new, Eautocons=Eprod_new, Pcons=Pcons_new) 
    Econs_test, Eprod_test = gen_new_data(Econs, Eautocons, coef_rand=0)
    Econs_new2, Eprod_new2, full_date_new2, days2 = create_data(method="year", n_init=1, forced_timeframe=timeframe, nb_days=36)

    model_year, Time_in_month, Nbdays_year = build_model(timeframe, Econs=Econs_test, Eautocons=Eprod_test, TE=TE_new, TP=TP_new)
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
if __name__ == '__main__' :
    model, Time_in_month, Nbdays_year = build_model(full_date, definer=2, TE=TE_new, TP=TP_new)
    solver = SolverFactory('ipopt')
    # solver.options['print_timing_statistics'] = 'yes'



    original = [120, 130, 130, 130, 130, 195]
    for p in range(6) : 
        model.Pprev[p].value = original[p]
    original_price = model.obj()

    res, pena = calculate_price(model.Pprev, model.Pcons, model.Econs, model.Eautocons, model.TP, model.TE, model.TEauto, model.Time, model.tep, model.Kp, Nbdays_year, Time_in_month, deltat, printation=True, sep_pena=True)

    pena_ori = pena()
    results = solver.solve(model, tee=True)

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
        small, Time_in_month, Nbdays= build_model(Tframe[month], TE=TE_new, TP=TP_new)
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

    csv_path = 'Results/csv/opti_simple.csv'

    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results')) : 
        os.mkdir(os.path.join(os.path.dirname(__file__), 'Results'))
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'Results/csv')) :
        os.mkdir(os.path.join(os.path.dirname(__file__), 'Results/csv'))
        
    results = results.round(3)

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
            
    #%% Representative tests
if __name__ == '__main__' :
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 11, 0, 1))
    nb_days = 100
    # timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 2, 1, 0, 1))
    # nb_days = 5
    Econs_new3, Eprod_new3, full_date_new3, days3, nb_repr = create_data(method="year_barycenter", n_init=1, nb_days=nb_days, forced_timeframe=timeframe, wanted=50)

    nb_repr_t = [None for k in range(len(full_date_new3))]
    k = 0
    date0 = days3[0]
    for t in range(len(full_date_new3)) : 
        if full_date_new3[t].date() == date0 :
            nb_repr_t[t] = nb_repr[k]
        else : 
            print(t, k)
            nb_repr_t[t] = nb_repr[k]
            k += 1
            try : date0 = days3[k]
            except : break
            
    model, _, Nbdays = build_model(full_date_new3, definer=2, Econs=Econs_new3, Eautocons=Eprod_new3, biased=True, nb_repr=nb_repr_t)
            
    # solver = SolverFactory('ipopt')
    # solver.options['print_timing_statistics'] = 'yes'
    # results = solver.solve(model, tee=True)
    timeframe = (dt.datetime(2024, 1, 1, 0, 0), dt.datetime(2024, 11, 10, 23, 59))
    # timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
    model_year, Time_in_month, Nbdays_year = build_model(timeframe)
    solver = SolverFactory('ipopt')
    solver.options['print_timing_statistics'] = 'yes'
    results = solver.solve(model_year, tee=True)
    Pprev = [model_year.Pprev[k].value for k in range(6)]
    res = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, printation=True)


    for p in range(6) : 
        model.Pprev[p].value = Pprev[p]
        
    #%% Biased test
if __name__ == '__main__' :
    nb_repr = []
    for k in range(len(Econs_repr_div)) : 
        nb_repr.append(6)
    model, _, Nbdays = build_model(full_date_repr_div, definer=2, Econs=Econs_repr_div, Eautocons=Eprod_repr_div, biased=True, nb_repr=nb_repr)

        
    solver = SolverFactory('ipopt')
    solver.options['print_level'] = 7
    results = solver.solve(model, tee=True)
    
#%% Plot opti interest Tubacer
if __name__ == '__main__' : 
    
    Eautocons, Econs, full_time, deltat = treat_data(name="TUBACER")
    timerange = (full_time[0], dt.datetime(2024, 10, 31, 23, 59))

    model_year, Time_in_month, Nbdays_year = build_model(timerange, full_date=full_time, TE=TE, TP=TP, Econs=Econs, Eautocons=Eautocons)
    res0 = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, printation=True)()
    solver = SolverFactory('ipopt')
    solver.options['print_timing_statistics'] = 'yes'
    results = solver.solve(model_year, tee=True)
    Pprev = [model_year.Pprev[k].value for k in range(6)]
    res = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, printation=True)

    # from multidim_poly_fit import *
    import numpy as np
    opti = Pprev
    original = [120, 130, 130, 130, 130, 195]
    too_much = [200, 200, 200, 200, 200, 200]
    n = 15
    values = [list(np.linspace(original[p], opti[p], n//2)) for p in range(6)]
    values = [values[p] + list(np.linspace(opti[p], too_much[p], n//2)) for p in range(6)]
    n = (n//2)*2
    Pena_prices = []
    Power_prices = []
    for k in range(n) : 
        for p in range(6) : 
            model_year.Pprev[p].value = values[p][k]
        res, pena, se, sp = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, sep_pena=True)
        Pena_prices.append(pena() if not isinstance(pena, float) else pena)
        Power_prices.append(sp() if not isinstance(sp, float) else sp)
    
    fig, ax = plt.subplots()
    ax.plot(Pena_prices, Power_prices, '+', markersize=20)
    ax.plot(Pena_prices[0], Power_prices[0], '+', color='orange', markersize=20)
    ax.plot(Pena_prices[-1], Power_prices[-1], '+', color='orange', markersize=20)
    ax.plot(Pena_prices[n//2], Power_prices[n//2], 'o', color='orange', markersize=20)
    tup = str(tuple(round(val) for val in opti)).replace(' ', '')
    ax.annotate(f'Optimal contracted power : {tup}\nContracted power + penalization cost : {round(Pena_prices[n//2]+Power_prices[n//2])} €', xy=(Pena_prices[n//2], Power_prices[n//2]), xytext=(Pena_prices[n//2]+200, Power_prices[n//2]+200))
    tup = str(tuple(round(val) for val in original)).replace(' ', '')
    ax.annotate(f'Original contracted power : {tup}\nContracted power + penalization cost : {round(Pena_prices[0]+Power_prices[0])} €', xy=(Pena_prices[0], Power_prices[0]), xytext=(Pena_prices[0] - 1000, Power_prices[0]+200))
    tup = str(tuple(round(val) for val in too_much)).replace(' ', '')
    ax.annotate(f'Over-contracted power : {tup}\nContracted power + penalization cost : {round(Pena_prices[-1]+Power_prices[-1])} €', xy=(Pena_prices[-1], Power_prices[-1]), xytext=(Pena_prices[-1]+300, Power_prices[-1] - 200))
    ax.set_xlabel('Yearly penalization cost (€)')
    ax.set_ylabel('Yearly contracted power cost (€)')
    ax.set_xlim(-200, 15400)
    plt.show()
        
#%% Same for Porto motor

if __name__ == '__main__' : 
    pm2024_path = os.path.join(os.path.dirname(__file__), 'Datasets', '2_PORTOMOTOR', 'Porto Motor_2024.xlsx')
    Eautocons, Econs, full_time, deltat = treat_data(path=pm2024_path, prod_col='Producción fotovoltaica', cons_col='Consumo', first_index=1,
                                                 format="%d.%m.%Y %H:%M", date_col="Fecha y hora", one_time_col=True, sheet_name=0, fac=1/1000)
    full_date = full_time
    deltat = deltat[0]
    timerange = (full_time[0], dt.datetime(2024, 10, 31, 23, 59))
    
    model_year, Time_in_month, Nbdays_year = build_model(timerange, full_date=full_time, TE=TE_pm_2024, TP=TP_pm_2024, Econs=Econs, Eautocons=Eautocons, deltat=deltat)
    res0 = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, printation=True)()
    solver = SolverFactory('ipopt')
    solver.options['print_timing_statistics'] = 'yes'
    results = solver.solve(model_year, tee=True)
    Pprev = [model_year.Pprev[k].value for k in range(6)]
    res = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, printation=True)

    import numpy as np
    opti = Pprev
    original = [35, 35, 35, 35, 35, 35]
    not_so_much = [15, 15, 15, 15, 15, 15]
    n = 15
    values = [list(np.linspace(original[p], opti[p], n//2)) for p in range(6)]
    values = [values[p] + list(np.linspace(opti[p], not_so_much[p], n//2)) for p in range(6)]
    n = (n//2)*2
    Pena_prices = []
    Power_prices = []
    for k in range(n) : 
        for p in range(6) : 
            model_year.Pprev[p].value = values[p][k]
        res, pena, se, sp = calculate_price(model_year.Pprev, model_year.Pcons, model_year.Econs, model_year.Eautocons, model_year.TP, model_year.TE, model_year.TEauto, model_year.Time, model_year.tep, model_year.Kp, Nbdays_year, Time_in_month, deltat, sep_pena=True)
        Pena_prices.append(pena() if not isinstance(pena, float) else pena)
        Power_prices.append(sp() if not isinstance(sp, float) else sp)
    
    
    fig, ax = plt.subplots()
    ax.plot(Pena_prices, Power_prices, '+', markersize=20)
    ax.plot(Pena_prices[0], Power_prices[0], '+', color='orange', markersize=20)
    ax.plot(Pena_prices[-1], Power_prices[-1], '+', color='orange', markersize=20)
    ax.plot(Pena_prices[n//2], Power_prices[n//2], 'o', color='orange', markersize=20)
    tup = str(tuple(round(val) for val in opti)).replace(' ', '')
    ax.annotate(f'Optimal contracted power : {tup}\nContracted power + penalization cost : {round(Pena_prices[n//2]+Power_prices[n//2])} €', xy=(Pena_prices[n//2], Power_prices[n//2]), xytext=(Pena_prices[n//2]+100, Power_prices[n//2]-20))
    tup = str(tuple(round(val) for val in original)).replace(' ', '')
    ax.annotate(f'Original contracted power : {tup}\nContracted power + penalization cost : {round(Pena_prices[0]+Power_prices[0])} €', xy=(Pena_prices[0], Power_prices[0]), xytext=(Pena_prices[0]+100, Power_prices[0]))
    tup = str(tuple(round(val) for val in not_so_much)).replace(' ', '')
    ax.annotate(f'Under-contracted power : {tup}\nContracted power + penalization cost : {round(Pena_prices[-1]+Power_prices[-1])} €', xy=(Pena_prices[-1], Power_prices[-1]), xytext=(Pena_prices[-1]-230, Power_prices[-1]+50))
    ax.set_xlabel('Yearly penalization cost (€)')
    ax.set_ylabel('Yearly contracted power cost (€)')
    ax.set_xlim(-100, 2400)
    ax.set_ylim(550, 1550)
    plt.show()