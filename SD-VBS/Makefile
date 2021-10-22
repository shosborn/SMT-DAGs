include common/makefiles/Makefile.include
include common/makefiles/Makefile.recurse

table:
	@echo Generate Table for cycles
	@find cycles/*/ -iname "C_*.txt" -exec python common/support/buildTable.py {} \; | tee cycles.txt
	@find cycles/*/ -iname "Matlab_*.txt" -exec python common/support/buildTable.py {} \; | tee MCycles.txt
	@cat MCycles.txt >> cycles.txt
	@rm MCycles.txt
	@mv cycles.txt cycles/.

timetable:
	@echo Generate Timetable
	@find times/*/ -iname "T_*.txt" -exec python common/support/buildTimeTable.py {} \; | tee times.txt
	@mv times.txt times/.

preload-timetable:
	@echo Generate Timetable
	@find preload-times/*/ -iname "T_*.txt" -exec python common/support/buildTimeTable.py {} \; | tee times.txt
	@mv times.txt preload-times/.
