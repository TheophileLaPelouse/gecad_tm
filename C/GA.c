#ifndef META_H
#define META_H

#include "meta.h"

#endif // META_H

void init_individual(Individual *ind, Model *model, double pl, double pq, double *bounds[2]) {
    ind->mod = model;
    ind->pl = pl;
    ind->pq = pq;
    ind->Var = malloc(model->Var_size * sizeof(double));
    ind->bounds = malloc(model->Var_size * sizeof(double[2]));
    // srand(time(NULL));
    for (size_t i = 0; i < model->Var_size; i++) {
        ind->bounds[i][0] = bounds[i][0];
        ind->bounds[i][1] = bounds[i][1];
        ind->Var[i] = bounds[i][0] + ((double)rand() / RAND_MAX) * (bounds[i][1] - bounds[i][0]);
        
        // printf("Var_size: %zu\n", model->Var_size);
        // printf("bounds: %f %f\n", bounds[i][0], bounds[i][1]);
        // printf("Var[%zu]: %f\n", i, ind->Var[i]);
    }
    
    ind->fitness = obj(ind->mod, ind->Var, ind->pl, ind->pq) ; 
}

void copy_var(Individual *ind1, Individual *ind2) {
    for (size_t i =0 ; i < ind1->mod->Var_size ; i++) {
        ind1->Var[i] = ind2->Var[i] ;
    }
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

// void linear_random_crossover(Individual *par1, Individual *par2, Individual *child1, Individual *child2, double fac) {
//     double rd = (double)rand() / (double)RAND_MAX ;
//     rd = rd*fac ;
//     for (int i = 0; i < par1->mod->Var_size; i++) {
//         child1->Var[i] = (1 + rd) * par2->Var[i] - rd * par1->Var[i];
//         child2->Var[i] = (1 + rd) * par1->Var[i] - rd * par2->Var[i];
//         child1->fitness = obj(child1->mod, child1->Var, child1->pl, child1->pq) ;
//         child1->fitness = obj(child2->mod, child2->Var, child2->pl, child2->pq) ;
//     }
// }

void linear_random_crossover(Individual *par1, Individual *par2, Individual *child1, Individual *child2, double fac) {
    double rd = (double)rand() / (double)RAND_MAX ;
    rd = rd*fac ;
    for (size_t i = 0; i < par1->mod->Var_size; i++) {
        // printf("i: %d\n", i);
        child1->Var[i] = (1 - rd) * par2->Var[i] + rd * par1->Var[i];
        child2->Var[i] = (1 - rd) * par1->Var[i] + rd * par2->Var[i];
    }
    child1->fitness = obj(child1->mod, child1->Var, child1->pl, child1->pq) ;
    child1->fitness = obj(child2->mod, child2->Var, child2->pl, child2->pq) ;
}

void random_mutation(Individual *Pop, int nb_pop, double mutation_rate, int c, int nb_gen, double min_val, double max_val) {
    double mut_fac ;
    double lb ;
    double ub ;
    double mutation_value ;
    double mutated_var ;
    for (int k=0; k<nb_pop; k++) {
        int flag = 0 ;
        for (size_t i=0; i<Pop[k].mod->Var_size; i++) {
            double rd = (double)rand()/RAND_MAX ; 
            if (rd<mutation_rate) {
                flag = 1 ; 
                lb = Pop[k].bounds[i][0] ; 
                ub = Pop[k].bounds[i][1] ;
                // double mut_fac = min_val + (1 - min_val) * (double)(nb_gen - c) / nb_gen ;
                mut_fac = min_val + (max_val - min_val) * (exp(-0.01 * (double)c));
                // double mut_fac = best_known/(ub-lb) ;
                mutation_value = generate_normal_random()*(ub - lb)/6*mut_fac ;
                mutated_var = Pop[k].Var[i] + mutation_value ; 
                if (mutated_var > ub) mutated_var = ub ;
                if (mutated_var < lb) mutated_var = lb ;
                Pop[k].Var[i] = mutated_var ;
            }
        }
        if (flag) Pop[k].fitness = obj(Pop[k].mod, Pop[k].Var, Pop[k].pl, Pop[k].pq) ;
    }
    printf("mut_fac : %f\n", mut_fac);
}

Individual GA(Model *mod, double *opti_bounds[2], int nb_pop, int nb_gen, double pl, double pq
, double mutation_rate, int last_element, double threshold, double fac, double min_mut, double max_mut) {
    Individual *Pop = malloc(nb_pop * sizeof(Individual));
    for (int i = 0; i < nb_pop; i++) {
        init_individual(&Pop[i], mod, pl, pq, opti_bounds);
    }
    for (size_t i = 0; i < Pop[0].mod->Var_size; i++) {
            printf(" Var[%zu]: %f", i, Pop[0].Var[i]);
        }
    printf("\nC etait les variables de 0\n");
    if (!(nb_pop/2 == (int) ((double) nb_pop/2.0))) nb_pop = nb_pop+1 ;
    int current_pop = nb_pop;
    double *last_obj ;
    last_obj = malloc(nb_gen * sizeof(double));
    int len = 0 ;
    Individual best_indiv ;
    init_individual(&best_indiv, mod, pl, pq, opti_bounds) ;
    // for (size_t i = 0; i < best_indiv.mod->Var_size; i++) {
    //         printf(" Var[%zu]: %f", i, best_indiv.Var[i]);
    //     }
    // printf("\nC etait les variables de best_indiv\n");

    int chosen[nb_pop/2] ;
    for (int i = 0; i < nb_pop/2; i++) {
        chosen[i] = i ;
    }
    int pairs[nb_pop/2/2][2] ;

    clock_t start_time ;
    clock_t start_time2 ;
    clock_t start_time3 ;
    clock_t start_time4 ;
    clock_t end_time ;
    int c = 0 ;
    while (c < nb_gen && !(no_evolution(last_obj, threshold, last_element, len))) {
        start_time = clock();
        sort_population(Pop, nb_pop) ;
        if (len == 0) {
            len += 1 ;
            last_obj[0] = Pop[0].fitness ;
        }
        else {
            last_obj[len] = Pop[0].fitness ; 
            len += 1 ;
        }
        if (Pop[0].fitness < last_obj[len-1]) {
            copy_var(&best_indiv, &Pop[0]) ;
            best_indiv.fitness = Pop[0].fitness ;
        }
        end_time = clock();
        printf("Time sort: %f\n", (double)(end_time - start_time) / CLOCKS_PER_SEC);
        start_time2 = clock();
        printf("\n");
        printf("Generation %d:\n", c);
        printf("Best fitness: %f\n", Pop[0].fitness);
        printf("Just to verify model Econs: %f\n", Pop[0].mod->Econs[0]);
        // printf("Best individual variables: \n");
        // for (size_t i = 0; i < Pop[0].mod->Var_size; i++) {
        //     printf("Var[%zu]: %f", i, Pop[0].Var[i]);
        // }
        // printf("Best individual variables: \n");
        printf("\n");

        // Selection
        current_pop = nb_pop/2 ; 
        shuffle(chosen, nb_pop/2) ;
        for (int i = 0; i < nb_pop/2/2; i++) {
            pairs[i][0] = chosen[2*i] ;
            pairs[i][1] = chosen[2*i+1] ;
        }
        end_time = clock();
        printf("Time shuffle and pairing: %f\n", (double)(end_time - start_time2) / CLOCKS_PER_SEC);
        start_time3 = clock();

        // Crossover
        for (int i=0; i<nb_pop/2/2 ; i++) {
            int ch1 = current_pop ;
            int ch2 = current_pop + 1 ;
            int p1 = pairs[i][0] ;
            int p2 = pairs[i][1] ;
            current_pop += 2 ; 
            linear_random_crossover(&Pop[p1], &Pop[p2], &Pop[ch1], &Pop[ch2], fac) ;
        }
        end_time = clock();
        printf("Time crossover: %f\n", (double)(end_time - start_time3) / CLOCKS_PER_SEC);
        start_time4 = clock();
        // Mutation
        random_mutation(Pop, nb_pop, mutation_rate, c, nb_gen, min_mut, max_mut) ;
        c += 1 ;
        end_time = clock();
        printf("Time mutation: %f\n", (double)(end_time - start_time4) / CLOCKS_PER_SEC);
        end_time = clock();
        printf("Time taken: %f\n", (double)(end_time - start_time) / CLOCKS_PER_SEC);
    }
    best_indiv.list_obj = malloc(len * sizeof(double));
    if (best_indiv.list_obj == NULL) {
        fprintf(stderr, "Failed to allocate memory for best_indiv.list_obj\n");
        return best_indiv;
    }
    for (int i = 0; i < len; i++) {
        printf("last_obj[%d]: %f\n", i, last_obj[i]);
        best_indiv.list_obj[i] = last_obj[i];
    }
    best_indiv.len = len;
    return best_indiv ;
}