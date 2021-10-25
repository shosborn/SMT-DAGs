# -*- coding: utf-8 -*-
"""
Created on Tue Oct 19 16:18:13 2021

@author: simsh
"""

#!/usr/bin/python3

import os.path
from multiprocessing.pool import ThreadPool
import sys
import multiprocessing as mp

import rtasConstants as constants
from dagTask import dagTask
import makePairs as ILP
from random import uniform


outputFile="10-24-1521-layers-randomUtil.csv"


#How to optimize performance?
#I get ten nodes at a time.
#Save the giant DAGs for last.
#Priority: get some complete scenarios.
#Start with the easiest cases: low subtask count, high p.
#Write the graph code so that problems can be found early.
#Six graphs per page, each page gives one count+prob combo?
#Then each run will produce one page of graphs.

#Today: get the new batch running; write graph code.

INFINITY=float('inf')


count=int(sys.argv[1])
#prob=float(sys.argv[2])
maxDist=int(sys.argv[2])
maxSol=int(sys.argv[3])
numLayers=int(sys.argv[4]) #set to 0 to keep using Erdos-Renyi
PROB_LIST=[0.1, 0.3, 0.5, 0.7, 0.9, 1]
UTIL_LIST=[constants.NARROW, constants.WIDE]
SMT_LIST=[constants.OPTIMIST, constants.OK, constants.PESSIMIST]


dagsPerScenario=100
deadlinesPerDag=1

#what can Gurobi use per DAG?
maxThreads=1

'''
count=10
PROB_LIST=[0.5]
maxDist=5
maxSol=5
numLayers=2
UTIL_LIST=[constants.NARROW, constants.WIDE]
SMT_LIST=[constants.OPTIMIST, constants.OK, constants.PESSIMIST]


dagsPerScenario=5
deadlinesPerDag=1
'''

#utilStep=0.25



configurations=[]
for util in UTIL_LIST:
    for smt in SMT_LIST:
        for i in range(dagsPerScenario):
            for prob in PROB_LIST:
                config={}
                config["c"]=count
                config["u"]=util
                config["s"]=smt
                config["p"]=prob
                config["i"]=len(configurations)+i
                config["nL"]=numLayers
                configurations.append(config)
                
SYNC = False

#the input to run_test, 'config', is one of the many dictionaries contained in the list 'configurations'
def run_test(config):
    #the '**' notation indicates that dictionary config is to be treated as a set of keyword arguments
    runDagFamily(**config)


def runDagFamily(u, s, p, c, i, nL):           
    scenarioList=[str(u), str(s), str(p), str(c), str(maxDist), str(maxSol)]
    scenarioString=','.join(scenarioList)
    #last chance to add some parallelism
    myDAG=dagTask(fileName="random", targetNodeCount=c, targetCost=0, 
  nodeUtilDist=u, smtDist=s, erdoRenyiP=p, numLayers=numLayers)
    
    #make DAG using the fork-join model
    #I need fatter DAGs
    
    minDeadline=myDAG.length    # util>1, but hard to know by how much

    #deadline=uniform(minDeadline, myDAG.totalCost)
    
    
    #baseUtil=myDAG.totalCost/deadline
    
    #alternate version: uniform util instead of uniform deadline
    maxUtil=myDAG.totalCost/myDAG.length
    baseUtil=uniform(1, maxUtil)
    deadline=myDAG.totalCost/baseUtil

    myDAG.deadline=deadline
    
    #schedule without SMT and record cores
    myDAG.makeBaselinePairList();
    baseCost=myDAG.totalCost
    #baseUtil=myDAG.totalCost/deadline
    baseCores=myDAG.howManyCores()
    

    pairs=ILP.makePairs(myDAG)
    #set max solutions, maxDistance
    pairs.setSolverParams(maxThreads, maxSol, maxDist)
    pairs.createSchedVars()

    baselineString=(scenarioString +
                ',' + str(i) +
                ',' + str(deadline) +
                 ',' + str(myDAG.length) +
                 ',' + str(baseCost) +
                 ',' + str(baseUtil) + 
                 ',' + str(baseCores))
    pairs.solver.optimize()
    #solver time
    solverTime=pairs.solver.runtime
    #optimal? gap?
    #optimal=pairs.solver.OPTIMAL
    #smt cost
    smtCost=pairs.varTotalCost.x
    #smt util
    smtUtil=smtCost/deadline
    #smt cores
    myDAG.makeSmtPairList(pairs.getPairList())
    smtCores=myDAG.howManyCores()
    
    smtString=(baselineString +
               ',' + str(solverTime) +
               #',' + str(gap) +
               ',' + str(smtCost) +
               ',' + str(smtUtil) +
               ',' + str(smtUtil/baseUtil) +
               ',' + str(smtCores) +
               ',' + str(smtCores/baseCores) +
               ',' + str(pairs.solver.SolCount) +
               ',' + str(pairs.solver.MIPGap) +
               ',' + str(numLayers)
               )
    
    with open(outputFile, "a") as f:
            print(smtString, file=f)


if __name__ == '__main__':
    #print headers
    with open(outputFile, "a") as f:
        print("utilDist", "smtDist", "Prob", "nodeCount",
          "maxDist", "maxSol",
          "dagFamilyID",
          "deadline", "length", "baseCost", "baseUtil", "baseCores",
          "solverTime", "smtCost", "smtUtil", "smtUtil/base",
          "smtCores", "smtCores/base",
          "solutionsFound", "optimalGap",
          "numLayers",
          sep=",", file=f)
        
    #with ThreadPool(processes=len(configurations)) as pool:
    with ThreadPool(processes=mp.cpu_count()) as pool:
        for res_tup in pool.imap_unordered(run_test, configurations):
            pass
    

