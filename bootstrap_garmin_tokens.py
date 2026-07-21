#!/usr/bin/env python3
"""Perform Garmin MFA once and create a reusable token secret locally."""

import getpass
import os
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin


TOKEN_PATH = Path(".garmin_tokens/garmin_tokens.json")


def prompt_mfa() -> str:
    """Read the one-time MFA code Garmin sends during login."""
    code = input("Garmin MFA code: ").strip()
    if not code:
        raise ValueError("An MFA code is required")
    return code


def main() -> None:
    """Log in interactively and persist the resulting refresh tokens."""
    load_dotenv()

    email = os.getenv("GARMIN_EMAIL") or input("Garmin email: ").strip()
    password = os.getenv("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    if not email or not password:
        raise SystemExit("Garmin email and password are required")

    client = Garmin(email, password, prompt_mfa=prompt_mfa)
    client.login(tokenstore=str(TOKEN_PATH))

    print(f"Garmin token file created at {TOKEN_PATH}")
    print("Save it as the GARMINTOKENS GitHub Actions secret:")
    print(f"  gh secret set GARMINTOKENS < {TOKEN_PATH}")


if __name__ == "__main__":
    main()
