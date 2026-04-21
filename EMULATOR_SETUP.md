# I2P Emulator Setup Guide

This is the from-zero setup guide for the final I2P emulator project.

It covers:

- installing prerequisites;
- cloning the emulator repository;
- cloning the patched I2P router source;
- building the patched router;
- deploying a public-address isolated testnet;
- installing the patched router jar;
- running the GUI;
- importing Java-router authoritative exact-hop truth;
- normalizing and detecting path changes;
- validating the final outputs.

---

## 0. Repository layout

### Emulator repository

```text
https://github.com/boutros-farah/i2p-emulator.git
branch: main
```

### Patched I2P router repository

```text
https://github.com/boutros-farah/i2p.i2p.git
branch: authoritative-hop-writer
```

The emulator repository contains the GUI, deployment tooling, topology model, measurements, scenario support, path analytics, and truth-processing scripts.

The patched router repository contains the Java router modification required for authoritative exact-hop capture.

---

## 1. Install prerequisites

Run on Ubuntu:

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
  openssh-client \
  expect
```

Install GUI dependencies:

```bash
sudo apt install -y \
  python3-pyqt6 \
  python3-pyqt6.qtwebengine
```

If the Ubuntu package names are unavailable, install PyQt through pip:

```bash
python3 -m pip install --user PyQt6 PyQt6-WebEngine
```

Check versions:

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

## 2. Clone the emulator repository

```bash
mkdir -p ~/Desktop
cd ~/Desktop

git clone https://github.com/boutros-farah/i2p-emulator.git i2p_emulator
cd ~/Desktop/i2p_emulator

git checkout main
git pull --ff-only origin main
```

Confirm:

```bash
git branch --show-current
git status --short --untracked-files=all
ls -l working-gui.py setup-i2p-emulator.sh topology.sample.json
```

Expected branch:

```text
main
```

Ensure the setup script is executable:

```bash
chmod +x setup-i2p-emulator.sh
```

---

## 3. Clone the patched I2P router source

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

---

## 4. Build the patched router

```bash
cd ~/src/i2p.i2p

export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"

ant buildRouter
```

Expected:

```text
BUILD SUCCESSFUL
```

Verify the patched router jar exists and contains the authoritative writer:

```bash
ls -lh ~/src/i2p.i2p/router/java/build/router.jar
jar tf ~/src/i2p.i2p/router/java/build/router.jar | grep AuthoritativeHopEventWriter
```

Expected class:

```text
net/i2p/router/tunnel/pool/AuthoritativeHopEventWriter.class
```

---

## 5. Validate the default public-address topology

```bash
cd ~/Desktop/i2p_emulator

python3 topology_model.py topology.sample.json --debug-report
python3 topology_model.py topology.public-any-location.template.json --debug-report
```

Expected addressing mode:

```text
public-any-location
```

Expected example topology:

```text
Locations : 3
Subnets   : 3
Routers   : 7
Floodfill : 2
Subnet /16 diversity : required
```

---

## 6. Generate deployment tables

```bash
cd ~/Desktop/i2p_emulator

python3 export_subnet_tables.py topology.sample.json \
  --routers-out routers.generated.tsv \
  --subnets-out subnets.generated.tsv
```

Inspect:

```bash
column -t -s $'\t' routers.generated.tsv
column -t -s $'\t' subnets.generated.tsv
```

Expected public-style subnets:

```text
45.10.1.0/29
91.80.1.0/29
185.20.1.0/29
```

---

## 7. Deploy the testnet

```bash
cd ~/Desktop/i2p_emulator

sudo ./setup-i2p-emulator.sh \
  --routers-tsv routers.generated.tsv \
  --subnets-tsv subnets.generated.tsv \
  --yes
```

Expected behavior:

- I2P base is installed under `~/i2p`;
- Linux namespaces and bridges are created;
- router configs are generated;
- router systemd units are installed;
- router consoles become reachable;
- a testnet directory is created under `~/i2p-testnet-*`.

Find the newest testnet:

```bash
ls -td ~/i2p-testnet-* | head -1
```

For the validated run, the directory was:

```text
/home/ubuntu/i2p-testnet-7
```

---

## 8. Verify deployed public-style IPs

Set the testnet path:

```bash
export TESTNET_BASE="$(ls -td ~/i2p-testnet-* | head -1)"
echo "$TESTNET_BASE"
cd "$TESTNET_BASE"
```

Check status:

```bash
./manage-testnet.sh status
./manage-testnet.sh netmap
```

Verify namespace IPs:

```bash
for n in 1 2 3 4 5 6 7; do
  echo "===== Router $n / i2pns-r$n ====="
  sudo ip netns exec i2pns-r$n ip -4 addr show scope global
done
```

Expected:

```text
Router 1: 45.10.1.2/29
Router 2: 45.10.1.3/29
Router 3: 45.10.1.4/29
Router 4: 91.80.1.2/29
Router 5: 91.80.1.3/29
Router 6: 185.20.1.2/29
Router 7: 185.20.1.3/29
```

Verify router config uses the same public-style IPs:

```bash
cd "$TESTNET_BASE"

for n in 1 2 3 4 5 6 7; do
  echo "===== Router $n ====="
  grep -E 'i2np\.ntcp\.host|i2np\.udp\.host|i2np\.ntcp\.port|i2np\.udp\.port|routerconsole\.port' \
    r$n/config/router.config
done
```

---

## 9. Verify cross-subnet connectivity

```bash
cd "$TESTNET_BASE"

sudo ip netns exec i2pns-r1 ping -c 2 -W 2 91.80.1.2
sudo ip netns exec i2pns-r1 ping -c 2 -W 2 185.20.1.2
sudo ip netns exec i2pns-r4 ping -c 2 -W 2 45.10.1.2
sudo ip netns exec i2pns-r6 ping -c 2 -W 2 45.10.1.2
```

Expected:

```text
0% packet loss
```

Check listening sockets:

```bash
for n in 1 2 3 4 5 6 7; do
  echo "===== Router $n listening sockets ====="
  sudo ip netns exec i2pns-r$n ss -lntup | grep -E '770|5000|5100|4444' || true
done
```

---

## 10. Install the patched router jar

The setup script may install or reinstall the stock I2P router jar. For authoritative exact-hop capture, install the patched jar after deployment.

Check current installed router jar:

```bash
jar tf ~/i2p/lib/router.jar | grep AuthoritativeHopEventWriter || true
```

If no class is printed, install the patched jar:

```bash
cp ~/i2p/lib/router.jar ~/i2p/lib/router.jar.stock-before-authoritative-hop.$(date +%Y%m%d_%H%M%S)
cp ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
```

Verify:

```bash
jar tf ~/i2p/lib/router.jar | grep AuthoritativeHopEventWriter
```

Restart the testnet:

```bash
cd "$TESTNET_BASE"
./manage-testnet.sh restart
./manage-testnet.sh status
```

---

## 11. Verify authoritative router output

```bash
cd "$TESTNET_BASE"

find r*/data/authoritative \
  -maxdepth 1 \
  -type f \
  -name 'authoritative-hop-events.jsonl' \
  -print 2>/dev/null | sort
```

Inspect counts and sample rows:

```bash
for f in $(find r*/data/authoritative -maxdepth 1 -type f -name 'authoritative-hop-events.jsonl' -print 2>/dev/null | sort); do
  echo "===== $f ====="
  wc -l "$f"
  ls -lh "$f"
  head -n 2 "$f"
done
```

Correct rows contain:

```text
"event_type":"tunnel_accepted"
"source_mode":"java-router-authoritative"
"truth_level":"ground-truth"
"hop_hashes":[...]
```

---

## 12. Import Java authoritative truth

```bash
cd ~/Desktop/i2p_emulator

python3 import_java_authoritative_truth.py --testnet-base "$TESTNET_BASE"
```

Expected output:

```text
success: true
files_scanned: 7
rows_read: non-zero
rows_written: non-zero
```

---

## 13. Normalize truth and detect path changes

```bash
cd ~/Desktop/i2p_emulator

python3 run_phase5b_normalization.py
python3 run_phase5d_change_detection.py
```

Check final files:

```bash
ls -lh ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl \
       ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.json \
       ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl \
       ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.json
```

Preview truth:

```bash
grep -n "java-router-authoritative" ~/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl | head
```

Preview changes:

```bash
head -n 10 ~/i2p-gui/logs/hop_truth/events/exact-hop-change-events.jsonl
```

---

## 14. Clean Java-authoritative-only truth workspace

Use this before an official validation run if old manual or observed records exist.

```bash
stamp=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p ~/i2p-gui/logs/hop_truth_archive

if [ -d ~/i2p-gui/logs/hop_truth ]; then
  mv ~/i2p-gui/logs/hop_truth ~/i2p-gui/logs/hop_truth_archive/hop_truth_mixed_$stamp
fi

mkdir -p ~/i2p-gui/logs/hop_truth/{raw,imports,events,summaries}
```

Then rerun:

```bash
cd ~/Desktop/i2p_emulator

python3 import_java_authoritative_truth.py --testnet-base "$TESTNET_BASE"
python3 run_phase5b_normalization.py
python3 run_phase5d_change_detection.py
```

Verify source modes:

```bash
python3 - <<'PY'
import json
from collections import Counter

path = "/home/ubuntu/i2p-gui/logs/hop_truth/events/exact-hop-truth.jsonl"
source_modes = Counter()
routers = set()
rows = 0

with open(path, encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        rows += 1
        obj = json.loads(line)
        source_modes[obj.get("source_mode")] += 1
        if obj.get("router_id"):
            routers.add(str(obj.get("router_id")))

print("rows:", rows)
print("source_modes:", dict(source_modes))
print("router_count:", len(routers))
print("routers:", sorted(routers, key=lambda x: int(x) if x.isdigit() else x))
PY
```

Expected clean result:

```text
source_modes: {'java-router-authoritative': ...}
router_count: 7
```

---

## 15. Run the GUI

```bash
cd ~/Desktop/i2p_emulator
python3 working-gui.py
```

Recommended GUI workflow:

```text
1. Run a measurement probe.
2. Open Measurements -> Path Records -> Ingestion.
3. Run Scan Now.
4. Run Normalization.
5. Run Change Detection.
6. Review Authoritative Exact-Hop Truth.
7. Review Path Analysis and Observed Path Comparison.
```

---

## 16. Common troubleshooting

### Installer says `/home/ubuntu/i2p` cannot be written

Fix ownership:

```bash
sudo rm -rf /home/ubuntu/i2p
mkdir -p /home/ubuntu/i2p
sudo chown -R ubuntu:ubuntu /home/ubuntu/i2p
chmod 755 /home/ubuntu/i2p
```

Then rerun the deployment.

### Authoritative files are missing

Check the patched jar:

```bash
jar tf ~/i2p/lib/router.jar | grep AuthoritativeHopEventWriter
```

If missing:

```bash
cp ~/src/i2p.i2p/router/java/build/router.jar ~/i2p/lib/router.jar
cd "$TESTNET_BASE"
./manage-testnet.sh restart
```

### Import reads zero files

Check the testnet path:

```bash
find "$TESTNET_BASE"/r*/data/authoritative \
  -maxdepth 1 \
  -type f \
  -name 'authoritative-hop-events.jsonl' | sort
```

Then rerun the import using that exact testnet path.

### GUI freezes during authoritative actions

Use the external worker scripts:

```text
run_phase5c_scan.py
run_phase5b_normalization.py
run_phase5d_change_detection.py
```

Do not reintroduce heavy authoritative processing inline inside `working-gui.py`.

---

## 17. Repository hygiene

Before committing:

```bash
cd ~/Desktop/i2p_emulator

git status --short --untracked-files=all
git diff --check

python3 -m py_compile \
  topology_model.py \
  build_topology_manifest.py \
  export_deployment_tables.py \
  export_subnet_tables.py \
  import_java_authoritative_truth.py \
  phase5_backend.py \
  run_phase5b_normalization.py \
  run_phase5c_scan.py \
  run_phase5d_change_detection.py \
  working-gui.py

bash -n setup-i2p-emulator.sh

python3 topology_model.py topology.sample.json --debug-report
python3 topology_model.py topology.public-any-location.template.json --debug-report
```

Do not commit generated runtime outputs:

```text
routers.generated.tsv
subnets.generated.tsv
routers.public-any-location.tsv
subnets.public-any-location.tsv
~/i2p-testnet-*
~/i2p-gui/logs/
*.jsonl runtime truth files
```

---

## 18. Final validated result

The final validated public-IP authoritative run produced:

```text
Imported Java authoritative rows: 216
Normalized canonical truth events: 598
Router count: 7
Tunnel count: 215
Source modes: java-router-authoritative only
Change events: 144
Streams: 30
```

This confirms that the emulator supports functional public-style IP deployment and clean Java-router authoritative exact-hop validation.
