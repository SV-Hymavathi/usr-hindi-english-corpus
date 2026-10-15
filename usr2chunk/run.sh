#!/bin/bash
# usr2chunk - USR -> English chunks
#
#   ./run.sh <usr_file>                        generate -> out/<name>.chunks.txt (+ USR structure check)
#   ./run.sh <usr_file> <gold.tsv> <ids.txt>   generate and score against a gold file for the listed ids
#   ./run.sh test                              morphology + regression tests
#   ./run.sh eval                              score all bundled data (tourism dev / held-out / new 549, health, geography)
set -e
cd "$(dirname "$0")"
mkdir -p out

if [ "$1" = "test" ]; then
    python3 tests/test_morph.py
    python3 generate.py examples/tourism_all_561.txt > out/tourism_all_561.chunks.txt
    python3 tests/test_regression.py out/tourism_all_561.chunks.txt
    exit 0
fi

if [ "$1" = "eval" ]; then
    python3 generate.py examples/tourism_all_561.txt > out/tourism_all_561.chunks.txt
    echo "dev      (post-edited gold):"; python3 score.py out/tourism_all_561.chunks.txt eval/gold_tourism_dev.tsv eval/split_dev.txt
    echo "held-out (post-edited gold):"; python3 score.py out/tourism_all_561.chunks.txt eval/gold_tourism_heldout.tsv eval/split_test.txt
    python3 generate.py examples/tourism_new_549.txt > out/tourism_new_549.chunks.txt
    echo "tourism new 549:            "; python3 score.py out/tourism_new_549.chunks.txt eval/gold_new549.tsv eval/ids_new549.txt
    python3 generate.py examples/health_402.txt > out/health_402.chunks.txt
    echo "health 402:                 "; python3 score.py out/health_402.chunks.txt eval/gold_health.tsv eval/ids_health.txt
    python3 generate.py examples/geography_558.txt > out/geography_558.chunks.txt
    echo "geography 558:              "; python3 score.py out/geography_558.chunks.txt eval/gold_geography.tsv eval/ids_geography.txt
    exit 0
fi

if [ -z "$1" ]; then
    echo "usage: ./run.sh <usr_file> [gold.tsv ids.txt] | test | eval"; exit 1
fi

USR="$1"
NAME=$(basename "$USR"); NAME="${NAME%.*}"
python3 generate.py "$USR" > "out/$NAME.chunks.txt"
echo "generated $(grep -c ': ' "out/$NAME.chunks.txt") sentences -> out/$NAME.chunks.txt (errors: $(grep -c 'ERROR' "out/$NAME.chunks.txt" || true))"
python3 validate_usr.py "$USR" "out/$NAME.usr_issues.csv" | head -1
if [ -n "$2" ] && [ -n "$3" ]; then
    python3 score.py "out/$NAME.chunks.txt" "$2" "$3"
fi
