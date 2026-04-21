#!/usr/bin/env python3
"""
Stage A helper: import and adapt Java authoritative tunnel-path records.

Purpose
-------
- Scan router-side authoritative JSONL files under a testnet base
- Validate and copy/adapt rows into the hop_truth imports area
- Build router-hash -> Router N mapping from local_router_hash values
- Emit one adapted authoritative-hop-events.jsonl file plus one manifest
- Print a single machine-readable JSON result to stdout

Designed to be called from the GUI with subprocess.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

HOME = str(Path.home())
DEFAULT_IMPORTS_ROOT = os.path.join(HOME, "i2p-gui", "logs", "hop_truth", "imports")
DEFAULT_TESTNET_GLOB = os.path.join(HOME, "i2p-testnet-*")
SOURCE_PATTERN = os.path.join("r*", "data", "authoritative", "authoritative-hop-events.jsonl")


@dataclass
class RouterMapEntry:
    router_id: str
    router_name: str


def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def safe_json_loads(line: str) -> Optional[dict]:
    try:
        value = json.loads(line)
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def find_latest_testnet_base() -> str:
    candidates = [p for p in glob.glob(DEFAULT_TESTNET_GLOB) if os.path.isdir(p)]
    if not candidates:
        return ""
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def resolve_testnet_base(explicit: str) -> str:
    explicit = str(explicit or "").strip()
    if explicit:
        return explicit if os.path.isdir(explicit) else ""
    return find_latest_testnet_base()


def discover_source_files(testnet_base: str) -> List[str]:
    pattern = os.path.join(testnet_base, SOURCE_PATTERN)
    files = sorted(glob.glob(pattern))
    return [p for p in files if os.path.isfile(p)]


def router_id_from_source_path(path: str) -> str:
    parts = Path(path).parts
    for token in parts:
        if token.startswith("r") and token[1:].isdigit():
            return token[1:]
    return ""


def build_hash_to_router_map(source_files: Iterable[str]) -> Dict[str, RouterMapEntry]:
    mapping: Dict[str, RouterMapEntry] = {}
    for path in source_files:
        rid = router_id_from_source_path(path)
        if not rid:
            continue
        router_name = f"Router {rid}"
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for raw in fh:
                    row = safe_json_loads(raw.strip())
                    if not row:
                        continue
                    local_hash = str(row.get("local_router_hash") or "").strip()
                    if local_hash:
                        mapping[local_hash] = RouterMapEntry(router_id=rid, router_name=router_name)
                        break
        except Exception:
            continue
    return mapping


def hop_hashes_to_names(hop_hashes: List[str], mapping: Dict[str, RouterMapEntry]) -> Tuple[List[str], List[str]]:
    ids: List[str] = []
    names: List[str] = []
    for item in hop_hashes:
        key = str(item or "").strip()
        if key and key in mapping:
            entry = mapping[key]
            ids.append(entry.router_id)
            names.append(entry.router_name)
        else:
            ids.append("")
            preview = key[:12] if key else "unknown"
            names.append(f"Unknown[{preview}]")
    return ids, names


def build_tunnel_id(row: dict) -> str:
    basis = "|".join([
        str(row.get("local_router_hash") or ""),
        str(row.get("direction") or ""),
        str(row.get("tunnel_kind") or ""),
        str(row.get("destination_hash") or ""),
        str(row.get("expiration_ms") or ""),
        ",".join([str(x) for x in (row.get("hop_hashes") or [])]),
    ])
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]
    return f"java-auth-{digest}"


def adapt_row(
    row: dict,
    mapping: Dict[str, RouterMapEntry],
    adapted_run_id: str,
    source_file: str,
) -> Optional[dict]:
    hop_hashes = row.get("hop_hashes") or []
    if not isinstance(hop_hashes, list) or not hop_hashes:
        return None

    hop_chain_ids, hop_chain_names = hop_hashes_to_names(hop_hashes, mapping)
    hop_count = len(hop_chain_names)
    if hop_count <= 0:
        return None

    return {
        "ts_utc": str(row.get("ts_utc") or ""),
        "ts_local": str(row.get("ts_utc") or ""),
        "run_id": adapted_run_id,
        "scenario_bucket": "authoritative",
        "scenario_label": "java_authoritative_import",
        "phase_stage": "runtime",
        "phase_trigger_reason": "java_router_authoritative_adapter",
        "source_mode": "java-router-authoritative",
        "truth_level": str(row.get("truth_level") or "ground-truth"),
        "tunnel_id": build_tunnel_id(row),
        "tunnel_direction": str(row.get("direction") or "unknown"),
        "tunnel_kind": str(row.get("tunnel_kind") or "unknown"),
        "hop_count": hop_count,
        "hop_chain_ids": hop_chain_ids,
        "hop_chain_names": hop_chain_names,
        "full_hop_chain": hop_chain_names,
        "_source_file": source_file,
        "_java_local_router_hash": str(row.get("local_router_hash") or ""),
        "_java_destination_hash": str(row.get("destination_hash") or ""),
        "_java_gateway_hash": str(row.get("gateway_hash") or ""),
        "_java_endpoint_hash": str(row.get("endpoint_hash") or ""),
        "_java_far_end_hash": str(row.get("far_end_hash") or ""),
        "_java_expiration_ms": row.get("expiration_ms"),
        "_java_was_reused": row.get("was_reused"),
        "_java_pool_name": str(row.get("pool_name") or ""),
    }


def write_json(path: str, payload: dict) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import/adapt Java authoritative tunnel-path JSONL into hop_truth imports.")
    parser.add_argument("--testnet-base", default="", help="Explicit testnet base path. Defaults to latest ~/i2p-testnet-* directory.")
    parser.add_argument("--imports-root", default=DEFAULT_IMPORTS_ROOT, help="Root imports directory. Defaults to ~/i2p-gui/logs/hop_truth/imports")
    args = parser.parse_args()

    started_local = now_local()
    testnet_base = resolve_testnet_base(args.testnet_base)
    imports_root = ensure_dir(os.path.expanduser(args.imports_root))

    result = {
        "success": False,
        "started_local": started_local,
        "finished_local": None,
        "testnet_base": testnet_base,
        "files_scanned": 0,
        "rows_read": 0,
        "rows_written": 0,
        "rows_skipped": 0,
        "import_dir": "",
        "output_jsonl": "",
        "manifest_path": "",
        "result_text": "",
    }

    if not testnet_base:
        result["finished_local"] = now_local()
        result["result_text"] = "No valid testnet base found."
        print(json.dumps(result, ensure_ascii=False))
        return 1

    source_files = discover_source_files(testnet_base)
    result["files_scanned"] = len(source_files)
    if not source_files:
        result["finished_local"] = now_local()
        result["result_text"] = "No authoritative-hop-events.jsonl files were found under the selected testnet base."
        print(json.dumps(result, ensure_ascii=False))
        return 1

    hash_mapping = build_hash_to_router_map(source_files)
    adapted_run_id = f"{os.path.basename(testnet_base)}-java-authoritative-adapted-{now_stamp()}"
    import_dir = ensure_dir(os.path.join(imports_root, adapted_run_id))
    output_jsonl = os.path.join(import_dir, "authoritative-hop-events.jsonl")
    manifest_path = os.path.join(import_dir, "java-authoritative-adapter-manifest.json")

    adapted_rows: List[dict] = []
    source_manifest: List[dict] = []

    for src in source_files:
        per_file_read = 0
        per_file_written = 0
        per_file_skipped = 0
        try:
            with open(src, "r", encoding="utf-8", errors="ignore") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    per_file_read += 1
                    row = safe_json_loads(line)
                    if not row:
                        per_file_skipped += 1
                        continue
                    adapted = adapt_row(row, hash_mapping, adapted_run_id, src)
                    if not adapted:
                        per_file_skipped += 1
                        continue
                    adapted_rows.append(adapted)
                    per_file_written += 1
        except Exception:
            per_file_skipped += 1

        result["rows_read"] += per_file_read
        result["rows_written"] += per_file_written
        result["rows_skipped"] += per_file_skipped
        source_manifest.append({
            "source_file": src,
            "rows_read": per_file_read,
            "rows_written": per_file_written,
            "rows_skipped": per_file_skipped,
        })

    with open(output_jsonl, "w", encoding="utf-8") as fh:
        for row in adapted_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "generated_at_local": now_local(),
        "testnet_base": testnet_base,
        "import_dir": import_dir,
        "output_jsonl": output_jsonl,
        "run_id": adapted_run_id,
        "files_scanned": result["files_scanned"],
        "rows_read": result["rows_read"],
        "rows_written": result["rows_written"],
        "rows_skipped": result["rows_skipped"],
        "source_mode": "java-router-authoritative",
        "source_files": source_manifest,
        "notes": [
            "Adapts Java authoritative raw rows into the hop_truth normalization contract.",
            "Maps hop_hashes to Router N labels using local_router_hash values from imported router files.",
            "Preserves original Java fields under _java_* metadata keys.",
        ],
    }
    write_json(manifest_path, manifest)

    result.update({
        "success": result["rows_written"] > 0,
        "finished_local": now_local(),
        "import_dir": import_dir,
        "output_jsonl": output_jsonl,
        "manifest_path": manifest_path,
        "result_text": (
            f"Imported {result['rows_written']} authoritative rows from {result['files_scanned']} files "
            f"under {testnet_base}."
            if result["rows_written"] > 0
            else "No authoritative rows were adapted successfully."
        ),
    })

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
