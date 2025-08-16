import time

print("import start")
time.sleep(0.5)

import poh_ack_rust  # ← ここで止まる？

print("import success")
print("poh_ack_rust =", poh_ack_rust)
