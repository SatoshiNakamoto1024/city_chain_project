# テスト前にMongoDBを起動する必要がある
【方法①】Windows上でMongoDBをサービスとして起動する場合
管理者としてコマンドプロンプトを開く

以下を実行：
net start MongoDB

(.venv312) D:\city_chain_project\network\DAGs\common\db\tests>net start MongoDB
MongoDB Server (MongoDB) サービスを開始します...
MongoDB Server (MongoDB) サービスは正常に開始されました。


(.venv312) D:\city_chain_project\network\DAGs\common\db\tests>
(.venv312) D:\city_chain_project\network\DAGs\common\db\tests>pytest -v test_db_async.py
D:\city_chain_project\.venv312\Lib\site-packages\pytest_asyncio\plugin.py:208: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.3.5, pluggy-1.5.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 1 item

test_db_async.py::test_async_insert_and_find PASSED                                                              [100%]

================================================== 1 passed in 0.91s ==================================================
