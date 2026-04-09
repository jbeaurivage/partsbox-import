import argparse
import json
import logging
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import os

import requests

load_dotenv()
api_key = os.getenv("PARTSBOX_API_KEY")

BASE_URL = "https://api.partsbox.com/api/1"
headers = { "Authorization": f"APIKey {api_key}" }

# Load backup storage locations
backup_path = Path("partsbox-backup-2024-12-19.json")
with open(backup_path, "r") as f:
    backup_data = json.load(f).get("storage")

# Build a mapping from storage name to old ID
backup_name_to_id = {
    loc["storage/name"]: loc["storage/id"]
    for loc in backup_data
    if "storage/name" in loc and "storage/id" in loc
}

# Fetch current storage locations from API
response = requests.post(f"{BASE_URL}/storage/all", headers=headers, json={})
response.raise_for_status()
response_json = response.json()

# Parse locations from the 'data' key
current_locations = response_json.get("data")

# Build sets of names for comparison
backup_names = set(backup_name_to_id.keys())
current_names = set(loc.get("storage/name") for loc in current_locations if "storage/name" in loc)

# Build mapping: old_id -> new_id for matching storage names
id_mapping = []
for loc in current_locations:
    name = loc.get("storage/name")
    new_id = loc.get("storage/id")
    old_id = backup_name_to_id.get(name)
    if old_id and new_id:
        id_mapping.append({
            "storage/name": name,
            "old_id": old_id,
            "new_id": new_id
        })

# Warn on missed locations
missed_in_new = backup_names - current_names
missed_in_old = current_names - backup_names

if missed_in_new:
    print("WARNING: The following storage locations are in the backup but not in the current data:")
    for name in missed_in_new:
        print(f"  - {name}")

if missed_in_old:
    print("WARNING: The following storage locations are in the current data but not in the backup:")
    for name in missed_in_old:
        print(f"  - {name}")

# Save mapping to JSON file
with open("storage_id_mapping.json", "w") as f:
    json.dump(id_mapping, f, indent=2)

print(f"Saved {len(id_mapping)} old/new ID mappings to storage_id_mapping.json")