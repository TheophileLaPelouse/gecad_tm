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
    double Effc ;
    double Effd ;
    double **TE;
    double *TP;
    int indexPprev[2];
    int Nbdays;
    double *Kp;
    double tep;
    int indexCb ;
    double TB;
    double batterie_life;
    double TBm;
    double *SOC; 
    size_t *tot_time;
    size_t n_tot_time;
    size_t ***time_month;
    size_t **n_time_month;
    int *months;
    int n_m ;
    int *periods;
    int n_p;
} Model;

typedef struct {
    Model *mod ; 
    double *Var ;
    double pl ;
    double pq ;
    double fitness ;
    double (*bounds)[2];
    double *list_obj ;
    int len ;
} Individual ;

typedef struct {
    Model *mod ; 
    double *Var ;
    double *Speed ;
    double *VarBest ;
    double wm ; //inertia memory
    double wb ; // inertia best
    double wp ; // inertia particle
    double pl ;
    double pq ;
    double fitness ;
    double (*bounds)[2];
    double *list_obj ;
    int len ;
} Particle ;

// Model functions
Model* init_model(size_t var_size, double *Econs, double *Eprod, int indexPb[2], double deltat, double charge_rate, double discharge_rate, double Effc, double Effd, double **TE, double *TP, int indexPprev[2], int Nbdays, double *Kp, double tep, int indexCb, double TB, double batterie_life, double TBm, double *SOC, size_t *tot_time, size_t n_tot_time, size_t ***time_month, size_t **n_time_month, int *months, int n_m, int *periods, int n_p) ;
void free_model(Model *model) ;
double obj(Model *mod, double *Var, double pl, double pq) ;
double penalty_bound_elem(double x, double a, double b, double pl, double pq) ;
double penalty_bound(double *var, int *indices, double varlb, double varub, double pl, double pq) ;

// GA functions
Individual GA(Model *model, double *bounds[2], int nb_pop, int nb_gen, double pl, double pq, double mutation_rate, int last_element, double threshold, double fac, double min_mut, double max_mut) ;
void init_individual(Individual *ind, Model *model, double pl, double pq, double *bounds[2]) ;
int no_evolution(double *last_obj, double threshold, int last_element, int len) ;
int compare_indiv(const void *a, const void *b) ;
void sort_population(Individual *Pop, int nb_pop) ;
void copy_var(Individual *ind1, Individual *ind2) ;

// PSO functions
int compare_part(const void *a, const void *b) ;
void sort_particles(Particle *Pop, int nb_pop) ;
void copy_var_p(Particle *ind1, Particle *ind2) ;
void init_particle(Particle *ind, Model *model, double pl, double pq, double *bounds[2]) ;
void update_part_weight(Particle *part) ; 
Particle PSO(Model *model, double *bounds[2], int nb_pop, int nb_gen, double pl, double pq, int last_element, double threshold) ;

// Utils
double generate_normal_random();