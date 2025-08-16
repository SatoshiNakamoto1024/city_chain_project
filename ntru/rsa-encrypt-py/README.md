# モジュール化して他のファイルから呼び出す方法
In D:\city_chain_project\ntru\rsa-encrypt-py\, create a setup.py:

# D:\city_chain_project\ntru\rsa-encrypt-py\setup.py
from setuptools import setup

setup(
    name="rsa_encrypt",
    version="0.1.0",
    py_modules=["rsa_encrypt"],
    install_requires=["cryptography"],
    description="Pure-Python RSA encryption helpers",
)
Make sure that the one file in that folder is rsa_encrypt.py (the code you pasted).


(.venv312) D:\city_chain_project\ntru\rsa-encrypt-py>pip install -e .
Obtaining file:///D:/city_chain_project/ntru/rsa-encrypt-py
  Installing build dependencies ... done
  Checking if build backend supports build_editable ... done
  Getting requirements to build editable ... done
  Preparing editable metadata (pyproject.toml) ... done
Requirement already satisfied: cryptography in d:\city_chain_project\.venv312\lib\site-packages (from rsa_encrypt==0.1.0) (44.0.2)
Requirement already satisfied: cffi>=1.12 in d:\city_chain_project\.venv312\lib\site-packages (from cryptography->rsa_encrypt==0.1.0) (1.17.1)
Requirement already satisfied: pycparser in d:\city_chain_project\.venv312\lib\site-packages (from cffi>=1.12->cryptography->rsa_encrypt==0.1.0) (2.22)
Building wheels for collected packages: rsa_encrypt
  Building editable for rsa_encrypt (pyproject.toml) ... done
  Created wheel for rsa_encrypt: filename=rsa_encrypt-0.1.0-0.editable-py3-none-any.whl size=2768 sha256=42a4b96b7a171e01b9a2f52ae128c7dbd22f4d36704625f8076f7f877c82a9e6
  Stored in directory: C:\Users\kibiy\AppData\Local\Temp\pip-ephem-wheel-cache-r9i4cw32\wheels\59\83\85\75f089ada8466165a6142d767cef78f40c2cf1a14ee5686a4a
Successfully built rsa_encrypt
Installing collected packages: rsa_encrypt
Successfully installed rsa_encrypt-0.1.0

(.venv312) D:\city_chain_project\ntru\rsa-encrypt-py>