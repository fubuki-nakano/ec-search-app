import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SERPAPI_KEY")

url = "https://serpapi.com/search"

params = {
    "engine": "google_shopping",
    "q": "PS5 本体",
    "gl": "jp",
    "hl": "ja",
    "api_key": api_key,
}

response = requests.get(url, params=params, timeout=15)

print(response.status_code)

data = response.json()

print(data.keys())

if data.get("shopping_results"):
    print(data["shopping_results"][0])