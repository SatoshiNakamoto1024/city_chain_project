# network/DAGs/common/security/app_security.py
"""
app_security.py
FastAPI で Security API を起動して、各ユーティリティを HTTP で試せるデモサーバ
起動: python -m network.DAGs.common.security.app_security
"""
import os
import sys
sys.path.append(os.path.abspath("D:\\city_chain_project\\network\\DAGs\\common"))

from fastapi import FastAPI, File, HTTPException, Query
from security import certs, mtls, signing, encryption

app = FastAPI(title="Security Demo")


@app.get("/certs/load")
async def load_cert(path: str = Query(..., description="PEM 証明書のパス")):
    try:
        c = certs.load_pem_cert(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cn": certs.get_cn(c)}


@app.get("/certs/validate")
async def validate_cert(
    path: str = Query(..., description="検証対象 PEM"),
    trust: str = Query(..., description="信頼アンカー PEM"),
):
    try:
        c = certs.load_pem_cert(path)
        a = certs.load_pem_cert(trust)
        ok = certs.validate_chain(c, [a])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"valid": ok}


@app.get("/mtls/grpc")
async def test_grpc(target: str = Query(..., description="gRPC ターゲット")):
    ch = mtls.create_grpc_channel(target)
    return {"type": type(ch).__name__}


@app.get("/mtls/http")
async def test_http():
    s = mtls.create_https_session()
    return {"cert": s.cert, "verify": s.verify}


@app.post("/sign/dilithium")
async def sign_dilithium(msg: bytes = File(...)):
    pk, sk = signing.create_dilithium_keypair()
    sig = signing.sign_dilithium(msg, sk)
    ok = signing.verify_dilithium(msg, sig, pk)
    return {"pub": pk.hex(), "sig": sig.hex(), "verified": ok}


@app.post("/sign/ntru")
async def sign_ntru(msg: bytes = File(...)):
    pk, sk = signing.create_ntru_keypair()
    ct, ss = signing.encrypt_ntru(pk)
    ss2 = signing.decrypt_ntru(ct, sk)
    return {"pub": pk.hex(), "cipher": ct.hex(), "secret": ss.hex(), "decrypted": ss2.hex()}


@app.post("/sign/rsa")
async def sign_rsa(msg: bytes = File(...)):
    priv, pub = signing.create_rsa_keypair()
    sig = signing.sign_rsa(msg, priv)
    ok = signing.verify_rsa(msg, sig, pub)
    return {"sig": sig.decode(), "verified": ok}


@app.post("/encrypt")
async def http_encrypt(data: bytes = File(...), key: str = Query(...)):
    k = bytes.fromhex(key)
    ct = encryption.encrypt_field(data, k)
    return {"cipher": ct.hex()}


@app.post("/decrypt")
async def http_decrypt(data: bytes = File(...), key: str = Query(...)):
    k = bytes.fromhex(key)
    pt = encryption.decrypt_field(bytes.fromhex(data.decode()), k)
    return {"plain": pt.decode()}


@app.get("/key")
async def get_key():
    kid, k = encryption.create_data_key()
    return {"key_id": kid, "key": k.hex()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083, log_level="info")
