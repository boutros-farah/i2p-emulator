"""Export router deployment tables from a topology JSON file."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, List

from build_topology_manifest import build_manifest


ROUTER_COLUMNS: List[str] = [
    "id",
    "name",
    "country",
    "country_code",
    "city",
    "lat",
    "lon",
    "display_lat",
    "display_lon",
    "subnet_label",
    "cidr",
    "router_ip",
    "gateway_ip",
    "namespace",
    "bridge",
    "host_veth",
    "ns_veth",
    "floodfill",
    "location_index",
    "subnet_index",
    "router_index_in_subnet",
]


def sanitize_tsv_value(value: Any) -> str:
    """
    Convert any value into a TSV-safe string:
    - no tabs
    - no newlines
    - booleans as lowercase true/false
    """
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)

    text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()
    return text


def export_router_tsv(topology_file: str, output_tsv: str) -> None:
    manifest = build_manifest(topology_file)
    routers = manifest["routers"]

    out_path = Path(output_tsv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(ROUTER_COLUMNS)

        for router in routers:
            row = [sanitize_tsv_value(router.get(col, "")) for col in ROUTER_COLUMNS]
            writer.writerow(row)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export Bash-friendly deployment tables from topology JSON.")
    parser.add_argument("topology_file", help="Path to topology JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default="routers.tsv",
        help="Output TSV path (default: routers.tsv)",
    )
    args = parser.parse_args()

    export_router_tsv(args.topology_file, args.output)
    print(f"Router TSV written to: {args.output}")


if __name__ == "__main__":
    main()
