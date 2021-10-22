
case-study:
	sed -i "s/LITMUS 0/LITMUS 1/g" extra.h
	$(MAKE) -C baseline all
	$(MAKE) -C dis baseline
	$(MAKE) -C SD-VBS/benchmarks compile

benchmarks:
	sed -i "s/LITMUS 1/LITMUS 0/g" extra.h
	#$(MAKE) -C baseline all
	#$(MAKE) -C all_pairs all
	#$(MAKE) -C dis pairs
	$(MAKE) -C SD-VBS/benchmarks CFLAGS=-DPAIRED compile


benches := svm mser sift texture_synthesis tracking disparity localization multi_ncut stitch
bench_path := SD-VBS/benchmarks
dag_path := SD-VBS/dag_binaries
single_suffix := _qcif_single
pair_suffix := _qcif_pair
dag-case-study:
	sudo sed -i "s/LITMUS 0/LITMUS 1/g" extra.h
	sudo mkdir -p SD-VBS/dag_binaries
	$(MAKE) -C SD-VBS/benchmarks compile
	@for v in $(benches) ; do \
		# echo "$(dag_path)/$$v""$(single_suffix)"; \
        sudo cp $(bench_path)/$$v/data/qcif/$$v "$(dag_path)/$$v""$(single_suffix)"; \
    done
	$(MAKE) -C SD-VBS/benchmarks CFLAGS=-DPAIRED compile
	@for v in $(benches) ; do \
		# echo "$(dag_path)/$$v""$(pair_suffix)"; \
        sudo cp $(bench_path)/$$v/data/qcif/$$v "$(dag_path)/$$v""$(pair_suffix)"; \
    done
