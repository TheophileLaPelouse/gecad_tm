Small guide to use the code (for linux/mac users) : 

First create (if you want) an environnement for this code specifically,
`python3 -m venv <name of your environnement>`
Then to activate the environnement,
`source <path to env folder>/bin/activate`

Then copy this work if not already done using `git clone https://github.com/TheophileLaPelouse/gecad_tm`.
To install all the library of my own environnement type : 
`pip install -r requirements.txt`
-> It can take some time, if you want to be sure it is not locked somewhere, add `--verbose` to it.

---

# Overview of the code 

In this repository there is all the codes I wrote for the optimisation of P contracted values and battery.

Here how we do an optimization : 
- First step : Treat the data
- Second step : Define the optimization model using pyomo or homemade code (for meta heuristic)
- Third step : Give to the optimization model the treated data
- Fourth step : Compute and save the results

In the code, during Second and Third step there are a lot of tests being done.

The first step is done using the function defined in `prices.py` and the other prices files, and there is also `representative_days.py` which completes it by providing method to create representative days data. The second step is done in all the code named `opti`, as well as in the C part. The third and Fourth steps are done in general in the same opti files but also in files with names beginning by `result`.

# First step

## prices.py

This file defines all the used global data such as period_hours, as well as function to treat the different excel file, namely treat_data. A lot of others utility function are defined at the end of the file.

The other files with a name beginning by prices define the array for the prices of each companies defined in their invoices.

## representative_days.py

This file define a lot of function to select days using different methods. The first used one is select_days2 which uses the ratio production consumption. The other method are different variants using K mean clustering methods. The main function that will be used in other files is create_data

# Second step

## Opti files 

So opti.py is the simple optimisation to optimize only the P contracted values. opti_battery is the one that put a battery and try to find the optimal battery management. opti_h_bat is a file that optimize the P contracted values assuming a known behaviour of the battery usage. And finally metaheuristic_opti is a python implementation of some metaheuristic solvers.

On the opti file, we will first import the necessary ressources from the First step. Then define a function named build_model that take a lot of keyword arguments so that we can test all there is to test. This function build the optimisation model that will be used to solve the problems.

After this those files are composed of a whole lot of tests.

## C files 

The C files are implementation of GA and PSO for our model. They can be run using the file tests.py that uses the First step to have the input data, and then make the necessary conversion to make the variables as input for the C code. Recovering the output on python does not work really well at the moment but is not necessary.

# Third and Fourth step

Those two steps are in the tests in the opti files, representative_days.py and result files. They consist of calling the optimization function and then plot, save csv...


