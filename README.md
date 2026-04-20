# I2P Testnet Emulator

A professional desktop-controlled **I2P testnet emulator** for deployment, monitoring, measurement, churn testing, tunnel-path analysis, authoritative exact-hop truth capture, and scenario-level analytics.

This project is intended for **real controlled testing**, not just a visual demo. It combines a deployment script, topology tooling, a PyQt GUI, measurement runners, path-history analytics, and an authoritative router-truth workflow into one repeatable lab environment.

---

## Repositories and branches

This project has two repositories because the authoritative exact-hop feature needs both emulator-side tooling and a patched I2P router source.

### Emulator repository

```text
https://github.com/boutros-farah/i2p-emulator.git
```

Recommended Branch 5 branch:

```text
branch5-authoritative-hop-truth-lifecycle
```

This repository contains the emulator GUI, deployment script, topology tooling, measurement logic, path-record ingestion, normalization, change-detection helpers, and documentation.

### Patched router source repository

```text
https://github.com/boutros-farah/i2p.i2p.git
```

Required router patch branch:

```text
authoritative-hop-writer
```

This repository is a fork of the I2P router source. The branch adds an authoritative tunnel snapshot writer inside the router so the emulator can capture real creator-side tunnel paths instead of inferring them from observed surfaces.

---

## What this emulator does

At a high level, the emulator provides:

- isolated multi-router I2P testnet deployment
- namespace/subnet-based router isolation
- GUI-based fleet control
- topology-driven deployment
- baseline and post-churn measurement runs
- churn and scenario testing
- map-based router visualization
- long-term measurement analytics
- observed path-history analytics
- authoritative exact-hop truth capture
- authoritative path-change detection
- exportable result files for reports and supervisor review

Once the environment is installed correctly, the intended daily workflow is GUI-driven.

---

## Validated milestone summary

### Branch 1 — stock-like tunnel policy

The emulator was aligned to a fixed stock-like tunnel policy:

- tunnel length = 3
- length variance = 0
- tunnel quantity = 2
- backup quantity = 0

This gives the testnet predictable tunnel behavior for controlled experiments.

### Branch 2 — runtime non-RFC1918 addressing

The emulator supports topology-driven runtime addressing using a lab-safe special-purpose non-RFC1918 range.

The current default architecture uses:

```text
100.64.0.0/10
```

This is used inside the isolated emulator environment. Map placement is not driven by IP geolocation; map placement comes from explicit topology metadata.

### Branch 3 — observed path history

Branch 3 improved the observed path-history side of the project.

Observed path history is useful for trend analysis and comparison, but it is **not authoritative exact-hop truth**.

Observed data belongs under:

```text
~/i2p-gui/logs/hop_history/
```

### Branch 4 — GUI/professional cleanup

Branch 4 focused on layout, wording, and operator usability improvements so the GUI is easier to use for real testing.

### Branch 5 — authoritative exact-hop truth

Branch 5 adds the authoritative exact-hop workflow.

The patched router writes real creator-side tunnel snapshots to each router’s data directory. The emulator then imports, normalizes, and compares those snapshots over time.

Authoritative truth belongs under:

```text
~/i2p-gui/logs/hop_truth/
```

---

## Critical truth-boundary rule

The project intentionally separates observed path history from authoritative truth.

### Observed / surface-derived path history

Observed path history belongs under:

```text
~/i2p-gui/logs/hop_history/
```

This data is useful, but it must be treated as observed / non-authoritative.

### Authoritative exact-hop truth

Authoritative exact-hop truth belongs under:

```text
~/i2p-gui/logs/hop_truth/
```

Only records with the following fields should be treated as real router-direct exact-hop truth:

```text
source_mode = java-router-authoritative
truth_level = ground-truth
```

The emulator must not fabricate exact-hop truth from non-authoritative observations. If there is no authoritative source, exact-hop truth should stay empty instead of being guessed.

---

## Important repository files

```text
working-gui.py                         Main PyQt GUI
setup-i2p-emulator.sh                  Testnet deployment script
topology_model.py                      Topology validation/model helper
build_topology_manifest.py             Topology manifest builder
export_deployment_tables.py            Router deployment TSV exporter
export_subnet_tables.py                Subnet TSV exporter
topology.sample.json                   Example topology file
import_java_authoritative_truth.py      Java-router authoritative import adapter
phase5_backend.py                      Pure backend utilities for Phase 5 workers
run_phase5c_scan.py                    GUI worker: Java import / scan
run_phase5b_normalization.py           GUI worker: normalize authoritative truth
run_phase5d_change_detection.py        GUI worker: detect authoritative path changes
README.md                              Main project documentation
EMULATOR_SETUP.md       Reproducible setup guide
```

---

## Generated runtime paths

Common runtime outputs include:

```text
~/i2p-testnet-<N>/
~/i2p-testnet-<N>/r*/data/authoritative/authoritative-hop-events.jsonl
~/i2p-gui/logs/
~/i2p-gui/logs/measurements/
~/i2p-gui/logs/scenarios/
~/i2p-gui/logs/hop_history/
~/i2p-gui/logs/hop_truth/
~/i2p-gui/logs/hop_truth/imports/
~/i2p-gui/logs/hop_truth/events/
~/i2p-gui/logs/hop_truth/summaries/
```

Main authoritative output files:

```text
~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl
~/i2p-gui/logs/hop_truth/events/exact-hop-truth.json
~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl
~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.json
```

---

## Prerequisites

Recommended environment:

- Ubuntu Linux VM or host
- Python 3
- PyQt/PySide runtime used by the GUI environment
- Java 17 JDK
- Apache Ant
- Git
- local I2P install under `~/i2p`
- emulator testnet deployment under `~/i2p-testnet-<N>`

Install common command-line prerequisites:

```bash
sudo apt update
sudo apt install -y git openjdk-17-jdk ant python3 python3-pip
```

Depending on your GUI environment, additional Qt/PyQt packages may already be installed by the project setup or by your previous environment.

---

## Fresh clone quick start

For a complete new-machine setup, follow:

```text
EMULATOR_SETUP.md
```

That file contains copy-paste commands for:

1. cloning the emulator repo
2. cloning the patched router fork
3. building the patched router
4. installing the patched `router.jar`
5. running the GUI
6. importing authoritative truth
7. normalizing truth
8. detecting path changes
9. validating the output

---

## Manual authoritative workflow

After the patched router is installed and the testnet is running:

1. Start the GUI:

```bash
cd ~/Desktop/i2p_emulator
python3 working-gui.py
```

2. Run a measurement probe.

3. Go to:

```text
Measurements → Path Records → Ingestion
```

4. Run these in order:

```text
Scan Now
Run Normalization
Run Change Detection
```

5. Review results in:

```text
Measurements → Path Records → Overview → Tunnel Ground Truth
Measurements → Path Records → Ingestion → Change Detection
Measurements → Path Analysis → Overview
Measurements → Path Analysis → Trace Comparison
```

---

## CLI validation commands

Check authoritative output files:

```bash
ls -lh ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl \
      ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.json \
      ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl \
      ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.json
```

Check for Java-authoritative truth:

```bash
grep -n "java-router-authoritative" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head -20
```

Check path-change events:

```bash
head -n 10 ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl
```

A clean authoritative dataset should contain `java-router-authoritative` rows and should not rely on older `operator-entered-ground-truth` or `emulator-observed` rows.

---

## Clean Java-authoritative-only dataset

If old manual or observed records polluted the truth workspace, archive the old workspace and rebuild it from Java-router truth only:

```bash
stamp=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p ~/i2p-gui/logs/hop_truth_archive
mv ~/i2p-gui/logs/hop_truth ~/i2p-gui/logs/hop_truth_archive/hop_truth_$stamp
mkdir -p ~/i2p-gui/logs/hop_truth/{raw,imports,events,summaries}

cd ~/Desktop/i2p_emulator
python3 import_java_authoritative_truth.py --testnet-base ~/i2p-testnet-8
```

Then use the GUI to run:

```text
Run Normalization
Run Change Detection
```

Verify that the dataset is clean:

```bash
grep -n "java-router-authoritative" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head
grep -n "operator-entered-ground-truth" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head
grep -n "emulator-observed" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head
```

Expected:

- first command returns rows
- second command returns nothing
- third command returns nothing

---

## Reproducible router patch workflow

The authoritative exact-hop feature requires the patched router branch:

```text
https://github.com/boutros-farah/i2p.i2p.git
authoritative-hop-writer
```

Build patched router:

```bash
mkdir -p ~/src
cd ~/src

git clone https://github.com/boutros-farah/i2p.i2p.git
cd ~/src/i2p.i2p
git checkout authoritative-hop-writer

export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"

ant buildRouter
```

Install patched router jar:

```bash
cp ~/i2p/lib/router.jar ~/i2p/lib/router.jar.backup
cp ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
```

Restart testnet:

```bash
cd ~/i2p-testnet-8
./manage-testnet.sh restart
```

Check raw authoritative router output:

```bash
find ~/i2p-testnet-8/r*/data/authoritative -maxdepth 1 -type f -name 'authoritative-hop-events.jsonl' | sort

for f in $(find ~/i2p-testnet-8/r*/data/authoritative -maxdepth 1 -type f -name 'authoritative-hop-events.jsonl' | sort); do
  echo "===== $f ====="
  wc -l "$f"
  head -n 2 "$f"
done
```

---

## Development push workflow

Push emulator changes:

```bash
cd ~/Desktop/i2p_emulator

git status --short --untracked-files=all

git add README.md EMULATOR_SETUP.md working-gui.py \
  import_java_authoritative_truth.py phase5_backend.py \
  run_phase5c_scan.py run_phase5b_normalization.py run_phase5d_change_detection.py

git commit -m "Document reproducible authoritative exact-hop workflow"
git push origin branch5-authoritative-hop-truth-lifecycle
```

Push router patch changes:

```bash
cd ~/src/i2p.i2p

git status
git branch -vv
git remote -v

git push origin authoritative-hop-writer
```

---

## Notes for reports / explanation

Simple explanation:

> The emulator has two path systems. `hop_history` records observed path behavior and is useful for comparison, but it is not exact truth. `hop_truth` stores authoritative exact-hop truth. For Branch 5, we patched the Java router so it writes the actual creator-side tunnel path. The emulator imports those records, normalizes them, and compares snapshots over time to detect real path changes.

