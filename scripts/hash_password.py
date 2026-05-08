#!/usr/bin/env python3
"""
Generate a bcrypt hash for the admin password.

Usage:
    pip install passlib[bcrypt]
    python scripts/hash_password.py

Paste the printed hash into .env as ADMIN_PASSWORD_HASH.
The plaintext password is never stored anywhere.
"""
import getpass
from passlib.context import CryptContext

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

password = getpass.getpass("Enter admin password: ")
confirm = getpass.getpass("Confirm admin password: ")

if password != confirm:
    print("Passwords do not match.")
    raise SystemExit(1)

print("\nADMIN_PASSWORD_HASH=" + ctx.hash(password))
