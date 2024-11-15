#include "FFT2.h"

#include "measureTime3.h"

#include <omp.h>

channel_t CombineDFTBuf_1[2];
channel_t CombineDFTBuf_2[2];
channel_t CombineDFTBuf_4[2];
channel_t CombineDFTBuf_8[2];
channel_t CombineDFTBuf_16[2];
channel_t CombineDFTBuf_32[2];
channel_t FFTReorderBuf_1[2];
channel_t FFTReorderBuf_2[2];
channel_t FFTReorderBuf_4[2];
channel_t FFTReorderBuf_8[2];
channel_t FFTReorderBuf_16[2];
channel_t SourceBuf;
channel_t FloatPrinterBuf;
channel_t SplitJoinBuf[2];

void fft2_reorder_simple_1(int branch) {
    fft2_reorder_simple(64, &FFTReorderBuf_1[branch].buffer_in, &FFTReorderBuf_2[branch].buffer_in);
}
void fft2_reorder_simple_2(int branch) {
    fft2_reorder_simple(32, &FFTReorderBuf_2[branch].buffer_in, &FFTReorderBuf_4[branch].buffer_in);
    fft2_reorder_simple(32, &FFTReorderBuf_2[branch].buffer_in, &FFTReorderBuf_4[branch].buffer_in);
}
void fft2_reorder_simple_4(int branch) {
    FOR(uint32_t, i, 0, <, 4 , i++)
        fft2_reorder_simple(16, &FFTReorderBuf_4[branch].buffer_in, &FFTReorderBuf_8[branch].buffer_in);
    ENDFOR
}
void fft2_reorder_simple_8(int branch) {
    FOR(uint32_t, i, 0, <, 8 , i++)
        fft2_reorder_simple(8, &FFTReorderBuf_8[branch].buffer_in, &FFTReorderBuf_16[branch].buffer_in);
    ENDFOR
}
void fft2_reorder_simple_16(int branch) {
    FOR(uint32_t, i, 0, <, 16 , i++)
        fft2_reorder_simple(4, &FFTReorderBuf_16[branch].buffer_in, &CombineDFTBuf_32[branch].buffer_in);
    ENDFOR
}

void fft2_reorder_simple(int iter, buffer_float_t *in, buffer_float_t *out) {
    FOR2(uint32_t, i, 0, <, 2*iter, 2*TheGlobal_N, i+=4)
        push_float(out, peek_float(in, i));
        push_float(out, peek_float(in, i+1));
    ENDFOR

    FOR2(uint32_t, i, 2, <, 2*iter, 2*TheGlobal_N , i+=4)
        push_float(out, peek_float(in, i));
        push_float(out, peek_float(in, i+1));
    ENDFOR

    FOR2(uint32_t, i, 0, <, iter, TheGlobal_N , i++)
        pop_float(in);
        pop_float(in);
    ENDFOR
}

void fft2_combine_dft_32(int branch) {// FFT6.str:169
    FOR(uint32_t, i, 0, <, 32 , i++)
        fft2_combine_dft(2, &CombineDFTBuf_32[branch].buffer_in, &CombineDFTBuf_16[branch].buffer_in);
    ENDFOR
}
void fft2_combine_dft_16(int branch) {// FFT6.str:169
    FOR(uint32_t, i, 0, <, 16 , i++)
        fft2_combine_dft(4, &CombineDFTBuf_16[branch].buffer_in, &CombineDFTBuf_8[branch].buffer_in);
    ENDFOR
}
void fft2_combine_dft_8(int branch) {// FFT6.str:169
    FOR(uint32_t, i, 0, <, 8 , i++)
        fft2_combine_dft(8, &CombineDFTBuf_8[branch].buffer_in, &CombineDFTBuf_4[branch].buffer_in);
    ENDFOR
}
void fft2_combine_dft_4(int branch) {// FFT6.str:169
    FOR(uint32_t, i, 0, <, 4 , i++)
        fft2_combine_dft(16, &CombineDFTBuf_4[branch].buffer_in, &CombineDFTBuf_2[branch].buffer_in);
    ENDFOR
}
void fft2_combine_dft_2(int branch) {// FFT6.str:169
    fft2_combine_dft(32, &CombineDFTBuf_2[branch].buffer_in, &CombineDFTBuf_1[branch].buffer_in);
    fft2_combine_dft(32, &CombineDFTBuf_2[branch].buffer_in, &CombineDFTBuf_1[branch].buffer_in);
}

void fft2_combine_dft_1(int branch) {// FFT6.str:169
    fft2_combine_dft(64, &CombineDFTBuf_1[branch].buffer_in, &SplitJoinBuf[branch].buffer_out);
}

void fft2_combine_dft(int iter, buffer_float_t *in, buffer_float_t *out) {
    // coefficients, real and imaginary interleaved
    float w[TheGlobal_N];
    float wn_r = (float)cos(2 * 3.141592654 / iter);
    float wn_i = (float)sin(-2 * 3.141592654 / iter);
    float real = 1;
    float imag = 0;
    float next_real, next_imag;
    FOR2(uint32_t, i, 0, <, iter, TheGlobal_N, i+=2)
        w[i] = real;
        w[i+1] = imag;
        next_real = real * wn_r - imag * wn_i;
        next_imag = real * wn_i + imag * wn_r;
        real = next_real;
        imag = next_imag;
    ENDFOR
    
    float results[2*TheGlobal_N];

    FOR2(uint32_t, i, 0, <, iter, TheGlobal_N, i += 2)
        // this is a temporary work-around since there seems to be
        // a bug in field prop that does not propagate nWay into the
        // array references.  --BFT 9/10/02

        //int tempN = nWay;
        //Fixed --jasperln

        // removed nWay, just using n  --sitij 9/26/03

        int i_plus_1 = i+1;

        float y0_r = peek_float(in, i);
        float y0_i = peek_float(in, i_plus_1);

        float y1_r = peek_float(in, iter + i);
        float y1_i = peek_float(in, iter + i_plus_1);

        // load into temps to make sure it doesn't got loaded
        // separately for each load
        float weight_real = w[i];
        float weight_imag = w[i_plus_1];

        float y1w_r = y1_r * weight_real - y1_i * weight_imag;
        float y1w_i = y1_r * weight_imag + y1_i * weight_real;

        results[i] = y0_r + y1w_r;
        results[i + 1] = y0_i + y1w_i;

        results[iter + i] = y0_r - y1w_r;
        results[iter + i + 1] = y0_i - y1w_i;
    ENDFOR

    FOR2(uint32_t, i, 0, <, 2 * iter, 2*TheGlobal_N, i++)
        pop_float(in);
        push_float(out, results[i]);
    ENDFOR
}

void fft2_test_source() { // FFT2.str:157
    push_float(&SourceBuf.buffer_out, 0.0f);
    push_float(&SourceBuf.buffer_out, 0.0);
    push_float(&SourceBuf.buffer_out, 1.0);
    push_float(&SourceBuf.buffer_out, 0.0);

    FOR(uint32_t, i, 0, <, 2*(TheGlobal_N-2), i++)
      push_float(&SourceBuf.buffer_out, 0.0);
    ENDFOR
    
    push_float(&SourceBuf.buffer_out, 0.0);
    push_float(&SourceBuf.buffer_out, 0.0);
    push_float(&SourceBuf.buffer_out, 1.0);
    push_float(&SourceBuf.buffer_out, 0.0);

    FOR(uint32_t, i, 0, <, 2*(TheGlobal_N-2), i++)
      push_float(&SourceBuf.buffer_out, 0.0);
    ENDFOR
}

void fft2_float_printer() {
    FOR(uint32_t, i, 0, <, 4*TheGlobal_N , i++)
        printf("%f\n", pop_float(&FloatPrinterBuf.buffer_in));
    ENDFOR
}

void fft2_split1_round_robin() {
    FOR(uint32_t, i, 0, <, 2*TheGlobal_N , i++)
        push_float(&FFTReorderBuf_1[0].buffer_in, pop_float(&SourceBuf.buffer_out));
    ENDFOR
    FOR(uint32_t, i, 0, <, 2*TheGlobal_N , i++)
        push_float(&FFTReorderBuf_1[1].buffer_in, pop_float(&SourceBuf.buffer_out));
    ENDFOR
}

void fft2_join1_round_robin() {
    FOR(uint32_t, i, 0, <, 2*TheGlobal_N , i++)
        push_float(&FloatPrinterBuf.buffer_in, pop_float(&SplitJoinBuf[0].buffer_out));
    ENDFOR
    FOR(uint32_t, i, 0, <, 2*TheGlobal_N , i++)
        push_float(&FloatPrinterBuf.buffer_in, pop_float(&SplitJoinBuf[1].buffer_out));
    ENDFOR
}

void fft2_init() {
    FOR(uint32_t, i, 0, <, 2 , i++)
        init_buffer_float(&FFTReorderBuf_1[i].buffer_in);
        init_buffer_float(&FFTReorderBuf_2[i].buffer_in);
        init_buffer_float(&FFTReorderBuf_4[i].buffer_in);
        init_buffer_float(&FFTReorderBuf_8[i].buffer_in);
        init_buffer_float(&FFTReorderBuf_16[i].buffer_in);
        init_buffer_float(&CombineDFTBuf_1[i].buffer_in);
        init_buffer_float(&CombineDFTBuf_2[i].buffer_in);
        init_buffer_float(&CombineDFTBuf_4[i].buffer_in);
        init_buffer_float(&CombineDFTBuf_8[i].buffer_in);
        init_buffer_float(&CombineDFTBuf_16[i].buffer_in);
        init_buffer_float(&CombineDFTBuf_32[i].buffer_in);
        init_buffer_float(&SplitJoinBuf[i].buffer_out);
    ENDFOR
    init_buffer_float(&FloatPrinterBuf.buffer_in);
    init_buffer_float(&SourceBuf.buffer_out);
}
int main(int argc, char** argv) {


    SET_UP
    fft2_init();
    

    //FOR(uint32_t, i, 0, <, MAX_ITERATION , i++)
    /*
    Issues to adjust:
    --how to properly increment _rt_jobs_complete?
    --how to properly save results?
    --how to use timer values
    --START_TIMER, STOP_TIMER, and SAVE_SUBTASK_COUNT
    are inside parallel region

    --I think taking care of _rt_jobs_complete will solve everything
    ---Counts how many jobs have been completed
    ---used as an array index to save results
    ---the sum of rt_job_complete (if puiblic) is guaranteed to be correct at the 
    beginning and end of each loop, but what about in between?
    ---in a parallel world, can't uniquely ID jobs by order in which they complete.
    ---array holding timing results needs to be shared.
    */
    omp_set_num_threads(2);
    //export OMP_PROC_BIND = True
    #pragma omp parallel private(_rt_jobs_complete, _rt_start, _rt_end)
    {
        int t_id = omp_get_thread_num();
        _rt_jobs_complete = t_id
        int a, j;
        a=t_id

        FOR(uint32_t, i, 0, <, _rt_loop_count , i++)
            FLUSH_CACHE
            #pragma omp master{
                START_TIMER
                fft2_test_source();
                STOP_TIMER
                _rt_save_job_result(a, _rt_start, _rt_end)
                a=a+2;

                START_TIMER
                fft2_split1_round_robin();
                STOP_TIMER
                _rt_save_job_result(a, _rt_start, _rt_end)
                a=a+2;
            }

        if (t_id!=0){a=6;}

            #pragma omp barrier
            //#pragma omp for schedule (static, 1)
            j=t_id

            START_TIMER
            fft2_reorder_simple_1(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_reorder_simple_2(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_reorder_simple_4(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier                
            START_TIMER
            fft2_reorder_simple_8(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_reorder_simple_16(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_combine_dft_32(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_combine_dft_16(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_combine_dft_8(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier              
            START_TIMER
            fft2_combine_dft_4(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_combine_dft_2(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier
            START_TIMER
            fft2_combine_dft_1(j);
            STOP_TIMER
            _rt_save_job_result(a, _rt_start, _rt_end)
            a=a+4;
            #pragma omp barrier

            #pragma omp master
            {
                START_TIMER
                fft2_join1_round_robin();
                STOP_TIMER
                _rt_save_job_result(a, _rt_start, _rt_end)
                a=a+2;

                START_TIMER
                fft2_float_printer();
                STOP_TIMER
                _rt_save_job_result(a, _rt_start, _rt_end)
                a=a+2;

                //SAVE_SUBTASK_COUNT
            }
            if (t_id!=0){a=a+4}
            #pragma omp barrier
        ENDFOR

        //combine saved timing results here?
        /*
        for t_id in threadCount
            _rt_exec_time
        */

    }   //end parallel region
    WRITE_TO_FILE

    return EXIT_SUCCESS;
} 
