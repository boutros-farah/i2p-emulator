"""Topology validation and expansion helpers for the I2P emulator.

This module keeps topology parsing, validation, and router-record expansion
separate from deployment and GUI logic so future contributors can extend the
builder pipeline without touching runtime code.
"""

from __future__ import annotations

import ipaddress
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


class TopologyError(Exception):
    """Raised when the topology file is invalid."""


RFC1918_NETWORKS: tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

SPECIAL_PURPOSE_POOL_PRESETS: Dict[str, tuple[ipaddress.IPv4Network, ...]] = {
    "shared": (ipaddress.ip_network("100.64.0.0/10"),),
    "benchmark": (ipaddress.ip_network("198.18.0.0/15"),),
    "documentation": (
        ipaddress.ip_network("192.0.2.0/24"),
        ipaddress.ip_network("198.51.100.0/24"),
        ipaddress.ip_network("203.0.113.0/24"),
    ),
}
SPECIAL_PURPOSE_POOL_PRESETS["all"] = (
    SPECIAL_PURPOSE_POOL_PRESETS["shared"]
    + SPECIAL_PURPOSE_POOL_PRESETS["benchmark"]
    + SPECIAL_PURPOSE_POOL_PRESETS["documentation"]
)

PUBLIC_ANY_LOCATION_MODE = "public-any-location"
ADDRESSING_MODES = {
    "legacy-private",
    "special-purpose-non-rfc1918",
    "mixed-lab",
    PUBLIC_ANY_LOCATION_MODE,
}

DEFAULT_PUBLIC_ANY_LOCATION_POOLS: Dict[str, tuple[ipaddress.IPv4Network, ...]] = {
    # These are public-looking IPv4 pools for isolated lab emulation only.
    # They are intentionally explicit so reviewers can see that public-any-location
    # is an emulation mode, not an ownership claim over Internet address space.
    "LB": (ipaddress.ip_network("45.0.0.0/12"),),
    "DE": (ipaddress.ip_network("91.80.0.0/12"),),
    "FR": (ipaddress.ip_network("185.16.0.0/12"),),
    "NL": (ipaddress.ip_network("31.16.0.0/12"),),
    "US": (ipaddress.ip_network("23.16.0.0/12"),),
    "GB": (ipaddress.ip_network("51.16.0.0/12"),),
}

DEFAULT_ADDRESSING_POLICY: Dict[str, Any] = {
    "mode": "legacy-private",
    "pool": "rfc1918",
    "allocator": "manual",
    "strict": True,
}


@dataclass(frozen=True)
class RouterRecord:
    id: int
    name: str
    country: str
    country_code: str
    city: str
    lat: float
    lon: float
    display_lat: float
    display_lon: float
    subnet_label: str
    cidr: str
    router_ip: str
    gateway_ip: str
    namespace: str
    bridge: str
    host_veth: str
    ns_veth: str
    floodfill: bool
    location_index: int
    subnet_index: int
    router_index_in_subnet: int


@dataclass(frozen=True)
class SubnetRecord:
    subnet_label: str
    cidr: str
    gateway_ip: str
    country: str
    country_code: str
    city: str
    bridge: str
    location_index: int
    subnet_index: int


def _require_keys(obj: Dict[str, Any], required: List[str], where: str) -> None:
    for key in required:
        if key not in obj:
            raise TopologyError(f"Missing required key '{key}' in {where}.")



def _as_nonempty_str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TopologyError(f"Expected non-empty string in {where}.")
    return value.strip()



def _as_positive_int(value: Any, where: str, minimum: int = 1) -> int:
    if not isinstance(value, int) or value < minimum:
        raise TopologyError(f"Expected integer >= {minimum} in {where}.")
    return value



def _as_bool(value: Any, where: str) -> bool:
    if isinstance(value, bool):
        return value
    raise TopologyError(f"Expected boolean value in {where}.")



def _as_float(value: Any, where: str) -> float:
    if not isinstance(value, (int, float)):
        raise TopologyError(f"Expected numeric value in {where}.")
    return float(value)



def _validate_country_code(code: str, where: str) -> str:
    code = _as_nonempty_str(code, where).upper()
    if len(code) != 2 or not code.isalpha():
        raise TopologyError(f"Country code in {where} must be a 2-letter code like 'LB' or 'DE'.")
    return code



def _parse_ipv4_network(cidr: str, where: str) -> ipaddress.IPv4Network:
    try:
        network = ipaddress.ip_network(cidr, strict=True)
    except ValueError as exc:
        raise TopologyError(f"Invalid CIDR '{cidr}' in {where}: {exc}") from exc

    if not isinstance(network, ipaddress.IPv4Network):
        raise TopologyError(f"Only IPv4 CIDRs are supported in {where}.")
    if network.prefixlen > 29:
        raise TopologyError(
            f"CIDR '{cidr}' in {where} is too small. Use /29 or larger subnet sizes so gateway and routers fit."
        )
    return network



def _network_within_any(network: ipaddress.IPv4Network, allowed: Iterable[ipaddress.IPv4Network]) -> bool:
    return any(network.subnet_of(candidate) for candidate in allowed)



def _normalize_country_name(value: str) -> str:
    return " ".join(str(value or "").split()).strip().lower()



def _is_globally_routable_public_network(network: ipaddress.IPv4Network) -> bool:
    return bool(
        network.is_global
        and not network.is_private
        and not network.is_loopback
        and not network.is_link_local
        and not network.is_multicast
        and not network.is_reserved
        and not network.is_unspecified
        and not _network_within_any(network, RFC1918_NETWORKS)
        and not _network_within_any(network, SPECIAL_PURPOSE_POOL_PRESETS["all"])
    )



def _expand_pool_spec(spec: str, where: str, *, allow_public_any: bool = False) -> List[ipaddress.IPv4Network]:
    token = _as_nonempty_str(spec, where).lower()
    if token == "rfc1918":
        return list(RFC1918_NETWORKS)
    if token in SPECIAL_PURPOSE_POOL_PRESETS:
        return list(SPECIAL_PURPOSE_POOL_PRESETS[token])

    network = _parse_ipv4_network(spec, where)
    if _network_within_any(network, SPECIAL_PURPOSE_POOL_PRESETS["all"]):
        return [network]
    if _network_within_any(network, RFC1918_NETWORKS):
        return [network]
    if allow_public_any and _is_globally_routable_public_network(network):
        return [network]

    allowed_text = "RFC1918, approved special-purpose ranges"
    if allow_public_any:
        allowed_text += ", or globally routable public IPv4 ranges"
    raise TopologyError(
        f"Pool '{spec}' in {where} is not within an allowed IPv4 pool. "
        f"Use {allowed_text}."
    )



def _as_pool_spec_list(value: Any, where: str, *, allow_empty: bool = False) -> List[str]:
    if isinstance(value, list):
        if not value and not allow_empty:
            raise TopologyError(f"Topology '{where}' must not be an empty list.")
        return [_as_nonempty_str(item, f"topology.{where}[]") for item in value]
    if value is None:
        if allow_empty:
            return []
        raise TopologyError(f"Topology '{where}' is required.")
    return [_as_nonempty_str(str(value), f"topology.{where}")]



def _normalize_location_pools(raw: Dict[str, Any]) -> Dict[str, List[ipaddress.IPv4Network]]:
    value = raw.get("location_pools")
    if value is None:
        return {code: list(networks) for code, networks in DEFAULT_PUBLIC_ANY_LOCATION_POOLS.items()}
    if not isinstance(value, dict) or not value:
        raise TopologyError("Topology 'addressing.location_pools' must be a non-empty object when provided.")

    normalized: Dict[str, List[ipaddress.IPv4Network]] = {}
    for raw_code, raw_pools in value.items():
        code = _validate_country_code(str(raw_code), f"topology.addressing.location_pools.{raw_code}")
        pool_specs = _as_pool_spec_list(raw_pools, f"addressing.location_pools.{code}")
        networks: List[ipaddress.IPv4Network] = []
        for idx, spec in enumerate(pool_specs):
            for network in _expand_pool_spec(
                spec,
                f"topology.addressing.location_pools.{code}[{idx}]",
                allow_public_any=True,
            ):
                if not _is_globally_routable_public_network(network):
                    raise TopologyError(
                        f"Pool '{network}' in topology.addressing.location_pools.{code}[{idx}] must be a "
                        "globally routable public IPv4 range for public-any-location mode."
                    )
                networks.append(network)
        if not networks:
            raise TopologyError(f"No usable public pools configured for country code '{code}'.")
        normalized[code] = networks
    return normalized



def _subnet_16_bucket(network: ipaddress.IPv4Network) -> str:
    first, second, *_ = str(network.network_address).split(".")
    return f"{first}.{second}.0.0/16"



def _normalize_addressing_policy(data: Dict[str, Any]) -> Dict[str, Any]:
    raw = data.get("addressing", DEFAULT_ADDRESSING_POLICY)
    if raw is None:
        raw = DEFAULT_ADDRESSING_POLICY
    if not isinstance(raw, dict):
        raise TopologyError("Topology 'addressing' must be an object when provided.")

    mode = str(raw.get("mode", DEFAULT_ADDRESSING_POLICY["mode"])).strip().lower()
    allocator = str(raw.get("allocator", DEFAULT_ADDRESSING_POLICY["allocator"])).strip() or "manual"
    strict = _as_bool(raw.get("strict", DEFAULT_ADDRESSING_POLICY["strict"]), "topology.addressing.strict")

    if mode not in ADDRESSING_MODES:
        raise TopologyError(
            "Topology addressing mode must be one of: " + ", ".join(sorted(ADDRESSING_MODES)) + "."
        )

    # Support both historical 'pool' and newer 'pools'. 'pools' wins when both are present.
    pool_value = raw.get("pools", raw.get("pool", DEFAULT_ADDRESSING_POLICY["pool"]))
    location_pools: Dict[str, List[ipaddress.IPv4Network]] = {}

    if mode == PUBLIC_ANY_LOCATION_MODE:
        acknowledge = _as_bool(
            raw.get("acknowledge_unassigned_public_ip_risk", False),
            "topology.addressing.acknowledge_unassigned_public_ip_risk",
        )
        if not acknowledge:
            raise TopologyError(
                "public-any-location mode requires addressing.acknowledge_unassigned_public_ip_risk=true "
                "because arbitrary public IPv4 ranges may belong to real organizations."
            )
        location_pools = _normalize_location_pools(raw)
        pool_specs = [f"{code}:{','.join(str(net) for net in nets)}" for code, nets in sorted(location_pools.items())]
        allowed_networks = [net for nets in location_pools.values() for net in nets]
    else:
        pool_specs = _as_pool_spec_list(pool_value, "addressing.pools" if "pools" in raw else "addressing.pool")
        if mode == "legacy-private" and pool_specs == ["rfc1918"]:
            allowed_networks = list(RFC1918_NETWORKS)
        elif mode == "special-purpose-non-rfc1918" and pool_specs == ["rfc1918"]:
            pool_specs = ["shared"]
            allowed_networks = list(SPECIAL_PURPOSE_POOL_PRESETS["shared"])
        else:
            allowed_networks = []
            for idx, spec in enumerate(pool_specs, start=1):
                allowed_networks.extend(_expand_pool_spec(spec, f"topology.addressing.pool[{idx - 1}]"))

    if mode == "legacy-private":
        non_private = [net for net in allowed_networks if not _network_within_any(net, RFC1918_NETWORKS)]
        if non_private:
            raise TopologyError(
                "Topology addressing mode 'legacy-private' only allows RFC1918 pools. "
                f"Found unsupported pool(s): {', '.join(str(net) for net in non_private)}."
            )
    elif mode == "special-purpose-non-rfc1918":
        invalid = [
            net
            for net in allowed_networks
            if not _network_within_any(net, SPECIAL_PURPOSE_POOL_PRESETS["all"])
            or _network_within_any(net, RFC1918_NETWORKS)
        ]
        if invalid:
            raise TopologyError(
                "Topology addressing mode 'special-purpose-non-rfc1918' only allows approved non-RFC1918 "
                f"special-purpose pools. Found unsupported pool(s): {', '.join(str(net) for net in invalid)}."
            )
    elif mode == "mixed-lab":
        invalid = [
            net
            for net in allowed_networks
            if not _network_within_any(net, RFC1918_NETWORKS)
            and not _network_within_any(net, SPECIAL_PURPOSE_POOL_PRESETS["all"])
        ]
        if invalid:
            raise TopologyError(
                "Topology addressing mode 'mixed-lab' only allows RFC1918 or approved special-purpose pools. "
                f"Found unsupported pool(s): {', '.join(str(net) for net in invalid)}."
            )
    elif mode == PUBLIC_ANY_LOCATION_MODE:
        invalid = [net for net in allowed_networks if not _is_globally_routable_public_network(net)]
        if invalid:
            raise TopologyError(
                "Topology addressing mode 'public-any-location' only allows globally routable public IPv4 pools. "
                f"Found unsupported pool(s): {', '.join(str(net) for net in invalid)}."
            )

    deduped_allowed: List[ipaddress.IPv4Network] = []
    seen = set()
    for net in allowed_networks:
        key = str(net)
        if key in seen:
            continue
        seen.add(key)
        deduped_allowed.append(net)

    subnet_16_diversity = _as_bool(
        raw.get("stocklike_subnet_16_diversity", mode == PUBLIC_ANY_LOCATION_MODE),
        "topology.addressing.stocklike_subnet_16_diversity",
    )

    return {
        "mode": mode,
        "pool": list(pool_specs),
        "allocator": allocator,
        "strict": strict,
        "allowed_networks": deduped_allowed,
        "location_pools": location_pools,
        "stocklike_subnet_16_diversity": subnet_16_diversity,
    }


def _validate_runtime_cidr_policy(
    network: ipaddress.IPv4Network,
    where: str,
    policy: Dict[str, Any],
    country_code: str | None = None,
) -> None:
    allowed_networks = list(policy.get("allowed_networks") or [])
    mode = str(policy.get("mode") or "unknown")

    if mode == PUBLIC_ANY_LOCATION_MODE:
        code = str(country_code or "").strip().upper()
        location_pools = policy.get("location_pools") or {}
        allowed_for_location = list(location_pools.get(code) or [])
        if not code or not allowed_for_location:
            known = ", ".join(sorted(location_pools.keys())) or "none"
            raise TopologyError(
                f"CIDR '{network}' in {where} uses public-any-location mode, but country code "
                f"'{code or 'unknown'}' has no configured public pool. Known codes: {known}."
            )
        if _network_within_any(network, allowed_for_location):
            return
        pool_text = ", ".join(str(net) for net in allowed_for_location)
        raise TopologyError(
            f"CIDR '{network}' in {where} is not inside the public-any-location pool for country code "
            f"'{code}'. Allowed pool(s): {pool_text}."
        )

    if allowed_networks and _network_within_any(network, allowed_networks):
        return

    pool_text = ", ".join(str(net) for net in allowed_networks) if allowed_networks else "(no allowed pools configured)"
    raise TopologyError(
        f"CIDR '{network}' in {where} is not allowed by addressing mode '{mode}'. "
        f"Allowed pool(s): {pool_text}."
    )


def _validate_subnet_capacity(network: ipaddress.IPv4Network, routers: int, where: str) -> None:
    usable_hosts = list(network.hosts())
    usable_capacity_for_routers = max(0, len(usable_hosts) - 1)
    if routers > usable_capacity_for_routers:
        raise TopologyError(
            f"{where} has {routers} routers but CIDR {network} only supports "
            f"{usable_capacity_for_routers} router IPs after reserving one gateway IP."
        )



def _validate_no_overlap(network: ipaddress.IPv4Network, seen_networks: List[ipaddress.IPv4Network], where: str) -> None:
    for existing in seen_networks:
        if network.overlaps(existing):
            raise TopologyError(
                f"CIDR '{network}' in {where} overlaps with existing subnet '{existing}'. "
                "Topology subnets must not overlap."
            )



def _compute_display_offset(
    base_lat: float,
    base_lon: float,
    spread: float,
    ordinal: int,
    total: int,
) -> tuple[float, float]:
    """
    Spread routers in the same location around the center in a small circle.
    This is for map display only, not for networking.
    """
    if total <= 1 or spread <= 0:
        return base_lat, base_lon

    angle = (2.0 * math.pi * (ordinal - 1)) / total
    lat_offset = spread * math.sin(angle)
    lon_offset = spread * math.cos(angle)

    display_lat = max(-90.0, min(90.0, base_lat + lat_offset))
    display_lon = max(-180.0, min(180.0, base_lon + lon_offset))
    return display_lat, display_lon



def load_topology_file(path: str | Path) -> Dict[str, Any]:
    topology_path = Path(path)
    if not topology_path.exists():
        raise TopologyError(f"Topology file not found: {topology_path}")

    try:
        with topology_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise TopologyError(f"Invalid JSON in topology file '{topology_path}': {exc}") from exc

    if not isinstance(data, dict):
        raise TopologyError("Topology root must be a JSON object.")
    return data



def validate_topology(data: Dict[str, Any]) -> None:
    _require_keys(data, ["locations"], "topology root")

    version = data.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise TopologyError("Topology 'version' must be an integer >= 1.")

    policy = _normalize_addressing_policy(data)

    locations = data["locations"]
    if not isinstance(locations, list) or not locations:
        raise TopologyError("Topology must contain a non-empty 'locations' list.")

    country_names_by_code: Dict[str, str] = {}
    seen_subnet_labels: set[str] = set()
    seen_networks: List[ipaddress.IPv4Network] = []
    seen_subnet_16_buckets: Dict[str, str] = {}

    for loc_idx, location in enumerate(locations, start=1):
        where_loc = f"locations[{loc_idx - 1}]"
        if not isinstance(location, dict):
            raise TopologyError(f"{where_loc} must be an object.")

        _require_keys(location, ["country", "country_code", "center", "subnets"], where_loc)

        country_name = _as_nonempty_str(location["country"], f"{where_loc}.country")
        country_code = _validate_country_code(location["country_code"], f"{where_loc}.country_code")
        country_name_norm = _normalize_country_name(country_name)

        previous_country = country_names_by_code.get(country_code)
        if previous_country is None:
            country_names_by_code[country_code] = country_name_norm
        elif previous_country != country_name_norm:
            raise TopologyError(
                f"Country code '{country_code}' is used for multiple country names in topology. "
                f"Found '{country_name}' in {where_loc}."
            )

        if "city" in location and not isinstance(location["city"], str):
            raise TopologyError(f"{where_loc}.city must be a string if provided.")

        if "map_spread" in location:
            spread = _as_float(location["map_spread"], f"{where_loc}.map_spread")
            if spread < 0:
                raise TopologyError(f"{where_loc}.map_spread must be >= 0.")

        center = location["center"]
        if not isinstance(center, dict):
            raise TopologyError(f"{where_loc}.center must be an object.")
        _require_keys(center, ["lat", "lon"], f"{where_loc}.center")

        lat = _as_float(center["lat"], f"{where_loc}.center.lat")
        lon = _as_float(center["lon"], f"{where_loc}.center.lon")

        if not (-90.0 <= lat <= 90.0):
            raise TopologyError(f"{where_loc}.center.lat must be between -90 and 90.")
        if not (-180.0 <= lon <= 180.0):
            raise TopologyError(f"{where_loc}.center.lon must be between -180 and 180.")

        subnets = location["subnets"]
        if not isinstance(subnets, list) or not subnets:
            raise TopologyError(f"{where_loc}.subnets must be a non-empty list.")

        for subnet_idx, subnet in enumerate(subnets, start=1):
            where_sub = f"{where_loc}.subnets[{subnet_idx - 1}]"
            if not isinstance(subnet, dict):
                raise TopologyError(f"{where_sub} must be an object.")

            _require_keys(subnet, ["label", "cidr", "routers", "floodfill"], where_sub)

            label = _as_nonempty_str(subnet["label"], f"{where_sub}.label")
            if label in seen_subnet_labels:
                raise TopologyError(f"Duplicate subnet label '{label}' in {where_sub}.")
            seen_subnet_labels.add(label)

            cidr = _as_nonempty_str(subnet["cidr"], f"{where_sub}.cidr")
            network = _parse_ipv4_network(cidr, f"{where_sub}.cidr")
            _validate_runtime_cidr_policy(network, f"{where_sub}.cidr", policy, country_code)
            _validate_no_overlap(network, seen_networks, f"{where_sub}.cidr")
            if policy.get("stocklike_subnet_16_diversity"):
                bucket = _subnet_16_bucket(network)
                previous_label = seen_subnet_16_buckets.get(bucket)
                if previous_label is not None:
                    raise TopologyError(
                        f"CIDR '{network}' in {where_sub}.cidr shares /16 bucket '{bucket}' with subnet "
                        f"'{previous_label}'. Stock-like subnet /16 diversity requires different topology "
                        "subnets to use different first-two-octet IP families. Multiple routers inside the "
                        "same subnet are still allowed."
                    )
                seen_subnet_16_buckets[bucket] = label
            seen_networks.append(network)

            routers = _as_positive_int(subnet["routers"], f"{where_sub}.routers", minimum=1)
            floodfill = _as_positive_int(subnet["floodfill"], f"{where_sub}.floodfill", minimum=0)

            if floodfill > routers:
                raise TopologyError(
                    f"{where_sub}.floodfill ({floodfill}) cannot exceed routers ({routers})."
                )

            _validate_subnet_capacity(network, routers, where_sub)



def _shared_subnet_bridge_name(global_subnet_index: int) -> str:
    return f"i2pbr-s{global_subnet_index}"



def expand_subnets(data: Dict[str, Any]) -> List[SubnetRecord]:
    validate_topology(data)

    subnets: List[SubnetRecord] = []
    global_subnet_index = 0
    for loc_idx, location in enumerate(data["locations"], start=1):
        country = location["country"].strip()
        country_code = location["country_code"].strip().upper()
        city = str(location.get("city", "")).strip()

        for subnet_idx, subnet in enumerate(location["subnets"], start=1):
            global_subnet_index += 1
            network = ipaddress.ip_network(str(subnet["cidr"]).strip(), strict=True)
            gateway_ip = str(next(network.hosts()))
            subnets.append(
                SubnetRecord(
                    subnet_label=str(subnet["label"]).strip(),
                    cidr=str(subnet["cidr"]).strip(),
                    gateway_ip=gateway_ip,
                    country=country,
                    country_code=country_code,
                    city=city,
                    bridge=_shared_subnet_bridge_name(global_subnet_index),
                    location_index=loc_idx,
                    subnet_index=subnet_idx,
                )
            )
    return subnets



def expand_topology(data: Dict[str, Any]) -> List[RouterRecord]:
    validate_topology(data)

    routers: List[RouterRecord] = []
    router_id = 1
    global_subnet_index = 0

    for loc_idx, location in enumerate(data["locations"], start=1):
        country = location["country"].strip()
        country_code = location["country_code"].strip().upper()
        city = str(location.get("city", "")).strip()
        lat = float(location["center"]["lat"])
        lon = float(location["center"]["lon"])
        map_spread = float(location.get("map_spread", 0.12))

        total_routers_in_location = sum(int(sub["routers"]) for sub in location["subnets"])
        location_router_ordinal = 0

        for subnet_idx, subnet in enumerate(location["subnets"], start=1):
            global_subnet_index += 1
            label = subnet["label"].strip()
            cidr = subnet["cidr"].strip()
            network = ipaddress.ip_network(cidr, strict=True)
            hosts = list(network.hosts())

            gateway_ip = str(hosts[0])
            router_count = int(subnet["routers"])
            floodfill_count = int(subnet["floodfill"])

            for router_idx_in_subnet in range(1, router_count + 1):
                location_router_ordinal += 1
                router_ip = str(hosts[router_idx_in_subnet])
                is_floodfill = router_idx_in_subnet <= floodfill_count
                display_lat, display_lon = _compute_display_offset(
                    lat, lon, map_spread, location_router_ordinal, total_routers_in_location
                )

                rid = router_id
                routers.append(
                    RouterRecord(
                        id=rid,
                        name=f"Router {rid}",
                        country=country,
                        country_code=country_code,
                        city=city,
                        lat=lat,
                        lon=lon,
                        display_lat=display_lat,
                        display_lon=display_lon,
                        subnet_label=label,
                        cidr=cidr,
                        router_ip=router_ip,
                        gateway_ip=gateway_ip,
                        namespace=f"i2pns-r{rid}",
                        bridge=_shared_subnet_bridge_name(global_subnet_index),
                        host_veth=f"i2ph{rid}",
                        ns_veth=f"i2pn{rid}",
                        floodfill=is_floodfill,
                        location_index=loc_idx,
                        subnet_index=subnet_idx,
                        router_index_in_subnet=router_idx_in_subnet,
                    )
                )
                router_id += 1

    return routers



def summarize_topology(data: Dict[str, Any]) -> Dict[str, int]:
    validate_topology(data)
    expanded = expand_topology(data)

    return {
        "locations": len(data["locations"]),
        "subnets": sum(len(location["subnets"]) for location in data["locations"]),
        "routers": len(expanded),
        "floodfill": sum(1 for router in expanded if router.floodfill),
    }



def topology_debug_report(data: Dict[str, Any]) -> str:
    summary = summarize_topology(data)
    policy = _normalize_addressing_policy(data)
    lines = [
        "Topology summary",
        "================",
        f"Locations : {summary['locations']}",
        f"Subnets   : {summary['subnets']}",
        f"Routers   : {summary['routers']}",
        f"Floodfill : {summary['floodfill']}",
        "",
        "Address policy",
        "--------------",
        f"Mode      : {policy['mode']}",
        f"Pool(s)   : {', '.join(policy['pool'])}",
        f"Allocator : {policy['allocator']}",
        f"Strict    : {'true' if policy['strict'] else 'false'}",
        f"Subnet /16 diversity : {'required' if policy.get('stocklike_subnet_16_diversity') else 'not required'}",
        "",
        "Location breakdown",
        "------------------",
    ]

    for location in data["locations"]:
        location_router_count = sum(int(sub["routers"]) for sub in location["subnets"])
        location_ff_count = sum(int(sub["floodfill"]) for sub in location["subnets"])
        city = location.get("city", "")
        city_suffix = f" ({city})" if city else ""
        lines.append(
            f"{location['country']} [{location['country_code'].upper()}]{city_suffix}: "
            f"{len(location['subnets'])} subnets, {location_router_count} routers, {location_ff_count} floodfill"
        )

    return "\n".join(lines)



def router_records_as_dicts(records: List[RouterRecord]) -> List[Dict[str, Any]]:
    return [asdict(r) for r in records]



def subnet_records_as_dicts(records: List[SubnetRecord]) -> List[Dict[str, Any]]:
    return [asdict(r) for r in records]



def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate and expand an emulator topology JSON file.")
    parser.add_argument("topology_file", help="Path to topology JSON file")
    parser.add_argument("--print-routers", action="store_true", help="Print expanded router records as JSON")
    parser.add_argument("--debug-report", action="store_true", help="Print formatted topology debug report")
    parser.add_argument("--print-subnets", action="store_true", help="Print expanded subnet records as JSON")
    args = parser.parse_args()

    data = load_topology_file(args.topology_file)

    if args.debug_report:
        print(topology_debug_report(data))
    else:
        summary = summarize_topology(data)
        print("Topology summary")
        print("================")
        print(f"Locations : {summary['locations']}")
        print(f"Subnets   : {summary['subnets']}")
        print(f"Routers   : {summary['routers']}")
        print(f"Floodfill : {summary['floodfill']}")

    if args.print_routers:
        print()
        print(json.dumps(router_records_as_dicts(expand_topology(data)), indent=2))

    if args.print_subnets:
        print()
        print(json.dumps(subnet_records_as_dicts(expand_subnets(data)), indent=2))


if __name__ == "__main__":
    main()
