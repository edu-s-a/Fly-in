#!/usr/bin/env bash
# Usage: bash bench.sh "<command that runs fly_in.py>"
read -ra RUN <<< "${1:-python3 fly_in.py}"

DIRS=(maps maps/own maps/easy maps/medium maps/hard maps/challenger)

target_for() {
    case "$1" in
        *01_linear_path*) echo 6 ;;
        *02_simple_fork*) echo 8 ;;
        *03_basic_capacity*) echo 6 ;;
        *01_dead_end_trap*) echo 12 ;;
        *02_circular_loop*) echo 15 ;;
        *03_priority_puzzle*) echo 12 ;;
        *01_maze_nightmare*) echo 30 ;;
        *02_capacity_hell*) echo 35 ;;
        *03_ultimate_challenge*) echo 45 ;;
        *01_the_impossible_dream*) echo 45 ;;
        *) echo "-" ;;
    esac
}

printf "%-44s %-9s %-7s %-6s %s\n" MAP TURNS TARGET STATUS TIME
for dir in "${DIRS[@]}"; do
    for map in "$dir"/*.txt; do
        [ -e "$map" ] || continue
        target=$(target_for "$map")
        start=$(date +%s.%N)
        out=$("${RUN[@]}" --stats "$map" 2>&1 >/dev/null | head -n 1)
        end=$(date +%s.%N)
        turns=${out#turns: }
        status="-"
        if [ "$target" != "-" ]; then
            if [[ "$turns" =~ ^[0-9]+$ ]] && [ "$turns" -le "$target" ]; then
                status="ok"
            else
                status="OVER"
            fi
        fi
        secs=$(awk -v a="$start" -v b="$end" 'BEGIN { printf "%.2f", b - a }')
        printf "%-44s %-9s %-7s %-6s %ss\n" \
            "$map" "$turns" "$target" "$status" "$secs"
    done
done