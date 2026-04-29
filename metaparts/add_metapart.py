import csv
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("PARTSBOX_API_KEY")

BASE_URL = "https://api.partsbox.com/api/1"
headers = { "Authorization": f"APIKey {api_key}" }

# Fetch all parts from the API
# response = requests.post(f"{BASE_URL}/part/all", headers=headers, json={})
# response.raise_for_status()
# parts = response.json().get("data", [])

class PartsboxApi:
    BASE_URL = "https://api.partsbox.com/api/1"

    def __init__(self, api_key=None):
        if api_key is None:
            self.api_key = os.getenv("PARTSBOX_API_KEY")
        else:
            self.api_key = api_key

        self.headers = { "Authorization": f"APIKey {self.api_key}" }
    
    def post(self, path, payload={}):
        print(f"{self.BASE_URL}/{path}")
        response = requests.post(f"{self.BASE_URL}/{path}", headers=self.headers, json=payload)
        print(response)
        response.raise_for_status()
        return response.json().get("data", [])

    def all_parts(self):
        return self.post("part/all")

    def new_metapart(self, name)

if __name__ == "__main__":
    load_dotenv()
    api = PartsboxApi()

    print(api.all_parts())