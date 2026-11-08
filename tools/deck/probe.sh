#!/bin/bash
# Copy to user/debug.env (with the lines from docs/HANDOFF.md) for a debug run; PIN=1 pins VUThread.
# Started from user/debug.env next to a game run: every 5 s logs how busy each game thread was (% of one CPU) and the
# average CPU clock, to logs/threads-<stamp>.txt. PIN=1 also gives VUThread a physical core of its own (its SMT sibling
# left idle; every other thread kept off that core).
here=$1; stamp=$2; out=$here/logs/threads-$stamp.txt
hz=$(getconf CLK_TCK)
pid=
for i in $(seq 1 120); do pid=$(pgrep -n -x jackass) && break; sleep 0.5; done
[ -n "$pid" ] || { echo "probe: no jackass process" > "$out"; exit 0; }
echo "probe: pid $pid, PIN=${PIN:-0}, cpus $(nproc), cpu0 siblings $(cat /sys/devices/system/cpu/cpu0/topology/thread_siblings_list)" > "$out"
ncpu=$(nproc)
vucpu=0
sib=$(cat /sys/devices/system/cpu/cpu$vucpu/topology/thread_siblings_list)
others=$(for c in $(seq 0 $((ncpu-1))); do case ",$(echo $sib | tr '-' ',')," in *",$c,"*) ;; *) printf '%s,' $c ;; esac; done | sed 's/,$//')
declare -A prev
last=$(date +%s.%N)
while kill -0 "$pid" 2>/dev/null; do
  if [ "${PIN:-0}" = 1 ]; then
    for t in /proc/$pid/task/*; do
      tid=${t##*/}; name=$(cat $t/comm 2>/dev/null) || continue
      if [ "$name" = VUThread ]; then taskset -pc $vucpu $tid > /dev/null 2>&1; else taskset -pc $others $tid > /dev/null 2>&1; fi
    done
  fi
  sleep 5
  now=$(date +%s.%N); dt=$(awk -v a=$now -v b=$last 'BEGIN{print a-b}'); last=$now
  line="$(date +%T)"
  declare -A agg=()
  for t in /proc/$pid/task/*; do
    tid=${t##*/}
    read -r -a f < $t/stat 2>/dev/null || continue
    name=$(cat $t/comm 2>/dev/null)
    ticks=$(( f[13] + f[14] ))
    if [ -n "${prev[$tid]}" ]; then agg[$name]=$(( ${agg[$name]:-0} + ticks - prev[$tid] )); fi
    prev[$tid]=$ticks
  done
  for n in "${!agg[@]}"; do
    pct=$(awk -v t=${agg[$n]} -v h=$hz -v d=$dt 'BEGIN{printf "%d", t*100/(h*d)}')
    [ "$pct" -ge 3 ] && line="$line $n=$pct%"
  done
  mhz=$(awk '/MHz/{s+=$4; n++} END{if(n) printf "%d", s/n}' /proc/cpuinfo)
  echo "$line cpuMHz=$mhz" >> "$out"
done
echo "probe: game exited" >> "$out"
