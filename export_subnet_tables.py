"""Export topology-derived deployment TSV files.

This module remains compatible with the GUI's current behavior, which invokes
it as the combined exporter and passes both ``--routers-out`` and
``--subnets-out``. It can also be used on its own to export only the subnet
TSV when desired.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from build_topology_manifest import build_manifest
from export_deployment_tables import export_router_tsv


SUBNET_COLUMNS: List[str] = [
    "subnet_label",
    "cidr",
    "gateway_ip",
    "country",
    "country_code",
    "city",
    "bridge",
]


def sanitize_tsv_value(value: Any) -> str:
    """Convert any value into a TSV-safe string."""
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return text.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()


def build_subnet_rows(topology_file: str) -> List[Dict[str, Any]]:
    manifest = build_manifest(topology_file)
    return list(manifest.get("subnets", []))


def export_subnet_tsv(topology_file: str, output_tsv: str) -> None:
    rows = build_subnet_rows(topology_file)
    out_path = Path(output_tsv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(SUBNET_COLUMNS)
        for row in rows:
            writer.writerow([sanitize_tsv_value(row.get(column, "")) for column in SUBNET_COLUMNS])


def export_combined_tables(topology_file: str, routers_out: str | None, subnets_out: str) -> List[str]:
    outputs: List[str] = []
    if routers_out:
        export_router_tsv(topology_file, routers_out)
        outputs.append(f"Routers TSV written to: {routers_out}")
    export_subnet_tsv(topology_file, subnets_out)
    outputs.append(f"Subnets TSV written to: {subnets_out}")
    return outputs


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export subnet deployment tables from topology JSON.")
    parser.add_argument("topology_file", help="Path to topology JSON file")
    parser.add_argument(
        "--routers-out",
        default=None,
        help="Optional router TSV path. When provided, a router TSV is exported too for GUI compatibility.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output TSV path (default: subnets.tsv)",
    )
    parser.add_argument(
        "--subnets-out",
        default=None,
        help="Optional explicit subnet TSV path. Takes precedence over --output.",
    )
    args = parser.parse_args()

    subnets_out = args.subnets_out or args.output or "subnets.tsv"
    for line in export_combined_tables(args.topology_file, args.routers_out, subnets_out):
        print(line)


if __name__ == "__main__":
    main()
