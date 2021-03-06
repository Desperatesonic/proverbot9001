#!/usr/bin/env bash

set -e

# determine physical directory of this script
src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
  dir="$(cd -P "$(dirname "$src")" && pwd)"
  src="$(readlink "$src")"
  [[ $src != /* ]] && src="$dir/$src"
done
MYDIR="$(cd -P "$(dirname "$src")" && pwd)"

PARAMS=""
OUTDIR=$MYDIR/search-report
: "${NUM_THREADS:=5}"

while (( "$#" )); do
    case "$1" in
        -o|--output)
            OUTDIR=$2
            shift 2
            ;;
        --output=*) # Not sure this is working yet
            OUTDIR="${i#*=}"
            shift
            ;;
        -j|--num-threads)
            NUM_THREADS=$2
            shift 2
            ;;
        *) # preserve all other arguments
            PARAMS="$PARAMS $1"
            shift
            ;;
    esac
done

: "${JOBS_FILE:=$MYDIR/data/compcert-test-files.txt}"
grep -v -f <($MYDIR/bench/completed-files.sh $OUTDIR) $JOBS_FILE > jobs_todo.txt

mkdir -p logs
parallel -j $NUM_THREADS -a jobs_todo.txt --fg \
         --tmux tmux joinp -t :0 \; \
         "tmux select-layout -t :0 even-vertical ; ulimit -s unlimited ;
          python3 $MYDIR/src/search_file.py -o $OUTDIR $PARAMS {} 2> logs/{/.}.txt --proof-times=logs/{/.}-times.txt"
cat $JOBS_FILE | xargs python3.7 $MYDIR/src/search_report.py -o $OUTDIR $PARAMS
