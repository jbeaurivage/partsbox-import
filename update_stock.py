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

# Load backup data
backup_path = Path("partsbox-backup-2024-12-19.json")
with open(backup_path, "r") as f:
    backup_json = json.load(f)
parts = backup_json.get("parts", [])
storage_backup = backup_json.get("storage", [])

# Load storage and part ID mappings
storage_map_path = Path("storage_id_mapping.json")
with open(storage_map_path, "r") as f:
    storage_map = json.load(f)

part_map_path = Path("part_id_mapping.json")
with open(part_map_path, "r") as f:
    part_map = json.load(f)

# Build lookup dicts for old_id -> new_id and name
storage_id_lookup = {entry["old_id"]: entry["new_id"] for entry in storage_map if "old_id" in entry and "new_id" in entry}
storage_name_lookup = {entry["old_id"]: entry["storage/name"] for entry in storage_map if "old_id" in entry and "storage/name" in entry}
part_id_lookup = {entry["old_id"]: entry["new_id"] for entry in part_map if "old_id" in entry and "new_id" in entry}
part_name_lookup = {entry["old_id"]: entry["part/name"] for entry in part_map if "old_id" in entry and "part/name" in entry}

# Collapse stock entries for each (part, storage) pair
stock_totals = {}  # (old_part_id, old_storage_id) -> total quantity

for part in parts:
    old_part_id = part.get("part/id")
    part_name = part.get("part/name", "")
    stock_entries = part.get("part/stock", [])
    for entry in stock_entries:
        old_storage_id = entry.get("stock/storage-id")
        if not old_part_id or not old_storage_id:
            continue
        key = (old_part_id, old_storage_id)
        if key not in stock_totals:
            stock_totals[key] = {
                "quantity": 0,
                "part_name": part_name,
            }
        stock_totals[key]["quantity"] += entry.get("stock/quantity", 0)

# Add stock for each (part, storage) pair with quantity > 0
for (old_part_id, old_storage_id), info in stock_totals.items():
    qty = info["quantity"]
    if qty <= 0:
        continue
    new_part_id = part_id_lookup.get(old_part_id)
    new_storage_id = storage_id_lookup.get(old_storage_id)
    part_name = info["part_name"]
    storage_name = storage_name_lookup.get(old_storage_id, "N/A")
    if not new_part_id or not new_storage_id:
        print(f"WARNING: Could not map part or storage ID for part '{part_name}' ({old_part_id}) or storage '{storage_name}' ({old_storage_id})")
        continue
    payload = {
        "stock/part-id": new_part_id,
        "stock/storage-id": new_storage_id,
        "stock/quantity": qty,
        "stock/comments": f"Imported from backup for part '{part_name}' in storage '{storage_name}'"
    }
    response = requests.post(f"{BASE_URL}/stock/add", headers=headers, json=payload)
    if response.ok:
        print(f"Added stock: part={part_name} ({new_part_id}), storage={storage_name} ({new_storage_id}), qty={qty}")
    else:
        print(f"ERROR adding stock for part={part_name} ({new_part_id}), storage={storage_name} ({new_storage_id}): {response.text}")