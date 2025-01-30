def calculate_price(Pprev, Pcons, Econs, Eautocons, TP, TE, TEauto, Time, tep, Kp, Nbdays, Time_in_month, opti = True) :
    # For it to be faster, we could rewrite this function in a C code and import it 
    # -> it should speed up the evaluation of the objective function
    # Here optimization is fast so not necessary
    Se = 0
    Seauto = 0
    Spena = 0
    Sp = 0
    Se_p = [0 for k in range(6)]
    Spena_P = [0.00001 for k in range(6)]
    for p in range(len(TP)) :
        Sp += TP[p]*Pprev[p]*Nbdays
        if opti :  
            time_table = Time[p].value 
        else :
            time_table = Time[p]
        for t in time_table: 
            m = 0 
            while t not in Time_in_month[m] : 
                m+=1
            Se += TE[m][p]*(Econs[t]-Eautocons[t])
            Se_p[p] += TE[m][p]*(Econs[t]-Eautocons[t])
            Seauto += TEauto[p]*Eautocons[t]
            Spena_P[p] += ((Pcons[t] - Pprev[p] + abs(Pcons[t] - Pprev[p]))/2)**2 
            
            # x+abs(x) = 2x if x>0, x+abs(x) = 0 if x < 0
        Spena_P[p] = Spena_P[p]**(1/2)
        Spena += Kp[p]*tep*Spena_P[p]
    return Se + Seauto + Spena + Sp


double calculate_price(double *Pprev, double *Pcons, 
                    double *Econs, double *Eautocons, 
                    double *TP, double **TE, double *TEauto, 
                    double *Time, double tep, double *Kp, int Nbdays, int **Time_in_month) {
    // Time_in_month should be the only array for all of this to work well
    double Se = 0;
    double Seauto = 0;
    double Spena = 0;
    double Sp = 0;
    double Se_p[6] = {0};
    double Spena_P[6] = {0.00001};
    for (p = 0 ; p < 6 ; p++) {
        Sp += TP[p]*Pprev[p]*Nbdays;
        int* time_table;
        time_table = Time[p];
