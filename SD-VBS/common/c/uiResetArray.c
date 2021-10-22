/********************************
Author: Sravanthi Kota Venkata
********************************/

#include <stdio.h>
#include <stdlib.h>
#include "sdvbs_common.h"

void uiResetArray(UI2D* out, int rows, int cols, int val)
{
    int i, j;

    
    for(i=0; i<rows; i++)
        for(j=0; j<cols; j++)
            subsref(out,i,j) = val;
    
    
}
