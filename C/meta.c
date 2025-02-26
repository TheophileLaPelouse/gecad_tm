#ifndef META_H
#define META_H

#include "meta.h"

#endif // META_H

// gcc -fPIC -shared -o libmodel.so meta.c
// python tests.py 200 3000 0.13 0.02 0.04 100 0.000001 1 0.001 10

double generate_normal_random() {
    // Using the Box–Muller transform
    double u1 = (double)rand() / RAND_MAX;
    double u2 = (double)rand() / RAND_MAX;
    double z0 = sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
    return z0;
}


Model* init_model(size_t var_size, double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, double discharge_rate, double Effc, double Effd, double **TE, double *TP, int indexPprev[2], int Nbdays, double *Kp, double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, size_t n_tot_time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) {
    printf("Econs: %p, first value: %f\n", Econs, Econs[0]);
    printf("Eprod: %p, first value: %f\n", Eprod, Eprod[0]);
    printf("indexPb: %p, first value: %d\n", indexPb, indexPb[0]);
    printf("TE: %p, first value: %f\n", TE, TE[0][0]);
    printf("TP: %p, first value: %f\n", TP, TP[0]);
    printf("indexPprev: %p, first value: %d\n", indexPprev, indexPprev[0]);
    printf("Kp: %p, first value: %f\n", Kp, Kp[0]);
    printf("SOC: %p, first value: %f\n", SOC, SOC[0]);
    printf("tot_time: %p, first value: %zu\n", tot_time, tot_time[0]);
    printf("time_month: %p, first value: %zu\n", time_month, time_month[0][0][0]);
    printf("n_time_month: %p, first value: %zu\n", n_time_month, n_time_month[0][0]);
    printf("months: %p, first value: %d\n", months, months[0]);
    printf("periods: %p, first value: %d\n", periods, periods[0]);
    
    Model *model = (Model*)malloc(sizeof(Model));
    if (model == NULL) {
        fprintf(stderr, "Failed to allocate memory for model\n");
        return NULL;
    }
    printf("Model\n");
    model->Var_size = var_size;
    model->Econs = Econs;
    printf("Model Econs\n");
    model->Eprod = Eprod;
    printf("Model Eprod\n");
    memcpy(model->indexPb, indexPb, 2 * sizeof(int));
    printf("Model indexPb\n");
    model->deltat = deltat;
    printf("Model deltat\n");
    model->charge_rate = charge_rate;
    printf("Model charge_rate\n");
    model->discharge_rate = discharge_rate;
    model->Effc = Effc;
    printf("Model Effc %f\n", Effc);
    model->Effd = Effd;
    printf("Model discharge_rate\n");
    model->TE = TE;
    printf("Model TE\n");
    model->TP = TP;
    printf("Model TP\n");
    memcpy(model->indexPprev, indexPprev, 2 * sizeof(int));
    printf("Model indexPprev\n");
    model->Nbdays = Nbdays;
    printf("Model Nbdays\n");
    model->Kp = Kp;
    printf("Model Kp\n");
    model->tep = tep;
    printf("Model tep\n");
    model->indexCb = indexCb;
    printf("Model indexCb\n");
    model->TB = TB;
    printf("Model TB\n");
    model->batterie_life = batterie_life;
    printf("Model batterie_life\n");
    model->TBm = TBm;
    printf("Model TBm\n");
    model->SOC = SOC;
    printf("Model SOC\n");
    model->tot_time = tot_time;
    printf("Model tot_time\n");
    model->n_tot_time = n_tot_time;
    printf("Model n_tot_time\n");
    model->time_month = time_month;
    printf("Model time_month\n");
    model->n_time_month = n_time_month;
    printf("Model n_time_month\n");
    model->months = months;
    printf("Model months\n");
    model->n_m = n_m;
    printf("Model n_m\n");
    model->periods = periods;
    printf("Model periods\n");
    model->n_p = n_p;
    printf("Model n_p\n");
    return model;
}

void free_model(Model *model) {
    free(model->Econs);
    free(model->Eprod);
    free(model->TE);
    free(model->TP);
    free(model->SOC);
    free(model->tot_time);
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
    // clock_t tic = clock();
    double *Egrid = malloc(sizeof(double) * mod->n_tot_time);
    for (size_t t = 0; t < mod->n_tot_time; t++) {
        Egrid[t] = mod->Econs[t] + 
            (
                (Var[mod->indexPb[0]+t] > 0) * Var[mod->indexPb[0]+t] + 
                (Var[mod->indexPb[0]+t] < 0) * Var[mod->indexPb[0]+t]
            ) * mod->deltat * Var[mod->indexCb] 
            - mod->Eprod[t]
            ;
        // printf("Econs: %f, Eprod: %f, Ebat %f\n", mod->Econs[t], mod->Eprod[t], (
        //         (Var[mod->indexPb[0]+t] > 0) * mod->charge_rate * Var[mod->indexPb[0]+t] + 
        //         (Var[mod->indexPb[0]+t] < 0) * Var[mod->indexPb[0]+t] * mod->discharge_rate
        //     ) * mod->deltat * Var[mod->indexCb] );
    }
    // clock_t toc = clock();
    // printf("Time to calculate Egrid: %f\n", (double)(toc - tic) / CLOCKS_PER_SEC);
    // tic = clock();
    double Egrid_price = 0;
    for (int month = 0; month < mod->n_m; month++) {
        for (int p = 0; p < mod->n_p; p++) {
            for (size_t t = 0; t < mod->n_time_month[month][p]; t++) {
                if (Egrid[mod->time_month[month][p][t]] > 0) {
                    Egrid_price += mod->TE[month][p] * Egrid[mod->time_month[month][p][t]];
                    // printf("buying energy %f\n", mod->TE[month][p] * Egrid[mod->time_month[month][p][t]]);
                }
                // else {
                //     total += mod->TE[month][p] * Egrid[mod->time_month[month][p][t]]/2;
                //     // printf("selling energy %f\n", mod->TE[month][p] * Egrid[mod->time_month[month][p][t]]/2);
                // }
            }
        }
    }
    total += Egrid_price;
    // toc = clock();
    // printf("Time to calculate total: %f\n", (double)(toc - tic) / CLOCKS_PER_SEC);
    // tic = clock();
    double power_price = 0;
    double excess = 0;
    for (int p = 0; p < mod->n_p; p++) {
        power_price += mod->TP[p] * Var[mod->indexPprev[0]+p] * mod->Nbdays;
        // printf("power %f\n", mod->TP[p] * Var[mod->indexPprev[0]+p] * mod->Nbdays);
        double st = 0;
        for (int month = 0; month < mod->n_m; month++) {
            for (size_t t = 0; t < mod->n_time_month[month][p]; t++) {
                double val = Egrid[mod->time_month[month][p][t]] / mod->deltat - Var[mod->indexPprev[0]+p];
                if (val > 0) {
                    st += val * val;
                }
            }
        }
        // if (pl == 1.000012) printf("excess power p %d %f %f %f %f\n", p, mod->Kp[p],  mod->tep, sqrt(st), mod->Kp[p]*mod->tep*sqrt(st));
        // printf("excess power %f\n", mod->Kp[p] * mod->tep * sqrt(st));
        // total += power_price ;
        // total += mod->Kp[p] * mod->tep * sqrt(st);
        excess += mod->Kp[p] * mod->tep * sqrt(st) ;
    }
    total += excess;
    total += power_price;
    // printf("battery price %f\n", Var[mod->indexCb] * (mod->TB / mod->batterie_life + mod->TBm) * mod->Nbdays / 365);
    // if (pl == 1.000012) printf("Cb %f, TB %f, batterie_life %f, TBm %f, Nbdays %d\n", Var[mod->indexCb], mod->TB, mod->batterie_life, mod->TBm, mod->Nbdays);
    double bat_price = Var[mod->indexCb] * (mod->TB / mod->batterie_life + mod->TBm) * mod->Nbdays / 365;
    total += bat_price;
    // toc = clock();
    // printf("Time to calculate total: %f\n", (double)(toc - tic) / CLOCKS_PER_SEC);
    // tic = clock();
    // Constraints
    double constraint_cost = 0; 
    mod->SOC[0] = Var[mod->indexCb]*0.2 ;
    for (size_t t =0; t<mod->n_tot_time-1 ; t++) {
        mod->SOC[t+1] = mod->SOC[t] + (
                (double) (Var[mod->indexPb[0]+t] > 0) * mod->charge_rate * Var[mod->indexPb[0]+t] * mod->Effc + 
                (double) (Var[mod->indexPb[0]+t] < 0) * Var[mod->indexPb[0]+t] * mod->discharge_rate / mod->Effd
            ) * mod->deltat * Var[mod->indexCb] ;
        constraint_cost += penalty_bound_elem(mod->SOC[t+1], 
                                0.2*Var[mod->indexCb], Var[mod->indexCb], pl, pq);
        // if (pl == 1.000012) printf("SOC: %f\n", mod->SOC[t+1]);
    }
    // if (pl == 1.000012) printf("Cb: %f\n", Var[mod->indexCb]);
    // constraint_cost += penalty_bound(Var, mod->indexPb, 
    //                 -mod->discharge_rate*Var[mod->indexCb], 
    //                 mod->charge_rate*Var[mod->indexCb], pl, pq) ; 

    for (int p =0 ; p<mod->n_p-1; p++) {
        constraint_cost += penalty_bound_elem(Var[mod->indexPprev[0]+p], 0, Var[mod->indexPprev[0]+p+1], pl, pq);
    }
    free(Egrid);
    if (pl == 1.000012) {
        printf("\nTotal: %f\n", total);
        printf("Constraint cost: %f\n", constraint_cost);
        printf("Total + constraint cost: %f\n\n", total+constraint_cost);
        printf("Excess: %f\n", excess);
        printf("Power price: %f\n", power_price);
        printf("Egrid price: %f\n", Egrid_price);
        printf("bat_price: %f\n", bat_price);
    }
    return total+constraint_cost;
}

// We have the eqeuivalent of the model class in python.


void init_feasible_var(double *Var, double *bounds[2], int *indPb, int *indPprev, int indCb, double charge_rate, double discharge_rate, double Effc, double Effd, double deltat) {
    // Init the Pb variables 
    // We need a random feasible solution
    // The idea will be to begin at 0.2 of the battery capacity
    // and then generate random values that will be feasible regarding to the SOC
    // and the power constraints
    double Cb = Var[indCb];
    int ind = indPb[0];
    double SOC = 0.2 * Cb;
    double rd ;
    double E_t ;
    for (int i = ind; i < indPb[1]; i++) {
        rd = ((double) rand() / RAND_MAX - 0.5)*2.0;
        // printf("SOC(t-1) %f rd: %f\n", SOC, rd);
        if (rd >= 0) {
            E_t = rd * charge_rate * Cb * Effc * deltat;
            if (SOC + E_t > Cb) {
                Var[i] = (Cb - SOC) / (charge_rate * Effc * deltat * Cb);
                // printf("Var[i] result %f, num : %f, denum : %f, Effc, deltat, \n",);
                SOC = Cb;
            }
            else {
                SOC = SOC + E_t;
                Var[i] = rd;
            }
        } else {
            E_t = rd * discharge_rate * Cb / Effd * deltat;
            if (SOC + E_t < 0.2*Cb) {
                Var[i] = (0.2*Cb - SOC) / (discharge_rate / Effd * deltat * Cb);
                SOC = 0.2*Cb;
            }
            else {
                SOC = SOC + E_t;
                Var[i] = rd;
            }
        }
        // printf("SOC: %f, Var[%d] : %f, Cb : %f\n", SOC, i, Var[i], Cb);
    }
    // Init the Pprev variables
    double last_val = bounds[indPprev[0]][0] ;
    for (int i = indPprev[0]; i < indPprev[1]; i++) {
        Var[i] = last_val + ((double)rand() / RAND_MAX) * (bounds[i][1] - last_val) ;
        last_val = Var[i] ;
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
