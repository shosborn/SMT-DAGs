# -*- coding: utf-8 -*-
"""
Created on Thu Oct 14 09:28:43 2021

@author: simsh
"""
import csv
import pandas as pd

def dataToPandas(dataFile, nameFile):
    data={'node1':[],
            'node1Start':[],
            'node1Finish':[],
            'node1Exec':[],
            'node1FromFirstStart':[],
            'node1FromLoopStart':[],
            'node2':[],
            'node2Start':[],
            'node2Finish':[],
            'node2Exec':[],
            'node2FromFirstStart':[],
            'node2FromLoopStart':[],
            'finishDif':[],
            'startDif':[]
            }
    '''
    df=pandas.DataFrame(columns=['node1', 'node1Start', 'node1Finish', 
                                 'node2', 'node2Start', 'node2Finish'])
    '''
    # read in subtask names
    # odd entries are for task1, even for task2
    nameList=[]
    with open(nameFile) as f:
        myReader=csv.reader(f)
        for row in myReader:
            #print(row)
            nameList.append(row[0])
            nameList.append(row[1])
    #done with reading in names
    print(nameList)
    
    with open(dataFile) as d:
        myReader=csv.reader(d)
        for row in myReader:
            #nameList will always be even
            pairCount=int(len(nameList)/2)
            #i tracks position in nameList
            #j tracks position in each row of data
            i=j=0
            loopStart=int(row[0])
            while i < 2*pairCount:
                # add the task names and start/stop times
                data['node1'].append(nameList[i])
                data['node2'].append(nameList[i+1])
                data['node1Start'].append(int(row[j]))
                data['node1Finish'].append(int(row[j+1]))
                data['node1Exec'].append(int(row[j+1])-int(row[j]))
                data['node1FromLoopStart'].append(int(row[j+1])-loopStart)
                if (nameList[i+1]=="NONE"):
                    data['node2Start'].append('NA')
                    data['node2Finish'].append('NA')
                    data['node2Exec'].append('NA')
                    data['startDif'].append('NA')
                    data['finishDif'].append('NA')
                    data['node1FromFirstStart'].append(int(row[j+1])-int(row[j]))
                    data['node2FromFirstStart'].append('NA')
                    data['node2FromLoopStart'].append('NA')
                    #j=i+2
                    j=j+2
                else:
                    data['node2Start'].append(int(row[j+2]))
                    data['node2Finish'].append(int(row[j+3]))
                    data['node2Exec'].append(int(row[j+3])-int(row[j+2]))
                    data['startDif'].append(int(row[j])-int(row[j+2]))
                    data['finishDif'].append(int(row[j+1])-int(row[j+3]))
                    minStart=min(int(row[j]), int(row[j+2]))
                    data['node1FromFirstStart'].append(int(row[j+1])-minStart)
                    data['node2FromFirstStart'].append(int(row[j+3])-minStart)
                    data['node2FromLoopStart'].append(int(row[j+3])-loopStart)
                    
                    j=j+4
                i=i+2
            #end of while i< pairCount
            #finished 1 row in datafile
            
            #add info for time taken by the whole task.
            #assumes first and last nodes are solos
            
            #edit C code to print start and finish times
            '''
            data['node1'].append('FullTask')
            data['node2'].append('NONE')
            data['node1Start'].append(row[0])
            data['node1Finish'].append(row[pairCount*4])
            data['node2'].append('NONE')
            data['node2Start'].append('NA')
            data['node2Start'].append('NA')
            '''
        #end of for row in myReader
        
        #take a look at what we have so far
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)
        
            
    
    #now have all the raw data
    df=pd.DataFrame(data)
    
    dfCompact = df.drop(['node1Start', 'node1Finish', 
                         'node2Start', 'node2Finish', 
                         'node1Exec', 'node2Exec',
                         'node1FromFirstStart', 'node2FromFirstStart',
                         'node1FromLoopStart', 'node2FromLoopStart',
                         'node2'], axis=1)
    
    df.info()
    print(dfCompact.head(15))
    print(dfCompact.tail(15))
    print(dfCompact)
    #print(df.head(10))
    
    
    
    '''
    
    
    
    
    What do I see that's wrong?
    ---start difference range from a few hundred nanoseconds to huge.
    ---combine16 has a huge execution time on thread 0 but no thread 1.
    ---start differnces run in blocks that alternate between a few hundred ns
    and a few thousand.
    
    ---How closely related are these issues? I don't know!
    
    What could be the problem?
    ---code not running in parallel.
    ---I'm recording it wrong.
    ---OpenMP synchronization is just that bad.  Threads take too long to get past the barrier.
    ---Underlying code issue I haven't considered.
    
    What is not the problem?
    ---barrier are not working; I've verified the barriers are barricading.
    ---Problem is NOT exclusive to use of hyperthreads, but possibly caused by the strict synchronization
    I'm using to support hyperthreads.
    
    What happens if I do this in parallel but without SMT?
    ---Similar pattern (high start difference, combine16 is extra troublesome.)
    In some cases the execution times are worse (which suggests a cache affinity issue.)
    
    What about running it on one core?
    ---one thread of combine16 still gets hit with high costs, around 85 microseconds.
    ---reading stuff from main memory and the second thread gets the benefit of it being cached?
    
    What if I don't flush the cache?
    ---Not a huge difference.  Does cause pattern of small positive or large negative difference.
    
    
    
    '''
    #add task totals
    
    #add missing time per task
    
    #add max per pair
    
    #add end-end per pair
    
    #add start time differentials
    
    #add predicted values and % difference
    


                    

def main():
    dataFile='testNoPrinter.csv'
    nameFile='DataEntryOrder.csv'
    
    dataToPandas(dataFile, nameFile)

if __name__== "__main__":
     main() 