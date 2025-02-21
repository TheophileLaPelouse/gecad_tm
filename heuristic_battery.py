
import matplotlib.pyplot as plt


from prices import define_time, Econs, Eautocons as Eprod, TEauto, tep, Kp, period_hours, full_date, last_day, search_dico

Pcons = [val/0.25 for val in Econs]
TP = [0.066889, 0.040255, 0.031037, 0.025345, 0.004733, 0.002652]
TE = [
      [0.176631, 0.170670, 0, 0, 0, 0.125919], 
      [0.126656, 0.131860, 0, 0, 0, 0.092685], 
      [0, 0.126656, 0.131860, 0, 0, 0.073864], # March is not in the invoices so the figures are based on february
      [0, 0, 0, 0.066662, 0.079025, 0.073864], 
      [0, 0, 0, 0.079119, 0.094265, 0.097955], 
      [0, 0, 0.124591, 0.143611, 0, 0.138129], 
      [0.150950, 0.179345, 0, 0, 0, 0.148744], 
      [0, 0, 0.165865, 0.181045, 0, 0.169511], 
      [0, 0, 0.145440, 0.167703, 0, 0.150691], 
      [0, 0, 0, 0.137424, 0.169721, 0.133218], 
      [0, 0.195679, 0.210640, 0, 0, 0.172424]
      ]

#%%

def allocation_t(Pcons, Pprod, Pmax, Pmin, SOC, Emin, Emax, deltat) : 
    # print("Pcons :", Pcons, "Pprod :", Pprod, "SOC :", SOC)
    # print("Pcons - Pprod :", Pcons - Pprod)
    # print("SOC - Emin :", SOC - Emin, "EMax - SOC :", Emax - SOC)
    
    if Pcons > Pprod : 
        if SOC > Emin :
            alloc = min(Pcons - Pprod, Pmax)
            if SOC - alloc*deltat < Emin : 
                alloc = (SOC - Emin)/deltat
        else :
            alloc = 0
    else :
        if SOC < Emax :
            alloc = max(Pcons - Pprod, Pmin)
            if SOC + alloc*deltat > Emax : 
                alloc = (Emax - SOC)/deltat
        else :
            alloc = 0
    # print("valeur ", alloc)
    return alloc

def create_profile(Econs, Cb, Effc, Effd, charge_rate, dcharge_rate, full_date, SOC0 = 0.5) : 
    SOC = [SOC0*Cb]
    Pd = []
    Pc = []
    Pmax = Cb*charge_rate
    Pmin = -Cb*dcharge_rate
    for k in range(1, len(full_date)) : 
        deltat = (full_date[k] - full_date[k-1]).total_seconds()/60/60
        alloc = allocation_t(Econs[k]/deltat, Eprod[k]/deltat, Pmax, Pmin, SOC[k-1], Cb*0.2, Cb*0.8, deltat)*deltat
        SOC.append(SOC[k-1] - alloc/Effd*(alloc>0) - alloc*Effc*(alloc<0))
        Pd.append(alloc*(alloc>0))
        Pc.append(-alloc*(alloc<0))
    return SOC, Pd, Pc

#%% plot

if __name__ == '__main__' :  
    n = -1
    SOC, Pd, Pc = create_profile(Econs, 50, 0.95, 0.95, 0.5, 0.5, full_date[:n])
    plt.plot(full_date[:n], SOC)
    plt.show()
    
#%% test 

if __name__ == '__main__' : 
    print()
    
#%% to import 

# SOC = {}
# SOC[10] = create_profile(Econs, 10, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[20] = create_profile(Econs, 20, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[30] = create_profile(Econs, 30, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[40] = create_profile(Econs, 40, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[50] = create_profile(Econs, 50, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[60] = create_profile(Econs, 60, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[70] = create_profile(Econs, 70, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[80] = create_profile(Econs, 80, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[90] = create_profile(Econs, 90, 0.95, 0.95, 0.5, 0.5, full_date)
# SOC[100] = create_profile(Econs, 100, 0.95, 0.95, 0.5, 0.5, full_date)
