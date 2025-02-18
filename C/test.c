#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
typedef struct {
    int entier;
    double reel;
    size_t *tab1 ;
    size_t **tab2 ;
    size_t ***tab3 ;
} lol ;

lol* init_lol(int num, double real, size_t *tab1, size_t **tab2, size_t ***tab3) {
    lol *l = (lol*)malloc(sizeof(lol));
    if (l == NULL) {
        fprintf(stderr, "Failed to allocate memory for lol\n");
        return NULL;
    }
    l->entier = num ;
    l->reel = real ;
    l->tab1 = tab1 ;
    l->tab2 = tab2 ;
    l->tab3 = tab3 ;
    printf("tab3: %p\n", tab3);
    return l ;
}
