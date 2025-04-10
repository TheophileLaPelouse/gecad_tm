"""
Optimization of with peer and batteries

Create the optimization model and then use the two previous files to load the parameters of the opti framework to do tests

Optimization model : 
Same as before with just the battery but adding peer2peer exchange.
For this need to considerate every prosumers and contract so different way of treating the thing, using the dico defined in opti_peer_prosumers.py

Optimization framework : 
- run the optimization model with representative days 
- run use the battery as parameters and Pcontracted to compute optimization over small intervals
- Compute by putting everything into a big model.
"""