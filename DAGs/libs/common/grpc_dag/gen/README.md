(.venv312) D:\city_chain_project>python -m grpc_tools.protoc -I network/DAGs/common/grpc_dag/proto --python_out=network/DAGs/common/grpc_dag/gen --grpc_python_out=network/DAGs/common/grpc_dag/gen network/DAGs/common/grpc_dag/proto/dag.proto
D:\city_chain_project\.venv312\Lib\site-packages\grpc_tools\protoc.py:21: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  import pkg_resources

という表記になり、生成される。
