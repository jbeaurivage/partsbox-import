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
response = requests.post(f"{BASE_URL}/part/all", headers=headers, json={})
response.raise_for_status()
parts = response.json().get("data", [])

print(parts)

# # Write to CSV
# with open("all_parts.csv", "w", newline="") as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["part_number", "id", "description", "footprint", "tags"])
#     for part in parts:
#         part_number = part.get("part/name", "")
#         part_id = part.get("part/id", "")
#         description = part.get("part/description", "")
#         footprint = part.get("part/footprint", "")
#         tags = part.get("part/tags", [])
#         tags_str = ";".join(tags) if tags else ""
#         writer.writerow([part_number, part_id, description, footprint, tags_str])

# print("Wrote all_parts.csv")