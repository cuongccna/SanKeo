import os
from dotenv import load_dotenv

load_dotenv()

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

if api_id and api_hash and api_id != "0":
    print("OK")
else:
    print("MISSING")
