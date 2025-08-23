# dag/dag_utils.py
import hashlib


def compute_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()


if __name__ == "__main__":
    print(compute_hash("example data"))
