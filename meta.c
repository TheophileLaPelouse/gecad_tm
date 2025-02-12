// class Model : 
//     def __init__(self, Var, **kwargs) : 
//         self.Var = Var
//         self.Param = set()
//         for key, value in kwargs.items():
//             if key in Var : 
//                 try : 
//                     setattr(self, key, np.zeros(len(value)))
//                 except : 
//                     setattr(self, key, np.zeros(1))
//                 setattr(self, key+'_parameter', value)
//             elif isinstance(value, (int, float)) : 
//                 setattr(self, key, value)
//                 self.Param.add(key)
//             else : 
//                 try : 
//                     setattr(self, key, np.array(value))
//                 except : 
//                     setattr(self, key, value) # Should be useful only for Time in month
//                 self.Param.add(key)
                    
//         self.opti_bounds = {var : [-np.inf, np.inf] for var in self.Var} 
        
//     def detailed_obj(self, pl, pq) : 
//         detail = {}
//         total = 0
//         Egrid = self.Econs - self.Eprod + ((self.Pb > 0)*self.charge_rate*self.Pb - (self.Pb < 0)*self.Pb/self.discharge_rate)*self.deltat
//         tot_egrid = 0
//         for month in self.months : 
//             for p in self.periods : 
//                 for t in self.time_month[month][p] : 
//                     if Egrid[t] > 0 :
//                         total += self.TE[month][p]*Egrid[t]
//                         tot_egrid += self.TE[month][p]*Egrid[t]
//         detail['Egrid'] = tot_egrid
        
//         tot_pena = 0
//         for p in self.periods : 
//             total += self.TP[p]*self.Pprev[p]*self.Nbdays
//             st = 0
//             for t in self.time[p] : 
//                 val = Egrid[t]/self.deltat - self.Pprev[p]
//                 if val > 0 : 
//                     st+=val**2
//             total += self.Kp[p]*self.tep*st**(1/2)
//             tot_pena += self.Kp[p]*self.tep*st**(1/2)
        
//         detail['pena'] = tot_pena
        
//         total += self.Cb*(self.TB/self.batterie_life + self.TBm) * self.Nbdays/365
        
//         # Constraints penalisation cost for lower and upper bound
        
//         constraint_cost = 0
//         for t in self.tot_time[:-1] : 
//             self.SOC[t+1] = self.Pb[t]*self.deltat
//             constraint_cost += self.penalty_bound_elem(self.SOC[t+1], 0.2*self.Cb, self.Cb, pl, pq)
//             detail[f'SOC[{t}+1]'] = self.penalty_bound_elem(self.SOC[t+1], 0.2*self.Cb, self.Cb, pl, pq)
        
//         val = self.penalty_bound(self.Pb, -self.discharge_rate*self.Cb, self.charge_rate*self.Cb, pl, pq)
//         constraint_cost += val
//         detail['Pb'] = val
        
//         for p in self.periods[:-1]: 
//             constraint_cost += self.penalty_bound_elem(self.Pprev[p], 0, self.Pprev[p+1], pl, pq)
//             detail['Pprev[%d]'%p] = self.penalty_bound_elem(self.Pprev[p], 0, self.Pprev[p+1], pl, pq)
        
//         return total + constraint_cost, total, constraint_cost, detail
    
//     def obj(self, pl, pq):
//         total = 0
//         Egrid = self.Econs - self.Eprod + ((self.Pb > 0) * self.charge_rate * self.Pb - (self.Pb < 0) * self.Pb / self.discharge_rate) * self.deltat
//         for month in self.months:
//             for p in self.periods:
//                 for t in self.time_month[month][p]:
//                     if Egrid[t] > 0:
//                         total += self.TE[month][p] * Egrid[t]

//         for p in self.periods:
//             total += self.TP[p] * self.Pprev[p] * self.Nbdays
//             st = 0
//             for t in self.time[p]:
//                 val = Egrid[t] / self.deltat - self.Pprev[p]
//                 if val > 0:
//                     st += val ** 2
//             total += self.Kp[p] * self.tep * st ** (1 / 2)

//         total += self.Cb * (self.TB / self.batterie_life + self.TBm) * self.Nbdays / 365

//         # Constraints penalisation cost for lower and upper bound
//         constraint_cost = 0
//         for t in self.tot_time[:-1]:
//             self.SOC[t + 1] = self.Pb[t] * self.deltat
//             constraint_cost += self.penalty_bound_elem(self.SOC[t + 1], 0.2 * self.Cb, self.Cb, pl, pq)

//         val = self.penalty_bound(self.Pb, -self.discharge_rate * self.Cb, self.charge_rate * self.Cb, pl, pq)
//         constraint_cost += val

//         for p in self.periods[:-1]:
//             constraint_cost += self.penalty_bound_elem(self.Pprev[p], 0, self.Pprev[p + 1], pl, pq)

//         return total + constraint_cost, total, constraint_cost
            
//     def penalty_bound(self, var, varlb, varub, pl, pq) : 
//         # Take into account an array
//         penalty = (varlb - var[var < varlb]).sum() + (var[var > varub] - varub).sum()
//         total_penalty = penalty * pl + penalty ** 2 * pq
//         return total_penalty
    
//     def penalty_bound_elem(self, var, varlb, varub, pl, pq) :
//         # single element 
//         penalty = (varlb - var)*(varlb-var>0) + (var - varub)*(var-varub>0)
//         total_penalty = penalty * pl + penalty ** 2 * pq
//         return total_penalty
    
//     def set_bounds(self, var, lb, ub) : 
//         if isinstance(var, list) : 
//             for k in range(len(var)) :
//                 self.opti_bounds[var[k]] = [lb[k], ub[k]]
//         else :
//             self.opti_bounds[var] = [lb, ub]

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef struct {
    size_t Var_size;
    double *Econs;
    double *Eprod;
    int indexPb[2];
    double deltat;
    double charge_rate;
    double discharge_rate;
    double **TE;
    double *TP;
    int indexPprev[2];
    int Nbdays;
    double Kp;
    double tep;
    int indexCb ;
    double TB;
    double batterie_life;
    double TBm;
    double *SOC;
    size_t *tot_time;
    size_t n_tot_time;
    size_t *time;
    size_t ***time_month;
    size_t **n_time_month;
    int *months;
    int n_m ;
    int *periods;
    int n_p;
} Model;

void init_model(Model *model, double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, double discharge_rate, double *TE, double *TP, int indexPprev[2], double Nbdays, double Kp, double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, int *tot_time, size_t n_tot_time, double *time, double ***time_month, size_t *n_time_month, double *months, int n_m, double *periods, int n_p) {
    model->Econs = Econs;
    model->Eprod = Eprod;
    memcpy(model->indexPb, indexPb, 2 * sizeof(int));
    model->deltat = deltat;
    model->charge_rate = charge_rate;
    model->discharge_rate = discharge_rate;
    model->TE = TE;
    model->TP = TP;
    memcpy(model->indexPprev, indexPprev, 2 * sizeof(int));
    model->Nbdays = Nbdays;
    model->Kp = Kp;
    model->tep = tep;
    model->indexCb = indexCb;
    model->TB = TB;
    model->batterie_life = batterie_life;
    model->TBm = TBm;
    model->SOC = SOC;
    model->tot_time = tot_time;
    model->n_tot_time = n_tot_time;
    model->time = time;
    model->time_month = time_month;
    model->n_time_month = n_time_month;
    model->months = months;
    model->n_m = n_m;
    model->periods = periods;
    model->n_p = n_p;
}

void free_model(Model *model) {
    free(model->Econs);
    free(model->Eprod);
    free(model->TE);
    free(model->TP);
    free(model->SOC);
    free(model->tot_time);
    free(model->time);
    for (int i = 0; i < model->n_m; i++) {
        for (int j = 0; j < model->n_p; j++) {
            free(model->time_month[i][j]);
        }
        free(model->time_month[i]);
    }
    free(model->time_month);
    free(model->n_time_month);
    free(model->months);
    free(model->periods);

}

double obj(Model *mod, double *Var, double pl, double pq) {
    double total = 0;
    double *Egrid = malloc(sizeof(double) * mod->n_tot_time);
    for (int t = 0; t < mod->n_tot_time; t++) {
        Egrid[t] = mod->Econs[t] + 
            (
                (Var[mod->indexPb[0]+t] > 0) * mod->charge_rate * Var[mod->indexPb[0]+t] - 
                (Var[mod->indexPb[0]+t] < 0) * Var[mod->indexPb[0]+t] / mod->discharge_rate
            ) * mod->deltat
            ;
    }
    for (int month = 0; month < mod->n_m; month++) {
        for (int p = 0; p < mod->n_p; p++) {
            for (int t = 0; t < mod->n_time_month[month][p]; t++) {
                if (Egrid > 0) {
                    total += mod->TE[month][p] * Egrid[mod->time_month[month][p][t]];
                }
            }
        }
    }
    for (int p = 0; p < mod->n_p; p++) {
        total += mod->TP[p] * Var[mod->indexPprev[0]+p] * mod->Nbdays;
        double st = 0;
        for (int t = 0; t < mod->n_tot_time; t++) {
            double val = Egrid[t] / mod->deltat - Var[mod->indexPprev[0]+p];
            if (val > 0) {
                st += val * val;
            }
        }
        total += mod->Kp * mod->tep * sqrt(st);
    }
    total += Var[mod->indexCb] * (mod->TB / mod->batterie_life + mod->TBm) * mod->Nbdays / 365;
    
    // Constraints
    double constraint_cost = 0; 
    for (int t =0; t<mod->n_tot_time-1 ; t++) {
        mod->SOC[t+1] = Var[mod->indexPb[0]+t] * mod->deltat ;
        constraint_cost += penalty_bound_elem(mod->SOC[t+1], 
                                0.2*Var[mod->indexCb], Var[mod->indexCb], pl, pq);

    constraint_cost += penalty_bound(Var, mod->indexPb, 
                    -mod->discharge_rate*Var[mod->indexCb], 
                    mod->charge_rate*Var[mod->indexCb], pl, pq) ; 

    for (int p =0 ; p<mod->n_p-1; p++) {
        constraint_cost += penalty_bound_elem(Var[mod->indexPprev[0]+p], 0, Var[mod->indexPprev[0]+p+1], pl, pq);
    }
    }
    return total;
}

double penalty_bound_elem(double var, double varlb, double varub, double pl, double pq) {
    double penalty = (varlb - var) * (varlb - var > 0) + (var - varub) * (var - varub > 0);
    double total_penalty = penalty * pl + penalty * penalty * pq;
    return total_penalty;
}

double penalty_bound(double *var, int *indices, double varlb, double varub, double pl, double pq) {
    double penalty = 0;
    for (int i = indices[0]; i <= indices[1]; i++) {
        penalty += (varlb - var[i]) * (varlb - var[i] > 0) + (var[i] - varub) * (var[i] - varub > 0);
    }
    double total_penalty = penalty * pl + penalty * penalty * pq;
    return total_penalty;
}

// We have the eqeuivalent of the model class in python.

typedef struct {
    Model *mod ; 
    double *Var ;
    double pl ;
    double pq ;
    double fitness ;
    double (*bounds)[2];
} Individual ;



void init_individual(Individual *ind, Model *model, double pl, double pq, double bounds[][2]) {
    ind->mod = model;
    ind->pl = pl;
    ind->pq = pq;
    ind->Var = malloc(model->Var_size * sizeof(double));
    ind->bounds = malloc(model->Var_size * sizeof(double[2]));

    srand(time(NULL));
    for (size_t i = 0; i < model->Var_size; i++) {
        ind->bounds[i][0] = bounds[i][0];
        ind->bounds[i][1] = bounds[i][1];
        ind->Var[i] = bounds[i][0] + ((double)rand() / RAND_MAX) * (bounds[i][1] - bounds[i][0]);
    }
    ind->fitness = obj(ind->mod, ind->Var, ind->pl, ind->pq) ; 
}

void copy_var(Individual *ind1, Individual *ind2) {
    for (int i =0 ; i < ind1->mod->Var_size ; i++) {
        ind1->Var[i] = ind2->Var[i] ;
    }
}
// We have the equivalent of the Individual class

Individual GA(Model *mod, double *opti_bounds, int nb_pop, int nb_gen, double pl, double pq
, double mutation_rate, int last_element, double threshold, int fac) {
    Individual *Pop = malloc(nb_pop * sizeof(Individual));
    for (int i = 0; i < nb_pop; i++) {
        init_individual(&Pop[i], mod, pl, pq, opti_bounds);
    }
    
}