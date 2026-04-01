#!/bin/bash
# =============================================================================
# I2P Local LAN Testnet Emulator - Namespace/Subnet Edition
#
# Supervisor handoff version:
# - cleaned project header
# - retained topology-driven deployment and namespace isolation logic
# - intended for reproducible local testnet deployment, churn testing,
#   telemetry collection, and GUI-driven experimentation
#
# Core behavior in this script:
# - each router runs in its own Linux network namespace
# - topology TSV files can define shared subnets, bridges, and router metadata
# - host-side bridges preserve direct access to router consoles from the host
# - a management helper script is generated for runtime operations
# - router metadata is written into router.config for GUI/runtime discovery
#
# This script is intentionally deployment-oriented. Helper/export logic lives in
# the Python topology tooling so that topology generation and deployment remain
# separated and easier to maintain.
# =============================================================================

set -Eeuo pipefail

CURRENT_STEP="startup"
trap 'echo -e "\n${RED:-}✗${NC:-} Failed during: ${CURRENT_STEP} (line $LINENO)" >&2' ERR

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "\n${BLUE}━━[STEP $1]━━${NC} $2"; }
info() { echo -e " ${GREEN}●${NC} $1"; }
warn() { echo -e " ${YELLOW}⚠${NC}  $1"; }
die()  { echo -e " ${RED}✗${NC}  $1"; exit 1; }
ok()   { echo -e " ${GREEN}✓${NC}  $1"; }
hr()   { echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"; }

# ── Resolve real user ─────────────────────────────────────────────────────────
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)
I2P_HOME="$ACTUAL_HOME/i2p"
INSTALLER_JAR="$ACTUAL_HOME/i2pinstall_latest.jar"

# ── Namespace / bridge naming ────────────────────────────────────────────────
NS_PREFIX="i2pns-r"
BR_PREFIX="i2pbr-r"
HV_PREFIX="i2ph"
NV_PREFIX="i2pn"

router_ns_name()   { echo "${NS_PREFIX}$1"; }
router_br_name()   { echo "${BR_PREFIX}$1"; }
router_host_veth() { echo "${HV_PREFIX}$1"; }
router_ns_veth()   { echo "${NV_PREFIX}$1"; }

# We intentionally place each router in its own /24 lab subnet.
# Example:
#   Router 1  -> 10.210.1.0/24  gateway 10.210.1.1  router 10.210.1.2
#   Router 2  -> 10.210.2.0/24  gateway 10.210.2.1  router 10.210.2.2
#
# This is simple, readable, and ideal for a teaching/research lab where
# “different routers, different subnets” should be obvious in configs and GUI.
calc_octets() {
    local idx=$1
    local oct2=$(( 210 + ((idx - 1) / 250) ))
    local oct3=$(( ((idx - 1) % 250) + 1 ))
    if [ "$oct2" -gt 254 ]; then
        die "Router count too large for current lab addressing plan."
    fi
    echo "$oct2 $oct3"
}
router_subnet() {
    local oct2 oct3
    read -r oct2 oct3 <<< "$(calc_octets "$1")"
    echo "10.${oct2}.${oct3}.0/24"
}
router_gateway_ip() {
    local oct2 oct3
    read -r oct2 oct3 <<< "$(calc_octets "$1")"
    echo "10.${oct2}.${oct3}.1"
}
router_ip() {
    local oct2 oct3
    read -r oct2 oct3 <<< "$(calc_octets "$1")"
    echo "10.${oct2}.${oct3}.2"
}
router_console_port() { echo $(( 7700 + $1 )); }
router_ntcp_port()    { echo $(( 50000 + $1 )); }
router_udp_port()     { echo $(( 51000 + $1 )); }
router_proxy_port()   { echo $(( 44440 + $1 )); }

router_ip_for_runtime() {
    local i="$1"
    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "$ROUTERS_TSV" "$i" "router_ip"
    else
        router_ip "$i"
    fi
}

router_ns_for_runtime() {
    local i="$1"
    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "$ROUTERS_TSV" "$i" "namespace"
    else
        router_ns_name "$i"
    fi
}

router_floodfill_for_runtime() {
    local i="$1"
    local val
    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        normalize_bool "$(get_router_tsv_field "$ROUTERS_TSV" "$i" "floodfill")"
    else
        if [ "$i" -le "$NUM_FF" ]; then
            echo "true"
        else
            echo "false"
        fi
    fi
}

list_floodfill_router_ids() {
    local i
    for i in $(seq 1 "$TOTAL_ROUTERS"); do
        if [ "$(router_floodfill_for_runtime "$i")" = "true" ]; then
            echo "$i"
        fi
    done
}

cleanup_network_artifacts() {
    # Namespaces first
    local ns
    while read -r ns; do
        [ -n "$ns" ] || continue
        sudo ip netns delete "$ns" 2>/dev/null || true
    done < <(ip netns list 2>/dev/null | awk '{print $1}' | grep -E "^${NS_PREFIX}[0-9]+$" || true)

    # Then bridges / leftover host-side links
    local link
    while read -r link; do
        [ -n "$link" ] || continue
        sudo ip link delete "$link" 2>/dev/null || true
    done < <(
        ip -o link show 2>/dev/null \
        | awk -F': ' '{print $2}' \
        | cut -d@ -f1 \
        | grep -E "^((i2pbr-r|i2pbr-s)|${HV_PREFIX}|${NV_PREFIX})[0-9]+$" \
        | sort -r \
        || true
    )
}

console_ready() {
    local i=$1
    local url="http://$(router_ip_for_runtime "$i"):$(router_console_port "$i")/"
    curl -fsS --max-time 2 "$url" >/dev/null 2>&1
}

wait_for_router_console() {
    local router_id="$1"
    local timeout="${2:-45}"
    local waited=0
    while [ "$waited" -lt "$timeout" ]; do
        if console_ready "$router_id"; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

wait_for_any_floodfill_console() {
    local timeout="${1:-20}"
    local waited=0
    local i
    while [ "$waited" -lt "$timeout" ]; do
        for i in $(list_floodfill_router_ids); do
            if console_ready "$i"; then
                return 0
            fi
        done
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

router_proxy_listening() {
    local i="$1"
    local ns
    local port
    ns="$(router_ns_for_runtime "$i")"
    port="$(router_proxy_port "$i")"
    sudo -n ip netns exec "$ns" ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}$"
}

fetch_i2ptunnel_list() {
    local i="$1"
    curl -fsS --max-time 5 "http://$(router_ip_for_runtime "$i"):$(router_console_port "$i")/i2ptunnel/list" 2>/dev/null || true
}

extract_i2ptunnel_nonce() {
    grep -oE 'nonce=[0-9]+' | head -n 1 | cut -d= -f2
}

start_all_tunnels_via_console() {
    local i="$1"
    local page nonce url
    page="$(fetch_i2ptunnel_list "$i")"
    [ -n "$page" ] || return 1
    nonce="$(printf '%s' "$page" | extract_i2ptunnel_nonce)"
    [ -n "$nonce" ] || return 1
    url="http://$(router_ip_for_runtime "$i"):$(router_console_port "$i")/i2ptunnel/list?nonce=${nonce}&action=Start%20all"
    curl -fsS --max-time 5 "$url" >/dev/null 2>&1 || return 1
    return 0
}

warm_client_tunnel() {
    local i="$1"
    local timeout="${2:-90}"
    local waited=0
    local page=""
    if ! wait_for_router_console "$i" 30; then
        warn "Router $i console did not become reachable for tunnel warm-up."
        return 1
    fi
    while [ "$waited" -lt "$timeout" ]; do
        if router_proxy_listening "$i"; then
            ok "Router $i client proxy is listening on 127.0.0.1:$(router_proxy_port "$i")."
            return 0
        fi
        page="$(fetch_i2ptunnel_list "$i")"
        if printf '%s' "$page" | grep -q 'statusNotRunning'; then
            start_all_tunnels_via_console "$i" >/dev/null 2>&1 || true
        elif [ -n "$page" ] && ! printf '%s' "$page" | grep -q 'statusRunning'; then
            start_all_tunnels_via_console "$i" >/dev/null 2>&1 || true
        fi
        sleep 5
        waited=$((waited + 5))
    done
    warn "Router $i client proxy did not reach LISTEN state on 127.0.0.1:$(router_proxy_port "$i") within ${timeout}s."
    return 1
}

warm_all_client_tunnels() {
    local i
    local failures=0
    log "11/11" "Post-start tunnel warm-up: ensuring client HTTP proxies are listening..."
    for i in $(seq 1 "$TOTAL_ROUTERS"); do
        info "Warming Router $i client tunnel (proxy $(router_proxy_port "$i"))..."
        warm_client_tunnel "$i" 90 || failures=$((failures + 1))
    done
    if [ "$failures" -eq 0 ]; then
        ok "All router client HTTP proxies are listening."
    else
        warn "$failures router client proxy/proxies did not reach LISTEN state during warm-up."
    fi
}

print_help() {
    cat <<EOF
Usage:
  $0
  $0 --routers N --floodfill F --yes
  $0 --routers-tsv routers.generated.tsv --subnets-tsv subnets.generated.tsv --yes
  $0 --help

Options:
  -r, --routers N       Total number of routers in direct numeric mode
  -f, --floodfill F     Number of floodfill routers in direct numeric mode
      --routers-tsv P   Router TSV generated from the topology tooling
      --subnets-tsv P   Subnet TSV generated from the topology tooling
                         (same files the GUI builder/exporter generates)
  -y, --yes             Skip confirmation prompt
  -h, --help            Show this help message
EOF
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

java_is_17_or_newer() {
    if ! command_exists java; then
        return 1
    fi
    local ver
    ver=$(java -version 2>&1 | awk -F '[".]' '/version/ {print $2; exit}')
    [ -n "$ver" ] && [ "$ver" -ge 17 ]
}

have_required_prereqs() {
    java_is_17_or_newer || return 1
    command_exists wget     || return 1
    command_exists curl     || return 1
    command_exists python3  || return 1
    command_exists unzip    || return 1
    command_exists expect   || return 1
    command_exists dos2unix || return 1
    command_exists ip       || return 1
    return 0
}

apt_locks_held() {
    sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1 && return 0
    sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 && return 0
    sudo fuser /var/cache/apt/archives/lock >/dev/null 2>&1 && return 0
    sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1 && return 0
    pgrep -x apt >/dev/null 2>&1 && return 0
    pgrep -x apt-get >/dev/null 2>&1 && return 0
    pgrep -x unattended-upgrade >/dev/null 2>&1 && return 0
    pgrep -x unattended-upgrades >/dev/null 2>&1 && return 0
    return 1
}

wait_for_apt_locks() {
    local timeout="${1:-600}"
    local waited=0
    while apt_locks_held; do
        if [ "$waited" -eq 0 ]; then
            warn "APT/dpkg is busy (often unattended-upgrades). Waiting for the lock to be released..."
        fi
        if [ "$waited" -ge "$timeout" ]; then
            die "Timed out waiting for APT/dpkg lock after ${timeout}s. Try again in a minute."
        fi
        sleep 5
        waited=$(( waited + 5 ))
    done
}

count_tsv_routers() {
    local tsv="$1"
    tail -n +2 "$tsv" | sed '/^[[:space:]]*$/d' | wc -l
}

count_tsv_floodfill() {
    local tsv="$1"
    awk -F $'\t' 'NR > 1 && tolower($18) == "true" {count++} END {print count+0}' "$tsv"
}

validate_routers_tsv() {
    local tsv="$1"
    [ -f "$tsv" ] || die "Routers TSV not found: $tsv"

    local header
    header=$(head -n 1 "$tsv")

    local expected=$'id\tname\tcountry\tcountry_code\tcity\tlat\tlon\tdisplay_lat\tdisplay_lon\tsubnet_label\tcidr\trouter_ip\tgateway_ip\tnamespace\tbridge\thost_veth\tns_veth\tfloodfill\tlocation_index\tsubnet_index\trouter_index_in_subnet'

    [ "$header" = "$expected" ] || die "Invalid routers TSV header in $tsv"
}

get_router_tsv_field() {
    local tsv="$1"
    local router_id="$2"
    local field_name="$3"

    awk -F $'\t' -v rid="$router_id" -v field="$field_name" '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == field) col = i
            }
            next
        }
        $1 == rid {
            if (col > 0) print $col
            exit
        }
    ' "$tsv"
}

validate_subnets_tsv() {
    local tsv="$1"
    [ -f "$tsv" ] || die "Subnets TSV not found: $tsv"

    local header
    header=$(head -n 1 "$tsv")

    local expected=$'subnet_label\tcidr\tgateway_ip\tcountry\tcountry_code\tcity\tbridge'

    [ "$header" = "$expected" ] || die "Invalid subnets TSV header in $tsv"
}

validate_topology_bridge_consistency() {
    local routers_tsv="$1"
    local subnets_tsv="$2"
    awk -F $'\t' '
        FNR == NR {
            if (FNR > 1) subnet_bridge[$1] = $7
            next
        }
        FNR == 1 { next }
        {
            expected = subnet_bridge[$10]
            if (expected != "" && $15 != expected) {
                printf("Router %s bridge column (%s) differs from subnet %s bridge (%s)\\n", $1, $15, $10, expected)
            }
        }
    ' "$subnets_tsv" "$routers_tsv"
}

get_subnet_tsv_field() {
    local tsv="$1"
    local subnet_label="$2"
    local field_name="$3"

    awk -F $'\t' -v label="$subnet_label" -v field="$field_name" '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == field) col = i
            }
            next
        }
        $1 == label {
            if (col > 0) print $col
            exit
        }
    ' "$tsv"
}

cidr_prefixlen() {
    local cidr="$1"
    echo "${cidr#*/}"
}

normalize_bool() {
    local val="${1:-}"
    val=$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')
    case "$val" in
        true|1|yes|y) echo "true" ;;
        *) echo "false" ;;
    esac
}

archive_testnet_logs() {
    local ts archive_dir base log_found logfile
    ts=$(date +%Y%m%d-%H%M%S)
    while IFS= read -r -d '' base; do
        log_found="false"
        while IFS= read -r -d '' logfile; do
            if [ "$log_found" = "false" ]; then
                archive_dir="$base/logs/archive/$ts"
                mkdir -p "$archive_dir"
                log_found="true"
            fi
            mv "$logfile" "$archive_dir/" 2>/dev/null || true
        done < <(find "$base" -type f             \( -name 'stdout.log' -o -name 'bootstrap.log' -o -name 'crosspollinate.log' \)             ! -path "$base/logs/archive/*" -print0 2>/dev/null)
    done < <(find "/home/$ACTUAL_USER" -maxdepth 1 -type d -name 'i2p-testnet-*' -print0 2>/dev/null)
}

list_existing_router_units() {
    local path
    shopt -s nullglob
    for path in /etc/systemd/system/i2p-router@*.service; do
        [ -e "$path" ] || continue
        basename "$path"
    done
    shopt -u nullglob
    return 0
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

TOTAL_ROUTERS=""
NUM_FF=""
AUTO_YES="false"
NON_INTERACTIVE="false"
ROUTERS_TSV=""
SUBNETS_TSV=""
USE_TOPOLOGY_TSV="false"

while [ $# -gt 0 ]; do
    case "$1" in
        -r|--routers)
            [ $# -ge 2 ] || die "Missing value after $1"
            TOTAL_ROUTERS="$2"
            NON_INTERACTIVE="true"
            shift 2
            ;;
        -f|--floodfill)
            [ $# -ge 2 ] || die "Missing value after $1"
            NUM_FF="$2"
            NON_INTERACTIVE="true"
            shift 2
            ;;
        --routers-tsv)
            [ $# -ge 2 ] || die "Missing value after $1"
            ROUTERS_TSV="$2"
            USE_TOPOLOGY_TSV="true"
            NON_INTERACTIVE="true"
            shift 2
            ;;
        --subnets-tsv)
            [ $# -ge 2 ] || die "Missing value after $1"
            SUBNETS_TSV="$2"
            USE_TOPOLOGY_TSV="true"
            NON_INTERACTIVE="true"
            shift 2
            ;;
        -y|--yes)
            AUTO_YES="true"
            NON_INTERACTIVE="true"
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            die "Unknown argument: $1"
            ;;
    esac
done

# =============================================================================
# BANNER + USER INPUT
# =============================================================================
[ -t 1 ] && clear
hr
echo -e "${BOLD}  I2P Local LAN Testnet Emulator – Namespace/Subnet Edition${NC}"
echo    "  Clean deployment handoff for isolated local I2P testnet experiments"
echo    "  Topology-driven namespace deployment, telemetry, and GUI integration"
hr
echo ""

if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
    validate_routers_tsv "$ROUTERS_TSV"
    ROUTERS_TSV="$(readlink -f "$ROUTERS_TSV")"

    if [ -z "$SUBNETS_TSV" ]; then
        SUBNETS_TSV="$(dirname "$ROUTERS_TSV")/subnets.tsv"
    fi
    validate_subnets_tsv "$SUBNETS_TSV"
    SUBNETS_TSV="$(readlink -f "$SUBNETS_TSV")"

    BRIDGE_WARNINGS="$(validate_topology_bridge_consistency "$ROUTERS_TSV" "$SUBNETS_TSV" || true)"
    if [ -n "$BRIDGE_WARNINGS" ]; then
        warn "Routers TSV contains bridge values that differ from subnet bridge definitions. Using subnet bridges at runtime."
        while IFS= read -r line; do
            [ -n "$line" ] && warn "$line"
        done <<< "$BRIDGE_WARNINGS"
    fi

    TOTAL_ROUTERS=$(count_tsv_routers "$ROUTERS_TSV")
    NUM_FF=$(count_tsv_floodfill "$ROUTERS_TSV")
    [ "$TOTAL_ROUTERS" -ge 1 ] || die "Routers TSV contains no routers."

    TESTNET_BASE="$ACTUAL_HOME/i2p-testnet-$TOTAL_ROUTERS"

    echo ""
    echo -e "${BOLD}── Topology TSV Mode ───────────────────────────────${NC}"
    printf "  %-20s %s\n" "Routers TSV:" "$ROUTERS_TSV"
    printf "  %-20s %s\n" "Subnets TSV:" "$SUBNETS_TSV"
    printf "  %-20s %s\n" "Total routers:" "$TOTAL_ROUTERS"
    printf "  %-20s %s\n" "Floodfill:" "$NUM_FF"
    printf "  %-20s %s\n" "Testnet dir:" "$TESTNET_BASE"
    printf "  %-20s %s\n" "User:" "$ACTUAL_USER"
    echo ""

    if [ "$AUTO_YES" != "true" ]; then
        read -rp "Proceed? (y/n): " go
        [[ "$go" == "y" ]] || { info "Aborted."; exit 0; }
    else
        info "Auto-confirm enabled. Proceeding without prompt."
    fi

else
    if [ "$NON_INTERACTIVE" = "true" ]; then
        [ -n "$TOTAL_ROUTERS" ] || die "Non-interactive mode requires --routers"
        [[ "$TOTAL_ROUTERS" =~ ^[0-9]+$ ]] && [ "$TOTAL_ROUTERS" -ge 2 ] \
            || die "Need at least 2 routers."

        DEFAULT_FF=$(( TOTAL_ROUTERS * 6 / 100 ))
        [ "$DEFAULT_FF" -lt 1 ] && DEFAULT_FF=1

        if [ -z "$NUM_FF" ]; then
            NUM_FF="$DEFAULT_FF"
        fi

        [[ "$NUM_FF" =~ ^[0-9]+$ ]] && [ "$NUM_FF" -le "$TOTAL_ROUTERS" ] \
            || die "Floodfill routers must be a number <= total routers."
    else
        read -rp "Total I2P routers (minimum 5 recommended): " TOTAL_ROUTERS
        [[ "$TOTAL_ROUTERS" =~ ^[0-9]+$ ]] && [ "$TOTAL_ROUTERS" -ge 2 ] \
            || die "Need at least 2 routers."

        DEFAULT_FF=$(( TOTAL_ROUTERS * 6 / 100 ))
        [ "$DEFAULT_FF" -lt 1 ] && DEFAULT_FF=1
        read -rp "Floodfill routers (~6%, default=$DEFAULT_FF): " NUM_FF
        NUM_FF="${NUM_FF:-$DEFAULT_FF}"
        [[ "$NUM_FF" =~ ^[0-9]+$ ]] && [ "$NUM_FF" -le "$TOTAL_ROUTERS" ] \
            || { warn "Invalid – using $DEFAULT_FF"; NUM_FF=$DEFAULT_FF; }
    fi

    TESTNET_BASE="$ACTUAL_HOME/i2p-testnet-$TOTAL_ROUTERS"

    echo ""
    echo -e "${BOLD}── Configuration ──────────────────────────────────${NC}"
    printf "  %-20s %s\n" "Total routers:"    "$TOTAL_ROUTERS"
    printf "  %-20s %s\n" "Floodfill:"        "$NUM_FF  (routers 1–$NUM_FF)"
    printf "  %-20s %s\n" "Regular:"          "$((TOTAL_ROUTERS-NUM_FF))  (routers $((NUM_FF+1))–$TOTAL_ROUTERS)"
    printf "  %-20s %s\n" "Testnet dir:"      "$TESTNET_BASE"
    printf "  %-20s %s\n" "I2P home:"         "$I2P_HOME"
    printf "  %-20s %s\n" "User:"             "$ACTUAL_USER"
    printf "  %-20s %s\n" "Namespaces:"       "${NS_PREFIX}1 .. ${NS_PREFIX}${TOTAL_ROUTERS}"
    printf "  %-20s %s\n" "Subnet model:"     "one /24 lab subnet per router"
    echo ""

    if [ "$AUTO_YES" != "true" ]; then
        read -rp "Proceed? (y/n): " go
        [[ "$go" == "y" ]] || { info "Aborted."; exit 0; }
    else
        info "Auto-confirm enabled. Proceeding without prompt."
    fi
fi

# =============================================================================
# STEP 1 – PREREQUISITES
# =============================================================================
CURRENT_STEP="1/11 prerequisites"
log "1/11" "Installing prerequisites..."
if have_required_prereqs; then
    ok "Required prerequisites already installed – skipping apt operations."
else
    wait_for_apt_locks 600
    sudo apt-get update -qq
    sudo apt-get install -y openjdk-17-jdk wget curl python3 \
        net-tools unzip expect dos2unix iproute2
    ok "Prerequisites ready."
fi

# =============================================================================
# PRE-CLEANUP – STOP ANY PREVIOUS TESTNET
# =============================================================================
echo ""
CURRENT_STEP="pre-cleanup"
echo "Stopping any existing testnet services and clearing stale router processes..."
archive_testnet_logs

sudo systemctl stop i2p-testnet.target 2>/dev/null || true
sudo systemctl stop i2p-testnet-net.service 2>/dev/null || true
sudo systemctl stop i2p-crosspoll.timer 2>/dev/null || true
sudo systemctl stop i2p-crosspoll.service 2>/dev/null || true

mapfile -t EXISTING_ROUTER_UNITS < <(list_existing_router_units | sort -V)

for unit in "${EXISTING_ROUTER_UNITS[@]}"; do
    [ -n "$unit" ] || continue
    sudo systemctl stop "$unit" 2>/dev/null || true
done

sudo pkill -f '/home/.*/i2p-testnet-.*/r[0-9]+/start\.sh' 2>/dev/null || true
sudo pkill -f 'net\.i2p\.router\.RouterLaunch' 2>/dev/null || true
sleep 2
sudo pkill -9 -f 'net\.i2p\.router\.RouterLaunch' 2>/dev/null || true
cleanup_network_artifacts

sleep 2
echo "Old testnet services stopped."

sudo find "/home/$ACTUAL_USER" -maxdepth 1 -type d -name 'i2p-testnet-*' \
    -exec chown -R "$ACTUAL_USER":"$ACTUAL_USER" {} \; 2>/dev/null || true

# =============================================================================
# STEP 2 – DOWNLOAD + VALIDATE INSTALLER JAR
# =============================================================================
CURRENT_STEP="2/11"
log "2/11" "Obtaining I2P installer jar..."

jar_valid() {
    [ -f "$1" ] || return 1
    [ "$(stat -c%s "$1")" -gt 10000000 ] || return 1
    unzip -t "$1" > /dev/null 2>&1 || return 1
}

get_online_i2p_version() {
    local ver=""
    ver=$(curl -fsSL --max-time 20 "https://i2p.net/en/downloads/" \
        | grep -oP 'i2pinstall_\K[0-9]+\.[0-9]+\.[0-9]+(?=\.jar)' \
        | head -1 || true)

    if [ -z "$ver" ]; then
        ver=$(curl -fsSL --max-time 20 \
            "https://api.github.com/repos/i2p/i2p.i2p/releases/latest" \
            | grep -oP '"tag_name":\s*"\K[^"]+' \
            | sed 's/^i2p-//' || true)
    fi

    echo "$ver"
}

get_installed_i2p_version() {
    local jar="$I2P_HOME/lib/router.jar"
    local impl=""
    local spec=""

    [ -f "$jar" ] || return 1

    impl=$(unzip -p "$jar" META-INF/MANIFEST.MF 2>/dev/null \
        | awk -F': ' '/^Implementation-Version:/ {
            gsub(/\r/,"",$2)
            sub(/-[0-9]+$/, "", $2)
            print $2
            exit
        }')

    if [ -n "$impl" ]; then
        echo "$impl"
        return 0
    fi

    spec=$(unzip -p "$jar" META-INF/MANIFEST.MF 2>/dev/null \
        | awk -F': ' '/^Specification-Version:/ {
            gsub(/\r/,"",$2)
            print $2
            exit
        }')

    [ -n "$spec" ] && echo "$spec"
}

VER="$(get_online_i2p_version || true)"

INSTALLED_VER="$(get_installed_i2p_version || true)"
if [ -n "${INSTALLED_VER:-}" ]; then
    info "Installed I2P version: $INSTALLED_VER"
else
    info "Installed I2P version: not found"
fi

if [ -n "${VER:-}" ]; then
    info "Latest available I2P version: $VER"
else
    warn "Could not detect latest I2P version online. Network/DNS may be unavailable."
fi

NEED_INSTALL="true"

if [ -n "${VER:-}" ]; then
    if [ -n "${INSTALLED_VER:-}" ] && [ "$INSTALLED_VER" = "$VER" ] && [ -f "$I2P_HOME/lib/router.jar" ]; then
        NEED_INSTALL="false"
    fi
else
    if [ -n "${INSTALLED_VER:-}" ] && [ -f "$I2P_HOME/lib/router.jar" ]; then
        NEED_INSTALL="false"
        VER="$INSTALLED_VER"
        info "Proceeding with installed I2P version because online version check is unavailable."
    elif jar_valid "$INSTALLER_JAR"; then
        NEED_INSTALL="true"
        info "Proceeding with existing local installer jar because online version check is unavailable."
    else
        die "Cannot detect latest I2P version, and no usable installed version or local installer jar is available."
    fi
fi

if [ "$NEED_INSTALL" = "false" ]; then
    if jar_valid "$INSTALLER_JAR"; then
        ok "Usable installer jar already present."
    else
        warn "Installer jar not present or invalid, but installed I2P is usable."
    fi
else
    if jar_valid "$INSTALLER_JAR"; then
        ok "Using existing local installer jar: $INSTALLER_JAR"
    else
        [ -n "${VER:-}" ] || die "Cannot download installer because online version is unknown."
        info "Downloading I2P $VER..."
        wget --timeout=120 --tries=3 --show-progress \
            "https://files.i2p.net/${VER}/i2pinstall_${VER}.jar" \
            -O "$INSTALLER_JAR" || die "Download failed."
        jar_valid "$INSTALLER_JAR" || die "Downloaded jar is corrupt."
        ok "Installer downloaded: $INSTALLER_JAR"
    fi
fi

# =============================================================================
# STEP 3 – INSTALL / UPDATE I2P
# =============================================================================
CURRENT_STEP="3/11"
log "3/11" "Installing I2P to $I2P_HOME..."

if [ "$NEED_INSTALL" = "false" ]; then
    ok "I2P $INSTALLED_VER is already the latest version – skipping reinstall."
else
    if [ -d "$I2P_HOME" ]; then
        warn "Outdated or partial I2P installation detected in $I2P_HOME"
        warn "Removing old I2P installation before installing $VER..."
        rm -rf "$I2P_HOME"
    fi

    mkdir -p "$I2P_HOME"
    EXPECT_SCRIPT="$ACTUAL_HOME/i2p_install.exp"

    cat > "$EXPECT_SCRIPT" << 'EXPEOF'
#!/usr/bin/expect -f
set timeout 300
set installer  [lindex $argv 0]
set installdir [lindex $argv 1]
spawn java -jar $installer -console
while 1 {
    expect {
        -re {Select the installation path:} { sleep 0.3; send "$installdir\r" }
        -re {Press 1 to accept}             { send "1\r" }
        -re {Press 1 to continue}           { send "1\r" }
        -re {Input selection:}              { send "\r"  }
        -re {[Cc]reate (desktop|shortcut)}  { send "N\r" }
        -re {Press ENTER to exit}           { send "\r"; break }
        eof     { break }
        timeout { puts "\n[expect] TIMEOUT: $expect_out(buffer)"; exit 1 }
    }
}
EXPEOF

    chmod +x "$EXPECT_SCRIPT"
    sudo -u "$ACTUAL_USER" "$EXPECT_SCRIPT" "$INSTALLER_JAR" "$I2P_HOME" \
        || die "Installer failed."

    if [ ! -f "$I2P_HOME/lib/router.jar" ] && \
       [ -f "$I2P_HOME/i2p/lib/router.jar" ]; then
        mv "$I2P_HOME/i2p/"* "$I2P_HOME/" && rmdir "$I2P_HOME/i2p"
    fi

    [ -f "$I2P_HOME/lib/router.jar" ] || die "router.jar missing after install."

    NEW_INSTALLED_VER="$(get_installed_i2p_version || true)"
    if [ -n "$NEW_INSTALLED_VER" ]; then
        ok "I2P installed successfully. Installed version: $NEW_INSTALLED_VER"
    else
        ok "I2P installed successfully."
    fi
fi

# =============================================================================
# STEP 4 – CLASSPATH
# =============================================================================
CURRENT_STEP="4/11"
log "4/11" "Building Java classpath..."
CLASSPATH=$(find "$I2P_HOME/lib" -name "*.jar" 2>/dev/null | sort | tr '\n' ':')
[ -z "$CLASSPATH" ] && die "No JARs in $I2P_HOME/lib"
echo "CLASSPATH='$CLASSPATH'" > "$ACTUAL_HOME/.i2p_classpath"
chown "$ACTUAL_USER" "$ACTUAL_HOME/.i2p_classpath"
ok "Classpath: $(echo "$CLASSPATH" | tr ':' '\n' | grep -c '\.jar') JARs"

# =============================================================================
# STEP 5 – NETWORK FABRIC + PER-ROUTER DIRS / CONFIGS
# =============================================================================
CURRENT_STEP="5/11"
log "5/11" "Creating network fabric and per-router configurations..."

if [ -d "$TESTNET_BASE" ]; then
    warn "Existing target directory detected: $TESTNET_BASE"
    warn "Removing it first so this deployment is fully clean."
    rm -rf "$TESTNET_BASE"
fi
mkdir -p "$TESTNET_BASE"
TOPOLOGY_MAP="$TESTNET_BASE/topology-map.tsv"
NETWORK_SETUP="$TESTNET_BASE/setup-network.sh"

cat > "$NETWORK_SETUP" <<EOF
#!/bin/bash
set -euo pipefail

CURRENT_STEP="startup"
trap 'echo -e "\n${RED:-}✗${NC:-} Failed during: ${CURRENT_STEP} (line $LINENO)" >&2' ERR
TOTAL="$TOTAL_ROUTERS"
ROUTERS_TSV="$ROUTERS_TSV"
SUBNETS_TSV="$SUBNETS_TSV"
USE_TOPOLOGY_TSV="$USE_TOPOLOGY_TSV"
NS_PREFIX="$NS_PREFIX"
BR_PREFIX="$BR_PREFIX"
HV_PREFIX="$HV_PREFIX"
NV_PREFIX="$NV_PREFIX"

router_ns_name()   { echo "\${NS_PREFIX}\$1"; }
router_br_name()   { echo "\${BR_PREFIX}\$1"; }
router_host_veth() { echo "\${HV_PREFIX}\$1"; }
router_ns_veth()   { echo "\${NV_PREFIX}\$1"; }

calc_octets() {
    local idx=\$1
    local oct2=\$(( 210 + ((idx - 1) / 250) ))
    local oct3=\$(( ((idx - 1) % 250) + 1 ))
    echo "\$oct2 \$oct3"
}

router_gateway_ip_legacy() {
    local oct2 oct3
    read -r oct2 oct3 <<< "\$(calc_octets "\$1")"
    echo "10.\${oct2}.\${oct3}.1"
}

router_ip_legacy() {
    local oct2 oct3
    read -r oct2 oct3 <<< "\$(calc_octets "\$1")"
    echo "10.\${oct2}.\${oct3}.2"
}

get_router_tsv_field() {
    local tsv="\$1"
    local router_id="\$2"
    local field_name="\$3"

    awk -F \$'\\t' -v rid="\$router_id" -v field="\$field_name" '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if (\$i == field) col = i
            }
            next
        }
        \$1 == rid {
            if (col > 0) print \$col
            exit
        }
    ' "\$tsv"
}

get_subnet_tsv_field() {
    local tsv="\$1"
    local subnet_label="\$2"
    local field_name="\$3"

    awk -F \$'\\t' -v label="\$subnet_label" -v field="\$field_name" '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if (\$i == field) col = i
            }
            next
        }
        \$1 == label {
            if (col > 0) print \$col
            exit
        }
    ' "\$tsv"
}

cidr_prefixlen() {
    local cidr="\$1"
    echo "\${cidr#*/}"
}

router_gateway_ip() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "\$ROUTERS_TSV" "\$i" "gateway_ip"
    else
        router_gateway_ip_legacy "\$i"
    fi
}

router_ip() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "\$ROUTERS_TSV" "\$i" "router_ip"
    else
        router_ip_legacy "\$i"
    fi
}

router_ns() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "\$ROUTERS_TSV" "\$i" "namespace"
    else
        router_ns_name "\$i"
    fi
}

router_hv() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "\$ROUTERS_TSV" "\$i" "host_veth"
    else
        router_host_veth "\$i"
    fi
}

router_nv() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "\$ROUTERS_TSV" "\$i" "ns_veth"
    else
        router_ns_veth "\$i"
    fi
}

router_subnet_label() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "\$ROUTERS_TSV" "\$i" "subnet_label"
    else
        echo "r\$i"
    fi
}

router_bridge() {
    local i="\$1"
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        local subnet_label
        subnet_label="\$(router_subnet_label "\$i")"
        get_subnet_tsv_field "\$SUBNETS_TSV" "\$subnet_label" "bridge"
    else
        router_br_name "\$i"
    fi
}

delete_router_net() {
    local i=\$1
    local ns="\$(router_ns "\$i")"
    sudo ip netns delete "\$ns" 2>/dev/null || true
}

delete_all_bridges() {
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        while IFS=\$'\\t' read -r subnet_label cidr gateway_ip country country_code city bridge; do
            [ "\$subnet_label" = "subnet_label" ] && continue
            [ -n "\$bridge" ] || continue
            sudo ip link delete "\$bridge" 2>/dev/null || true
        done < "\$SUBNETS_TSV"
    else
        local i
        for i in \$(seq 1 "\$TOTAL"); do
            sudo ip link delete "\$(router_br_name "\$i")" 2>/dev/null || true
        done
    fi
}

create_subnet_bridges() {
    while IFS=\$'\\t' read -r subnet_label cidr gateway_ip country country_code city bridge; do
        [ "\$subnet_label" = "subnet_label" ] && continue
        [ -n "\$bridge" ] || continue

        prefix="\$(cidr_prefixlen "\$cidr")"

        sudo ip link delete "\$bridge" 2>/dev/null || true
        sudo ip link add name "\$bridge" type bridge
        sudo ip addr add "\${gateway_ip}/\${prefix}" dev "\$bridge"
        sudo ip link set "\$bridge" up
    done < "\$SUBNETS_TSV"

    sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null
}

attach_router_to_network() {
    local i=\$1
    local ns="\$(router_ns "\$i")"
    local hv="\$(router_hv "\$i")"
    local nv="\$(router_nv "\$i")"
    local br="\$(router_bridge "\$i")"
    local rip="\$(router_ip "\$i")"
    local gw="\$(router_gateway_ip "\$i")"
    local cidr
    local prefix

    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        cidr="\$(get_router_tsv_field "\$ROUTERS_TSV" "\$i" "cidr")"
    else
        cidr="\$(echo "\$gw" | awk -F. '{print \$1 "." \$2 "." \$3 ".0/24"}')"
    fi
    prefix="\$(cidr_prefixlen "\$cidr")"

    delete_router_net "\$i"

    sudo ip netns add "\$ns"
    sudo ip link add "\$hv" type veth peer name "\$nv"
    sudo ip link set "\$hv" master "\$br"
    sudo ip link set "\$hv" up
    sudo ip link set "\$nv" netns "\$ns"

    sudo ip -n "\$ns" link set lo up
    sudo ip -n "\$ns" link set "\$nv" name eth0
    sudo ip -n "\$ns" addr add "\${rip}/\${prefix}" dev eth0
    sudo ip -n "\$ns" link set eth0 up
    sudo ip -n "\$ns" route add default via "\$gw"
}

cleanup_all() {
    local ns
    while read -r ns; do
        [ -n "\$ns" ] || continue
        sudo ip netns delete "\$ns" 2>/dev/null || true
    done < <(ip netns list 2>/dev/null | awk '{print \$1}' | grep -E "^\\\${NS_PREFIX}[0-9]+$" || true)

    delete_all_bridges

    local link
    while read -r link; do
        [ -n "\$link" ] || continue
        sudo ip link delete "\$link" 2>/dev/null || true
    done < <(
        ip -o link show 2>/dev/null \
        | awk -F': ' '{print \$2}' \
        | cut -d@ -f1 \
        | grep -E "^(\\\${HV_PREFIX}|\\\${NV_PREFIX})[0-9]+$" \
        | sort -r \
        || true
    )
}

case "\${1:-up}" in
  up)
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        create_subnet_bridges
        for i in \$(seq 1 "\$TOTAL"); do
            attach_router_to_network "\$i"
        done
    else
        for i in \$(seq 1 "\$TOTAL"); do
            br="\$(router_bridge "\$i")"
            gw="\$(router_gateway_ip "\$i")"
            prefix="24"
            sudo ip link delete "\$br" 2>/dev/null || true
            sudo ip link add name "\$br" type bridge
            sudo ip addr add "\${gw}/\${prefix}" dev "\$br"
            sudo ip link set "\$br" up
            sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null
            attach_router_to_network "\$i"
        done
    fi
    ;;
  down)
    cleanup_all
    ;;
  rebuild)
    cleanup_all
    if [ "\$USE_TOPOLOGY_TSV" = "true" ]; then
        create_subnet_bridges
        for i in \$(seq 1 "\$TOTAL"); do
            attach_router_to_network "\$i"
        done
    else
        for i in \$(seq 1 "\$TOTAL"); do
            br="\$(router_bridge "\$i")"
            gw="\$(router_gateway_ip "\$i")"
            prefix="24"
            sudo ip link delete "\$br" 2>/dev/null || true
            sudo ip link add name "\$br" type bridge
            sudo ip addr add "\${gw}/\${prefix}" dev "\$br"
            sudo ip link set "\$br" up
            sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null
            attach_router_to_network "\$i"
        done
    fi
    ;;
  *)
    echo "Usage: \$0 {up|down|rebuild}" >&2
    exit 1
    ;;
esac
EOF

chmod +x "$NETWORK_SETUP"
chown "$ACTUAL_USER":"$ACTUAL_USER" "$NETWORK_SETUP"

: > "$TOPOLOGY_MAP"
printf "router_id\tcountry\tcountry_code\tcity\tdisplay_lat\tdisplay_lon\tnamespace\tbridge\tsubnet_label\tsubnet\tgateway\tip\tconsole_port\tconsole_url\tntcp_port\tudp_port\tfloodfill\n" >> "$TOPOLOGY_MAP"

for i in $(seq 1 "$TOTAL_ROUTERS"); do
    mkdir -p "$TESTNET_BASE/r$i"/{logs,data/netDb,config}

    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        IS_FF=$(normalize_bool "$(get_router_tsv_field "$ROUTERS_TSV" "$i" "floodfill")")
        UDP_PORT=$(router_udp_port "$i")
        NTCP_PORT=$(router_ntcp_port "$i")
        CON_PORT=$(router_console_port "$i")
        HTTP_PROXY_PORT=$(router_proxy_port "$i")

        ROUTER_NS=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "namespace")
        SUBNET_LABEL=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "subnet_label")
        ROUTER_BR=$(get_subnet_tsv_field "$SUBNETS_TSV" "$SUBNET_LABEL" "bridge")
        HOST_VETH=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "host_veth")
        NS_VETH=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "ns_veth")
        SUBNET_CIDR=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "cidr")
        GATEWAY_IP=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "gateway_ip")
        ROUTER_IP=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "router_ip")
        COUNTRY=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "country")
        COUNTRY_CODE=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "country_code")
        CITY=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "city")
        DISPLAY_LAT=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "display_lat")
        DISPLAY_LON=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "display_lon")
        CONSOLE_URL="http://${ROUTER_IP}:${CON_PORT}"
    else
        IS_FF="false"; [ "$i" -le "$NUM_FF" ] && IS_FF="true"
        UDP_PORT=$(router_udp_port "$i")
        NTCP_PORT=$(router_ntcp_port "$i")
        CON_PORT=$(router_console_port "$i")
        HTTP_PROXY_PORT=$(router_proxy_port "$i")

        ROUTER_NS=$(router_ns_name "$i")
        ROUTER_BR=$(router_br_name "$i")
        HOST_VETH=$(router_host_veth "$i")
        NS_VETH=$(router_ns_veth "$i")
        SUBNET_CIDR=$(router_subnet "$i")
        GATEWAY_IP=$(router_gateway_ip "$i")
        ROUTER_IP=$(router_ip "$i")
        COUNTRY=""
        COUNTRY_CODE=""
        CITY=""
        DISPLAY_LAT=""
        DISPLAY_LON=""
        SUBNET_LABEL=""
        CONSOLE_URL="http://${ROUTER_IP}:${CON_PORT}"
    fi

    CFG="$TESTNET_BASE/r$i/config/router.config"

    cat > "$CFG" <<RCEOF
# =============================================================
# I2P Testnet Router $i  |  floodfill=$IS_FF
# Namespace/subnet-isolated edition
# =============================================================

# ── Directories ───────────────────────────────────────────────
i2p.dir.base=$I2P_HOME
i2p.dir.config=$TESTNET_BASE/r$i/config
i2p.dir.router=$TESTNET_BASE/r$i/data
i2p.dir.data=$TESTNET_BASE/r$i/data
i2p.dir.log=$TESTNET_BASE/r$i/logs

# ── Transport: namespace IP, not loopback ────────────────────
i2np.allowLocal=true
i2np.ntcp.enable=true
i2np.udp.enable=true
i2np.ntcp.host=$ROUTER_IP
i2np.ntcp.port=$NTCP_PORT
i2np.udp.host=$ROUTER_IP
i2np.udp.port=$UDP_PORT

# ── Router console ────────────────────────────────────────────
routerconsole.port=$CON_PORT
routerconsole.host=0.0.0.0
routerconsole.auth.enable=false

# ── GUI / lab metadata ───────────────────────────────────────
router.testnet.namespace=$ROUTER_NS
router.testnet.bridge=$ROUTER_BR
router.testnet.subnet=$SUBNET_CIDR
router.testnet.subnetLabel=$SUBNET_LABEL
router.testnet.gateway=$GATEWAY_IP
router.testnet.ip=$ROUTER_IP
router.testnet.consoleHost=$ROUTER_IP
router.testnet.consoleURL=$CONSOLE_URL
router.testnet.hostVeth=$HOST_VETH
router.testnet.nsVeth=eth0
router.testnet.country=$COUNTRY
router.testnet.countryCode=$COUNTRY_CODE
router.testnet.city=$CITY
router.testnet.displayLat=$DISPLAY_LAT
router.testnet.displayLon=$DISPLAY_LON
router.testnet.measurementEepsiteName=testnet-r1.i2p
router.testnet.measurementEepsiteRole=$([ "$i" -eq 1 ] && echo server || echo client)

# ── Network isolation ────────────────────────────────────────
router.networkID=99

# ── Reseed: disabled (static private bootstrap) ──────────────
i2p.reseedURLList=
i2p.reseedURL=
router.reseedCompleted=true

# ── Disable internet-dependent extras ────────────────────────
router.newsRefreshFrequency=0
time.disabled=true
time.sntpServerList=
router.blocklist.enable=false
i2np.upnp.enable=false

# ── Role ─────────────────────────────────────────────────────
router.floodfillParticipant=$IS_FF
router.isHidden=false
routerconsole.welcomeWizardComplete=true

# ── Bandwidth ────────────────────────────────────────────────
i2np.bandwidth.inboundKBytesPerSecond=5120
i2np.bandwidth.outboundKBytesPerSecond=5120
i2np.tunnel.participatingLimit=100

# ── Small-testnet tunnel settings ────────────────────────────
tunnel.default.length=1
tunnel.default.lengthVariance=0

router.exploratory.inboundLength=1
router.exploratory.inboundLengthVariance=0
router.exploratory.inboundQuantity=1
router.exploratory.inboundBackupQuantity=0

router.exploratory.outboundLength=1
router.exploratory.outboundLengthVariance=0
router.exploratory.outboundQuantity=1
router.exploratory.outboundBackupQuantity=0

router.defaultInboundTunnelLength=1
router.defaultInboundTunnelQuantity=1
router.defaultInboundBackupQuantity=0
router.defaultInboundTunnelLengthVariance=0

router.defaultOutboundTunnelLength=1
router.defaultOutboundTunnelQuantity=1
router.defaultOutboundBackupQuantity=0
router.defaultOutboundTunnelLengthVariance=0

# ── Peer thresholds ──────────────────────────────────────────
router.minThreshold=2
router.maxThreshold=20

# ── Logging ──────────────────────────────────────────────────
logger.record.enable=true
logger.record.file=$TESTNET_BASE/r$i/logs/log-router-$i.txt
RCEOF

    mkdir -p "$TESTNET_BASE/r$i/config/clients.config.d"
    mkdir -p "$TESTNET_BASE/r$i/config/i2ptunnel.config.d"

    OUT_CC="$TESTNET_BASE/r$i/config/clients.config.d/10-testnet-clients.config"
    cat > "$OUT_CC" <<CCEOF
clientApp.0.main=net.i2p.router.web.RouterConsoleRunner
clientApp.0.name=Router Console
clientApp.0.args=$CON_PORT 0.0.0.0 ./webapps/
clientApp.0.delay=1
clientApp.0.onBoot=true
clientApp.0.startOnLoad=true

clientApp.1.main=net.i2p.i2ptunnel.TunnelControllerGroup
clientApp.1.name=Application tunnels
clientApp.1.args=./i2ptunnel.config
clientApp.1.delay=5
clientApp.1.onBoot=true
clientApp.1.startOnLoad=true
CCEOF

    OUT_TUN="$TESTNET_BASE/r$i/config/i2ptunnel.config"
    cat > "$OUT_TUN" <<TUNEOF
tunnel.0.type=httpclient
tunnel.0.name=Router $i Client Tunnel
tunnel.0.description=Auto-created client HTTP proxy for emulator testing
tunnel.0.interface=127.0.0.1
tunnel.0.listenPort=$HTTP_PROXY_PORT
tunnel.0.startOnLoad=true
tunnel.0.sharedClient=false

tunnel.0.option.inbound.length=1
tunnel.0.option.outbound.length=1
tunnel.0.option.inbound.quantity=1
tunnel.0.option.outbound.quantity=1
tunnel.0.option.inbound.backupQuantity=0
tunnel.0.option.outbound.backupQuantity=0
TUNEOF

    if [[ "$i" == "1" ]]; then
        cat >> "$OUT_TUN" <<TUNEOF

tunnel.1.type=httpserver
tunnel.1.name=Router 1 Internal Eepsite
tunnel.1.description=Internal eepsite exposing Router 1 console for measurement
tunnel.1.targetHost=127.0.0.1
tunnel.1.targetPort=$CON_PORT
tunnel.1.spoofedHost=testnet-r1.i2p
tunnel.1.privKeyFile=router1-eepsite-keys.dat
tunnel.1.startOnLoad=true

tunnel.1.option.inbound.length=1
tunnel.1.option.outbound.length=1
tunnel.1.option.inbound.quantity=1
tunnel.1.option.outbound.quantity=1
tunnel.1.option.inbound.backupQuantity=0
tunnel.1.option.outbound.backupQuantity=0
TUNEOF
    fi

    cat > "$TESTNET_BASE/r$i/start.sh" <<STARTEOF
#!/bin/bash
source "$ACTUAL_HOME/.i2p_classpath"
rm -f "$TESTNET_BASE/r$i/data/router.ping"   2>/dev/null || true
rm -f "$TESTNET_BASE/r$i/config/router.ping" 2>/dev/null || true
find  "$TESTNET_BASE/r$i/data" -name "*.lck" -delete 2>/dev/null || true
exec java \
  -Di2p.dir.base="$I2P_HOME" \
  -Di2p.dir.config="$TESTNET_BASE/r$i/config" \
  -Di2p.dir.router="$TESTNET_BASE/r$i/data" \
  -Di2p.dir.data="$TESTNET_BASE/r$i/data" \
  -Di2p.dir.log="$TESTNET_BASE/r$i/logs" \
  -Xms64m -Xmx256m \
  -cp "\$CLASSPATH" \
  net.i2p.router.RouterLaunch
STARTEOF

    cat > "$TESTNET_BASE/r$i/run-in-netns.sh" <<RUNEOF
#!/bin/bash
set -euo pipefail

CURRENT_STEP="startup"
trap 'echo -e "\n${RED:-}✗${NC:-} Failed during: ${CURRENT_STEP} (line $LINENO)" >&2' ERR
exec ip netns exec "$ROUTER_NS" runuser -u "$ACTUAL_USER" -- bash "$TESTNET_BASE/r$i/start.sh"
RUNEOF

    chmod +x "$TESTNET_BASE/r$i/start.sh" "$TESTNET_BASE/r$i/run-in-netns.sh"
    sudo chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$TESTNET_BASE/r$i" 2>/dev/null || true

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$i" "$COUNTRY" "$COUNTRY_CODE" "$CITY" "$DISPLAY_LAT" "$DISPLAY_LON" \
        "$ROUTER_NS" "$ROUTER_BR" "$SUBNET_LABEL" "$SUBNET_CIDR" "$GATEWAY_IP" "$ROUTER_IP" \
        "$CON_PORT" "$CONSOLE_URL" "$NTCP_PORT" "$UDP_PORT" "$IS_FF" >> "$TOPOLOGY_MAP"

    ok "Router $i  FF=$IS_FF  ns=$ROUTER_NS  ip=$ROUTER_IP  subnet=$SUBNET_CIDR  console=$CONSOLE_URL"
done

sudo bash "$NETWORK_SETUP" rebuild
ok "Namespace/bridge fabric created."

# =============================================================================
# STEP 6 – PHASE A: BOOTSTRAP ROUTER #1 → readiness seed
# =============================================================================
CURRENT_STEP="6/11"
log "6/11" "Phase A: Bootstrapping Router #1 inside its namespace (console-first readiness, up to 45 s)..."

find "$TESTNET_BASE/r1" \( -name "router.ping" -o -name "*.lck" \) \
    -delete 2>/dev/null || true

sudo ip netns exec "$(router_ns_for_runtime 1)" \
    runuser -u "$ACTUAL_USER" -- bash "$TESTNET_BASE/r1/start.sh" \
    > "$TESTNET_BASE/r1/logs/bootstrap.log" 2>&1 &
BOOT_PID=$!

echo -n "  Waiting for router console"
CONSOLE_OK="false"
for s in $(seq 1 45); do
    sleep 1
    echo -n "."
    if console_ready 1; then
        CONSOLE_OK="true"
        echo -e "  ${GREEN}✓ console reachable at ${s}s${NC}"
        break
    fi
done
echo ""

RI_FILE=$(find "$TESTNET_BASE/r1/data" -name "routerInfo-*.dat" 2>/dev/null | head -1 || true)

kill "$BOOT_PID" 2>/dev/null || true
wait "$BOOT_PID" 2>/dev/null || true
sleep 2
rm -f "$TESTNET_BASE/r1/data/router.ping"   2>/dev/null || true
rm -f "$TESTNET_BASE/r1/config/router.ping" 2>/dev/null || true

if [ "$CONSOLE_OK" = "true" ]; then
    ok "Router #1 bootstrap console became reachable."
    if [ -n "$RI_FILE" ]; then
        ok "Router #1 RouterInfo prepared: $(basename "$RI_FILE")"
    else
        warn "Router #1 console is up, but RouterInfo was not yet observed during bootstrap seeding."
    fi
else
    warn "Router #1 console did not become reachable within 45 s. Check bootstrap.log."
    if [ -n "$RI_FILE" ]; then
        warn "RouterInfo exists despite delayed console readiness: $(basename "$RI_FILE")"
    else
        warn "Continuing – routers will still start, but peer formation may take longer."
    fi
fi

# =============================================================================
# STEP 7 – PHASE A: PRE-SEED ALL OTHER ROUTERS' netDb
# =============================================================================
CURRENT_STEP="7/11"
log "7/11" "Phase A: Pre-seeding all routers' netDb from Router #1..."

RI_FILES=$(find "$TESTNET_BASE/r1/data" \
    -name "routerInfo-*.dat" 2>/dev/null || true)
RI_COUNT=$(echo "$RI_FILES" | grep -c '\.dat' 2>/dev/null || echo 0)

for i in $(seq 2 "$TOTAL_ROUTERS"); do
    mkdir -p "$TESTNET_BASE/r$i/data/netDb"
    if [ "$RI_COUNT" -gt 0 ]; then
        echo "$RI_FILES" | while read -r f; do
            [ -n "$f" ] && cp "$f" "$TESTNET_BASE/r$i/data/netDb/"
        done
        sudo chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$TESTNET_BASE/r$i/data" 2>/dev/null || true
        ok "Router $i netDb seeded with $RI_COUNT file(s) from Router #1"
    else
        warn "Router $i netDb: no files to seed (Router #1 generated none)"
    fi
done

# =============================================================================
# STEP 8 – WRITE THE CROSS-POLLINATOR SCRIPT
# =============================================================================
CURRENT_STEP="8/11"
log "8/11" "Writing cross-pollinator script..."

CROSSPOLL="$TESTNET_BASE/crosspollinate.sh"
cat > "$CROSSPOLL" <<CPEOF
#!/bin/bash
TESTNET_BASE="$TESTNET_BASE"
TOTAL=$TOTAL_ROUTERS
ACTUAL_USER="$ACTUAL_USER"
LOG="\$TESTNET_BASE/crosspollinate.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
echo "\$(ts)  Cross-pollination starting..." >> "\$LOG"

TMPDIR_CP=\$(mktemp -d)
COLLECTED=0
for i in \$(seq 1 "\$TOTAL"); do
    while IFS= read -r -d '' f; do
        cp "\$f" "\$TMPDIR_CP/" 2>/dev/null && COLLECTED=\$(( COLLECTED + 1 ))
    done < <(find "\$TESTNET_BASE/r\$i/data" -name "routerInfo-*.dat" -print0 2>/dev/null)
done
echo "\$(ts)  Collected \$COLLECTED RouterInfo files." >> "\$LOG"

COPIED_TOTAL=0
for i in \$(seq 1 "\$TOTAL"); do
    mkdir -p "\$TESTNET_BASE/r\$i/data/netDb"
    COPIED=0
    for f in "\$TMPDIR_CP"/routerInfo-*.dat; do
        [ -f "\$f" ] || continue
        DEST="\$TESTNET_BASE/r\$i/data/netDb/\$(basename "\$f")"
        cp "\$f" "\$DEST" 2>/dev/null && COPIED=\$(( COPIED + 1 ))
    done
    chown -R "\$ACTUAL_USER":"\$ACTUAL_USER" "\$TESTNET_BASE/r\$i/data/netDb" 2>/dev/null || true
    COPIED_TOTAL=\$(( COPIED_TOTAL + COPIED ))
done
rm -rf "\$TMPDIR_CP"

echo "\$(ts)  Distributed \$COPIED_TOTAL RouterInfo entries across \$TOTAL routers." >> "\$LOG"
echo "\$(ts)  Cross-pollination complete." >> "\$LOG"
echo "Cross-pollination done: \$COLLECTED files → \$TOTAL routers."
CPEOF
chmod +x "$CROSSPOLL"
chown "$ACTUAL_USER":"$ACTUAL_USER" "$CROSSPOLL"
ok "Cross-pollinator: $CROSSPOLL"

# =============================================================================
# STEP 9 – SYSTEMD SERVICES + TARGET + NETWORK FABRIC SERVICE
# =============================================================================
CURRENT_STEP="9/11"
log "9/11" "Installing systemd services..."

sudo systemctl stop i2p-testnet.target 2>/dev/null || true
sudo systemctl stop i2p-testnet-net.service 2>/dev/null || true
sudo systemctl stop i2p-crosspoll.service 2>/dev/null || true
sudo systemctl stop i2p-crosspoll.timer 2>/dev/null || true

info "Removing previous systemd router units..."
mapfile -t EXISTING_ROUTER_UNITS_STEP9 < <(list_existing_router_units | sort -V)

for unit in "${EXISTING_ROUTER_UNITS_STEP9[@]}"; do
    [ -n "$unit" ] || continue
    sudo systemctl stop "$unit" 2>/dev/null || true
    sudo systemctl disable "$unit" 2>/dev/null || true
done

sudo rm -f /etc/systemd/system/i2p-router@*.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/i2p-testnet.target
sudo rm -f /etc/systemd/system/i2p-testnet-net.service
sudo rm -f /etc/systemd/system/i2p-crosspoll.service
sudo rm -f /etc/systemd/system/i2p-crosspoll.timer
ok "Previous systemd unit files removed."

sudo tee /etc/systemd/system/i2p-testnet-net.service > /dev/null <<SEOF
[Unit]
Description=I2P Testnet Namespace/Subnet Fabric
After=network.target
PartOf=i2p-testnet.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$NETWORK_SETUP up
ExecStop=$NETWORK_SETUP down

[Install]
WantedBy=i2p-testnet.target
SEOF
ok "Service: i2p-testnet-net.service"

FF_IDS_SYSTEMD="$(list_floodfill_router_ids || true)"

for i in $(seq 1 "$TOTAL_ROUTERS"); do
    IS_FF=$(router_floodfill_for_runtime "$i")
    ROUTER_NS=$(router_ns_for_runtime "$i")
    ROUTER_IP=$(router_ip_for_runtime "$i")
    CON=$(router_console_port "$i")

    if [ "$IS_FF" = "true" ]; then
        AFTER_LINE="After=network.target i2p-testnet-net.service"
        PRE_SLEEP="ExecStartPre=/bin/sleep 3"
    else
        if [ -n "$FF_IDS_SYSTEMD" ]; then
            FF_LIST=$(echo "$FF_IDS_SYSTEMD" | xargs -I{} printf "i2p-router@%s.service " "{}")
            AFTER_LINE="After=network.target i2p-testnet-net.service ${FF_LIST}"
        else
            AFTER_LINE="After=network.target i2p-testnet-net.service"
        fi
        PRE_SLEEP="ExecStartPre=/bin/sleep 8"
    fi

    sudo tee "/etc/systemd/system/i2p-router@${i}.service" > /dev/null <<SEOF
[Unit]
Description=I2P Testnet Router $i (FF=$IS_FF, namespace=$ROUTER_NS, console=$ROUTER_IP:$CON)
Requires=i2p-testnet-net.service
$AFTER_LINE
PartOf=i2p-testnet.target
Documentation=https://i2p.net/

[Service]
Type=simple
WorkingDirectory=$TESTNET_BASE/r$i
$PRE_SLEEP
ExecStart=$TESTNET_BASE/r$i/run-in-netns.sh
Restart=on-failure
RestartSec=10
TimeoutStopSec=25
TimeoutStartSec=120
KillMode=mixed
StandardOutput=append:$TESTNET_BASE/r$i/logs/stdout.log
StandardError=append:$TESTNET_BASE/r$i/logs/stdout.log

[Install]
WantedBy=i2p-testnet.target
SEOF
    ok "Service: i2p-router@${i}.service  (FF=$IS_FF  ns=$ROUTER_NS  console=$ROUTER_IP:$CON)"
done

sudo tee /etc/systemd/system/i2p-crosspoll.service > /dev/null <<SEOF
[Unit]
Description=I2P Testnet NetDB Cross-Pollinator
After=i2p-testnet-net.service i2p-router@1.service

[Service]
Type=oneshot
User=$ACTUAL_USER
ExecStart=$CROSSPOLL
StandardOutput=journal
StandardError=journal
SEOF

sudo tee /etc/systemd/system/i2p-crosspoll.timer > /dev/null <<SEOF
[Unit]
Description=I2P Testnet Cross-Pollinator Timer
After=i2p-testnet.target

[Timer]
OnActiveSec=1min
OnUnitActiveSec=2min
Unit=i2p-crosspoll.service

[Install]
WantedBy=i2p-testnet.target
SEOF

WANTS=$(seq 1 "$TOTAL_ROUTERS" | xargs printf "i2p-router@%d.service ")
sudo tee /etc/systemd/system/i2p-testnet.target > /dev/null <<SEOF
[Unit]
Description=I2P Local LAN Testnet ($TOTAL_ROUTERS routers, $NUM_FF FF, topology-defined subnets)
Wants=i2p-testnet-net.service ${WANTS}i2p-crosspoll.timer

[Install]
WantedBy=multi-user.target
SEOF

sudo systemctl daemon-reload
sudo systemctl enable i2p-testnet-net.service 2>/dev/null
for i in $(seq 1 "$TOTAL_ROUTERS"); do
    sudo systemctl enable "i2p-router@${i}.service" 2>/dev/null
done
sudo systemctl enable i2p-crosspoll.timer  2>/dev/null
sudo systemctl enable i2p-testnet.target   2>/dev/null
ok "All services enabled (network fabric persists across boot via systemd recreation)."

# =============================================================================
# STEP 10 – START EVERYTHING (sequenced)
# =============================================================================
CURRENT_STEP="10/11"
log "10/11" "Starting the testnet..."

for i in $(seq 1 "$TOTAL_ROUTERS"); do
    find "$TESTNET_BASE/r$i" \( -name "router.ping" -o -name "*.lck" \) \
        -delete 2>/dev/null || true
done

sudo systemctl start i2p-testnet-net.service
ok "Namespace/bridge fabric is up."

FF_IDS="$(list_floodfill_router_ids || true)"

if [ -n "$FF_IDS" ]; then
    for i in $FF_IDS; do
        sudo systemctl start "i2p-router@${i}.service"
        ok "Started floodfill router $i ($(router_ip_for_runtime "$i"))"
    done

    echo ""
    info "Waiting up to 20 s for floodfill router(s) to open at least one console..."
    if wait_for_any_floodfill_console 20; then
        ok "At least one floodfill console is reachable. Continuing startup."
    else
        warn "No floodfill console became reachable within 20 s. Continuing anyway."
    fi
fi

for i in $(seq 1 "$TOTAL_ROUTERS"); do
    if [ "$(router_floodfill_for_runtime "$i")" = "true" ]; then
        continue
    fi
    sudo systemctl start "i2p-router@${i}.service"
    ok "Started regular router $i ($(router_ip_for_runtime "$i"))"
    sleep 4
done

sudo systemctl start i2p-crosspoll.timer 2>/dev/null || true
ok "Cross-pollinator timer started (fires at 1 min, repeats every 2 min)."

# =============================================================================
# STEP 11 – VERIFY CONSOLES
# =============================================================================
CURRENT_STEP="11/11"
log "11/11" "Polling console URLs (up to 3 min)..."

WAIT_MAX=120
INTERVAL=3
ELAPSED=0
while [ "$ELAPSED" -lt "$WAIT_MAX" ]; do
    READY=0
    for i in $(seq 1 "$TOTAL_ROUTERS"); do
        console_ready "$i" && READY=$(( READY + 1 ))
    done
    printf "\r  [%3ds] %d / %d consoles reachable..." \
        "$ELAPSED" "$READY" "$TOTAL_ROUTERS"
    [ "$READY" -eq "$TOTAL_ROUTERS" ] && { echo ""; ok "All router consoles are reachable."; break; }
    sleep "$INTERVAL"
    ELAPSED=$(( ELAPSED + INTERVAL ))
done
echo ""

warm_all_client_tunnels

# =============================================================================
# MANAGEMENT SCRIPT
# =============================================================================
MGMT="$TESTNET_BASE/manage-testnet.sh"
cat > "$MGMT" <<'MGEOF'
#!/bin/bash

TOTAL=__TOTAL__
NUM_FF=__NUM_FF__
BASE="__BASE__"
CROSSPOLL="__CROSSPOLL__"
NETWORK_SETUP="__NETWORK_SETUP__"
NS_PREFIX="__NS_PREFIX__"
USE_TOPOLOGY_TSV="__USE_TOPOLOGY_TSV__"
ROUTERS_TSV="__ROUTERS_TSV__"
SUBNETS_TSV="__SUBNETS_TSV__"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

calc_octets() {
    local idx=$1
    local oct2=$(( 210 + ((idx - 1) / 250) ))
    local oct3=$(( ((idx - 1) % 250) + 1 ))
    echo "$oct2 $oct3"
}

router_ip_legacy() {
    local oct2 oct3
    read -r oct2 oct3 <<< "$(calc_octets "$1")"
    echo "10.${oct2}.${oct3}.2"
}

get_router_tsv_field() {
    local tsv="$1"
    local router_id="$2"
    local field_name="$3"

    awk -F $'\t' -v rid="$router_id" -v field="$field_name" '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == field) col = i
            }
            next
        }
        $1 == rid {
            if (col > 0) print $col
            exit
        }
    ' "$tsv"
}

router_ip() {
    local i="$1"
    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "$ROUTERS_TSV" "$i" "router_ip"
    else
        router_ip_legacy "$i"
    fi
}

router_console_port() { echo $(( 7700 + $1 )); }
router_console_url()  { echo "http://$(router_ip "$1"):$(router_console_port "$1")"; }

router_ns_name() {
    local i="$1"
    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        get_router_tsv_field "$ROUTERS_TSV" "$i" "namespace"
    else
        echo "${NS_PREFIX}$i"
    fi
}

router_floodfill() {
    local i="$1"
    local val
    if [ "$USE_TOPOLOGY_TSV" = "true" ]; then
        val=$(get_router_tsv_field "$ROUTERS_TSV" "$i" "floodfill" | tr '[:upper:]' '[:lower:]')
        if [ "$val" = "true" ]; then
            echo "true"
        else
            echo "false"
        fi
    else
        if [ "$i" -le "$NUM_FF" ]; then
            echo "true"
        else
            echo "false"
        fi
    fi
}

list_floodfill_router_ids() {
    local i
    for i in $(seq 1 "$TOTAL"); do
        if [ "$(router_floodfill "$i")" = "true" ]; then
            echo "$i"
        fi
    done
}

_locks() {
    for i in $(seq 1 "$TOTAL"); do
        find "$BASE/r$i" \( -name "router.ping" -o -name "*.lck" \) -delete 2>/dev/null || true
    done
}

_console_ready() {
    curl -fsS --max-time 2 "$(router_console_url "$1")/" >/dev/null 2>&1
}

_wait_for_any_floodfill_console() {
    local timeout="${1:-20}"
    local waited=0
    local i
    while [ "$waited" -lt "$timeout" ]; do
        for i in $(list_floodfill_router_ids); do
            if _console_ready "$i"; then
                return 0
            fi
        done
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

router_proxy_port()   { echo $(( 44440 + $1 )); }

_router_proxy_listening() {
    local i="$1"
    local ns port
    ns="$(router_ns_name "$i")"
    port="$(router_proxy_port "$i")"
    sudo -n ip netns exec "$ns" ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}$"
}

_fetch_i2ptunnel_list() {
    local i="$1"
    curl -fsS --max-time 5 "http://$(router_ip "$i"):$(router_console_port "$i")/i2ptunnel/list" 2>/dev/null || true
}

_extract_i2ptunnel_nonce() {
    grep -oE 'nonce=[0-9]+' | head -n 1 | cut -d= -f2
}

_start_all_tunnels_via_console() {
    local i="$1"
    local page nonce url
    page="$(_fetch_i2ptunnel_list "$i")"
    [ -n "$page" ] || return 1
    nonce="$(printf '%s' "$page" | _extract_i2ptunnel_nonce)"
    [ -n "$nonce" ] || return 1
    url="http://$(router_ip "$i"):$(router_console_port "$i")/i2ptunnel/list?nonce=${nonce}&action=Start%20all"
    curl -fsS --max-time 5 "$url" >/dev/null 2>&1 || return 1
    return 0
}

_wait_for_router_console() {
    local router_id="$1"
    local timeout="${2:-45}"
    local waited=0
    while [ "$waited" -lt "$timeout" ]; do
        if _console_ready "$router_id"; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

_warm_client_tunnel() {
    local i="$1"
    local timeout="${2:-90}"
    local waited=0
    local page=""
    if ! _wait_for_router_console "$i" 30; then
        echo "  Router $i console not reachable for tunnel warm-up."
        return 1
    fi
    while [ "$waited" -lt "$timeout" ]; do
        if _router_proxy_listening "$i"; then
            echo "  Router $i client proxy listening on 127.0.0.1:$(router_proxy_port "$i")"
            return 0
        fi
        page="$(_fetch_i2ptunnel_list "$i")"
        if printf '%s' "$page" | grep -q 'statusNotRunning'; then
            _start_all_tunnels_via_console "$i" >/dev/null 2>&1 || true
        elif [ -n "$page" ] && ! printf '%s' "$page" | grep -q 'statusRunning'; then
            _start_all_tunnels_via_console "$i" >/dev/null 2>&1 || true
        fi
        sleep 5
        waited=$((waited + 5))
    done
    echo "  Router $i client proxy failed to reach LISTEN state on 127.0.0.1:$(router_proxy_port "$i")"
    return 1
}

_warm_all_client_tunnels() {
    local i
    local failures=0
    echo "  Ensuring client HTTP proxies are listening..."
    for i in $(seq 1 "$TOTAL"); do
        _warm_client_tunnel "$i" 90 || failures=$((failures + 1))
    done
    if [ "$failures" -eq 0 ]; then
        echo "  All client HTTP proxies are listening."
    else
        echo "  WARNING: $failures client proxy/proxies did not reach LISTEN state."
    fi
}

case "${1:-status}" in
  start)
    echo -e "${BOLD}Starting testnet...${NC}"
    _locks
    sudo systemctl start i2p-testnet-net.service
    
    FF_IDS="$(list_floodfill_router_ids || true)"
    if [ -n "$FF_IDS" ]; then
        for i in $FF_IDS; do
            sudo systemctl start "i2p-router@${i}.service"
            echo -e "  ${GREEN}●${NC} Floodfill router $i started ($(router_ip "$i"))"
        done
        echo "  Waiting up to 20 s for at least one floodfill console..."
        if _wait_for_any_floodfill_console 20; then
            echo "  Floodfill readiness detected."
        else
            echo "  Floodfill console not yet reachable; continuing."
        fi
    fi

    for i in $(seq 1 "$TOTAL"); do
        if [ "$(router_floodfill "$i")" = "true" ]; then
            continue
        fi
        sudo systemctl start "i2p-router@${i}.service"
        echo -e "  ${GREEN}●${NC} Regular router $i started ($(router_ip "$i"))"
        sleep 4
    done
    
    sudo systemctl start i2p-crosspoll.timer 2>/dev/null || true
    _warm_all_client_tunnels
    echo -e "${GREEN}Done.${NC}"
    ;;

  stop)
    echo -e "${BOLD}Stopping testnet...${NC}"
    sudo systemctl stop i2p-crosspoll.timer 2>/dev/null || true
    for i in $(seq 1 "$TOTAL"); do
        sudo systemctl stop "i2p-router@${i}.service" 2>/dev/null
        echo -e "  ${YELLOW}●${NC} Router $i stopped"
    done
    sudo systemctl stop i2p-testnet-net.service 2>/dev/null || true
    echo -e "${GREEN}Done.${NC}"
    ;;

  restart)
    "$0" stop
    sleep 5
    "$0" start
    ;;

  status)
    echo -e "\n${BOLD}${BLUE}══ I2P Testnet Status ($TOTAL routers) ══${NC}\n"
    RUN=0
    STOP=0
    FAIL=0
    for i in $(seq 1 "$TOTAL"); do
        URL="$(router_console_url "$i")"
        SVC="i2p-router@${i}.service"
        LABEL="Router $i"
        [ "$(router_floodfill "$i")" = "true" ] && LABEL="Router $i [FF]"
        ACTIVE=$(systemctl show -p ActiveState --value "$SVC" 2>/dev/null || echo inactive)
        if [ "$ACTIVE" = "active" ] && _console_ready "$i"; then
            echo -e "  ${GREEN}●${NC} $LABEL  RUNNING   $URL"
            RUN=$(( RUN + 1 ))
        elif [ "$ACTIVE" = "active" ]; then
            echo -e "  ${YELLOW}●${NC} $LABEL  STARTING  $URL"
            RUN=$(( RUN + 1 ))
        elif [ "$ACTIVE" = "failed" ]; then
            echo -e "  ${RED}●${NC} $LABEL  FAILED"
            FAIL=$(( FAIL + 1 ))
        else
            echo -e "  ${RED}●${NC} $LABEL  STOPPED"
            STOP=$(( STOP + 1 ))
        fi
    done
    echo -e "\n  ${GREEN}$RUN active${NC}  ${RED}$STOP stopped${NC}  ${RED}$FAIL failed${NC}"
    echo ""
    NETSTATE=$(systemctl show -p ActiveState --value i2p-testnet-net.service 2>/dev/null || echo inactive)
    CPSTATE=$(systemctl show -p ActiveState --value i2p-crosspoll.timer 2>/dev/null || echo inactive)
    echo -e "  Namespace fabric: ${NETSTATE}"
    echo -e "  Cross-pollinator timer: ${CPSTATE}"
    echo ""
    ;;

  logs)
    N="${2:-1}"
    LOG="$BASE/r$N/logs/stdout.log"
    [ -f "$LOG" ] && tail -f "$LOG" || journalctl -fu "i2p-router@${N}.service"
    ;;

  console)
    N="${2:-1}"
    URL="$(router_console_url "$N")"
    echo "Router $N console: $URL"
    xdg-open "$URL" 2>/dev/null || echo "Open in Firefox manually."
    ;;

  shell)
    N="${2:-1}"
    sudo ip netns exec "$(router_ns_name "$N")" bash
    ;;

  crosspoll)
    echo "Running cross-pollination now..."
    sudo -u "__ACTUAL_USER__" bash "$CROSSPOLL"
    ;;

  netmap)
    cat "$BASE/topology-map.tsv"
    ;;

  destroy)
    "$0" stop || true
    mapfile -t EXISTING_ROUTER_UNITS < <(list_existing_router_units | sort -V)
    for unit in "${EXISTING_ROUTER_UNITS[@]}"; do
        [ -n "$unit" ] || continue
        sudo systemctl disable "$unit" 2>/dev/null || true
    done
    sudo rm -f /etc/systemd/system/i2p-router@*.service 2>/dev/null || true
    sudo systemctl disable i2p-crosspoll.timer i2p-testnet.target i2p-testnet-net.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/i2p-crosspoll.service
    sudo rm -f /etc/systemd/system/i2p-crosspoll.timer
    sudo rm -f /etc/systemd/system/i2p-testnet.target
    sudo rm -f /etc/systemd/system/i2p-testnet-net.service
    sudo systemctl daemon-reload
    sudo bash "$NETWORK_SETUP" down || true
    rm -rf "$BASE"
    echo -e "${GREEN}Destroyed testnet artifacts.${NC}"
    ;;

  *)
    echo "Usage: $0 {start|stop|restart|status|logs [N]|console [N]|shell [N]|crosspoll|netmap|destroy}"
    ;;
esac
MGEOF

sed -i "s|__TOTAL__|$TOTAL_ROUTERS|g" "$MGMT"
sed -i "s|__NUM_FF__|$NUM_FF|g" "$MGMT"
sed -i "s|__BASE__|$TESTNET_BASE|g" "$MGMT"
sed -i "s|__CROSSPOLL__|$CROSSPOLL|g" "$MGMT"
sed -i "s|__NETWORK_SETUP__|$NETWORK_SETUP|g" "$MGMT"
sed -i "s|__NS_PREFIX__|$NS_PREFIX|g" "$MGMT"
sed -i "s|__ACTUAL_USER__|$ACTUAL_USER|g" "$MGMT"
sed -i "s|__USE_TOPOLOGY_TSV__|$USE_TOPOLOGY_TSV|g" "$MGMT"
sed -i "s|__ROUTERS_TSV__|$ROUTERS_TSV|g" "$MGMT"
sed -i "s|__SUBNETS_TSV__|$SUBNETS_TSV|g" "$MGMT"

chmod +x "$MGMT"
chown "$ACTUAL_USER":"$ACTUAL_USER" "$MGMT"

# =============================================================================
# FINAL SUMMARY
# =============================================================================
echo ""
hr
echo -e "${BOLD}  I2P Testnet is UP!${NC}"
hr
echo ""
echo -e "  ${CYAN}Directory       :${NC} $TESTNET_BASE"
echo -e "  ${CYAN}Auto-boot       :${NC} YES – systemd recreates namespaces/bridges on boot"
echo -e "  ${CYAN}Reseed          :${NC} BYPASSED – direct netDb pre-seeding"
echo -e "  ${CYAN}Cross-poll      :${NC} Fires at t+1 min, repeats every 2 min"
echo -e "  ${CYAN}Tunnel length   :${NC} 1 (optimised for small LAN testnet)"
echo -e "  ${CYAN}Topology map    :${NC} $TOPOLOGY_MAP"
echo ""
echo -e "  ${CYAN}Router consoles:${NC}"

for i in $(seq 1 "$TOTAL_ROUTERS"); do
    URL="http://$(router_ip_for_runtime "$i"):$(router_console_port "$i")"
    LABEL="Router $i"
    [ "$(router_floodfill_for_runtime "$i")" = "true" ] && LABEL="Router $i [Floodfill]"
    if console_ready "$i"; then
        echo -e "    ${GREEN}●${NC} $LABEL  →  $URL  ${GREEN}[OPEN]${NC}"
    else
        echo -e "    ${YELLOW}●${NC} $LABEL  →  $URL  ${YELLOW}[starting…]${NC}"
    fi
done
echo ""
echo -e "  ${CYAN}What changed in this build:${NC}"
echo "    • each router now has its own Linux network namespace"
echo "    • routers are placed into topology-defined shared subnets with explicit IPs"
echo "    • router transports advertise namespace IPs, not 127.0.0.1"
echo "    • GUI/host access each console through the router IP"
echo ""
echo -e "  ${CYAN}Management:${NC}"
echo "    $MGMT status"
echo "    $MGMT netmap"
echo "    $MGMT shell 1"
echo "    $MGMT crosspoll"
echo "    $MGMT stop / start / restart / destroy"
echo ""
echo -e "  ${CYAN}Debug:${NC}"
echo "    journalctl -fu i2p-router@1"
echo "    cat $TESTNET_BASE/crosspollinate.log"
echo "    systemctl status i2p-testnet-net.service"
hr
