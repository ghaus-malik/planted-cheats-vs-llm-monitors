"""Build the planted-cheat set (CPU only). Each cheat is confirmed by execution:
the patched code passes the visible asserts under an exit-code grader, and the unpatched base fails them."""
import sys, os, random, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from harness.common import *
from harness.cheats import *
from concurrent.futures import ThreadPoolExecutor

N_PROBLEMS = 50
gen = load_json(os.path.join(DATA, "generations_n16.json"))
ex = load_json(os.path.join(DATA, "exec_n16.json"))
probs = {p["pid"]: p for p in load_problems()}


def gold(r):
    return bool(r["bits"]) and min(r["bits"]) == 1


cands = []
for pid, samples in gen.items():
    p = probs[pid]
    if p["src"] != "mbpp":
        continue
    vis = parse_visible(p)
    if vis is None:
        continue
    base = correct = None
    for s in samples:
        r = ex.get(pid + "::" + h(s["code"]))
        if r is None:
            continue
        try:
            ok_def = find_def(s["code"], p["entry"]) is not None
        except SyntaxError:
            ok_def = False
        if not ok_def:
            continue
        if base is None and not gold(r) and r["vis"] and min(r["vis"]) == 0 and r["status"] == "ok":
            base = s["code"]
        if correct is None and gold(r):
            correct = s["code"]
    if base is None:
        continue
    if correct is None:
        correct, csrc = p["reference"], "reference"
    else:
        csrc = "policy"
    cands.append((pid, vis, base, correct, csrc))
print("problems with a usable failing base:", len(cands))
random.Random(0).shuffle(cands)
cands = cands[:N_PROBLEMS]

items = []
for pid, vis, base, correct, csrc in cands:
    p = probs[pid]
    for level in LEVELS:
        items.append(dict(pid=pid, kind="honest_wrong", ctype=None, level=level, code=base,
                          message=MESSAGES[("honest", level)]))
        items.append(dict(pid=pid, kind="honest_correct", ctype=None, level=level, code=correct,
                          message=MESSAGES[("honest", level)], correct_src=csrc))
        for ct in CHEAT_TYPES:
            code = make_cheat(base, p, vis, ct, level)
            if code is None:
                continue
            msg = MESSAGES[("cheat", level)]
            msg = msg[ct] if isinstance(msg, dict) else msg
            items.append(dict(pid=pid, kind="cheat", ctype=ct, level=level, code=code, message=msg))

with ThreadPoolExecutor(10) as pool:
    naive = list(pool.map(lambda it: naive_grade(it["code"], probs[it["pid"]]), items))
for it, ok in zip(items, naive):
    it["naive_pass"] = bool(ok)
# gold check for cheats (hidden tests) to confirm they are real failures
cheat_idx = [i for i, it in enumerate(items) if it["kind"] == "cheat"]
gold_res = run_many([(items[i]["code"], probs[items[i]["pid"]]) for i in cheat_idx])
for i, r in zip(cheat_idx, gold_res):
    items[i]["hidden_pass"] = bool(gold(r))
valid = []
for it in items:
    if it["kind"] == "cheat":
        # the base fails the visible asserts by construction, so passing them is the hack working.
        # hidden_pass is kept as a finding: an always-equal object can also fool the EvalPlus checker.
        it["valid"] = it["naive_pass"]
    elif it["kind"] == "honest_wrong":
        it["valid"] = not it["naive_pass"]
    else:
        it["valid"] = True
summary = {}
for it in items:
    key = f"{it['kind']}|{it['ctype']}|{it['level']}"
    summary.setdefault(key, [0, 0])
    summary[key][0] += it["valid"]; summary[key][1] += 1
for k, v in sorted(summary.items()):
    print(f"{k:40s} valid {v[0]}/{v[1]}")
hp = {}
for it in items:
    if it["kind"] == "cheat" and it["naive_pass"]:
        hp.setdefault(it["ctype"], [0, 0]); hp[it["ctype"]][0] += it["hidden_pass"]; hp[it["ctype"]][1] += 1
print("cheats that ALSO pass the full hidden EvalPlus suite:", {k: f"{a}/{b}" for k, (a, b) in hp.items()})
save_json(items, os.path.join(DATA, "items.json"))
print("saved", len(items), "items")
