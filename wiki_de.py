import pyomo 
import numpy.random as rd
import re
from time import time
import os


type_list = [pyomo.core.base.var.Var, pyomo.core.base.constraint.Constraint, pyomo.core.base.param.Param]


def split_string(s) :
    current = ''
    args = []
    flag_bracket = False
    for c in s :
        if c == ' ' and not flag_bracket : 
            # print(c, 1)
            args.append(current)
            current = ''
        elif re.match(r'[\+\-\/\*\(\)]', c) : 
            # print(c, 2)
            args.append(current)
            args.append(c)
            current = ''
            
        elif c == '[' :
            # print(c, 3)
            flag_bracket = True
            current += c
        elif c == ']' :
            # print(c, 4)
            flag_bracket = False
            current += c
        else :
            # print(c, 5)
            current += c
    args.append(current)
    return args

def read_constraints(names, con) : 
    args = split_string(con)
    # print(args)
    left = []
    right = []
    flag_left = True
    sense = ''
    for arg in args : 
        if arg in names : 
            new_arg = 'x[%s]' % names[arg]
            if flag_left : 
                left.append(new_arg)
            else : 
                right.append(new_arg)
        elif arg in ['<=', '==', '>='] : 
            sense = arg
            flag_left = False
        else : 
            if flag_left : 
                left.append(arg)
            else : 
                right.append(arg)
    if 'Pplus' in ''.join(left) + '-' +'(' + ''.join(right) + ')' : 
        print()
        print(con)
        print(args)
        print(left, right)
        print(''.join(left) + '-' +'(' + ''.join(right) + ')')
    return (sense, ''.join(left) + '-' +'(' + ''.join(right) + ')')

def read_objective(names, obj) : 
    args = split_string(obj)
    new_args = []
    for arg in args : 
        if arg in names : 
            new_args.append('x[%s]' % names[arg])
        else : 
            new_args.append(arg)
    return ''.join(new_args)
            

def pyomo_translate(pyomo_model) : 
    # The goal is to take as input a Pyomo model and optimise it using the Differential Evolution algorithm
    # added stuff in model : [val for val in model.component_objects()]
    # Les trucs ont un ctype pour savoir ce qu'on regarde
    # les variables ont une méthode set_value et set_values
    # Si on veut tout reconstruire du modèle, on peut utiliser extract_values pour les variables
    
    # Première chose, on va réécrire le modèle de manière à avoir un modèle de la forme :
    # min f(x) st, Ax == b
    
    comp = [val for val in pyomo_model.component_objects()]
    variables = {}
    values = []
    constraints = []
    objs = []
    c = 0
    for val in comp : 
        if val.ctype == pyomo.core.base.var.Var : 
            if val.is_indexed() : 
                for index, var in val.items() : 
                    variables[var.name] = c 
                    values.append(var.value)
                    c += 1
            else :
                variables[val.name] = c
                values.append(var.value)
                c += 1
            
            
    for val in comp : 
        if val.ctype == pyomo.core.base.constraint.Constraint : 
            if val.is_indexed() : 
                for index, con in val.items() : 
                    constraints.append(read_constraints(variables, con.expr.to_string()))
            else : 
                constraints.append(read_constraints(variables, val.expr.to_string()))
                
        if val.ctype == pyomo.core.base.objective.Objective :
            sense = val.sense.name
            if val.is_indexed() : 
                for index, obj in val.items() : 
                    objs.append(read_objective(variables, obj.expr.to_string()))
            else :
                objs.append(read_objective(variables, val.expr.to_string()))
        
    con_cost = {}
    def constraint_obj() : 
        s = ''
        for c in constraints : 
            # print('('+c[1]+')'+'**2*p1')
            con_cost[c[1]] = lambda x, p1 : eval('('+c[1]+')'+'**2*p1')
            if c[0] == '<=' : 
                # s+= '+ ' + '('+c[1]+')'+'*p0'
                s+= '+ ' + '('+c[1]+'>0)*' +'('+'('+c[1]+')'+'**2*p1'+'+abs('+c[1]+')'+'*p0'+')'
            elif c[0] == '==' :
                s+= '+ ' +'('+c[1]+')'+'**2*p1'+'+abs('+c[1]+')'+'*p0'
            else :
                # s+= '- ' '('+c[1]+')'+'*p0'
                s+= '+ ' + '('+c[1]+'<0)*' +'('+'('+c[1]+')'+'**2*p1'+'+abs('+c[1]+')'+'*p0'+')'
        return s
    
    
    if sense == 'minimize' : 
        sense = 1
    else : 
        sense = -1
    
    # Penalisation if the the solution does not respect the constraint
    # print(constraint_obj())
    # print('\n\n')
    # print(objs)
    # print('\n\n')
    # print(sense*('+'.join(objs) + '+' + constraint_obj()))
    # print("obj = lambda x, p0, p1 : " + str(sense) + '*(' + '+'.join(objs) + '+' + constraint_obj() + ')')
    obj_str = ("obj = lambda x, p0, p1 : " + str(sense) + '*(' + '+'.join(objs) + '+' + constraint_obj() + ')').replace('++', '+')
    
    local_vars = {}
    try : 
        exec(obj_str, globals(), local_vars)
        obj = local_vars['obj'] 
    except Exception as e: 
        print(e)
        with open('objective_function.py', 'w') as f:
            f.write(obj_str)
        from objective_function import obj
        
    # obj = lambda x, p0, p1 : eval(sense*('+'.join(objs) + '+' + constraint_obj()))
    obj_str = "obj = lambda x, p0, p1 : " + str(sense) + '*(' + '+'.join(objs) + '+' + constraint_obj() + ')'
    return obj, variables, values, con_cost, obj_str, '+'.join(objs)

def no_evolution(l, thresh, nb_elem) : 
    if len(l) < nb_elem : 
        return False
    for k in range(len(l)-nb_elem, len(l) - 1) : 
        if abs(l[k] - l[k+1]) > thresh : 
            return False
    return True
        
def mean(l) : 
    if l : 
        return(sum(l)/len(l))
    else : 
        return 0
    
def differential_evolution(obj, n, nb_iteration_max = 1000, nb_population = 100, F = 0.8, CR = 0.9, p0 = 100, p1= 100, lb=-500, ub=500, threshold = 10**(-5), nb_last_element = 10) :
    if nb_population < 3 :
        raise ValueError("Population should be greater than 3")
    X = [[rd.uniform(lb, ub) for i in range(n)] for j in range(nb_population)]
    X_obj = [obj(x, p0, p1) for x in X]
    last_obj = min(X_obj)
    best = None
    nb_iter = 0
    last_obj = [last_obj]
    
    tic1 = []
    tac1 = []
    tic2 = []
    tac2 = []
    while nb_iter < nb_iteration_max and not no_evolution(last_obj, threshold, nb_last_element) :
        print()
        print(last_obj[-1])
        print(last_obj[-1]/last_obj[0])
        print(nb_iter)
        
        index2choose = [k for k in range(1, nb_population)]
        for k in range(nb_population) :
            tic1.append(time())
            y = X[k][:]
            if k != 0 : 
                index2choose[k-1] = k-1 # Make sure the current k is never in index2choose
            a, b, c = rd.choice(index2choose, size=3, replace=False)
            # print(a, b, c)
            a, b, c = X[a], X[b], X[c]
            R = rd.randint(n)
            for i in range(n) : 
                u = rd.rand()
                if u < CR or i == R :
                    y[i] = a[i] + F*(b[i] - c[i])
            tac1.append(time())
            tic2.append(time())
            y_obj = obj(y, p0, p1)
            # print('y_obj', y_obj, 'X_obj[k]', X_obj[k])
            if y_obj < X_obj[k] :
                X[k] = y
                X_obj[k] = y_obj
                if y_obj < last_obj[-1] : 
                    last_obj.append(y_obj)
                    best = y
            tac2.append(time())
        nb_iter += 1
    time1 = [tac1[i] - tic1[i] for i in range(len(tac1))]
    time2 = [tac2[i] - tic2[i] for i in range(len(tac2))]
    print('avant obj', mean(time1))
    print('après obj', mean(time2))
    return(best, last_obj)
      
# On va ajouter la notion de scaling à tout ça avant de continuer sur d'autres tests.  
def PSO(obj, n, nb_iteration_max = 1000, nb_population = 100, lb=-1000, ub=1000, w=0.2, p0=1000, p1=1000, threshold = 10**(-5), nb_last_element = 10) :
    X = [[rd.uniform(lb, ub) for i in range(n)] for j in range(nb_population)]
    X_obj = [obj(x, p0, p1) for x in X]
    Xbest = [[[X[k][i] for i in range(n)], X_obj[k]] for k in range(nb_population)]
    last_obj = min(X_obj)
    best = [min(X, key = lambda x : obj(x, p0, p1)), last_obj]
    
    phi_max = 2.5
    phi_min = 0.5
    nb_iter = 0
    last_obj = [last_obj]
    V = [[rd.uniform(abs(lb-ub), abs(ub-lb)) for i in range(n)] for j in range(nb_population)]
    while nb_iter < nb_iteration_max and not no_evolution(last_obj, threshold, nb_last_element) :
        # p1+=(nb_iter//200)*0.5
        print()
        print(last_obj[-1])
        print(last_obj[-1]/last_obj[0])
        print(nb_iter)
        phig = (phi_max - phi_min)*nb_iter/nb_iteration_max + phi_min
        phip = (phi_min - phi_max)*nb_iter/nb_iteration_max + phi_max
        w = ((1/2*(phig + phip) - 1) + 1)/2
        for k in range(nb_population) :
            for j in range(n) :
                rp, rg = rd.rand(), rd.rand()
                # print(len(Xbest))
                V[k][j] = w*V[k][j] + phip*rp*(Xbest[k][0][j]- X[k][j]) + phig*rg*(best[0][j]-X[k][j])
                X[k][j] += V[k][j]
            x_obj = obj(X[k], p0, p1)
            if x_obj < Xbest[k][1] : 
                Xbest[k] = [X[k][:], x_obj]
            if x_obj < best[1] : 
                best = [X[k][:], x_obj]
                last_obj.append(best[1])
        nb_iter += 1
    return(best)

# def GA(obj, variables, nb_iteration_max = 1000, nb_population = 100, lb=-1000, ub=1000, p0=1000, p1=1000, threshold = 10**(-5), nb_last_element = 10) :
#     n = len(variables)
#     X = [[rd.uniform(lb, ub) for i in range(n)] for j in range(nb_population)]
#     Xobj = [obj(x, p0, p1) for x in X]
#     last_obj = min(Xobj)
    
    

#%%
if __name__ == '__main__' : 
    # from opti_batterie import model
    obj, variables, values, constraints, truc1, truc2 = pyomo_translate(model)
    nb_population = 100
    n = len(variables)
    X = [[(rd.rand() - 0.5)*1000 for i in range(n)] for j in range(nb_population)]
    p0 = 10000
    p1 = 10000
    obj(X[0], p0, p1)
    best, last_obj = differential_evolution(obj, variables)
    
    
    
            

                    
    
    