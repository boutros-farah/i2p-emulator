# I2P Emulator Final Project Status

## Project purpose

This repository contains a controlled I2P testnet emulator for repeatable network experiments. It is intended for real testing, measurement, churn simulation, path analysis, and authoritative exact-hop validation in an isolated lab environment.

The emulator is not only a visual topology demo. It creates Linux network namespaces, assigns router IP addresses, builds subnet bridges, starts real I2P router instances, collects measurements, runs churn scenarios, and imports authoritative tunnel-path events emitted by a patched I2P router.

## Final repository state

Final emulator branch:

```text
main
```

Important merged work:

```text
Branch 5: authoritative exact-hop truth lifecycle
Branch 6: location-based public IPv4 addressing mode
Branch 7: professional operator-facing naming cleanup
```

The patched router source is kept separately:

```text
Repository: https://github.com/boutros-farah/i2p.i2p.git
Branch: authoritative-hop-writer
```

The emulator repository contains the deployment, GUI, topology, measurement, import, normalization, and analysis logic. The patched router repository contains the Java router modification that emits authoritative tunnel snapshots.

## Core capabilities

The final emulator supports:

- isolated multi-router I2P testnet deployment;
- one Linux network namespace per router;
- topology-defined subnets and bridges;
- configurable router counts, floodfill routers, countries, cities, and map positions;
- location-based public IPv4 emulation;
- stock-like fixed tunnel policy defaults;
- GUI-based deployment and operation;
- measurement probes and scenario execution;
- churn testing;
- observed path-history analytics;
- Java-router authoritative exact-hop truth capture;
- authoritative truth import, normalization, and path-change detection;
- clean exportable JSON, JSONL, CSV, and report-oriented outputs.

## Addressing model

The final default topology uses:

```text
public-any-location
```

This is a location-aware public IPv4 emulation mode for isolated lab testing.

In this mode:

- routers receive public-style IPv4 addresses as their actual Linux namespace interface IPs;
- I2P router configuration uses the same addresses for NTCP and UDP transport host settings;
- GUI and deployment tables display the same runtime addresses;
- public-style addresses are selected according to configured topology location;
- multiple routers may exist inside the same topology subnet;
- different topology subnets are placed in different `/16` address families where possible.

Validated example:

```text
Subnet LB-1: 45.10.1.0/29
  Router 1: 45.10.1.2
  Router 2: 45.10.1.3
  Router 3: 45.10.1.4

Subnet DE-1: 91.80.1.0/29
  Router 4: 91.80.1.2
  Router 5: 91.80.1.3

Subnet FR-1: 185.20.1.0/29
  Router 6: 185.20.1.2
  Router 7: 185.20.1.3
```

This mode is not cosmetic. The public-style addresses are assigned to router namespaces and written into router transport configuration.

## Important addressing note

`public-any-location` is an isolated-lab emulation mode. It uses public-style globally routable IPv4 ranges inside the local emulator, but it does not claim ownership of those public ranges on the real Internet.

For a production-grade or institution-approved deployment, a stricter future mode can be added where the user supplies assigned public CIDRs from a university, lab, ISP, or cloud provider.

## Subnet and `/16` behavior

The emulator uses small topology subnets such as `/29` because they are efficient for isolated router groups. A `/29` subnet gives enough usable host addresses for one gateway and several routers.

The stock-like I2P concern is different from the Linux subnet size. I2P peer selection considers IP-family diversity, especially the `/16` address family. For this reason, the public-address topology keeps different topology subnets in different `/16` buckets where possible.

Example:

```text
LB-1: 45.10.1.0/29      -> 45.10.0.0/16 bucket
DE-1: 91.80.1.0/29      -> 91.80.0.0/16 bucket
FR-1: 185.20.1.0/29     -> 185.20.0.0/16 bucket
```

Multiple routers are allowed inside the same topology subnet. Different topology subnets should avoid sharing the same `/16` bucket when the goal is stock-like peer-selection behavior.

## Authoritative exact-hop truth

The project separates observed path history from authoritative truth.

Observed path history:

```text
~/i2p-gui/logs/hop_history/
```

Authoritative exact-hop truth:

```text
~/i2p-gui/logs/hop_truth/
```

Only Java-router authoritative records should be treated as real exact-hop tunnel truth:

```text
source_mode = java-router-authoritative
truth_level = ground-truth
```

The emulator should not infer exact-hop truth from observed path records.

## Patched router source

The authoritative exact-hop capture requires the patched router source branch:

```text
Repository: https://github.com/boutros-farah/i2p.i2p.git
Branch: authoritative-hop-writer
```

Primary patched files:

```text
router/java/src/net/i2p/router/tunnel/pool/AuthoritativeHopEventWriter.java
router/java/src/net/i2p/router/tunnel/pool/TunnelPool.java
```

The patched router writes Java-authoritative tunnel event rows to each router data directory:

```text
r*/data/authoritative/authoritative-hop-events.jsonl
```

Important emitted fields include:

```text
ts_utc
event_type
source_mode
truth_level
local_router_hash
direction
tunnel_kind
destination_hash
hop_count
gateway_hash
endpoint_hash
far_end_hash
hop_hashes
pool_name
```

## Validated public-IP testnet

A 7-router public-IP testnet was validated with:

```text
Testnet directory: /home/ubuntu/i2p-testnet-7
Routers: 7
Floodfill routers: 2
Address policy: public-any-location
```

Validation confirmed:

- all 7 routers running;
- namespace fabric active;
- public-style namespace interface IPs assigned;
- I2P router configs using those IPs for NTCP and UDP;
- cross-subnet ping connectivity working;
- router services listening on expected ports;
- patched router jar installed;
- authoritative event files written by all routers.

Validated namespace addresses:

```text
Router 1: 45.10.1.2/29
Router 2: 45.10.1.3/29
Router 3: 45.10.1.4/29
Router 4: 91.80.1.2/29
Router 5: 91.80.1.3/29
Router 6: 185.20.1.2/29
Router 7: 185.20.1.3/29
```

Validated router transport configuration:

```text
Router 1: i2np.ntcp.host=45.10.1.2, i2np.udp.host=45.10.1.2
Router 2: i2np.ntcp.host=45.10.1.3, i2np.udp.host=45.10.1.3
Router 3: i2np.ntcp.host=45.10.1.4, i2np.udp.host=45.10.1.4
Router 4: i2np.ntcp.host=91.80.1.2, i2np.udp.host=91.80.1.2
Router 5: i2np.ntcp.host=91.80.1.3, i2np.udp.host=91.80.1.3
Router 6: i2np.ntcp.host=185.20.1.2, i2np.udp.host=185.20.1.2
Router 7: i2np.ntcp.host=185.20.1.3, i2np.udp.host=185.20.1.3
```

## Clean authoritative dataset validation

After archiving the old mixed `hop_truth` workspace, the Java-authoritative pipeline was rerun cleanly.

Final clean dataset summary:

```text
Imported Java authoritative rows: 216
Normalized canonical truth events: 598
Router count: 7
Tunnel count: 215
Source modes: java-router-authoritative only
Change events: 144
Streams: 30
```

This confirms that the final public-IP testnet produced a clean Java-only authoritative exact-hop dataset.

## Main workflow

Typical workflow:

```text
1. Define or load topology.
2. Generate router and subnet deployment tables.
3. Deploy the isolated testnet.
4. Start routers and verify namespace fabric.
5. Run measurements and scenarios.
6. Install the patched router jar when authoritative truth capture is required.
7. Import Java authoritative truth.
8. Normalize exact-hop truth.
9. Run path-change detection.
10. Analyze results in the GUI and exported reports.
```

## Important operational note

The setup script may reinstall the base I2P router into:

```text
~/i2p
```

When that happens, the stock `router.jar` can replace the patched authoritative-hop router jar. Before authoritative truth capture, verify and reinstall the patched router jar if needed:

```bash
jar tf ~/i2p/lib/router.jar | grep AuthoritativeHopEventWriter
```

If the class is missing:

```bash
cp ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
```

Then restart the testnet.

## Key emulator files

```text
working-gui.py
setup-i2p-emulator.sh
topology_model.py
topology.sample.json
topology.public-any-location.template.json
build_topology_manifest.py
export_deployment_tables.py
export_subnet_tables.py
import_java_authoritative_truth.py
phase5_backend.py
run_phase5c_scan.py
run_phase5b_normalization.py
run_phase5d_change_detection.py
README.md
EMULATOR_SETUP.md
```

## Files that should not be committed

Generated runtime files should not be committed to the repository.

Do not commit:

```text
routers.generated.tsv
subnets.generated.tsv
routers.public-any-location.tsv
subnets.public-any-location.tsv
~/i2p-testnet-*
~/i2p-gui/logs/
exact-hop-truth.jsonl
exact-hop-truth.json
exact-hop-change-events.jsonl
exact-hop-change-events.json
authoritative-hop-events.jsonl
```

Only source code, documentation, topology templates, and reusable scripts should be committed.

## Final report positioning

The project should be presented as:

```text
A controlled I2P emulator and measurement platform for isolated testnet deployment, public-address behavior emulation, churn testing, tunnel-path analysis, and Java-router authoritative exact-hop validation.
```

Avoid describing it as only a GUI, demo, prototype, or visualization tool.

## Remaining optional improvements

The current project is ready for report work. Optional future improvements include:

- adding a stricter `public-owned` addressing mode for institution-assigned public CIDRs;
- adding a GUI action to archive/reset the authoritative truth workspace;
- adding automated CI smoke tests for topology validation and syntax checks;
- adding release notes per major milestone;
- adding more visual path-change diagrams in the GUI;
- adding a report-ready validation bundle exporter.
