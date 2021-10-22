/**
 * Copyright 2019 Sims Hill Osborne and 2020 Joshua Bakita
 *
 * This header provides facilities by which to separably run and time TACLeBench
 * To use this for paired task timing, define PAIRED (pass CFLAGS=-DPAIRED to make)
 **/
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

// This is only visible if _GNU_SOURCE is defined, and that define does not
// come along to places where this file is included. Address this by manually
// forcing it into the global namespace.
extern int sched_getcpu();

// These constants correspond to the imx6q-sabredb platform
#define LINE_SIZE 32
#define L2_SIZE 16*2048*32

#if __arm__
#include <unistd.h>
#include <sys/syscall.h>
#endif

// This is a proxy for "case study mode" now
#define LITMUS 1    
#define MMDC_PROF 0

#if LITMUS
#include <litmus.h>
#endif

#if MMDC_PROF
#include  "/media/speedy/litmus/tools/mmdc/mmdc.h"
#endif

// Store state globally so that the job can be outside main()
// Arrays use float as a comprimise between overflow and size
// Paired arrays use long longs as precision is more important for those times
#ifdef PAIRED
long long *_rt_start_time;
long long *_rt_end_time;
#else
float *_rt_exec_time;
#endif
#if MMDC_PERF
float *_rt_mmdc_read;
float *_rt_mmdc_write;
#endif
long _rt_jobs_complete;
long _rt_max_jobs;
int _rt_core;
int _rt_will_output;
struct timespec _rt_start, _rt_end;

char *_rt_run_id;
char *_rt_our_prog_name;
char *_rt_other_prog_name;
char *_rt_other_core;
#define _RT_FILENAME_LEN 64
#define _BILLION (1000*1000*1000)
#ifdef PAIRED
char *_rt_barrier;
sem_t *_rt_first_sem, *_rt_second_sem;
int _rt_lock_id;
#define _ID_SZ 128
char _rt_sem1_name[_ID_SZ] = "/_libextra_first_sem-";
char _rt_sem2_name[_ID_SZ] = "/_libextra_second_sem-";
char _rt_shm_name[_ID_SZ] = "/_libextra_barrier-";
#endif /* PAIRED */

#if LITMUS
lt_t _rt_period;
lt_t _rt_phase;
int _rt_crit;
struct control_page *_rt_cp;
#endif

static void _rt_load_params_itrl(int argc, char **argv) {
#ifdef PAIRED
    if (argc != (9 + LITMUS*2) && argc != (10 + LITMUS*2)) {
        fprintf(stderr, "Usage: %s <name> <loops> <my core> <other core> <other name> <runID> <save results?> <pairID> <task period> <task criticality> <task phase>\n", argv[0]);
#else
    if (argc != (7 + LITMUS*2)) {
        fprintf(stderr, "Usage: %s <name> <loops> <my core> <runID> <save results?> <task period> <task criticality> <task phase>\n", argv[0]);
#endif /* PAIRED */
        fprintf(stderr, " <name> string for logging. Name of this task.\n");
        fprintf(stderr, " <loops> integer number of iterations. -1 for infinite.\n");
        fprintf(stderr, " <my core> integer core number. Only used for LITMUS-RT.\n");
#ifdef PAIRED
        fprintf(stderr, " <other core> integer for logging. Core of paired task.\n");
        fprintf(stderr, " <other name> string for logging. Name of paired task.\n");
#endif /* PAIRED */
        fprintf(stderr, " <runID> string to append with .txt to yield output file name.\n");
        fprintf(stderr, " <save results?> 1 to save results, 0 to discard.\n");
#ifdef PAIRED
        fprintf(stderr, " <pairID> (optional).\n");
#endif
#if LITMUS
        fprintf(stderr, " <task period> in ms\n");
        fprintf(stderr, " <task criticality level> 0 for Level-A, 1 for Level-B, 2 for Level-C\n");
	    fprintf(stderr, " <task phase> in ms\n");
#endif /* LITMUS */
        exit(1);
    }
    _rt_our_prog_name = argv[1];
    _rt_max_jobs = atol(argv[2]);
#if !LITMUS
    _rt_core = sched_getcpu();
#else
    _rt_core = atoi(argv[3]);
#endif
#ifdef PAIRED
    _rt_other_core = argv[4];
    _rt_other_prog_name = argv[5];
    _rt_run_id = argv[6];
    _rt_will_output = atoi(argv[7]);
    char *pairId;
    int end;
    if (argc > 8) {
        pairId = argv[8];
        end = 9;
    } else {
        pairId = "none";
        end = 8;
    }
#else
    _rt_other_core = "none";
    _rt_other_prog_name = "none";
    _rt_run_id = argv[4];
    _rt_will_output = atoi(argv[5]);
    int end = 6;
#endif /* PAIRED */
    if (_rt_max_jobs < 0 && _rt_will_output != 0) {
        fprintf(stderr, "Infinite loops only supported when output is disabled!\n");
        exit(1);
    }
    if (strlen(_rt_run_id) + 5 > _RT_FILENAME_LEN) {
        fprintf(stderr, "Run ID is too large! Keep it to less than %d characters.\n", _RT_FILENAME_LEN);
        exit(1);
    }
#ifdef PAIRED
    // __rt_sem2_name happens to be the longest
    if (strlen(pairId) + strlen(_rt_sem2_name) > _ID_SZ) {
        fprintf(stderr, "PairID is too long! Maximum length is %ld characters.\n", _ID_SZ - strlen(_rt_sem2_name));
        exit(1);
    }
    _rt_start_time = calloc(_rt_max_jobs * _rt_will_output, sizeof(long long));
    _rt_end_time = calloc(_rt_max_jobs * _rt_will_output, sizeof(long long));
    if (!_rt_end_time || !_rt_start_time) {
        perror("Unable to allocate buffers for execution times");
        exit(1);
    }
    // Use PairID to create unique semaphore and shared memory paths
    strcat(_rt_sem1_name, pairId);
    strcat(_rt_sem2_name, pairId);
    strcat(_rt_shm_name, pairId);
    _rt_first_sem = sem_open(_rt_sem1_name, O_CREAT, 644, 0);
    _rt_second_sem = sem_open(_rt_sem2_name, O_CREAT, 644, 0);
    if (_rt_first_sem == SEM_FAILED || _rt_second_sem == SEM_FAILED) {
        perror("Error while creating semaphores");
        exit(1);
    }
    // Create shared memory for barrier synchronization and infer lock ID
    int barrier_file = shm_open(_rt_shm_name, O_CREAT | O_RDWR | O_EXCL, 644);
    if (barrier_file == -1) {
        // File already existed - we're the 2nd program and thus lock ID 2
        _rt_lock_id = 2;
        barrier_file = shm_open(_rt_shm_name, O_CREAT | O_RDWR, 644);
    } else {
        _rt_lock_id = 1;
    }
    if (barrier_file == -1) {
        perror("Error while creating shared memory for barrier synchronization");
        exit(1);
    }
    if (ftruncate(barrier_file, 2) == -1) {
        perror("Error while setting size of shared memory for barrier synchronization");
        exit(1);
    }
    _rt_barrier = mmap(NULL, 2, PROT_WRITE, MAP_SHARED, barrier_file, 0);
    if (_rt_barrier == MAP_FAILED) {
        perror("Error while mapping shared memory for barrier synchronization");
        exit(1);
    }
    // If we're the 2nd user of this barrier, mark it as in-use
    if (_rt_lock_id == 2 && !__sync_bool_compare_and_swap(_rt_barrier+1, 0, 1)) {
        fprintf(stderr, "Pair ID already in use!\n");
        exit(1);
    }
    *_rt_barrier = 0;
#else
    _rt_exec_time = calloc(_rt_max_jobs * _rt_will_output, sizeof(float));
    if (!_rt_exec_time) {
        perror("Unable to allocate buffer for execution times");
        exit(1);
    }
#endif /* PAIRED */
    _rt_jobs_complete = 0;
    mlockall(MCL_CURRENT || MCL_FUTURE);
#if LITMUS
    _rt_period = ms2ns(strtoul(argv[end], NULL, 10));
    _rt_crit = atoi(argv[end+1]);
    _rt_phase = ms2ns(strtoul(argv[end+2], NULL, 10));
    // _rt_phase = 0;
    unsigned int wait = 1;
    if (be_migrate_to_domain(_rt_core) < 0) {
        perror("Unable to migrate to specified CPU");
        exit(1);
    }
    struct rt_task rt_param;
    init_rt_task_param(&rt_param);
    // Fake exec cost - this value ignored by the MC^2 scheduler
    rt_param.exec_cost = _rt_period;
    rt_param.period = _rt_period;
    rt_param.relative_deadline = 0;
    rt_param.phase = _rt_phase;
    rt_param.priority = LITMUS_LOWEST_PRIORITY;
    // rt_param.priority = ns2ms(_rt_phase);
    rt_param.cls = _rt_crit;
    rt_param.budget_policy = NO_ENFORCEMENT;
    rt_param.cpu = _rt_core;
    rt_param.release_policy = TASK_PERIODIC;
    if (set_rt_task_param(gettid(), &rt_param) < 0) {
        perror("Unable to set real-time parameters");
        exit(1);
    }
    if (init_litmus() != 0) {
        perror("init_litmus failed");
        exit(1);
    }
    if (task_mode(LITMUS_RT_TASK) != 0) {
        perror("Unable to become real-time task");
        exit(1);
    }
    _rt_cp = get_ctrl_page();
    if (wait && wait_for_ts_release() != 0) {
        perror("Unable to wait for taskset release");
        exit(1);
    }
#endif /* LITMUS */
#if MMDC_PROF
    SETUP_MMDC
#endif
}

#define SETUP_MMDC \
    _rt_mmdc_read = calloc(_rt_max_jobs * _rt_will_output, sizeof(float));\
    _rt_mmdc_write = calloc(_rt_max_jobs * _rt_will_output, sizeof(float));\
    if (!_rt_mmdc_read || !_rt_mmdc_write) {\
        perror("Unable to allocate buffer for MMDC data");\
        exit(1);\
    }\
    MMDC_PROFILE_RES_t mmdc_res;\
    memset(&mmdc_res, 0, sizeof(MMDC_PROFILE_RES_t));\
    int fd = open("/dev/mem", O_RDWR, 0);\
    if (fd < 0) {\
        perror("Unable to open /dev/mem");\
        exit(1);\
    }\
    pMMDC_t mmdc = mmap(NULL, 0x4000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, MMDC_P0_IPS_BASE_ADDR);\
    if (mmdc == MAP_FAILED) {\
        perror("Unable to map MMDC address space");\
        exit(1);\
    }\
    mmdc->madpcr1 = axi_arm1;\
    msync(&(mmdc->madpcr1),4,MS_SYNC);

#if __arm__
// On ARM, manually flush the cache
#define FLUSH_CACHES \
    volatile uint8_t buffer[L2_SIZE * 4]; \
    for (uint32_t j = 0; j < 4; j++) \
        for (uint32_t i = 0; i < L2_SIZE * 4; i += LINE_SIZE) \
            buffer[i]++;
#else
// On x86 call the wbinvld instruction (it's in a kernel module due to it being ring-0)
#define FLUSH_CACHES \
    FILE *fp = fopen("/proc/wbinvd", "r");\
    if (fp == NULL) {\
        perror("Cache flush module interface cannot be opened");\
        exit(1);\
    }\
    char dummy;\
    if (fread(&dummy, 1, 1, fp) == 0) {\
        perror("Unable to access cache flush module interface");\
        exit(1);\
    }\
    fclose(fp);
#endif

// This semaphore-based synchronization is from Sims
#define FIRST_UNLOCK \
    if (_rt_lock_id == 1) {\
        if (sem_post(_rt_second_sem) != 0) {\
            perror("Unable to unlock second semaphore");\
            exit(1);\
        }\
    } \
    else {\
        if (sem_post(_rt_first_sem) != 0) {\
            perror("Unable to unlock first semaphore");\
            exit(1);\
        }\
    } \

#define FIRST_LOCK \
    if (_rt_lock_id == 1) {\
        if (sem_wait(_rt_first_sem) != 0) {\
            perror("Unable to wait on first semaphore");\
            exit(1);\
        }\
    }\
    else {\
        if (sem_wait(_rt_second_sem) != 0) {\
            perror("Unable to wait on second semaphore");\
            exit(1);\
        }\
    }

// This ensures a very low difference between pair member start times
#define BARRIER_SYNC \
    if (__sync_bool_compare_and_swap(_rt_barrier, 0, 1)) {\
        while (!__sync_bool_compare_and_swap(_rt_barrier, 0, 0)) {};\
    }\
    else {\
        __sync_bool_compare_and_swap(_rt_barrier, 1, 0);\
    }

// Buffer timing result from a single job
static void _rt_save_job_result() {
    if (!_rt_will_output)
        return;
    if (_rt_jobs_complete >= _rt_max_jobs) {
        fprintf(stderr, "Max jobs setting too small! Trying to record job #%ld when we only have space for %ld jobs. Exiting...\n", _rt_jobs_complete, _rt_max_jobs);
        exit(1);
    }
#ifdef PAIRED
    _rt_start_time[_rt_jobs_complete] = _rt_start.tv_sec;
    _rt_start_time[_rt_jobs_complete] *= _BILLION;
    _rt_start_time[_rt_jobs_complete] += _rt_start.tv_nsec;
    _rt_end_time[_rt_jobs_complete] = _rt_end.tv_sec;
    _rt_end_time[_rt_jobs_complete] *= _BILLION;
    _rt_end_time[_rt_jobs_complete] += _rt_end.tv_nsec;
#else
    _rt_exec_time[_rt_jobs_complete] = _rt_end.tv_sec - _rt_start.tv_sec;
    _rt_exec_time[_rt_jobs_complete] *= _BILLION;
    _rt_exec_time[_rt_jobs_complete] += _rt_end.tv_nsec - _rt_start.tv_nsec;
#endif /* PAIRED */
#if MMDC_PROF
    _rt_mmdc_read[_rt_jobs_complete] = mmdc_res.read_bytes;
    _rt_mmdc_write[_rt_jobs_complete] = mmdc_res.write_bytes;
#endif /* MMDC_PROF */
}

// Save all buffered timing results to disk
static void _rt_write_to_file() {
    char fileName[_RT_FILENAME_LEN];
    FILE *fp;
    munlockall();
    if (!_rt_will_output)
        goto out;
    strcpy(fileName, _rt_run_id);
    strcat(fileName, ".txt");
    fp = fopen(fileName, "a");
    if (fp == NULL) {
        perror("Unable to open output file");
        exit(1);
    }
    // Baseline output uses a similar format with "none" for unused fields
    for (int i = 0; i < _rt_jobs_complete; i++){
        fprintf(fp, "%s %s %u %s %ld", _rt_our_prog_name, _rt_other_prog_name,
            _rt_core, _rt_other_core, _rt_max_jobs);
#ifdef PAIRED
        // For unclear legacy reasons, paired tasks emit sec and ns separately
        fprintf(fp, " %lld %lld %lld %lld",
            _rt_start_time[i] / _BILLION, _rt_start_time[i] % _BILLION,
            _rt_end_time[i] / _BILLION, _rt_end_time[i] % _BILLION);
#else
        fprintf(fp, " %.f", _rt_exec_time[i]);
#endif /* PAIRED */
        fprintf(fp, " %s %d %.f %.f\n",  _rt_run_id, i,
#if MMDC_PROF
            _rt_mmdc_read[i], _rt_mmdc_write[i]);
#else
            0.0, 0.0);
#endif /* MMDC_PROF */
    }
    fclose(fp);
out:
#if LITMUS
    if (task_mode(BACKGROUND_TASK) != 0) {
        perror("Unable to become a real-time task");
        exit(1);
    }
#endif /* LITMUS */
#ifdef PAIRED
    munmap(_rt_barrier, 2);
    sem_unlink(_rt_sem1_name);
    sem_unlink(_rt_sem2_name);
    shm_unlink(_rt_shm_name);
    free(_rt_start_time);
    free(_rt_end_time);
#else
    free(_rt_exec_time);
#endif /* PAIRED */
#if MMDC_PROF
    free(_rt_mmdc_read);
    free(_rt_mmdc_write);
#endif /* MMDC_PROF */
}

// Start a job
static void _rt_start_loop() {
#if LITMUS
    static lt_t last = 0;
    lt_t now = litmus_clock();
    if (now > _rt_cp->deadline) {
        fprintf(stderr, "(%s/%d:%lu) ", _rt_our_prog_name, gettid(), _rt_cp->job_index);
        if (_rt_crit == 0)
            fprintf(stderr, "CATASTROPHIC: Level-A");
        else if (_rt_crit == 1)
            fprintf(stderr, "HAZARDOUS: Level-B");
        else
            fprintf(stderr, "MAJOR: Level-C");
        fprintf(stderr, " tardy %llu ns, "
               "relative tardiness %f\n",
               now - _rt_cp->deadline,
               (now - _rt_cp->deadline) / (double)_rt_period);
    }
    if (last == 0) {
        last = now;
    } 
    // else if (now > last + 60ull * _BILLION && _rt_crit >= 2) {
    //     last = now;
    //     fprintf(stderr, "(%s/%d:%lu) Ping\n", _rt_our_prog_name, gettid(), _rt_cp->job_index);
    // }
    if (sleep_next_period() != 0) {
        perror("Unable to sleep for next period");
    }
#else
    sched_yield();
#endif /* LITMUS */
#ifdef PAIRED
    FIRST_UNLOCK
    FIRST_LOCK
#endif /* PAIRED */
#if !LITMUS
    FLUSH_CACHES
#endif
#ifdef PAIRED
    BARRIER_SYNC
#endif /* PAIRED */
#if MMDC_PROF
    /* This disables profiling, resets the counters, clears the overflow bit, and enables profiling */
    start_mmdc_profiling(mmdc);
#endif /* MMDC_PROF */
    clock_gettime(CLOCK_MONOTONIC, &_rt_start);
}

// Complete a job
static void _rt_stop_loop() {
    clock_gettime(CLOCK_MONOTONIC, &_rt_end);
#if MMDC_PROF
    /* This freezes the profiling and makes results available */
    pause_mmdc_profiling(mmdc);
    get_mmdc_profiling_results(mmdc, &mmdc_res);
#endif /* MMDC_PROF */
    _rt_save_job_result();
    _rt_jobs_complete++;
}

/****** New API ******
 * Intended structure:
 *
 * |int main(int argc, char **argv) {
 * |  SET_UP
 * |  ...
 * |  for_each_job {
 * |    tacleInit();
 * |    tacleMain();
 * |  }
 * |  WRITE_TO_FILE
 * |}
 *
 * The main() function must call its parameters argc and argv for SET_UP to be
 * able to read them.
 * Only SET_UP necessarily has to be in main().
 *
 * We use some niche C features, here's a quick explaination:
 * 1. The && operator doesn't evaluate the right-hand side of the expression
 *    unless the left side evaluated to true. We use this to only execute 
 *    _rt_start_loop() when the loop will actually run.
 * 2. The comma operator executes the first expression and then throws away the
 *    result. We use this to call our void function from inside a comparison.
 */
#define for_each_job \
    for (; (_rt_max_jobs == -1 || _rt_jobs_complete < _rt_max_jobs) && (_rt_start_loop(),1); \
         _rt_stop_loop())

/****** Legacy API ******
 * Intended structure:
 *
 * |int main(int argc, char **argv) {
 * |  SET_UP
 * |  for (jobsComplete=0; jobsComplete<maxJobs; jobsComplete++){
 * |    START_LOOP
 * |    tacleInit();
 * |    tacleMain();
 * |    STOP_LOOP
 * |  }
 * |  WRITE_TO_FILE
 * |  tacleReturn
 * |}
 *
 * The main() function must call its parameters argc and argv for SET_UP to be
 * able to read them.
 */
static int jobsComplete = 0;
#define SET_UP _rt_load_params_itrl(argc, argv);
#define START_LOOP _rt_start_loop();
#define STOP_LOOP _rt_stop_loop();
#define WRITE_TO_FILE _rt_write_to_file();
#define maxJobs _rt_max_jobs
// Has been part of STOP_LOOP for quite some time
#define SAVE_RESULTS \
    #warning "The SAVE_RESULTS macro is deprecated and will soon be removed!";
// Unclear if SLEEP is used anywhere.
#define SLEEP \
    #warning "The SLEEP macro is deprecated and may be removed!" \
    nanosleep((const struct timespec[]){{0, 1000000}}, NULL);
