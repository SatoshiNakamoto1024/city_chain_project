from fastapi import FastAPI
from pathlib import Path
from .distributor.sender_manager import SenderManager

app = FastAPI(title="Sending-DAG Gateway")
sm = SenderManager(Path("pem/client.pem"))


@app.post("/send")
def send(sender: str, receiver: str, amount: float):
    tx_id = sm.create_tx(sender, receiver, amount)
    return {"status": "tx_created", "tx_id": tx_id}
