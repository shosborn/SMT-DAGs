//ONLY WORKS WITH FFT2!
//NODE COUNT IS CURRENTLY HARD-CODED!


#define _GNU_SOURCE
#include <fcntl.h>     // For O_CREAT and O_RDWR
#include <sched.h>     // For sched_yield()
#include <semaphore.h> // For sem_{open, post, wait}()
#include <stdio.h>
#include <stdlib.h>    // For exit()
#include <string.h>    // For strlen()
#include <sys/mman.h>  // For mlockall()
#include <unistd.h>    // For ftruncate()
#include <time.h>
#include <sched.h>	// to check cpuID

#ifdef PAIRED
long long unsigned *_rt_start_time;
long long unsigned *_rt_end_time;
#else
long long unsigned *_rt_exec_time;
#endif

long _rt_jobs_complete;
long _rt_loop_count;
long _rt_max_subtasks;
int _rt_core;
int _rt_will_output;
struct timespec _rt_start, _rt_end;

char *_rt_run_id;
char *_rt_our_prog_name;
#define _RT_FILENAME_LEN 64
#define _BILLION (1000*1000*1000)

//int subTaskCounter=0;
//TO-DO: fix the hard-coding
//#define subTaskCount 26;

int subTaskCount;

//#TO-DO: include arg parser. Do it right!

static void _rt_set_up(int argc, char **argv){

	subTaskCount = 26;

	if (argc!=4){
		fprintf(stderr, "Usage: %s <loops> <runID> <save results?> \n", argv[0]);
		fprintf(stderr, " <loops> Number of times to repeat the DAG. \n");
		fprintf(stderr, " <runID> string to append with .txt to yield output file name.\n");
		fprintf(stderr, " <save results?> 1 to save results, 0 to discard. \n");
		exit(1);
		
	}

	_rt_loop_count = atol(argv[1]);

	_rt_run_id = argv[2];
	_rt_will_output = atoi(argv[3]);
	
	//get program name
	//get # of runs to do
	//output?
	//file name?
	//core ID? I think only need it if I want to put in output
	_rt_jobs_complete = 0;
	//TO-DO: fix the hard coding
	_rt_max_subtasks = subTaskCount * _rt_loop_count;
	//multiplier is because we're saving start and end times, not just total
	_rt_exec_time = calloc(_rt_max_subtasks * _rt_will_output *4 , sizeof (long long unsigned));
    if (!_rt_exec_time) {
        perror("Unable to allocate buffer for execution times");
        exit(1);
	}
	mlockall(MCL_CURRENT || MCL_FUTURE);
}

// Save all buffered timing results to disk
static void _rt_write_to_file() {
    //printf("Attempting to write to file. \n");
    char fileName[_RT_FILENAME_LEN];
    FILE *fp;
    munlockall();
    if (!_rt_will_output)
        //goto out;
		//Not sure why Joshua had this as a goto
		exit(0);
    strcpy(fileName, _rt_run_id);
    strcat(fileName, ".csv");
    fp = fopen(fileName, "a");
    if (fp == NULL) {
        perror("Unable to open output file");
        exit(1);
    }
	
	//Loop through all saved values
	//Remember that values from the first loop weren't saved
	
	
	for (int i = 0; i< _rt_loop_count-1; i++){
		//loop through the number of subtasks we have
		for (int j = 0; j<subTaskCount*2; j++){
			//print the value
			fprintf(fp, "%llu%s", _rt_exec_time[i*subTaskCount + j], ",");
		}
		//print newline
		fprintf(fp, "\n");
	}
    fclose(fp);
    free(_rt_exec_time);
    printf("File writing done.! \n");
}

// On x86 call the wbinvld instruction (it's in a kernel module due to it being ring-0)
static void _rt_flush_caches(){
    FILE *fp = fopen("/proc/wbinvd", "r");
    if (fp == NULL) 
	{
        perror("Cache flush module interface cannot be opened");
        exit(1);\
    }
    char dummy;
    if (fread(&dummy, 1, 1, fp) == 0) {\
        perror("Unable to access cache flush module interface");\
        exit(1);\
    }
    fclose(fp);
}


// Start a job
static void _rt_start_timer() {
    //printf("Starting timer. \n");
    //_rt_flush_caches();	
    clock_gettime(CLOCK_MONOTONIC, &_rt_start);
}

static void _rt_save_job_result(int a, struct timespec _rt_start, struct timespec _rt_end) {
    //printf("Saving job result. \n");	
    if (!_rt_will_output)
        return;
    if (a > 4*_rt_max_subtasks) {
        fprintf(stderr, "Max jobs setting too small! Trying to record job #%ld when we only have space for %ld jobs. Exiting...\n", _rt_jobs_complete, _rt_max_subtasks);
        exit(1);
    }
	/*savedSubTaskCount is made to equal the number of subtasks (nodes)
	and then remains constant.  _rt_jobs_complete is incremented after
	every subjob (node), including the first unrecorded loop.  Subtraction
	enables saving only the results we want to.
	*/
	
	//save start time _rt_start.tv_sec*BILLION + _rt_start.tv_nsec;
	//save stop time  _rt_end.tv_sec*BILLION + _rt_end.tv_nsec;
	
	_rt_exec_time[a]=_rt_start.tv_sec * _BILLION + _rt_start.tv_nsec;
	_rt_exec_time[a+1]=_rt_end.tv_sec * _BILLION + _rt_end.tv_nsec;

    //printf("Job result saved. \n");
}


// Complete a job
static void _rt_stop_timer() {
    clock_gettime(CLOCK_MONOTONIC, &_rt_end);
}


/*
static void _rt_saveSubtaskCount() {
	//Function called at end of benchmark's main loop
	//will only be true the first time around
	if (_rt_jobs_complete <= savedSubTaskCount){
		savedSubTaskCount=_rt_jobs_complete;
		//printf("Saving subtask count. \n");
		_rt_max_subtasks = savedSubTaskCount * _rt_loop_count;
		_rt_exec_time = calloc(_rt_max_subtasks * _rt_will_output, sizeof (long long));
		if (!_rt_exec_time){
			perror("Unable to allocate buffer for execution times.");
			exit(1);
		}
	}
}
*/


#define SET_UP _rt_set_up(argc, argv);

//#define START_TIMER _rt_start_timer();
#define START_TIMER clock_gettime(CLOCK_MONOTONIC, &_rt_start);

//#define WRITE_TO_FILE _rt_write_to_file();

//#define STOP_TIMER _rt_stop_timer();

#define STOP_TIMER clock_gettime(CLOCK_MONOTONIC, &_rt_end);

#define FLUSH_CACHE _rt_flush_caches();
