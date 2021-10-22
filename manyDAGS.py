# -*- coding: utf-8 -*-
"""
Created on Tue Oct 19 16:18:13 2021

@author: simsh
"""

'''
What questions are we trying to answer/ explore?
---what is the effect of the number of nodes? Are there any magic inflection points?
---Are there magic inflectino points for p? How many do I need to get good gains? When does performance
start to be an issue?
---As deadlines increase, base util falls.  Greater deadline is better for
decreasing util (more flexibility), but worse for decreasing core count.  Explore.

Graphs I want to show:
    --Effect of changing deadline on util and core reduction, all else constant.
    
Decisions
    --core count should be random or in small increments.
    --core count random: we don't know where the interesting things will happen.
    --3 pseudo-deadlines per real deadline: Length, Average, Cost.  Go back and
    try more options if this turns out to be interesting.  Or just do 25, 50, 75. Saves having to go back.
    --utilDist and smtDist should be deterministic.
    --deadline in range [Length, Cost*4]. Random or deterministic given Length, cost?
    
    --how many? Per unique(util, smt, P, count, util) should have about 50, i.e. 50 DAGs per specification.
    
'''

#!/usr/bin/python3

import os.path
from multiprocessing.pool import ThreadPool
import sys

import rtasConstants as constants
from dagTask import dagTask
import makePairs as ILP
from random import uniform


outputFile="sample5.csv"

'''
countList=[10, 20, 40, 80, 160, 320, 640, 1280]

utilList=[constants.NARROW, constants.MEDIUM, constants.WIDE]

smtList=[constants.OPTIMIST, constants.OK, constants.PESSIMIST]


erList=[0.1, 0.3, 0.5, 0.7, 0.9]


'''
INFINITY=float('inf')

#COUNT_LIST=[10]
COUNT_LIST=[int(sys.argv[1])]
UTIL_LIST=[constants.NARROW, constants.MEDIUM, constants.WIDE]
SMT_LIST=[constants.OPTIMIST, constants.OK, constants.PESSIMIST]
#PROB_LIST=[0.3]
PROB_LIST=[float(sys.argv[2])]

dagsPerScenario=50
#deadlinesPerDag=5
utilStep=0.25

configurations=[]
for count in COUNT_LIST:
    for util in UTIL_LIST:
        for smt in SMT_LIST:
            for prob in PROB_LIST:
                for i in range(dagsPerScenario):
                    config={}
                    config["c"]=count
                    config["u"]=util
                    config["s"]=smt
                    config["p"]=prob
                    config["i"]=len(configurations)+i
                    configurations.append(config)
                
SYNC = False

#the input to run_test, 'config', is one of the many dictionaries contained in the list 'configurations'
def run_test(config):
    #the '**' notation indicates that dictionary config is to be treated as a set of keyword arguments
    runDagFamily(**config)


#countList=[10]
#utilList=[constants.NARROW]
#smtList=[constants.OPTIMIST]
#erList=[0.1]
#dagsPerScenario=5
#deadlinesPerDag=10






def runDagFamily(u, s, p, c, i):           
    scenarioList=[str(u), str(s), str(p), str(c)]
    scenarioString=','.join(scenarioList)
    #last chance to add some parallelism
    myDAG=dagTask(fileName="random", targetNodeCount=c, targetCost=0, 
  nodeUtilDist=u, smtDist=s, erdoRenyiP=p)
    minDeadline=myDAG.length    # util>1, but hard to know by how much
    #maxDeadline=myDAG.totalCost*1.1    # util=.5
    '''
    if deadlinesPerDag==1:
        step=INFINITY     #just do the length
    else:
        step=(maxDeadline-minDeadline)/(deadlinesPerDag-1)    #kind of arbitrary
    '''
    deadline=minDeadline
    
    
    baseUtil=myDAG.totalCost/deadline
    #don't do parallel here; will probably slow down since it's
    #repeating the same DAG
    #while deadline<=maxDeadline:
    while baseUtil>0.75:
    #for deadline in range(minDeadline, maxDeadline+step, step):
        myDAG.deadline=deadline
        
        #schedule without SMT and record cores
        myDAG.makeBaselinePairList();
        baseCost=myDAG.totalCost
        #baseUtil=myDAG.totalCost/deadline
        baseCores=myDAG.howManyCores()
        
        #try SMT with different pseudo deadlines
        pairs=ILP.makePairs(myDAG)
        pairs.setSolverParams()
        pairs.createSchedVars()
        #default pseudoDeadline is length=minDeadline
        #record util
        #schedule and record core count
        
        #pseudoDeadline in range(length, trueDeadline)
        #nothing to do if true deadline=length
        baselineString=(scenarioString +
                    ',' + str(i) +
                    ',' + str(deadline) +
                     ',' + str(myDAG.length) +
                     ',' + str(baseCost) +
                     ',' + str(baseUtil) + 
                     ',' + str(baseCores))
        if deadline==myDAG.length:
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
                       ',' + str(deadline) +
                       ',' + str(solverTime) +
                       #',' + str(gap) +
                       ',' + str(smtCost) +
                       ',' + str(smtUtil) +
                       ',' + str(smtUtil/baseUtil) +
                       ',' + str(smtCores) +
                       ',' + str(smtCores/baseCores))
            
            with open(outputFile, "a") as f:
                    print(smtString, file=f)

        else:
            pseudoDeadlines=[myDAG.length, (deadline+myDAG.length)/2, deadline]
            smtString = baselineString
            for ps in pseudoDeadlines:
                pairs.changeDeadline(ps)
                pairs.solver.optimize()
                #record stuff
                #solver time
                solverTime=pairs.solver.runtime
                #optimal? gap?
                #gap=pairs.solver.MIPGap
                #smt cost
                smtCost=pairs.varTotalCost.x
                #smt util
                smtUtil=smtCost/deadline
                #smt cores
                myDAG.makeSmtPairList(pairs.getPairList())
                smtCores=myDAG.howManyCores()
                
                smtString=(smtString +
                       ',' + str(ps) +
                       ',' + str(solverTime) +
                       #',' + str(gap) +
                       ',' + str(smtCost) +
                       ',' + str(smtUtil) +
                       ',' + str(smtUtil/baseUtil) +
                       ',' + str(smtCores) +
                       ',' + str(smtCores/baseCores)
                       )
                #end of pseudoDeadline loop
            with open(outputFile, "a") as f:
                print(smtString, file=f)

        #util-based ste
        baseUtil=baseUtil-utilStep
        #util=cost/deadline
        deadline=myDAG.totalCost/baseUtil
        
        #deadline=deadline+step        
    #end of deadline loop


if __name__ == '__main__':
    #print headers
    with open(outputFile, "a") as f:
        print("utilDist", "smtDist", "Prob", "nodeCount",
          "dagFamilyID",
          "deadline", "length", "baseCost", "baseUtil", "baseCores",
          "pseudoDeadline", "solverTime", "smtCost", "smtUtil", "smtUtil/base",
          "smtCores", "smtCores/base",
          sep=",", file=f)
        
    with ThreadPool(processes=len(configurations)) as pool:
        for res_tup in pool.imap_unordered(run_test, configurations):
            pass
    

