from pathlib import Path

from deploy import create_cmd, function_name

V = {"name": "eager-512", "app": "eager", "runtime": "python3.14", "arch": "arm64", "memory": 512,
     "deps": True, "pyc": "right", "snapstart": False, "env": {}}
ROLE = "arn:aws:iam::1:role/r"


def test_function_name_prefix():
    assert function_name(V) == "lazytown-v3-eager-512"


def test_small_zip_direct_upload():
    cmd = create_cmd(V, Path("a.zip"), ROLE, zip_bytes=10_000_000)
    assert "fileb://a.zip" in " ".join(cmd) and not any("S3Bucket=" in c for c in cmd)


def test_large_zip_uses_s3():
    cmd = create_cmd(V, Path("a.zip"), ROLE, zip_bytes=51 * 1024 * 1024, bucket="b")
    assert any(c.startswith("S3Bucket=b") for c in cmd)


def test_timeout_and_tag():
    cmd = create_cmd(V, Path("a.zip"), ROLE, zip_bytes=1)
    assert cmd[cmd.index("--timeout") + 1] == "60"
    assert cmd[cmd.index("--tags") + 1] == "project=lazytown-v3"


def test_go_uses_bootstrap_handler():
    g = {**V, "name": "final-go", "app": "go", "runtime": "provided.al2023"}
    cmd = create_cmd(g, Path("a.zip"), ROLE, zip_bytes=1)
    assert cmd[cmd.index("--handler") + 1] == "bootstrap"


def test_snapstart_flag():
    cmd = create_cmd({**V, "snapstart": True}, Path("a.zip"), ROLE, zip_bytes=1)
    assert cmd[cmd.index("--snap-start") + 1] == "ApplyOn=PublishedVersions"


def test_env_vars_passed():
    cmd = create_cmd({**V, "env": {"PYTHONPROFILEIMPORTTIME": "1"}}, Path("a.zip"), ROLE, zip_bytes=1)
    assert "PYTHONPROFILEIMPORTTIME=1" in cmd[cmd.index("--environment") + 1]
