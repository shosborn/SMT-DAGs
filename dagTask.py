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
import makePairs as ILP
import xml.etree.ElementTree as ET
import csv
import copy
#import MultiFrameNoSMT_sched as multi
#import OneFrameSizeSMT_sched as oneFrame
#import fullPreemption2_sched as fullPreempt
from gurobipy import *
from random import random, gauss, uniform, choice
from numpy.random import lognormal
import pandas as pd

import math

#used to copy template C file to a new destination file
import shutil
import os


UNIFORM=1
SPLIT_UNIFORM=2
NORMAL=3
SPLIT_NORMAL=4

BASELINE=1
#Preemptive CE scheduler
CERT_MT=2
#multiple frames, non-SMT tasks are preemptable
FAIL=3

INFINITY=float('inf')
    
        

'''
New input parameters: numNodes, nodeUtilDistrib, smtDistrib


New setUp: initialize DAG then build randomly or from files

'''
class dagTask:
    #create task system to approximate a specified total cost with randomly-determined
    #costs, SMT costs, and precedence constraints (from supplied parameters)
    #TO-DO: make the init function call either a random creator or a create from file
    def __init__(self, targetCost, minCost, maxCost, deadline, predProb,
                                       symParam1, symParam2, symParam3, symDistrib, 
                                       timeout, solutionLimit, threadsPerTest,
                                       excludePrinters):
        

        #will be used by solvers
        self.timeout=timeout
        self.solutionLimit=solutionLimit
        self.symParam1=symParam1
        self.symParam2=symParam2
        self.symParam3=symParam3
        self.symDistrib=symDistrib
        
        self.targetCost=targetCost
        self.minCost=minCost
        self.maxCost=maxCost
        self.deadline=deadline
        
        self.excludePrinters=excludePrinters

        #how many threads should the solver use per test?
        #if not set, will take all available threads.
        #This will make individual tests run faster, but probably harmful overall,
        #since we're also trying to parallelize the graphs.
        self.threadsPerTest=threadsPerTest


        self.allTasks=[]
        self.totalCost = 0
        '''
        while self.totalCost < targetCost:
            self.addTask() 
        print("Total tasks: ", self.nTotal)
        if predProb>0:
            self.ErdoRenyiCreateDag(predProb)
        self.assignPairCosts()
        '''       

    
    def buildDagFromFilesSB_VBS(self, predConstraintsFile, baselineCostFile, smtCostFile):
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
            self.visit(self.protoTaskDict[n])

        #Add in paired
        # read in cost file (csv)
        with open(smtCostFile) as f:
            myReader = csv.reader(f)
            # skip the header row and count the columns

            headers = next(myReader)
            columns = len(headers)
            assert(columns>0)
            #print("Headers from baseline: ", headers)
            if self.excludePrinters:
                for h in headers:
                    if "print" in h:
                        headers.remove(h)
                        columns -=1
                
            
            
            for i in range(0, columns):
                headers[i]=headers[i].strip(" ")
            
            dataByRows=[]
            #print(dataByColumns)
            #print(headers)
            #print("# of columns=", columns)
            # next(myReader) # i think this was bc of double header in baseline file?
            #print("Iterating through baseline file by row.")
            for row in myReader:
                newrow = []
                for entry in row:
                    newrow.append(int(entry))
                if len(newrow)==0: continue
                dataByRows.append(newrow)
            print(dataByRows)
        #don't need the file open anymore

        #Get solo costs
        with open(baselineCostFile) as f:
            myReader = csv.reader(f)
            # skip the header row and count the columns
            # headers will be the same between this file and the smt cost
            # next(myReader) no headers
            #columns = len(headers)
            #print("headers: ", headers)
            
            baselines=[]
            
            for row in myReader:
                #print(row)
                baselines.append(int(row[0]))

        # next Sims finds duplicate columns, don't think this should be a probelm

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

            infl = 1
            
            t1.cost = t1.allCosts[t1.permID] = math.ceil(baselines[index1]*infl)
            self.totalCost = self.totalCost + t1.cost

            for i in range(t1.permID + 1, self.nTotal):
                t2 = self.allTasks[i]
                j=t2.name.find('__')
                if j>=0:
                    shortName2 = t2.name[:j]
                else:
                    shortName2=t2.name
        
                index2 = headers.index(shortName2)

                #t2.cost = t2.allCosts[t2.permID] = 

                t1.allCosts[t2.permID]=math.ceil(dataByRows[index1][index2]*infl)
                t2.allCosts[t1.permID]=math.ceil(dataByRows[index2][index1]*infl)
            

            print("[",t1.permID,"]",shortName1,t1.allCosts)

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

        print("length:",self.length)
        print("total cost:",self.totalCost)




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
            self.visit(self.protoTaskDict[n])
            
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
    
    #could be buggy if called where task1=task2.
    def estimateSMT(self, task1, task2, estimate1, estimate2):
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
    
    #ready to make some pairs
    
    #recursive.  Inserts a subtask into allTasks once all its predecessors
    #have been inserted and returns the subtasks permID.
    
    # 0 = no mark
    # 1 = temp
    # 2 = permanent
    
    
    # this is wrong!
    def visit(self, myProtoTask):
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
            myProtoTask.numericPreds.append(self.visit(self.protoTaskDict[pred]))
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
        cost = int(uniform(self.minCost, self.maxCost))
        task = subTask(cost, permID)
        self.allTasks.append(task)
        self.totalCost = self.totalCost + cost
        self.nTotal += 1
        return permID
    
    def printDag(self):
        print("total Cost: ", self.totalCost)
        for i in range(self.nTotal):
            task=self.allTasks[i]
            print(i, " name: ", task.name, "cost:", task.cost, "otherCosts: ", task.allCosts)
            print("predList: ", task.predList)
            print()
            
    def schedulePairs(self, totalCores, waitingList):
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
        
        while time<=deadline:
            # see what's done running
            for p in runningList:
                if p.finish[0]==time:
                    eventTimes.remove(time)
                    # for debugging; doesn't do anything
                    completed.append(self.allTasks[p.IDs[0]])
                    for w in waitingList:
                        # can't remove items that aren't there.
                        if p.IDs[0] in w.remainingPredList:
                            w.remainingPredList.remove(p.IDs[0])
                        
                    
                if p.finish[1]==time:
                    eventTimes.remove(time)
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
            
            if len(runningList)==0 and len(waitingList)==0 and len(readyList)==0:
                return (True, schedByCore)
            
            # add tasks to readyList
            for w in waitingList:
                if len(w.remainingPredList)==0:
                    readyList.append(w)
                    waitingList.remove(w)


            #debug code
            if len(readyList)==0:
                print("Warning: ready list is empty.")
                for w in waitingList:
                    print("Tasks ", w.IDs, " waiting on ", w.remainingPredList)
            #start new tasks runninning
            while len(readyList)>0 and coresUsed < totalCores:
                cur=readyList.pop()
                for findFreeCore in range(totalCores):
                    if findFreeCore not in coresInUse:
                        cur.core=findFreeCore
                        schedByCore[findFreeCore].append(cur)
                        coresUsed+=1
                        coresInUse.append(findFreeCore)
                        break
                        
                cur.start=time
                cur.finish[0]=time+cur.costs[0]
                cur.finish[1]=time+cur.costs[1]
                runningList.append(cur)
                
                
                if cur.finish[0]>deadline or cur.finish[1]>deadline:
                    # reset pairs
                    for p in self.pairList:
                        p.remainingPredList=copy.copy(p.predList)
                        p.finish=[INFINITY, INFINITY]
                        p.start=[INFINITY, INFINITY]
                        p.core=-1
                    return (False, schedByCore)
                eventTimes.append(cur.finish[0])
                eventTimes.append(cur.finish[1])
                
            #end of loop to start new tasks
            time=min(eventTimes)  
        # end of time loop


class taskPair:
    def __init__(self, task1, task2):
        self.IDs=[task1.permID, task2.permID]
        self.start=INFINITY
        self.finish=[INFINITY, INFINITY]
        self.costs=[task1.allCosts[task2.permID], 
                    task2.allCosts[task1.permID]]
        self.predList=list(set(task1.predList + task2.predList))
        self.remainingPredList=copy.copy(self.predList)
        self.core=-1   

'''
    def ErdoRenyiCreateDag(self, p):
        for i in range(self.nTotal):
            for j in range(i):
                if random()<p:
                    self.allTasks[i].predList.append(j)
                    #print(j, " Preceeds ", i)
                    #self.addToPredList(i, j)
'''   
    #making each task's pred list include all its ancestors
    #means fewer Gurobi variables=faster execution
'''
    def addToPredList(self, i, pred):
        self.allTasks[i].predList.append(pred)
        for ancestor in self.allTasks[pred].predList:
            self.addToPredList(i, ancestor)
'''


    #def assignPairCosts(self):
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
'''
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
    
    
    
'''    



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
    
class subTask:
    def __init__(self, cost, permID):
        #self.util = float(util)
        #self.period = period
        self.cost = cost
        self.permID = permID
        self.allCosts=[]
        self.predList=[]
        self.name=""

        self.minStart=0
        self.minFinish=0


'''
    def __str__(self):
        return "tau{0}: ({1:0.2f}U, {2:0.0f}T, {3})".format(self.permID, self.util, self.period, str(self.symAdj))

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


'''
Key steps handled here:
---Set or get parameters: DAG total util, SMT friendliness, DAG num tasks, likelihood of connections.
---Create DAG from file or randomized.
---Run through ILP to reduce utilization.  Optional: try with different deadlines or other tunable parameters.
---Find core count.

Q1: How much can we reduce a DAG's utilization?
    
Q2: How much can we reduce a DAG's core requirement/ increase its schedulability?
Q3: How much can we reduce a system's utilization (is this really any different from Q1?)
Q4: How much can we reduce a system's core requirement/ increase its schedulability?

---All output should be to a CSV with each row representing one Graph (or one line on graph.)
--- 
'''

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

def ns2ms(ns):
    return int(math.ceil(ns/1000/1000))

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
    solutionLimit=1000
    #lowerBound=0
    #upperBound=100
    threadsPerTest=0
    
    targetCost=5000
    minCost=5
    maxCost=15
    deadline=4891667013
              
    
    #Idea: use binary search deadline to find pseudoDeadline in range(
    #crit path, trueDeadline)
    #that minimizes cores needed
    
    #0.2 was value used by Dinh et al 2020
    predProb=.2
    
    #this works only if anything involving print is the last task
    excludePrinters=False

    myDAG = dagTask(targetCost, minCost, maxCost, deadline, predProb,
                                       symParam1, symParam2, symParam3, symDistrib, 
                                       timeout, solutionLimit, threadsPerTest, excludePrinters)

    
    '''
    All this is doing right now is reading the xml file and then
    printing out names and predecessors.
    '''
    #myDAG.buildDagFromFiles("FFT2-NoPrint.xml", "NoSMT-50-NoPrint.csv", "SMT-50-NoPrint.csv", 0)
    myDAG.buildDagFromFilesSB_VBS("smalltest-SD-VBS.xml","sd-vbs-solo-costs.csv","sd-vbs-paired-costs.csv")
    myDAG.printDag()
    
    '''
    Note: total cost without SMT of FFT2=955996.  Most of this is the print method.
    
    If we exclude the print method, total cost = 128180.  Applying SMT gets it down to 77786.
    '''
    
    # Make pairs using the ILP
    pairs=ILP.makePairs(myDAG)
    pairs.setSolverParams()
    pairs.createSchedVars()
    pairs.solver.optimize()
    pairs.printSolution('long')
    pairIDList=pairs.getPairList()
    myDAG.pairList=[]
    for p in pairIDList:
        task1=myDAG.allTasks[p[0]]
        task2=myDAG.allTasks[p[1]]
        myDAG.pairList.append(taskPair(task1, task2))
    scheduled=False

    # set these as desired:
    cores=1
    iterations_for_script = 1 # doesnt impact this script but affects tasket run script's number of iterations

    # could streamline this by getting/ calculating the width
    
    # Now that we have the pairs, compute a schedule using Graham's list.
    while not scheduled and cores <=myDAG.nTotal:
        result=myDAG.schedulePairs(cores, copy.copy(myDAG.pairList))
        scheduled=result[0]
        print("Deadline: ", deadline)
        if scheduled: 
            print("Cores needed: ", cores)
            schedByCore=result[1]
            runId = 1
            finish = 0
            for c in range(cores):
                #print("Pairs on core ", c)
                for p in schedByCore[c]:
                    #print(p.IDs[0], p.IDs[1], "start=", p.start, "finish=", 
                    #      max(p.finish[0], p.finish[1]))
                    t1 = myDAG.allTasks[p.IDs[0]]
                    t2 = myDAG.allTasks[p.IDs[1]]
                    i=t1.name.find('__')
                    if i>=0:
                        shortName1 = t1.name[:i]
                    else:
                        shortName1=t1.name
                    i=t2.name.find('__')
                    if i>=0:
                        shortName2 = t2.name[:i]
                    else:
                        shortName2=t2.name
                    if p.IDs[0]==p.IDs[1]:
                        print(str(0)+", "+shortName1+", "+str(t1.name)+", "+str(iterations_for_script)+", "+str(c+1)+", "+str(runId)+", "+str(1)+", "+str(ns2ms(deadline))+", "+str(1)+", "+str(ns2ms(p.start)))
                    else: # paired
                        print(str(1)+", "+shortName1+", "+str(t1.name)+", "+str(iterations_for_script)+", "+str(c+1)+", "+str(runId)+", "+str(1)+", "+str(ns2ms(deadline))+", "+str(1)+", "+str(ns2ms(p.start))+", "+shortName2+", "+str(t2.name))
                    runId=runId+1
                    finish = max(finish,p.finish[0])
                    finish = max(finish,p.finish[1])
            print("finished at",finish)
            for c in range(cores):
                for p in schedByCore[c]:
                    print(p.IDs[0], p.IDs[1], "start=", p.start, "finish=", 
                          max(p.finish[0], p.finish[1]))
                
        cores+=1
        # end while
    if not scheduled: print("DAG infeasible with",myDAG.nTotal," cores.")

    
    # output C code that implements the schedule computed above.
    
    '''
    Inputs:
        result[1], i.e. schedByCores
        allTasks, to allow me to get task names
        
        For each core used:
            create 2 pthreads
            
        For each pthread:
            call subtasks in order where there start.
            As each subtask completes, signal all its predecessors (broadcast?)
            Before each subtask starts, it needs to wait on a signal from its predecessors.
            
        Starting file: edit the original C file to not have a main method.
        I'm writing a new main method onto that file.
        
        What is success?
            ---All precedence and synchronization requirements respected.
            ---Weak success: The total execution time is never greater than the
            deadline, across many runs.
            ---Strong success: Total execution time assuming each pair hits its
            worst observed case at the same time is no greater than the deadline.
        What data do we need?
            ---all runtimes for each pair (remember we can't assume order for
            pairs on different cores; careful with the record keeping.)
            ---start-end time (excluding cache flushes.)  May be easier to compute
            after run is complete.
            ---Not sure I can just ignore cache-flush costs once we go multicore.
            
        Concerning cache-flush:
            ---will negatively affect running jobs; flushes ALL the cache.
            ---could cause excess waiting if we have complex precedence constraints.
            ---Not having cache flush should be acceptable for multicore jobs.
            If single-core jobs are preemptable, even between subtasks, 
            then they need cache flush in place.
            ---subjobs on different cores or executing in different orders
            than initial timing run may be subject to cache effects.
            ---omitting cache flush may change optimal pairings.
            
        What if I flush caches in the timing run but not in the scheduled run?
        ---Scheduled run results should be valid as long as non-preemptivity is maintained.
        ---not clear that timing run is still a good guide for the scheduled run.
        
        What if I only flush cache between dag jobs on timing run?
        ---schedRun subjobs that go out of order or on different cores may take
        longer than in timing run, especially with cache isolation in place.
        
        Decision: Do both the timing and execution runs without cache wiping
        between subjobs.  Consider iterative approach if results are too far apart.
            
        
        pthreads need to be per-process, not per-core?
        
        Goal broken down:
            --without SMT: execute a given process an a pre-determined core only after
            other processes have been completed.
            --with SMT: as above, but also beginning at the exact same time as a process on
            another core.
        
        Output:
            CSV
        '''

            
        


        
        
        
    #sched.schedule()
    #sched.printSolution()
    #sched.solver.getAttr(GRB.Attr.Status)


if __name__== "__main__":
     main() 
     
'''
To-Do:
    -Report results of pairing ILP in useful form. DONE
    -Build a schedule consisting of core assignments + per-core sequence
    -Graham's list? Another ILP? DONE
    ---Minimize cores needed subject to: everything scheduled; 
    deadline respected; pred constraints respected DONE (not true minimization)
    ---Never minimize number of subtasks scheduled simultaneously
    -Express schedule as a C program.  TO-DO.
    
    --get a list of the variables that are paired together.
    --Use to define a new ILP
    
'''
