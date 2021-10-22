#!/bin/bash
# Redirect all interrupts to core 0
# i=0
for IRQ in /proc/irq/*
do
    # Skip default_smp_affinity
    if [ -d $IRQ ]; then
        irqList[$i]=$(cat $IRQ/smp_affinity_list)
        echo 0 2> /dev/null > $IRQ/smp_affinity_list
        echo $IRQ:  $(cat $IRQ/smp_affinity_list)
    fi
    i=$(( $i + 1 ))
done