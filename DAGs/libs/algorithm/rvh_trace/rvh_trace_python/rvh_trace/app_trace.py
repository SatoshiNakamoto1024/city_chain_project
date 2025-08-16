# D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python\rvh_trace\app_trace.py
"""
CLI entry point:

    python -m rvh_trace.app_trace --level info --name demo
"""

from __future__ import annotations

import argparse
import random
import time

from rvh_trace import init_tracing, span


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--level", default="info")
    p.add_argument("--name", default="cli_demo")
    args = p.parse_args()

    init_tracing(args.level)

    with span(args.name, cli=True):
        for i in range(3):
            with span("inner", i=i):
                time.sleep(random.random() / 10)
                print(f"step {i}")


if __name__ == "__main__":
    main()
