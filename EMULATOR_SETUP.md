# I2P Emulator Setup Guide

This file is the **from-zero setup guide** for the I2P emulator and the patched authoritative router.

Use it on a fresh Ubuntu VM or a new machine when you want to reproduce the full project:

- install prerequisites
- clone the emulator repository
- clone the patched I2P router repository
- build and install the patched router
- deploy or restart the testnet
- run the GUI
- generate authoritative exact-hop truth
- validate the output

---

## Repositories

### Emulator repository

```text
https://github.com/boutros-farah/i2p-emulator.git
branch: branch5-authoritative-hop-truth-lifecycle
```

### Patched I2P router repository

```text
https://github.com/boutros-farah/i2p.i2p.git
branch: authoritative-hop-writer
```

The emulator repository contains the GUI, deployment scripts, topology tooling, authoritative path backend workers, and helper scripts.

The patched router repository contains the modified I2P router source that writes authoritative tunnel-hop snapshots.

---

## 0. Install prerequisites

Run this first on the Ubuntu VM:

```bash
sudo apt update

sudo apt install -y \
  git \
  openjdk-17-jdk \
  ant \
  python3 \
  python3-pip \
  iproute2 \
  bridge-utils \
  net-tools \
  curl \
  wget \
  unzip \
  rsync \
  openssh-client
```

Install GUI dependencies:

```bash
sudo apt install -y \
  python3-pyqt6 \
  python3-pyqt6.qtwebengine
```

If your Ubuntu image does not provide those PyQt packages, use pip as a fallback:

```bash
python3 -m pip install --user PyQt6 PyQt6-WebEngine
```

Check the important versions:

```bash
java -version
javac -version
ant -version
python3 --version
git --version
```

Expected Java version:

```text
Java 17
```

---

## 1. Clone the emulator repository

```bash
mkdir -p ~/Desktop
cd ~/Desktop

git clone https://github.com/boutros-farah/i2p-emulator.git i2p_emulator
cd ~/Desktop/i2p_emulator

git checkout branch5-authoritative-hop-truth-lifecycle
```

Confirm:

```bash
git branch --show-current
git status
ls -l working-gui.py setup-i2p-emulator.sh
```

Expected branch:

```text
branch5-authoritative-hop-truth-lifecycle
```

Make the setup script executable:

```bash
chmod +x setup-i2p-emulator.sh
```

---

## 2. Clone the patched I2P router source

```bash
mkdir -p ~/src
cd ~/src

git clone https://github.com/boutros-farah/i2p.i2p.git
cd ~/src/i2p.i2p

git checkout authoritative-hop-writer
```

Confirm:

```bash
git branch --show-current
git log --oneline -3
```

Expected branch:

```text
authoritative-hop-writer
```

You should see a commit like:

```text
Add authoritative exact-hop tunnel snapshot writer
```

---

## 3. Build the patched router

```bash
cd ~/src/i2p.i2p

export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"

ant buildRouter
```

Expected final line:

```text
BUILD SUCCESSFUL
```

The patched router jar should exist here:

```text
~/src/i2p.i2p/router/java/build/router.jar
```

Confirm:

```bash
ls -lh ~/src/i2p.i2p/router/java/build/router.jar
```

---

## 4. Deploy the emulator testnet

Go to the emulator repo:

```bash
cd ~/Desktop/i2p_emulator
```

### Recommended topology-driven deployment

Generate router and subnet TSV files from the sample topology:

```bash
python3 build_topology_manifest.py topology.sample.json
python3 export_subnet_tables.py topology.sample.json \
  --routers-out routers.generated.tsv \
  --subnets-out subnets.generated.tsv
```

Deploy the testnet:

```bash
sudo ./setup-i2p-emulator.sh \
  --routers-tsv routers.generated.tsv \
  --subnets-tsv subnets.generated.tsv \
  --yes
```

If you prefer the simpler numeric deployment mode:

```bash
sudo ./setup-i2p-emulator.sh --routers 8 --floodfill 3 --yes
```

After deployment, check that a testnet directory exists:

```bash
ls -ld ~/i2p-testnet-*
```

For this project, the examples usually use:

```text
~/i2p-testnet-8
```

---

## 5. Install the patched router jar

After the emulator has installed or prepared the local I2P base at `~/i2p`, replace the stock router jar with the patched one.

Check the current router jar:

```bash
ls -lh ~/i2p/lib/router.jar
```

Back it up and install the patched jar:

```bash
cp ~/i2p/lib/router.jar ~/i2p/lib/router.jar.backup
cp ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
```

Confirm:

```bash
ls -lh ~/i2p/lib/router.jar ~/i2p/lib/router.jar.backup
```

---

## 6. Start or restart the testnet

If the testnet already exists:

```bash
cd ~/i2p-testnet-8
./manage-testnet.sh restart
```

If `restart` is not supported:

```bash
cd ~/i2p-testnet-8
./manage-testnet.sh stop
./manage-testnet.sh start
```

Check status:

```bash
cd ~/i2p-testnet-8
./manage-testnet.sh status
```

---

## 7. Start the GUI

```bash
cd ~/Desktop/i2p_emulator
python3 working-gui.py
```

The GUI is the main operating interface for:

- deployment review
- router monitoring
- measurements
- churn scenarios
- Path Records
- Path Analysis
- authoritative truth inspection

---

## 8. Verify that the patched routers are writing authoritative files

After routers run for a short time, check for authoritative router output:

```bash
find ~/i2p-testnet-8/r*/data/authoritative \
  -maxdepth 1 \
  -type f \
  -name 'authoritative-hop-events.jsonl' | sort
```

Inspect rows:

```bash
for f in $(find ~/i2p-testnet-8/r*/data/authoritative -maxdepth 1 -type f -name 'authoritative-hop-events.jsonl' | sort); do
  echo "===== $f ====="
  wc -l "$f"
  head -n 2 "$f"
done
```

Correct rows should contain:

```text
"source_mode":"java-router-authoritative"
"truth_level":"ground-truth"
"hop_hashes":[...]
```

---

## 9. Run the GUI authoritative workflow

In the GUI:

1. run a measurement probe
2. go to **Measurements → Path Records → Ingestion**
3. click **Scan Now**
4. click **Run Normalization**
5. click **Run Change Detection**

Then inspect:

```text
Measurements → Path Records → Overview → Authoritative Exact-Hop Truth
Measurements → Path Records → Ingestion → Change Detection
Measurements → Path Analysis → Overview
Measurements → Path Analysis → Observed Path Comparison
```

What each action means:

- **Scan Now** imports/adapts Java-router authoritative files.
- **Run Normalization** rebuilds the canonical truth dataset.
- **Run Change Detection** builds the path-change history from authoritative snapshots.
- **Authoritative Exact-Hop Truth** shows authoritative path snapshots.
- **Change Detection** shows how paths changed over time.

---

## 10. Run the same workflow from terminal if needed

Import Java authoritative router output:

```bash
cd ~/Desktop/i2p_emulator
python3 import_java_authoritative_truth.py --testnet-base ~/i2p-testnet-8
```

Run the backend workers:

```bash
python3 run_phase5c_scan.py --testnet-base ~/i2p-testnet-8
python3 run_phase5b_normalization.py
python3 run_phase5d_change_detection.py
```

---

## 11. Validate output files

Check that the output files exist:

```bash
ls -lh ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl \
      ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.json \
      ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl \
      ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.json
```

Check authoritative truth rows:

```bash
grep -n "java-router-authoritative" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head -20
```

Check path-change rows:

```bash
head -n 10 ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl
```

Expected change rows include fields like:

```text
source_mode
truth_level
creator_router_name
tunnel_direction
tunnel_kind
change_type
previous_path_signature
current_path_signature
```

---

## 12. Optional: create a clean Java-only truth workspace

Use this if your truth files contain older manual or observed records and you want a clean official Java-router-only run.

Archive the old truth workspace:

```bash
stamp=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p ~/i2p-gui/logs/hop_truth_archive

if [ -d ~/i2p-gui/logs/hop_truth ]; then
  mv ~/i2p-gui/logs/hop_truth ~/i2p-gui/logs/hop_truth_archive/hop_truth_$stamp
fi

mkdir -p ~/i2p-gui/logs/hop_truth/{raw,imports,events,summaries}
```

Import only Java-router authoritative truth:

```bash
cd ~/Desktop/i2p_emulator
python3 import_java_authoritative_truth.py --testnet-base ~/i2p-testnet-8
```

Then run in the GUI:

```text
Run Normalization
Run Change Detection
```

Verify it is clean:

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

## 13. Troubleshooting

### `~/i2p/lib/router.jar` does not exist

Run the emulator deployment step first:

```bash
cd ~/Desktop/i2p_emulator
sudo ./setup-i2p-emulator.sh --routers 8 --floodfill 3 --yes
```

Then install the patched router jar again.

### Router output files do not exist

Check that the patched router jar was installed:

```bash
ls -lh ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
```

Restart the testnet:

```bash
cd ~/i2p-testnet-8
./manage-testnet.sh restart
```

Check authoritative output again:

```bash
find ~/i2p-testnet-8/r*/data/authoritative -maxdepth 1 -type f -name 'authoritative-hop-events.jsonl' | sort
```

### Java authoritative import reads zero files

Check the testnet path:

```bash
find ~/i2p-testnet-8/r*/data/authoritative -maxdepth 1 -type f -name 'authoritative-hop-events.jsonl' | sort
```

Then rerun:

```bash
cd ~/Desktop/i2p_emulator
python3 import_java_authoritative_truth.py --testnet-base ~/i2p-testnet-8
```

### GUI freezes during heavy path actions

The GUI uses external worker scripts for heavy authoritative-path work.

Make sure these files are present:

```bash
ls -l \
  phase5_backend.py \
  run_phase5c_scan.py \
  run_phase5b_normalization.py \
  run_phase5d_change_detection.py \
  import_java_authoritative_truth.py
```

Avoid running old GUI copies that still execute heavy authoritative-path work inline.

---

## 14. Maintainer commands: update emulator repo

Use this after editing emulator files or documentation:

```bash
cd ~/Desktop/i2p_emulator

git status --short --untracked-files=all

git add README.md EMULATOR_SETUP.md working-gui.py \
  import_java_authoritative_truth.py \
  phase5_backend.py \
  run_phase5c_scan.py \
  run_phase5b_normalization.py \
  run_phase5d_change_detection.py

git commit -m "Update emulator setup and authoritative exact-hop workflow"

git push origin branch5-authoritative-hop-truth-lifecycle
```

Verify:

```bash
git status
git log --oneline -3
git branch -vv
```

---

## 15. Maintainer commands: update patched router branch

```bash
cd ~/src/i2p.i2p

git status
git branch -vv
git remote -v

git push origin authoritative-hop-writer
```


## Location-based public IPv4 emulation workflow

For supervisor-facing public-IP tests, use `topology.sample.json` or
`topology.public-any-location.template.json`. These files use `public-any-location`,
which assigns public-looking IPv4 CIDRs as the actual runtime router/subnet addresses
inside the isolated emulator.

Validate and export:

```bash
cd ~/Desktop/i2p_emulator
python3 topology_model.py topology.sample.json --debug-report
python3 export_subnet_tables.py topology.sample.json \
  --routers-out routers.generated.tsv \
  --subnets-out subnets.generated.tsv
```

Deploy from the generated TSVs:

```bash
sudo ./setup-i2p-emulator.sh \
  --routers-tsv routers.generated.tsv \
  --subnets-tsv subnets.generated.tsv \
  --yes
```

After deployment, verify that the addresses are real runtime namespace addresses, not
only GUI labels:

```bash
for ns in $(ip netns list | awk '{print $1}' | sort -V); do
  echo "===== $ns ====="
  sudo ip netns exec "$ns" ip -4 addr show scope global | grep -E 'inet '
done
```

Expected shape:

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

Keep the testnet isolated unless the public ranges are actually assigned to the lab.
