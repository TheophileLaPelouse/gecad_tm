import pyomo.environ as pyo

def objective_function(a) : 
    prod = 1 
    sum_ = 0
    for k in range(1000000) :
        prod = 1
        sum_ = 0
        for val in a : 
            prod = val*prod 
            sum_ += val 
    return prod/sum_

model = pyo.ConcreteModel()

model.range = pyo.RangeSet(0, 10)
model.a = pyo.Var(model.range, domain=pyo.NonNegativeReals, initialize=1)

model.obj = pyo.Objective(expr=objective_function(model.a), sense=pyo.maximize)

def lower_bound_rule(model, r):
    return model.a[r] >= 0

def upper_bound_rule(model, r):
    return model.a[r] <= 1

model.a_lower_con = pyo.Constraint(model.range, rule=lower_bound_rule)
model.a_upper_con = pyo.Constraint(model.range, rule=upper_bound_rule)




solver = pyo.SolverFactory('ipopt')
solver.options['print_timing_statistics'] = 'yes'

solver.solve(model, tee=True)
