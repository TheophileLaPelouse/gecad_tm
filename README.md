Small guide to use the code (for linux/mac users) : 

First create (if you want) an environnement for this code specifically,
`python3 -m venv <name of your environnement>`
Then to activate the environnement,
`source <path to env folder>/bin/activate`

Then copy this work if not already done using `git clone https://github.com/TheophileLaPelouse/gecad_tm`.
To install all the library of my own environnement type : 
`pip install -r requirements.txt`
-> It can take some time, if you want to be sure it is not locked somewhere, add `--verbose` to it.

prices.py treat the data from the excel
And the opti files are meant for the optimisation, opti.py is the P contracted optimisation.
