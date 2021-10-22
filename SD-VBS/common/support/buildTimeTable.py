import re
import sys
import os

def getExprName(fileName):
    exprFileName = os.path.basename(fileName)
    exprName = re.sub("\.txt", "", exprFileName)
    exprName = re.sub("_","\t", exprName, 1)
    exprName = re.sub("_", "", exprName)
    return(exprName)

def getBmrkName(fileName):
    benchmarkDir = os.path.dirname(fileName)
    benchmarkName = os.path.basename(benchmarkDir)
    return(benchmarkName)

def getTimeTup(fileName):
    try:
        inp = open(fileName, 'r')
    except IOError, err:
        print "ERROR: Could not open the inputFile:"+fileName
        sys.exit(1)
    globalTup = None
    for currline in inp:
        currline = currline.strip()
        currline = currline.lower()
        if(re.match("real", currline)):
            #valTup = re.findall("(\d+)", currline)

            return(currline[4:].strip())

    if(globalTup != None):
        return(globalTup)
    else:
        print "ERROR: INVALID INPUT FILE:"+fileName
        sys.exit(2)

def main():
    if(len(sys.argv)<2):
        print "USAGE: "+sys.argv[0]+" <inputFileName>"
        sys.exit(1)

    fileName = sys.argv[1]
    exprName = getExprName(fileName)
    benchmarkName = getBmrkName(fileName)
    timeTup = getTimeTup(fileName)
    
    print "%-20s %-20s %10s\n" % (benchmarkName,exprName,timeTup)





if __name__=="__main__":
    main()
