#ifndef META_H
#define META_H

#include "meta.h"

#endif // META_H

int main() {
    printf("Hello, World!\n");
    return 0;

}


void* run_comp(
    int code, 
    double *opti_bounds[2], int nb_pop, int nb_gen, double pl, double pq, double mutation_rate, int last_element, double threshold, double fac, double min_mut, double max_mut,
    size_t Var_size, double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, 
    double discharge_rate, double **TE, double *TP, int indexPprev[2], int Nbdays, double *Kp, 
    double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, 
    size_t n_tot_time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) {
    
    Model *model = init_model(Var_size, Econs, Eprod, indexPb, deltat, charge_rate, discharge_rate, TE, TP, indexPprev, Nbdays, Kp, tep, indexCb, TB, batterie_life, TBm, SOC, tot_time, n_tot_time, time_month, n_time_month, months, n_m, periods, n_p);
    printf("Model Econs avant : %f\n", model->Econs[0]);
    for (int i = 0; i < Var_size; i++) {
        printf("opti_bounds[%d][0]: %f, opti_bounds[%d][1]: %f\n", i, opti_bounds[i][0], i, opti_bounds[i][1]);
    }
    if (code == 1) {
    Individual best_indiv = GA(model, opti_bounds, nb_pop, nb_gen, pl, pq, mutation_rate, last_element, threshold, fac, min_mut, max_mut);
    printf("Model Econs après : %f\n", model->Econs[0]);
    Individual *best_indiv_ptr = (Individual *)malloc(sizeof(Individual));
    if (best_indiv_ptr == NULL) {
        fprintf(stderr, "Failed to allocate memory for best_indiv_ptr\n");
        return NULL;
    }
    *best_indiv_ptr = best_indiv;
    // Plotting best_indiv.list_obj
    FILE *resultsFile = fopen("results_c.dat", "w");
    if (resultsFile) {
        fprintf(resultsFile, "Generation Fitness\n");
        for (int i = 0; i < best_indiv.len; i++) {
            fprintf(resultsFile, "%d %f\n", i, best_indiv.list_obj[i]);
        }
        fclose(resultsFile);
    } else {
        fprintf(stderr, "Failed to open results_c.dat for writing\n");
    }
    return best_indiv_ptr;
    }
    if (code == 2) {
        printf("PSO\n");
        Particle best_particle = PSO(model, opti_bounds, nb_pop, nb_gen, pl, pq, last_element, threshold);
        printf("Le best du best de PSO: %f\n", best_particle.fitness);
        Particle *best_particle_ptr = (Particle *)malloc(sizeof(Particle));
        if (best_particle_ptr == NULL) {
            fprintf(stderr, "Failed to allocate memory for best_indiv_ptr\n");
            return NULL;
        }
        *best_particle_ptr = best_particle;
        return best_particle_ptr;
    }
    // free_model(model);

    // Time test 
    // clock_t start_time = clock();
    // int sum = 0;
    // for (size_t i = 0; i < best_indiv.mod->Var_size; i++) {
    //     sum += best_indiv.Var[i];
    // }
    // clock_t end_time = clock();
    // printf("Time to loop over best_indiv->Var: %f seconds\n", (double)(end_time - start_time) / CLOCKS_PER_SEC);

    // start_time = clock();
    // sum = obj(best_indiv.mod, best_indiv.Var, best_indiv.pl, best_indiv.pq);
    // end_time = clock();
    // printf("time for obj: %f seconds\n", (double)(end_time - start_time) / CLOCKS_PER_SEC); 
    else {
        return NULL;
    }
}