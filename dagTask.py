
import rtasConstants as constants
import makePairs as ILP
import xml.etree.ElementTree as ET
import csv
import copy

from gurobipy import *
from random import random, gauss, uniform, choice, sample
#from numpy.random import lognormal
#import numpy as np
import pandas as pd
import math

'''
INFINITY=float('inf')
# possibilites for cost distribution
NARROW=0
MEDIUM=1
WIDE=2

# possibilites for smt behavior
OPTIMIST=0
OK=1
PESSIMIST=2
'''
    
        

'''
New input parameters: numNodes, nodeUtilDistrib, smtDistrib


New setUp: initialize DAG then build randomly or from files

'''
class dagTask:
    #create task system to approximate a specified total cost with randomly-determined
    #costs, SMT costs, and precedence constraints (from supplied parameters)
    #TO-DO: make the init function call either a random creator or a create from file
    '''
    def __init__(self, targetCost, minCost, maxCost, deadline, predProb,
                                       symParam1, symParam2, symParam3, symDistrib, 
                                       timeout, solutionLimit, threadsPerTest,
                                       excludePrinters):
    '''    
    def __init__(self, fileName="random", targetNodeCount=0, targetCost=0, nodeUtilDist=-1, smtDist=-1, erdoRenyiP=0, numLayers=0):

        #timeout, solutionLimit, and threadCount shouldn't be solverParams

        #generate nodes randomly OR get from xml file

        #xml creation
        #read file to get costs and precedence constraints
        #add in some SMT costs

        #random creation
        #addTaskRandomCost until either the number of nodes OR the total cost target has been reached
        #assignPairCosts

        if fileName=="random":
            self.nodeUtilDist=nodeUtilDist
            self.smtDist=smtDist
            self.allTasks=[]
            self.totalCost = 0
            self.nTotal=0
            if targetNodeCount==0:
                while self.totalCost < targetCost:
                    self.addTaskRandomCost()
            elif targetCost==0:
                while self.nTotal < targetNodeCount:
                    self.addTaskRandomCost()
            else:
                print("Error: for random file generation, only one of nodeCount or target cost may be specified.")

            #SMT costs
            self.assignPairCosts()

            #add precedence constraints
            if numLayers==0:
                self.ErdoRenyiCreateDag(erdoRenyiP)
            else:
                p=erdoRenyiP
                self.layeredDag(p, numLayers)
        # end of if fileName="random"

        else:
            print("Warning: reading from xmls not bug-checked!")
            print("The code's there but not put together.  Goodbye.")
            return

        #either way, calculate length
        #relies on tasks being topologically ordered
        #minFinish and minStart both default to 0
        self.length=0
        for t in self.allTasks:
            for pred in t.predList:
                t.minStart=max(t.minStart, self.allTasks[pred].minFinish)
            t.minFinish=t.minStart + t.cost
            self.length=max(t.minFinish, self.length)

        # we're going to want to try some different deadlines
        # pseudo deadline should be a solver param, not a dag param
        # 
        self.deadline=self.length

        
    def buildDagFromFiles(self, predConstraintsFile, baselineCostFile, smtCostFile, deadline):
        self.protoTaskDict={}
        
        #create protoTasks from xml file
        tree = ET.parse(predConstraintsFile)
        root = tree.getroot()
        for xmlTask in root.iter("task"):
            name=xmlTask.get("id")
            if self.excludePrinters:
                if "print" in name: continue
            #print("Subtask name from xml: ", name)
            predList = []
            for pred in xmlTask.iter("prev"):
                predID=pred.get("id")
                #print("     Pred: ", predID)
                predList.append(predID)
            #end for pred
            #do I really want to have name as both an attribute and the key?
            #print("Creating protoTask ", name)
            #print("with predList ", predList)
            self.protoTaskDict[name]=protoTask(name, predList)
        #end for subtask in root
        #topologically sort proto tasks into real tasks
        for n in self.protoTaskDict.keys():
            #create tasks and add to allTasks in topological order
            self.visitProtoTask(self.protoTaskDict[n])
            
        #Add in solo costs
        # read in baseline cost file (csv)
        with open(baselineCostFile) as f:
            myReader = csv.reader(f)
            # skip the header row and count the columns

            headers = next(myReader)
            columns = len(headers)
            #print("Headers from baseline: ", headers)
            if self.excludePrinters:
                for h in headers:
                    if "print" in h:
                        headers.remove(h)
                        columns -=1
                
            
            
            for i in range(0, columns):
                headers[i]=headers[i].strip(" ")
            
            dataByColumns=[[] for i in range (0, columns)]
            #print(dataByColumns)
            #print(headers)
            #print("# of columns=", columns)
            next(myReader)
            #print("Iterating through baseline file by row.")
            for row in myReader:
                #print(row)
                col = 0
                for entry in row:
                    if entry=="": continue
                    #print("col: ", col, ": entry=", entry)
                    dataByColumns[col].append(int(entry))
                    col+=1
                    #print()
                #end entry loop
            # end row loop
        #don't need the file open anymore
        
        #Get (estimated) SMT costs
        with open(smtCostFile) as f:
            myReader = csv.reader(f)
            # skip the header row and count the columns
            # headers will be the same between this file and the baseline
            next(myReader)
            #columns = len(headers)
            #print("headers: ", headers)
            
            smtDataByColumns=[[] for i in range (0, columns)]
            
            for row in myReader:
                #print(row)
                col = 0
                for entry in row:
                    if entry=="": continue
                    #print("col: ", col, ": entry=", entry)
                    smtDataByColumns[col].append(int(entry))
                    col+=1
        
        
        #find and combine duplicate column entries
        duplicates=[]
        for i in range(columns):
            for j in range(i+1, columns):
                if not(j in duplicates) and (headers[i] == headers [j]):
                    # add the contents of col j to col i
                    #print("i=", i)
                    #print("dataBycolumns[i]=", dataByColumns[i])
                    #print("j=", j)
                    #print("dataBycolumns[j]=", dataByColumns[j])
                    dataByColumns[i].extend(dataByColumns[j])
                    smtDataByColumns[i].extend(smtDataByColumns[j])
                    duplicates.append(j)
        
        #remove duplicate entries
        #or would it be better to just ignore them?


        # find the max for all values
        # assign to task with matching name in allTasks (ignore __ and following)
        # should be a way to reduce the amount of string matching needed here
        for t1 in self.allTasks:
            t1.allCosts=[None]*self.nTotal
        
        for t1 in self.allTasks:
            # get only the part of the name that come before the "__"
            i=t1.name.find('__')
            if i>=0:
                shortName1 = t1.name[:i]
            else:
                shortName1=t1.name
            #print("t1.name: ", t1.name)
            #print("shortName1: ", shortName1)
            #print()
            #find the header that matches shortName
            index1 = headers.index(shortName1)
            #print(t1.allCosts[t1.permID])
            #print(max(dataByColumns[index1]))
            
            #problem: all costs is not defined
            #t1.allCosts=[None]*self.nTotal
            t1.cost = t1.allCosts[t1.permID]=max(dataByColumns[index1])
            estimate1 = max(smtDataByColumns[index1])
            self.totalCost = self.totalCost + t1.cost
            for i in range(t1.permID + 1, self.nTotal):
                t2 = self.allTasks[i]
                j=t2.name.find('__')
                if j>=0:
                    shortName2 = t2.name[:j]
                else:
                    shortName2=t2.name
                
                #print("t2 permID: ", t2.permID)
                #print("t2.name: ", t2.name)
                #print("shortName2: ", shortName2)
                #print()
                
                #print(headers)
                # need a comparison that ignores excess spaces
                '''
                renamed fft_float_prfloater in xml file to fft_float_printer;
                xml name did not match procedure name.
                '''
                
                index2 = headers.index(shortName2)
                t2.cost = t2.allCosts[t2.permID]=max(dataByColumns[index2])
                #t2.cost will already have been defined since t2 has
                #a greater index than t1
                estimate2 = max(smtDataByColumns[index2])
                self.estimateSMT(t1, t2, estimate1, estimate2)
                
                #I think this covers everything on building the DAG.
                #Debug (including printing) before continuing
                    

    #could be buggy if called where task1=task2.
    def estimateSMT(self, task1, task2, estimate1, estimate2):

        #consider adding a fudge factor in here to have estimates consistently
        #greater than the truth
        '''
        slowdownFactor=% increase in exec time due to SMT.
        Expected range from 0 (no effect) to 1 (exec time doubles).
        Outliers>1 are possible, but should not have any negatives.
        Consider resetting negatives and near-zero values to 
        something more plausible (0.05? 0.1?).

        Also, set so SMT will never be less than the baseline

        Do I want to make additional adjustments?
        '''

        #print ("task1: ", task1.permID, task1.name, task1.cost)
        #print ("task2: ", task2.permID, task2.name, task2.cost)
        if task1.cost == task2.cost:
            task1.allCosts[task2.permID] = max(estimate1, task1.cost)
            #print("Cost ", task1.permID, "[", task2.permID, "]=", task1.allCosts[task2.permID])
            task2.allCosts[task1.permID] = max(estimate2, task2.cost)
            #print("Cost ", task2.permID, "[", task1.permID, "]=", task2.allCosts[task1.permID])
        elif task1.cost > task2.cost:
            task2.allCosts[task1.permID] = max(estimate2, task2.cost)
            #adjusting negative values to 0.01 matches ECRTS '20 paper, I think.
            #consider what to do here before final version.
            slowdownFactor = max((estimate1-task1.cost) / task1.cost, 0.01)
            task1.allCosts[task2.permID] = task1.cost + slowdownFactor * task2.cost
            #print("Cost ", task1.permID, "[", task2.permID, "]=", task1.allCosts[task2.permID])
            #print("Task1 slowdownFactor=", slowdownFactor)
            #print("Cost ", task2.permID, "[", task1.permID, "]=", task2.allCosts[task1.permID])
            
        else:
            task1.allCosts[task2.permID] = estimate1
            slowdownFactor = max((estimate2 - task2.cost) / task2.cost, 0.01)
            task2.allCosts[task1.permID] = task2.cost + slowdownFactor * task1.cost
            #print("Cost ", task1.permID, "[", task2.permID, "]=", task1.allCosts[task2.permID])
            #print("Cost ", task2.permID, "[", task1.permID, "]=", task2.allCosts[task1.permID])
            #print("Task2 slowdownFactor=", slowdownFactor)
        task1.allCosts[task1.permID] = task1.cost
        task2.allCosts[task2.permID] = task2.cost
        #print()
    

    
    def visitProtoTask(self, myProtoTask):
        if myProtoTask.mark == 2:
            return myProtoTask.permID
            # need to return a value
            #return self.permID
        elif myProtoTask.mark ==1:
            print("Warning: cycle found!")
            #To-Do: exit gracefully in this case.
            return

        myProtoTask.mark = 1
        for pred in myProtoTask.predNameList:
            #print("Inside visit method.")
            #print("current task: ", myProtoTask.name)
            #print("predNameList: ", myProtoTask.predNameList)
            #print("numericPreds: ", myProtoTask.numericPreds)
            #print("Next task: ", pred)
            #print()
            # pred is a string.  Need to visit the corresponding task.
            
            
            #Problem arises if task's predecessor has already been added?
            myProtoTask.numericPreds.append(self.visitProtoTask(self.protoTaskDict[pred]))
        #all of cur's predecessors (immediate or otherwise) have been
        #visited and added to the permanent list.
        myProtoTask.mark = 2
        # create a real task from cur and return the new task's ID
        # cost initially set to 0; will be updated later.
        #return self.addTaskSetCost(0, myProtoTask.name)
        myProtoTask.permID=self.addTaskFromProto(myProtoTask)
        #print(myProtoTask.name, " gets permID ", self.permID, ". Has preds ", 
        #      myProtoTask.numericPreds)
        #print()
        return myProtoTask.permID
        #return self.addTaskFromProto(myProtoTask)


            
    #should be able to consolidate these two
    #how does overloading work in Python?
    def addTaskFromProto(self, proto):
        #tasks are zero-indexed
        self.nTotal = permID = len(self.allTasks)
        task = subTask(0, permID)
        task.name = proto.name
        task.predList=proto.numericPreds
        self.allTasks.append(task)
        #self.totalCost = self.totalCost + cost
        #print("current total util=", self.totalUtil)
        self.nTotal += 1
        return permID

    def addTaskRandomCost(self):
        #tasks are zero-indexed
        self.nTotal = permID = len(self.allTasks)
        dist=self.nodeUtilDist
        if dist==constants.NARROW:
            cost = uniform(1, 2)
        elif dist==constants.MEDIUM:
            cost = uniform(1, 10)
        elif dist==constants.WIDE:
            cost = uniform(1, 20)
        task = subTask(cost, permID)
        self.allTasks.append(task)
        self.totalCost = self.totalCost + cost
        self.nTotal += 1
        return permID
    


    def printDag(self):
        print("total Cost: ", self.totalCost)
        print("length: ", self.length)
        for i in range(self.nTotal):
            task=self.allTasks[i]
            print(i, " name: ", task.name, "cost:", task.cost, "otherCosts: ", task.allCosts)
            print("predList: ", task.predList)
            print()
            
    def schedulePairs(self, totalCores, waitingList, r):
        #waitingList = self.pairList
        readyList = []
        runningList = []
        eventTimes = []
        completed = []
        coresInUse = []
        schedByCore=[[]for c in range(0, totalCores)]
        
        time=0
        coresUsed=0
        deadline=self.deadline
        
        '''
        print("Initial waiting list: ")
        for w in waitingList:
            print(w.IDs)
        '''
        #print()
        #print("time=0")
        
        while time<=deadline:
            # see what's done running
            for p in runningList:
                if p.finish[0]==time:
                    eventTimes.remove(time)
                    #print(p.IDs[0], " complete.")
                    #print("eventTimes: ", eventTimes)
                    # for debugging; doesn't do anything
                    completed.append(self.allTasks[p.IDs[0]])
                    for w in waitingList:
                        # can't remove items that aren't there.
                        if p.IDs[0] in w.remainingPredList:
                            w.remainingPredList.remove(p.IDs[0])
                            
                        
                    
                if p.finish[1]==time:
                    eventTimes.remove(time)
                    #print(p.IDs[1], " complete.")
                    #print("eventTimes: ", eventTimes)
                    if not (self.allTasks[p.IDs[0]]) in completed:
                        # for debugging; doesn't do anything
                        completed.append(self.allTasks[p.IDs[0]])
                    for w in waitingList:
                        if p.IDs[1] in w.remainingPredList:
                            w.remainingPredList.remove(p.IDs[1])
                        
                    
                if p.finish[0]<=time and p.finish[1]<=time:
                    coresInUse.remove(p.core)
                    coresUsed-=1
                    runningList.remove(p)
                    #print("Core freed: ", p.core)
            
            if len(runningList)==0 and len(waitingList)==0 and len(readyList)==0:
                return (True, schedByCore)
            
            # add tasks to readyList
            newlyReady=[]
            for w in waitingList:
                if len(w.remainingPredList)==0:
                    readyList.append(w)
                    #print("Ready: ", w.IDs)
                    #waitingList.remove(w)
                    newlyReady.append(w)
                #else: print("Not ready: ", w.IDs, " , waiting on ", w.remainingPredList)
            # calling remove causes items to be skipped and thus not start executing when they should
            for n in newlyReady: waitingList.remove(n)

            #debug code
            '''
            if len(readyList)==0:
                print("Warning: ready list is empty.")
                for w in waitingList:
                    print("Tasks ", w.IDs, " waiting on ", w.remainingPredList)
            '''
            #start new tasks runninning
            while len(readyList)>0 and coresUsed < totalCores:
                
                # sort readylist
                readyList.sort(key=lambda x: x.pairCost, reverse=r)
                
                cur=readyList.pop()
                for findFreeCore in range(totalCores):
                    if findFreeCore not in coresInUse:
                        cur.core=findFreeCore
                        schedByCore[findFreeCore].append(cur)
                        coresUsed+=1
                        coresInUse.append(findFreeCore)
                        #print("Now starting: ", cur.IDs)
                        break
                        
                cur.start=time
                cur.finish[0]=time+cur.costs[0]
                cur.finish[1]=time+cur.costs[1]
                runningList.append(cur)
                
                
                if cur.finish[0]>deadline or cur.finish[1]>deadline:
                    # reset pairs
                    for p in self.pairList:
                        p.remainingPredList=copy.copy(p.predList)
                        p.finish=[constants.INFINITY, constants.INFINITY]
                        p.start=[constants.INFINITY, constants.INFINITY]
                        p.core=-1
                    
                    return (False, schedByCore)
                eventTimes.append(cur.finish[0])
                eventTimes.append(cur.finish[1])
                
            #end of loop to start new tasks
            #print("eventTimes=", eventTimes)
            time=min(eventTimes)
            #print()
            #print("time=", time)
        # end of time loop


    def layeredDag(self, p, numLayers):
        # assign tasks to layers while maintaining topological sort
        '''
        Each layer is equal?
        Pick k-1 randoms from range to be the breakpoint?
        '''
        maxLayerIndices=sample(range(self.nTotal), numLayers-1)
        maxLayerIndices.sort()
        maxLayerIndices.append(self.nTotal) #last layer always ends with the last task
        
        #divide tasks into layers
        curLayer=0
        for i in range(self.nTotal):
            if i> maxLayerIndices[curLayer]:
                curLayer+=1
            self.allTasks[i].layer=curLayer
            
        #add precedence constraints
        for i in range(self.nTotal):
            for j in range(i):
                if self.allTasks[j].layer < self.allTasks[i].layer:
                    if random()<p:
                        self.allTasks[i].predList.append(j)
        
                


    def ErdoRenyiCreateDag(self, p):
        for i in range(self.nTotal):
            for j in range(i):
                if random()<p:
                    self.allTasks[i].predList.append(j)


    def assignPairCosts(self):
        for i in range(self.nTotal):
            self.allTasks[i].allCosts=[0]*self.nTotal

        #populate the lists
        for i in range(self.nTotal):
            for j in range(self.nTotal):
                if i==j:
                    self.allTasks[i].allCosts[j]=self.allTasks[i].cost
                else:
                    maxCost=max(self.allTasks[i].cost, self.allTasks[j].cost)
                    minCost=min(self.allTasks[i].cost, self.allTasks[j].cost)
                    if maxCost>minCost*10:
                        #don't use threading
                        #timing analysis is not predictable in this case
                        #plus it wouldn't be any good anyway.
                        highPairCost=maxCost*10
                        lowPairCost=maxCost*10
                    else:
                        # returns a tuple (minMult, maxMult)
                        multiplier=self.smtMultiplier()
                        highPairCost=maxCost+multiplier[1]*minCost
                        #lowPairCost=min(highPairCost, minCost*multiplier[0])
                        lowPairCost=min(highPairCost, minCost + multiplier[0]*minCost)
                    
                    #allows each task to have a seperate cost
                    #will be important once we bring in precedence constraints
                    if self.allTasks[i].cost>self.allTasks[j].cost:
                        self.allTasks[i].allCosts[j]=highPairCost
                        self.allTasks[j].allCosts[i]=lowPairCost
                    else:
                        self.allTasks[j].allCosts[i]=highPairCost
                        self.allTasks[i].allCosts[j]=lowPairCost

    
    # keep it simple for plausibility testing                
    def smtMultiplier(self):

        dist=self.smtDist

        if dist==constants.OPTIMIST:
            #minMult=uniform(1, 1.8)
            minMult=gauss(0.34, 0.2)
            #based on DIS results in SMT + MC^2
            maxMult=gauss(0.34, 0.2)

        elif dist==constants.OK:
            #based on San Diego Vision in SMT + MC^2
            if uniform(0, 1)<0.05:
                minMult=maxMult=10
            else:
                #minMult=uniform(1.1, 1.8)
                minMult=gauss(0.52, 0.17)
                maxMult=gauss(.52, .17)

        elif dist==constants.PESSIMIST:
            #based on RTCSA and ECRTS pessimistic (worse than anything observed in SMT + MC^2)
            if uniform(0, 1)<0.2:
                minMult=maxMult=10
            else: 
                #minMult=uniform(1, 2)
                minMult=gauss(0.6, 0.07)
                maxMult=gauss(.6, .07)
        #negative results are illogical
        #follows from previous work
        maxMult=max(maxMult, 0.01)
        minMult=max(minMult, 0.01)
        return(minMult, maxMult)
        
    #no pairs, i.e. each task paired with itself
    def makeBaselinePairList(self):
        self.pairList=[]
        for t in self.allTasks:
            self.pairList.append(taskPair(t, t))
            
    def makeSmtPairList(self, pairIDList):
        self.pairList=[]
        #pairIDList=pairs.getPairList()

        for p in pairIDList:
            task1=self.allTasks[p[0]]
            task2=self.allTasks[p[1]]
            self.pairList.append(taskPair(task1, task2))
            
    def howManyCores(self):
        cores=math.ceil(self.totalCost/self.deadline)
        
        for r in [True, False]: #should ready list be ordered ascending or descending?
            scheduled=False
            while not scheduled and cores <=self.nTotal:
                # debug code: just check the last loop
                #cores=myDAG.nTotal
                result=self.schedulePairs(cores, copy.copy(self.pairList), r)
                scheduled=result[0]
                #print("Deadline: ", myDAG.deadline)
                if scheduled:
                    continue
                    '''
                    print("Cores needed: ", cores)
                    schedByCore=result[1]
                    for c in range(cores):
                        print("Pairs on core ", c)
                        for p in schedByCore[c]:
                            print(p.IDs[0], p.IDs[1], "start=", p.start, "finish=", 
                                  max(p.finish[0], p.finish[1]))
                        print()
                    '''
                else: cores+=1
            # end while
            if r: cores1=cores
            else: cores2=cores
        #end r loop
        return min(cores1, cores2)
        
        

class protoTask:
    def __init__(self, name, predNameList):
        self.name=name
        self.predNameList=predNameList
        self.numericPreds=[]
        self.permID = -1
        # for use if depth-first search
        # 0 = no mark
        # 1 = temp
        # 2 = permanent
        self.mark=0

class taskPair:
    def __init__(self, task1, task2):
        self.IDs=[task1.permID, task2.permID]
        self.start=constants.INFINITY
        self.finish=[constants.INFINITY, constants.INFINITY]
        self.costs=[task1.allCosts[task2.permID], 
                    task2.allCosts[task1.permID]]
        self.pairCost=max(self.costs[0], self.costs[1])
        self.predList=list(set(task1.predList + task2.predList))
        self.remainingPredList=copy.copy(self.predList)
        self.core=-1   

class subTask:
    def __init__(self, cost, permID):
        #self.util = float(util)
        #self.period = period
        self.cost = cost
        self.permID = permID
        self.allCosts=[]
        self.predList=[]
        self.name=""
        # for use if depth-first search
        # 0 = no mark
        # 1 = temp
        # 2 = permanent
        self.mark=0
        self.minStart=0
        self.minFinish=0
        self.layer=0 #used when building DAGs using the layer method



def printToCSV():
    '''
    Input parameters:
    dagID numNodes nodeUtilDis smtFriendliness ErdosRenyiP
    
    DAG characteristics
    Length Deadlines(plural; deadline is a function of length)
    
    For each deadline
    smtUtil percentReduced gurobiTime
    
    Seperate file for tracking cores used?
    dagID totalUtil deadline coresUsed
    
    for each combo of pseudoDeadline, schedMethod:
        smtCoresUsed percentReduced
    
    '''

def main():

    myDAG=dagTask(fileName="random", targetNodeCount=10, targetCost=0, nodeUtilDist=MEDIUM, smtDist=OK, erdoRenyiP=0.2)
    #myDAG.printDag()
    # Make pairs using the ILP
    pairs=ILP.makePairs(myDAG)

    #can I try different deadlines without recreating the whole DAG?

    pairs.setSolverParams(timeLimit=60, solutionLimit=1000, threadsPerTest=0)
    pairs.createSchedVars()
    
    
    deadlineMultiples=[1, 1.5, 2]
    
    for d in deadlineMultiples:
        pseudoDeadline=myDAG.deadline*d
        print("CHANGING PSEUDO-DEADLINE:")
        print("pseudo-deadline= ", pseudoDeadline)
        pairs.changeDeadline(pseudoDeadline)
    
        pairs.solver.optimize()
        pairs.printSolution('short')
        pairIDList=pairs.getPairList()
        myDAG.pairList=[]
        for p in pairIDList:
            task1=myDAG.allTasks[p[0]]
            task2=myDAG.allTasks[p[1]]
            myDAG.pairList.append(taskPair(task1, task2))
        scheduled=False
        #print("pairList: ", myDAG.pairList)
        #minimum number of cores
        cores=int(myDAG.totalCost/myDAG.deadline)
        # could streamline this by getting/ calculating the width
        
        # Now that we have the pairs, compute a schedule using Graham's list.
        # this should be its own method
        while not scheduled and cores <=myDAG.nTotal:
            # debug code: just check the last loop
            #cores=myDAG.nTotal
            result=myDAG.schedulePairs(cores, copy.copy(myDAG.pairList), True)
            scheduled=result[0]
            print("Deadline: ", myDAG.deadline)
            if scheduled: 
                print("Cores needed: ", cores)
                schedByCore=result[1]
                for c in range(cores):
                    print("Pairs on core ", c)
                    for p in schedByCore[c]:
                        print(p.IDs[0], p.IDs[1], "start=", p.start, "finish=", 
                              max(p.finish[0], p.finish[1]))
                    print()
                    
            cores+=1
            # end while
        if not scheduled: 
            print("DAG infeasible.")
            schedByCore=result[1]
            for c in range(cores):
                print("Pairs on core ", c)
                for p in schedByCore[c]:
                    print(p.IDs[0], p.IDs[1], "start=", p.start, "finish=", 
                    max(p.finish[0], p.finish[1]))
            print("DAG infeasible.")


if __name__== "__main__":
     main() 
     

