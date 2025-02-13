#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define PY_SSIZE_T_CLEAN

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

Model init_model(double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, double discharge_rate, double **TE, double *TP, int indexPprev[2], int Nbdays, double Kp, double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, size_t n_tot_time, size_t *time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) {
    Model model;
    model.Econs = Econs;
    model.Eprod = Eprod;
    memcpy(model.indexPb, indexPb, 2 * sizeof(int));
    model.deltat = deltat;
    model.charge_rate = charge_rate;
    model.discharge_rate = discharge_rate;
    model.TE = TE;
    model.TP = TP;
    memcpy(model.indexPprev, indexPprev, 2 * sizeof(int));
    model.Nbdays = Nbdays;
    model.Kp = Kp;
    model.tep = tep;
    model.indexCb = indexCb;
    model.TB = TB;
    model.batterie_life = batterie_life;
    model.TBm = TBm;
    model.SOC = SOC;
    model.tot_time = tot_time;
    model.n_tot_time = n_tot_time;
    model.time = time;
    model.time_month = time_month;
    model.n_time_month = n_time_month;
    model.months = months;
    model.n_m = n_m;
    model.periods = periods;
    model.n_p = n_p;
    return model;
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
    mod->SOC[0] = Var[mod->indexCb]*0.2 ;
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

int no_evolution(double *last_obj, double threshold, int last_element, int len) {
    if (len < last_element) {
        return 0 ;
    }
    for (int k=len-last_element; k<len-1; k++) {
        if (fabs(last_obj[k] - last_obj[k+1]) > threshold) {
            return 0 ;
        }
    }
    return 1 ;
}

int compare_indiv(const void *a, const void *b) {
    Individual *ind1 = (Individual *)a;
    Individual *ind2 = (Individual *)b;
    if (ind1->fitness < ind2->fitness) return -1;
    if (ind1->fitness > ind2->fitness) return 1;
    return 0;
}

void sort_population(Individual *population, int nb_pop) {
    qsort(population, nb_pop, sizeof(Individual), compare_indiv) ;
}

void shuffle(int *array, size_t n)
{
    if (n > 1) 
    {
        size_t i;
        for (i = 0; i < n - 1; i++) 
        {
          size_t j = i + rand() / (RAND_MAX / (n - i) + 1);
          int t = array[j];
          array[j] = array[i];
          array[i] = t;
        }
    }
}

void linear_random_crossover(Individual *par1, Individual *par2, Individual *child1, Individual *child2, double fac) {
    double rd = (double)rand() / (double)RAND_MAX ;
    rd = rd*fac ;
    for (int i = 0; i < par1->mod->Var_size; i++) {
        child1->Var[i] = (1 + rd) * par2->Var[i] - rd * par1->Var[i];
        child2->Var[i] = (1 + rd) * par1->Var[i] - rd * par2->Var[i];
        child1->fitness = obj(child1->mod, child1->Var, child1->pl, child1->pq) ;
        child1->fitness = obj(child2->mod, child2->Var, child2->pl, child2->pq) ;
    }
}

double generate_normal_random() {
    // Using the Box–Muller transform
    double u1 = (double)rand() / RAND_MAX;
    double u2 = (double)rand() / RAND_MAX;
    double z0 = sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
    return z0;
}

void random_mutation(Individual *Pop, int nb_pop, double mutation_rate, int c, int nb_gen, double min_val, double max_val) {
    for (int k=0; k<nb_pop; k++) {
        int flag = 0 ;
        for (int i=0; i<Pop[k].mod->Var_size; i++) {
            double rd = (double)rand()/RAND_MAX ; 
            if (rd<mutation_rate) {
                flag = 1 ; 
                double lb = Pop[k].bounds[i][0] ; 
                double ub = Pop[k].bounds[i][1] ;
                double mut_fac = min_val + (1 - min_val) * (double)(nb_gen - c) / nb_gen ;
                double mutation_value = generate_normal_random()*(ub - lb)/6*mut_fac ;
                double mutated_var = Pop[k].Var[i] + mutation_value ; 
                if (mutated_var > ub) mutated_var = ub ;
                if (mutated_var < lb) mutated_var = lb ;
                Pop[k].Var[i] = mutated_var ;
            }
        }
        if (flag) Pop[k].fitness = obj(Pop[k].mod, Pop[k].Var, Pop[k].pl, Pop[k].pq) ;
    }
}

Individual GA(Model *mod, double opti_bounds[][2], int nb_pop, int nb_gen, double pl, double pq
, double mutation_rate, int last_element, double threshold, int fac) {
    Individual *Pop = malloc(nb_pop * sizeof(Individual));
    for (int i = 0; i < nb_pop; i++) {
        init_individual(&Pop[i], mod, pl, pq, opti_bounds);
    }
    if (!(nb_pop/2 == (int) ((double) nb_pop/2.0))) nb_pop = nb_pop+1 ;
    int current_pop = nb_pop;
    double last_obj[nb_gen] ;
    int len = 0 ;
    Individual best_indiv ;
    init_individual(&best_indiv, mod, pl, pq, opti_bounds) ;
    
    int chosen[nb_pop/2] ;
    for (int i = 0; i < nb_pop/2; i++) {
        chosen[i] = i ;
    }
    int pairs[nb_pop/2/2][2] ;


    int c = 0 ;
    while (c < nb_gen && !(no_evolution(last_obj, threshold, last_element, len))) {
        sort_population(Pop, nb_pop) ;
        if (len == 0) {
            len += 1 ;
            last_obj[0] = Pop[0].fitness ;
        }
        if (Pop[0].fitness < last_obj[len-1]) {
            last_obj[len] = Pop[0].fitness ; 
            copy_var(&best_indiv, &Pop[0]) ;
            best_indiv.fitness = Pop[0].fitness ;
        }
        printf("Generation %d:\n", c);
        printf("Best fitness: %f\n", Pop[0].fitness);
        printf("Best individual variables:\n");
        printf("\n");

        // Selection
        current_pop = nb_pop/2 ; 
        shuffle(chosen, nb_pop/2) ;
        for (int i = 0; i < nb_pop/2/2; i++) {
            pairs[i][0] = chosen[2*i] ;
            pairs[i][1] = chosen[2*i+1] ;
        }

        // Crossover
        for (int i=0; i<nb_pop/2/2 ; i++) {
            int ch1 = current_pop ;
            int ch2 = current_pop + 1 ;
            int p1 = pairs[i][0] ;
            int p2 = pairs[i][1] ;
            current_pop += 2 ; 
            linear_random_crossover(&Pop[p1], &Pop[p2], &Pop[ch1], &Pop[ch2], fac) ;
        }

        // Mutation
        random_mutation(Pop, nb_pop, mutation_rate, c, nb_gen, 1.0/1000, 1.0/10) ;
        c += 1 ;

    }
    return best_indiv ;
}

int main() {
    printf("Hello, World!\n");

    // Take file named param.txt, on each line there is name ; value ; type ; 
    return 0;

}