from setuptools import setup, find_packages

setup(
    name="immudb-py",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # 必要な依存パッケージを記述（例: requestsなど）
        "requests",
    ],
    author="Codenotary",
    author_email="contact@codenotary.com",
    description="ImmuDB Python client library",
    url="https://github.com/codenotary/immudb",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
