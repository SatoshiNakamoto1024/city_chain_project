# D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\rvh_stable\tests\test_cli.py
import sys
from io import StringIO
import pytest

from rvh_stable.app_stable import main

def run_cli(args):
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["app_stable"] + args
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    exit_code = 0
    try:
        main()
    except SystemExit as e:
        exit_code = e.code
    finally:
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    return exit_code, out, err

def test_cli_sync_basic():
    code, out, err = run_cli(["--key", "123", "--buckets", "5"])
    assert code == 0
    assert err == ""
    assert out.strip().isdigit()
    n = int(out.strip())
    assert 0 <= n < 5

def test_cli_async_basic():
    code, out, err = run_cli(["--key", "98765", "--buckets", "7", "--async"])
    assert code == 0
    assert err == ""
    assert out.strip().isdigit()
    n = int(out.strip())
    assert 0 <= n < 7

def test_invalid_buckets():
    code, out, err = run_cli(["--key", "foo", "--buckets", "0"])
    assert code == 1
    assert "[ERROR]" in err
