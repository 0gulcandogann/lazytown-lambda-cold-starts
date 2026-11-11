from run_all import build_groups

GROUPS = build_groups()


def test_final_race_groups_first():
    t9 = {"final-baseline", "final-free", "final-opt", "final-snap", "final-go", "pep810-315"}
    first = {g["function"].removeprefix("lazytown-v3-") for g in GROUPS[:len(t9)]}
    assert first == t9


def test_one_group_per_function():
    fns = [g["function"] for g in GROUPS]
    assert len(fns) == len(set(fns))


def test_eager_512_runs_both_payloads_in_one_group():
    g = next(g for g in GROUPS if g["function"] == "lazytown-v3-eager-512")
    assert [j["label"] for j in g["jobs"]] == ["eager-512-simple", "eager-512-report"]


def test_snapstart_only_for_final_snap():
    snaps = {g["function"] for g in GROUPS for j in g["jobs"] if j["snapstart"]}
    assert snaps == {"lazytown-v3-final-snap"}


def test_old_rerun_included_last():
    assert GROUPS[-1]["function"].startswith("lazytown-") and not GROUPS[-1]["function"].startswith("lazytown-v3-")
    old = [j["label"] for g in GROUPS for j in g["jobs"] if j["label"].startswith("old-")]
    assert len(old) == 19 and "old-slide07-lazy-report" in old


def test_unique_outputs():
    outs = [j["output"] for g in GROUPS for j in g["jobs"]]
    assert len(outs) == len(set(outs))
