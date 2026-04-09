import json
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("PARTSBOX_API_KEY")

BASE_URL = "https://api.partsbox.com/api/1"
headers = { "Authorization": f"APIKey {api_key}" }

# Load backup parts
backup_path = Path("partsbox-backup-2024-12-19.json")
with open(backup_path, "r") as f:
    backup_data = json.load(f)
parts = backup_data.get("parts", [])

# Classify parts
local_parts = [p for p in parts if p.get("part/type") == "local"]
linked_parts = [p for p in parts if p.get("part/type") == "linked"]
meta_parts = [p for p in parts if p.get("part/type") == "meta"]
subassy_parts = [p for p in parts if p.get("part/type") == "sub-assembly"]

part_id_mapping = []

def create_part(part, extra_payload=None, part_type=None):
    if part_type is None:
        part_type = part.get("part/type")
    payload = {
        "part/type": part_type,
        "part/name": part.get("part/name"),
        "part/description": part.get("part/description", ""),
        "part/footprint": part.get("part/footprint", ""),
        "part/tags": part.get("part/tags", []),
        "part/low-stock": part.get("part/low-stock", {}),
        # Add more fields as needed
    }
    if extra_payload:
        payload.update(extra_payload)
    # Remove empty fields
    payload = {k: v for k, v in payload.items() if v}
    resp = requests.post(f"{BASE_URL}/part/create", headers=headers, json=payload)
    if resp.ok:
        new_id = resp.json().get("data", {}).get("part/id")
        return new_id
    else:
        print(f"Failed to import part: {part.get('part/name')} ({part.get('part/id')})")
        print(resp.text)
        return None

# Import local parts
for part in local_parts:
    old_id = part.get("part/id")
    new_id = create_part(part)
    name = part.get("part/name")
    if old_id and new_id:
        part_id_mapping.append({
            "part/name": name,
            "old_id": old_id,
            "new_id": new_id
        })

# Import linked parts
for part in linked_parts:
    old_id = part.get("part/id")
    new_id = create_part(part, part_type="local")
    name = part.get("part/name")
    if old_id and new_id:
        part_id_mapping.append({
            "part/name": name,
            "old_id": old_id,
            "new_id": new_id
        })
    print(f"WARN: Part must be linked manually: {name}, (ID: {new_id})")

# Import sub-assembly parts (after all leaves are imported)
# subassy can't be created directly, converting to local
for part in subassy_parts:
    old_id = part.get("part/id")
    new_id = create_part(part, part_type="local")
    name = part.get("part/name")
    if old_id and new_id:
        part_id_mapping.append({
            "part/name": name,
            "old_id": old_id,
            "new_id": new_id
        })
    print(f"WARN: Subassembly part converted to local: {name}, (ID: {new_id})")

# Import meta parts (after all leaves and subassemblies are imported)
for part in meta_parts:
    old_id = part.get("part/id")
    # Map part/part-ids to new IDs
    part_ids = [part_id_mapping.get(pid, pid) for pid in part.get("part/part-ids", [])]
    payload = {
        "part/type": part.get("part/type"),
        "part/name": part.get("part/name"),
        "part/description": part.get("part/description", ""),
        "part/footprint": part.get("part/footprint", ""),
        "part/part-ids": part_ids,
        "part/tags": part.get("part/tags", []),
        "part/low-stock": part.get("part/low-stock", {}),
    }
    payload = {k: v for k, v in payload.items() if v}
    resp = requests.post(f"{BASE_URL}/part/create", headers=headers, json=payload)
    if resp.ok:
        new_id = resp.json().get("data", {}).get("part/id")
        part_id_mapping[old_id] = new_id
    else:
        print(f"Failed to import meta part: {part.get('part/name')} ({old_id})")
        print(resp.text)

# Save mapping
with open("part_id_mapping.json", "w") as f:
    json.dump(part_id_mapping, f, indent=2)

print(f"Imported {len(part_id_mapping)} parts. Mapping saved to part_id_mapping.json.")

# Warn about linked parts
if linked_parts:
    print(f"WARNING: {len(linked_parts)} linked parts found. These must be linked manually in the UI after import.")