"""Export topology-derived deployment TSV files.

This module preserves the existing subnet TSV schema so the current deployment
script remains compatible during the Branch 2 runtime-addressing migration.

Important design note
---------------------
The exported subnet TSV already carries the real runtime deployment fields:

- subnet_label
- cidr
- gateway_ip

After Branch 2, those fields continue to represent the actual runtime subnet
configuration used by the emulator. We intentionally avoid adding parallel
"public" mirror fields here until the setup script is updated in lockstep, so
deployment stays low-regression and professionally staged.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

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


def _validate_subnet_row_shape(row: Dict[str, Any]) -> None:
    """Ensure every exported subnet row contains the expected deployment keys."""
    missing = [column for column in SUBNET_COLUMNS if column not in row]
    if missing:
        raise ValueError(
            "Expanded subnet record is missing required export column(s): "
            + ", ".join(missing)
        )


def build_subnet_rows(topology_file: str) -> List[Dict[str, Any]]:
    """Build normalized subnet rows from a topology JSON file."""
    manifest = build_manifest(topology_file)
    rows = manifest.get("subnets", [])
    if not isinstance(rows, list):
        raise ValueError("Manifest 'subnets' payload must be a list.")
    for row in rows:
        _validate_subnet_row_shape(row)
    return rows


def _iter_subnet_rows(rows: Iterable[Dict[str, Any]]) -> Iterable[List[str]]:
    """Yield sanitized subnet TSV rows in header order."""
    for row in rows:
        yield [sanitize_tsv_value(row.get(column, "")) for column in SUBNET_COLUMNS]


def export_subnet_tsv(topology_file: str, output_tsv: str) -> None:
    """Export subnet deployment rows from a topology JSON file to TSV."""
    rows = build_subnet_rows(topology_file)
    out_path = Path(output_tsv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(SUBNET_COLUMNS)
        for row in _iter_subnet_rows(rows):
            writer.writerow(row)


def export_combined_tables(topology_file: str, routers_out: str | None, subnets_out: str) -> List[str]:
    """Export router and subnet TSVs together for GUI/deployment compatibility."""
    outputs: List[str] = []
    if routers_out:
        export_router_tsv(topology_file, routers_out)
        outputs.append(f"Routers TSV written to: {routers_out}")
    export_subnet_tsv(topology_file, subnets_out)
    outputs.append(f"Subnets TSV written to: {subnets_out}")
    return outputs


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Export deployment TSV files from topology JSON."
    )
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
        help="Output subnet TSV path (default: subnets.tsv)",
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
