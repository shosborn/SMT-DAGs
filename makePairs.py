# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 08:53:41 2019

@author: shosborn
"""


# need to have a fully defined DAG before this can run.
from gurobipy import *
#from random import random, gauss, uniform, choice
import pandas as pd

class makePairs:
    #create variables for frame sizes
    
    def __init__(self, dag):
        self.solver=Model("qcp")
        self.dag=dag
        
    #print("Testing if arguments work.")
    #print(taskSystem.allTasks[1].allCosts[5])
     
    def setSolverParams(self):
        #taskSystem=self.taskSystem
        self.solver.setParam("TimeLimit", self.dag.timeout)
        self.solver.setParam("SolutionLimit", self.dag.solutionLimit)
        self.solver.setParam(GRB.Param.Threads, self.dag.threadsPerTest)
        #For fastest peformance, set lb=ub=1
        coreLB=1
        #coreUB=(self.dag.totalCost/self.dag.deadline)*2 + 1
        coreUB=100
        #self.varCoreCount=self.solver.addVar(lb=coreLB, ub=coreUB, vtype=GRB.INTEGER)
        #self.solver.setObjective(self.varCoreCount, GRB.MINIMIZE)
        self.varTotalCost=self.solver.addVar(vtype=GRB.INTEGER)
        self.solver.setObjective(self.varTotalCost, GRB.MINIMIZE)
    
    def schedule(self):
        self.setSolverParams()
        self.createSchedVars()
        self.solver.optimize()
        #self.printSolution()
        
        return self.solver.getAttr(GRB.Attr.Status)

                    
        print("All Cost vars:")
        for i in range(nTotal):
            for j in range(nTotal):
                print(i, j, self.costVars[i][j].x)
                    
        print("varTotalCost=",self.varTotalCost.x)
        #print("localTotalCost=",self.localTotalCost.x)
        print("End of solution")

    def evaluateSchedVar(self, schedVar):
        if schedVar.x==1: return True
        else: return False
        
    '''
    def pairList(self):
        self.schedVarsP['result'] = self.schedVarsP[(self.schedVarsP['schedVar'].apply(evaluate))]
        solution=self.schedVarsP[(self.schedVarsP['result']==True)][taskID_1][taskID_2]
        print(solution)
    '''
    
    def getPairList(self):
        self.schedVarsP['result'] = self.schedVarsP['schedVar'].apply(self.evaluateSchedVar)
        resultDF = self.schedVarsP[(self.schedVarsP['result'] == True)
                                   ][['taskID_1', 'taskID_2']]
        return [tuple(r) for r in resultDF.values.tolist()]
    
    def printSolution(self, length):
        self.schedVarsP['result'] = self.schedVarsP['schedVar'].apply(self.evaluateSchedVar)
        #solution=self.schedVarsP[(self.schedVarsP['result']==True)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)
        #print(self.schedVarsP)
        
        
        #this line works
        #resultDF = self.schedVarsP[self.schedVarsP['result'] == True][['taskID_1', 'taskID_2']]
        if length=='short':
            resultDF = self.schedVarsP[(self.schedVarsP['result'] == True)
                                   ][['taskID_1', 'taskID_2']]
        else:
            resultDF = self.schedVarsP[(self.schedVarsP['result'] == True)
                                   ][['taskID_1', 'taskID_2', 'costVar', 'startVar', 'finishVar1', 'finishVar2']]
        #print(resultDF)
        print(resultDF)
        #print(self.schedVarsP[(self.schedVarsP['result']==1)]['taskID_1','taskID_2'])
        
        '''
        taskSystem=self.dag
        deadline=taskSystem.deadline
        nTotal=self.dag.nTotal
        
        print('*****')
        print("Printing Solution")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        #pd.set_option('display.width', None)
        #pd.set_option('display.max_colwidth', -1)

        print(self.schedVarsP[['taskID_1','taskID_2', 'costVar', 'startVar', 'finishVar']])
        print("End of solution")
        '''

    def createSchedVars(self):
        taskSystem=self.dag
        deadline=taskSystem.deadline

        self.schedVars={'taskID_1'      : [],
                        'taskID_2'      : [],
                        'schedVar'      : [],
                        'costVar'       : [],
                        'startVar'      : [],
                        'finishVar1'     : [],
                        'finishVar2'    :[]
                }



        for i in range(self.dag.nTotal):
            subTask1=taskSystem.allTasks[i]
            exprScheduled = LinExpr()
            for j in range(i, self.dag.nTotal):
                subTask2=taskSystem.allTasks[j]
                
                #code will be more efficient if I can avoid creating vars
                #for precedence-constrainted subtasks
                if i in subTask2.predList or j in subTask1.predList:
                    continue
                maxCost=max(subTask1.allCosts[j], subTask2.allCosts[i])
                
                var = self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                costVar=self.solver.addVar(vtype=GRB.INTEGER)
                self.solver.addConstr(lhs=costVar, rhs=var*maxCost, sense=GRB.EQUAL)
                startVar=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                finishVar1=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                finishVar2=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                
                self.schedVars['taskID_1'].append(i)
                self.schedVars['taskID_2'].append(j)
                #self.schedVars['t1LesserEq'].append(i<=j)
                self.schedVars['schedVar'].append(var)
                self.schedVars['costVar'].append(costVar)
                self.schedVars['startVar'].append(startVar)
                self.schedVars['finishVar1'].append(finishVar1)
                self.schedVars['finishVar2'].append(finishVar2)
                
                #if two tasks are not co-scheduled, then the corresponding finish var can take any value
                self.solver.addConstr(lhs=finishVar1, rhs=(startVar+subTask1.allCosts[j])*var,
                                      sense=GRB.EQUAL)
                self.solver.addConstr(lhs=finishVar2, rhs=(startVar+subTask2.allCosts[i])*var,
                                      sense=GRB.EQUAL)

                
                
                '''    
                if i!=j:

                    self.schedVars['taskID_2'].append(i)
                    self.schedVars['taskID_1'].append(j)
                    self.schedVars['t1LesserEq'].append(i>j)
                    self.schedVars['schedVar'].append(var)
                    self.schedVars['costVar'].append(costVar)
                    self.schedVars['startVar'].append(startVar)
                    #finish var is different for the two tasks!
                    finishVar2=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                    self.schedVars['finishVar'].append(finishVar2)
                    self.solver.addConstr(lhs=finishVar2, rhs=startVar+subTask2.allCosts[i]*var,
                                      sense=GRB.GREATER_EQUAL)
                '''
                #end if  
            #end j loop
        #end i loop
        
        self.schedVarsP=pd.DataFrame(self.schedVars)
        
        
        #everything is scheduled
        for i in range(self.dag.nTotal):
            subTask1=self.dag.allTasks[i]
            schedVars_I=self.schedVarsP[(self.schedVarsP['taskID_1']==i) | (self.schedVarsP['taskID_2']==i)]
            exprTaskScheduled=LinExpr()
            #sum is at least one
            #for each row in schedVars i
            for k in range(schedVars_I.shape[0]):
                exprTaskScheduled+=schedVars_I['schedVar'].iloc[k]
            #end k loop
            self.solver.addConstr(lhs=exprTaskScheduled, rhs=1, sense=GRB.EQUAL)
        #end i loop
        
        #determine costs
        exprTotalCost=LinExpr()
        for i in range(self.dag.nTotal):
            subTask1=self.dag.allTasks[i]
            schedVars_I=self.schedVarsP[(self.schedVarsP['taskID_1']==i)]
            noDuplicates=schedVars_I[(schedVars_I['taskID_2']>=i)]
            for k in range(noDuplicates.shape[0]):
                exprTotalCost += noDuplicates['costVar'].iloc[k]
        self.solver.addConstr(lhs=exprTotalCost, rhs=self.varTotalCost, sense=GRB.EQUAL)
        
        #precedence constraints

        for i in range(self.dag.nTotal):
            subTask1=self.dag.allTasks[i]
            schedVars_I=self.schedVarsP[(self.schedVarsP['taskID_1']==i) | 
                    (self.schedVarsP['taskID_2']==i)]
            for p in subTask1.predList:
                schedVars_P1=self.schedVarsP[(self.schedVarsP['taskID_1']==p)]
                schedVars_P2=self.schedVarsP[(self.schedVarsP['taskID_2']==p)]
                for j in range(schedVars_I.shape[0]):
                    startVar=schedVars_I['startVar'].iloc[j]
                    for k1 in range(schedVars_P1.shape[0]):
                        finishVar1=schedVars_P1['finishVar1'].iloc[k1]
                        #schedVar=schedVars_P1['schedVar'].iloc[k1]
                        #self.solver.addConstr(lhs=startVar, rhs=finishVar1*schedVar, sense=GRB.GREATER_EQUAL)
                        self.solver.addConstr(lhs=startVar, rhs=finishVar1, sense=GRB.GREATER_EQUAL)
                    for k2 in range(schedVars_P2.shape[0]):
                        finishVar2=schedVars_P2['finishVar2'].iloc[k2]
                        #schedVar=schedVars_P2['schedVar'].iloc[k2]
                        #self.solver.addConstr(lhs=startVar, rhs=finishVar2*schedVar, sense=GRB.GREATER_EQUAL)
                        self.solver.addConstr(lhs=startVar, rhs=finishVar2, sense=GRB.GREATER_EQUAL)
         




 