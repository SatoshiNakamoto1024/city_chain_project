管理者がイベント条件を入力するシンプルな HTML＋JavaScript。
① いつ（開始／終了日時）、② どこで（市町村 or ポリゴン座標）、③ 何を（action）、④ どのように（multiplier）、⑤ 説明、を入力して API へ POST します。

以上で以下が実現できます。
管理者が http://<host>:<port>/event_form にアクセス
市町村／ポリゴンイベントを直感的にフォーム入力
/events/* API → JSON ファイルに追記
check_*_event は起動中のメモリにも反映
最後に get_place_info_and_bonus を呼ぶと、動的追加イベントが即時有効
既存のコードはほぼそのまま残し、必要な機能だけを足し込みました。これで本番運用に耐える実装になります。


(.venv312) D:\city_chain_project\Algorithm\PoP\pop_python>cd ..

(.venv312) D:\city_chain_project\Algorithm\PoP>uvicorn pop_python.app_pop:app --reload
[32mINFO[0m:     Will watch for changes in these directories: ['D:\\city_chain_project\\Algorithm\\PoP']
[32mINFO[0m:     Uvicorn running on [1mhttp://127.0.0.1:8000[0m (Press CTRL+C to quit)
[32mINFO[0m:     Started reloader process [[36m[1m6296[0m] using [36m[1mWatchFiles[0m
[32mINFO[0m:     Started server process [[36m19908[0m]
[32mINFO[0m:     Waiting for application startup.
[32mINFO[0m:     Application startup complete.

このあと、ブラウザでフォームを開く
http://localhost:8000/static/pop_event.html

フォームから JSON を入力・「登録」→ /events/... が更新され、即座に pop_python.events の定義にも反映されます。

これで、UI → FastAPI → JSON 保存 → Python API → PoP 本体 の一連のフローが動くはずです。

