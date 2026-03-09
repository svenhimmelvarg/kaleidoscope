#!/usr/bin/env python3
import sys
import time
import os
import binascii
import struct
import argparse
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.kbkdf import KBKDFHMAC, CounterLocation, Mode
from cryptography.hazmat.primitives.ciphers.aead import AESGCMSIV
from cryptography.hazmat.backends import default_backend
import google.protobuf.empty_pb2

# Import the generated protobuf code
# If this fails, ensure you run: protoc --python_out=. convex_keys.proto
import convex_keys_pb2

# Constants
ADMIN_KEY_VERSION = 1
KEY_LEN = 16
NONCE_LEN = 12


def derive_key(secret_hex, purpose_bytes):
    """
    Derives the AES encryption key using KBKDF-CTR-HMAC-SHA256.
    Matches the aws-lc-rs implementation used in convex-backend.
    """
    try:
        secret = binascii.unhexlify(secret_hex)
    except binascii.Error:
        raise ValueError("Instance secret must be a valid hex string")

    if len(secret) != 32:
        raise ValueError(
            f"Instance secret must be 32 bytes (64 hex chars). Got {len(secret)} bytes."
        )

    # KBKDF-CTR-HMAC-SHA256 configuration:
    # - Mode: Counter Mode
    # - PRF: HMAC-SHA256
    # - R (Counter Length): 4 bytes (32-bit big endian)
    # - L (Derived Key Length): 4 bytes (32-bit big endian)
    # - Fixed Input: "admin key" (Used directly as 'info', no null separators)
    kdf = KBKDFHMAC(
        algorithm=hashes.SHA256(),
        mode=Mode.CounterMode,
        length=KEY_LEN,
        rlen=4,
        llen=4,
        location=CounterLocation.BeforeFixed,
        label=None,  # Not used because we provide 'fixed'
        context=None,  # Not used because we provide 'fixed'
        fixed=purpose_bytes,
        backend=default_backend(),
    )
    return kdf.derive(secret)


def generate_admin_key(instance_name, instance_secret_hex, member_id=0, system=False):
    # 1. Derive the Encryption Key
    purpose = b"admin key"
    try:
        key = derive_key(instance_secret_hex, purpose)
    except Exception as e:
        sys.stderr.write(f"Error deriving key: {e}\n")
        return None

    # 2. Create the Protobuf Message
    admin_key = convex_keys_pb2.AdminKey()
    # instance_name is left unset (None) in the proto for admin keys
    admin_key.issued_s = int(time.time())
    admin_key.is_read_only = False

    if system:
        admin_key.system.CopyFrom(google.protobuf.empty_pb2.Empty())
    else:
        admin_key.member_id = member_id

    plaintext = admin_key.SerializeToString()

    # 3. Encrypt using AES-128-GCM-SIV
    nonce = os.urandom(NONCE_LEN)
    aad = bytes([ADMIN_KEY_VERSION])  # Version 1

    aesgcm = AESGCMSIV(key)
    # Encrypt returns ciphertext + tag (16 bytes appended)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, aad)

    # 4. Construct Output
    # Format: [Version (1 byte)] + [Nonce (12 bytes)] + [Ciphertext + Tag]
    blob = aad + nonce + ciphertext_with_tag
    hex_blob = binascii.hexlify(blob).decode("utf-8")

    return f"{instance_name}|{hex_blob}"


def main():
    parser = argparse.ArgumentParser(description="Generate Convex Admin Key")
    parser.add_argument("instance_name", help="Name of the Convex instance")
    parser.add_argument("secret_hex", help="32-byte hex secret")
    parser.add_argument("--member-id", type=int, default=0, help="Member ID (default: 0)")
    parser.add_argument(
        "--system", action="store_true", help="Generate system key instead of admin key"
    )

    args = parser.parse_args()

    key = generate_admin_key(args.instance_name, args.secret_hex, args.member_id, args.system)

    if key:
        print(key)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
