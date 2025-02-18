#ifndef META_H
#define META_H

#include "meta.h"

#endif // META_H

// For the moment test with the technique where inertia evolve with a gaussian
void init_particle(Particle *part, Model *model, double pl, double pq, double *bounds[2]) {
    part->mod = model;
    part->pl = pl;
    part->pq = pq;
    part->Var = malloc(model->Var_size * sizeof(double));
    part->Speed = malloc(model->Var_size * sizeof(double));
    part->VarBest = malloc(model->Var_size * sizeof(double));
    part->bounds = malloc(model->Var_size * sizeof(double[2]));
    // srand(time(NULL));
    part->pl = pl;
    part->pq = pq;
    part->wm = (double)rand() / RAND_MAX;
    part->wb = (double)rand() / RAND_MAX;
    part->wp = (double)rand() / RAND_MAX;
    for (size_t i = 0; i < model->Var_size; i++) {
        part->bounds[i][0] = bounds[i][0];
        part->bounds[i][1] = bounds[i][1];
        part->Var[i] = bounds[i][0] + ((double)rand() / RAND_MAX) * (bounds[i][1] - bounds[i][0]);
        part->VarBest[i] = part->Var[i];
        part->Speed[i] = ((double)rand() / RAND_MAX - 0.5) * (bounds[i][1] - bounds[i][0]);
    }
    part->fitness = obj(part->mod, part->Var, part->pl, part->pq) ;
}

int compare_part(const void *a, const void *b) {
    Particle *part1 = (Particle *)a;
    Particle *part2 = (Particle *)b;
    if (part1->fitness < part2->fitness) return -1;
    if (part1->fitness > part2->fitness) return 1;
    return 0;
}
void sort_particles(Particle *population, int nb_pop) {
    qsort(population, nb_pop, sizeof(Particle), compare_part) ;
}

void copy_var_p(Particle *part1, Particle *part2) {
    // printf("Alors part1==part2 ? %d\n", part1==part2);
    if (part1 == part2) {
        for (size_t i = 0 ; i < part1->mod->Var_size ; i++) {
            part1->VarBest[i] = part1->Var[i] ;
        }
        return ;
    }
    else {
        for (size_t i =0 ; i < part1->mod->Var_size ; i++) {
            part1->Var[i] = part2->Var[i] ;
        }
    }
}

void update_part_weight(Particle *part) {
    double u ; 
    u = generate_normal_random() ;
    part->wm = part->wm + u ;
    if (part->wm > 1) part->wm = 1 ;
    if (part->wm < 0) part->wm = 0 ;
    u = generate_normal_random() ;
    part->wb = part->wb + u ;
    if (part->wb > 1) part->wb = 1 ;
    if (part->wb < 0) part->wb = 0 ;
    u = generate_normal_random() ;
    part->wp = part->wp + u ;
    if (part->wp > 1) part->wp = 1 ;
    if (part->wp < 0) part->wp = 0 ;
}

Particle PSO(Model *model, double *bounds[2], int nb_pop, int nb_gen, double pl, double pq, int last_element, double threshold) {
    printf("On entre dans la fonction %d\n", nb_pop);
    Particle *Pop = malloc(nb_pop * sizeof(Particle));
    double best_fit ;
    int k = 0 ;
    
    printf("Particle initialisation\n");
    for (int i = 0; i < nb_pop; i++) {
        
        init_particle(&Pop[i], model, pl, pq, bounds);
        if (i == 0) {
            best_fit = Pop[i].fitness ;
            k = i ;
        }
        else {
            if (Pop[i].fitness < best_fit) {
                best_fit = Pop[i].fitness ;
                k = i ;
            }
        }
    }
    printf("Best fitness: %f\n", best_fit);
    Particle best_indiv ;
    init_particle(&best_indiv, model, pl, pq, bounds) ;
    printf("debug1\n");
    copy_var_p(&best_indiv, &Pop[k]) ;
    printf("debug2\n");
    best_indiv.fitness = Pop[k].fitness ;
    double *last_obj ;
    last_obj = malloc(nb_gen * sizeof(double));
    int len = 0 ;
    double obj_val ;
    int c = 0 ;

    double global_wm ;
    double global_wb ;
    double global_wp ;
    double rm ; 
    double rb ;
    while  (c < nb_gen && !(no_evolution(last_obj, threshold, last_element, len))) {
        printf("\n");
        printf("Generation %d:\n", c);
        printf("Best fitness: %f\n", best_indiv.fitness);
        printf("fitness of the first particle: %f\n", Pop[0].fitness);
        printf("fitness of the second particle: %f\n", Pop[1].fitness);
        printf("\n");
        // global_wb = (2.5 - 0.5)*c/1000 + 0.5 ;
        // global_wm = 0.5 - (2.5 - 0.5)*c/1000 ;
        global_wb = 0.5 ;
        global_wm = 2.5 ;
        global_wp =  ((1/2*(global_wm + global_wb) - 1) + 1)/2;
        for (int k=0 ; k< nb_pop ; k++) {
            // update_part_weight(&Pop[k]) ;
            Pop[k].wm = global_wm ;
            Pop[k].wb = global_wb ;
            Pop[k].wp = global_wp ;
            for (size_t i = 0; i < model->Var_size; i++) {
                rm = (double)rand() / RAND_MAX ;
                rb = (double)rand() / RAND_MAX ;
                // rm =1;
                // rb =1 ;
                Pop[k].Speed[i] = Pop[k].wp * Pop[k].Speed[i] + Pop[k].wm * rm * (Pop[k].VarBest[i] - Pop[k].Var[i]) + Pop[k].wb * rb * (best_indiv.Var[i] - Pop[k].Var[i]) ;
                Pop[k].Var[i] += Pop[k].Speed[i] ;
                // if (Pop[k].Var[i] > Pop[k].bounds[i][1]) init_particle(&Pop[k], model, pl, pq, bounds) ;
                // if (Pop[k].Var[i] < Pop[k].bounds[i][0]) init_particle(&Pop[k], model, pl, pq, bounds) ;
            }
            obj_val = obj(Pop[k].mod, Pop[k].Var, Pop[k].pl, Pop[k].pq) ;
            if (obj_val < Pop[k].fitness) {
                Pop[k].fitness = obj_val ;
                copy_var_p(&Pop[k], &Pop[k]) ;
                if (obj_val < best_indiv.fitness) {
                    best_indiv.fitness = obj_val ;
                    copy_var_p(&best_indiv, &Pop[k]) ;
                }
            }
        }
        c += 1 ;
    }
    for (int i = 0; i < nb_pop; i++) {
        free(Pop[i].Var);
        free(Pop[i].Speed);
        free(Pop[i].VarBest);
        free(Pop[i].bounds);
    }
    free(Pop);
    free(last_obj);
    return best_indiv ;
}