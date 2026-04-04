# I2P Private Testnet Emulator

A professional desktop-controlled **I2P private testnet emulator** for deployment, monitoring, measurement, churn testing, tunnel-surface tracing, exact-hop truth capture, and scenario-level analytics.

This project is intended for **real controlled testing**, not just a visual demo. It combines a deployment script, topology tooling, and a full PyQt GUI into one workflow so a user can build and operate an isolated I2P lab from a single control center.

---

## Table of contents

1. [Project overview](#project-overview)
2. [What this project does](#what-this-project-does)
3. [Current validated capabilities](#current-validated-capabilities)
4. [How the system is designed](#how-the-system-is-designed)
5. [Repository structure](#repository-structure)
6. [Requirements](#requirements)
7. [Permissions and the sudo issue](#permissions-and-the-sudo-issue)
8. [Installation and first setup](#installation-and-first-setup)
9. [How to run the project](#how-to-run-the-project)
10. [How to use the GUI](#how-to-use-the-gui)
11. [What each major feature does](#what-each-major-feature-does)
12. [Measurement and scenario workflow](#measurement-and-scenario-workflow)
13. [Exact-hop truth pipeline](#exact-hop-truth-pipeline)
14. [Analytics pipeline by phase](#analytics-pipeline-by-phase)
15. [Generated files and exports](#generated-files-and-exports)
16. [Recommended validation workflow](#recommended-validation-workflow)
17. [Troubleshooting](#troubleshooting)
18. [Current limitations](#current-limitations)
19. [Suggested future work](#suggested-future-work)
20. [License](#license)

---

## Project overview

This emulator creates and manages a **small isolated I2P test environment** composed of multiple routers, local topology data, deployment automation, and a GUI for live operation.

The project is built around two main operational files:

- `setup-i2p-emulator.sh`  
  Deployment, topology application, router configuration generation, and startup workflow

- `working-gui.py`  
  Main desktop control center for deployment, monitoring, measurements, map view, exact-hop capture, and analytics

The goal is to let a tester:

- deploy a local multi-router I2P environment
- inspect router state and router consoles
- run baseline and churn/adversarial experiments
- collect tunnel-surface and exact-hop data
- compare exact-hop behavior across scenarios
- export useful results for validation, reporting, or demonstrations

---

## What this project does

At a high level, the system provides:

- **private testnet deployment**
- **GUI-based control of the testnet**
- **router state monitoring**
- **measurement instrumentation**
- **churn and adversarial scenario execution**
- **map-based router and trace visualization**
- **long-term analytics**
- **exact-hop truth recording**
- **automatic exact-hop capture when authoritative chain fields exist**
- **scenario-level exact-hop comparison analytics**

A key strength of the project is that once the environment is set up correctly, **most day-to-day operations can be done directly from inside the GUI**.

---

## Current validated capabilities

The project currently supports a validated multi-phase analytics stack:

### Phase 1 — Long-term analytics
- multi-run measurement summaries
- router-level long-term stability trends
- scenario bucket summaries
- exportable analytics

### Phase 2 — Improved stability model
- better router stability scoring
- stronger rebuild/change interpretation

### Phase 3 — Map visualization and analytics overlay
- live router map
- link overlays
- stability-state overlays
- router detail panels

### Phase 4 — Deep trace / relationship hints
- surface-correlation hints
- related-router hints
- map-side trace interpretation support

### Phase 5A — Hop history recorder (inferred)
- conservative inferred hop-role history
- surface-based role/hop interpretation

### Phase 5B — Exact-hop truth recorder
- authoritative exact-hop raw store
- normalization pipeline
- recorder view and exports
- manual exact-hop entry as fallback

### Phase 5C — Automatic exact-hop capture
- automatic ingestion from measurement trace rows when authoritative chain fields are present
- no fake exact-hop generation when those fields are absent

### Phase 6 — Exact-hop analytics
- per-router exact-hop trends
- exact path persistence
- neighbor-pair analytics
- scenario comparison

### Phase 6.1 — Cleanup layer
- cleaner scenario grouping
- improved change-rate presentation
- safer summaries

### Phase 6.2 — Scenario-level exact-hop comparison
- rebuild rate by scenario
- role/hop shift rates by scenario
- path persistence by scenario
- neighbor volatility by scenario
- baseline deltas

---

## How the system is designed

The project is organized into a layered workflow.

### 1. Deployment layer
The setup script builds the testnet environment:

- determines router count and base directory
- supports topology-driven deployment
- generates per-router configuration
- writes `router.config` and `i2ptunnel.config`
- configures the validated **multi-hop default**
- starts and manages routers

### 2. Control layer
The GUI is the main user-facing control center:

- deployment actions
- router start/stop/restart
- router summaries
- configuration/log views
- measurements
- scenarios
- map view
- truth and analytics views

### 3. Trace and truth layer
The measurement system writes trace rows and metadata, which can later feed:

- long-term surface analytics
- inferred hop history
- exact-hop truth
- automatic exact-hop capture
- scenario comparison analytics

### 4. Analytics layer
Later phases interpret the captured data into:

- stability trends
- exact path persistence
- role/hop consistency
- neighbor relationships
- scenario-level comparison

---

## Repository structure

Important files typically include:

```text
working-gui.py
setup-i2p-emulator.sh
topology_model.py
build_topology_manifest.py
export_subnet_tables.py
export_deployment_tables.py
topology.sample.json
README.md
LICENSE
```

Typical runtime and generated areas include:

```text
~/i2p-testnet-<N>/
~/i2p-gui/logs/
~/i2p-gui/logs/measurements/
~/i2p-gui/logs/campaigns/
~/i2p-gui/logs/hop_truth/
```

Topology and generated data examples:

```text
routers.generated.tsv
subnets.generated.tsv
topology.generated.json
```

---

## Requirements

Typical environment:

- Ubuntu Linux
- Python 3
- PyQt desktop environment
- local I2P installation available to the deployment script
- Git
- systemd or equivalent local service control depending on setup mode

You should also be able to:

- run local shell scripts
- access router consoles locally
- restart/redeploy routers
- run the GUI on the test machine
- use `sudo` for deployment-related actions if required by your environment

---

## Permissions and the sudo issue

This is one of the most important practical points.

### Important note
In the validated workflow, **almost everything can be controlled from inside the GUI**, but that only works cleanly if the environment permissions are set up properly.

### What usually needs permission
Depending on your setup, the following may require elevated privileges:

- creating or modifying the deployed testnet
- starting/stopping certain services
- editing files under protected paths
- network namespace / service / bridge operations if your deployment uses them
- router management actions triggered by the GUI

### Recommended professional approach
Set up your environment so the GUI can run the operational commands it needs **without interactive sudo failures**.

That usually means one of these:

- run in a user-owned local environment where no privileged operations are needed during normal usage
- configure the required commands so they can be executed safely by the intended user
- validate that the setup/deployment workflow works before relying on GUI-only operation

### Practical summary
Once the permission problem is fixed, the GUI is designed to be the main operational interface.

---

## Installation and first setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd i2p_emulator
```

### 2. Make the setup script executable
```bash
chmod +x setup-i2p-emulator.sh
```

### 3. Run deployment
```bash
./setup-i2p-emulator.sh
```

This should create the testnet base, per-router configuration, and the local environment needed by the GUI.

### 4. Start the GUI
```bash
python3 working-gui.py
```

---

## How to run the project

### Recommended basic run
1. deploy or redeploy with `setup-i2p-emulator.sh`
2. open the GUI with `python3 working-gui.py`
3. verify router state
4. run a baseline measurement
5. run scenario testing
6. review trace, truth, and analytics
7. export results

---

## How to use the GUI

The GUI is the operational core of the project.

### Main idea
After initial deployment and permission setup, the user can perform most testing tasks from the GUI itself.

### Typical user flow
1. confirm routers are active
2. inspect router summary/config/logs if needed
3. run measurement probes
4. run churn/adversarial scenarios
5. inspect map and trace overlays
6. inspect exact-hop truth
7. inspect Phase 6 analytics
8. export results

---

## What each major feature does

### Fleet / system control
Used to manage the overall state of the testnet.

Typical actions:
- start all
- stop all
- restart all
- refresh state
- stop emulator
- destroy

Use this when you need to bring the whole lab up or down or refresh status after changes.

---

### Router detail panel
Shows information for the selected router.

Typical content:
- service status
- namespace / location / subnet
- console port / URL
- peer counts
- tunnel counts
- reachability
- tunnel acceptance state
- config/log/telemetry views

Use this to inspect one router in detail.

---

### Measurements
Used to run probe-based validation and read the current measurement state.

Typical outputs:
- root probe success
- netDb page success
- proxy/connect success
- latency
- first-byte timing
- trace row generation
- run directories and summaries

Use this to validate whether the current testnet state is healthy and measurable.

---

### Scenarios
Used to run controlled experiments.

Typical scenarios include:
- baseline
- moderate churn
- high churn
- floodfill-targeted behavior
- adversarial scenarios

Use this when testing how the network behaves under changes or stress.

---

### Map
The map is not just decorative; it is an experiment interpretation surface.

Typical map information:
- router placement
- selection state
- status/stability overlays
- tunnel-surface overlays
- deep-trace hints
- router detail card

Use this to visually interpret state changes and relationships during testing.

---

### Phase 5 exact-hop sections
These views are for exact-hop truth handling.

They support:
- manual exact-hop input
- auto-capture status
- truth normalization
- truth recording
- truth reset/cleanup

Use this when validating exact-hop truth generation and capture.

---

### Phase 6 analytics
These views summarize the exact-hop truth into a more useful form.

They support:
- per-router role/hop trends
- path persistence
- neighbor-pair frequency
- scenario-level comparison
- baseline deltas
- exports

Use this when comparing scenario behavior and preparing outputs.

---

## Measurement and scenario workflow

A typical operational sequence looks like this:

### Baseline
Run one baseline measurement first to validate that the network is healthy.

### Churn
Run a moderate churn scenario to observe how paths and router behavior change.

### Stronger scenario
Run a floodfill-targeted or adversarial scenario if needed.

### Refresh analytics
After each run, refresh:
- tunnel trace
- long-term analytics
- exact-hop truth
- Phase 6 analytics

### Export
Export CSV/JSON once the dataset is clean.

---

## Exact-hop truth pipeline

The exact-hop subsystem is intentionally layered.

### Phase 5A — inferred
Stores **conservative inferred** hop history from visible surfaces.

### Phase 5B — authoritative truth
Stores **authoritative exact-hop truth**:
- raw event store
- normalized event output
- recorder summaries
- exports

### Phase 5C — automatic ingestion
When trace rows carry explicit authoritative chain fields, Phase 5C automatically records them and feeds them into the truth pipeline.

### Design rule
If authoritative chain data is not present, the system stays honest and does **not** invent exact-hop truth.

That is a core design principle of the project.

---

## Analytics pipeline by phase

### Phase 1
Focuses on long-term surface-oriented measurement trends.

### Phase 2
Improves stability interpretation.

### Phase 3
Makes state visible on the map.

### Phase 4
Adds deeper relationship hints.

### Phase 5
Moves from inferred history to authoritative exact-hop truth.

### Phase 6
Turns exact-hop truth into usable analytics:
- trends
- persistence
- volatility
- comparison
- baseline deltas

---

## Generated files and exports

Important output areas:

```text
~/i2p-gui/logs/measurements/
~/i2p-gui/logs/campaigns/
~/i2p-gui/logs/hop_truth/raw/
~/i2p-gui/logs/hop_truth/events/
~/i2p-gui/logs/hop_truth/summaries/
```

Typical exports include:
- long-term analytics CSV / JSON
- Phase 5 hop truth CSV / JSON
- Phase 6 analytics CSV / JSON

These outputs are useful for:
- validation
- comparison
- reporting
- demo evidence
- later data processing

---

## Recommended validation workflow

For a clean final validation sequence:

1. deploy or redeploy the testnet
2. open the GUI
3. confirm routers are active
4. reset generated Phase 5B/5C test data if needed
5. run:
   - one baseline measurement
   - one moderate churn scenario
   - one adversarial or floodfill-targeted scenario
6. let Phase 5C auto-capture
7. refresh Phase 6.2 analytics
8. export CSV/JSON outputs

This produces the cleanest validation dataset.

---

## Troubleshooting

### GUI actions fail because of sudo or permissions
Cause:
- environment permissions are not configured for the commands the GUI needs

Fix:
- correct the permission model before relying on GUI-only operation

### Routers active but measurements weak
Cause:
- tunnel build pressure
- startup not settled
- scenario stress
- unstable environment

Fix:
- wait for the network to settle
- rerun baseline first
- confirm tunnel acceptance and readiness

### Exact-hop auto-capture shows zero events
Cause:
- measurement trace rows do not contain authoritative chain fields

Fix:
- verify the trace-writing path is carrying exact chain data
- use manual truth capture only as fallback

### Analytics look polluted
Cause:
- old manual truth/test data still exists

Fix:
- reset Phase 5B/5C generated test data
- rerun a clean scenario sequence

---

## Current limitations

- exact-hop analytics only reflect authoritative chain data that actually exists
- old test data can pollute summaries unless reset
- this remains a controlled lab emulator, so interpretation should stay within that context
- stronger tunnel settings can increase build pressure and reduce stability if pushed too far

---

## Suggested future work

Possible extensions after the current validated state:

- more polished scenario dashboards
- deeper historical comparison
- improved presentation/reporting views
- stronger provenance tracking for chain sources
- richer export pipelines
- more documentation screenshots and demos

---

## License

See `LICENSE`.

---

## Summary

This project is a **professional I2P private testnet emulator** that combines:

- controlled deployment
- GUI-based operation
- measurements and scenarios
- map-based state interpretation
- exact-hop truth capture
- automatic exact-hop ingestion
- scenario-level exact-hop analytics

With permissions configured correctly, the GUI becomes the main operational interface for the user. The result is a practical environment for controlled experimentation, validation, demonstration, and project reporting.
