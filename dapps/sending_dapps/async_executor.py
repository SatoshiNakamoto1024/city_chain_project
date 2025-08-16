# sending_dapps/async_executor.py
"""
非同期実行ユーティリティ。将来的に複数の非同期タスクをまとめて実行したい場合に使います。
（現状はあまり使っていませんが、拡張用に置いておきます。）
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=10)
_loop = asyncio.get_event_loop()

def run_in_thread(func, *args, **kwargs):
    """
    ブロッキングな処理を別スレッドで実行したいときに呼び出します。
    例:
       result = run_in_thread(blocking_function, arg1, arg2)
    """
    return _loop.run_in_executor(_executor, lambda: func(*args, **kwargs))

async def run_concurrent(tasks):
    """
    asyncio.gather 相当ですが、例外をまとめて返したい場合に使います。
    tasks: awaitable のリスト
    """
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
