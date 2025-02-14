#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
# typedef struct {
#     int entier;
#     double reel;
#     size_t *tab1 ;
#     size_t **tab2 ;
#     size_t ***tab3 ;
# } lol ;

# lol* init_lol(int num, double real, size_t *tab1, size_t **tab2, size_t ***tab3) {
#     lol *l = (lol*)malloc(sizeof(lol));
#     if (l == NULL) {
#         fprintf(stderr, "Failed to allocate memory for lol\n");
#         return NULL;
#     }
#     l->entier = num ;
#     l->reel = real ;
#     l->tab1 = tab1 ;
#     l->tab2 = tab2 ;
#     l->tab3 = tab3 ;
#     printf("tab3: %p\n", tab3);
#     return l ;
# }


import ctypes 

class Lol(ctypes.Structure):
    _fields_ = [
        ("entier", ctypes.c_int),
        ("reel", ctypes.c_double),
        ("tab1", ctypes.POINTER(ctypes.c_size_t)),
        ("tab2", ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t))),
        ("tab3", ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t))))
    ]


num =1 
real = 2.0
tab1 = [1, 2, 3]
tab2 = [[1, 2, 3], [4, 5, 6]]
tab3 = [[[1, 2, 3], [4, 5, 6]], [[7, 8], [10, 11, 12]]]

fun = ctypes.CDLL('libfun.so')

tab1 = (ctypes.c_size_t * len(tab1))(*tab1)
tab2 = (ctypes.POINTER(ctypes.c_size_t) * len(tab2))(*[(ctypes.c_size_t * len(tab2[i]))(*tab2[i]) for i in range(len(tab2))])
tab3 = (ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)) * len(tab3))(*[
                            (ctypes.POINTER(ctypes.c_size_t) * len(tab3[month]))(*[
                                (ctypes.c_size_t * len(tab3[month][period]))(*tab3[month][period])
                                for period in range(len(tab3[month]))
                            ])
                            for month in range(len(tab3))
                        ])

fun.init_lol.argtypes = [ctypes.c_int, ctypes.c_double, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)), ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(ctypes.c_size_t)))]

# fun.init_lol.restype = ctypes.POINTER(Lol)
fun.init_lol.restype = ctypes.c_void_p 

l = fun.init_lol(num, real, tab1, tab2, tab3)
print(l)
print('success')

