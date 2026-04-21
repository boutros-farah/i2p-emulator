# I2P Testnet Emulator

A controlled desktop-operated **I2P testnet emulator** for isolated deployment, monitoring, measurement, churn testing, topology analysis, public-address behavior emulation, and authoritative exact-hop validation.

This project is intended for real controlled testing, not only visualization. It creates Linux network namespaces, assigns router IPs, builds subnet bridges, starts real I2P router instances, runs measurements and churn scenarios, and imports authoritative tunnel-path events emitted by a patched I2P router.

---

## Repository overview

The project uses two repositories.

### Emulator repository

```text
https://github.com/boutros-farah/i2p-emulator.git
```

Final working branch:

```text
main
```

This repository contains:

- GUI application;
- deployment script;
- topology model and validation tools;
- router/subnet table exporters;
- measurement and scenario tooling;
- observed path analytics;
- authoritative truth import, normalization, and change-detection workers;
- documentation.

### Patched I2P router repository

```text
https://github.com/boutros-farah/i2p.i2p.git
branch: authoritative-hop-writer
```

This fork contains the Java router patch that emits authoritative tunnel snapshots from inside the I2P router. The emulator imports those snapshots as ground-truth exact-hop data.

Primary patched router files:

```text
router/java/src/net/i2p/router/tunnel/pool/AuthoritativeHopEventWriter.java
router/java/src/net/i2p/router/tunnel/pool/TunnelPool.java
```

---

## What the emulator supports

The final emulator supports:

- isolated I2P routers in Linux network namespaces;
- topology-defined Linux bridges and subnets;
- configurable countries, cities, coordinates, routers, and floodfill routers;
- location-based public IPv4 emulation;
- stock-like fixed tunnel policy defaults;
- GUI-based deployment and operations;
- measurement probes;
- churn/scenario testing;
- observed path-history analytics;
- Java-router authoritative exact-hop truth capture;
- canonical truth normalization;
- path-change detection;
- exportable output files for reports and supervisor review.

---

## Addressing model

The final default topology uses:

```text
public-any-location
```

This is a location-aware public IPv4 emulation mode for isolated lab testing.

In this mode:

- routers receive public-style IPv4 addresses as their actual Linux namespace interface IPs;
- router configuration uses those same addresses for NTCP and UDP transport settings;
- generated router/subnet tables contain those addresses;
- GUI views and console URLs show the same runtime addresses;
- public-style pools are selected from the configured topology location;
- multiple routers may exist inside the same topology subnet;
- different topology subnets are kept in different `/16` address families where possible.

Validated example:

```text
LB-1: 45.10.1.0/29
  Router 1: 45.10.1.2
  Router 2: 45.10.1.3
  Router 3: 45.10.1.4

DE-1: 91.80.1.0/29
  Router 4: 91.80.1.2
  Router 5: 91.80.1.3

FR-1: 185.20.1.0/29
  Router 6: 185.20.1.2
  Router 7: 185.20.1.3
```

This is not cosmetic. The public-style addresses are assigned to router namespace interfaces and written into the router transport configuration.

Important note: `public-any-location` is an isolated-lab emulation mode. It does not claim ownership of arbitrary public IPv4 ranges on the real Internet. Keep it isolated unless a real public block is assigned to the lab.

---

## Stock-like `/16` diversity

The emulator uses small Linux subnets such as `/29` for efficient router grouping. A `/29` subnet can hold one gateway and several router hosts, which is suitable for compact testnet subnets.

The stock-like I2P concern is different: I2P peer selection considers IP-family diversity, especially `/16` address families. For stock-like testing, different topology subnets should avoid sharing the same first-two-octet `/16` bucket.

Example:

```text
LB-1: 45.10.1.0/29      -> 45.10.0.0/16
DE-1: 91.80.1.0/29      -> 91.80.0.0/16
FR-1: 185.20.1.0/29     -> 185.20.0.0/16
```

Multiple routers inside one topology subnet are allowed.

---

## Truth-boundary rule

The emulator separates observed path history from authoritative exact-hop truth.

Observed path history:

```text
~/i2p-gui/logs/hop_history/
```

Authoritative exact-hop truth:

```text
~/i2p-gui/logs/hop_truth/
```

Only Java-router authoritative records should be treated as real exact-hop truth:

```text
source_mode = java-router-authoritative
truth_level = ground-truth
```

Observed path records are useful for analysis and comparison, but they are not authoritative exact-hop truth. The emulator should not fabricate exact-hop truth from observed surface data.

---

## Main workflow

Typical workflow:

```text
1. Define or load topology.
2. Generate router and subnet deployment tables.
3. Deploy the isolated testnet.
4. Verify namespace fabric and router status.
5. Run measurements or scenarios.
6. Install the patched router jar when authoritative truth capture is required.
7. Import Java authoritative truth.
8. Normalize canonical exact-hop truth.
9. Run path-change detection.
10. Review GUI views and exported outputs.
```

---

## Important files

```text
working-gui.py                                  Main PyQt GUI
setup-i2p-emulator.sh                          Testnet deployment script
topology_model.py                               Topology validation and expansion
topology.sample.json                            Default public-any-location topology
topology.public-any-location.template.json      Public-address topology template
build_topology_manifest.py                      Topology manifest builder
export_deployment_tables.py                     Router deployment table exporter
export_subnet_tables.py                         Router/subnet TSV exporter
import_java_authoritative_truth.py              Java authoritative import adapter
phase5_backend.py                               Authoritative truth backend utilities
run_phase5c_scan.py                             Import/scan worker
run_phase5b_normalization.py                    Normalization worker
run_phase5d_change_detection.py                 Change-detection worker
README.md                                       Main project documentation
EMULATOR_SETUP.md                               Reproducible setup guide
PROJECT_STATUS.md                               Final validation/status summary
```

---

## Fresh setup

Use:

```text
EMULATOR_SETUP.md
```

That guide covers:

- installing prerequisites;
- cloning the emulator repo;
- cloning the patched I2P router fork;
- building the patched router;
- deploying the emulator;
- installing the patched `router.jar`;
- running the GUI;
- importing Java authoritative truth;
- normalizing exact-hop truth;
- running change detection;
- validating outputs.

---

## Quick validation commands

Validate topology:

```bash
cd ~/Desktop/i2p_emulator
python3 topology_model.py topology.sample.json --debug-report
python3 topology_model.py topology.public-any-location.template.json --debug-report
```

Generate deployment tables:

```bash
python3 export_subnet_tables.py topology.sample.json \
  --routers-out routers.generated.tsv \
  --subnets-out subnets.generated.tsv
```

Deploy:

```bash
sudo ./setup-i2p-emulator.sh \
  --routers-tsv routers.generated.tsv \
  --subnets-tsv subnets.generated.tsv \
  --yes
```

Check status:

```bash
cd ~/i2p-testnet-7
./manage-testnet.sh status
./manage-testnet.sh netmap
```

Verify namespace IPs:

```bash
for n in 1 2 3 4 5 6 7; do
  echo "===== Router $n ====="
  sudo ip netns exec i2pns-r$n ip -4 addr show scope global
done
```

Verify router transport configuration:

```bash
cd ~/i2p-testnet-7

for n in 1 2 3 4 5 6 7; do
  echo "===== Router $n ====="
  grep -E 'i2np\.ntcp\.host|i2np\.udp\.host|i2np\.ntcp\.port|i2np\.udp\.port|routerconsole\.port' \
    r$n/config/router.config
done
```

---

## Authoritative exact-hop workflow

Build the patched router:

```bash
cd ~/src/i2p.i2p
git checkout authoritative-hop-writer

export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"

ant buildRouter
```

Install patched router jar:

```bash
cp ~/i2p/lib/router.jar ~/i2p/lib/router.jar.backup.$(date +%Y%m%d_%H%M%S)
cp ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
```

Verify the patched class exists:

```bash
jar tf ~/i2p/lib/router.jar | grep AuthoritativeHopEventWriter
```

Restart the testnet:

```bash
cd ~/i2p-testnet-7
./manage-testnet.sh restart
```

Check raw authoritative events:

```bash
find ~/i2p-testnet-7/r*/data/authoritative \
  -maxdepth 1 \
  -type f \
  -name 'authoritative-hop-events.jsonl' | sort
```

Import and process truth:

```bash
cd ~/Desktop/i2p_emulator

python3 import_java_authoritative_truth.py --testnet-base ~/i2p-testnet-7
python3 run_phase5b_normalization.py
python3 run_phase5d_change_detection.py
```

Validate outputs:

```bash
ls -lh ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl \
       ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.json \
       ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl \
       ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.json

grep -n "java-router-authoritative" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head
head -n 10 ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl
```

---

## Clean Java-authoritative-only dataset

If old manual or observed records exist, archive the previous truth workspace and rebuild it from Java-router truth only:

```bash
stamp=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p ~/i2p-gui/logs/hop_truth_archive

if [ -d ~/i2p-gui/logs/hop_truth ]; then
  mv ~/i2p-gui/logs/hop_truth ~/i2p-gui/logs/hop_truth_archive/hop_truth_$stamp
fi

mkdir -p ~/i2p-gui/logs/hop_truth/{raw,imports,events,summaries}

cd ~/Desktop/i2p_emulator
python3 import_java_authoritative_truth.py --testnet-base ~/i2p-testnet-7
python3 run_phase5b_normalization.py
python3 run_phase5d_change_detection.py
```

Expected clean source modes:

```text
java-router-authoritative only
```

---

## GUI workflow

Start the GUI:

```bash
cd ~/Desktop/i2p_emulator
python3 working-gui.py
```

Useful GUI areas:

```text
Measurements -> Path Records -> Overview -> Authoritative Exact-Hop Truth
Measurements -> Path Records -> Ingestion -> Change Detection
Measurements -> Path Analysis -> Overview
Measurements -> Path Analysis -> Observed Path Comparison
```

The heavy authoritative workflow should run through worker scripts, not inline in the GUI.

---

## Validated final public-IP testnet

The final validation run confirmed:

```text
Testnet directory: /home/ubuntu/i2p-testnet-7
Routers: 7
Floodfill routers: 2
Address policy: public-any-location
```

Validated results:

```text
Imported Java authoritative rows: 216
Normalized canonical truth events: 598
Router count: 7
Tunnel count: 215
Source modes: java-router-authoritative only
Change events: 144
Streams: 30
```

---

## Repository hygiene

Do not commit generated runtime files:

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

Commit only source code, documentation, topology templates, and reusable scripts.

---

## Report positioning

Use this description in the report:

```text
A controlled I2P emulator and measurement platform for isolated testnet deployment, public-address behavior emulation, churn testing, tunnel-path analysis, and Java-router authoritative exact-hop validation.
```

Avoid presenting the project as only a GUI, demo, prototype, or visualization.
