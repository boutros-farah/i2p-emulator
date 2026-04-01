# I2P Local Testnet Emulator

A local, isolated I2P emulator for controlled experimentation, topology design, churn injection, telemetry collection, and measurement-driven evaluation.

This project creates a private I2P test environment that can be deployed and operated entirely on a Linux machine without joining the public I2P network. It is intended for safe testing, performance analysis, and future research on I2P behavior under controlled conditions such as baseline operation, router churn, and floodfill-targeted scenarios.

---

## Overview

The emulator combines:

- a topology model for defining routers, countries, cities, and subnets,
- TSV and manifest generators for turning a topology JSON file into deployment-ready data,
- a setup script that builds an isolated Linux namespace-based network and prepares per-router I2P instances,
- a GUI for topology building, deployment, router control, live monitoring, measurements, experiment history, and map visualization.

The current implementation uses Linux network namespaces, bridges, veth pairs, and systemd-managed router services to isolate routers while keeping them reachable for local testing and visualization.

---

## Goals

- Emulate I2P routers in a fully isolated local environment.
- Study I2P concepts such as unidirectional tunnels, netDb behavior, and floodfill roles without using the public network.
- Run repeatable experiments under normal and adversarial conditions.
- Collect telemetry and measurements for later analysis.
- Provide a foundation that can be extended and improved later.

---

## Main Features

### Topology-driven deployment
- Define locations, subnets, router counts, and floodfill roles in JSON.
- Validate the topology before deployment.
- Generate deployment-ready router and subnet TSV files.

### Isolated router runtime
- Each router runs in its own Linux network namespace.
- Routers are attached to private lab subnets through host-side bridges and veth pairs.
- Router metadata is written into configuration files for GUI and measurement use.

### GUI-based workflow
- Builder-driven deployment from inside the GUI.
- Fleet view for router state inspection.
- Topology and map visualization.
- Scenario runner for churn experiments.
- History and dashboard views.
- Measurement workflow for tunnel and proxy-related testing.

### Experiment support
- Baseline measurements.
- Moderate and high churn scenarios.
- Floodfill-targeted testing paths.

### Operational tooling
- Automatic deployment logging.
- Start, stop, and destroy runtime controls.
- Generated artifacts that can be reused and inspected.

---

## Repository Structure

```text
.
├── working-gui.py
├── setup-i2p-emulator.sh
├── topology_model.py
├── build_topology_manifest.py
├── export_deployment_tables.py
├── export_subnet_tables.py
├── topology.sample.json
├── README.md
└── LICENSE
```

### File Roles

#### `working-gui.py`
Main application interface.

It provides:
- Builder
- Fleet
- Topology
- Scenarios
- History
- Measurements
- Map

It can validate topology input, generate the required JSON and TSV deployment files, launch the setup script, monitor routers, and control emulator actions from one place.

#### `setup-i2p-emulator.sh`
Main deployment and runtime preparation script.

It is responsible for:
- checking or installing prerequisites,
- cleaning old deployments,
- downloading or validating the I2P installer,
- creating network namespaces, bridges, and veth pairs,
- preparing per-router directories and configs,
- generating runtime scripts,
- installing and enabling systemd services,
- starting the local emulator.

#### `topology_model.py`
Topology schema, validation, expansion, and summary logic.

#### `build_topology_manifest.py`
Builds an expanded manifest from a topology JSON file.

#### `export_deployment_tables.py`
Exports router deployment data as TSV.

#### `export_subnet_tables.py`
Exports subnet deployment data and supports the GUI deployment flow.

#### `topology.sample.json`
Example topology file for testing and first-time deployment.

---

## Architecture Summary

### 1. Topology Layer
The topology JSON defines:
- locations,
- country and city metadata,
- geographic center points for display,
- subnets,
- router counts per subnet,
- floodfill allocation.

The topology tools validate the file, expand it into router records, and generate deployment tables.

### 2. Deployment Layer
The setup script converts the generated tables into a local testnet by creating:
- one namespace per router,
- private bridges and subnets,
- per-router config, data, and log directories,
- router-specific systemd services,
- a restartable network fabric.

### 3. Control and Visualization Layer
The GUI is the main operator interface. It manages:
- topology authoring,
- deployment,
- router status refresh,
- scenario execution,
- measurement runs,
- map-based and topology-based visualization,
- history and log review.

---

## Prerequisites

This project is designed for Linux and expects a system with systemd.

### Required operating environment

- Linux host or Linux VM
- systemd
- sudo access
- network namespace support (`ip netns`)
- bridge and veth support (`ip link`)
- Python 3
- Java 17

### Required packages

The setup script installs or expects the following core packages:

- `openjdk-17-jdk`
- `wget`
- `curl`
- `python3`
- `net-tools`
- `unzip`
- `expect`
- `dos2unix`
- `iproute2`

### Python GUI dependencies

The GUI is designed to work with either:
- `PyQt6`, or
- `PyQt5`

Optional but useful:
- `PyQt6-WebEngine` or `PyQt5-WebEngine`
- `pycountry`
- `countryinfo`

### Sudo requirement

The GUI calls privileged system commands in non-interactive mode. Because of that, it is strongly recommended to refresh sudo before starting the GUI:

```bash
sudo -v
```

If this is not done, deployment or runtime control actions may fail because the GUI will not stop and ask for a password interactively.

---

## Installation

Clone or copy the repository to your Linux machine, then make sure the setup script is executable:

```bash
chmod +x setup-i2p-emulator.sh
```

When deployment is started from the GUI, the GUI can try to set the executable bit automatically. Keeping the script executable in the repository is still recommended.

Install the Python dependencies required for the GUI in the way you prefer for your environment.

Example:

```bash
pip install PyQt6 PyQt6-WebEngine pycountry countryinfo
```

If you prefer PyQt5, install the equivalent PyQt5 packages instead.

---

## How to Run

### Recommended workflow

The recommended workflow is to run the deployment from the GUI.

1. Open a terminal in the project directory.
2. Refresh sudo credentials:

```bash
sudo -v
```

3. Launch the GUI:

```bash
python3 working-gui.py
```

4. In the GUI:
   - open the **Builder** tab,
   - load `topology.sample.json` or create your own topology,
   - validate the topology,
   - generate the deployment files,
   - deploy the emulator from the Builder.

The GUI can generate the topology JSON plus the router and subnet TSV files automatically, then call the setup script internally.

### Manual setup script usage

The setup script can also be executed directly when needed.

Example:

```bash
./setup-i2p-emulator.sh --help
```

A typical manual workflow is:
- create or edit a topology JSON file,
- generate the router TSV file,
- generate the subnet TSV file,
- run the setup script with the generated deployment files.

---

## Topology Workflow

A typical topology-driven workflow is:

1. Define the topology in JSON.
2. Validate and expand the topology.
3. Export router deployment tables.
4. Export subnet deployment tables.
5. Deploy the emulator.
6. Use the GUI to operate, observe, and measure the environment.

This keeps the deployment reproducible and makes it easier to compare experiment runs across different configurations.

---

## Outputs and Generated Artifacts

Depending on the workflow, the project can generate or use artifacts such as:

- expanded topology JSON files,
- router deployment TSV files,
- subnet deployment TSV files,
- per-router configuration directories,
- runtime logs,
- measurement summaries,
- experiment history data.

These files are useful for debugging, reproducibility, and later analysis.

---

## Use Cases

This project is intended for:

- controlled I2P experimentation,
- local testing without public network exposure,
- churn and resilience studies,
- floodfill-related behavior analysis,
- student projects and research prototypes,
- future extension into larger test and analysis workflows.

---

## Limitations

- This project is Linux-focused and depends on system-level networking features.
- Runtime behavior depends on the host system resources, namespace support, and systemd behavior.
- Large-scale experiments may require additional optimization in resource management, monitoring, and service orchestration.
- The project is a local emulator for controlled testing; it is not a production I2P deployment manager.

---

## Troubleshooting

### The GUI cannot deploy or control routers
Refresh sudo first:

```bash
sudo -v
```

Then restart the GUI.

### The setup script fails to create namespaces or bridges
Verify that:
- the host is Linux,
- `iproute2` is installed,
- sudo privileges are available,
- no conflicting old deployment is still present.

### The GUI opens but some visual components are missing
Install the appropriate WebEngine package for your PyQt version.

### Deployment files are missing
Use the Builder tab to regenerate the topology outputs, or run the export scripts manually.

---

## Future Improvements

Possible extensions include:

- stronger modularization of the GUI,
- improved large-scale orchestration,
- richer telemetry dashboards,
- automated experiment scheduling,
- more advanced topology presets,
- exportable experiment reports,
- tighter validation and recovery paths for deployment failures.

---

## License

This project is released under the MIT License. See the `LICENSE` file for details.
