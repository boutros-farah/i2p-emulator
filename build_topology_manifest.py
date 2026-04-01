"""Build an expanded topology manifest from a topology JSON file."""

from __future__ import annotations

from typing import Any, Dict

from topology_model import (
    expand_subnets,
    expand_topology,
    load_topology_file,
    router_records_as_dicts,
    subnet_records_as_dicts,
    summarize_topology,
    validate_topology,
)


def build_manifest(topology_file: str) -> Dict[str, Any]:
    """Build a normalized manifest for deployment tooling and supervisor review."""
    data = load_topology_file(topology_file)
    validate_topology(data)
    routers = expand_topology(data)
    subnets = expand_subnets(data)
    return {
        "topology": data,
        "summary": summarize_topology(data),
        "routers": router_records_as_dicts(routers),
        "subnets": subnet_records_as_dicts(subnets),
    }


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build expanded topology manifest from topology JSON.")
    parser.add_argument("topology_file", help="Path to topology JSON file")
    args = parser.parse_args()

    manifest = build_manifest(args.topology_file)
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()
