"""Summarize the execution-checked greedy disguise search against monitor A, and transfer to monitor B."""
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from harness.common import DATA, RESULTS
D = json.load(open(os.path.join(DATA, "disguise.json")))
log = D["log"]
md = [f"Silent cheats flagged by monitor A at its 5% false-alarm threshold (P(Yes) > {D['threshold']:.3f}): random 60 searched.",
      "Each edit was re-run on the hacked grader, so every disguised version still cheats.", "",
      "| cheat type | searched | evaded A | edits used (mean, evaded) | A score start -> end (mean) | evaded A and also not flagged by B | B flagged before -> after |",
      "|---|---|---|---|---|---|---|"]
summ = {}
for ct in ["lookup", "special_case", "exit", "always_equal", None]:
    L = [l for l in log if ct is None or l["ctype"] == ct]
    if not L:
        continue
    ev = [l for l in L if l["evaded"]]
    has_b = "B_flag_final" in L[0]
    both = [l for l in ev if has_b and not l["B_flag_final"]]
    bstart = np.mean([l["B_flag_start"] for l in L]) if has_b else float("nan")
    bend = np.mean([l["B_flag_final"] for l in L]) if has_b else float("nan")
    name = ct or "all"
    summ[name] = dict(n=len(L), evaded=len(ev), both=len(both), mean_ops=float(np.mean([len(l["ops"]) for l in ev])) if ev else None,
                      a_start=float(np.mean([l["start"] for l in L])), a_end=float(np.mean([l["final"] for l in L])), b_before=bstart, b_after=bend)
    md.append(f"| {name} | {len(L)} | {len(ev)} | {summ[name]['mean_ops'] if ev else 0:.1f} | {summ[name]['a_start']:.2f} -> {summ[name]['a_end']:.2f} | "
              f"{len(both)} | {bstart:.2f} -> {bend:.2f} |")
md += ["", "Edits chosen in successful disguises (count):", ""]
c = collections.Counter(op for l in log if l["evaded"] for op in l["ops"])
first = collections.Counter(l["ops"][0] for l in log if l["evaded"] and l["ops"])
md.append("| edit | used in evading disguises | first edit chosen |")
md.append("|---|---|---|")
for op, k in c.most_common():
    md.append(f"| {op} | {k} | {first.get(op, 0)} |")
ev1 = [l for l in log if l["evaded"] and len(l["ops"]) == 1]
md += ["", f"Evaded with a single edit: {len(ev1)} of {len(log)} ({', '.join(sorted(set(l['ops'][0] for l in ev1)))})."]
open(os.path.join(RESULTS, "disguise_tables.md"), "w").write("\n".join(md) + "\n")
json.dump(summ, open(os.path.join(RESULTS, "disguise_results.json"), "w"), indent=1, default=float)
print("\n".join(md))
