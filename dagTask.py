'''
Communicate to outside:
    total util.
    util of just-added task.
    result of test:  success/ fail/ timeout.
Need to add tasks individually to system.
Have seperate methods for CERT-MT, multi-frame no SMT, baseline.
'''

#import CERTMT_sched as cert
#import npCERTMT_sched as np
#import baseline_sched as base
#import RTCSA_ILP as ILP
import schedDAG3 as ILP
#import MultiFrameNoSMT_sched as multi
#import OneFrameSizeSMT_sched as oneFrame
#import fullPreemption2_sched as fullPreempt

from gurobipy import *
from random import random, gauss, uniform, choice
from numpy.random import lognormal
import pandas as pd


UNIFORM=1
SPLIT_UNIFORM=2
NORMAL=3
SPLIT_NORMAL=4

BASELINE=1
#Preemptive CE scheduler
CERT_MT=2
#multiple frames, non-SMT tasks are preemptable
FAIL=3


    
        

#create task system
class dagTask:
          #test=TaskSet(targetUtil, utilMin, utilMax, periodMin, periodCount, symMean, symDev, symDistrib, m, timeout, solutionLimit, lowerBound, upperBound)
    def __init__(self, targetCost, minCost, maxCost, deadline, 
                                       symParam1, symParam2, symParam3, symDistrib, 
                                       timeout, solutionLimit, threadsPerTest):
        

        #will be used by solvers
        self.timeout=timeout
        self.solutionLimit=solutionLimit
        #self.lowerBound=lowerBound
        #self.upperBound=upperBound
        
        #self.targetUtil = targetUtil
        #self.utilMin=utilMin
        #self.utilMax=utilMax
        #self.periodMin = periodMin
        #self.periodCount = periodCount
        self.symParam1=symParam1
        self.symParam2=symParam2
        self.symParam3=symParam3
        self.symDistrib=symDistrib
        #self.m=m
        
        self.targetCost=targetCost
        self.minCost=minCost
        self.maxCost=maxCost
        self.deadline=deadline

        #how many threads should the solver use per test?
        #if not set, will take all available threads.
        #This will make individual tests run faster, but probably harmful overall,
        #since we're also trying to parallelize the graphs.
        self.threadsPerTest=threadsPerTest
        
        
        #self.hyperperiod=periodMin*2**(periodCount-1)
        #self.periods=[]

        
        '''      
        #print("Creating periods")
        for i in range(periodCount):
            self.periods.append(periodMin*(2**i))
            #print(self.periods[i])
        self.allTasks = []
        self.totalUtil = 0
        '''
        self.allTasks=[]
        self.totalCost = 0
        while self.totalCost < targetCost:
            self.addTask()   
        
        self.assignPairCosts()
        
        

    def addTask(self):
        #tasks are zero-indexed
        self.nTotal = permID = len(self.allTasks)
        cost = int(uniform(self.minCost, self.maxCost))
        #period = choice(self.periods)
        #print("New task period", period)
        task = subTask(cost, permID)
        self.allTasks.append(task)
        self.totalCost = self.totalCost + cost
        #print("current total util=", self.totalUtil)
        self.nTotal += 1
    
    #need to update the way I'm handling costs
    
    #only used when adding a new task to an already created system
    #don't need for plausibility testing
    #def addTaskAndUpdateCosts(self):
  
    
   # used by the next method up
   # deleted so I wouldn't have to look at it
   # can be found in CERTMT_sched.py
   # def testSystem(self, runBaseline, runCertMT):



    def assignPairCosts(self):
        '''
        for i in range(self.nTotal):
            self.allTasks[i].allCosts=[]
            for j in range(self.nTotal):
                #debugging: prevent SMT
                if i==j:
                    self.allTasks[i].allCosts.append(int(self.allTasks[i].cost))
                else:
                    self.allTasks[i].allCosts.append(self.deadline*2)
                #self.allTasks[i].allCosts.append(0)
        '''
        #set up all costs array first
        for i in range(self.nTotal):
            self.allTasks[i].allCosts=[0]*self.nTotal

        #populate the lists
        for i in range(self.nTotal):
            for j in range(self.nTotal):
                if i==j:
                    self.allTasks[i].allCosts[j]=int(self.allTasks[i].cost)
                else:
                    maxCost=max(self.allTasks[i].cost, self.allTasks[j].cost)
                    minCost=min(self.allTasks[i].cost, self.allTasks[j].cost)
                    if maxCost>minCost*10:
                        #don't use threading
                        #timing analysis is not predictable in this case
                        #plus it wouldn't be any good anyway.
                        costToHide=10
                    else:
                        costToHide=self.setCostToHide()
                    pairCost=int(maxCost+costToHide*minCost)
                    
                    #allows each task to have a seperate cost
                    #will be important once we bring in precedence constraints
                    if self.allTasks[i].cost>self.allTasks[j].cost:
                        self.allTasks[i].allCosts[j]=pairCost
                        #need a more rigourus way to come up with the shorter cost
                        self.allTasks[j].allCosts[i]=int((1+costToHide)*minCost)
                    else:
                        self.allTasks[j].allCosts[i]=pairCost
                        #need a more rigourus way to come up with the shorter cost
                        self.allTasks[i].allCosts[j]=int((1+costToHide)*minCost)

    
    # keep it simple for plausibility testing                
    def setCostToHide(self):
        #if self.symDistrib==UNIFORM:
            costToHide=uniform(self.symParam1, self.symParam2)
            #costToHide = 10
            return costToHide
            #return uniform(self.symParam1, self.symParam2)
        #elif self.symDistrib==SPLIT_UNIFORM:
         #   whichRange=random()
          #  if whichRange<self.symParam3:
                #no threading here
           #     costToHide=10
            #else:
             #   costToHide=uniform(self.symParam1, self.symParam2)
        #elif self.symDistrib==NORMAL:
            #don't want values <=0
         #   costToHide=min(0.01, gauss(self.symParam1, self.symParam2))
        #elif self.symDistrib==SPLIT_NORMAL:
        #    whichRange=random()
         #   if whichRange<self.symParam3:
                #no threading here
          #      costToHide=10
           # else:
            #    costToHide=min(0.01, gauss(self.symParam1, self.symParam2))
        #return costToHide
    
    
    
    
    def printTaskSystem(self):
        print("totalUtil: ", self.totalUtil)
        for i in range(self.nTotal):
            task=self.allTasks[i]
            print(i, "period:", task.period, "cost:", task.cost, "otherCosts:", task.allCosts)


    
class subTask:

    def __init__(self, cost, permID):
        #self.util = float(util)
        #self.period = period
        self.cost = cost
        self.permID = permID
        self.allCosts=[]
        self.predList=[-1]


'''
    def __str__(self):
        return "τ{0}: ({1:0.2f}U, {2:0.0f}T, {3})".format(self.permID, self.util, self.period, str(self.symAdj))

    def __repr__(self):
        return self.__str__()
'''


'''
targetUtil=4
utilMin=.1
utilMax=1
periodMin=1
periodCount=4
symMean=.5
symDev=.1
symDistrib=NORMAL
m=4
timeout=60
solutionLimit=100
lowerBound=1
upperBound=1
test=CERTMT_TaskSystem(targetUtil, utilMin, utilMax, periodMin, periodCount, symMean, symDev, symDistrib, m, timeout, solutionLimit, lowerBound, upperBound)
test.testSystem()
'''

def main():
    #parameterrs for testing
    #targetUtil=16
    #utilMin=0
    #utilMax=1
    #periodMin=10
    #periodCount=1
    symDistrib=SPLIT_UNIFORM
    symParam1=.1
    symParam2=.8
    symParam3=.1
    #m=4
    timeout=60
    solutionLimit=10000
    #lowerBound=0
    #upperBound=100
    threadsPerTest=0
    
    targetCost=10000
    minCost=5
    maxCost=15
    deadline=200

    
    
    myDAG = dagTask(targetCost, minCost, maxCost, deadline, 
                                       symParam1, symParam2, symParam3, symDistrib, 
                                       timeout, solutionLimit, threadsPerTest)
    
    sched=ILP.schedDAG3(myDAG)
    #sched.setSolverParams()
    #sched.createSchedVars()
    #sched.solver.optimize()
    #sched.printSolution()
    sched.schedule()
    #sched.printSolution()
    sched.solver.getAttr(GRB.Attr.Status)


if __name__== "__main__":
     main() 
