import datetime as dt
import calendar as cal
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import os 
import matplotlib.pyplot as plt
import numpy as np 
import numpy.random as rd

#%%
from prices import define_time, Econs, Eautocons, TEauto, tep, Kp, period_hours, full_date, define_time2
from representative_days import Econs_new, Eprod_new, full_date_new, days

Pcons_new = [val/0.25 for val in Econs_new]
Pprod_new = [val/0.25 for val in Eprod_new]

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

# For the moment, for the battery we will take values that looks ok, but with not so many reasearch behind.

# Emax = 30 # kwh
# Emin = 0.2*Emax*0
charge_rate = 0.5 
discharge_rate = 0.5
Effc = 0.95 # Efficiency, we count the conversion losses, do we need to lessen the losses if come from PV ? Maybe
Effd = 0.95 # order of magnitude, need to be looked into.

#%%

from time import time

class Model : 
    def __init__(self, Var, **kwargs) : 
        self.Var = Var
        self.Param = set()
        for key, value in kwargs.items():
            if key in Var : 
                try : 
                    setattr(self, key, np.zeros(len(value)))
                except : 
                    setattr(self, key, np.zeros(1))
                setattr(self, key+'_parameter', value)
            elif isinstance(value, (int, float)) : 
                setattr(self, key, value)
                self.Param.add(key)
            else : 
                try : 
                    setattr(self, key, np.array(value))
                except : 
                    setattr(self, key, value) # Should be useful only for Time in month
                self.Param.add(key)
                    
        self.opti_bounds = {var : [-np.inf, np.inf] for var in self.Var} 
        
    def detailed_obj(self, pl, pq) : 
        detail = {}
        total = 0
        Egrid = self.Econs - self.Eprod + ((self.Pb > 0)*self.charge_rate*self.Pb - (self.Pb < 0)*self.Pb/self.discharge_rate)*self.deltat
        tot_egrid = 0
        for month in self.months : 
            for p in self.periods : 
                for t in self.time_month[month][p] : 
                    if Egrid[t] > 0 :
                        total += self.TE[month][p]*Egrid[t]
                        tot_egrid += self.TE[month][p]*Egrid[t]
        detail['Egrid'] = tot_egrid
        
        tot_pena = 0
        for p in self.periods : 
            total += self.TP[p]*self.Pprev[p]*self.Nbdays
            st = 0
            for t in self.time[p] : 
                val = Egrid[t]/self.deltat - self.Pprev[p]
                if val > 0 : 
                    st+=val**2
            total += self.Kp[p]*self.tep*st**(1/2)
            tot_pena += self.Kp[p]*self.tep*st**(1/2)
        
        detail['pena'] = tot_pena
        
        total += self.Cb*(self.TB/self.batterie_life + self.TBm) * self.Nbdays/365
        
        # Constraints penalisation cost for lower and upper bound
        
        constraint_cost = 0
        for t in self.tot_time[:-1] : 
            self.SOC[t+1] = self.Pb[t]*self.deltat
            constraint_cost += self.penalty_bound_elem(self.SOC[t+1], 0.2*self.Cb, self.Cb, pl, pq)
            detail[f'SOC[{t}+1]'] = self.penalty_bound_elem(self.SOC[t+1], 0.2*self.Cb, self.Cb, pl, pq)
        
        val = self.penalty_bound(self.Pb, -self.discharge_rate*self.Cb, self.charge_rate*self.Cb, pl, pq)
        constraint_cost += val
        detail['Pb'] = val
        
        for p in self.periods[:-1]: 
            constraint_cost += self.penalty_bound_elem(self.Pprev[p], 0, self.Pprev[p+1], pl, pq)
            detail['Pprev[%d]'%p] = self.penalty_bound_elem(self.Pprev[p], 0, self.Pprev[p+1], pl, pq)
        
        return total + constraint_cost, total, constraint_cost, detail
    
    def obj(self, pl, pq):
        total = 0
        Egrid = self.Econs - self.Eprod + ((self.Pb > 0) * self.charge_rate * self.Pb - (self.Pb < 0) * self.Pb / self.discharge_rate) * self.deltat
        for month in self.months:
            for p in self.periods:
                for t in self.time_month[month][p]:
                    if Egrid[t] > 0:
                        total += self.TE[month][p] * Egrid[t]

        for p in self.periods:
            total += self.TP[p] * self.Pprev[p] * self.Nbdays
            st = 0
            for t in self.time[p]:
                val = Egrid[t] / self.deltat - self.Pprev[p]
                if val > 0:
                    st += val ** 2
            total += self.Kp[p] * self.tep * st ** (1 / 2)

        total += self.Cb * (self.TB / self.batterie_life + self.TBm) * self.Nbdays / 365

        # Constraints penalisation cost for lower and upper bound
        constraint_cost = 0
        for t in self.tot_time[:-1]:
            self.SOC[t + 1] = self.Pb[t] * self.deltat
            constraint_cost += self.penalty_bound_elem(self.SOC[t + 1], 0.2 * self.Cb, self.Cb, pl, pq)

        val = self.penalty_bound(self.Pb, -self.discharge_rate * self.Cb, self.charge_rate * self.Cb, pl, pq)
        constraint_cost += val

        for p in self.periods[:-1]:
            constraint_cost += self.penalty_bound_elem(self.Pprev[p], 0, self.Pprev[p + 1], pl, pq)

        return total + constraint_cost, total, constraint_cost
            
    def penalty_bound(self, var, varlb, varub, pl, pq) : 
        # Take into account an array
        penalty = (varlb - var[var < varlb]).sum() + (var[var > varub] - varub).sum()
        total_penalty = penalty * pl + penalty ** 2 * pq
        return total_penalty
    
    def penalty_bound_elem(self, var, varlb, varub, pl, pq) :
        # single element 
        penalty = (varlb - var)*(varlb-var>0) + (var - varub)*(var-varub>0)
        total_penalty = penalty * pl + penalty ** 2 * pq
        return total_penalty
    
    def set_bounds(self, var, lb, ub) : 
        if isinstance(var, list) : 
            for k in range(len(var)) :
                self.opti_bounds[var[k]] = [lb[k], ub[k]]
        else :
            self.opti_bounds[var] = [lb, ub]
        
        
class Individual(Model) : 
    # Represent one individual/particle/thing of the model
    def __init__(self, model, pl=1, pq=1, pso=False) : 
        for param in model.Param : 
            setattr(self, param, getattr(model, param)) 
            # This is not a copy so it is really fast and does not change anything in term of memory
        self.opti_bounds = model.opti_bounds
        self.Var = model.Var
        for var in model.Var : 
            tab = (rd.rand(*getattr(model, var).shape) * (model.opti_bounds[var][1] - model.opti_bounds[var][0]) + model.opti_bounds[var][0])
            setattr(self, var, tab)
            if pso :
                tab = (rd.rand(*getattr(model, var).shape) -0.5) * (model.opti_bounds[var][1] - model.opti_bounds[var][0]) * 2
                setattr(self, var+'__v', tab)
 
        self.pl = pl 
        self.pq = pq
        self.fitness = self.obj(pl, pq)[0][0]
        if pso : 
            self.best = Individual(model, pl, pq)
            self.best = self.best.copy_var(self)
            self.best.fitness=self.fitness
            
            
    def copy_var(self, indiv) : 
        for var in self.Var : 
            setattr(self, var, getattr(indiv, var)[:])


def no_evolution(l, thresh, nb_elem) : 
    if len(l) < nb_elem : 
        return False
    for k in range(len(l)-nb_elem, len(l) - 1) : 
        if abs(l[k] - l[k+1]) > thresh : 
            return False
    return True

class GA :
    def __init__(self, model, nb_pop=100, nb_gen=100, pl=1, pq=1, mutation_rate=0.2, nb_last_element = 10, threshold=1e-05, fac=1) : 
        # Generate population
        self.model = model
        self.var_len = {var : len(getattr(self.model, var)) for var in self.model.Var}
        self.nb_pop = nb_pop
        self.current_pop = nb_pop
        self.Pop = np.array([None for k in range(nb_pop)])
        self.last_obj = []
        self.pl = pl
        self.pq = pq
        self.nb_gen = nb_gen
        self.mutation_rate = mutation_rate
        self.threshold = threshold
        self.nb_last_element = nb_last_element
        self.fac = fac
        
        tic = time()
        for k in range(nb_pop) :
            self.Pop[k] = Individual(model, pl, pq)
        print()
        print("Création d'un individu : ", time()-tic)
        
        self.best_indiv = Individual(model, pl, pq)
        
        
    def solve(self) : 
        c = 0
        while c < self.nb_gen and not no_evolution(self.last_obj, self.threshold, self.nb_last_element) :
            
            tic = time()
            sorted_indices = np.argsort([individual.fitness for individual in self.Pop])
            self.Pop = self.Pop[sorted_indices]
            if not self.last_obj : 
                self.last_obj.append(self.Pop[0].fitness)
            if self.Pop[0].fitness < self.last_obj[-1] : 
                self.last_obj.append(self.Pop[0].fitness)
                self.best_indiv.copy_var(self.Pop[0])
                self.best_indiv.fitness = self.best_indiv.detailed_obj(self.pl, self.pq)
            print()
            print("Initialisation boucle : ", time()-tic)
            
            print(c)
            print("last saved value", self.last_obj[-1])
            print("current best", self.Pop[0].fitness)
            
            # Selection
            tic = time()
            self.chosen_ones = self.selection_half_most_ranked()
            print()
            print('Selection : ', time()-tic)
            # Pairing
            tic = time()
            self.pairs = self.pairing(2)
            print('Pairing : ', time() -tic)
            # Crossover
            tic = time()
            print()
            self.linear_random_crossover(self.fac)
            print('Crossover : ', time() - tic)
            # Mutation
            tic = time()
            self.random_mutation(self.mutation_rate, c)
            print()
            print('Mutation : ', time() - tic)
            
            c +=1

    def __call__(self) : 
        return self.best_indiv
    
    def selection_half_most_ranked(self) : 
        self.current_pop = self.current_pop//2
        return(self.Pop[:self.current_pop])
    
    def pairing(self, n) : 
        return rd.choice(self.chosen_ones, size=(len(self.chosen_ones)//n, n), replace=False)
        
    def linear_random_crossover(self, fac) : 
        c = self.current_pop
        for pair in self.pairs : 
            child1 = self.Pop[c]
            child2 = self.Pop[c+1]
            par1 = pair[0]
            par2 = pair[1]
            c += 2
            rand = fac*rd.rand()
            for var in self.model.Var : 
                setattr(child1, var, getattr(par1, var)*(1+rand) - rand*getattr(par2, var))
                setattr(child2, var, getattr(par2, var)*(1+rand) - rand*getattr(par1, var))
                child1.fitness = child1.obj(self.pl, self.pq)[0][0]
                child2.fitness = child2.obj(self.pl, self.pq)[0][0]
                # This changes the values in Pop
            self.current_pop += 2
            
    def random_mutation(self, mutation_rate, c, min_value=1/1000, max_value=1/10) :
        for individual in self.Pop:
            flag = False
            for var in self.model.Var:
                var_table = getattr(individual, var)
                for k in range(self.var_len[var]) :
                    if rd.rand() < mutation_rate:
                        flag = True
                        lb, ub = self.model.opti_bounds[var]
                        mut_fac = min_value + (1 - min_value) * (self.nb_gen - c) / self.nb_gen
                        mut_fac = self.last_obj[-1]/self.last_obj[0]
                        mutation_value = rd.randn(1)[0]*(ub-lb)/6*mut_fac
                        # standard deviation see wikipedia mutation
                        mutated_var = var_table[k] + mutation_value
                        mutated_var = np.clip(mutated_var, lb, ub)
                        var_table[k] = mutated_var # array so not needed to reaffect value
            if flag : 
                individual.fitness = individual.obj(self.pl, self.pq)[0][0]
                    

            
# For now the time for a population of 100 are : 
    # Crossover : 8s
    # Mutation : 6s
    # Other : none
            
class PSO:
    def __init__(self, model, nb_pop=100, nb_gen=1000, lb=-1000, ub=1000, w=0.2, pl=1000, pq=1000, threshold=1e-5, nb_last_element=10):
        self.model = model
        self.nb_pop = nb_pop
        self.nb_gen = nb_gen
        self.w = w
        self.pl = pl
        self.pq = pq
        self.threshold = threshold
        self.nb_last_element = nb_last_element
        self.var_len = {var: len(getattr(self.model, var)) for var in self.model.Var}
        self.phi_max=2.5
        self.phi_min=0.5
        
        # Initialize population and velocities
        self.Pop = np.array([Individual(model, pl, pq, velocity=True) for _ in range(nb_pop)])
        
        # Initialize best positions
        self.best_indiv = Individual(model, pl, pq)
        
    
    def solve(self):
        c = 0 
        while c < self.nb_gen and not no_evolution(self.last_obj, self.threshold, self.nb_last_element) :
            sorted_indices = np.argsort([individual.fitness for individual in self.Pop])
            self.Pop = self.Pop[sorted_indices]
            phig = (self.phi_max - self.phi_min)*c/nb_gen + self.phi_min
            phip = (self.phi_min - self.phi_max)*c/nb_gen + self.phi_max
            w = ((1/2*(phig + phip) - 1) + 1)/2
            for k in range(self.nb_population) :
                for var in self.Var : 
                    for j in self.var_len[var] :
                        rp, rg = rd.rand(), rd.rand()
                        Vel = getattr(self.Pop[k], var__v)
                        Pos = getattr(self.Pop[k], var)
                        Best = getattr(self.Pop[k].best, var)
                        Vel[j] = w*Vel[j] + phig*rg*(getattr(self.best_indiv, var)[j] - Pos[j]) + phip*rp*(Best[j]-Pos[j])
                        Pos[j] += Vel[j]
                self.Pop[k].fitness = self.obj(self.pl, self.pq)[0][0]
                if self.Pop[k].fitness < self.Pop[k].best.fitness : 
                    self.Pop[k].best.copy_var(self.Pop[k])
                    self.Pop[k].best.fitness = self.Pop[k].fitness
                if self.Pop[k].fitness < self.best_indiv.fitness : 
                    self.best_indiv.copy_var(self.Pop[k])
                    self.best_indiv.fitness = self.Pop[k].fitness
                    self.last_obj.append(self.best_indiv.fitness)  
            c += 1
    def __call__(self):
        return self.best[0]


def build_model(timeframe, definer=1, charge_rate=0.5, decharge_rate=0.5, Effc=0.95, Effd=0.95, Econs=Econs, Eautocons=Eautocons, TP=TP, TE=TE, tep=tep, Kp=Kp, period_hours=period_hours) :
    if definer == 1 :
        Time, Nbdays, Time_in_month = define_time(timeframe, period_hours)
        Nbdays += 1
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
    elif definer == 2 :
        Time, Nbdays, Time_in_month = define_time2(full_date_new, period_hours)
        timerange = (min(min(t) if t else 999999999 for t in Time), max(max(t) if t else 0 for t in Time))
        # Same way as in the opti_batterie.py file
    else : 
        raise ValueError("definer must be 1 or 2")
        
    Var = ['Pb', 'Cb', 'Pprev']
    Econs = Econs[timerange[0]:timerange[1]+1]
    Eautocons = Eautocons[timerange[0]:timerange[1]+1]
    Pb = np.zeros(len(Econs))
    Cb = 0
    Pprev = np.zeros(6)
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
      
    
    args = {
        'Econs': Econs, 
        'Eprod': Eautocons, 
        'TE': TE, 
        'TP': TP, 
        'periods': range(6),
        'time' : Time, 
        'time_month': time_month,
        'tep': tep,
        'Kp': Kp,
        'Nbdays': Nbdays,
        'deltat': 0.25,
        'batterie_life': 10,
        'TB': 359,
        'TBm': 0.019,
        'tot_time' : tot_time, 
        'SOC' : np.zeros(len(tot_time)),
        'Pb' : Pb, 
        'Pprev' : Pprev, 
        'Cb' : Cb, 
        'charge_rate' : charge_rate, 
        'discharge_rate' : discharge_rate,
        'months' : range(12)
    }
    
    mod = Model(Var, **args)
    return mod
            
if __name__ == '__main__' : 
    timeframe = (dt.datetime(2024, 4, 1, 0, 0), dt.datetime(2024, 4, 1, 0, 59))
    # mod = build_model(timeframe)
    mod = build_model(full_date_new, definer=2, Econs=Econs_new, Eautocons=Eprod_new) 
    mod.set_bounds(['Pb', 'Cb', 'Pprev'], [-1000, 0, 0], [1000, 1000, 1000])
    
    import sys 
    print("bonjour", sys.argv)
    if len(sys.argv) > 1 : 
        res = GA(mod, nb_pop=100, nb_gen=1, mutation_rate=0.2, pl=0.01, pq=0.01, nb_last_element = 100, threshold=1e-05, fac=1)
        res.solve()
        

# class model : 
#     def __init__(self, Variables, Parameters, Constraints, Costs) : 
#         # Constraints of the form [(expression, lb, ub, variables in constraint in the right order with the function expression)]
#         self.variables = Variables 
#         self.parameters = Parameters
#         self.constraints = Constraints
#         self.var_names = {}
#         c = 0
#         for key in Variables : 
#             var_names[key] = c
#             c += 1
        
#         self.var = np.zeros((c, 1))
#         variables_cons = {key:[] for key in self.variables}
#         for con in constraint : 
#             for var in con[3] : 
#                 variables_cons[var].append(con)
                
        
#         self.cons_cost = {var : self.create_constraint_cost_function(variables_cons[var]) for var in variables_cons}
        
        
            
            
#     def create_constraint_cost_function(self, l_cons) :
#         # Faire une somme d'appelle de fonction est plus lent que de faire une somme tout court (environ 3 fois plus lent)
#         # Donc si notre truc est prométeur, on pourra changer les lambda par des chaines de caractère que l'on évalue après.
#         def cost_func(pl, pq) :
#             total_cost = 0
#             for cons in l_cons : 
#                 args = set()
#                 for var in cons[-1] : 
#                     args.add(self.var[self.var_names[var]])
#                 con_val = con[0](*args)
#                 if con_val < lb : 
#                     e = lb-con_val
#                     total_cost += e**2*pq + e*pl
#                 elif con_val > ub : 
#                     e = con_val - ub
#                     total_cost += e**2*pq + e*pl
#             return total_cost
#         return cost_func
    
        