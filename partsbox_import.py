#!/usr/bin/env python3
"""
PartsBox Data Importer
======================
Reimports storage locations, part definitions, and stock from a PartsBox JSON export.

Usage:
    python partsbox_import.py --file export.json --api-key YOUR_API_KEY [options]

Options:
    --file        Path to the PartsBox JSON export file (required)
    --api-key     Your PartsBox API key (required)
    --base-url    API base URL (default: https://api.partsbox.com/api/1)
    --dry-run     Simulate the import without making any API calls
    --skip-stock  Only create storage locations and parts, skip stock entries
    --log         Path to write a detailed log (default: partsbox_import.log)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.partsbox.com/api/1"
REQUEST_DELAY = 0.2          # seconds between API calls (be polite to the server)
MAX_RETRIES = 3
RETRY_DELAY = 2.0


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger("partsbox_import")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AlreadyExistsError(Exception):
    """Raised when the API returns 409 – item already exists in the database."""


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------

class PartsBoxClient:
    def __init__(self, api_key: str, base_url: str, dry_run: bool, logger: logging.Logger):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.log = logger
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"APIKey {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _post(self, endpoint: str, payload: dict) -> dict:
        """POST to an API endpoint with retry logic."""
        url = f"{self.base_url}/{endpoint}"
        self.log.debug("POST %s  payload=%s", url, json.dumps(payload))

        if self.dry_run:
            self.log.info("[DRY RUN] Would POST to %s with: %s", endpoint, json.dumps(payload, indent=2))
            # Return a fake ID so downstream steps (stock, meta-part children) can proceed
            fake_id = f"dry-run-{endpoint.replace('/', '-')}-{int(time.time() * 1000) % 100000}"
            return {"partsbox.status/category": "status/ok", "data": {
                "storage/id": fake_id,
                "part/id": fake_id,
            }}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.post(url, json=payload, timeout=30)
                if resp.status_code == 409:
                    raise AlreadyExistsError()
                resp.raise_for_status()
                result = resp.json()
                self.log.debug("Response: %s", json.dumps(result))
                time.sleep(REQUEST_DELAY)
                return result
            except AlreadyExistsError:
                raise  # don't retry, bubble up immediately
            except requests.HTTPError as e:
                self.log.warning("HTTP error on attempt %d/%d: %s", attempt, MAX_RETRIES, e)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY * attempt)
            except requests.RequestException as e:
                self.log.warning("Request error on attempt %d/%d: %s", attempt, MAX_RETRIES, e)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY * attempt)

    def create_storage(self, name: str, description: str = "", tags: list = None) -> str | None:
        """Create a storage location; returns new storage ID or None on failure."""
        payload = {"storage/name": name}
        if description:
            payload["storage/description"] = description
        if tags:
            payload["storage/tags"] = tags

        try:
            result = self._post("storage/create", payload)
            if result.get("partsbox.status/category") == "status/ok":
                new_id = result.get("data", {}).get("storage/id")
                self.log.info("  ✓ Storage created: '%s'  new_id=%s", name, new_id)
                return new_id
            else:
                self.log.error("  ✗ Storage create failed for '%s': %s", name, result.get("partsbox.status/message"))
                return None
        except AlreadyExistsError:
            self.log.warning("  ~ Storage SKIPPED (already exists): '%s'", name)
            return "SKIPPED"
        except Exception as e:
            self.log.error("  ✗ Exception creating storage '%s': %s", name, e)
            return None

    def create_part(self, payload: dict) -> str | None:
        """Create a part; returns new part ID or None on failure."""
        name = payload.get("part/name", "?")
        try:
            result = self._post("part/create", payload)
            if result.get("partsbox.status/category") == "status/ok":
                new_id = result.get("data", {}).get("part/id")
                self.log.info("  ✓ Part created: '%s'  new_id=%s", name, new_id)
                return new_id
            else:
                self.log.error("  ✗ Part create failed for '%s': %s", name, result.get("partsbox.status/message"))
                return None
        except AlreadyExistsError:
            self.log.warning("  ~ Part SKIPPED (already exists): '%s'", name)
            return "SKIPPED"
        except Exception as e:
            self.log.error("  ✗ Exception creating part '%s': %s", name, e)
            return None

    def add_stock(self, part_id: str, storage_id: str, quantity: int,
                  price: float = None, currency: str = None, comments: str = "") -> bool:
        """Add a stock entry. Returns True on success."""
        payload = {
            "stock/part-id": part_id,
            "stock/storage-id": storage_id,
            "stock/quantity": quantity,
        }
        if price is not None:
            payload["stock/price"] = price
        if currency:
            payload["stock/currency"] = currency
        if comments:
            payload["stock/comments"] = comments

        try:
            result = self._post("stock/add", payload)
            if result.get("partsbox.status/category") == "status/ok":
                self.log.info("    ✓ Stock added: qty=%+d  storage=%s", quantity, storage_id)
                return True
            else:
                self.log.error("    ✗ Stock add failed (qty=%d): %s", quantity, result.get("partsbox.status/message"))
                return False
        except Exception as e:
            self.log.error("    ✗ Exception adding stock (qty=%d): %s", quantity, e)
            return False


# ---------------------------------------------------------------------------
# Import Logic
# ---------------------------------------------------------------------------

class PartsBoxImporter:
    def __init__(self, client: PartsBoxClient, logger: logging.Logger, skip_stock: bool):
        self.client = client
        self.log = logger
        self.skip_stock = skip_stock

        # Maps old export IDs → newly created IDs
        self.storage_id_map: dict[str, str] = {}   # old_id -> new_id
        self.part_id_map: dict[str, str] = {}       # old_id -> new_id

        # Stats
        self.stats = {
            "storage_ok": 0, "storage_fail": 0, "storage_skip": 0,
            "part_ok": 0, "part_fail": 0, "part_skip": 0,
            "stock_ok": 0, "stock_fail": 0, "stock_skip": 0,
        }

    # ------------------------------------------------------------------ #
    # Phase 1 – Storage locations
    # ------------------------------------------------------------------ #

    def import_storages(self, storages: list[dict]):
        self.log.info("=" * 60)
        self.log.info("PHASE 1: Importing %d storage locations", len(storages))
        self.log.info("=" * 60)

        for s in storages:
            old_id = s.get("storage/id")
            name = s.get("storage/name", "")
            description = s.get("storage/description", "")
            tags = s.get("storage/tags", [])

            self.log.info("Storage: '%s'  (old_id=%s)", name, old_id)

            new_id = self.client.create_storage(name, description, tags)
            if new_id == "SKIPPED":
                self.stats["storage_skip"] += 1
            elif new_id:
                self.storage_id_map[old_id] = new_id
                self.stats["storage_ok"] += 1
            else:
                self.stats["storage_fail"] += 1

    # ------------------------------------------------------------------ #
    # Phase 2 – Parts
    # ------------------------------------------------------------------ #

    def import_parts(self, parts: list[dict]):
        self.log.info("=" * 60)
        self.log.info("PHASE 2: Importing %d parts", len(parts))
        self.log.info("=" * 60)

        # Meta-parts reference children by ID, so import all non-meta parts first,
        # then meta-parts — by then every child will already be in part_id_map.
        ordered = sorted(parts, key=lambda p: 1 if p.get("part/type") == "meta" else 0)

        for p in ordered:
            self._import_part(p)

    def _import_part(self, p: dict):
        old_id = p.get("part/id")
        ptype = p.get("part/type", "local")
        name = p.get("part/name", "")

        self.log.info("Part [%s]: '%s'  (old_id=%s)", ptype, name, old_id)

        if ptype == "linked":
            # The API cannot create linked parts directly – create as local,
            # user must re-link via UI.
            self.log.warning(
                "  ! Part '%s' is linked; will be created as LOCAL. "
                "Re-link manually via UI (linked-id was: %s).",
                name, p.get("part/linked-id", "?")
            )
            ptype = "local"

        if ptype == "meta":
            self._import_meta_part(p, old_id, name)
        else:
            self._import_local_part(p, old_id, name, ptype)

    def _build_common_payload(self, p: dict, ptype: str) -> dict:
        """Fields shared by local and meta parts."""
        payload: dict = {"part/type": ptype, "part/name": p["part/name"]}

        for field in ("part/description", "part/notes", "part/footprint",
                      "part/manufacturer", "part/mpn"):
            if p.get(field):
                # Map export keys → API keys (manufacturer/mpn aren't standard
                # API params but we include them anyway so nothing is lost)
                payload[field] = p[field]

        if p.get("part/tags"):
            payload["part/tags"] = p["part/tags"]

        if p.get("part/low-stock"):
            payload["part/low-stock"] = p["part/low-stock"]

        # Default storage: map old → new if we have it
        default_sid = p.get("part/default-storage-id")
        if default_sid and default_sid in self.storage_id_map:
            payload["part/default-storage-id"] = self.storage_id_map[default_sid]

        return payload

    def _import_local_part(self, p: dict, old_id: str, name: str, ptype: str):
        payload = self._build_common_payload(p, ptype)

        new_id = self.client.create_part(payload)
        if new_id == "SKIPPED":
            self.stats["part_skip"] += 1
        elif new_id:
            self.part_id_map[old_id] = new_id
            self.stats["part_ok"] += 1
            if not self.skip_stock:
                self._import_stock(p, new_id)
        else:
            self.stats["part_fail"] += 1

    def _import_meta_part(self, p: dict, old_id: str, name: str):
        payload = self._build_common_payload(p, "meta")

        # Remap child part IDs
        child_old_ids = p.get("part/part-ids", [])
        child_new_ids = []
        for cid in child_old_ids:
            if cid in self.part_id_map:
                child_new_ids.append(self.part_id_map[cid])
            else:
                self.log.warning("  ! Meta-part '%s': child %s not yet imported; skipping child.", name, cid)
        if child_new_ids:
            payload["part/part-ids"] = child_new_ids

        new_id = self.client.create_part(payload)
        if new_id == "SKIPPED":
            self.stats["part_skip"] += 1
        elif new_id:
            self.part_id_map[old_id] = new_id
            self.stats["part_ok"] += 1
        else:
            self.stats["part_fail"] += 1

    # ------------------------------------------------------------------ #
    # Phase 3 – Stock
    # ------------------------------------------------------------------ #

    def _import_stock(self, p: dict, new_part_id: str):
        """
        Collapse all stock entries for a part into a single net quantity per
        storage location, then add one stock entry per location.

        Why collapse? The API's stock/add simply records a transaction.
        Replaying every historical transaction would give the right final
        quantity, but it pollutes the transaction log with old build events.
        Instead we compute net quantity per storage location and add that once.
        """
        stock_entries = p.get("part/stock", [])
        if not stock_entries:
            return

        # Aggregate net qty + grab representative price/currency per storage
        net: dict[str, dict] = {}   # old_storage_id -> {qty, price, currency}
        for s in stock_entries:
            sid = s.get("stock/storage-id")
            qty = s.get("stock/quantity", 0)
            if not sid:
                continue
            if sid not in net:
                net[sid] = {"qty": 0, "price": None, "currency": None}
            net[sid]["qty"] += qty
            # Keep the first price we see (usually the add-stock entry)
            if net[sid]["price"] is None and s.get("stock/price") is not None:
                net[sid]["price"] = s["stock/price"]
                net[sid]["currency"] = s.get("stock/currency")

        for old_sid, data in net.items():
            qty = data["qty"]
            if qty <= 0:
                self.log.info("    ~ Stock for storage %s has net qty %d – skipping.", old_sid, qty)
                self.stats["stock_skip"] += 1
                continue

            new_sid = self.storage_id_map.get(old_sid)
            if not new_sid:
                self.log.warning(
                    "    ! Storage %s not in ID map (import may have failed). "
                    "Stock of %d units skipped.", old_sid, qty
                )
                self.stats["stock_skip"] += 1
                continue

            ok = self.client.add_stock(
                part_id=new_part_id,
                storage_id=new_sid,
                quantity=qty,
                price=data["price"],
                currency=data["currency"],
                comments="Imported from export",
            )
            if ok:
                self.stats["stock_ok"] += 1
            else:
                self.stats["stock_fail"] += 1

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #

    def run(self, data: dict):
        storages = data.get("storage", [])
        parts = data.get("parts", [])

        self.import_storages(storages)
        self.import_parts(parts)

        # Summary
        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("IMPORT COMPLETE")
        self.log.info("  Storage:  %d created, %d skipped (already existed), %d failed",
                      self.stats["storage_ok"], self.stats["storage_skip"], self.stats["storage_fail"])
        self.log.info("  Parts:    %d created, %d skipped (already existed), %d failed",
                      self.stats["part_ok"], self.stats["part_skip"], self.stats["part_fail"])
        if not self.skip_stock:
            self.log.info("  Stock:    %d added, %d failed, %d skipped (zero/negative net)",
                          self.stats["stock_ok"], self.stats["stock_fail"], self.stats["stock_skip"])
        self.log.info("=" * 60)

        if self.client.dry_run:
            self.log.info("(This was a DRY RUN – no changes were made.)")

        # Dump the ID mapping so the user can cross-reference
        mapping_path = Path("partsbox_id_mapping.json")
        mapping = {
            "storage": self.storage_id_map,
            "parts": self.part_id_map,
        }
        mapping_path.write_text(json.dumps(mapping, indent=2))
        self.log.info("ID mapping saved to: %s", mapping_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Reimport a PartsBox JSON export via the API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--file", required=True, help="Path to the JSON export file")
    parser.add_argument("--api-key", required=True, help="PartsBox API key")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without making API calls")
    parser.add_argument("--skip-stock", action="store_true",
                        help="Skip stock import (only create storage & parts)")
    parser.add_argument("--log", default="partsbox_import.log",
                        help="Path for the detailed log file")
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging(args.log)

    # Load export file
    export_path = Path(args.file)
    if not export_path.exists():
        logger.error("Export file not found: %s", export_path)
        sys.exit(1)

    logger.info("Loading export from: %s", export_path)
    with open(export_path, encoding="utf-8") as f:
        data = json.load(f)

    storages = data.get("storage", [])
    parts = data.get("parts", [])
    logger.info("Found %d storage location(s) and %d part(s) in export.", len(storages), len(parts))

    client = PartsBoxClient(
        api_key=args.api_key,
        base_url=args.base_url,
        dry_run=args.dry_run,
        logger=logger,
    )
    importer = PartsBoxImporter(client, logger, skip_stock=args.skip_stock)
    importer.run(data)


if __name__ == "__main__":
    main()