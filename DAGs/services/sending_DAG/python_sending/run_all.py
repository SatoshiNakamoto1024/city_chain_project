# D:\city_chain_project\network\DAGs\python\run_all.py

"""
run_all.py

プロジェクト全体を一括で起動する簡易スクリプト。
City/Main, Continent/Main, Global/Main のFlaskサーバを
それぞれサブプロセス/スレッドで起動してみる例。

実際には docker-compose や supervisor などの仕組みを
使ったほうが本番向き。
"""

import subprocess
import time
import sys

def main():
    try:
        # city_main
        city_proc = subprocess.Popen([sys.executable, "city_level/city_main.py"])
        print("[RUN_ALL] city_main.py 起動...")

        # continent_main
        continent_proc = subprocess.Popen([sys.executable, "continent_level/continent_main.py"])
        print("[RUN_ALL] continent_main.py 起動...")

        # global_main
        global_proc = subprocess.Popen([sys.executable, "global_level/global_main.py"])
        print("[RUN_ALL] global_main.py 起動...")

        print("[RUN_ALL] すべてのFlaskサーバを起動しました。Ctrl+Cで停止できます。")

        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("[RUN_ALL] 停止中...")
        city_proc.terminate()
        continent_proc.terminate()
        global_proc.terminate()

if __name__ == "__main__":
    main()
