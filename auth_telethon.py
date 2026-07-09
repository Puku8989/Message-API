"""One-time Telethon authentication script.

Run this script once to authenticate your Telegram account and generate
a session file.  After successful authentication, the main FastAPI
application can reuse the session without further interaction.

Usage::

    python auth_telethon.py

You will be prompted to enter the verification code that Telegram sends
to your app (or via SMS).  If you have Two-Step Verification enabled,
you will also be prompted for your password.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys

from dotenv import load_dotenv

# Load .env from the same directory as this script
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(_SCRIPT_DIR / ".env")


async def main() -> None:
    """Run the interactive Telethon authentication flow."""
    # Import here to avoid issues if telethon is not installed
    from telethon import TelegramClient

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")

    if not api_id or not api_hash or not phone:
        print("❌ Error: Missing required environment variables.")
        print("   Please set the following in your .env file:")
        print("     TELEGRAM_API_ID    — from https://my.telegram.org")
        print("     TELEGRAM_API_HASH  — from https://my.telegram.org")
        print("     TELEGRAM_PHONE     — your Telegram phone number")
        sys.exit(1)

    session_path = str(_SCRIPT_DIR / "telethon_session")

    print(f"[*] Authenticating with phone: {phone}")
    print(f"[*] Session will be saved to: {session_path}.session")
    print()

    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"[OK] Already authenticated as: {me.first_name} (@{me.username})")
        print("     Session file exists and is valid. No action needed.")
        await client.disconnect()
        return

    print("[*] Sending verification code to your Telegram app...")
    await client.send_code_request(phone)

    code = input("[?] Enter the verification code you received: ").strip()

    try:
        await client.sign_in(phone, code)
    except Exception:
        # Two-Step Verification might be enabled
        password = input("[?] Two-Step Verification enabled. Enter your password: ").strip()
        await client.sign_in(password=password)

    me = await client.get_me()
    print()
    print(f"[OK] Successfully authenticated as: {me.first_name} (@{me.username})")
    print(f"[OK] Session saved to: {session_path}.session")
    print()
    print("You can now start the API server -- phone-number messaging is ready!")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
