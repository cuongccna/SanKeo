import asyncio
import json
import os
from pyrogram import Client

async def test_proxy():
    print("--- Proxy Connection Test ---")
    
    # Load Proxy Config
    try:
        with open("proxies.json", "r") as f:
            proxies = json.load(f)
    except FileNotFoundError:
        print("❌ proxies.json not found!")
        return

    # Find the first proxy config
    phone = "84389961241"
    if phone not in proxies:
        print(f"❌ No proxy config found for {phone}")
        # Fallback to first key if specific phone not found
        if proxies:
            phone = list(proxies.keys())[0]
            print(f"⚠️ Using proxy for {phone} instead.")
        else:
            return

    proxy_conf = proxies[phone]
    print(f"Testing Proxy: {proxy_conf['scheme']}://{proxy_conf['hostname']}:{proxy_conf['port']}")

    # Setup Client
    # We use the existing session file
    session_name = phone
    
    app = Client(
        name=session_name,
        workdir="sessions/",
        proxy=proxy_conf
    )

    print("Connecting to Telegram...")
    try:
        await app.start()
        me = await app.get_me()
        print(f"✅ Connection Successful!")
        print(f"👤 Logged in as: {me.first_name} (@{me.username})")
        print(f"🆔 ID: {me.id}")
        await app.stop()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy())
