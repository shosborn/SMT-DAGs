/********************************
Author: Sravanthi Kota Venkata
********************************/

#include "sdvbs_common.h"

int iCheck(I2D* in1, I2D* in2){
	if(in1->width != in2 -> width || in1->height != in2->height) return 0;
	for(int i = 0; i < in1->width;i++){
		for(int j = 0; j < in1->height;j++){
			if(subsref(in1,i,j) != subsref(in2,i,j)) return 0;
		}
	}
	return 1;

}


