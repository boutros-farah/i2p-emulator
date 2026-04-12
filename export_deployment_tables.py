"""Export router deployment tables from a topology JSON file.

This exporter intentionally preserves the existing router TSV schema so that
the current deployment script and GUI remain compatible during the Branch 2
runtime-addressing migration.

Important design note
---------------------
The router TSV already carries the *real* runtime deployment fields:

- cidr
- router_ip
- gateway_ip

After Branch 2, those fields continue to represent the actual runtime network
addresses used by the emulator. No parallel "public_ip" mirror column is added
here because that would create a dual-address export schema and would require
additional changes in the deployment script before they are needed.

If richer addressing metadata is required later (for example allocator group or
policy tags), it should be introduced together with the setup-script TSV header
update so deployment stays low-regression.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

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
    """Convert any value into a TSV-safe string."""
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)

    return text.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()


def _validate_router_row_shape(router: Dict[str, Any]) -> None:
    """Ensure every exported router row contains the expected deployment keys."""
    missing = [column for column in ROUTER_COLUMNS if column not in router]
    if missing:
        raise ValueError(
            "Expanded router record is missing required export column(s): "
            + ", ".join(missing)
        )


def _iter_router_rows(routers: Iterable[Dict[str, Any]]) -> Iterable[List[str]]:
    """Yield sanitized TSV rows in the deployment header order."""
    for router in routers:
        _validate_router_row_shape(router)
        yield [sanitize_tsv_value(router.get(column, "")) for column in ROUTER_COLUMNS]


def export_router_tsv(topology_file: str, output_tsv: str) -> None:
    """Export router deployment rows from a topology JSON file to TSV."""
    manifest = build_manifest(topology_file)
    routers = manifest.get("routers", [])
    if not isinstance(routers, list):
        raise ValueError("Manifest 'routers' payload must be a list.")

    out_path = Path(output_tsv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(ROUTER_COLUMNS)
        for row in _iter_router_rows(routers):
            writer.writerow(row)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Export Bash-friendly router deployment tables from topology JSON."
    )
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
