# VRF/vrf_python/app_vrf.py
"""Command-line demo for VRF Python client."""
import argparse
from .vrf_builder import generate_keypair, prove_vrf
from .vrf_validator import verify_vrf


def main():
    parser = argparse.ArgumentParser(description="VRF demo CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("gen", help="Generate VRF keypair")

    prove = sub.add_parser("prove", help="Generate VRF proof")
    prove.add_argument("sk", help="Secret key (hex)")
    prove.add_argument("message", help="Message string")

    verify = sub.add_parser("verify", help="Verify VRF proof")
    verify.add_argument("pk", help="Public key (hex)")
    verify.add_argument("proof", help="Proof (hex)")
    verify.add_argument("message", help="Message string")

    args = parser.parse_args()

    if args.cmd == "gen":
        pk, sk = generate_keypair()
        print("Public Key:", pk)
        print("Secret Key:", sk)

    elif args.cmd == "prove":
        proof, h = prove_vrf(args.sk, args.message.encode())
        print("Proof:", proof)
        print("Hash: ", h)

    elif args.cmd == "verify":
        h = verify_vrf(args.pk, args.proof, args.message.encode())
        print("Hash: ", h)


if __name__ == "__main__":
    main()
