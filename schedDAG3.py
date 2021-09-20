# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 08:53:41 2019

@author: shosborn
"""


# need to have a fully defined DAG before this can run.

from gurobipy import *
#from random import random, gauss, uniform, choice
import pandas as pd

class schedDAG3:
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

    def printSolution(self):
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
        '''
        for i in range(nTotal):
            for j in range(i, nTotal):
                schedVar=self.schedVarsP[(self.schedVarsP['taskID_1'==i]) & 
                                         (self.schedVarsP['taskID_2'==j]) ]['schedVars'].iloc[0]
                costVar=self.schedVarsP[(self.schedVarsP['taskID_1'==i]) & 
                                         (self.schedVarsP['taskID_2'==j]) ]['costVars'].iloc[0]
                

                if schedVar.x>0:
                    print("Selected pair!")
                    print(i, j)
                    print("schedVar=",schedVar.x)
                    #print("schedVar=",self.schedVars[j][i].x)
                    print("costVar=",costVar.x)
                    print("Cost=", taskSystem.allTasks[i].allCosts[j])
                    print()
                    
                else:
                    print("Pair not chosen.")
                    print(i, j)
                    print("schedVar=",schedVar.x)
                    #print("schedVar=",self.schedVars[j][i].x)
                    print("costVar=",costVar.x)
                    print("Cost=", taskSystem.allTasks[i].allCosts[j])
                    print()
                    
        print("All Cost vars:")
        for i in range(nTotal):
            for j in range(nTotal):
                print(i, j, self.costVars[i][j].x)
                    
        print("varTotalCost=",self.varTotalCost.x)
        #print("localTotalCost=",self.localTotalCost.x)
        '''
        print("End of solution")

    def createSchedVars(self):
        taskSystem=self.dag
        deadline=taskSystem.deadline

        self.schedVars={'taskID_1'      : [],
                        'taskID_2'      : [],
                        'schedVar'      : [],
                        'costVar'       : [],
                        'startVar'      : [],
                        'finishVar'     : []
                }



        for i in range(self.dag.nTotal):
            subTask1=taskSystem.allTasks[i]
            exprScheduled = LinExpr()
            for j in range(i, self.dag.nTotal):
                subTask2=taskSystem.allTasks[j]
                
                #code will be more efficient if I can avoid creating vars
                #for precedence-constrainted subtasks
                if i in subTask2.predList:
                    continue
                maxCost=max(subTask1.allCosts[j], subTask2.allCosts[i])
                
                var = self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                costVar=self.solver.addVar(vtype=GRB.INTEGER)
                self.solver.addConstr(lhs=costVar, rhs=var*maxCost, sense=GRB.EQUAL)
                startVar=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                finishVar=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                
                self.schedVars['taskID_1'].append(i)
                self.schedVars['taskID_2'].append(j)
                self.schedVars['schedVar'].append(var)
                self.schedVars['costVar'].append(costVar)
                self.schedVars['startVar'].append(startVar)
                self.schedVars['finishVar'].append(finishVar)
                
                #if two tasks are not co-scheduled, then the corresponding finish var can take any value
                self.solver.addConstr(lhs=finishVar, rhs=startVar+subTask1.allCosts[j]*var,
                                      sense=GRB.GREATER_EQUAL)

                
                
                    
                if i!=j:
                    '''
                    var2 = self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    costVar2=self.solver.addVar(vtype=GRB.INTEGER)
                    self.schedVars['taskID_2'].append(i)
                    self.schedVars['taskID_1'].append(j)
                    self.schedVars['schedVar'].append(var2)
                    self.schedVars['costVar'].append(costVar2)
                    '''
                    self.schedVars['taskID_2'].append(i)
                    self.schedVars['taskID_1'].append(j)
                    self.schedVars['schedVar'].append(var)
                    self.schedVars['costVar'].append(costVar)
                    self.schedVars['startVar'].append(startVar)
                    #finish var is different for the two tasks!
                    finishVar2=self.solver.addVar(lb=0, ub=deadline, vtype=GRB.INTEGER)
                    self.schedVars['finishVar'].append(finishVar2)
                    self.solver.addConstr(lhs=finishVar2, rhs=startVar+subTask2.allCosts[i]*var,
                                      sense=GRB.GREATER_EQUAL)

                    
                    #i scheduled with j iff j scheduled with i
                    #self.solver.addConstr(lhs=var, rhs=var2, sense=GRB.EQUAL)
                    #self.solver.addConstr(lhs=costVar, rhs=costVar2, sense=GRB.EQUAL)
                #end if  
            #end j loop
        #end i loop
        
        self.schedVarsP=pd.DataFrame(self.schedVars)
        
        #everything is scheduled
        for i in range(self.dag.nTotal):
            subTask1=self.dag.allTasks[i]
            schedVars_I=self.schedVarsP[(self.schedVarsP['taskID_1']==i)]
            exprTaskScheduled=LinExpr()
            #sum is at least one
            #for each row in schedVars i
            for k in range(schedVars_I.shape[0]):
                exprTaskScheduled+=schedVars_I['schedVar'].iloc[k]
            #end k loop
            '''
            for j in range(self.dag.nTotal):
                subTask2=self.dag.allTasks[j]
                if not (j in subTask2.predList or i in subTask1.predList):
                    exprTaskScheduled+=schedVars_I['schedVar'].iloc[j]
            #end j loop
            '''
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
            
            
        '''    
        self.solver.addConstr(lhs=exprTotalCost, rhs=self.varTotalCost, sense=GRB.EQUAL)
        schedVars_I=self.schedVarsP[(self.schedVarsP['taskID_1']==i)]
        noDuplicates=self.schedVarsP[(self.schedVarsP['taskID_1']<=['taskID_2'])]
        for c in noDuplicates['costVar']:
            exprTotalCost+=c
        '''
        self.solver.addConstr(lhs=exprTotalCost, rhs=self.varTotalCost, sense=GRB.EQUAL)
            
        '''
        for i in range(self.dag.nTotal):
            subTask1=self.dag.allTasks[i]
            schedVars_I=self.schedVarsP[(self.schedVarsP['taskID_1']==i)]
            exprCost=LinExpr()
            #sum is at least one
            for j in range(i, self.dag.nTotal):
                subTask2=self.dag.allTasks[j]
                if not (j in subTask2.predList or i in subTask1.predList):
                    exprTotalCost+=schedVars_I['costVar'].iloc[j]
            #end j loop
        #end i loop
        self.solver.addConstr(lhs=exprTotalCost, rhs=self.varTotalCost, sense=GRB.EQUAL)
        '''

        #add precedence constraints
        for i in range(self.dag.nTotal):
            subTask1=self.dag.allTasks[i]
            startVarList=self.schedVarsP[(self.schedVarsP['taskID_1']==i)]
            for p in subTask1.predList:
                #all startVars for subTask 1 >= all finish vars for p
                #print("Adding precedence constraint:")
                #print("Constraint: ", p, " preceeds ", i)
                finVarList=startVarList[(startVarList['taskID_2']==p)]['finishVar']
                for s in startVarList['startVar']:
                    for predFinish in finVarList:
                        self.solver.addConstr(lhs=s, rhs=predFinish, sense=GRB.GREATER_EQUAL)
            #end p loop
        #end i loop



 