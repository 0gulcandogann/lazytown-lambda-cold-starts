from cleanup import OLD_STACKS, targets

NAMES = ["lazytown-v3-eager-512", "lazytown-slide05-go", "lazytown-final-go", "someone-elses-fn"]


def test_default_targets_only_v3():
    assert targets(NAMES) == ["lazytown-v3-eager-512"]


def test_include_old_adds_v2_but_never_foreign():
    t = targets(NAMES, include_old=True)
    assert "lazytown-slide05-go" in t and "lazytown-final-go" in t and "someone-elses-fn" not in t


def test_old_stack_names():
    assert OLD_STACKS == ["lazytown-slide03", "lazytown-slide05", "lazytown-slide06", "lazytown-slide07",
                          "lazytown-slide08", "lazytown-slide09", "lazytown-slide10"]
