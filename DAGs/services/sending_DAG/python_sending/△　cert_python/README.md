以下は 「クライアント証明書（PEM）を端末に保持し，
Dilithium 署名 / NTRU 暗号（ここでは stub）で本人性を証明するモジュール」 を
PoH／Tx フラグと同じ流儀で

cert_python/ … 端末側・署名生成＆PEMロード

cert_rust/ … 署名検証＋PEMパーサ（pyo3 拡張）

の 2 フォルダに分けて実装した最小フルコードです。
（本物の量子耐性実装を差し替える箇所は コメント TODO: real impl を明示）