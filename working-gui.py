import os
import re
import sys
import html
import glob
import csv
import json
import shutil
import urllib.request
import urllib.parse
import urllib.error
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import time
import math
import hashlib
import random
from functools import lru_cache

try:
    import pycountry
except Exception:
    pycountry = None

try:
    from countryinfo import CountryInfo
except Exception:
    CountryInfo = None

# VM-safe rendering defaults
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

try:
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QRectF, QPointF, QStringListModel
    from PyQt6.QtGui import QDesktopServices, QFont, QPainter, QColor, QPen, QBrush
    from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QPlainTextEdit, QSpinBox, QMessageBox, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QSplitter, QTabWidget, QGroupBox, QSizePolicy,
    QFileDialog, QLineEdit, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
    QFormLayout, QStackedWidget, QComboBox, QCompleter, QListView, QCompleter, QListView, QCompleter, QListView
    )
    PYQT_VER = 6
except Exception:
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QRectF, QPointF, QStringListModel
    from PyQt5.QtGui import QDesktopServices, QFont, QPainter, QColor, QPen, QBrush
    from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QPlainTextEdit, QSpinBox, QMessageBox, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QSplitter, QTabWidget, QGroupBox, QSizePolicy,
    QFileDialog, QLineEdit, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
    QFormLayout, QStackedWidget, QComboBox, QCompleter, QListView, QCompleter, QListView, QCompleter, QListView
    )
    PYQT_VER = 5

WEBENGINE_AVAILABLE = False
QWebEngineView = None
QWebEnginePage = None
try:
    if PYQT_VER == 6:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEnginePage
    else:
        from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
    WEBENGINE_AVAILABLE = True
except Exception:
    WEBENGINE_AVAILABLE = False

APP_NAME = "I2P Testnet Emulator"
HOME = str(Path.home())
DEPLOY_SCRIPT_PATH = os.path.join(HOME, "Desktop", "setup-i2p-emulator.sh")
LOG_DIR = os.path.join(HOME, "i2p-gui", "logs")
DEPLOY_LOG_FILE = os.path.join(LOG_DIR, "deployment.log")
TELEMETRY_ROOT_DIR = os.path.join(LOG_DIR, "telemetry")
TELEMETRY_STATE_FILE = os.path.join(TELEMETRY_ROOT_DIR, "latest-session.json")
SCENARIO_ROOT_DIR = os.path.join(LOG_DIR, "scenarios")
MEASUREMENT_ROOT_DIR = os.path.join(LOG_DIR, "measurements")
CAMPAIGN_ROOT_DIR = os.path.join(LOG_DIR, "campaigns")
HOP_HISTORY_ROOT_DIR = os.path.join(LOG_DIR, "hop_history")
HOP_TRUTH_ROOT_DIR = os.path.join(LOG_DIR, "hop_truth")
SCENARIO_LOG_LINE_LIMIT = 300
SCENARIO_ACTION_SOURCE = "scenario_runner"
SCENARIO_DEFAULT_MIN_INTERVAL = 15.0
SCENARIO_DEFAULT_MAX_INTERVAL = 25.0
SCENARIO_DEFAULT_DOWNTIME = 10.0
SCENARIO_DEFAULT_MAX_CYCLES = 10
TELEMETRY_RECENT_EVENT_LIMIT = 200
TELEMETRY_VIEW_EVENT_LIMIT = 20
TELEMETRY_DERIVED_EVENT_WINDOW_SECONDS = 180.0
TELEMETRY_ACTION_INTENT_WINDOW_SECONDS = 120.0

READ_FILE_MAX_LINES = 300
LOG_CMD_TIMEOUT = 15
STATUS_CMD_TIMEOUT = 4
ACTION_CMD_TIMEOUT = 10
ACTION_WAIT_TIMEOUT = 45
ACTION_POLL_INTERVAL = 0.5
CONSOLE_FETCH_TIMEOUT = 1.2
MEASUREMENT_FETCH_TIMEOUT_DEFAULT = 3.0
MEASUREMENT_CLIENT_PROXY_TARGET_URL = ""
MEASUREMENT_SCENARIO_CORRELATION_WINDOW_SECONDS = 6 * 3600
MEASUREMENT_RECENT_RUN_LIMIT = 8
TUNNEL_TRACE_RECENT_RUN_LIMIT = 12
CAMPAIGN_RECENT_RUN_LIMIT = 8
POLL_SECONDS = 8.0
DEPLOY_MAX_ROUTER_SERVICE_ID = 50
DETAIL_REFRESH_SECONDS = 3.0
CONFIG_REFRESH_SECONDS = 15.0
LOG_REFRESH_SECONDS = 5.0
CARD_MIN_WIDTH = 360
CARD_GRID_SPACING = 12
CARD_GRID_MARGIN = 8
TOPOLOGY_MIN_HEIGHT = 460
BUILDER_PREVIEW_MAX_LINES = 220

PREFERRED_TESTNET_BASE = None

SCENARIO_PRESETS = {
    "moderate_non_floodfill": {
        "name": "Moderate churn (non-floodfill)",
        "experiment_label": "moderate_churn_non_floodfill",
        "scenario_type": "random_stop_start",
        "target_group": "non_floodfill",
        "min_interval_seconds": 15.0,
        "max_interval_seconds": 25.0,
        "downtime_seconds": 10.0,
        "max_cycles": 10,
        "campaign_probe_interval_seconds": 15.0,
        "probe_after_each_cycle": True,
        "post_settle_seconds": 8.0,
    },
    "high_churn_non_floodfill": {
        "name": "High churn (non-floodfill)",
        "experiment_label": "high_churn_non_floodfill",
        "scenario_type": "random_stop_start",
        "target_group": "non_floodfill",
        "min_interval_seconds": 5.0,
        "max_interval_seconds": 10.0,
        "downtime_seconds": 12.0,
        "max_cycles": 12,
        "campaign_probe_interval_seconds": 8.0,
        "probe_after_each_cycle": True,
        "post_settle_seconds": 12.0,
    },
    "floodfill_targeted_churn": {
        "name": "Floodfill-targeted churn",
        "experiment_label": "floodfill_targeted_churn",
        "scenario_type": "random_stop_start",
        "target_group": "floodfill_only",
        "min_interval_seconds": 12.0,
        "max_interval_seconds": 20.0,
        "downtime_seconds": 10.0,
        "max_cycles": 8,
        "campaign_probe_interval_seconds": 10.0,
        "probe_after_each_cycle": True,
        "post_settle_seconds": 10.0,
    },
    "adversarial_floodfill_failure": {
        "name": "Adversarial floodfill / failure scenario",
        "experiment_label": "adversarial_floodfill_failure",
        "scenario_type": "random_stop_start",
        "target_group": "floodfill_only",
        "min_interval_seconds": 3.0,
        "max_interval_seconds": 6.0,
        "downtime_seconds": 18.0,
        "max_cycles": 12,
        "campaign_probe_interval_seconds": 6.0,
        "probe_after_each_cycle": True,
        "post_settle_seconds": 15.0,
    },
}


def combo_set_current_data(combo, value):
    if combo is None:
        return False
    try:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return True
    except Exception:
        return False
    return False


def _clean_i2p_host(value):
    value = str(value or "").strip()
    if not value or value.lower() == "unknown":
        return ""
    return value.rstrip("/")


def _i2p_url_from_host(value):
    host = _clean_i2p_host(value)
    return f"http://{host}/" if host else ""


def _extract_b32_from_keybackup(testnet_base, router_id):
    base = str(testnet_base or PREFERRED_TESTNET_BASE or "").strip()
    rid = str(router_id or "").strip()
    if not base or not rid or rid.lower() == "unknown":
        return ""
    backup_dir = os.path.join(base, f"r{rid}", "config", "i2ptunnel-keyBackup")
    if not os.path.isdir(backup_dir):
        return ""
    try:
        entries = sorted(os.listdir(backup_dir))
    except Exception:
        return ""
    for name in entries:
        match = B32_HOST_RE.search(name)
        if match:
            return match.group(1).lower()
    return ""


def set_preferred_testnet_base(path):
    global PREFERRED_TESTNET_BASE
    path = (path or '').strip()
    PREFERRED_TESTNET_BASE = path or None


def clear_preferred_testnet_base():
    global PREFERRED_TESTNET_BASE
    PREFERRED_TESTNET_BASE = None


def get_preferred_testnet_base():
    global PREFERRED_TESTNET_BASE
    preferred = PREFERRED_TESTNET_BASE
    if preferred and os.path.isdir(preferred):
        return preferred

    bases = get_existing_testnet_bases()
    if not bases:
        return None

    # Prefer an existing base with a management script and topology map.
    for candidate in reversed(bases):
        if os.path.exists(os.path.join(candidate, 'manage-testnet.sh')):
            return candidate
    return bases[-1]


CITY_PRESETS = {
    "Tokyo, Japan": {"country": "Japan", "country_code": "JP", "city": "Tokyo", "lat": "35.6762", "lon": "139.6503", "spread": "0.12"},
    "Sao Paulo, Brazil": {"country": "Brazil", "country_code": "BR", "city": "Sao Paulo", "lat": "-23.5505", "lon": "-46.6333", "spread": "0.16"},
    "Toronto, Canada": {"country": "Canada", "country_code": "CA", "city": "Toronto", "lat": "43.6532", "lon": "-79.3832", "spread": "0.14"},
    "Mumbai, India": {"country": "India", "country_code": "IN", "city": "Mumbai", "lat": "19.0760", "lon": "72.8777", "spread": "0.14"},
    "Johannesburg, South Africa": {"country": "South Africa", "country_code": "ZA", "city": "Johannesburg", "lat": "-26.2041", "lon": "28.0473", "spread": "0.14"},
    "Berlin, Germany": {"country": "Germany", "country_code": "DE", "city": "Berlin", "lat": "52.5200", "lon": "13.4050", "spread": "0.12"},
    "Beirut, Lebanon": {"country": "Lebanon", "country_code": "LB", "city": "Beirut", "lat": "33.8938", "lon": "35.5018", "spread": "0.12"},
}

OFFLINE_MAJOR_CITY_OVERRIDES = [
    {"country": "Argentina", "country_code": "AR", "city": "Buenos Aires", "lat": -34.6037, "lon": -58.3816, "spread": 0.14},
    {"country": "Australia", "country_code": "AU", "city": "Sydney", "lat": -33.8688, "lon": 151.2093, "spread": 0.14},
    {"country": "Australia", "country_code": "AU", "city": "Melbourne", "lat": -37.8136, "lon": 144.9631, "spread": 0.14},
    {"country": "Brazil", "country_code": "BR", "city": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729, "spread": 0.16},
    {"country": "Canada", "country_code": "CA", "city": "Montreal", "lat": 45.5017, "lon": -73.5673, "spread": 0.14},
    {"country": "Canada", "country_code": "CA", "city": "Vancouver", "lat": 49.2827, "lon": -123.1207, "spread": 0.14},
    {"country": "China", "country_code": "CN", "city": "Beijing", "lat": 39.9042, "lon": 116.4074, "spread": 0.16},
    {"country": "China", "country_code": "CN", "city": "Shanghai", "lat": 31.2304, "lon": 121.4737, "spread": 0.16},
    {"country": "Egypt", "country_code": "EG", "city": "Cairo", "lat": 30.0444, "lon": 31.2357, "spread": 0.14},
    {"country": "France", "country_code": "FR", "city": "Paris", "lat": 48.8566, "lon": 2.3522, "spread": 0.12},
    {"country": "Germany", "country_code": "DE", "city": "Munich", "lat": 48.1351, "lon": 11.5820, "spread": 0.12},
    {"country": "India", "country_code": "IN", "city": "New Delhi", "lat": 28.6139, "lon": 77.2090, "spread": 0.14},
    {"country": "India", "country_code": "IN", "city": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "spread": 0.14},
    {"country": "Italy", "country_code": "IT", "city": "Rome", "lat": 41.9028, "lon": 12.4964, "spread": 0.12},
    {"country": "Japan", "country_code": "JP", "city": "Osaka", "lat": 34.6937, "lon": 135.5023, "spread": 0.12},
    {"country": "Lebanon", "country_code": "LB", "city": "Tripoli", "lat": 34.4367, "lon": 35.8497, "spread": 0.12},
    {"country": "Lebanon", "country_code": "LB", "city": "Sidon", "lat": 33.5606, "lon": 35.3756, "spread": 0.12},
    {"country": "Mexico", "country_code": "MX", "city": "Mexico City", "lat": 19.4326, "lon": -99.1332, "spread": 0.14},
    {"country": "Netherlands", "country_code": "NL", "city": "Amsterdam", "lat": 52.3676, "lon": 4.9041, "spread": 0.12},
    {"country": "Saudi Arabia", "country_code": "SA", "city": "Riyadh", "lat": 24.7136, "lon": 46.6753, "spread": 0.14},
    {"country": "South Africa", "country_code": "ZA", "city": "Cape Town", "lat": -33.9249, "lon": 18.4241, "spread": 0.14},
    {"country": "South Korea", "country_code": "KR", "city": "Seoul", "lat": 37.5665, "lon": 126.9780, "spread": 0.12},
    {"country": "Spain", "country_code": "ES", "city": "Madrid", "lat": 40.4168, "lon": -3.7038, "spread": 0.12},
    {"country": "Turkey", "country_code": "TR", "city": "Istanbul", "lat": 41.0082, "lon": 28.9784, "spread": 0.14},
    {"country": "United Arab Emirates", "country_code": "AE", "city": "Dubai", "lat": 25.2048, "lon": 55.2708, "spread": 0.14},
    {"country": "United Kingdom", "country_code": "GB", "city": "London", "lat": 51.5074, "lon": -0.1278, "spread": 0.12},
    {"country": "United States", "country_code": "US", "city": "New York", "lat": 40.7128, "lon": -74.0060, "spread": 0.16},
    {"country": "United States", "country_code": "US", "city": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "spread": 0.16},
    {"country": "United States", "country_code": "US", "city": "Chicago", "lat": 41.8781, "lon": -87.6298, "spread": 0.14},
    {"country": "Russia", "country_code": "RU", "city": "Moscow", "lat": 55.7558, "lon": 37.6173, "spread": 0.16},
]

OFFLINE_LOCATION_CATALOG = [
    {
        "country": item.get("country", ""),
        "country_code": item.get("country_code", ""),
        "city": item.get("city", ""),
    }
    for item in OFFLINE_MAJOR_CITY_OVERRIDES
] + [
    {
        "country": preset.get("country", ""),
        "country_code": preset.get("country_code", ""),
        "city": preset.get("city", ""),
    }
    for preset in CITY_PRESETS.values()
]

ONLINE_GEOCODER_TIMEOUT_SECONDS = 2.0
BUILDER_DEFAULT_MAP_SPREAD = 0.12
BUILDER_LARGE_COUNTRY_CODES = {"AU", "BR", "CA", "CN", "IN", "RU", "US"}
BUILDER_PLACEHOLDER_COUNTRY = "Choose country..."
BUILDER_PLACEHOLDER_CITY = "Choose or type city..."

STATIC_COUNTRY_RECORDS = [
  {
    "name": "Afghanistan",
    "code": "AF"
  },
  {
    "name": "Albania",
    "code": "AL"
  },
  {
    "name": "Algeria",
    "code": "DZ"
  },
  {
    "name": "American Samoa",
    "code": "AS"
  },
  {
    "name": "Andorra",
    "code": "AD"
  },
  {
    "name": "Angola",
    "code": "AO"
  },
  {
    "name": "Anguilla",
    "code": "AI"
  },
  {
    "name": "Antarctica",
    "code": "AQ"
  },
  {
    "name": "Antigua and Barbuda",
    "code": "AG"
  },
  {
    "name": "Argentina",
    "code": "AR"
  },
  {
    "name": "Armenia",
    "code": "AM"
  },
  {
    "name": "Aruba",
    "code": "AW"
  },
  {
    "name": "Australia",
    "code": "AU"
  },
  {
    "name": "Austria",
    "code": "AT"
  },
  {
    "name": "Azerbaijan",
    "code": "AZ"
  },
  {
    "name": "Bahamas",
    "code": "BS"
  },
  {
    "name": "Bahrain",
    "code": "BH"
  },
  {
    "name": "Bangladesh",
    "code": "BD"
  },
  {
    "name": "Barbados",
    "code": "BB"
  },
  {
    "name": "Belarus",
    "code": "BY"
  },
  {
    "name": "Belgium",
    "code": "BE"
  },
  {
    "name": "Belize",
    "code": "BZ"
  },
  {
    "name": "Benin",
    "code": "BJ"
  },
  {
    "name": "Bermuda",
    "code": "BM"
  },
  {
    "name": "Bhutan",
    "code": "BT"
  },
  {
    "name": "Bolivia, Plurinational State of",
    "code": "BO"
  },
  {
    "name": "Bonaire, Sint Eustatius and Saba",
    "code": "BQ"
  },
  {
    "name": "Bosnia and Herzegovina",
    "code": "BA"
  },
  {
    "name": "Botswana",
    "code": "BW"
  },
  {
    "name": "Bouvet Island",
    "code": "BV"
  },
  {
    "name": "Brazil",
    "code": "BR"
  },
  {
    "name": "British Indian Ocean Territory",
    "code": "IO"
  },
  {
    "name": "Brunei Darussalam",
    "code": "BN"
  },
  {
    "name": "Bulgaria",
    "code": "BG"
  },
  {
    "name": "Burkina Faso",
    "code": "BF"
  },
  {
    "name": "Burundi",
    "code": "BI"
  },
  {
    "name": "Cabo Verde",
    "code": "CV"
  },
  {
    "name": "Cambodia",
    "code": "KH"
  },
  {
    "name": "Cameroon",
    "code": "CM"
  },
  {
    "name": "Canada",
    "code": "CA"
  },
  {
    "name": "Cayman Islands",
    "code": "KY"
  },
  {
    "name": "Central African Republic",
    "code": "CF"
  },
  {
    "name": "Chad",
    "code": "TD"
  },
  {
    "name": "Chile",
    "code": "CL"
  },
  {
    "name": "China",
    "code": "CN"
  },
  {
    "name": "Christmas Island",
    "code": "CX"
  },
  {
    "name": "Cocos (Keeling) Islands",
    "code": "CC"
  },
  {
    "name": "Colombia",
    "code": "CO"
  },
  {
    "name": "Comoros",
    "code": "KM"
  },
  {
    "name": "Congo",
    "code": "CG"
  },
  {
    "name": "Congo, The Democratic Republic of the",
    "code": "CD"
  },
  {
    "name": "Cook Islands",
    "code": "CK"
  },
  {
    "name": "Costa Rica",
    "code": "CR"
  },
  {
    "name": "Croatia",
    "code": "HR"
  },
  {
    "name": "Cuba",
    "code": "CU"
  },
  {
    "name": "Curaçao",
    "code": "CW"
  },
  {
    "name": "Cyprus",
    "code": "CY"
  },
  {
    "name": "Czechia",
    "code": "CZ"
  },
  {
    "name": "Côte d'Ivoire",
    "code": "CI"
  },
  {
    "name": "Denmark",
    "code": "DK"
  },
  {
    "name": "Djibouti",
    "code": "DJ"
  },
  {
    "name": "Dominica",
    "code": "DM"
  },
  {
    "name": "Dominican Republic",
    "code": "DO"
  },
  {
    "name": "Ecuador",
    "code": "EC"
  },
  {
    "name": "Egypt",
    "code": "EG"
  },
  {
    "name": "El Salvador",
    "code": "SV"
  },
  {
    "name": "Equatorial Guinea",
    "code": "GQ"
  },
  {
    "name": "Eritrea",
    "code": "ER"
  },
  {
    "name": "Estonia",
    "code": "EE"
  },
  {
    "name": "Eswatini",
    "code": "SZ"
  },
  {
    "name": "Ethiopia",
    "code": "ET"
  },
  {
    "name": "Falkland Islands (Malvinas)",
    "code": "FK"
  },
  {
    "name": "Faroe Islands",
    "code": "FO"
  },
  {
    "name": "Fiji",
    "code": "FJ"
  },
  {
    "name": "Finland",
    "code": "FI"
  },
  {
    "name": "France",
    "code": "FR"
  },
  {
    "name": "French Guiana",
    "code": "GF"
  },
  {
    "name": "French Polynesia",
    "code": "PF"
  },
  {
    "name": "French Southern Territories",
    "code": "TF"
  },
  {
    "name": "Gabon",
    "code": "GA"
  },
  {
    "name": "Gambia",
    "code": "GM"
  },
  {
    "name": "Georgia",
    "code": "GE"
  },
  {
    "name": "Germany",
    "code": "DE"
  },
  {
    "name": "Ghana",
    "code": "GH"
  },
  {
    "name": "Gibraltar",
    "code": "GI"
  },
  {
    "name": "Greece",
    "code": "GR"
  },
  {
    "name": "Greenland",
    "code": "GL"
  },
  {
    "name": "Grenada",
    "code": "GD"
  },
  {
    "name": "Guadeloupe",
    "code": "GP"
  },
  {
    "name": "Guam",
    "code": "GU"
  },
  {
    "name": "Guatemala",
    "code": "GT"
  },
  {
    "name": "Guernsey",
    "code": "GG"
  },
  {
    "name": "Guinea",
    "code": "GN"
  },
  {
    "name": "Guinea-Bissau",
    "code": "GW"
  },
  {
    "name": "Guyana",
    "code": "GY"
  },
  {
    "name": "Haiti",
    "code": "HT"
  },
  {
    "name": "Heard Island and McDonald Islands",
    "code": "HM"
  },
  {
    "name": "Holy See (Vatican City State)",
    "code": "VA"
  },
  {
    "name": "Honduras",
    "code": "HN"
  },
  {
    "name": "Hong Kong",
    "code": "HK"
  },
  {
    "name": "Hungary",
    "code": "HU"
  },
  {
    "name": "Iceland",
    "code": "IS"
  },
  {
    "name": "India",
    "code": "IN"
  },
  {
    "name": "Indonesia",
    "code": "ID"
  },
  {
    "name": "Iran, Islamic Republic of",
    "code": "IR"
  },
  {
    "name": "Iraq",
    "code": "IQ"
  },
  {
    "name": "Ireland",
    "code": "IE"
  },
  {
    "name": "Isle of Man",
    "code": "IM"
  },
  {
    "name": "Israel",
    "code": "IL"
  },
  {
    "name": "Italy",
    "code": "IT"
  },
  {
    "name": "Jamaica",
    "code": "JM"
  },
  {
    "name": "Japan",
    "code": "JP"
  },
  {
    "name": "Jersey",
    "code": "JE"
  },
  {
    "name": "Jordan",
    "code": "JO"
  },
  {
    "name": "Kazakhstan",
    "code": "KZ"
  },
  {
    "name": "Kenya",
    "code": "KE"
  },
  {
    "name": "Kiribati",
    "code": "KI"
  },
  {
    "name": "Korea, Democratic People's Republic of",
    "code": "KP"
  },
  {
    "name": "Korea, Republic of",
    "code": "KR"
  },
  {
    "name": "Kuwait",
    "code": "KW"
  },
  {
    "name": "Kyrgyzstan",
    "code": "KG"
  },
  {
    "name": "Lao People's Democratic Republic",
    "code": "LA"
  },
  {
    "name": "Latvia",
    "code": "LV"
  },
  {
    "name": "Lebanon",
    "code": "LB"
  },
  {
    "name": "Lesotho",
    "code": "LS"
  },
  {
    "name": "Liberia",
    "code": "LR"
  },
  {
    "name": "Libya",
    "code": "LY"
  },
  {
    "name": "Liechtenstein",
    "code": "LI"
  },
  {
    "name": "Lithuania",
    "code": "LT"
  },
  {
    "name": "Luxembourg",
    "code": "LU"
  },
  {
    "name": "Macao",
    "code": "MO"
  },
  {
    "name": "Madagascar",
    "code": "MG"
  },
  {
    "name": "Malawi",
    "code": "MW"
  },
  {
    "name": "Malaysia",
    "code": "MY"
  },
  {
    "name": "Maldives",
    "code": "MV"
  },
  {
    "name": "Mali",
    "code": "ML"
  },
  {
    "name": "Malta",
    "code": "MT"
  },
  {
    "name": "Marshall Islands",
    "code": "MH"
  },
  {
    "name": "Martinique",
    "code": "MQ"
  },
  {
    "name": "Mauritania",
    "code": "MR"
  },
  {
    "name": "Mauritius",
    "code": "MU"
  },
  {
    "name": "Mayotte",
    "code": "YT"
  },
  {
    "name": "Mexico",
    "code": "MX"
  },
  {
    "name": "Micronesia, Federated States of",
    "code": "FM"
  },
  {
    "name": "Moldova, Republic of",
    "code": "MD"
  },
  {
    "name": "Monaco",
    "code": "MC"
  },
  {
    "name": "Mongolia",
    "code": "MN"
  },
  {
    "name": "Montenegro",
    "code": "ME"
  },
  {
    "name": "Montserrat",
    "code": "MS"
  },
  {
    "name": "Morocco",
    "code": "MA"
  },
  {
    "name": "Mozambique",
    "code": "MZ"
  },
  {
    "name": "Myanmar",
    "code": "MM"
  },
  {
    "name": "Namibia",
    "code": "NA"
  },
  {
    "name": "Nauru",
    "code": "NR"
  },
  {
    "name": "Nepal",
    "code": "NP"
  },
  {
    "name": "Netherlands",
    "code": "NL"
  },
  {
    "name": "New Caledonia",
    "code": "NC"
  },
  {
    "name": "New Zealand",
    "code": "NZ"
  },
  {
    "name": "Nicaragua",
    "code": "NI"
  },
  {
    "name": "Niger",
    "code": "NE"
  },
  {
    "name": "Nigeria",
    "code": "NG"
  },
  {
    "name": "Niue",
    "code": "NU"
  },
  {
    "name": "Norfolk Island",
    "code": "NF"
  },
  {
    "name": "North Macedonia",
    "code": "MK"
  },
  {
    "name": "Northern Mariana Islands",
    "code": "MP"
  },
  {
    "name": "Norway",
    "code": "NO"
  },
  {
    "name": "Oman",
    "code": "OM"
  },
  {
    "name": "Pakistan",
    "code": "PK"
  },
  {
    "name": "Palau",
    "code": "PW"
  },
  {
    "name": "Palestine, State of",
    "code": "PS"
  },
  {
    "name": "Panama",
    "code": "PA"
  },
  {
    "name": "Papua New Guinea",
    "code": "PG"
  },
  {
    "name": "Paraguay",
    "code": "PY"
  },
  {
    "name": "Peru",
    "code": "PE"
  },
  {
    "name": "Philippines",
    "code": "PH"
  },
  {
    "name": "Pitcairn",
    "code": "PN"
  },
  {
    "name": "Poland",
    "code": "PL"
  },
  {
    "name": "Portugal",
    "code": "PT"
  },
  {
    "name": "Puerto Rico",
    "code": "PR"
  },
  {
    "name": "Qatar",
    "code": "QA"
  },
  {
    "name": "Romania",
    "code": "RO"
  },
  {
    "name": "Russian Federation",
    "code": "RU"
  },
  {
    "name": "Rwanda",
    "code": "RW"
  },
  {
    "name": "Réunion",
    "code": "RE"
  },
  {
    "name": "Saint Barthélemy",
    "code": "BL"
  },
  {
    "name": "Saint Helena, Ascension and Tristan da Cunha",
    "code": "SH"
  },
  {
    "name": "Saint Kitts and Nevis",
    "code": "KN"
  },
  {
    "name": "Saint Lucia",
    "code": "LC"
  },
  {
    "name": "Saint Martin (French part)",
    "code": "MF"
  },
  {
    "name": "Saint Pierre and Miquelon",
    "code": "PM"
  },
  {
    "name": "Saint Vincent and the Grenadines",
    "code": "VC"
  },
  {
    "name": "Samoa",
    "code": "WS"
  },
  {
    "name": "San Marino",
    "code": "SM"
  },
  {
    "name": "Sao Tome and Principe",
    "code": "ST"
  },
  {
    "name": "Saudi Arabia",
    "code": "SA"
  },
  {
    "name": "Senegal",
    "code": "SN"
  },
  {
    "name": "Serbia",
    "code": "RS"
  },
  {
    "name": "Seychelles",
    "code": "SC"
  },
  {
    "name": "Sierra Leone",
    "code": "SL"
  },
  {
    "name": "Singapore",
    "code": "SG"
  },
  {
    "name": "Sint Maarten (Dutch part)",
    "code": "SX"
  },
  {
    "name": "Slovakia",
    "code": "SK"
  },
  {
    "name": "Slovenia",
    "code": "SI"
  },
  {
    "name": "Solomon Islands",
    "code": "SB"
  },
  {
    "name": "Somalia",
    "code": "SO"
  },
  {
    "name": "South Africa",
    "code": "ZA"
  },
  {
    "name": "South Georgia and the South Sandwich Islands",
    "code": "GS"
  },
  {
    "name": "South Sudan",
    "code": "SS"
  },
  {
    "name": "Spain",
    "code": "ES"
  },
  {
    "name": "Sri Lanka",
    "code": "LK"
  },
  {
    "name": "Sudan",
    "code": "SD"
  },
  {
    "name": "Suriname",
    "code": "SR"
  },
  {
    "name": "Svalbard and Jan Mayen",
    "code": "SJ"
  },
  {
    "name": "Sweden",
    "code": "SE"
  },
  {
    "name": "Switzerland",
    "code": "CH"
  },
  {
    "name": "Syrian Arab Republic",
    "code": "SY"
  },
  {
    "name": "Taiwan, Province of China",
    "code": "TW"
  },
  {
    "name": "Tajikistan",
    "code": "TJ"
  },
  {
    "name": "Tanzania, United Republic of",
    "code": "TZ"
  },
  {
    "name": "Thailand",
    "code": "TH"
  },
  {
    "name": "Timor-Leste",
    "code": "TL"
  },
  {
    "name": "Togo",
    "code": "TG"
  },
  {
    "name": "Tokelau",
    "code": "TK"
  },
  {
    "name": "Tonga",
    "code": "TO"
  },
  {
    "name": "Trinidad and Tobago",
    "code": "TT"
  },
  {
    "name": "Tunisia",
    "code": "TN"
  },
  {
    "name": "Turkmenistan",
    "code": "TM"
  },
  {
    "name": "Turks and Caicos Islands",
    "code": "TC"
  },
  {
    "name": "Tuvalu",
    "code": "TV"
  },
  {
    "name": "Türkiye",
    "code": "TR"
  },
  {
    "name": "Uganda",
    "code": "UG"
  },
  {
    "name": "Ukraine",
    "code": "UA"
  },
  {
    "name": "United Arab Emirates",
    "code": "AE"
  },
  {
    "name": "United Kingdom",
    "code": "GB"
  },
  {
    "name": "United States",
    "code": "US"
  },
  {
    "name": "United States Minor Outlying Islands",
    "code": "UM"
  },
  {
    "name": "Uruguay",
    "code": "UY"
  },
  {
    "name": "Uzbekistan",
    "code": "UZ"
  },
  {
    "name": "Vanuatu",
    "code": "VU"
  },
  {
    "name": "Venezuela, Bolivarian Republic of",
    "code": "VE"
  },
  {
    "name": "Viet Nam",
    "code": "VN"
  },
  {
    "name": "Virgin Islands, British",
    "code": "VG"
  },
  {
    "name": "Virgin Islands, U.S.",
    "code": "VI"
  },
  {
    "name": "Wallis and Futuna",
    "code": "WF"
  },
  {
    "name": "Western Sahara",
    "code": "EH"
  },
  {
    "name": "Yemen",
    "code": "YE"
  },
  {
    "name": "Zambia",
    "code": "ZM"
  },
  {
    "name": "Zimbabwe",
    "code": "ZW"
  },
  {
    "name": "Åland Islands",
    "code": "AX"
  }
]

OFFLINE_CAPITAL_FALLBACKS = [
  {
    "country": "Afghanistan",
    "country_code": "AF",
    "city": "Kabul",
    "lat": 34.526011,
    "lon": 69.177684,
    "spread": 0.12
  },
  {
    "country": "Albania",
    "country_code": "AL",
    "city": "Tirana",
    "lat": 41.326873,
    "lon": 19.818791,
    "spread": 0.12
  },
  {
    "country": "Algeria",
    "country_code": "DZ",
    "city": "Algiers",
    "lat": 36.775361,
    "lon": 3.060188,
    "spread": 0.12
  },
  {
    "country": "American Samoa",
    "country_code": "AS",
    "city": "Pago Pago",
    "lat": -14.275479,
    "lon": -170.70483,
    "spread": 0.12
  },
  {
    "country": "Andorra",
    "country_code": "AD",
    "city": "Andorra la Vella",
    "lat": 42.5063,
    "lon": 1.5218,
    "spread": 0.12
  },
  {
    "country": "Angola",
    "country_code": "AO",
    "city": "Luanda",
    "lat": -8.82727,
    "lon": 13.243951,
    "spread": 0.12
  },
  {
    "country": "Anguilla",
    "country_code": "AI",
    "city": "The Valley",
    "lat": 41.559572,
    "lon": -98.980548,
    "spread": 0.12
  },
  {
    "country": "Antarctica",
    "country_code": "AQ",
    "city": "McMurdo Station",
    "lat": -77.8419,
    "lon": 166.6863,
    "spread": 0.14
  },
  {
    "country": "Antigua and Barbuda",
    "country_code": "AG",
    "city": "Saint John's",
    "lat": 47.561701,
    "lon": -52.715149,
    "spread": 0.12
  },
  {
    "country": "Argentina",
    "country_code": "AR",
    "city": "Buenos Aires",
    "lat": -34.607568,
    "lon": -58.437089,
    "spread": 0.12
  },
  {
    "country": "Armenia",
    "country_code": "AM",
    "city": "Yerevan",
    "lat": 40.177612,
    "lon": 44.512585,
    "spread": 0.12
  },
  {
    "country": "Aruba",
    "country_code": "AW",
    "city": "Oranjestad",
    "lat": 12.526874,
    "lon": -70.035684,
    "spread": 0.12
  },
  {
    "country": "Australia",
    "country_code": "AU",
    "city": "Canberra",
    "lat": -35.297591,
    "lon": 149.101268,
    "spread": 0.14
  },
  {
    "country": "Austria",
    "country_code": "AT",
    "city": "Vienna",
    "lat": 48.208354,
    "lon": 16.372504,
    "spread": 0.12
  },
  {
    "country": "Azerbaijan",
    "country_code": "AZ",
    "city": "Baku",
    "lat": 40.375443,
    "lon": 49.832675,
    "spread": 0.12
  },
  {
    "country": "Bahamas",
    "country_code": "BS",
    "city": "Nassau",
    "lat": 25.078346,
    "lon": -77.338333,
    "spread": 0.12
  },
  {
    "country": "Bahrain",
    "country_code": "BH",
    "city": "Manama",
    "lat": 26.223504,
    "lon": 50.582244,
    "spread": 0.12
  },
  {
    "country": "Bangladesh",
    "country_code": "BD",
    "city": "Dhaka",
    "lat": 23.759357,
    "lon": 90.378814,
    "spread": 0.12
  },
  {
    "country": "Barbados",
    "country_code": "BB",
    "city": "Bridgetown",
    "lat": 13.097783,
    "lon": -59.618418,
    "spread": 0.12
  },
  {
    "country": "Belarus",
    "country_code": "BY",
    "city": "Minsk",
    "lat": 53.902334,
    "lon": 27.561879,
    "spread": 0.12
  },
  {
    "country": "Belgium",
    "country_code": "BE",
    "city": "Brussels",
    "lat": 50.846557,
    "lon": 4.351697,
    "spread": 0.12
  },
  {
    "country": "Belize",
    "country_code": "BZ",
    "city": "Belmopan",
    "lat": 17.250199,
    "lon": -88.770018,
    "spread": 0.12
  },
  {
    "country": "Benin",
    "country_code": "BJ",
    "city": "Porto-Novo",
    "lat": 6.499072,
    "lon": 2.625336,
    "spread": 0.12
  },
  {
    "country": "Bermuda",
    "country_code": "BM",
    "city": "Hamilton",
    "lat": 43.25608,
    "lon": -79.872858,
    "spread": 0.12
  },
  {
    "country": "Bhutan",
    "country_code": "BT",
    "city": "Thimphu",
    "lat": 27.472762,
    "lon": 89.629548,
    "spread": 0.12
  },
  {
    "country": "Bolivia, Plurinational State of",
    "country_code": "BO",
    "city": "Sucre",
    "lat": -19.047725,
    "lon": -65.259431,
    "spread": 0.12
  },
  {
    "country": "Bonaire, Sint Eustatius and Saba",
    "country_code": "BQ",
    "city": "Kralendijk",
    "lat": 12.1443,
    "lon": -68.2655,
    "spread": 0.12
  },
  {
    "country": "Bosnia and Herzegovina",
    "country_code": "BA",
    "city": "Sarajevo",
    "lat": 43.851977,
    "lon": 18.386687,
    "spread": 0.12
  },
  {
    "country": "Botswana",
    "country_code": "BW",
    "city": "Gaborone",
    "lat": -24.658136,
    "lon": 25.908847,
    "spread": 0.12
  },
  {
    "country": "Bouvet Island",
    "country_code": "BV",
    "city": "Bouvet Island Center",
    "lat": -54.4208,
    "lon": 3.3464,
    "spread": 0.14
  },
  {
    "country": "Brazil",
    "country_code": "BR",
    "city": "Brasília",
    "lat": -10.333333,
    "lon": -53.2,
    "spread": 0.14
  },
  {
    "country": "British Indian Ocean Territory",
    "country_code": "IO",
    "city": "Diego Garcia",
    "lat": -7.338358,
    "lon": 72.471815,
    "spread": 0.12
  },
  {
    "country": "Brunei Darussalam",
    "country_code": "BN",
    "city": "Bandar Seri Begawan",
    "lat": 4.889545,
    "lon": 114.941757,
    "spread": 0.12
  },
  {
    "country": "Bulgaria",
    "country_code": "BG",
    "city": "Sofia",
    "lat": -15.25384,
    "lon": 48.256216,
    "spread": 0.12
  },
  {
    "country": "Burkina Faso",
    "country_code": "BF",
    "city": "Ouagadougou",
    "lat": 12.368187,
    "lon": -1.527094,
    "spread": 0.12
  },
  {
    "country": "Burundi",
    "country_code": "BI",
    "city": "Bujumbura",
    "lat": -3.363812,
    "lon": 29.367503,
    "spread": 0.12
  },
  {
    "country": "Cabo Verde",
    "country_code": "CV",
    "city": "Praia",
    "lat": 14.916017,
    "lon": -23.509613,
    "spread": 0.12
  },
  {
    "country": "Cambodia",
    "country_code": "KH",
    "city": "Phnom Penh",
    "lat": 11.568271,
    "lon": 104.922443,
    "spread": 0.12
  },
  {
    "country": "Cameroon",
    "country_code": "CM",
    "city": "Yaoundé",
    "lat": 3.868987,
    "lon": 11.521334,
    "spread": 0.12
  },
  {
    "country": "Canada",
    "country_code": "CA",
    "city": "Ottawa",
    "lat": 45.421106,
    "lon": -75.690308,
    "spread": 0.14
  },
  {
    "country": "Cayman Islands",
    "country_code": "KY",
    "city": "George Town",
    "lat": 5.414568,
    "lon": 100.329804,
    "spread": 0.12
  },
  {
    "country": "Central African Republic",
    "country_code": "CF",
    "city": "Bangui",
    "lat": 4.390715,
    "lon": 18.550913,
    "spread": 0.12
  },
  {
    "country": "Chad",
    "country_code": "TD",
    "city": "N'Djamena",
    "lat": 12.119154,
    "lon": 15.050276,
    "spread": 0.12
  },
  {
    "country": "Chile",
    "country_code": "CL",
    "city": "Santiago",
    "lat": 9.869479,
    "lon": -83.798075,
    "spread": 0.12
  },
  {
    "country": "China",
    "country_code": "CN",
    "city": "Beijing",
    "lat": 39.906217,
    "lon": 116.391276,
    "spread": 0.14
  },
  {
    "country": "Christmas Island",
    "country_code": "CX",
    "city": "Flying Fish Cove",
    "lat": -10.426665,
    "lon": 105.668672,
    "spread": 0.12
  },
  {
    "country": "Cocos (Keeling) Islands",
    "country_code": "CC",
    "city": "West Island",
    "lat": -12.189848,
    "lon": 96.830449,
    "spread": 0.12
  },
  {
    "country": "Colombia",
    "country_code": "CO",
    "city": "Bogotá",
    "lat": 4.59808,
    "lon": -74.076044,
    "spread": 0.12
  },
  {
    "country": "Comoros",
    "country_code": "KM",
    "city": "Moroni",
    "lat": -11.693126,
    "lon": 43.254304,
    "spread": 0.12
  },
  {
    "country": "Congo",
    "country_code": "CG",
    "city": "Brazzaville",
    "lat": -4.269441,
    "lon": 15.271226,
    "spread": 0.12
  },
  {
    "country": "Congo, The Democratic Republic of the",
    "country_code": "CD",
    "city": "Kinshasa",
    "lat": -4.321706,
    "lon": 15.312597,
    "spread": 0.12
  },
  {
    "country": "Cook Islands",
    "country_code": "CK",
    "city": "Avarua",
    "lat": -21.207474,
    "lon": -159.770814,
    "spread": 0.12
  },
  {
    "country": "Costa Rica",
    "country_code": "CR",
    "city": "San José",
    "lat": 9.932543,
    "lon": -84.079578,
    "spread": 0.12
  },
  {
    "country": "Croatia",
    "country_code": "HR",
    "city": "Zagreb",
    "lat": 45.813177,
    "lon": 15.977048,
    "spread": 0.12
  },
  {
    "country": "Cuba",
    "country_code": "CU",
    "city": "Havana",
    "lat": 23.135305,
    "lon": -82.358963,
    "spread": 0.12
  },
  {
    "country": "Curaçao",
    "country_code": "CW",
    "city": "Willemstad",
    "lat": 12.1084,
    "lon": -68.9335,
    "spread": 0.12
  },
  {
    "country": "Cyprus",
    "country_code": "CY",
    "city": "Nicosia",
    "lat": 35.17393,
    "lon": 33.364726,
    "spread": 0.12
  },
  {
    "country": "Czechia",
    "country_code": "CZ",
    "city": "Prague",
    "lat": 50.087465,
    "lon": 14.421254,
    "spread": 0.12
  },
  {
    "country": "Côte d'Ivoire",
    "country_code": "CI",
    "city": "Yamoussoukro",
    "lat": 6.809107,
    "lon": -5.273263,
    "spread": 0.12
  },
  {
    "country": "Denmark",
    "country_code": "DK",
    "city": "Copenhagen",
    "lat": 55.686724,
    "lon": 12.570072,
    "spread": 0.12
  },
  {
    "country": "Djibouti",
    "country_code": "DJ",
    "city": "Djibouti",
    "lat": 11.814597,
    "lon": 42.845306,
    "spread": 0.12
  },
  {
    "country": "Dominica",
    "country_code": "DM",
    "city": "Roseau",
    "lat": 48.771037,
    "lon": -95.769788,
    "spread": 0.12
  },
  {
    "country": "Dominican Republic",
    "country_code": "DO",
    "city": "Santo Domingo",
    "lat": 18.480197,
    "lon": -69.942111,
    "spread": 0.12
  },
  {
    "country": "Ecuador",
    "country_code": "EC",
    "city": "Quito",
    "lat": -0.220164,
    "lon": -78.512327,
    "spread": 0.12
  },
  {
    "country": "Egypt",
    "country_code": "EG",
    "city": "Cairo",
    "lat": 30.048819,
    "lon": 31.243666,
    "spread": 0.12
  },
  {
    "country": "El Salvador",
    "country_code": "SV",
    "city": "San Salvador",
    "lat": 13.698994,
    "lon": -89.191425,
    "spread": 0.12
  },
  {
    "country": "Equatorial Guinea",
    "country_code": "GQ",
    "city": "Malabo",
    "lat": 3.752828,
    "lon": 8.780061,
    "spread": 0.12
  },
  {
    "country": "Eritrea",
    "country_code": "ER",
    "city": "Asmara",
    "lat": 15.338967,
    "lon": 38.932676,
    "spread": 0.12
  },
  {
    "country": "Estonia",
    "country_code": "EE",
    "city": "Tallinn",
    "lat": 59.437216,
    "lon": 24.745369,
    "spread": 0.12
  },
  {
    "country": "Eswatini",
    "country_code": "SZ",
    "city": "Lobamba",
    "lat": -26.446285,
    "lon": 31.208378,
    "spread": 0.12
  },
  {
    "country": "Ethiopia",
    "country_code": "ET",
    "city": "Addis Ababa",
    "lat": 9.010793,
    "lon": 38.761252,
    "spread": 0.12
  },
  {
    "country": "Falkland Islands (Malvinas)",
    "country_code": "FK",
    "city": "Stanley",
    "lat": -51.695058,
    "lon": -57.849169,
    "spread": 0.12
  },
  {
    "country": "Faroe Islands",
    "country_code": "FO",
    "city": "Tórshavn",
    "lat": 62.012,
    "lon": -6.768,
    "spread": 0.12
  },
  {
    "country": "Fiji",
    "country_code": "FJ",
    "city": "Suva",
    "lat": -18.141588,
    "lon": 178.442166,
    "spread": 0.12
  },
  {
    "country": "Finland",
    "country_code": "FI",
    "city": "Helsinki",
    "lat": 60.16741,
    "lon": 24.942577,
    "spread": 0.12
  },
  {
    "country": "France",
    "country_code": "FR",
    "city": "Paris",
    "lat": 48.856697,
    "lon": 2.351462,
    "spread": 0.12
  },
  {
    "country": "French Guiana",
    "country_code": "GF",
    "city": "Cayenne",
    "lat": 4.937114,
    "lon": -52.325831,
    "spread": 0.12
  },
  {
    "country": "French Polynesia",
    "country_code": "PF",
    "city": "Papeetē",
    "lat": -17.537384,
    "lon": -149.565996,
    "spread": 0.12
  },
  {
    "country": "French Southern Territories",
    "country_code": "TF",
    "city": "Port-aux-Français",
    "lat": -49.353677,
    "lon": 70.243567,
    "spread": 0.12
  },
  {
    "country": "Gabon",
    "country_code": "GA",
    "city": "Libreville",
    "lat": 0.390002,
    "lon": 9.454001,
    "spread": 0.12
  },
  {
    "country": "Gambia",
    "country_code": "GM",
    "city": "Banjul",
    "lat": 13.441346,
    "lon": -16.562471,
    "spread": 0.12
  },
  {
    "country": "Georgia",
    "country_code": "GE",
    "city": "Tbilisi",
    "lat": 41.693459,
    "lon": 44.80145,
    "spread": 0.12
  },
  {
    "country": "Germany",
    "country_code": "DE",
    "city": "Berlin",
    "lat": 52.517036,
    "lon": 13.38886,
    "spread": 0.12
  },
  {
    "country": "Ghana",
    "country_code": "GH",
    "city": "Accra",
    "lat": 5.560014,
    "lon": -0.205744,
    "spread": 0.12
  },
  {
    "country": "Gibraltar",
    "country_code": "GI",
    "city": "Gibraltar",
    "lat": 36.140807,
    "lon": -5.35413,
    "spread": 0.12
  },
  {
    "country": "Greece",
    "country_code": "GR",
    "city": "Athens",
    "lat": 37.983941,
    "lon": 23.728305,
    "spread": 0.12
  },
  {
    "country": "Greenland",
    "country_code": "GL",
    "city": "Nuuk",
    "lat": 64.175029,
    "lon": -51.735539,
    "spread": 0.12
  },
  {
    "country": "Grenada",
    "country_code": "GD",
    "city": "St. George's",
    "lat": 48.658138,
    "lon": 6.928099,
    "spread": 0.12
  },
  {
    "country": "Guadeloupe",
    "country_code": "GP",
    "city": "Basse-Terre",
    "lat": 16.000078,
    "lon": -61.733337,
    "spread": 0.12
  },
  {
    "country": "Guam",
    "country_code": "GU",
    "city": "Hagåtña",
    "lat": 13.472745,
    "lon": 144.752018,
    "spread": 0.12
  },
  {
    "country": "Guatemala",
    "country_code": "GT",
    "city": "Guatemala City",
    "lat": 14.622233,
    "lon": -90.518519,
    "spread": 0.12
  },
  {
    "country": "Guernsey",
    "country_code": "GG",
    "city": "St. Peter Port",
    "lat": 49.456814,
    "lon": -2.538998,
    "spread": 0.12
  },
  {
    "country": "Guinea",
    "country_code": "GN",
    "city": "Conakry",
    "lat": 9.51706,
    "lon": -13.699843,
    "spread": 0.12
  },
  {
    "country": "Guinea-Bissau",
    "country_code": "GW",
    "city": "Bissau",
    "lat": 11.861324,
    "lon": -15.583055,
    "spread": 0.12
  },
  {
    "country": "Guyana",
    "country_code": "GY",
    "city": "Georgetown",
    "lat": 6.802577,
    "lon": -58.162861,
    "spread": 0.12
  },
  {
    "country": "Haiti",
    "country_code": "HT",
    "city": "Port-au-Prince",
    "lat": 18.547327,
    "lon": -72.339593,
    "spread": 0.12
  },
  {
    "country": "Heard Island and McDonald Islands",
    "country_code": "HM",
    "city": "Heard Island Center",
    "lat": -53.0818,
    "lon": 73.5042,
    "spread": 0.14
  },
  {
    "country": "Holy See (Vatican City State)",
    "country_code": "VA",
    "city": "Vatican City",
    "lat": 41.9029,
    "lon": 12.4534,
    "spread": 0.12
  },
  {
    "country": "Honduras",
    "country_code": "HN",
    "city": "Tegucigalpa",
    "lat": 14.105686,
    "lon": -87.204676,
    "spread": 0.12
  },
  {
    "country": "Hong Kong",
    "country_code": "HK",
    "city": "City of Victoria",
    "lat": -36.59861,
    "lon": 144.678005,
    "spread": 0.12
  },
  {
    "country": "Hungary",
    "country_code": "HU",
    "city": "Budapest",
    "lat": 47.498382,
    "lon": 19.040471,
    "spread": 0.12
  },
  {
    "country": "Iceland",
    "country_code": "IS",
    "city": "Reykjavik",
    "lat": 64.145981,
    "lon": -21.942237,
    "spread": 0.12
  },
  {
    "country": "India",
    "country_code": "IN",
    "city": "New Delhi",
    "lat": 28.614179,
    "lon": 77.202266,
    "spread": 0.14
  },
  {
    "country": "Indonesia",
    "country_code": "ID",
    "city": "Jakarta",
    "lat": -6.175394,
    "lon": 106.827183,
    "spread": 0.12
  },
  {
    "country": "Iran, Islamic Republic of",
    "country_code": "IR",
    "city": "Tehran",
    "lat": 35.700618,
    "lon": 51.401378,
    "spread": 0.12
  },
  {
    "country": "Iraq",
    "country_code": "IQ",
    "city": "Baghdad",
    "lat": 33.302431,
    "lon": 44.378799,
    "spread": 0.12
  },
  {
    "country": "Ireland",
    "country_code": "IE",
    "city": "Dublin",
    "lat": 53.349764,
    "lon": -6.260273,
    "spread": 0.12
  },
  {
    "country": "Isle of Man",
    "country_code": "IM",
    "city": "Douglas",
    "lat": 39.762842,
    "lon": -88.217052,
    "spread": 0.12
  },
  {
    "country": "Israel",
    "country_code": "IL",
    "city": "Jerusalem",
    "lat": 31.778345,
    "lon": 35.225079,
    "spread": 0.12
  },
  {
    "country": "Italy",
    "country_code": "IT",
    "city": "Rome",
    "lat": 41.89332,
    "lon": 12.482932,
    "spread": 0.12
  },
  {
    "country": "Jamaica",
    "country_code": "JM",
    "city": "Kingston",
    "lat": 17.971215,
    "lon": -76.792813,
    "spread": 0.12
  },
  {
    "country": "Japan",
    "country_code": "JP",
    "city": "Tokyo",
    "lat": 35.682839,
    "lon": 139.759455,
    "spread": 0.12
  },
  {
    "country": "Jersey",
    "country_code": "JE",
    "city": "Saint Helier",
    "lat": 47.384387,
    "lon": 4.683325,
    "spread": 0.12
  },
  {
    "country": "Jordan",
    "country_code": "JO",
    "city": "Amman",
    "lat": 31.951569,
    "lon": 35.923962,
    "spread": 0.12
  },
  {
    "country": "Kazakhstan",
    "country_code": "KZ",
    "city": "Astana",
    "lat": 51.12822,
    "lon": 71.430668,
    "spread": 0.12
  },
  {
    "country": "Kenya",
    "country_code": "KE",
    "city": "Nairobi",
    "lat": -1.283253,
    "lon": 36.817245,
    "spread": 0.12
  },
  {
    "country": "Kiribati",
    "country_code": "KI",
    "city": "South Tarawa",
    "lat": 1.349078,
    "lon": 173.038651,
    "spread": 0.12
  },
  {
    "country": "Korea, Democratic People's Republic of",
    "country_code": "KP",
    "city": "Pyongyang",
    "lat": 39.019474,
    "lon": 125.753388,
    "spread": 0.12
  },
  {
    "country": "Korea, Republic of",
    "country_code": "KR",
    "city": "Seoul",
    "lat": 37.566679,
    "lon": 126.978291,
    "spread": 0.12
  },
  {
    "country": "Kuwait",
    "country_code": "KW",
    "city": "Kuwait City",
    "lat": 29.379709,
    "lon": 47.973563,
    "spread": 0.12
  },
  {
    "country": "Kyrgyzstan",
    "country_code": "KG",
    "city": "Bishkek",
    "lat": 42.876562,
    "lon": 74.607008,
    "spread": 0.12
  },
  {
    "country": "Lao People's Democratic Republic",
    "country_code": "LA",
    "city": "Vientiane",
    "lat": 17.964099,
    "lon": 102.613371,
    "spread": 0.12
  },
  {
    "country": "Latvia",
    "country_code": "LV",
    "city": "Riga",
    "lat": 56.949398,
    "lon": 24.105185,
    "spread": 0.12
  },
  {
    "country": "Lebanon",
    "country_code": "LB",
    "city": "Beirut",
    "lat": 33.89592,
    "lon": 35.47843,
    "spread": 0.12
  },
  {
    "country": "Lesotho",
    "country_code": "LS",
    "city": "Maseru",
    "lat": -29.310054,
    "lon": 27.478222,
    "spread": 0.12
  },
  {
    "country": "Liberia",
    "country_code": "LR",
    "city": "Monrovia",
    "lat": 6.328034,
    "lon": -10.797788,
    "spread": 0.12
  },
  {
    "country": "Libya",
    "country_code": "LY",
    "city": "Tripoli",
    "lat": 32.896672,
    "lon": 13.177792,
    "spread": 0.12
  },
  {
    "country": "Liechtenstein",
    "country_code": "LI",
    "city": "Vaduz",
    "lat": 47.139286,
    "lon": 9.522796,
    "spread": 0.12
  },
  {
    "country": "Lithuania",
    "country_code": "LT",
    "city": "Vilnius",
    "lat": 54.687046,
    "lon": 25.282911,
    "spread": 0.12
  },
  {
    "country": "Luxembourg",
    "country_code": "LU",
    "city": "Luxembourg",
    "lat": 49.815868,
    "lon": 6.129675,
    "spread": 0.12
  },
  {
    "country": "Macao",
    "country_code": "MO",
    "city": "Macau",
    "lat": 22.1987,
    "lon": 113.5439,
    "spread": 0.12
  },
  {
    "country": "Madagascar",
    "country_code": "MG",
    "city": "Antananarivo",
    "lat": -18.910012,
    "lon": 47.525581,
    "spread": 0.12
  },
  {
    "country": "Malawi",
    "country_code": "MW",
    "city": "Lilongwe",
    "lat": -13.987511,
    "lon": 33.768144,
    "spread": 0.12
  },
  {
    "country": "Malaysia",
    "country_code": "MY",
    "city": "Kuala Lumpur",
    "lat": 3.151696,
    "lon": 101.694237,
    "spread": 0.12
  },
  {
    "country": "Maldives",
    "country_code": "MV",
    "city": "Malé",
    "lat": 16.370036,
    "lon": -2.290024,
    "spread": 0.12
  },
  {
    "country": "Mali",
    "country_code": "ML",
    "city": "Bamako",
    "lat": 12.605033,
    "lon": -7.986514,
    "spread": 0.12
  },
  {
    "country": "Malta",
    "country_code": "MT",
    "city": "Valletta",
    "lat": 35.898982,
    "lon": 14.513676,
    "spread": 0.12
  },
  {
    "country": "Marshall Islands",
    "country_code": "MH",
    "city": "Majuro",
    "lat": 7.090992,
    "lon": 171.381635,
    "spread": 0.12
  },
  {
    "country": "Martinique",
    "country_code": "MQ",
    "city": "Fort-de-France",
    "lat": 14.602796,
    "lon": -61.067672,
    "spread": 0.12
  },
  {
    "country": "Mauritania",
    "country_code": "MR",
    "city": "Nouakchott",
    "lat": 18.079238,
    "lon": -15.978007,
    "spread": 0.12
  },
  {
    "country": "Mauritius",
    "country_code": "MU",
    "city": "Port Louis",
    "lat": -20.163728,
    "lon": 57.504533,
    "spread": 0.12
  },
  {
    "country": "Mayotte",
    "country_code": "YT",
    "city": "Mamoudzou",
    "lat": -12.780586,
    "lon": 45.227991,
    "spread": 0.12
  },
  {
    "country": "Mexico",
    "country_code": "MX",
    "city": "Mexico City",
    "lat": 19.43263,
    "lon": -99.133178,
    "spread": 0.12
  },
  {
    "country": "Micronesia, Federated States of",
    "country_code": "FM",
    "city": "Palikir",
    "lat": 6.920744,
    "lon": 158.162714,
    "spread": 0.12
  },
  {
    "country": "Moldova, Republic of",
    "country_code": "MD",
    "city": "Chișinău",
    "lat": 47.024471,
    "lon": 28.832253,
    "spread": 0.12
  },
  {
    "country": "Monaco",
    "country_code": "MC",
    "city": "Monaco",
    "lat": 43.732349,
    "lon": 7.427683,
    "spread": 0.12
  },
  {
    "country": "Mongolia",
    "country_code": "MN",
    "city": "Ulan Bator",
    "lat": 47.918468,
    "lon": 106.917702,
    "spread": 0.12
  },
  {
    "country": "Montenegro",
    "country_code": "ME",
    "city": "Podgorica",
    "lat": 42.4304,
    "lon": 19.2594,
    "spread": 0.12
  },
  {
    "country": "Montserrat",
    "country_code": "MS",
    "city": "Plymouth",
    "lat": 50.371266,
    "lon": -4.142566,
    "spread": 0.12
  },
  {
    "country": "Morocco",
    "country_code": "MA",
    "city": "Rabat",
    "lat": 34.022405,
    "lon": -6.834543,
    "spread": 0.12
  },
  {
    "country": "Mozambique",
    "country_code": "MZ",
    "city": "Maputo",
    "lat": -25.966213,
    "lon": 32.56745,
    "spread": 0.12
  },
  {
    "country": "Myanmar",
    "country_code": "MM",
    "city": "Naypyidaw",
    "lat": 19.7633,
    "lon": 96.0785,
    "spread": 0.12
  },
  {
    "country": "Namibia",
    "country_code": "NA",
    "city": "Windhoek",
    "lat": -22.574392,
    "lon": 17.079069,
    "spread": 0.12
  },
  {
    "country": "Nauru",
    "country_code": "NR",
    "city": "Yaren",
    "lat": -0.547101,
    "lon": 166.9164,
    "spread": 0.12
  },
  {
    "country": "Nepal",
    "country_code": "NP",
    "city": "Kathmandu",
    "lat": 27.708317,
    "lon": 85.320582,
    "spread": 0.12
  },
  {
    "country": "Netherlands",
    "country_code": "NL",
    "city": "Amsterdam",
    "lat": 52.37276,
    "lon": 4.893604,
    "spread": 0.12
  },
  {
    "country": "New Caledonia",
    "country_code": "NC",
    "city": "Nouméa",
    "lat": -22.274526,
    "lon": 166.442419,
    "spread": 0.12
  },
  {
    "country": "New Zealand",
    "country_code": "NZ",
    "city": "Wellington",
    "lat": -41.288795,
    "lon": 174.777211,
    "spread": 0.12
  },
  {
    "country": "Nicaragua",
    "country_code": "NI",
    "city": "Managua",
    "lat": 12.145991,
    "lon": -86.274666,
    "spread": 0.12
  },
  {
    "country": "Niger",
    "country_code": "NE",
    "city": "Niamey",
    "lat": 13.524834,
    "lon": 2.109823,
    "spread": 0.12
  },
  {
    "country": "Nigeria",
    "country_code": "NG",
    "city": "Abuja",
    "lat": 9.06433,
    "lon": 7.489297,
    "spread": 0.12
  },
  {
    "country": "Niue",
    "country_code": "NU",
    "city": "Alofi",
    "lat": -19.053416,
    "lon": -169.919199,
    "spread": 0.12
  },
  {
    "country": "Norfolk Island",
    "country_code": "NF",
    "city": "Kingston",
    "lat": 17.971215,
    "lon": -76.792813,
    "spread": 0.12
  },
  {
    "country": "North Macedonia",
    "country_code": "MK",
    "city": "Skopje",
    "lat": 41.996092,
    "lon": 21.43165,
    "spread": 0.12
  },
  {
    "country": "Northern Mariana Islands",
    "country_code": "MP",
    "city": "Saipan",
    "lat": 15.190983,
    "lon": 145.746853,
    "spread": 0.12
  },
  {
    "country": "Norway",
    "country_code": "NO",
    "city": "Oslo",
    "lat": 59.91333,
    "lon": 10.73897,
    "spread": 0.12
  },
  {
    "country": "Oman",
    "country_code": "OM",
    "city": "Muscat",
    "lat": 23.599786,
    "lon": 58.54513,
    "spread": 0.12
  },
  {
    "country": "Pakistan",
    "country_code": "PK",
    "city": "Islamabad",
    "lat": 33.693812,
    "lon": 73.065151,
    "spread": 0.12
  },
  {
    "country": "Palau",
    "country_code": "PW",
    "city": "Ngerulmud",
    "lat": 7.500619,
    "lon": 134.624301,
    "spread": 0.12
  },
  {
    "country": "Palestine, State of",
    "country_code": "PS",
    "city": "Ramallah",
    "lat": 31.9038,
    "lon": 35.2034,
    "spread": 0.12
  },
  {
    "country": "Panama",
    "country_code": "PA",
    "city": "Panama City",
    "lat": 8.971449,
    "lon": -79.53418,
    "spread": 0.12
  },
  {
    "country": "Papua New Guinea",
    "country_code": "PG",
    "city": "Port Moresby",
    "lat": -9.47433,
    "lon": 147.15995,
    "spread": 0.12
  },
  {
    "country": "Paraguay",
    "country_code": "PY",
    "city": "Asunción",
    "lat": -25.280046,
    "lon": -57.634381,
    "spread": 0.12
  },
  {
    "country": "Peru",
    "country_code": "PE",
    "city": "Lima",
    "lat": -12.062106,
    "lon": -77.036526,
    "spread": 0.12
  },
  {
    "country": "Philippines",
    "country_code": "PH",
    "city": "Manila",
    "lat": 14.590622,
    "lon": 120.97997,
    "spread": 0.12
  },
  {
    "country": "Pitcairn",
    "country_code": "PN",
    "city": "Adamstown",
    "lat": -25.066667,
    "lon": -130.100205,
    "spread": 0.12
  },
  {
    "country": "Poland",
    "country_code": "PL",
    "city": "Warsaw",
    "lat": 52.233717,
    "lon": 21.071411,
    "spread": 0.12
  },
  {
    "country": "Portugal",
    "country_code": "PT",
    "city": "Lisbon",
    "lat": 38.707751,
    "lon": -9.136592,
    "spread": 0.12
  },
  {
    "country": "Puerto Rico",
    "country_code": "PR",
    "city": "San Juan",
    "lat": 18.465299,
    "lon": -66.116666,
    "spread": 0.12
  },
  {
    "country": "Qatar",
    "country_code": "QA",
    "city": "Doha",
    "lat": 25.285633,
    "lon": 51.526416,
    "spread": 0.12
  },
  {
    "country": "Romania",
    "country_code": "RO",
    "city": "Bucharest",
    "lat": 44.436141,
    "lon": 26.10272,
    "spread": 0.12
  },
  {
    "country": "Russian Federation",
    "country_code": "RU",
    "city": "Moscow",
    "lat": 55.750446,
    "lon": 37.617494,
    "spread": 0.14
  },
  {
    "country": "Rwanda",
    "country_code": "RW",
    "city": "Kigali",
    "lat": -1.88596,
    "lon": 30.129675,
    "spread": 0.12
  },
  {
    "country": "Réunion",
    "country_code": "RE",
    "city": "Saint-Denis",
    "lat": 48.935773,
    "lon": 2.358023,
    "spread": 0.12
  },
  {
    "country": "Saint Barthélemy",
    "country_code": "BL",
    "city": "Gustavia",
    "lat": 17.8962,
    "lon": -62.8506,
    "spread": 0.12
  },
  {
    "country": "Saint Helena, Ascension and Tristan da Cunha",
    "country_code": "SH",
    "city": "Jamestown",
    "lat": 37.210443,
    "lon": -76.773893,
    "spread": 0.12
  },
  {
    "country": "Saint Kitts and Nevis",
    "country_code": "KN",
    "city": "Basseterre",
    "lat": 17.296092,
    "lon": -62.722301,
    "spread": 0.12
  },
  {
    "country": "Saint Lucia",
    "country_code": "LC",
    "city": "Castries",
    "lat": 13.952589,
    "lon": -60.987824,
    "spread": 0.12
  },
  {
    "country": "Saint Martin (French part)",
    "country_code": "MF",
    "city": "Marigot",
    "lat": 18.0675,
    "lon": -63.0829,
    "spread": 0.12
  },
  {
    "country": "Saint Pierre and Miquelon",
    "country_code": "PM",
    "city": "Saint-Pierre",
    "lat": 48.383272,
    "lon": 7.471873,
    "spread": 0.12
  },
  {
    "country": "Saint Vincent and the Grenadines",
    "country_code": "VC",
    "city": "Kingstown",
    "lat": 13.156186,
    "lon": -61.227962,
    "spread": 0.12
  },
  {
    "country": "Samoa",
    "country_code": "WS",
    "city": "Apia",
    "lat": -13.834369,
    "lon": -171.769279,
    "spread": 0.12
  },
  {
    "country": "San Marino",
    "country_code": "SM",
    "city": "City of San Marino",
    "lat": 43.9364,
    "lon": 12.446699,
    "spread": 0.12
  },
  {
    "country": "Sao Tome and Principe",
    "country_code": "ST",
    "city": "São Tomé",
    "lat": 0.338924,
    "lon": 6.731303,
    "spread": 0.12
  },
  {
    "country": "Saudi Arabia",
    "country_code": "SA",
    "city": "Riyadh",
    "lat": 24.631969,
    "lon": 46.715065,
    "spread": 0.12
  },
  {
    "country": "Senegal",
    "country_code": "SN",
    "city": "Dakar",
    "lat": 14.693425,
    "lon": -17.447938,
    "spread": 0.12
  },
  {
    "country": "Serbia",
    "country_code": "RS",
    "city": "Belgrade",
    "lat": 44.817813,
    "lon": 20.456897,
    "spread": 0.12
  },
  {
    "country": "Seychelles",
    "country_code": "SC",
    "city": "Victoria",
    "lat": -36.59861,
    "lon": 144.678005,
    "spread": 0.12
  },
  {
    "country": "Sierra Leone",
    "country_code": "SL",
    "city": "Freetown",
    "lat": 8.479004,
    "lon": -13.26795,
    "spread": 0.12
  },
  {
    "country": "Singapore",
    "country_code": "SG",
    "city": "Singapore",
    "lat": 1.357107,
    "lon": 103.819499,
    "spread": 0.12
  },
  {
    "country": "Sint Maarten (Dutch part)",
    "country_code": "SX",
    "city": "Philipsburg",
    "lat": 18.026,
    "lon": -63.0458,
    "spread": 0.12
  },
  {
    "country": "Slovakia",
    "country_code": "SK",
    "city": "Bratislava",
    "lat": 48.151699,
    "lon": 17.109306,
    "spread": 0.12
  },
  {
    "country": "Slovenia",
    "country_code": "SI",
    "city": "Ljubljana",
    "lat": 46.04998,
    "lon": 14.50686,
    "spread": 0.12
  },
  {
    "country": "Solomon Islands",
    "country_code": "SB",
    "city": "Honiara",
    "lat": -9.431077,
    "lon": 159.955255,
    "spread": 0.12
  },
  {
    "country": "Somalia",
    "country_code": "SO",
    "city": "Mogadishu",
    "lat": 2.042778,
    "lon": 45.338564,
    "spread": 0.12
  },
  {
    "country": "South Africa",
    "country_code": "ZA",
    "city": "Pretoria",
    "lat": -25.745937,
    "lon": 28.187944,
    "spread": 0.12
  },
  {
    "country": "South Georgia and the South Sandwich Islands",
    "country_code": "GS",
    "city": "King Edward Point",
    "lat": -54.283545,
    "lon": -36.494636,
    "spread": 0.12
  },
  {
    "country": "South Sudan",
    "country_code": "SS",
    "city": "Juba",
    "lat": 4.847202,
    "lon": 31.595166,
    "spread": 0.12
  },
  {
    "country": "Spain",
    "country_code": "ES",
    "city": "Madrid",
    "lat": 40.416705,
    "lon": -3.703582,
    "spread": 0.12
  },
  {
    "country": "Sri Lanka",
    "country_code": "LK",
    "city": "Colombo",
    "lat": 6.934997,
    "lon": 79.853846,
    "spread": 0.12
  },
  {
    "country": "Sudan",
    "country_code": "SD",
    "city": "Khartoum",
    "lat": 15.593325,
    "lon": 32.53565,
    "spread": 0.12
  },
  {
    "country": "Suriname",
    "country_code": "SR",
    "city": "Paramaribo",
    "lat": 5.821609,
    "lon": -55.177043,
    "spread": 0.12
  },
  {
    "country": "Svalbard and Jan Mayen",
    "country_code": "SJ",
    "city": "Longyearbyen",
    "lat": 78.223156,
    "lon": 15.646366,
    "spread": 0.12
  },
  {
    "country": "Sweden",
    "country_code": "SE",
    "city": "Stockholm",
    "lat": 59.325117,
    "lon": 18.071094,
    "spread": 0.12
  },
  {
    "country": "Switzerland",
    "country_code": "CH",
    "city": "Bern",
    "lat": 46.948271,
    "lon": 7.451451,
    "spread": 0.12
  },
  {
    "country": "Syrian Arab Republic",
    "country_code": "SY",
    "city": "Damascus",
    "lat": 33.51307,
    "lon": 36.309581,
    "spread": 0.12
  },
  {
    "country": "Taiwan, Province of China",
    "country_code": "TW",
    "city": "Taipei",
    "lat": 25.03752,
    "lon": 121.56368,
    "spread": 0.12
  },
  {
    "country": "Tajikistan",
    "country_code": "TJ",
    "city": "Dushanbe",
    "lat": 38.542584,
    "lon": 68.815214,
    "spread": 0.12
  },
  {
    "country": "Tanzania, United Republic of",
    "country_code": "TZ",
    "city": "Dodoma",
    "lat": -6.337282,
    "lon": 35.737177,
    "spread": 0.12
  },
  {
    "country": "Thailand",
    "country_code": "TH",
    "city": "Bangkok",
    "lat": 13.754253,
    "lon": 100.493087,
    "spread": 0.12
  },
  {
    "country": "Timor-Leste",
    "country_code": "TL",
    "city": "Dili",
    "lat": 28.651718,
    "lon": 77.221939,
    "spread": 0.12
  },
  {
    "country": "Togo",
    "country_code": "TG",
    "city": "Lomé",
    "lat": 6.130419,
    "lon": 1.215829,
    "spread": 0.12
  },
  {
    "country": "Tokelau",
    "country_code": "TK",
    "city": "Fakaofo",
    "lat": -9.374305,
    "lon": -171.264536,
    "spread": 0.12
  },
  {
    "country": "Tonga",
    "country_code": "TO",
    "city": "Nuku'alofa",
    "lat": -21.13434,
    "lon": -175.201808,
    "spread": 0.12
  },
  {
    "country": "Trinidad and Tobago",
    "country_code": "TT",
    "city": "Port of Spain",
    "lat": 10.657268,
    "lon": -61.518017,
    "spread": 0.12
  },
  {
    "country": "Tunisia",
    "country_code": "TN",
    "city": "Tunis",
    "lat": 33.843941,
    "lon": 9.400138,
    "spread": 0.12
  },
  {
    "country": "Turkmenistan",
    "country_code": "TM",
    "city": "Ashgabat",
    "lat": 37.939668,
    "lon": 58.387426,
    "spread": 0.12
  },
  {
    "country": "Turks and Caicos Islands",
    "country_code": "TC",
    "city": "Cockburn Town",
    "lat": 21.4612,
    "lon": -71.1419,
    "spread": 0.12
  },
  {
    "country": "Tuvalu",
    "country_code": "TV",
    "city": "Funafuti",
    "lat": -8.534995,
    "lon": 179.11865,
    "spread": 0.12
  },
  {
    "country": "Türkiye",
    "country_code": "TR",
    "city": "Ankara",
    "lat": 39.920777,
    "lon": 32.854067,
    "spread": 0.12
  },
  {
    "country": "Uganda",
    "country_code": "UG",
    "city": "Kampala",
    "lat": 0.317714,
    "lon": 32.581354,
    "spread": 0.12
  },
  {
    "country": "Ukraine",
    "country_code": "UA",
    "city": "Kiev",
    "lat": 50.450034,
    "lon": 30.524136,
    "spread": 0.12
  },
  {
    "country": "United Arab Emirates",
    "country_code": "AE",
    "city": "Abu Dhabi",
    "lat": 24.474796,
    "lon": 54.370576,
    "spread": 0.12
  },
  {
    "country": "United Kingdom",
    "country_code": "GB",
    "city": "London",
    "lat": 51.507322,
    "lon": -0.127647,
    "spread": 0.12
  },
  {
    "country": "United States",
    "country_code": "US",
    "city": "Washington D.C.",
    "lat": 38.894986,
    "lon": -77.036571,
    "spread": 0.14
  },
  {
    "country": "United States Minor Outlying Islands",
    "country_code": "UM",
    "city": "Wake Island Center",
    "lat": 19.2823,
    "lon": 166.647,
    "spread": 0.14
  },
  {
    "country": "Uruguay",
    "country_code": "UY",
    "city": "Montevideo",
    "lat": -34.905904,
    "lon": -56.191357,
    "spread": 0.12
  },
  {
    "country": "Uzbekistan",
    "country_code": "UZ",
    "city": "Tashkent",
    "lat": 41.312336,
    "lon": 69.278708,
    "spread": 0.12
  },
  {
    "country": "Vanuatu",
    "country_code": "VU",
    "city": "Port Vila",
    "lat": -17.741497,
    "lon": 168.315016,
    "spread": 0.12
  },
  {
    "country": "Venezuela, Bolivarian Republic of",
    "country_code": "VE",
    "city": "Caracas",
    "lat": 10.506098,
    "lon": -66.914602,
    "spread": 0.12
  },
  {
    "country": "Viet Nam",
    "country_code": "VN",
    "city": "Hanoi",
    "lat": 21.02945,
    "lon": 105.854444,
    "spread": 0.12
  },
  {
    "country": "Virgin Islands, British",
    "country_code": "VG",
    "city": "Road Town",
    "lat": 18.4286,
    "lon": -64.6185,
    "spread": 0.12
  },
  {
    "country": "Virgin Islands, U.S.",
    "country_code": "VI",
    "city": "Charlotte Amalie",
    "lat": 18.3419,
    "lon": -64.9307,
    "spread": 0.12
  },
  {
    "country": "Wallis and Futuna",
    "country_code": "WF",
    "city": "Mata-Utu",
    "lat": -13.282042,
    "lon": -176.174022,
    "spread": 0.12
  },
  {
    "country": "Western Sahara",
    "country_code": "EH",
    "city": "El Aaiún",
    "lat": 27.154512,
    "lon": -13.195392,
    "spread": 0.12
  },
  {
    "country": "Yemen",
    "country_code": "YE",
    "city": "Sana'a",
    "lat": 15.353857,
    "lon": 44.205884,
    "spread": 0.12
  },
  {
    "country": "Zambia",
    "country_code": "ZM",
    "city": "Lusaka",
    "lat": -15.416449,
    "lon": 28.282154,
    "spread": 0.12
  },
  {
    "country": "Zimbabwe",
    "country_code": "ZW",
    "city": "Harare",
    "lat": -17.831773,
    "lon": 31.045686,
    "spread": 0.12
  },
  {
    "country": "Åland Islands",
    "country_code": "AX",
    "city": "Mariehamn",
    "lat": 60.0973,
    "lon": 19.9348,
    "spread": 0.12
  }
]



def normalize_preset_text(value):
    return str(value or '').strip().lower()


def _country_record_from_pycountry(country):
    if country is None:
        return None
    return {
        "name": getattr(country, "name", "") or "",
        "code": getattr(country, "alpha_2", "") or "",
    }


@lru_cache(maxsize=1)
def _country_indexes():
    by_name = {}
    by_code = {}
    names = []
    records = []
    if pycountry is not None:
        try:
            for country in pycountry.countries:
                record = _country_record_from_pycountry(country)
                if record["name"]:
                    records.append(record)
                    aliases = {
                        record["name"],
                        record["code"],
                        getattr(country, "official_name", None),
                        getattr(country, "common_name", None),
                    }
                    for alias in aliases:
                        if alias:
                            by_name[normalize_preset_text(alias)] = record
        except Exception:
            records = []
    if not records:
        records = [dict(entry) for entry in STATIC_COUNTRY_RECORDS]
        for record in records:
            by_name[normalize_preset_text(record.get("name", ""))] = record
    # merge offline catalog aliases/codes where available
    for entry in OFFLINE_LOCATION_CATALOG:
        country = str(entry.get("country", "")).strip()
        code = str(entry.get("country_code", "")).strip().upper()
        if country and normalize_preset_text(country) not in by_name:
            rec = {"name": country, "code": code}
            by_name[normalize_preset_text(country)] = rec
            records.append(rec)
        if code:
            rec = by_name.get(normalize_preset_text(country), {"name": country, "code": code})
            by_code[code] = rec
            by_name[normalize_preset_text(code)] = rec
    dedup = {}
    for record in records:
        name = str(record.get("name", "")).strip()
        if not name:
            continue
        code = str(record.get("code", "")).strip().upper()
        dedup[name] = {"name": name, "code": code}
        if code:
            by_code[code] = {"name": name, "code": code}
            by_name[normalize_preset_text(code)] = {"name": name, "code": code}
        by_name[normalize_preset_text(name)] = {"name": name, "code": code}
    names = sorted(dedup.keys())
    return by_name, by_code, names


def canonical_country_record(value):
    text = str(value or "").strip()
    if not text:
        return None
    by_name, by_code, names = _country_indexes()
    norm = normalize_preset_text(text)
    if norm in by_name:
        return dict(by_name[norm])
    if text.upper() in by_code:
        return dict(by_code[text.upper()])
    # prefix fallback for fully typed countries like "lebanon"
    prefix = [name for name in names if normalize_preset_text(name).startswith(norm)]
    if len(prefix) == 1:
        rec = by_name.get(normalize_preset_text(prefix[0]))
        if rec:
            return dict(rec)
    if pycountry is not None:
        try:
            country = pycountry.countries.lookup(text)
            return _country_record_from_pycountry(country)
        except Exception:
            try:
                country = pycountry.countries.search_fuzzy(text)[0]
                return _country_record_from_pycountry(country)
            except Exception:
                return None
    return None


def get_all_country_names():
    _by_name, _by_code, names = _country_indexes()
    return list(names)


def suggest_map_spread(country_code="", city=""):
    code = str(country_code or "").strip().upper()
    city_n = normalize_preset_text(city)
    if city_n in {
        "sao paulo", "rio de janeiro", "mumbai", "new delhi", "new york", "los angeles",
        "mexico city", "beijing", "shanghai", "moscow", "cairo", "istanbul", "dubai"
    }:
        return 0.14
    if code in BUILDER_LARGE_COUNTRY_CODES:
        return 0.14
    return BUILDER_DEFAULT_MAP_SPREAD


def _catalog_add_entry(catalog, country, country_code, city, lat, lon, spread=None, source="offline", is_capital=False):
    country = str(country or "").strip()
    country_code = str(country_code or "").strip().upper()
    city = str(city or "").strip()
    if not country or not city:
        return
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return
    spread_val = float(spread if spread is not None else suggest_map_spread(country_code, city))
    catalog.setdefault(country, [])
    city_n = normalize_preset_text(city)
    for entry in catalog[country]:
        if normalize_preset_text(entry.get("city")) == city_n:
            entry.update({
                "country": country,
                "country_code": country_code,
                "city": city,
                "lat": lat,
                "lon": lon,
                "spread": spread_val,
                "source": source,
                "is_capital": bool(entry.get("is_capital")) or bool(is_capital),
            })
            return
    catalog[country].append({
        "country": country,
        "country_code": country_code,
        "city": city,
        "lat": lat,
        "lon": lon,
        "spread": spread_val,
        "source": source,
        "is_capital": bool(is_capital),
    })


@lru_cache(maxsize=512)
def _countryinfo_capital_entry(country_name, country_code=""):
    country_name = str(country_name or "").strip()
    country_code = str(country_code or "").strip().upper()
    if not country_name and not country_code:
        return None
    record = canonical_country_record(country_code or country_name)
    target_name = (record or {}).get("name", country_name)
    target_code = (record or {}).get("code", country_code)
    for entry in OFFLINE_CAPITAL_FALLBACKS:
        if normalize_preset_text(entry.get("country")) == normalize_preset_text(target_name) or str(entry.get("country_code", "")).upper() == target_code:
            return {
                "country": target_name,
                "country_code": target_code,
                "city": str(entry.get("city", "")).strip(),
                "lat": float(entry.get("lat", 0.0)),
                "lon": float(entry.get("lon", 0.0)),
                "spread": float(entry.get("spread", suggest_map_spread(target_code, entry.get("city", "")))),
                "source": "offline_capital_catalog",
                "is_capital": True,
            }
    return None


@lru_cache(maxsize=1)
def build_location_catalog():
    catalog = {}
    for item in OFFLINE_MAJOR_CITY_OVERRIDES:
        _catalog_add_entry(
            catalog,
            item.get("country"),
            item.get("country_code"),
            item.get("city"),
            item.get("lat"),
            item.get("lon"),
            item.get("spread"),
            source="offline_city_catalog",
            is_capital=False,
        )
    for preset in CITY_PRESETS.values():
        _catalog_add_entry(
            catalog,
            preset.get("country"),
            preset.get("country_code"),
            preset.get("city"),
            preset.get("lat"),
            preset.get("lon"),
            preset.get("spread"),
            source="legacy_preset",
            is_capital=False,
        )
    for country_name in get_all_country_names():
        record = canonical_country_record(country_name)
        if not record:
            continue
        capital_entry = _countryinfo_capital_entry(record["name"], record["code"])
        if capital_entry:
            _catalog_add_entry(
                catalog,
                capital_entry.get("country"),
                capital_entry.get("country_code"),
                capital_entry.get("city"),
                capital_entry.get("lat"),
                capital_entry.get("lon"),
                capital_entry.get("spread"),
                source=capital_entry.get("source", "capital_catalog"),
                is_capital=True,
            )
    for country_name, entries in catalog.items():
        entries.sort(key=lambda entry: (0 if entry.get("is_capital") else 1, normalize_preset_text(entry.get("city"))))
    return catalog


def get_location_entries_for_country(country_name):
    if not country_name:
        return []
    catalog = build_location_catalog()
    record = canonical_country_record(country_name)
    if record and record["name"] in catalog:
        return list(catalog[record["name"]])
    return list(catalog.get(str(country_name).strip(), []))


@lru_cache(maxsize=512)
def resolve_location_online(country_name, country_code, city_name):
    country_name = str(country_name or "").strip()
    city_name = str(city_name or "").strip()
    if not country_name or not city_name:
        return None
    user_agent = f"{APP_NAME.replace(' ', '-')}/builder-location-lookup"
    queries = [
        {"format": "jsonv2", "limit": 1, "city": city_name, "country": country_name},
        {"format": "jsonv2", "limit": 1, "q": f"{city_name}, {country_name}"},
    ]
    for params in queries:
        try:
            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=ONLINE_GEOCODER_TIMEOUT_SECONDS) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if not payload:
                continue
            top = payload[0]
            return {
                "country": country_name,
                "country_code": str(country_code or "").upper(),
                "city": city_name,
                "lat": float(top.get("lat")),
                "lon": float(top.get("lon")),
                "spread": suggest_map_spread(country_code, city_name),
                "source": "online_geocoder",
                "is_capital": False,
            }
        except Exception:
            continue
    return None


def resolve_location_metadata(country="", city="", allow_online=True):
    country = str(country or "").strip()
    city = str(city or "").strip()
    country_record = canonical_country_record(country)
    country_name = country_record.get("name") if country_record else country
    country_code = country_record.get("code") if country_record else ""
    catalog_entries = get_location_entries_for_country(country_name)
    city_n = normalize_preset_text(city)
    if not country_name and city_n:
        matches = []
        for entries in build_location_catalog().values():
            for entry in entries:
                if normalize_preset_text(entry.get("city")) == city_n:
                    matches.append(entry)
        if len(matches) == 1:
            return dict(matches[0])
    if city_n:
        for entry in catalog_entries:
            if normalize_preset_text(entry.get("city")) == city_n:
                return dict(entry)
    if not city_n:
        if catalog_entries:
            return dict(catalog_entries[0])
        capital_entry = _countryinfo_capital_entry(country_name, country_code)
        if capital_entry:
            return dict(capital_entry)
    if allow_online and country_name and city_n:
        online = resolve_location_online(country_name, country_code, city)
        if online:
            return online
    if catalog_entries:
        fallback = dict(catalog_entries[0])
        fallback["source"] = "capital_fallback"
        if city:
            fallback["requested_city"] = city
        return fallback
    if country_name:
        return {
            "country": country_name,
            "country_code": country_code,
            "city": city,
            "lat": 0.0,
            "lon": 0.0,
            "spread": suggest_map_spread(country_code, city),
            "source": "country_only",
            "is_capital": False,
        }
    return None


def describe_location_resolution(resolved):
    source = str((resolved or {}).get("source", "")).strip().lower()
    country = str((resolved or {}).get("country", "")).strip()
    city = str((resolved or {}).get("city", "")).strip()
    if not resolved:
        return "Choose a country and city. The builder will auto-fill placement from the offline catalog."
    if source == "online_geocoder":
        return f"Auto-filled {city}, {country} using online geocoding."
    if source == "capital_fallback":
        requested = str(resolved.get("requested_city", "")).strip()
        if requested:
            return f"Typed city '{requested}' was not in the offline catalog. Using {city}, {country} as the fallback placement."
        return f"Using {city}, {country} as the fallback placement."
    if source in {"capital_catalog", "offline_capital_catalog", "legacy_preset", "offline_city_catalog"}:
        return f"Auto-filled {city}, {country} from the offline location catalog."
    if source == "country_only":
        return f"Country selected: {country}. City coordinates are not resolved yet."
    return f"Using {city}, {country} for map placement."



def now_display():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_display_timestamp(value):
    value = (value or "").strip()
    if not value:
        return None
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d_%H-%M-%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in patterns:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def parse_ts_local(value):
    return parse_display_timestamp(value)


def safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def digits_or_default(value, default="0"):
    value = "" if value is None else str(value).strip()
    return value if re.fullmatch(r"\d+", value) else default


def decimal_or_default(value, default="0"):
    value = "" if value is None else str(value).strip()
    return value if re.fullmatch(r"\d+(?:\.\d+)?", value) else default




def dominant_tunnel_profile(metrics):
    e = safe_int((metrics or {}).get("tunnel_exploratory", 0))
    c = safe_int((metrics or {}).get("tunnel_client", 0))
    p = safe_int((metrics or {}).get("tunnel_participating", 0))
    total = safe_int((metrics or {}).get("tunnel_count", e + c + p))
    if total <= 0:
        return "none"
    vals = {"exploratory": e, "client": c, "participating": p}
    maxv = max(vals.values())
    winners = [k for k, v in vals.items() if v == maxv and maxv > 0]
    return winners[0] if len(winners) == 1 else "mixed"


def sudo_cmd(*parts):
    return ["sudo", "-n", *parts]


def resolve_deploy_script_path():
    local_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        DEPLOY_SCRIPT_PATH,
        os.path.join(os.getcwd(), "setup-i2p-emulator.sh"),
        os.path.join(local_dir, "setup-i2p-emulator.sh"),
        os.path.join(os.getcwd(), "script.sh"),
        os.path.join(local_dir, "script.sh"),
    ]
    seen = set()
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        if os.path.exists(path):
            return path
    return DEPLOY_SCRIPT_PATH


def resolve_local_path(filename):
    local_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.getcwd(), filename),
        os.path.join(local_dir, filename),
        os.path.join(HOME, "Desktop", "testing", filename),
        os.path.join(HOME, filename),
    ]
    seen = set()
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        if os.path.exists(path):
            return path
    return os.path.join(local_dir, filename)


def python_executable():
    return sys.executable or "python3"


def builder_generated_paths():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return {
        "json": os.path.join(base_dir, "topology.generated.json"),
        "routers_tsv": os.path.join(base_dir, "routers.generated.tsv"),
        "subnets_tsv": os.path.join(base_dir, "subnets.generated.tsv"),
    }


def now_iso_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def format_kv(key, value):
    return f"{str(key):<22}: {value}"


def configure_compact_text_view(view, min_height=120, max_height=None, wrap=True):
    if view is None:
        return view
    try:
        view.setMinimumHeight(int(min_height))
    except Exception:
        pass
    if max_height is not None:
        try:
            view.setMaximumHeight(int(max_height))
        except Exception:
            pass
    try:
        if wrap:
            mode = QPlainTextEdit.LineWrapMode.WidgetWidth if PYQT_VER == 6 else QPlainTextEdit.WidgetWidth
            view.setLineWrapMode(mode)
            policy = Qt.ScrollBarPolicy.ScrollBarAlwaysOff if PYQT_VER == 6 else Qt.ScrollBarAlwaysOff
            view.setHorizontalScrollBarPolicy(policy)
        else:
            mode = QPlainTextEdit.LineWrapMode.NoWrap if PYQT_VER == 6 else QPlainTextEdit.NoWrap
            view.setLineWrapMode(mode)
    except Exception:
        pass
    return view



def phase5b_normalize_router_name(value):
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.match(r"(?i)^router\s*(\d+)$", text)
    if match:
        return f"Router {match.group(1)}"
    match = re.match(r"(?i)^r\s*(\d+)$", text)
    if match:
        return f"Router {match.group(1)}"
    if text.isdigit():
        return f"Router {text}"
    return text


def phase5b_router_numeric_id(router_name):
    text = str(router_name or "").strip().lower()
    match = re.match(r"^router\s*(\d+)$", text)
    if match:
        return int(match.group(1))
    match = re.match(r"^r\s*(\d+)$", text)
    if match:
        return int(match.group(1))
    return None


def phase5b_classify_role(hop_index, hop_count):
    try:
        hop_index = int(hop_index or 0)
        hop_count = int(hop_count or 0)
    except Exception:
        return "unknown"
    if hop_count <= 0 or hop_index <= 0:
        return "unknown"
    if hop_index == 1:
        return "entry"
    if hop_index == hop_count:
        return "endpoint"
    if 1 < hop_index < hop_count:
        return "middle"
    return "unknown"


def phase5b_infer_change_type(prev_chain, curr_chain, router_name):
    prev_chain = list(prev_chain or [])
    curr_chain = list(curr_chain or [])
    if not prev_chain:
        return "initial_observation"
    if prev_chain == curr_chain:
        return "stable"
    prev_idx = prev_chain.index(router_name) + 1 if router_name in prev_chain else None
    curr_idx = curr_chain.index(router_name) + 1 if router_name in curr_chain else None
    if prev_idx != curr_idx:
        return "hop_position_changed"
    if len(prev_chain) != len(curr_chain):
        return "path_length_changed"
    if prev_chain and curr_chain and prev_chain[0] != curr_chain[0]:
        return "entry_hop_changed"
    if prev_chain and curr_chain and prev_chain[-1] != curr_chain[-1]:
        return "endpoint_hop_changed"
    if prev_chain != curr_chain:
        return "middle_hop_changed"
    return "full_path_changed"


def phase5b_parse_hop_chain(value):
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value or "").split(",")
    out = []
    for item in items:
        norm = phase5b_normalize_router_name(item)
        if norm:
            out.append(norm)
    return out


def phase5b_build_raw_capture_record(
    *,
    run_id,
    scenario_bucket,
    scenario_label,
    tunnel_id,
    tunnel_direction,
    tunnel_kind,
    hop_chain,
    source_mode="operator-entered-ground-truth",
    phase_stage="runtime",
    phase_trigger_reason="manual_gui_capture",
    previous_chain=None,
    metadata=None,
    ts_utc=None,
):
    ts_utc = str(ts_utc or now_iso_utc())
    clean_chain = phase5b_parse_hop_chain(hop_chain)
    previous_chain = phase5b_parse_hop_chain(previous_chain or [])
    hop_count = len(clean_chain)
    per_router = []
    for idx, router_name in enumerate(clean_chain, start=1):
        neighbors = []
        if idx > 1:
            neighbors.append(clean_chain[idx - 2])
        if idx < hop_count:
            neighbors.append(clean_chain[idx])
        per_router.append({
            "ts_utc": ts_utc,
            "run_id": str(run_id or ""),
            "scenario_bucket": str(scenario_bucket or "other"),
            "scenario_label": str(scenario_label or "unknown"),
            "phase_stage": str(phase_stage or "runtime"),
            "phase_trigger_reason": str(phase_trigger_reason or "manual_gui_capture"),
            "source_mode": str(source_mode or "operator-entered-ground-truth"),
            "truth_level": "ground-truth",
            "tunnel_id": str(tunnel_id or ""),
            "tunnel_direction": str(tunnel_direction or "unknown"),
            "tunnel_kind": str(tunnel_kind or "unknown"),
            "hop_count": hop_count,
            "hop_chain": clean_chain,
            "router_id": phase5b_router_numeric_id(router_name),
            "router_name": router_name,
            "role": phase5b_classify_role(idx, hop_count),
            "hop_index": idx,
            "neighbor_routers": neighbors,
            "previous_hop_chain": previous_chain,
            "changed_from_previous": bool(previous_chain) and previous_chain != clean_chain,
            "change_type": phase5b_infer_change_type(previous_chain, clean_chain, router_name),
            "metadata": dict(metadata or {}),
        })
    return {
        "ts_utc": ts_utc,
        "run_id": str(run_id or ""),
        "scenario_bucket": str(scenario_bucket or "other"),
        "scenario_label": str(scenario_label or "unknown"),
        "phase_stage": str(phase_stage or "runtime"),
        "phase_trigger_reason": str(phase_trigger_reason or "manual_gui_capture"),
        "source_mode": str(source_mode or "operator-entered-ground-truth"),
        "truth_level": "ground-truth",
        "tunnel_id": str(tunnel_id or ""),
        "tunnel_direction": str(tunnel_direction or "unknown"),
        "tunnel_kind": str(tunnel_kind or "unknown"),
        "hop_count": hop_count,
        "hop_chain": clean_chain,
        "previous_hop_chain": previous_chain,
        "changed_from_previous": bool(previous_chain) and previous_chain != clean_chain,
        "metadata": dict(metadata or {}),
        "per_router_events": per_router,
    }




PHASE5C_CHAIN_KEYS = (
    "exact_hop_chain",
    "hop_chain",
    "full_hop_chain",
    "hop_chain_names",
    "route_chain",
    "exact_route",
    "selected_routers",
    "selected_route",
    "router_chain",
)

def phase5c_extract_candidate_chains(value, depth=0):
    if depth > 4:
        return []
    chains = []
    if isinstance(value, dict):
        for key in PHASE5C_CHAIN_KEYS:
            if key in value:
                chains.extend(phase5c_extract_candidate_chains(value.get(key), depth + 1))
    elif isinstance(value, (list, tuple)):
        names = []
        for item in value:
            if isinstance(item, dict):
                raw_name = item.get("router_name") or item.get("name") or item.get("router_id") or item.get("id")
                norm = phase5b_normalize_router_name(raw_name)
            else:
                norm = phase5b_normalize_router_name(item)
            if norm:
                names.append(norm)
        if len(names) >= 2:
            chains.append(names)
    elif isinstance(value, str):
        parsed = phase5b_parse_hop_chain(value)
        if len(parsed) >= 2:
            chains.append(parsed)
    deduped = []
    seen = set()
    for chain in chains:
        key = tuple(chain)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chain)
    return deduped


def phase5c_chain_signature(chain):
    chain = phase5b_parse_hop_chain(chain)
    return " > ".join(chain)

PHASE5C_AUTHORITATIVE_CHAIN_FILE_CANDIDATES = (
    os.path.join(HOP_TRUTH_ROOT_DIR, "events", "exact-hop-truth.jsonl"),
    os.path.join(HOP_TRUTH_ROOT_DIR, "events", "exact-hop-truth.json"),
    os.path.join(HOP_TRUTH_ROOT_DIR, "exact-hop-truth.jsonl"),
    os.path.join(HOP_TRUTH_ROOT_DIR, "exact-hop-truth.json"),
)

def phase5c_truth_event_candidate_files():
    out = []
    seen = set()
    for path in PHASE5C_AUTHORITATIVE_CHAIN_FILE_CANDIDATES:
        if path and os.path.isfile(path) and path not in seen:
            seen.add(path)
            out.append(path)
    return out

def phase5c_truth_event_rows():
    rows = []
    for path in phase5c_truth_event_candidate_files():
        lower = str(path).lower()
        payload = None
        if lower.endswith(".jsonl"):
            payload = read_jsonl_records(path, limit=20000)
        else:
            payload = read_json_file(path, default=[]) or []
            if isinstance(payload, dict):
                payload = payload.get("events") or payload.get("rows") or payload.get("routers") or []
        if not isinstance(payload, list):
            continue
        for item in payload:
            if isinstance(item, dict):
                row = dict(item)
                row["_source_file"] = path
                rows.append(row)
    return rows

def phase5c_authoritative_chain_index():
    rows = phase5c_truth_event_rows()
    normalized = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        chain = []
        for key in ("full_hop_chain", "hop_chain_names", "exact_hop_chain", "hop_chain", "full_hop_chain_names"):
            value = raw.get(key)
            if value:
                chain = phase5b_parse_hop_chain(value)
                if len(chain) >= 2:
                    break
        if len(chain) < 2:
            continue
        rid = str(raw.get("router_id") or phase5b_router_numeric_id(raw.get("router_name")) or "").strip()
        rname = phase5b_normalize_router_name(raw.get("router_name") or (f"Router {rid}" if rid else ""))
        ts_value = str(raw.get("ts_utc") or raw.get("ts_local") or raw.get("timestamp") or "")
        normalized.append({
            "router_id": rid,
            "router_name": rname,
            "hop_chain_names": chain,
            "hop_chain_ids": [str(x) for x in (raw.get("full_hop_chain_ids") or raw.get("hop_chain_ids") or []) if str(x).strip()],
            "tunnel_direction": str(raw.get("tunnel_direction") or raw.get("direction") or "unknown").strip() or "unknown",
            "tunnel_kind": str(raw.get("tunnel_kind") or raw.get("kind") or raw.get("tunnel_type") or "unknown").strip() or "unknown",
            "source_mode": str(raw.get("source_mode") or "authoritative-cache").strip() or "authoritative-cache",
            "path_signature": str(raw.get("path_signature") or phase5c_chain_signature(chain)).strip(),
            "ts_utc": ts_value,
            "run_id": str(raw.get("run_id") or "").strip(),
            "source_file": raw.get("_source_file"),
        })
    normalized.sort(key=lambda item: (str(item.get("ts_utc") or ""), str(item.get("run_id") or ""), str(item.get("path_signature") or "")))
    by_router_id = {}
    by_router_name = {}
    for item in normalized:
        rid = str(item.get("router_id") or "").strip()
        if rid:
            by_router_id[rid] = dict(item)
        rname = phase5b_normalize_router_name(item.get("router_name"))
        if rname:
            by_router_name[rname.lower()] = dict(item)
    return {
        "generated_at_utc": now_iso_utc(),
        "row_count": len(rows),
        "normalized_count": len(normalized),
        "by_router_id": by_router_id,
        "by_router_name": by_router_name,
    }

def phase5c_lookup_authoritative_chain(router, authoritative_chain_index=None):
    idx = authoritative_chain_index or {}
    by_router_id = dict(idx.get("by_router_id") or {})
    by_router_name = dict(idx.get("by_router_name") or {})
    rid = str((router or {}).get("id") or (router or {}).get("router_id") or "").strip()
    rname = phase5b_normalize_router_name((router or {}).get("name") or (router or {}).get("router_name") or (f"Router {rid}" if rid else ""))
    hit = None
    if rid and rid in by_router_id:
        hit = dict(by_router_id.get(rid) or {})
    elif rname and rname.lower() in by_router_name:
        hit = dict(by_router_name.get(rname.lower()) or {})
    return hit or {}

def filesystem_safe_name(value, fallback="session"):
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    return text or fallback


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def append_jsonl(path, record):
    ensure_dir(os.path.dirname(path))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")


def write_json_atomic(path, payload):
    ensure_dir(os.path.dirname(path))
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json_file(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def read_jsonl_records(path, limit=None):
    records = []
    if not path or not os.path.exists(path):
        return records
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    if isinstance(limit, int) and limit > 0 and len(records) > limit:
        return records[-limit:]
    return records


def list_recent_run_dirs(root_dir, require_files=None, limit=8):
    require_files = list(require_files or [])
    items = []
    if not root_dir or not os.path.isdir(root_dir):
        return items
    try:
        for name in os.listdir(root_dir):
            path = os.path.join(root_dir, name)
            if not os.path.isdir(path):
                continue
            if any(not os.path.exists(os.path.join(path, req)) for req in require_files):
                continue
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = 0.0
            items.append((mtime, path))
    except Exception:
        return []
    items.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in items[:max(1, int(limit or 1))]]


def format_optional_seconds(value):
    try:
        number = float(value)
    except Exception:
        return "unknown"
    return format_seconds_brief(number)


def format_seconds_brief(value):
    try:
        seconds = float(value)
    except Exception:
        return "0.0s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rem = divmod(seconds, 60.0)
    if minutes < 60:
        return f"{int(minutes)}m {rem:.1f}s"
    hours, rem = divmod(minutes, 60.0)
    return f"{int(hours)}h {int(rem)}m"


def create_churn_run_manifest(testnet_base, config):
    ensure_dir(SCENARIO_ROOT_DIR)
    timestamp_local = now_display().replace(":", "-").replace(" ", "_")
    timestamp_utc = now_iso_utc()
    base_name = filesystem_safe_name(os.path.basename(testnet_base) or "testnet")
    scenario_tag = filesystem_safe_name(str(config.get("scenario_type", "scenario") or "scenario"))
    run_id = f"{base_name}-{scenario_tag}-{timestamp_local}"
    run_dir = os.path.join(SCENARIO_ROOT_DIR, run_id)
    ensure_dir(run_dir)
    manifest = {
        "run_id": run_id,
        "run_dir": run_dir,
        "testnet_base": testnet_base,
        "started_at_local": now_display(),
        "started_at_utc": timestamp_utc,
        "config": config,
        "files": {
            "run": os.path.join(run_dir, "run.json"),
            "state": os.path.join(run_dir, "state.json"),
            "events": os.path.join(run_dir, "events.jsonl"),
        },
    }
    write_json_atomic(manifest["files"]["run"], manifest)
    write_json_atomic(manifest["files"]["state"], {
        "run_id": run_id,
        "run_dir": run_dir,
        "status": "prepared",
        "started_at_local": manifest["started_at_local"],
        "started_at_utc": manifest["started_at_utc"],
        "completed_cycles": 0,
        "requested_cycles": safe_int(config.get("max_cycles", 0), 0),
        "last_message": "Scenario prepared.",
    })
    return manifest


def create_measurement_run_manifest(testnet_base, config):
    ensure_dir(MEASUREMENT_ROOT_DIR)
    timestamp_local = now_display().replace(":", "-").replace(" ", "_")
    timestamp_utc = now_iso_utc()
    base_name = filesystem_safe_name(os.path.basename(testnet_base) or "testnet")
    run_id = f"{base_name}-measurement-{timestamp_local}"
    run_dir = os.path.join(MEASUREMENT_ROOT_DIR, run_id)
    ensure_dir(run_dir)
    manifest = {
        "run_id": run_id,
        "run_dir": run_dir,
        "testnet_base": testnet_base,
        "started_at_local": now_display(),
        "started_at_utc": timestamp_utc,
        "config": config,
        "files": {
            "run": os.path.join(run_dir, "run.json"),
            "state": os.path.join(run_dir, "state.json"),
            "probes": os.path.join(run_dir, "probes.jsonl"),
            "summary": os.path.join(run_dir, "summary.json"),
            "trace": os.path.join(run_dir, "trace.jsonl"),
        },
    }
    write_json_atomic(manifest["files"]["run"], manifest)
    write_json_atomic(manifest["files"]["state"], {
        "run_id": run_id,
        "run_dir": run_dir,
        "status": "prepared",
        "started_at_local": manifest["started_at_local"],
        "started_at_utc": manifest["started_at_utc"],
        "completed_probes": 0,
        "requested_probes": 0,
        "last_message": "Measurement run prepared.",
    })
    return manifest


def create_campaign_run_manifest(testnet_base, config):
    ensure_dir(CAMPAIGN_ROOT_DIR)
    timestamp_local = now_display().replace(":", "-").replace(" ", "_")
    timestamp_utc = now_iso_utc()
    base_name = filesystem_safe_name(os.path.basename(testnet_base) or "testnet")
    run_id = f"{base_name}-campaign-{timestamp_local}"
    run_dir = os.path.join(CAMPAIGN_ROOT_DIR, run_id)
    ensure_dir(run_dir)
    manifest = {
        "run_id": run_id,
        "run_dir": run_dir,
        "testnet_base": testnet_base,
        "started_at_local": now_display(),
        "started_at_utc": timestamp_utc,
        "config": config,
        "files": {
            "run": os.path.join(run_dir, "run.json"),
            "state": os.path.join(run_dir, "state.json"),
            "events": os.path.join(run_dir, "events.jsonl"),
            "summary": os.path.join(run_dir, "summary.json"),
            "trace": os.path.join(run_dir, "trace.jsonl"),
        },
    }
    write_json_atomic(manifest["files"]["run"], manifest)
    write_json_atomic(manifest["files"]["state"], {
        "run_id": run_id,
        "run_dir": run_dir,
        "status": "prepared",
        "started_at_local": manifest["started_at_local"],
        "started_at_utc": manifest["started_at_utc"],
        "baseline_run_id": None,
        "final_run_id": None,
        "interim_measurements": 0,
        "cycle_trigger_measurements": 0,
        "periodic_measurements": 0,
        "last_message": "Campaign prepared.",
    })
    return manifest


class TelemetrySessionManager:
    ACTIVE_STATUSES = {"active"}
    WARM_STATUSES = {"starting"}
    DOWN_STATUSES = {"stopping", "stopped", "failed"}
    UP_STATUSES = ACTIVE_STATUSES | WARM_STATUSES

    def __init__(self, root_dir=TELEMETRY_ROOT_DIR, poll_seconds=POLL_SECONDS):
        self.root_dir = root_dir
        self.poll_seconds = float(poll_seconds)
        self.reset_runtime_state(clear_recent=True)

    def reset_runtime_state(self, clear_recent=False):
        self.session_id = None
        self.session_dir = None
        self.session_base = None
        self.session_started_local = None
        self.session_started_utc = None
        self.sample_count = 0
        self.router_sample_count = 0
        self.event_count = 0
        self.last_snapshot = None
        self.last_router_state = {}
        self.last_fleet_state = None
        self.router_lifecycle = {}
        if clear_recent:
            self.recent_events = []
        else:
            self.recent_events = getattr(self, "recent_events", [])

    def has_active_session(self):
        return bool(self.session_dir and self.session_id)

    def ensure_session(self, snapshot):
        base = snapshot.get("base")
        if not snapshot.get("base_available") or not base:
            return False

        if self.session_base == base and self.has_active_session():
            return True

        timestamp_local = now_display().replace(":", "-").replace(" ", "_")
        timestamp_utc = now_iso_utc()
        base_name = filesystem_safe_name(os.path.basename(base) or "testnet")
        session_id = f"{base_name}-{timestamp_local}"
        session_dir = os.path.join(self.root_dir, session_id)
        ensure_dir(session_dir)

        self.reset_runtime_state(clear_recent=True)
        self.session_id = session_id
        self.session_dir = session_dir
        self.session_base = base
        self.session_started_local = now_display()
        self.session_started_utc = timestamp_utc

        manifest = {
            "session_id": self.session_id,
            "session_dir": self.session_dir,
            "testnet_base": self.session_base,
            "started_at_local": self.session_started_local,
            "started_at_utc": self.session_started_utc,
            "poll_seconds": self.poll_seconds,
            "app": APP_NAME,
            "files": {
                "session": os.path.join(self.session_dir, "session.json"),
                "state": os.path.join(self.session_dir, "state.json"),
                "fleet_snapshots": os.path.join(self.session_dir, "fleet_snapshots.jsonl"),
                "router_samples": os.path.join(self.session_dir, "router_samples.jsonl"),
                "router_events": os.path.join(self.session_dir, "router_events.jsonl"),
            },
        }
        write_json_atomic(manifest["files"]["session"], manifest)
        write_json_atomic(TELEMETRY_STATE_FILE, {
            "session_id": self.session_id,
            "session_dir": self.session_dir,
            "testnet_base": self.session_base,
            "started_at_local": self.session_started_local,
            "started_at_utc": self.session_started_utc,
        })
        return True

    def _lifecycle(self, router_id):
        rid = str(router_id)
        if rid not in self.router_lifecycle:
            self.router_lifecycle[rid] = {
                "current_churn_kind": None,
                "last_down_ts": None,
                "down_from_status": None,
                "last_derived_type": None,
                "last_derived_old": None,
                "last_derived_new": None,
                "pending_action": None,
            }
        return self.router_lifecycle[rid]

    def note_router_action_intent(self, action, router_id, source="gui"):
        action = str(action or "").strip().lower()
        if action not in {"start", "stop", "restart"}:
            return
        life = self._lifecycle(router_id)
        life["pending_action"] = {
            "action": action,
            "ts": time.time(),
            "source": str(source or "gui"),
        }

    def _get_pending_action(self, router_id, now_epoch=None):
        life = self._lifecycle(router_id)
        pending = life.get("pending_action")
        if not pending:
            return None
        if now_epoch is None:
            now_epoch = time.time()
        ts = float(pending.get("ts") or 0.0)
        if now_epoch - ts > TELEMETRY_ACTION_INTENT_WINDOW_SECONDS:
            life["pending_action"] = None
            return None
        return pending

    def _clear_pending_action(self, router_id):
        self._lifecycle(router_id)["pending_action"] = None

    def _register_derived_event(self, event_type, router_record, old_value, new_value, source, extra=None):
        life = self._lifecycle(router_record.get("router_id"))
        dedupe_key = (event_type, old_value, new_value)
        if (life.get("last_derived_type"), life.get("last_derived_old"), life.get("last_derived_new")) == dedupe_key:
            return False
        payload_extra = {"source": source, "derived": True}
        if extra:
            payload_extra.update(extra)
        self.register_event(self.make_event_record(
            event_type,
            router_record=router_record,
            old_value=old_value,
            new_value=new_value,
            extra=payload_extra,
        ))
        life["last_derived_type"], life["last_derived_old"], life["last_derived_new"] = dedupe_key
        return True

    def compact_router_record(self, router):
        parsed = router.get("parsed", {}) or {}
        metrics = router.get("metrics", {}) or {}

        peer_count = max(0, safe_int(metrics.get("peer_count", 0)))
        peer_active = max(0, min(peer_count, safe_int(metrics.get("peer_active", 0))))
        peer_known = max(peer_active, safe_int(metrics.get("peer_known", 0)))

        return {
            "router_id": str(router.get("id", "")),
            "router_name": router.get("name", ""),
            "status": router.get("status", "unknown"),
            "floodfill": str(router.get("floodfill", "")).lower() == "true",
            "main_pid": str(metrics.get("main_pid", "0")),
            "peer_count": peer_count,
            "peer_active": peer_active,
            "peer_known": peer_known,
            "tunnel_count": safe_int(metrics.get("tunnel_count", 0)),
            "tunnel_exploratory": safe_int(metrics.get("tunnel_exploratory", 0)),
            "tunnel_client": safe_int(metrics.get("tunnel_client", 0)),
            "tunnel_participating": safe_int(metrics.get("tunnel_participating", 0)),
            "share_ratio": str(metrics.get("share_ratio", "0")),
            "reachability": str(metrics.get("reachability", "unknown")),
            "tunnel_acceptance": str(metrics.get("tunnel_acceptance", "unknown")),
            "uptime": str(metrics.get("uptime", "unknown")),
            "country": parsed.get("country", ""),
            "city": parsed.get("city", ""),
            "subnet_label": parsed.get("subnet_label", ""),
            "namespace": parsed.get("namespace", ""),
            "router_ip": parsed.get("router_ip", router.get("router_ip", "")),
            "console_url": router.get("console_url", ""),
        }

    def make_event_record(self, event_type, router_record=None, old_value=None, new_value=None, extra=None):
        event = {
            "event_id": f"{self.session_id or 'no-session'}-{self.event_count + 1}",
            "ts_local": now_display(),
            "ts_utc": now_iso_utc(),
            "session_id": self.session_id,
            "testnet_base": self.session_base,
            "event_type": event_type,
            "old_value": old_value,
            "new_value": new_value,
        }
        if router_record:
            event.update(router_record)
        if extra:
            event.update(extra)
        return event

    def register_event(self, event):
        self.event_count += 1
        event["event_seq"] = self.event_count
        self.recent_events.append(event)
        if len(self.recent_events) > TELEMETRY_RECENT_EVENT_LIMIT:
            self.recent_events = self.recent_events[-TELEMETRY_RECENT_EVENT_LIMIT:]
        if self.has_active_session():
            append_jsonl(os.path.join(self.session_dir, "router_events.jsonl"), event)

    def _maybe_register_churn_markers(self, prev, record, source, now_epoch):
        prev_status = str((prev or {}).get("status", "unknown") or "unknown")
        curr_status = str(record.get("status", "unknown") or "unknown")
        if prev_status == curr_status:
            return

        rid = record.get("router_id")
        life = self._lifecycle(rid)
        pending = self._get_pending_action(rid, now_epoch=now_epoch)
        pending_action = str((pending or {}).get("action", "")).strip().lower()
        pending_source = str((pending or {}).get("source", "")).strip()

        if prev_status == "active" and curr_status == "starting":
            extra = {"phase": "begin"}
            if pending_action == "restart":
                extra["cause"] = "restart"
            if pending_source:
                extra["action_source"] = pending_source
            self._register_derived_event(
                "restart_detected",
                record,
                prev_status,
                curr_status,
                source,
                extra=extra,
            )
            life["current_churn_kind"] = "restart"
            return

        if prev_status in self.UP_STATUSES and curr_status in self.DOWN_STATUSES:
            life["last_down_ts"] = now_epoch
            life["down_from_status"] = prev_status
            cause = None
            if pending_action == "restart":
                cause = "restart"
                life["current_churn_kind"] = "restart"
            else:
                cause = "stop"
                if life.get("current_churn_kind") is None:
                    life["current_churn_kind"] = "stop"
            extra = {"phase": "begin" if curr_status == "stopping" else "down", "cause": cause}
            if pending_source:
                extra["action_source"] = pending_source
            self._register_derived_event(
                "stop_detected",
                record,
                prev_status,
                curr_status,
                source,
                extra=extra,
            )
            return

        if prev_status in self.DOWN_STATUSES and curr_status in self.UP_STATUSES:
            downtime = None
            if life.get("last_down_ts") is not None:
                downtime = max(0.0, now_epoch - float(life["last_down_ts"]))

            cause = None
            if pending_action == "restart" or life.get("current_churn_kind") == "restart":
                cause = "restart"
            elif pending_action == "start":
                cause = "manual_start"
            elif life.get("current_churn_kind") == "stop":
                cause = "manual_start"
            else:
                cause = "recovery"

            extra = {
                "downtime_seconds": round(downtime, 1) if downtime is not None else None,
                "cause": cause,
            }
            if pending_source:
                extra["action_source"] = pending_source
            self._register_derived_event(
                "rejoin_detected",
                record,
                prev_status,
                curr_status,
                source,
                extra=extra,
            )
            life["current_churn_kind"] = None if curr_status == "active" else "rejoin"

            if curr_status == "active":
                life["last_down_ts"] = None
                life["down_from_status"] = None
                self._clear_pending_action(rid)
            return

        if prev_status == "starting" and curr_status == "active":
            life["current_churn_kind"] = None
            life["last_down_ts"] = None
            life["down_from_status"] = None
            if pending_action in {"start", "restart"}:
                self._clear_pending_action(rid)

    def detect_events(self, snapshot, source):
        current_router_ids = set()
        new_state = {}
        now_epoch = time.time()

        for router in snapshot.get("routers", []):
            record = self.compact_router_record(router)
            rid = record["router_id"]
            current_router_ids.add(rid)
            new_state[rid] = record
            prev = self.last_router_state.get(rid)
            self._lifecycle(rid)

            if prev is None:
                self.register_event(self.make_event_record(
                    "router_first_seen",
                    router_record=record,
                    new_value=record["status"],
                    extra={"source": source},
                ))
                continue

            if prev.get("status") != record["status"]:
                self.register_event(self.make_event_record(
                    "status_change",
                    router_record=record,
                    old_value=prev.get("status"),
                    new_value=record["status"],
                    extra={"source": source},
                ))

            prev_pid = str(prev.get("main_pid", "0"))
            curr_pid = str(record.get("main_pid", "0"))
            if prev_pid != curr_pid and prev_pid not in {"", "0"} and curr_pid not in {"", "0"}:
                self.register_event(self.make_event_record(
                    "main_pid_change",
                    router_record=record,
                    old_value=prev_pid,
                    new_value=curr_pid,
                    extra={"source": source},
                ))

            if prev.get("reachability") != record["reachability"]:
                self.register_event(self.make_event_record(
                    "reachability_change",
                    router_record=record,
                    old_value=prev.get("reachability"),
                    new_value=record["reachability"],
                    extra={"source": source},
                ))

            if prev.get("tunnel_acceptance") != record["tunnel_acceptance"]:
                self.register_event(self.make_event_record(
                    "tunnel_acceptance_change",
                    router_record=record,
                    old_value=prev.get("tunnel_acceptance"),
                    new_value=record["tunnel_acceptance"],
                    extra={"source": source},
                ))

            self._maybe_register_churn_markers(prev, record, source, now_epoch)

        missing_router_ids = sorted(set(self.last_router_state.keys()) - current_router_ids, key=lambda x: safe_int(x, 999999))
        for rid in missing_router_ids:
            prev = self.last_router_state.get(rid, {})
            self.register_event(self.make_event_record(
                "router_missing_from_snapshot",
                router_record=prev,
                old_value=prev.get("status"),
                new_value="missing",
                extra={"source": source},
            ))
            life = self._lifecycle(rid)
            life["current_churn_kind"] = "missing"

        fleet = {
            "total": safe_int(snapshot.get("total", 0)),
            "active": safe_int(snapshot.get("active", 0)),
            "stopped": safe_int(snapshot.get("stopped", 0)),
            "failed": safe_int(snapshot.get("failed", 0)),
            "floodfill_count": safe_int(snapshot.get("floodfill_count", 0)),
        }
        if self.last_fleet_state and fleet != self.last_fleet_state:
            self.register_event(self.make_event_record(
                "fleet_state_change",
                old_value=self.last_fleet_state,
                new_value=fleet,
                extra={"source": source},
            ))

        self.last_router_state = new_state
        self.last_fleet_state = fleet

    def write_state_file(self):
        if not self.has_active_session():
            return
        payload = {
            "session_id": self.session_id,
            "session_dir": self.session_dir,
            "testnet_base": self.session_base,
            "started_at_local": self.session_started_local,
            "started_at_utc": self.session_started_utc,
            "last_snapshot": self.last_snapshot,
            "sample_count": self.sample_count,
            "router_sample_count": self.router_sample_count,
            "event_count": self.event_count,
            "poll_seconds": self.poll_seconds,
            "recent_events": self.recent_events[-10:],
        }
        write_json_atomic(os.path.join(self.session_dir, "state.json"), payload)
        write_json_atomic(TELEMETRY_STATE_FILE, payload)

    def process_snapshot(self, snapshot):
        source = str(snapshot.get("_snapshot_source", "monitor") or "monitor")
        if not self.ensure_session(snapshot):
            self.last_snapshot = {
                "source": source,
                "generated_at": snapshot.get("generated_at"),
                "base": snapshot.get("base"),
                "total": snapshot.get("total", 0),
                "active": snapshot.get("active", 0),
                "stopped": snapshot.get("stopped", 0),
                "failed": snapshot.get("failed", 0),
            }
            return

        sample_meta = {
            "ts_local": now_display(),
            "ts_utc": now_iso_utc(),
            "session_id": self.session_id,
            "testnet_base": self.session_base,
            "source": source,
        }
        fleet_record = {
            **sample_meta,
            "generated_at": snapshot.get("generated_at"),
            "total": safe_int(snapshot.get("total", 0)),
            "active": safe_int(snapshot.get("active", 0)),
            "stopped": safe_int(snapshot.get("stopped", 0)),
            "failed": safe_int(snapshot.get("failed", 0)),
            "floodfill_count": safe_int(snapshot.get("floodfill_count", 0)),
        }
        append_jsonl(os.path.join(self.session_dir, "fleet_snapshots.jsonl"), fleet_record)
        self.sample_count += 1

        for router in snapshot.get("routers", []):
            record = self.compact_router_record(router)
            append_jsonl(os.path.join(self.session_dir, "router_samples.jsonl"), {
                **sample_meta,
                **record,
            })
            self.router_sample_count += 1

        self.detect_events(snapshot, source)
        self.last_snapshot = fleet_record
        self.write_state_file()

    def _event_label(self, event):
        labels = []
        if event.get("derived"):
            labels.append("derived")
        phase = str(event.get("phase", "")).strip()
        if phase:
            labels.append(f"phase={phase}")
        cause = str(event.get("cause", "")).strip()
        if cause:
            labels.append(f"cause={cause}")
        action_source = str(event.get("action_source", "")).strip()
        if action_source:
            labels.append(f"source={action_source}")
        downtime = event.get("downtime_seconds")
        if isinstance(downtime, (int, float)):
            labels.append(f"downtime={downtime:.1f}s")
        return f" [{' | '.join(labels)}]" if labels else ""

    def _summarize_router_events(self, router_focus, events):
        derived_events = [e for e in events if e.get("derived") and str(e.get("router_id", "")) == router_focus]
        counts = {
            "stop_detected": 0,
            "rejoin_detected": 0,
            "restart_detected": 0,
            "rejoin_from_restart": 0,
            "rejoin_from_manual_start": 0,
            "rejoin_from_recovery": 0,
        }
        for event in derived_events:
            et = event.get("event_type")
            if et in counts:
                counts[et] += 1
            if et == "rejoin_detected":
                cause = str(event.get("cause", "")).strip()
                if cause == "restart":
                    counts["rejoin_from_restart"] += 1
                elif cause == "manual_start":
                    counts["rejoin_from_manual_start"] += 1
                else:
                    counts["rejoin_from_recovery"] += 1
        last_marker = derived_events[-1] if derived_events else None
        return counts, last_marker, derived_events[-8:]

    def build_view_text(self, selected_router_id=None):
        lines = [
            "Telemetry",
            "=" * 72,
            f"Root directory        : {self.root_dir}",
        ]

        if not self.has_active_session():
            lines.extend([
                "Session              : not started yet",
                "Status               : waiting for a live testnet base",
            ])
            return "\n".join(lines)

        lines.extend([
            f"Session ID           : {self.session_id}",
            f"Session directory    : {self.session_dir}",
            f"Testnet base         : {self.session_base}",
            f"Started              : {self.session_started_local}",
            f"Poll interval        : {self.poll_seconds:.1f}s",
            f"Fleet snapshots      : {self.sample_count}",
            f"Router samples       : {self.router_sample_count}",
            f"Events               : {self.event_count}",
            "",
            "Files",
            "-----",
            f"session.json         : {os.path.join(self.session_dir, 'session.json')}",
            f"state.json           : {os.path.join(self.session_dir, 'state.json')}",
            f"fleet_snapshots.jsonl: {os.path.join(self.session_dir, 'fleet_snapshots.jsonl')}",
            f"router_samples.jsonl : {os.path.join(self.session_dir, 'router_samples.jsonl')}",
            f"router_events.jsonl  : {os.path.join(self.session_dir, 'router_events.jsonl')}",
        ])

        if self.last_snapshot:
            lines.extend([
                "",
                "Latest fleet snapshot",
                "---------------------",
                f"Generated            : {self.last_snapshot.get('generated_at', 'unknown')}",
                f"Source               : {self.last_snapshot.get('source', 'unknown')}",
                f"Active / Stopped     : {self.last_snapshot.get('active', 0)} / {self.last_snapshot.get('stopped', 0)}",
                f"Failed               : {self.last_snapshot.get('failed', 0)}",
                f"Total routers        : {self.last_snapshot.get('total', 0)}",
            ])

        router_focus = str(selected_router_id or "").strip()
        events = self.recent_events
        if router_focus:
            counts, last_marker, recent_markers = self._summarize_router_events(router_focus, self.recent_events)
            lines.extend([
                "",
                f"Detected churn markers for Router {router_focus}",
                "-" * 72,
                f"restart_detected     : {counts['restart_detected']}",
                f"stop_detected        : {counts['stop_detected']}",
                f"rejoin_detected      : {counts['rejoin_detected']}",
                f"  ├─ from restart    : {counts['rejoin_from_restart']}",
                f"  ├─ from manual     : {counts['rejoin_from_manual_start']}",
                f"  └─ recovery/other  : {counts['rejoin_from_recovery']}",
            ])
            if last_marker:
                lines.append(
                    f"Last churn marker    : [{last_marker.get('ts_local', 'unknown')}] {last_marker.get('event_type', 'event')}"
                    f"{self._event_label(last_marker)} ({last_marker.get('old_value', '-')} -> {last_marker.get('new_value', '-')})"
                )
            else:
                lines.append("Last churn marker    : none recorded yet")

            lines.extend(["", "Recent churn markers", "-" * 72])
            if not recent_markers:
                lines.append("No churn markers recorded yet.")
            else:
                for event in reversed(recent_markers):
                    lines.append(
                        f"[{event.get('ts_local', 'unknown')}] Router {router_focus}  {event.get('event_type', 'event')}"
                        f"{self._event_label(event)}  ({event.get('old_value', '-')} -> {event.get('new_value', '-')})"
                    )
            events = [e for e in events if str(e.get("router_id", "")) == router_focus]

        events = events[-TELEMETRY_VIEW_EVENT_LIMIT:]
        lines.extend([
            "",
            f"Recent events{' for Router ' + router_focus if router_focus else ''}",
            "-" * 72,
        ])
        if not events:
            lines.append("No matching events recorded yet.")
        else:
            for event in reversed(events):
                rid = event.get("router_id")
                router_label = f"Router {rid}" if rid else "Fleet"
                lines.append(
                    f"[{event.get('ts_local', 'unknown')}] {router_label}  {event.get('event_type', 'event')}"
                    f"{self._event_label(event)}  ({event.get('old_value', '-') } -> {event.get('new_value', '-')})"
                )

        return "\n".join(lines)

def run_cmd(cmd, timeout=10):
    try:
        if isinstance(cmd, (list, tuple)):
            result = subprocess.run(list(cmd), shell=False, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1


def read_file_safe(path, max_lines=READ_FILE_MAX_LINES):
    if not path or not os.path.exists(path):
        return f"File not found: {path}"
    try:
        with open(path, "r", errors="ignore") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except Exception as e:
        return f"Error reading file: {e}"


def parse_key_values(path):
    data = {}
    if not path or not os.path.exists(path):
        return data
    try:
        with open(path, "r", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    except Exception:
        pass
    return data


def strip_html_tags(text):
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def extract_metric(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            return m.group(1).strip()
    return ""


def extract_table_block(html_text, table_id):
    if not html_text:
        return ""
    patterns = [
        rf'(?is)<table[^>]+id="{re.escape(table_id)}"[^>]*>(.*?)</table>',
        rf"(?is)<table[^>]+id='{re.escape(table_id)}'[^>]*>(.*?)</table>",
    ]
    for pattern in patterns:
        m = re.search(pattern, html_text)
        if m:
            return m.group(1)
    return ""


def extract_sidebar_metric(html_text, table_id, label):
    block = extract_table_block(html_text, table_id)
    if not block:
        return ""

    patterns = [
        rf'(?is)<tr[^>]*>.*?<b>\s*{re.escape(label)}\s*:?\s*</b>.*?<td[^>]*>\s*(.*?)\s*</td>',
        rf'(?is)<tr[^>]*>\s*<td[^>]*>\s*<b>\s*{re.escape(label)}\s*:?\s*</b>\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>',
        rf'(?is)\b{re.escape(label)}\b\s*:?\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>',
    ]

    for pattern in patterns:
        m = re.search(pattern, block)
        if m:
            value = strip_html_tags(m.group(1))
            if value:
                return value.strip()
    return ""


def extract_peer_active_value(active_text):
    if not active_text:
        return "0"
    m = re.search(r"(\d+)", active_text)
    return m.group(1) if m else "0"


def extract_reachability_from_html(html_text):
    if not html_text:
        return ""

    patterns = [
        r"(?is)>Network:\s*([^<]+)<",
        r'(?is)<p[^>]+id="upnpstatus"[^>]*>\s*<b>\s*Status:\s*([^<]+)\s*</b>',
        r"(?is)\bReachability\b[^A-Za-z0-9]{0,20}([A-Za-z][A-Za-z \-]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, html_text)
        if m:
            return strip_html_tags(m.group(1)).strip()
    return ""


def extract_tunnel_build_status(html_text):
    if not html_text:
        return ""

    patterns = [
        r'(?is)<span[^>]+class="tunnelBuildStatus"[^>]*>\s*(.*?)\s*</span>',
        r"(?is)(Accepting tunnels(?:\s*:\s*[^<]+)?|Rejecting tunnels(?:\s*:\s*[^<]+)?)",
    ]

    for pattern in patterns:
        m = re.search(pattern, html_text)
        if m:
            return strip_html_tags(m.group(1)).strip()
    return ""


def get_existing_testnet_bases():
    bases = []
    try:
        for path in glob.glob(os.path.join(HOME, "i2p-testnet-*")):
            if os.path.isdir(path):
                m = re.search(r"i2p-testnet-(\d+)$", path)
                sort_key = safe_int(m.group(1), 0) if m else 0
                bases.append((sort_key, path))
    except Exception:
        return []
    bases.sort(key=lambda x: (x[0], x[1]))
    return [p for _, p in bases]


def find_testnet_base():
    preferred = get_preferred_testnet_base()
    if preferred and os.path.isdir(preferred):
        return preferred
    bases = get_existing_testnet_bases()
    return bases[-1] if bases else None


def load_topology_map(base):
    mapping = {}
    if not base:
        return mapping
    topo_path = os.path.join(base, "topology-map.tsv")
    if not os.path.exists(topo_path):
        return mapping
    try:
        with open(topo_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                rid = str(row.get("router_id", "")).strip()
                if not rid:
                    continue
                mapping[rid] = {
                    "country": row.get("country", "").strip(),
                    "country_code": row.get("country_code", "").strip(),
                    "city": row.get("city", "").strip(),
                    "display_lat": row.get("display_lat", "").strip(),
                    "display_lon": row.get("display_lon", "").strip(),
                    "namespace": row.get("namespace", "").strip(),
                    "bridge": row.get("bridge", "").strip(),
                    "subnet_label": row.get("subnet_label", "").strip(),
                    "subnet": row.get("subnet", "").strip(),
                    "gateway": row.get("gateway", "").strip(),
                    "ip": row.get("ip", "").strip(),
                    "console_port": row.get("console_port", "").strip(),
                    "console_url": row.get("console_url", "").strip(),
                    "ntcp_port": row.get("ntcp_port", "").strip(),
                    "udp_port": row.get("udp_port", "").strip(),
                    "floodfill": row.get("floodfill", "").strip(),
                }
    except Exception:
        return {}
    return mapping


def parse_router_config(cfg_path):
    kv = parse_key_values(cfg_path)
    router_ip = kv.get("router.testnet.ip", kv.get("i2np.ntcp.host", "unknown"))
    console_host = kv.get("router.testnet.consoleHost", router_ip)
    console_url = kv.get("router.testnet.consoleURL", "")
    console_port = kv.get("routerconsole.port", "unknown")
    if not console_url and console_host not in ("", "unknown") and console_port != "unknown":
        console_url = f"http://{console_host}:{console_port}"
    return {
        "floodfill": kv.get("router.floodfillParticipant", "unknown"),
        "console_port": console_port,
        "network_id": kv.get("router.networkID", "unknown"),
        "console_bind_host": kv.get("routerconsole.host", "unknown"),
        "console_host": console_host,
        "console_url": console_url or "unknown",
        "namespace": kv.get("router.testnet.namespace", "unknown"),
        "bridge": kv.get("router.testnet.bridge", "unknown"),
        "subnet": kv.get("router.testnet.subnet", "unknown"),
        "gateway": kv.get("router.testnet.gateway", "unknown"),
        "router_ip": router_ip,
        "host_veth": kv.get("router.testnet.hostVeth", "unknown"),
        "ns_veth": kv.get("router.testnet.nsVeth", "unknown"),
        "ntcp_host": kv.get("i2np.ntcp.host", "unknown"),
        "ntcp_port": kv.get("i2np.ntcp.port", "unknown"),
        "udp_host": kv.get("i2np.udp.host", "unknown"),
        "udp_port": kv.get("i2np.udp.port", "unknown"),
        "bandwidth_in": kv.get("i2np.bandwidth.inboundKBytesPerSecond", "unknown"),
        "bandwidth_out": kv.get("i2np.bandwidth.outboundKBytesPerSecond", "unknown"),
        "participating_limit": kv.get("i2np.tunnel.participatingLimit", "unknown"),
        "expl_in_len": kv.get("router.exploratory.inboundLength", "unknown"),
        "expl_out_len": kv.get("router.exploratory.outboundLength", "unknown"),
        "router_dir_data": kv.get("i2p.dir.router", "unknown"),
        "router_dir_log": kv.get("i2p.dir.log", "unknown"),
        "country": kv.get("router.testnet.country", "unknown"),
        "country_code": kv.get("router.testnet.countryCode", "unknown"),
        "city": kv.get("router.testnet.city", "unknown"),
        "display_lat": kv.get("router.testnet.displayLat", "unknown"),
        "display_lon": kv.get("router.testnet.displayLon", "unknown"),
        "subnet_label": kv.get("router.testnet.subnetLabel", "unknown"),
        "measurement_eepsite_name": kv.get("router.testnet.measurementEepsiteName", "unknown"),
        "measurement_eepsite_role": kv.get("router.testnet.measurementEepsiteRole", "unknown"),
    }



def parse_i2ptunnel_config(cfg_path):
    kv = parse_key_values(cfg_path)
    listen_port = kv.get("tunnel.0.listenPort", "unknown")
    target_dest = _clean_i2p_host(kv.get("tunnel.0.targetDestination", ""))
    server_spoofed_host = _clean_i2p_host(kv.get("tunnel.1.spoofedHost", ""))
    client_target_url = _i2p_url_from_host(target_dest) or _i2p_url_from_host(server_spoofed_host)
    return {
        "client_tunnel_type": kv.get("tunnel.0.type", "unknown"),
        "client_tunnel_name": kv.get("tunnel.0.name", "unknown"),
        "client_proxy_port": listen_port,
        "client_target_destination": target_dest or "unknown",
        "client_target_url": client_target_url,
        "server_tunnel_type": kv.get("tunnel.1.type", "unknown"),
        "server_tunnel_name": kv.get("tunnel.1.name", "unknown"),
        "server_spoofed_host": server_spoofed_host or "unknown",
        "server_privkey_file": kv.get("tunnel.1.privKeyFile", "unknown"),
        "server_target_host": kv.get("tunnel.1.targetHost", "unknown"),
        "server_target_port": kv.get("tunnel.1.targetPort", "unknown"),
    }


def fetch_console_page(console_host, console_port, path="/", timeout=CONSOLE_FETCH_TIMEOUT):
    if not console_port or console_port == "unknown":
        return None
    host = (console_host or "").strip()
    if not host or host in {"unknown", "0.0.0.0"}:
        host = "127.0.0.1"
    url = f"http://{host}:{console_port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "I2P-GUI-Monitor/NativeQt"})
        with urllib.request.urlopen(req, timeout=float(timeout or CONSOLE_FETCH_TIMEOUT)) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="ignore")
    except Exception:
        return None


def tunnel_trace_signature_payload(text_map):
    text_map = dict(text_map or {})
    hosts = []
    for key in ("tunnels", "i2ptunnel", "peers"):
        page = text_map.get(key) or ""
        for host in B32_HOST_RE.findall(page):
            host_l = str(host).lower()
            if host_l not in hosts:
                hosts.append(host_l)

    def _kw_count(blob, pattern):
        return len(re.findall(pattern, blob or "", flags=re.IGNORECASE))

    tunnels_blob = text_map.get("tunnels") or ""
    peers_blob = text_map.get("peers") or ""
    i2pt_blob = text_map.get("i2ptunnel") or ""
    payload = {
        "b32_hosts": hosts[:8],
        "tunnels_bytes": len(tunnels_blob.encode("utf-8", errors="ignore")),
        "peers_bytes": len(peers_blob.encode("utf-8", errors="ignore")),
        "i2ptunnel_bytes": len(i2pt_blob.encode("utf-8", errors="ignore")),
        "inbound_mentions": _kw_count(tunnels_blob, r"\binbound\b"),
        "outbound_mentions": _kw_count(tunnels_blob, r"\boutbound\b"),
        "lease_mentions": _kw_count(tunnels_blob, r"\blease\b"),
        "exploratory_mentions": _kw_count(tunnels_blob, r"exploratory"),
        "client_mentions": _kw_count(tunnels_blob + "\n" + i2pt_blob, r"\bclient\b"),
        "participating_mentions": _kw_count(tunnels_blob, r"participating"),
        "peer_mentions": _kw_count(peers_blob, r"\bpeer\b"),
    }
    return payload


def build_tunnel_trace_snapshot(router, timeout=MEASUREMENT_FETCH_TIMEOUT_DEFAULT, previous_signature="", authoritative_chain_index=None):
    host = router.get("console_host")
    port = router.get("console_port")
    text_map = {
        "tunnels": fetch_console_page(host, port, "/tunnels", timeout=timeout) or "",
        "peers": fetch_console_page(host, port, "/peers", timeout=timeout) or "",
        "i2ptunnel": fetch_console_page(host, port, "/i2ptunnel/", timeout=timeout) or "",
    }
    payload = tunnel_trace_signature_payload(text_map)
    sig_src = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    signature = hashlib.sha1(sig_src.encode("utf-8", errors="ignore")).hexdigest()[:12] if sig_src else ""
    result = {
        "success": bool(text_map.get("tunnels")),
        "signature": signature,
        "previous_signature": previous_signature or "",
        "path_changed_since_previous": bool(previous_signature) and bool(signature) and previous_signature != signature,
        "sample_b32_hosts": payload.get("b32_hosts", []),
        "keyword_counts": {
            "inbound": payload.get("inbound_mentions", 0),
            "outbound": payload.get("outbound_mentions", 0),
            "lease": payload.get("lease_mentions", 0),
            "exploratory": payload.get("exploratory_mentions", 0),
            "client": payload.get("client_mentions", 0),
            "participating": payload.get("participating_mentions", 0),
            "peer": payload.get("peer_mentions", 0),
        },
        "page_bytes": {
            "tunnels": payload.get("tunnels_bytes", 0),
            "peers": payload.get("peers_bytes", 0),
            "i2ptunnel": payload.get("i2ptunnel_bytes", 0),
        },
        "trace_note": "Lifecycle trace captures visible tunnel and lease surface changes only. Exact hop order must come from an authoritative emulator-observed or log-derived source, not from cached truth.",
        "authoritative_chain_embedded": False,
    }
    return result

def load_recent_tunnel_trace_signatures(limit=TUNNEL_TRACE_RECENT_RUN_LIMIT):
    signatures = {}
    for run_dir in list_recent_run_dirs(MEASUREMENT_ROOT_DIR, require_files=["probes.jsonl"], limit=limit):
        probes = read_jsonl_records(os.path.join(run_dir, "probes.jsonl"))
        for rec in reversed(probes):
            rid = str(rec.get("router_id") or "")
            trace = rec.get("tunnel_trace") or {}
            sig = str(trace.get("signature") or "")
            if rid and sig and rid not in signatures:
                signatures[rid] = sig
    return signatures


def _classify_campaign_measurement_phase(stage, trigger_reason):
    stage_l = str(stage or "").strip().lower()
    reason_l = str(trigger_reason or "").strip().lower()
    if stage_l == "baseline" or reason_l == "pre_scenario":
        return "baseline"
    if stage_l == "post" or reason_l == "post_scenario":
        return "final"
    if stage_l.startswith("cycle-") or reason_l == "cycle_complete":
        return "cycle-trigger"
    if stage_l.startswith("periodic-") or reason_l == "periodic_timer":
        return "interim"
    if "scenario" in stage_l or "scenario" in reason_l:
        return "scenario-measurement"
    if stage_l or reason_l:
        return stage_l or reason_l
    return "standalone"


def load_recent_campaign_measurement_phase_index(limit_campaigns=80):
    index = {}
    for run_dir in list_recent_run_dirs(CAMPAIGN_ROOT_DIR, require_files=["summary.json"], limit=limit_campaigns):
        summary_payload = read_json_file(os.path.join(run_dir, "summary.json"), default={}) or {}
        summary = summary_payload.get("summary") or {}
        campaign_run_id = summary.get("campaign_run_id") or summary_payload.get("run_id") or os.path.basename(run_dir)
        experiment_label = summary.get("experiment_label") or summary_payload.get("experiment_label")
        scenario_run_id = summary.get("scenario_run_id")
        for item in list(summary.get("measurement_runs") or []):
            run_id = str(item.get("run_id") or "")
            if not run_id:
                continue
            stage = item.get("stage")
            trigger_reason = item.get("trigger_reason")
            phase_label = _classify_campaign_measurement_phase(stage, trigger_reason)
            info = {
                "campaign_run_id": campaign_run_id,
                "experiment_label": experiment_label,
                "scenario_run_id": scenario_run_id,
                "stage": stage,
                "trigger_reason": trigger_reason,
                "cycle_index": item.get("cycle_index"),
                "phase_label": phase_label,
                "is_baseline": phase_label == "baseline",
                "is_interim": phase_label == "interim",
                "is_post_churn": phase_label == "final",
                "is_final_probe": run_id == str(summary.get("final_run_id") or "") or phase_label == "final",
            }
            index[run_id] = info
    return index


B32_HOST_RE = re.compile(r"([a-z2-7]{52}\.b32\.i2p)", re.IGNORECASE)
PHASE5C_AUTHORITATIVE_CHAIN_TEXT_RE = re.compile(
    r"(?i)(?:exact_hop_chain|full_hop_chain|hop_chain_names|hop_chain|router_chain|path_chain|route_chain|routers|hops)\s*[:=]\s*(\[[^\]]+\]|[^;|]+)"
)
PHASE5C_LOG_TIMESTAMP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)
PHASE5C_TUNNEL_ID_RE = re.compile(r"(?i)(?:tunnel_id|tunnelId|tunnel)\s*[:=]\s*([A-Za-z0-9._:-]+)")
PHASE5C_DIRECTION_RE = re.compile(r"(?i)(?:tunnel_direction|direction)\s*[:=]\s*(inbound|outbound|exploratory|client)")
PHASE5C_KIND_RE = re.compile(r"(?i)(?:tunnel_kind|kind|tunnel_type|type)\s*[:=]\s*([A-Za-z0-9._-]+)")


def discover_internal_eepsite_target(routers):
    candidates = []
    for router in list(routers or []):
        if str(router.get("status", "")).lower() != "active":
            continue
        if str(router.get("server_tunnel_type", "")).lower() != "httpserver":
            continue
        candidates.append(router)

    page_paths = ("/i2ptunnel/", "/i2ptunnel/index.jsp", "/i2ptunnel", "/")
    for router in candidates:
        host = router.get("console_host")
        port = router.get("console_port")
        configured_spoofed = _clean_i2p_host(router.get("server_spoofed_host", ""))
        configured_name = _clean_i2p_host(router.get("measurement_eepsite_name", ""))

        for path in page_paths:
            page = fetch_console_page(host, port, path)
            if not page:
                continue
            matches = B32_HOST_RE.findall(page)
            if matches:
                selected = matches[0].lower()
                return {
                    "router_id": str(router.get("id", "")),
                    "router_name": router.get("name", f"Router {router.get('id', '?')}"),
                    "console_url": router.get("console_url", ""),
                    "spoofed_host": configured_spoofed or configured_name or "unknown",
                    "target_host": selected,
                    "target_url": f"http://{selected}/",
                    "source_path": path,
                }

        backup_b32 = _extract_b32_from_keybackup(router.get("testnet_base"), router.get("id"))
        if backup_b32:
            return {
                "router_id": str(router.get("id", "")),
                "router_name": router.get("name", f"Router {router.get('id', '?')}"),
                "console_url": router.get("console_url", ""),
                "spoofed_host": configured_spoofed or configured_name or "unknown",
                "target_host": backup_b32,
                "target_url": f"http://{backup_b32}/",
                "source_path": "i2ptunnel-keyBackup",
            }

        fallback_host = configured_spoofed or configured_name
        if fallback_host:
            return {
                "router_id": str(router.get("id", "")),
                "router_name": router.get("name", f"Router {router.get('id', '?')}"),
                "console_url": router.get("console_url", ""),
                "spoofed_host": fallback_host,
                "target_host": fallback_host,
                "target_url": f"http://{fallback_host}/",
                "source_path": "router_config",
            }
    return {}


def probe_console_endpoint(console_host, console_port, path="/", timeout=MEASUREMENT_FETCH_TIMEOUT_DEFAULT):
    result = {
        "path": path,
        "success": False,
        "latency_ms": None,
        "bytes": 0,
        "status_code": None,
        "error": "",
    }
    if not console_port or str(console_port).strip() in {"", "unknown"}:
        result["error"] = "console port unavailable"
        return result
    host = (console_host or "").strip()
    if not host or host in {"unknown", "0.0.0.0"}:
        host = "127.0.0.1"
    url = f"http://{host}:{console_port}{path}"
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "I2P-GUI-Measurement/NativeQt"})
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            payload = resp.read()
            result["status_code"] = getattr(resp, "status", None)
            result["bytes"] = len(payload or b"")
            result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    finally:
        result["latency_ms"] = round((time.perf_counter() - start) * 1000.0, 1)
    return result




def probe_client_tunnel_proxy(namespace, proxy_port, timeout=MEASUREMENT_FETCH_TIMEOUT_DEFAULT, target_url=MEASUREMENT_CLIENT_PROXY_TARGET_URL):
    result = {
        "success": False,
        "connect_success": False,
        "latency_ms": None,
        "first_byte_ms": None,
        "bytes": 0,
        "status_code": None,
        "status_line": "",
        "target_url": target_url,
        "probe_mode": "",
        "error": "",
    }
    ns = str(namespace or "").strip()
    port = str(proxy_port or "").strip()
    if not ns or ns == "unknown":
        result["error"] = "namespace unavailable"
        return result
    if not port or port in {"", "unknown"}:
        result["error"] = "client proxy port unavailable"
        return result
    try:
        port_int = int(port)
    except Exception:
        result["error"] = f"invalid client proxy port: {port}"
        return result

    timeout_f = float(timeout or MEASUREMENT_FETCH_TIMEOUT_DEFAULT)
    target_url = str(target_url or MEASUREMENT_CLIENT_PROXY_TARGET_URL).strip()
    if not target_url:
        result["error"] = "internal eepsite target unavailable"
        return result
    parsed = urllib.parse.urlsplit(target_url)
    target_host = parsed.netloc or parsed.path
    if not target_host:
        result["error"] = f"invalid target url: {target_url}"
        return result
    target_path = parsed.path or "/"
    if parsed.query:
        target_path += "?" + parsed.query

    # First verify that something is actually listening on the expected loopback port
    connect_py = (
        "import json, socket, sys; "
        "host='127.0.0.1'; port=int(sys.argv[1]); t=float(sys.argv[2]); "
        "res={'connect_success': False, 'error': ''}; "
        "s=socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(t); "
        "\ntry:\n"
        " s.connect((host, port)); res['connect_success']=True\n"
        "except Exception as e:\n"
        " res['error']=str(e)\n"
        "finally:\n"
        "\n try: s.close()\n except Exception: pass\n"
        "print(json.dumps(res))"
    )
    try:
        completed = subprocess.run(
            ["sudo", "-n", "ip", "netns", "exec", ns, "python3", "-c", connect_py, str(port_int), str(min(timeout_f, 2.0))],
            capture_output=True,
            text=True,
            timeout=max(3.0, min(timeout_f, 2.0) + 2.0),
            check=False,
        )
        stdout = (completed.stdout or "").strip()
        if stdout:
            try:
                parsed_connect = json.loads(stdout.splitlines()[-1])
                result["connect_success"] = bool(parsed_connect.get("connect_success"))
                if parsed_connect.get("error"):
                    result["error"] = parsed_connect.get("error")
            except Exception:
                pass
        if completed.returncode != 0 and not result["connect_success"]:
            stderr = (completed.stderr or "").strip()
            result["error"] = stderr or result.get("error") or f"return code {completed.returncode}"
            return result
    except Exception as e:
        result["error"] = str(e)
        return result

    if not result["connect_success"]:
        if not result["error"]:
            result["error"] = "client proxy port not accepting connections"
        return result

    curl_base = [
        "sudo", "-n", "ip", "netns", "exec", ns,
        "curl", "-sS",
        "--connect-timeout", str(min(timeout_f, 2.0)),
        "-m", str(timeout_f),
        "-o", "/dev/null",
        "-D", "-",
        "-w", "\n__CURLMETA__%{http_code} %{time_total} %{time_starttransfer} %{size_download}",
    ]

    attempts = [
        {
            "mode": "direct-host-header",
            "cmd": curl_base + ["-H", f"Host: {target_host}", f"http://127.0.0.1:{port_int}{target_path}"],
        },
        {
            "mode": "http-proxy",
            "cmd": curl_base + ["-x", f"http://127.0.0.1:{port_int}", target_url],
        },
    ]

    diagnostics = []
    for attempt in attempts:
        try:
            completed = subprocess.run(
                attempt["cmd"],
                capture_output=True,
                text=True,
                timeout=max(4.0, timeout_f + 2.5),
                check=False,
            )
        except Exception as e:
            diagnostics.append(f"{attempt['mode']}: {e}")
            continue

        stdout = completed.stdout or ""
        stderr = (completed.stderr or "").strip()
        meta = None
        if "__CURLMETA__" in stdout:
            body, meta = stdout.rsplit("__CURLMETA__", 1)
        else:
            body = stdout
        header_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        status_line = ""
        for ln in header_lines:
            if ln.upper().startswith("HTTP/"):
                status_line = ln
                break
        http_code = None
        time_total = None
        time_start = None
        size_download = None
        if meta:
            parts = meta.strip().split()
            if len(parts) >= 4:
                code_txt, total_txt, start_txt, size_txt = parts[:4]
                if code_txt.isdigit():
                    http_code = int(code_txt)
                try:
                    time_total = float(total_txt)
                except Exception:
                    time_total = None
                try:
                    time_start = float(start_txt)
                except Exception:
                    time_start = None
                try:
                    size_download = int(float(size_txt))
                except Exception:
                    size_download = None

        if status_line and http_code is None:
            parts = status_line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                http_code = int(parts[1])

        if status_line or (http_code is not None and http_code != 0):
            result.update({
                "success": True,
                "status_code": http_code,
                "status_line": status_line,
                "latency_ms": round(time_total * 1000.0, 1) if time_total is not None else None,
                "first_byte_ms": round(time_start * 1000.0, 1) if time_start is not None else None,
                "bytes": size_download or 0,
                "probe_mode": attempt["mode"],
                "error": "",
            })
            return result

        detail = stderr or (meta.strip() if meta else "no HTTP response") or f"return code {completed.returncode}"
        diagnostics.append(f"{attempt['mode']}: {detail}")

    result["error"] = "; ".join(diagnostics[-2:]) if diagnostics else (result.get("error") or "client proxy probe failed")
    return result


def correlate_measurement_scenario(started_at_local, finished_at_local, testnet_base, records=None):
    start_dt = parse_display_timestamp(started_at_local)
    finish_dt = parse_display_timestamp(finished_at_local) or start_dt
    if not start_dt:
        return {}
    best = None
    run_dirs = list_recent_run_dirs(SCENARIO_ROOT_DIR, require_files=["run.json", "state.json"], limit=20)
    for run_dir in run_dirs:
        run = read_json_file(os.path.join(run_dir, "run.json"), default={})
        state = read_json_file(os.path.join(run_dir, "state.json"), default={})
        if run.get("testnet_base") != testnet_base:
            continue
        if str(state.get("status", "")).strip().lower() != "completed":
            continue
        fin = parse_display_timestamp(state.get("finished_at_local", "")) or parse_display_timestamp(run.get("started_at_local", ""))
        if not fin or fin > start_dt:
            continue
        delta = (start_dt - fin).total_seconds()
        if delta < 0 or delta > MEASUREMENT_SCENARIO_CORRELATION_WINDOW_SECONDS:
            continue
        if best is None or fin > best[0]:
            best = (fin, run_dir, run, state)
    if not best:
        return {}
    _, run_dir, run, state = best
    events = read_jsonl_records(os.path.join(run_dir, "events.jsonl"))
    touched = []
    seen = set()
    for ev in events:
        rid = str(ev.get("router_id", "")).strip()
        if rid and rid not in seen:
            seen.add(rid)
            touched.append(rid)
    touched_names = []
    by_id = {str((r or {}).get("router_id", "")).strip(): r for r in (records or [])}
    recovered = 0
    full_ready = 0
    run_start = parse_display_timestamp(run.get("started_at_local", ""))
    for rid in touched:
        rec = by_id.get(rid)
        if rec:
            touched_names.append(rec.get("router_name", f"Router {rid}"))
            startup = rec.get("latest_startup") or {}
            trig_dt = parse_display_timestamp(startup.get("trigger_ts_local", "")) if startup else None
            if trig_dt and (run_start is None or trig_dt >= run_start) and trig_dt <= (finish_dt or trig_dt):
                recovered += 1
                if startup.get("to_status_active_s") is not None and startup.get("to_reachability_ok_s") is not None and startup.get("to_accepting_tunnels_s") is not None:
                    full_ready += 1
    return {
        "run_id": state.get("run_id", run.get("run_id", os.path.basename(run_dir))),
        "run_dir": run_dir,
        "scenario_type": state.get("scenario_type", (run.get("config") or {}).get("scenario_type", "unknown")),
        "target_group": state.get("target_group", (run.get("config") or {}).get("target_group", "unknown")),
        "started_at_local": run.get("started_at_local", "unknown"),
        "finished_at_local": state.get("finished_at_local", "unknown"),
        "seconds_since_finish": round((start_dt - best[0]).total_seconds(), 1),
        "completed_cycles": safe_int(state.get("completed_cycles", 0), 0),
        "requested_cycles": safe_int(state.get("requested_cycles", 0), 0),
        "actions_executed": safe_int(state.get("actions_executed", 0), 0),
        "routers_touched": len(touched),
        "touched_router_ids": touched,
        "touched_router_names": touched_names,
        "recovered_touched_routers": recovered,
        "full_ready_touched_routers": full_ready,
        "last_message": state.get("last_message", ""),
    }


def derive_startup_windows(session_dir, router_id):
    events = read_jsonl_records(os.path.join(session_dir or "", "router_events.jsonl"))
    rid = str(router_id or "").strip()
    if not rid or not events:
        return []
    scoped = [e for e in events if str(e.get("router_id", "")).strip() == rid]
    if not scoped:
        return []

    def _ts(ev):
        return parse_display_timestamp(ev.get("ts_local", ""))

    windows = []
    current = None
    for ev in scoped:
        et = str(ev.get("event_type", ""))
        ev_dt = _ts(ev)
        if not ev_dt:
            continue
        if et in {"rejoin_detected", "restart_detected"}:
            if current:
                windows.append(current)
            current = {
                "trigger_event": et,
                "trigger_ts_local": ev.get("ts_local", "unknown"),
                "cause": str(ev.get("cause", "")) or None,
                "downtime_seconds": round(float(ev.get("downtime_seconds", 0.0) or 0.0), 1) if et == "rejoin_detected" else None,
                "to_status_active_s": None,
                "to_reachability_ok_s": None,
                "to_accepting_tunnels_s": None,
                "window_open": True,
                "_start_dt": ev_dt,
            }
            continue
        if not current:
            continue
        start_dt = current.get("_start_dt")
        if not start_dt:
            continue
        elapsed = round((ev_dt - start_dt).total_seconds(), 1)
        if et == "status_change" and current["to_status_active_s"] is None:
            if str(ev.get("new_value", "")).strip().lower() == "active":
                current["to_status_active_s"] = elapsed
        elif et == "reachability_change" and current["to_reachability_ok_s"] is None:
            if str(ev.get("new_value", "")).strip().upper() == "OK":
                current["to_reachability_ok_s"] = elapsed
        elif et == "tunnel_acceptance_change" and current["to_accepting_tunnels_s"] is None:
            new_value = str(ev.get("new_value", "")).strip().lower()
            if new_value.startswith("accepting tunnels"):
                current["to_accepting_tunnels_s"] = elapsed
        if current.get("to_status_active_s") is not None and current.get("to_reachability_ok_s") is not None and current.get("to_accepting_tunnels_s") is not None:
            current["window_open"] = False
    if current:
        windows.append(current)
    for win in windows:
        win.pop("_start_dt", None)
    return windows


def derive_latest_startup_metrics(session_dir, router_id):
    windows = derive_startup_windows(session_dir, router_id)
    return dict(windows[-1]) if windows else {}



def summarize_measurement_probes(probes):
    probes = list(probes or [])
    summary = {
        "routers_requested": len(probes),
        "routers_probed": len(probes),
        "root_success": 0,
        "netdb_success": 0,
        "client_proxy_success": 0,
        "client_proxy_connect_success": 0,
        "routers_with_client_proxy": 0,
        "mean_root_latency_ms": None,
        "mean_netdb_latency_ms": None,
        "mean_client_proxy_latency_ms": None,
        "mean_client_proxy_first_byte_ms": None,
        "mean_startup_to_active_s": None,
        "mean_startup_to_ok_s": None,
        "mean_startup_to_accepting_s": None,
        "routers_with_startup_window": 0,
        "startup_to_ok_success_count": 0,
        "startup_to_accepting_success_count": 0,
        "tunnel_ready_routers": 0,
        "control_plane_ready_routers": 0,
        "full_ready_routers": 0,
        "transaction_ready_routers": 0,
        "tunnel_trace_success": 0,
        "tunnel_trace_changed_routers": 0,
        "top_slowest_root": [],
        "top_slowest_recovery": [],
        "top_slowest_client_proxy": [],
        "slowest_recovery_metric": "startup_to_accepting_s",
    }
    if not probes:
        return summary
    root_lat, netdb_lat = [], []
    client_lat, client_fbyte = [], []
    start_active, start_ok, start_accept = [], [], []
    ranked_root, ranked_recovery, ranked_client = [], [], []
    for rec in probes:
        endpoints = rec.get("endpoints", {}) or {}
        root = endpoints.get("root") or {}
        netdb = endpoints.get("netdb") or {}
        client_proxy = rec.get("client_proxy") or {}
        tunnel_trace = rec.get("tunnel_trace") or {}
        root_success = bool(root.get("success"))
        netdb_success = bool(netdb.get("success"))
        client_success = bool(client_proxy.get("success"))
        client_connect = bool(client_proxy.get("connect_success"))
        if root_success:
            summary["root_success"] += 1
            if root.get("latency_ms") is not None:
                lat = float(root.get("latency_ms") or 0.0)
                root_lat.append(lat)
                ranked_root.append((lat, rec.get("router_name", rec.get("router_id", "?"))))
        if netdb_success:
            summary["netdb_success"] += 1
            if netdb.get("latency_ms") is not None:
                netdb_lat.append(float(netdb.get("latency_ms") or 0.0))
        if tunnel_trace.get("success"):
            summary["tunnel_trace_success"] += 1
        if tunnel_trace.get("path_changed_since_previous"):
            summary["tunnel_trace_changed_routers"] += 1
        if client_proxy:
            summary["routers_with_client_proxy"] += 1
            if client_connect:
                summary["client_proxy_connect_success"] += 1
            if client_success:
                summary["client_proxy_success"] += 1
                if client_proxy.get("latency_ms") is not None:
                    lat = float(client_proxy.get("latency_ms") or 0.0)
                    client_lat.append(lat)
                    ranked_client.append((lat, rec.get("router_name", rec.get("router_id", "?")), client_proxy.get("status_code")))
                if client_proxy.get("first_byte_ms") is not None:
                    client_fbyte.append(float(client_proxy.get("first_byte_ms") or 0.0))
        if root_success and netdb_success:
            summary["control_plane_ready_routers"] += 1
        if root_success and netdb_success and client_success:
            summary["transaction_ready_routers"] += 1
        startup = rec.get("latest_startup") or {}
        if startup:
            summary["routers_with_startup_window"] += 1
            if startup.get("to_status_active_s") is not None:
                start_active.append(float(startup.get("to_status_active_s") or 0.0))
            if startup.get("to_reachability_ok_s") is not None:
                okv = float(startup.get("to_reachability_ok_s") or 0.0)
                start_ok.append(okv)
                summary["startup_to_ok_success_count"] += 1
            if startup.get("to_accepting_tunnels_s") is not None:
                accv = float(startup.get("to_accepting_tunnels_s") or 0.0)
                start_accept.append(accv)
                summary["startup_to_accepting_success_count"] += 1
                summary["tunnel_ready_routers"] += 1
                ranked_recovery.append((accv, rec.get("router_name", rec.get("router_id", "?")), startup.get("trigger_event", "unknown")))
            elif startup.get("to_reachability_ok_s") is not None:
                ranked_recovery.append((float(startup.get("to_reachability_ok_s") or 0.0), rec.get("router_name", rec.get("router_id", "?")), startup.get("trigger_event", "unknown")))
        if root_success and netdb_success and startup and startup.get("to_reachability_ok_s") is not None and startup.get("to_accepting_tunnels_s") is not None:
            summary["full_ready_routers"] += 1
    if root_lat:
        summary["mean_root_latency_ms"] = round(sum(root_lat) / len(root_lat), 1)
    if netdb_lat:
        summary["mean_netdb_latency_ms"] = round(sum(netdb_lat) / len(netdb_lat), 1)
    if client_lat:
        summary["mean_client_proxy_latency_ms"] = round(sum(client_lat) / len(client_lat), 1)
    if client_fbyte:
        summary["mean_client_proxy_first_byte_ms"] = round(sum(client_fbyte) / len(client_fbyte), 1)
    if start_active:
        summary["mean_startup_to_active_s"] = round(sum(start_active) / len(start_active), 1)
    if start_ok:
        summary["mean_startup_to_ok_s"] = round(sum(start_ok) / len(start_ok), 1)
    if start_accept:
        summary["mean_startup_to_accepting_s"] = round(sum(start_accept) / len(start_accept), 1)
    ranked_root.sort(reverse=True)
    ranked_recovery.sort(reverse=True)
    ranked_client.sort(reverse=True)
    summary["top_slowest_root"] = [{"router_name": name, "latency_ms": round(lat, 1)} for lat, name in ranked_root[:5]]
    summary["top_slowest_recovery"] = [{"router_name": name, "seconds": round(sec, 1), "trigger_event": trig} for sec, name, trig in ranked_recovery[:5]]
    summary["top_slowest_client_proxy"] = [{"router_name": name, "latency_ms": round(lat, 1), "status_code": code} for lat, name, code in ranked_client[:5]]
    return summary

def get_service_show(router_id):

    service = f"i2p-router@{router_id}"
    props = [
        "Id", "ActiveState", "SubState", "UnitFileState", "MainPID",
        "ExecMainPID", "ActiveEnterTimestamp", "InactiveEnterTimestamp",
        "FragmentPath", "LoadState", "Result"
    ]
    cmd = ["systemctl", "show"]
    for p in props:
        cmd.extend(["-p", p])
    cmd.append(service)
    out, _, _ = run_cmd(cmd, timeout=STATUS_CMD_TIMEOUT)
    data = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def classify_router_status(service_info):
    active_state = service_info.get("ActiveState", "").strip().lower()
    sub_state = service_info.get("SubState", "").strip().lower()
    result = service_info.get("Result", "").strip().lower()
    main_pid = service_info.get("MainPID", "0").strip()

    if active_state == "active":
        return "active"
    if active_state == "activating":
        return "starting"
    if active_state == "deactivating":
        return "stopping"
    if active_state == "inactive":
        return "stopped"
    if active_state == "failed":
        if sub_state in ("dead", "exited", "failed") and main_pid in ("", "0") and result in ("success", "", "exit-code", "signal"):
            return "stopped"
        return "failed"
    if sub_state == "dead":
        return "stopped"
    return "unknown"


def parse_systemctl_timestamp(value):
    value = (value or "").strip()
    if not value or value.lower() == "n/a":
        return None

    patterns = [
        "%a %Y-%m-%d %H:%M:%S %Z",
        "%a %Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S %z",
    ]
    for fmt in patterns:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def format_uptime_from_timestamp(ts):
    if not ts:
        return "0m"
    try:
        now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        delta = now - ts
        seconds = int(max(delta.total_seconds(), 0))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "0m"


def compute_dashboard_peer_total(peer_known, status):
    if status in ("stopped", "stopping", "failed"):
        return "0"
    known = safe_int(peer_known, 0)
    total = known + 1
    if total < 1:
        total = 1
    return str(total)


def detect_reachability(value, status):
    value = (value or "").strip()
    lower = value.lower()

    if status == "starting":
        return "starting"
    if status == "stopping":
        return "stopping"
    if status == "stopped":
        return "stopped"
    if status == "failed":
        return "failed"

    if value:
        return value
    if "firewalled" in lower:
        return "firewalled"
    if "testing" in lower:
        return "testing"
    if "running" in lower:
        return "running"
    if "hidden" in lower:
        return "hidden"
    return "running"


def detect_tunnel_acceptance(text, status):
    raw = (text or "").strip()
    lower = raw.lower()

    if status == "starting":
        return "starting up"
    if status == "stopping":
        return "stopping"
    if status == "stopped":
        return "stopped"
    if status == "failed":
        return "failed"

    if "rejecting tunnels" in lower and "starting up" in lower:
        return "rejecting tunnels: starting up"
    if "accepting tunnels" in lower:
        return raw.lower() if ":" in raw else "accepting tunnels"
    if "rejecting tunnels" in lower:
        return raw.lower() if ":" in raw else "rejecting tunnels"
    if "starting up" in lower:
        return "starting up"
    if status == "active":
        return "accepting tunnels"
    return "unknown"


def zero_metrics_for_status(status):
    return {
        "peer_count": "0",
        "peer_active": "0",
        "peer_fast": "0",
        "peer_floodfill": "0",
        "peer_known": "0",
        "tunnel_count": "0",
        "tunnel_exploratory": "0",
        "tunnel_client": "0",
        "tunnel_participating": "0",
        "share_ratio": "0",
        "reachability": "failed" if status == "failed" else ("stopped" if status in ("stopped", "stopping") else "unknown"),
        "tunnel_acceptance": "failed" if status == "failed" else ("stopped" if status in ("stopped", "stopping") else "unknown"),
        "uptime": "unknown",
        "main_pid": "0",
    }


def scrape_router_metrics(console_host, console_port, status):
    if status in ("stopped", "stopping", "failed"):
        return zero_metrics_for_status(status)

    root_html = fetch_console_page(console_host, console_port, "/") or ""
    peers_html = fetch_console_page(console_host, console_port, "/peers") or ""
    tunnels_html = fetch_console_page(console_host, console_port, "/tunnels") or ""
    combined_html = "\n".join([root_html, peers_html, tunnels_html])
    combined_text = strip_html_tags(combined_html)

    peer_active_raw = (

        extract_sidebar_metric(peers_html, "sb_peers", "Active")
        or extract_sidebar_metric(root_html, "sb_peers", "Active")
        or extract_sidebar_metric(tunnels_html, "sb_peers", "Active")
        or extract_metric(combined_text, [
            r"\bActive peers?\b[^0-9]{0,20}(\d+)",
            r"\bActive\b[^0-9]{0,20}(\d+)",
        ])
    )

    peer_fast = (
        extract_sidebar_metric(peers_html, "sb_peers", "Fast")
        or extract_sidebar_metric(root_html, "sb_peers", "Fast")
        or extract_sidebar_metric(tunnels_html, "sb_peers", "Fast")
        or extract_metric(combined_text, [r"\bFast\b[^0-9]{0,20}(\d+)"])
    )

    peer_floodfill = (
        extract_sidebar_metric(peers_html, "sb_peers", "Floodfill")
        or extract_sidebar_metric(root_html, "sb_peers", "Floodfill")
        or extract_sidebar_metric(tunnels_html, "sb_peers", "Floodfill")
        or extract_metric(combined_text, [r"\bFloodfill\b[^0-9]{0,20}(\d+)"])
    )

    peer_known = (
        extract_sidebar_metric(peers_html, "sb_peers", "Known")
        or extract_sidebar_metric(root_html, "sb_peers", "Known")
        or extract_sidebar_metric(tunnels_html, "sb_peers", "Known")
        or extract_metric(combined_text, [r"\bKnown\b[^0-9]{0,20}(\d+)"])
    )

    tunnel_exploratory = (
        extract_sidebar_metric(tunnels_html, "sb_tunnels", "Exploratory")
        or extract_sidebar_metric(peers_html, "sb_tunnels", "Exploratory")
        or extract_sidebar_metric(root_html, "sb_tunnels", "Exploratory")
        or extract_metric(combined_text, [r"\bExploratory\b[^0-9]{0,20}(\d+)"])
    )

    tunnel_client = (
        extract_sidebar_metric(tunnels_html, "sb_tunnels", "Client")
        or extract_sidebar_metric(peers_html, "sb_tunnels", "Client")
        or extract_sidebar_metric(root_html, "sb_tunnels", "Client")
        or extract_metric(combined_text, [r"\bClient\b[^0-9]{0,20}(\d+)"])
    )

    tunnel_participating = (
        extract_sidebar_metric(tunnels_html, "sb_tunnels", "Participating")
        or extract_sidebar_metric(peers_html, "sb_tunnels", "Participating")
        or extract_sidebar_metric(root_html, "sb_tunnels", "Participating")
        or extract_metric(combined_text, [r"\bParticipating\b[^0-9]{0,20}(\d+)"])
    )

    share_ratio = (
        extract_sidebar_metric(tunnels_html, "sb_tunnels", "Share ratio")
        or extract_sidebar_metric(peers_html, "sb_tunnels", "Share ratio")
        or extract_sidebar_metric(root_html, "sb_tunnels", "Share ratio")
        or extract_metric(combined_text, [r"\bShare ratio\b[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)"])
    )

    reachability = (
        extract_reachability_from_html(root_html)
        or extract_reachability_from_html(peers_html)
        or extract_reachability_from_html(tunnels_html)
    )

    tunnel_status_text = (
        extract_tunnel_build_status(tunnels_html)
        or extract_tunnel_build_status(peers_html)
        or extract_tunnel_build_status(root_html)
        or extract_metric(combined_text, [
            r"(Rejecting tunnels:\s*Starting up)",
            r"(Rejecting tunnels:\s*[A-Za-z0-9 _-]+)",
            r"(Accepting tunnels:\s*[A-Za-z0-9 _-]+)",
            r"(Accepting tunnels)",
            r"(Rejecting tunnels)",
        ])
    )

    peer_active = extract_peer_active_value(peer_active_raw)
    peer_fast = digits_or_default(peer_fast, "0")
    peer_floodfill = digits_or_default(peer_floodfill, "0")
    peer_known = digits_or_default(peer_known, "0")
    peer_total = compute_dashboard_peer_total(peer_known, status)

    peer_total_i = safe_int(peer_total, 0)
    peer_active_i = safe_int(peer_active, 0)
    peer_fast_i = safe_int(peer_fast, 0)
    peer_floodfill_i = safe_int(peer_floodfill, 0)

    if peer_total_i > 0:
        peer_active_i = min(peer_active_i, peer_total_i)
        peer_fast_i = min(peer_fast_i, peer_active_i)
        peer_floodfill_i = min(peer_floodfill_i, peer_total_i)
    else:
        peer_active_i = 0
        peer_fast_i = 0
        peer_floodfill_i = 0

    peer_active = str(peer_active_i)
    peer_fast = str(peer_fast_i)
    peer_floodfill = str(peer_floodfill_i)

    tunnel_exploratory = digits_or_default(tunnel_exploratory, "0")
    tunnel_client = digits_or_default(tunnel_client, "0")
    tunnel_participating = digits_or_default(tunnel_participating, "0")
    tunnel_total = str(
        safe_int(tunnel_exploratory)
        + safe_int(tunnel_client)
        + safe_int(tunnel_participating)
    )
    tunnel_total = digits_or_default(tunnel_total, "0")

    share_ratio = decimal_or_default(share_ratio, "0")
    reachability = detect_reachability(reachability, status)
    tunnel_acceptance = detect_tunnel_acceptance(tunnel_status_text, status)

    return {
        "peer_count": peer_total,
        "peer_active": peer_active,
        "peer_fast": peer_fast,
        "peer_floodfill": peer_floodfill,
        "peer_known": peer_known,
        "tunnel_count": tunnel_total,
        "tunnel_exploratory": tunnel_exploratory,
        "tunnel_client": tunnel_client,
        "tunnel_participating": tunnel_participating,
        "share_ratio": share_ratio,
        "reachability": reachability,
        "tunnel_acceptance": tunnel_acceptance,
        "uptime": "unknown",
        "main_pid": "0",
    }


def find_best_log(router_dir, router_id):
    candidates = [
        os.path.join(router_dir, "logs", f"log-router-{router_id}.txt"),
        os.path.join(router_dir, "logs", "wrapper.log"),
        os.path.join(router_dir, "logs", "router.log"),
        os.path.join(router_dir, "wrapper.log"),
        os.path.join(router_dir, "stdout.log"),
        os.path.join(router_dir, "bootstrap.log"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    try:
        log_dir = os.path.join(router_dir, "logs")
        txts = sorted(glob.glob(os.path.join(log_dir, "*.txt")))
        if txts:
            return txts[-1]
    except Exception:
        pass
    return None


def build_logs_view(router):
    service = router["service"]
    router_dir = router["router_dir"]
    router_id = router["id"]

    status_out, status_err, _ = run_cmd(["systemctl", "status", service, "--no-pager", "-l"], timeout=LOG_CMD_TIMEOUT)
    journal_out, journal_err, _ = run_cmd(
        ["journalctl", "-u", service, "-n", "200", "--no-pager", "-o", "short-iso"],
        timeout=LOG_CMD_TIMEOUT,
    )
    log_path = find_best_log(router_dir, router_id)
    file_log = read_file_safe(log_path, max_lines=READ_FILE_MAX_LINES) if log_path else "No router log file found."

    if not status_out and status_err:
        status_out = f"Error reading systemctl status: {status_err}"
    if not journal_out and journal_err:
        journal_out = f"Error reading journalctl output: {journal_err}"

    return "\n".join([
        f"Router {router_id} · Logs",
        "=" * 72,
        f"Generated: {now_display()}",
        "",
        "===== SYSTEMCTL STATUS =====",
        status_out or "No systemctl status output found.",
        "",
        "===== SERVICE JOURNAL =====",
        journal_out or "No journal entries found.",
        "",
        f"===== ROUTER LOG FILE ({log_path if log_path else 'none'}) =====",
        file_log,
    ])


def discover_router_entries():
    base = find_testnet_base()
    entries = []
    if not base:
        return None, entries

    try:
        dir_entries = sorted(
            os.listdir(base),
            key=lambda x: safe_int(x[1:], 9999) if re.fullmatch(r"r\d+", x) else 9999
        )
    except Exception:
        return base, entries

    for entry in dir_entries:
        if re.fullmatch(r"r\d+", entry):
            router_id = entry[1:]
            router_dir = os.path.join(base, entry)
            cfg = os.path.join(router_dir, "config", "router.config")
            tun_cfg = os.path.join(router_dir, "config", "i2ptunnel.config")
            parsed = parse_router_config(cfg)
            tunnel_parsed = parse_i2ptunnel_config(tun_cfg)
            parsed.update(tunnel_parsed)
            entries.append({
                "id": router_id,
                "name": f"Router {router_id}",
                "service": f"i2p-router@{router_id}",
                "router_dir": router_dir,
                "config_path": cfg,
                "i2ptunnel_config_path": tun_cfg,
                "logs_dir": os.path.join(router_dir, "logs"),
                "testnet_base": base,
                "parsed": parsed,
                "console_port": parsed["console_port"],
                "console_host": parsed.get("console_host", "unknown"),
                "console_url": parsed.get("console_url") if parsed.get("console_url") not in {"", "unknown"} else (f"http://{parsed.get('console_host')}:{parsed['console_port']}" if parsed["console_port"] != "unknown" and parsed.get("console_host") not in {"", "unknown"} else None),
                "router_ip": parsed.get("router_ip", "unknown"),
                "floodfill": parsed["floodfill"],
            })

    return base, entries


def collect_router_snapshot():
    base, entries = discover_router_entries()
    topology_map = load_topology_map(base)
    routers = []
    active = 0
    stopped = 0
    failed = 0
    floodfill_count = 0

    for entry in entries:
        service_info = get_service_show(entry["id"])
        status = classify_router_status(service_info)
        metrics = scrape_router_metrics(entry.get("console_host"), entry["console_port"], status)
        metrics["main_pid"] = service_info.get("MainPID", "0") or "0"

        if status == "active":
            ts = parse_systemctl_timestamp(service_info.get("ActiveEnterTimestamp", ""))
            metrics["uptime"] = format_uptime_from_timestamp(ts)
        elif status == "starting":
            metrics["uptime"] = "starting"
        elif status == "stopping":
            metrics["uptime"] = "stopping"
        elif status == "stopped":
            metrics["uptime"] = "stopped"
        elif status == "failed":
            metrics["uptime"] = "failed"

        router = dict(entry)
        router["status"] = status
        router["service_info"] = service_info
        router["metrics"] = metrics

        topo = topology_map.get(router["id"], {})
        parsed = dict(router.get("parsed", {}))
        for key, topo_key in [
            ("country", "country"),
            ("country_code", "country_code"),
            ("city", "city"),
            ("display_lat", "display_lat"),
            ("display_lon", "display_lon"),
            ("subnet_label", "subnet_label"),
            ("namespace", "namespace"),
            ("bridge", "bridge"),
            ("subnet", "subnet"),
            ("gateway", "gateway"),
        ]:
            topo_val = topo.get(topo_key, "")
            if topo_val:
                parsed[key] = topo_val
        if topo.get("ip"):
            parsed["router_ip"] = topo["ip"]
            router["router_ip"] = topo["ip"]
        if topo.get("console_url"):
            router["console_url"] = topo["console_url"]
            parsed["console_url"] = topo["console_url"]
        if topo.get("console_port"):
            router["console_port"] = topo["console_port"]
            parsed["console_port"] = topo["console_port"]
        if topo.get("floodfill"):
            router["floodfill"] = topo["floodfill"]
            parsed["floodfill"] = topo["floodfill"]
        router["parsed"] = parsed
        routers.append(router)

        if status == "active":
            active += 1
        elif status in ("stopped", "stopping"):
            stopped += 1
        elif status == "failed":
            failed += 1

        if str(entry.get("floodfill", "")).lower() == "true":
            floodfill_count += 1

    return {
        "generated_at": now_display(),
        "base": base,
        "base_available": bool(base),
        "total": len(routers),
        "active": active,
        "stopped": stopped,
        "failed": failed,
        "floodfill_count": floodfill_count,
        "routers": routers,
    }


def build_summary_text(router):
    p = router["parsed"]
    m = router["metrics"]
    s = router["service_info"]

    lines = [
        f"Router {router['id']} Summary",
        "=" * 72,
        f"Generated: {now_display()}",
        "",
        "[ Overview ]",
        f"Service               : {router['service']}",
        f"Status                : {router['status'].upper()}",
        f"Floodfill             : {router['floodfill']}",
        f"Namespace             : {p.get('namespace', 'unknown')}",
        f"Location              : {p.get('city', 'unknown')}, {p.get('country', 'unknown')}",
        f"Subnet Label          : {p.get('subnet_label', 'unknown')}",
        f"Subnet                : {p.get('subnet', 'unknown')}",
        f"Router IP             : {p.get('router_ip', 'unknown')}",
        f"Gateway               : {p.get('gateway', 'unknown')}",
        f"Console Port          : {router['console_port']}",
        f"Console URL           : {router['console_url'] or 'not available'}",
        f"Uptime                : {m['uptime']}",
        "",
        "[ Service ]",
        f"ActiveState           : {s.get('ActiveState', 'unknown')}",
        f"SubState              : {s.get('SubState', 'unknown')}",
        f"Result                : {s.get('Result', 'unknown')}",
        f"Main PID              : {m['main_pid']}",
        f"Reachability          : {m['reachability']}",
        f"Tunnel Acceptance     : {m['tunnel_acceptance']}",
        "",
        "[ Peers ]",
        f"Total                 : {m['peer_count']}",
        f"Active                : {m['peer_active']}",
        f"Fast                  : {m['peer_fast']}",
        f"Floodfill             : {m['peer_floodfill']}",
        f"Known                 : {m['peer_known']}",
        "",
        "[ Tunnels ]",
        f"Total                 : {m['tunnel_count']}",
        f"Exploratory           : {m['tunnel_exploratory']}",
        f"Client                : {m['tunnel_client']}",
        f"Participating         : {m['tunnel_participating']}",
        f"Share Ratio           : {m['share_ratio']}",
        "",
        "[ Router Properties ]",
        f"Network ID            : {p.get('network_id', 'unknown')}",
        f"Console Bind Host     : {p.get('console_bind_host', 'unknown')}",
        f"Console Access Host   : {p.get('console_host', 'unknown')}",
        f"Bridge                : {p.get('bridge', 'unknown')}",
        f"Host veth             : {p.get('host_veth', 'unknown')}",
        f"Namespace veth        : {p.get('ns_veth', 'unknown')}",
        f"NTCP Host             : {p.get('ntcp_host', 'unknown')}",
        f"NTCP Port             : {p.get('ntcp_port', 'unknown')}",
        f"UDP Host              : {p.get('udp_host', 'unknown')}",
        f"UDP Port              : {p.get('udp_port', 'unknown')}",
        "",
        "[ Performance ]",
        f"Inbound KB/s          : {p.get('bandwidth_in', 'unknown')}",
        f"Outbound KB/s         : {p.get('bandwidth_out', 'unknown')}",
        f"Participating Limit   : {p.get('participating_limit', 'unknown')}",
        f"Expl. Inbound Length  : {p.get('expl_in_len', 'unknown')}",
        f"Expl. Outbound Length : {p.get('expl_out_len', 'unknown')}",
        "",
        "[ Paths ]",
        f"Router Data Dir       : {p.get('router_dir_data', 'unknown')}",
        f"Router Log Dir        : {p.get('router_dir_log', 'unknown')}",
        f"Config File           : {router['config_path']}",
    ]
    return "\n".join(lines)


def deployment_log_reset():
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(DEPLOY_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"[{now_display()}] Deployment log reset.\n")


def deployment_log_write(line):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(DEPLOY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def deployment_log_tail(max_lines=300):
    if not os.path.exists(DEPLOY_LOG_FILE):
        return "No deployment log yet."
    try:
        with open(DEPLOY_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except Exception as e:
        return f"Unable to read deployment log: {e}"


def validate_deploy_params(routers, floodfill):
    routers = safe_int(routers, 0)
    floodfill = safe_int(floodfill, 0)
    if routers < 2:
        return None, None, "Routers must be at least 2."
    if floodfill < 1:
        return None, None, "Floodfill must be at least 1."
    if floodfill > routers:
        return None, None, "Floodfill cannot exceed total routers."
    return routers, floodfill, None


def count_tsv_rows(path):
    if not path or not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            rows = [line for line in f.read().splitlines() if line.strip()]
        return max(0, len(rows) - 1)
    except Exception:
        return 0


def discover_existing_runtime_targets():
    bases = get_existing_testnet_bases()
    router_ids = set()
    console_ports = set()
    router_meta = []
    for base in bases:
        try:
            for entry in os.listdir(base):
                if re.fullmatch(r"r\d+", entry):
                    router_id = int(entry[1:])
                    router_ids.add(router_id)
                    cfg = os.path.join(base, entry, "config", "router.config")
                    parsed = parse_router_config(cfg)
                    port = safe_int(parsed.get("console_port"), 0)
                    if port > 0:
                        console_ports.add(port)
                    router_meta.append({
                        "id": router_id,
                        "namespace": parsed.get("namespace", "unknown"),
                        "bridge": parsed.get("bridge", "unknown"),
                        "host_veth": parsed.get("host_veth", "unknown"),
                        "router_ip": parsed.get("router_ip", "unknown"),
                    })
        except Exception:
            continue
    return sorted(router_ids), sorted(console_ports), bases, router_meta


def list_prefixed_namespaces():
    out, _, _ = run_cmd(["ip", "netns", "list"], timeout=ACTION_CMD_TIMEOUT)
    names = []
    for line in out.splitlines():
        name = line.strip().split()[0] if line.strip() else ""
        if re.fullmatch(r"i2pns-r\d+", name):
            names.append(name)
    return names


def list_prefixed_links():
    out, _, _ = run_cmd(["ip", "-o", "link", "show"], timeout=ACTION_CMD_TIMEOUT)
    names = []
    for line in out.splitlines():
        parts = line.split(": ", 2)
        if len(parts) < 2:
            continue
        name = parts[1].split("@", 1)[0].strip()
        if re.fullmatch(r"(?:i2pbr-r|i2ph|i2pn)\d+", name):
            names.append(name)
    return names


def cleanup_prefixed_network_runtime():
    for ns in list_prefixed_namespaces():
        run_cmd(sudo_cmd("ip", "netns", "delete", ns), timeout=ACTION_CMD_TIMEOUT)

    seen = set()
    for link in list_prefixed_links():
        if link in seen:
            continue
        seen.add(link)
        run_cmd(sudo_cmd("ip", "link", "delete", link), timeout=ACTION_CMD_TIMEOUT)


def remove_tree_force(path):
    if not path or not os.path.exists(path):
        return
    try:
        shutil.rmtree(path)
        return
    except Exception:
        pass

    run_cmd(sudo_cmd("chown", "-R", f"{os.getuid()}:{os.getgid()}", path), timeout=ACTION_CMD_TIMEOUT)
    try:
        shutil.rmtree(path)
        return
    except Exception:
        pass

    out, err, rc = run_cmd(sudo_cmd("rm", "-rf", path), timeout=max(ACTION_CMD_TIMEOUT, 20))
    if rc != 0 and os.path.exists(path):
        combined = "\n".join(x for x in [out, err] if x).strip()
        raise RuntimeError(combined or f"Unable to delete directory: {path}")


def stop_emulator_runtime():
    router_ids, console_ports, bases, _router_meta = discover_existing_runtime_targets()
    if not bases and not router_ids:
        deployment_log_write("No deployed emulator detected under ~/i2p-testnet-* .")
        return

    deployment_log_write("Stopping emulator services.")
    commands = [
        sudo_cmd("systemctl", "stop", "i2p-crosspoll.timer"),
        sudo_cmd("systemctl", "stop", "i2p-crosspoll.service"),
        sudo_cmd("systemctl", "stop", "i2p-testnet.target"),
        sudo_cmd("systemctl", "stop", "i2p-testnet-net.service"),
    ]
    for cmd in commands:
        run_cmd(cmd, timeout=ACTION_CMD_TIMEOUT)

    ids_to_stop = router_ids if router_ids else list(range(1, DEPLOY_MAX_ROUTER_SERVICE_ID + 1))
    for n in ids_to_stop:
        run_cmd(sudo_cmd("systemctl", "stop", f"i2p-router@{n}.service"), timeout=ACTION_CMD_TIMEOUT)
        run_cmd(sudo_cmd("systemctl", "reset-failed", f"i2p-router@{n}.service"), timeout=ACTION_CMD_TIMEOUT)

    run_cmd(sudo_cmd("pkill", "-f", r"/home/.*/i2p-testnet-.*/r[0-9]+/start\.sh"), timeout=ACTION_CMD_TIMEOUT)
    run_cmd(sudo_cmd("pkill", "-f", r"net\.i2p\.router\.RouterLaunch"), timeout=ACTION_CMD_TIMEOUT)

    for port in console_ports:
        run_cmd(sudo_cmd("fuser", "-k", f"{port}/tcp"), timeout=3)

    deployment_log_write("Emulator stop sequence completed.")


def destroy_emulator_runtime():
    router_ids, _, bases, _router_meta = discover_existing_runtime_targets()
    if not bases:
        deployment_log_write("No emulator directory found to destroy.")
        return

    stop_emulator_runtime()

    for n in router_ids:
        run_cmd(sudo_cmd("systemctl", "disable", f"i2p-router@{n}.service"), timeout=ACTION_CMD_TIMEOUT)
        run_cmd(sudo_cmd("rm", "-f", f"/etc/systemd/system/i2p-router@{n}.service"), timeout=ACTION_CMD_TIMEOUT)

    for service_file in (
        "/etc/systemd/system/i2p-crosspoll.service",
        "/etc/systemd/system/i2p-crosspoll.timer",
        "/etc/systemd/system/i2p-testnet.target",
        "/etc/systemd/system/i2p-testnet-net.service",
    ):
        run_cmd(sudo_cmd("rm", "-f", service_file), timeout=ACTION_CMD_TIMEOUT)

    run_cmd(sudo_cmd("systemctl", "disable", "i2p-crosspoll.timer"), timeout=ACTION_CMD_TIMEOUT)
    run_cmd(sudo_cmd("systemctl", "disable", "i2p-testnet.target"), timeout=ACTION_CMD_TIMEOUT)
    run_cmd(sudo_cmd("systemctl", "disable", "i2p-testnet-net.service"), timeout=ACTION_CMD_TIMEOUT)
    run_cmd(sudo_cmd("systemctl", "daemon-reload"), timeout=ACTION_CMD_TIMEOUT)

    cleanup_prefixed_network_runtime()

    for path in bases:
        remove_tree_force(path)
        deployment_log_write(f"Deleted: {path}")

    deployment_log_write("Emulator directories and namespace fabric destroyed.")


def _raise_systemctl_error(action, out, err):
    combined = "\n".join(x for x in [out, err] if x).strip()
    if "sudo" in combined.lower() and ("password" in combined.lower() or "tty" in combined.lower()):
        raise RuntimeError("This GUI needs passwordless sudo for systemctl actions. Configure sudoers for these commands, then try again.")
    raise RuntimeError(combined or f"systemctl {action} failed")


def run_systemctl_checked(*parts, timeout=ACTION_CMD_TIMEOUT):
    out, err, rc = run_cmd(sudo_cmd("systemctl", *parts), timeout=timeout)
    if rc != 0:
        _raise_systemctl_error(" ".join(parts), out, err)
    return out, err, rc


def wait_for_router_states(router_id, target_states, timeout=ACTION_WAIT_TIMEOUT, require_pid=None, forbid_pid=None):
    deadline = time.time() + max(timeout, ACTION_POLL_INTERVAL)
    target_states = set(target_states)
    last_info = {}
    last_status = "unknown"
    while time.time() < deadline:
        info = get_service_show(router_id)
        status = classify_router_status(info)
        pid = safe_int(info.get("MainPID", "0"), 0)
        last_info = info
        last_status = status

        if status == "failed" and "failed" not in target_states:
            detail = f"ActiveState={info.get('ActiveState', 'unknown')}, SubState={info.get('SubState', 'unknown')}, Result={info.get('Result', 'unknown')}"
            raise RuntimeError(f"Router {router_id} entered failed state while waiting for {', '.join(sorted(target_states))}. {detail}")

        if status in target_states:
            if require_pid is True and pid <= 0:
                time.sleep(ACTION_POLL_INTERVAL)
                continue
            if forbid_pid is not None and forbid_pid > 0 and pid == forbid_pid:
                time.sleep(ACTION_POLL_INTERVAL)
                continue
            return info

        time.sleep(ACTION_POLL_INTERVAL)

    detail = f"ActiveState={last_info.get('ActiveState', 'unknown')}, SubState={last_info.get('SubState', 'unknown')}, Result={last_info.get('Result', 'unknown')}, MainPID={last_info.get('MainPID', '0')}"
    raise RuntimeError(f"Timed out waiting for Router {router_id} to reach {', '.join(sorted(target_states))}. Last state: {last_status}. {detail}")


def systemctl_action(action, router_id):
    service = f"i2p-router@{router_id}"
    if action not in {"start", "stop", "restart"}:
        raise RuntimeError(f"Unsupported action: {action}")

    old_info = get_service_show(router_id)
    old_pid = safe_int(old_info.get("MainPID", "0"), 0)

    if action == "restart":
        run_systemctl_checked("stop", service, timeout=ACTION_CMD_TIMEOUT)
        wait_for_router_states(router_id, {"stopped"}, timeout=ACTION_WAIT_TIMEOUT)
        run_systemctl_checked("reset-failed", service, timeout=ACTION_CMD_TIMEOUT)
        run_systemctl_checked("start", service, timeout=ACTION_CMD_TIMEOUT)
        wait_for_router_states(router_id, {"active", "starting"}, timeout=ACTION_WAIT_TIMEOUT, require_pid=True, forbid_pid=old_pid if old_pid > 0 else None)
        return

    run_systemctl_checked(action, service, timeout=ACTION_CMD_TIMEOUT)

    if action == "stop":
        wait_for_router_states(router_id, {"stopped"}, timeout=ACTION_WAIT_TIMEOUT)
        run_systemctl_checked("reset-failed", service, timeout=ACTION_CMD_TIMEOUT)
    elif action == "start":
        wait_for_router_states(router_id, {"active", "starting"}, timeout=ACTION_WAIT_TIMEOUT, require_pid=True)


class MonitorThread(QThread):
    snapshot_ready = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._last_base = object()

    def run(self):
        while self._running:
            try:
                snapshot = collect_router_snapshot()
                snapshot["_snapshot_source"] = "monitor"
                current_base = snapshot.get("base")
                if current_base != self._last_base:
                    self._last_base = current_base
                self.snapshot_ready.emit(snapshot)
            except Exception as e:
                self.error_signal.emit(str(e))
            self.msleep(int(POLL_SECONDS * 1000))

    def stop(self):
        self._running = False


class ActionThread(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, fn, success_message, parent=None):
        super().__init__(parent)
        self.fn = fn
        self.success_message = success_message

    def run(self):
        try:
            self.fn()
            self.done.emit(self.success_message)
        except Exception as e:
            self.failed.emit(str(e))


class ChurnRunnerThread(QThread):
    log_line = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    started_run = pyqtSignal(dict)
    progress = pyqtSignal(dict)
    finished_run = pyqtSignal(dict)
    failed_run = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    action_intent = pyqtSignal(str, str, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = dict(config or {})
        self._running = True
        self._event_seq = 0
        self._completed_cycles = 0
        self._actions_executed = 0
        self._current_phase = "idle"
        self.run_manifest = None
        self.run_dir = None
        self.last_message = "Not started."

    def stop(self):
        self._running = False

    def _append_event(self, event_type, **extra):
        self._event_seq += 1
        event = {
            "event_seq": self._event_seq,
            "ts_local": now_display(),
            "ts_utc": now_iso_utc(),
            "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
            "testnet_base": self.config.get("testnet_base"),
            "event_type": event_type,
            "scenario_type": self.config.get("scenario_type"),
            "target_group": self.config.get("target_group"),
            "scenario_preset_id": self.config.get("scenario_preset_id"),
            "scenario_preset_name": self.config.get("scenario_preset_name"),
            "experiment_label": self.config.get("experiment_label"),
            "completed_cycles": self._completed_cycles,
            "requested_cycles": safe_int(self.config.get("max_cycles", 0), 0),
        }
        event.update(extra)
        if self.run_manifest:
            append_jsonl(self.run_manifest["files"]["events"], event)
        return event

    def _update_state(self, status, **extra):
        self._current_phase = status
        payload = {
            "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
            "run_dir": self.run_manifest.get("run_dir") if self.run_manifest else None,
            "status": status,
            "scenario_type": self.config.get("scenario_type"),
            "target_group": self.config.get("target_group"),
            "scenario_preset_id": self.config.get("scenario_preset_id"),
            "scenario_preset_name": self.config.get("scenario_preset_name"),
            "experiment_label": self.config.get("experiment_label"),
            "testnet_base": self.config.get("testnet_base"),
            "completed_cycles": self._completed_cycles,
            "requested_cycles": safe_int(self.config.get("max_cycles", 0), 0),
            "actions_executed": self._actions_executed,
            "last_message": self.last_message,
            "updated_at_local": now_display(),
            "seed": self.config.get("seed"),
        }
        payload.update(extra)
        if self.run_manifest:
            write_json_atomic(self.run_manifest["files"]["state"], payload)
        self.progress.emit(payload)

    def _log(self, text, event_type=None, **extra):
        self.last_message = str(text)
        line = f"[{now_display()}] {text}"
        self.log_line.emit(line)
        self.status_changed.emit(text)
        if event_type:
            self._append_event(event_type, message=text, **extra)
        self._update_state(self._current_phase or "running")

    def _sleep_interruptible(self, seconds, phase, router_id=None):
        seconds = max(0.0, float(seconds))
        deadline = time.time() + seconds
        remaining = seconds
        self._update_state(phase, router_id=str(router_id) if router_id else None, remaining_seconds=round(remaining, 1))
        while self._running and time.time() < deadline:
            remaining = max(0.0, deadline - time.time())
            self._update_state(phase, router_id=str(router_id) if router_id else None, remaining_seconds=round(remaining, 1))
            time.sleep(min(0.25, max(0.05, remaining)))
        self._update_state(phase, router_id=str(router_id) if router_id else None, remaining_seconds=0.0)
        return self._running

    def _filtered_inventory(self):
        target_group = str(self.config.get("target_group", "non_floodfill")).strip()
        target_mode = str(self.config.get("target_mode", "random_pool") or "random_pool").strip()
        selected_router_ids = {str(rid).strip() for rid in (self.config.get("selected_router_ids") or []) if str(rid).strip()}
        routers = list(self.config.get("routers", []))
        if target_group == "floodfill_only":
            routers = [r for r in routers if r.get("floodfill")]
        elif target_group == "non_floodfill":
            routers = [r for r in routers if not r.get("floodfill")]
        if target_mode == "selected_routers":
            routers = [r for r in routers if str(r.get("id")).strip() in selected_router_ids]
        return routers

    def _eligible_routers(self, inventory, eligible_statuses):
        eligible = []
        for router in inventory:
            rid = str(router.get("id"))
            info = get_service_show(rid)
            status = classify_router_status(info)
            if status in eligible_statuses:
                enriched = dict(router)
                enriched["status"] = status
                enriched["main_pid"] = info.get("MainPID", "0")
                eligible.append(enriched)
        return eligible

    def run(self):
        try:
            inventory = self._filtered_inventory()
            if not inventory:
                raise RuntimeError("No eligible routers match the selected target group for this churn scenario.")

            self.run_manifest = create_churn_run_manifest(self.config.get("testnet_base"), self.config)
            self.run_dir = self.run_manifest["run_dir"]
            self.started_run.emit(dict(self.run_manifest))

            seed = self.config.get("seed")
            if seed in (None, 0, "0", ""):
                seed = int(time.time() * 1000) % 1000000000
            seed = safe_int(seed, 1)
            self.config["seed"] = seed
            rng = random.Random(seed)

            scenario_type = str(self.config.get("scenario_type", "random_stop_start"))
            min_interval = max(1.0, float(self.config.get("min_interval_seconds", SCENARIO_DEFAULT_MIN_INTERVAL)))
            max_interval = max(min_interval, float(self.config.get("max_interval_seconds", SCENARIO_DEFAULT_MAX_INTERVAL)))
            downtime = max(1.0, float(self.config.get("downtime_seconds", SCENARIO_DEFAULT_DOWNTIME)))
            max_cycles = max(1, safe_int(self.config.get("max_cycles", SCENARIO_DEFAULT_MAX_CYCLES), SCENARIO_DEFAULT_MAX_CYCLES))

            self._current_phase = "running"
            self._append_event("scenario_started", seed=seed, inventory_size=len(inventory))
            target_mode = str(self.config.get("target_mode", "random_pool") or "random_pool")
            selected_router_ids = [str(rid) for rid in (self.config.get("selected_router_ids") or []) if str(rid).strip()]
            self._log(
                f"Scenario started: {scenario_type} | target={self.config.get('target_group')} | mode={target_mode} | candidates={len(inventory)} | cycles={max_cycles} | seed={seed}",
                event_type="scenario_started_message",
            )
            self._update_state("running", seed=seed, inventory_size=len(inventory))

            selected_rotation_index = 0
            for cycle_index in range(1, max_cycles + 1):
                if not self._running:
                    break

                eligible = self._eligible_routers(inventory, {"active"})

                if not eligible:
                    wait_seconds = min_interval
                    self._log(f"No eligible active routers found for cycle {cycle_index}; waiting {format_seconds_brief(wait_seconds)}.", event_type="cycle_skipped", cycle_index=cycle_index)
                    if not self._sleep_interruptible(wait_seconds, "waiting_for_eligible"):
                        break
                    continue

                if target_mode == "selected_routers" and selected_router_ids:
                    ordered_ids = selected_router_ids[:]
                    eligible_by_id = {str(router.get("id")): router for router in eligible}
                    chosen = None
                    for offset in range(len(ordered_ids)):
                        candidate_id = ordered_ids[(selected_rotation_index + offset) % len(ordered_ids)]
                        if candidate_id in eligible_by_id:
                            chosen = eligible_by_id[candidate_id]
                            selected_rotation_index = (selected_rotation_index + offset + 1) % len(ordered_ids)
                            break
                    if chosen is None:
                        wait_seconds = min_interval
                        self._log(
                            f"No selected routers are currently eligible for cycle {cycle_index}; waiting {format_seconds_brief(wait_seconds)}.",
                            event_type="cycle_skipped",
                            cycle_index=cycle_index,
                        )
                        if not self._sleep_interruptible(wait_seconds, "waiting_for_selected"):
                            break
                        continue
                    target = chosen
                else:
                    target = rng.choice(eligible)

                rid = str(target.get("id"))
                router_name = target.get("name", f"Router {rid}")

                if scenario_type == "random_restart":
                    self.action_intent.emit("restart", rid, SCENARIO_ACTION_SOURCE)
                    self._append_event("cycle_begin", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="restart")
                    self._log(f"Cycle {cycle_index}/{max_cycles}: restarting {router_name}.", event_type="action_begin", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="restart")
                    systemctl_action("restart", rid)
                    self._actions_executed += 1
                    self.refresh_requested.emit()
                    self._completed_cycles += 1
                    self._append_event("cycle_complete", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="restart")
                    self._log(f"Cycle {cycle_index}/{max_cycles}: restart completed for {router_name}.", event_type="action_complete", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="restart")
                    self._update_state("running", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="restart")
                else:
                    self.action_intent.emit("stop", rid, SCENARIO_ACTION_SOURCE)
                    self._append_event("cycle_begin", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="stop_start")
                    self._log(f"Cycle {cycle_index}/{max_cycles}: stopping {router_name}.", event_type="action_begin", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="stop")
                    systemctl_action("stop", rid)
                    self._actions_executed += 1
                    self.refresh_requested.emit()
                    self._update_state("downtime", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="stop_start", remaining_seconds=round(downtime, 1))
                    self._append_event("downtime_begin", cycle_index=cycle_index, router_id=rid, router_name=router_name, downtime_seconds=round(downtime, 1))
                    self._log(f"Cycle {cycle_index}/{max_cycles}: {router_name} down for {format_seconds_brief(downtime)}.", event_type="downtime_begin_message", cycle_index=cycle_index, router_id=rid, router_name=router_name, downtime_seconds=round(downtime, 1))
                    still_running = self._sleep_interruptible(downtime, "downtime", router_id=rid)
                    if not still_running:
                        self._log(f"Stop requested during downtime; restoring {router_name} before exiting.", event_type="restore_on_stop", cycle_index=cycle_index, router_id=rid, router_name=router_name)
                    self.action_intent.emit("start", rid, SCENARIO_ACTION_SOURCE)
                    self._log(f"Cycle {cycle_index}/{max_cycles}: starting {router_name}.", event_type="action_begin", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="start")
                    systemctl_action("start", rid)
                    self._actions_executed += 1
                    self.refresh_requested.emit()
                    self._completed_cycles += 1
                    self._append_event("cycle_complete", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="stop_start")
                    self._log(f"Cycle {cycle_index}/{max_cycles}: stop/start cycle completed for {router_name}.", event_type="action_complete", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="stop_start")
                    self._update_state("running", cycle_index=cycle_index, router_id=rid, router_name=router_name, action="stop_start")
                    if not still_running:
                        break

                if cycle_index >= max_cycles or not self._running:
                    continue

                interval = rng.uniform(min_interval, max_interval)
                self._append_event("inter_cycle_wait", cycle_index=cycle_index, wait_seconds=round(interval, 1))
                self._log(f"Inter-cycle wait: {format_seconds_brief(interval)} before next cycle.", event_type="inter_cycle_wait_message", cycle_index=cycle_index, wait_seconds=round(interval, 1))
                if not self._sleep_interruptible(interval, "inter_cycle_wait"):
                    break

            status = "stopped" if not self._running and self._completed_cycles < max_cycles else "completed"
            self.last_message = f"Scenario {status}. Completed cycles: {self._completed_cycles}/{max_cycles}."
            summary = {
                "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
                "run_dir": self.run_manifest.get("run_dir") if self.run_manifest else None,
                "status": status,
                "scenario_type": self.config.get("scenario_type"),
                "target_group": self.config.get("target_group"),
                "scenario_preset_id": self.config.get("scenario_preset_id"),
                "scenario_preset_name": self.config.get("scenario_preset_name"),
                "experiment_label": self.config.get("experiment_label"),
                "completed_cycles": self._completed_cycles,
                "requested_cycles": max_cycles,
                "actions_executed": self._actions_executed,
                "seed": self.config.get("seed"),
                "finished_at_local": now_display(),
                "finished_at_utc": now_iso_utc(),
                "last_message": self.last_message,
                "router_id": None,
                "router_name": None,
                "action": None,
                "remaining_seconds": 0.0,
            }
            self._append_event("scenario_finished", **summary)
            payload = dict(summary)
            payload.pop("status", None)
            self._update_state(status, **payload)
            self.finished_run.emit(summary)
        except Exception as e:
            message = str(e)
            if self.run_manifest:
                self._append_event("scenario_failed", error=message)
                self.last_message = message
                self._update_state("failed", error=message)
            self.failed_run.emit(message)




class MeasurementProbeThread(QThread):
    log_line = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    started_run = pyqtSignal(dict)
    progress = pyqtSignal(dict)
    finished_run = pyqtSignal(dict)
    failed_run = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = dict(config or {})
        self._running = True
        self._probe_seq = 0
        self._completed_probes = 0
        self.run_manifest = None
        self.last_message = "Not started."
        self.records = []
        self._previous_trace_signatures = {}
        self._phase5c_authoritative_chain_index = {}

    def stop(self):
        self._running = False

    def _append_probe(self, record):
        self._probe_seq += 1
        record["probe_seq"] = self._probe_seq
        record["ts_local"] = now_display()
        record["ts_utc"] = now_iso_utc()
        record["run_id"] = self.run_manifest.get("run_id") if self.run_manifest else None
        if self.run_manifest:
            append_jsonl(self.run_manifest["files"]["probes"], record)

    def _update_state(self, status, **extra):
        payload = {
            "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
            "run_dir": self.run_manifest.get("run_dir") if self.run_manifest else None,
            "status": status,
            "testnet_base": self.config.get("testnet_base"),
            "target_group": self.config.get("target_group"),
            "completed_probes": self._completed_probes,
            "requested_probes": len(self.config.get("routers", []) or []),
            "last_message": self.last_message,
            "updated_at_local": now_display(),
        }
        payload.update(extra)
        if self.run_manifest:
            write_json_atomic(self.run_manifest["files"]["state"], payload)
        self.progress.emit(payload)

    def _log(self, text):
        self.last_message = str(text)
        line = f"[{now_display()}] {text}"
        self.log_line.emit(line)
        self.status_changed.emit(text)

    def _filtered_inventory(self):
        target_group = str(self.config.get("target_group", "active_all")).strip()
        selected_router_id = str(self.config.get("selected_router_id", "")).strip()
        routers = list(self.config.get("routers", []))
        if target_group == "selected_only" and selected_router_id:
            routers = [r for r in routers if str(r.get("id")) == selected_router_id]
        elif target_group == "active_non_floodfill":
            routers = [r for r in routers if r.get("status") == "active" and not (str(r.get("floodfill", "")).lower() == "true")]
        elif target_group == "active_floodfill":
            routers = [r for r in routers if r.get("status") == "active" and (str(r.get("floodfill", "")).lower() == "true")]
        elif target_group == "active_all":
            routers = [r for r in routers if r.get("status") == "active"]
        return routers


    def run(self):
        try:
            inventory = self._filtered_inventory()
            if not inventory:
                raise RuntimeError("No eligible routers are available for the selected measurement target.")
            self.run_manifest = create_measurement_run_manifest(self.config.get("testnet_base"), self.config)
            self.started_run.emit(dict(self.run_manifest))
            self._update_state("running", requested_probes=len(inventory))
            timeout = float(self.config.get("fetch_timeout", MEASUREMENT_FETCH_TIMEOUT_DEFAULT))
            session_dir = self.config.get("telemetry_session_dir")
            self._previous_trace_signatures = load_recent_tunnel_trace_signatures()
            eepsite_target = discover_internal_eepsite_target(self.config.get("routers", []))
            if eepsite_target.get("target_url"):
                self._log(f"Discovered internal eepsite target {eepsite_target.get('target_url')} on {eepsite_target.get('router_name')}.")
            else:
                fixed_clients = [r for r in inventory if str(r.get("client_target_destination", "unknown")).strip().lower() not in {"", "unknown"}]
                if fixed_clients:
                    self._log("No internal eepsite target discovered. Client tunnels still look fixed-target; redeploy with the internal-eepsite setup script to enable application transaction probes.")
                else:
                    self._log("No internal eepsite target discovered. Client transaction probes will likely remain unavailable until an internal eepsite is present.")
            for router in inventory:
                if not self._running:
                    break
                rid = str(router.get("id"))
                router_name = router.get("name", f"Router {rid}")
                self._log(f"Probing {router_name} console endpoints.")
                endpoints = {
                    "root": probe_console_endpoint(router.get("console_host"), router.get("console_port"), "/", timeout=timeout),
                    "peers": probe_console_endpoint(router.get("console_host"), router.get("console_port"), "/peers", timeout=timeout),
                    "tunnels": probe_console_endpoint(router.get("console_host"), router.get("console_port"), "/tunnels", timeout=timeout),
                    "netdb": probe_console_endpoint(router.get("console_host"), router.get("console_port"), "/netdb", timeout=timeout),
                }
                proxy_target_url = eepsite_target.get("target_url") or router.get("client_target_url") or _i2p_url_from_host(router.get("measurement_eepsite_name")) or _i2p_url_from_host(router.get("server_spoofed_host"))
                client_proxy = probe_client_tunnel_proxy(router.get("namespace"), router.get("client_proxy_port"), timeout=timeout, target_url=proxy_target_url)
                tunnel_trace = build_tunnel_trace_snapshot(router, timeout=timeout, previous_signature=self._previous_trace_signatures.get(rid, ""))
                if tunnel_trace.get("signature"):
                    self._previous_trace_signatures[rid] = tunnel_trace.get("signature")
                latencies = [float((ep or {}).get("latency_ms") or 0.0) for ep in endpoints.values() if (ep or {}).get("success") and (ep or {}).get("latency_ms") is not None]
                if client_proxy.get("success") and client_proxy.get("latency_ms") is not None:
                    latencies.append(float(client_proxy.get("latency_ms") or 0.0))
                latest_startup = derive_latest_startup_metrics(session_dir, rid) if session_dir else {}
                record = {
                    "router_id": rid,
                    "router_name": router_name,
                    "status": router.get("status"),
                    "floodfill": str(router.get("floodfill", "")).lower() == "true",
                    "console_url": router.get("console_url", ""),
                    "router_ip": router.get("router_ip", ""),
                    "namespace": router.get("namespace", "unknown"),
                    "client_proxy_port": router.get("client_proxy_port", "unknown"),
                    "client_target_url": proxy_target_url,
                    "client_target_mode": "internal_eepsite" if eepsite_target.get("target_url") else ("fixed_target" if str(router.get("client_target_destination", "unknown")).strip().lower() not in {"", "unknown"} else "generic_proxy"),
                    "endpoints": endpoints,
                    "client_proxy": client_proxy,
                    "tunnel_trace": tunnel_trace,
                    "successful_endpoints": sum(1 for ep in endpoints.values() if (ep or {}).get("success")),
                    "mean_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
                    "latest_startup": latest_startup,
                }
                self.records.append(record)
                self._append_probe(record)
                if self.run_manifest:
                    trace_row = {
                        "router_id": rid,
                        "router_name": router_name,
                        "run_id": self.run_manifest.get("run_id"),
                        "target_url": proxy_target_url,
                        "client_proxy_success": bool(client_proxy.get("success")),
                        "client_proxy_latency_ms": client_proxy.get("latency_ms"),
                        "client_proxy_first_byte_ms": client_proxy.get("first_byte_ms"),
                        "trace": tunnel_trace,
                        "ts_local": now_display(),
                        "ts_utc": now_iso_utc(),
                    }
                    for _chain_key in ("exact_hop_chain", "hop_chain", "full_hop_chain", "hop_chain_names"):
                        _value = tunnel_trace.get(_chain_key)
                        if _value:
                            trace_row[_chain_key] = _value
                    append_jsonl(self.run_manifest["files"]["trace"], trace_row)
                self._completed_probes += 1
                self._update_state("running", current_router=router_name, completed_probes=self._completed_probes, requested_probes=len(inventory))
            status = "stopped" if not self._running else "completed"
            finished_local = now_display()
            summary = summarize_measurement_probes(self.records)
            scenario_corr = correlate_measurement_scenario(self.run_manifest.get("started_at_local") if self.run_manifest else finished_local, finished_local, self.config.get("testnet_base"), self.records)
            payload = {
                "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
                "run_dir": self.run_manifest.get("run_dir") if self.run_manifest else None,
                "status": status,
                "target_group": self.config.get("target_group"),
                "fetch_timeout": timeout,
                "finished_at_local": finished_local,
                "finished_at_utc": now_iso_utc(),
                "requested_probes": len(inventory),
                "completed_probes": self._completed_probes,
                "summary": summary,
                "scenario_correlation": scenario_corr,
                "eepsite_target": eepsite_target,
                "last_message": f"Measurement run {status}. Completed probes: {self._completed_probes}/{len(inventory)}.",
            }
            if self.run_manifest:
                write_json_atomic(self.run_manifest["files"]["summary"], payload)
            self.last_message = payload["last_message"]
            state_payload = dict(payload)
            state_payload.pop("status", None)
            self._update_state(status, current_router=None, **state_payload)
            self.finished_run.emit(payload)
        except Exception as e:
            message = str(e)
            if self.run_manifest:
                self.last_message = message
                self._update_state("failed", error=message)
            self.failed_run.emit(message)
class ScenarioCampaignThread(QThread):
    log_line = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    started_run = pyqtSignal(dict)
    progress = pyqtSignal(dict)
    finished_run = pyqtSignal(dict)
    failed_run = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    action_intent = pyqtSignal(str, str, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = dict(config or {})
        self._running = True
        self._event_seq = 0
        self.run_manifest = None
        self.run_dir = None
        self.last_message = "Not started."
        self.scenario_thread = None
        self._stage_measurements = []
        self._scenario_result = None
        self._baseline_result = None
        self._final_result = None
        self._interim_results = []
        self._cycle_trigger_count = 0
        self._periodic_trigger_count = 0

    def stop(self):
        self._running = False
        try:
            if self.scenario_thread and self.scenario_thread.isRunning():
                self.scenario_thread.stop()
        except Exception:
            pass

    def _append_event(self, event_type, **extra):
        self._event_seq += 1
        event = {
            "event_seq": self._event_seq,
            "ts_local": now_display(),
            "ts_utc": now_iso_utc(),
            "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
            "testnet_base": self.config.get("testnet_base"),
            "event_type": event_type,
            "experiment_label": self.config.get("experiment_label"),
            "scenario_preset_id": self.config.get("scenario_preset_id"),
            "scenario_preset_name": self.config.get("scenario_preset_name"),
            "scenario_type": (self.config.get("scenario_config") or {}).get("scenario_type"),
            "scenario_target_group": (self.config.get("scenario_config") or {}).get("target_group"),
            "measurement_target_group": (self.config.get("measurement_template") or {}).get("target_group"),
        }
        event.update(extra)
        if self.run_manifest:
            append_jsonl(self.run_manifest["files"]["events"], event)
        return event

    def _stage_counts(self):
        return {
            "baseline_run_id": (self._baseline_result or {}).get("run_id"),
            "final_run_id": (self._final_result or {}).get("run_id"),
            "interim_measurements": len(self._interim_results),
            "cycle_trigger_measurements": self._cycle_trigger_count,
            "periodic_measurements": self._periodic_trigger_count,
            "scenario_run_id": (self._scenario_result or {}).get("run_id"),
            "scenario_status": (self._scenario_result or {}).get("status"),
        }

    def _update_state(self, status, **extra):
        payload = {
            "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
            "run_dir": self.run_manifest.get("run_dir") if self.run_manifest else None,
            "status": status,
            "testnet_base": self.config.get("testnet_base"),
            "experiment_label": self.config.get("experiment_label"),
            "scenario_preset_id": self.config.get("scenario_preset_id"),
            "scenario_preset_name": self.config.get("scenario_preset_name"),
            "scenario_type": (self.config.get("scenario_config") or {}).get("scenario_type"),
            "scenario_target_group": (self.config.get("scenario_config") or {}).get("target_group"),
            "measurement_target_group": (self.config.get("measurement_template") or {}).get("target_group"),
            "fetch_timeout": (self.config.get("measurement_template") or {}).get("fetch_timeout"),
            "probe_interval_seconds": self.config.get("probe_interval_seconds", 0.0),
            "probe_after_each_cycle": bool(self.config.get("probe_after_each_cycle", True)),
            "post_settle_seconds": self.config.get("post_settle_seconds", 0.0),
            "last_message": self.last_message,
            "updated_at_local": now_display(),
        }
        payload.update(self._stage_counts())
        payload.update(extra)
        if self.run_manifest:
            write_json_atomic(self.run_manifest["files"]["state"], payload)
        self.progress.emit(payload)

    def _log(self, text, event_type=None, **extra):
        self.last_message = str(text)
        line = f"[{now_display()}] {text}"
        self.log_line.emit(line)
        self.status_changed.emit(text)
        if event_type:
            self._append_event(event_type, message=text, **extra)
        self._update_state("running")

    def _sleep_interruptible(self, seconds, phase, **extra):
        seconds = max(0.0, float(seconds))
        deadline = time.time() + seconds
        while self._running and time.time() < deadline:
            remaining = max(0.0, deadline - time.time())
            self._update_state(phase, remaining_seconds=round(remaining, 1), **extra)
            time.sleep(min(0.25, max(0.05, remaining)))
        self._update_state(phase, remaining_seconds=0.0, **extra)
        return self._running

    def _connect_subthread_common(self, thread_obj, prefix):
        thread_obj.log_line.connect(lambda line, p=prefix: self.log_line.emit(f"{p} {line}"))
        thread_obj.status_changed.connect(lambda msg, p=prefix: self.status_changed.emit(f"{p} {msg}"))

    def _resolve_scenario_result(self, scenario_started, scenario_finished, scenario_errors):
        thread = self.scenario_thread
        manifest = dict(getattr(thread, "run_manifest", None) or {}) if thread else {}
        if not manifest and scenario_started:
            manifest = dict(scenario_started[-1] or {})
        run_dir = manifest.get("run_dir") or getattr(thread, "run_dir", None)
        run_id = manifest.get("run_id") or ((scenario_started[-1] or {}).get("run_id") if scenario_started else None)
        files = dict(manifest.get("files") or {})
        state_path = files.get("state") or (os.path.join(run_dir, "state.json") if run_dir else None)
        events_path = files.get("events") or (os.path.join(run_dir, "events.jsonl") if run_dir else None)

        def _load_terminal_sources():
            state = read_json_file(state_path, default={}) if state_path else {}
            events = read_jsonl_records(events_path) if events_path and os.path.exists(events_path) else []
            finished_event = None
            failed_event = None
            cycle_count = 0
            action_count = 0
            for event in events:
                event_type = str(event.get("event_type") or "")
                if event_type == "cycle_complete":
                    cycle_count += 1
                elif event_type == "action_complete":
                    action_count += 1
            for event in reversed(events):
                event_type = str(event.get("event_type") or "")
                if finished_event is None and event_type == "scenario_finished":
                    finished_event = event
                if failed_event is None and event_type == "scenario_failed":
                    failed_event = event
                if finished_event and failed_event:
                    break
            return state or {}, finished_event or {}, failed_event or {}, cycle_count, action_count

        resolved = dict(scenario_finished[-1] or {}) if scenario_finished else {}
        state = {}
        finished_event = {}
        failed_event = {}
        cycle_count = 0
        action_count = 0

        deadline = time.time() + 8.0
        while True:
            state, finished_event, failed_event, cycle_count, action_count = _load_terminal_sources()
            merged = {}
            for source in (resolved or {}, finished_event or {}, state or {}):
                if source:
                    merged.update(source)
            status = str(merged.get("status") or "").strip().lower()
            if status in {"completed", "stopped"}:
                resolved = merged
                break
            if failed_event or str(state.get("status") or "").strip().lower() == "failed":
                error_text = failed_event.get("error") or state.get("error") or (scenario_errors[-1] if scenario_errors else "Scenario failed.")
                raise RuntimeError(str(error_text))
            if time.time() >= deadline:
                resolved = merged
                break
            time.sleep(0.2)

        if scenario_errors and not resolved:
            raise RuntimeError(scenario_errors[-1])

        completed_cycles = safe_int(
            resolved.get("completed_cycles", 0),
            safe_int(cycle_count, safe_int(getattr(thread, "_completed_cycles", 0) if thread else 0, 0)),
        )
        requested_cycles = safe_int(
            resolved.get("requested_cycles", 0),
            safe_int((getattr(thread, "config", {}) or {}).get("max_cycles", 0) if thread else 0, 0),
        )
        actions_executed = safe_int(
            resolved.get("actions_executed", 0),
            safe_int(action_count, safe_int(getattr(thread, "_actions_executed", 0) if thread else 0, 0)),
        )

        status = str(resolved.get("status") or "").strip().lower()
        if status not in {"completed", "stopped"}:
            if thread and not thread.isRunning():
                if requested_cycles > 0 and completed_cycles >= requested_cycles:
                    status = "completed"
                elif completed_cycles > 0 or not self._running:
                    status = "stopped" if not self._running else "completed"

        if status not in {"completed", "stopped"}:
            return None

        payload = {
            "run_id": resolved.get("run_id") or run_id,
            "run_dir": resolved.get("run_dir") or run_dir,
            "status": status,
            "scenario_type": resolved.get("scenario_type") or (self.config.get("scenario_config") or {}).get("scenario_type"),
            "target_group": resolved.get("target_group") or (self.config.get("scenario_config") or {}).get("target_group"),
            "scenario_preset_id": resolved.get("scenario_preset_id") or self.config.get("scenario_preset_id"),
            "scenario_preset_name": resolved.get("scenario_preset_name") or self.config.get("scenario_preset_name") or "Custom",
            "experiment_label": resolved.get("experiment_label") or self.config.get("experiment_label"),
            "completed_cycles": completed_cycles,
            "requested_cycles": requested_cycles,
            "actions_executed": actions_executed,
            "seed": resolved.get("seed") if resolved.get("seed") not in (None, "") else ((getattr(thread, "config", {}) or {}).get("seed") if thread else None),
            "finished_at_local": resolved.get("finished_at_local") or now_display(),
            "finished_at_utc": resolved.get("finished_at_utc") or now_iso_utc(),
            "last_message": resolved.get("last_message") or getattr(thread, "last_message", f"Scenario {status}. Completed cycles: {completed_cycles}/{requested_cycles}."),
            "router_id": resolved.get("router_id"),
            "router_name": resolved.get("router_name"),
            "action": resolved.get("action"),
            "remaining_seconds": 0.0,
        }
        return payload


    def _build_live_measurement_config(self):
        template = dict((self.config.get("measurement_template") or {}))
        routers = []
        for router in list(template.get("routers", []) or []):
            item = dict(router)
            rid = str(item.get("id"))
            info = get_service_show(rid)
            item["status"] = classify_router_status(info)
            routers.append(item)
        template["routers"] = routers
        return template

    def _run_inline_measurement(self, stage_label, trigger_reason, cycle_index=None):
        if not self._running:
            return None
        config = self._build_live_measurement_config()
        errors = []
        finished = []
        thread = MeasurementProbeThread(config, parent=None)
        self._connect_subthread_common(thread, f"[{stage_label}]")
        thread.finished_run.connect(lambda payload: finished.append(dict(payload or {})))
        thread.failed_run.connect(lambda message: errors.append(str(message)))
        self._log(f"Starting {stage_label} measurement probe.", event_type="campaign_measurement_begin", stage=stage_label, trigger_reason=trigger_reason, cycle_index=cycle_index)
        thread.run()
        if errors:
            raise RuntimeError(errors[-1])
        payload = finished[-1] if finished else None
        if payload is None:
            raise RuntimeError(f"{stage_label} measurement did not return a payload.")
        record = {
            "stage": stage_label,
            "trigger_reason": trigger_reason,
            "cycle_index": cycle_index,
            "run_id": payload.get("run_id"),
            "run_dir": payload.get("run_dir"),
            "status": payload.get("status"),
            "finished_at_local": payload.get("finished_at_local"),
            "summary": payload.get("summary") or {},
        }
        self._stage_measurements.append(record)
        self._append_event("campaign_measurement_complete", **record)
        self.refresh_requested.emit()
        self._update_state("running", latest_measurement_stage=stage_label, latest_measurement_run_id=payload.get("run_id"))
        return payload

    def _summarize_campaign(self):
        baseline_summary = (self._baseline_result or {}).get("summary") or {}
        final_summary = (self._final_result or {}).get("summary") or {}

        def metric(summary, key):
            return safe_int(summary.get(key, 0), 0)

        def metric_float(summary, key):
            value = summary.get(key)
            if value is None:
                return None
            try:
                return float(value)
            except Exception:
                return None

        worst_interim = None
        for item in self._interim_results:
            s = item.get("summary") or {}
            score = (metric(s, "client_proxy_success"), metric(s, "netdb_success"), -(metric_float(s, "mean_client_proxy_latency_ms") or 0.0))
            if worst_interim is None or score < worst_interim[0]:
                worst_interim = (score, item)

        return {
            "campaign_run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
            "experiment_label": self.config.get("experiment_label"),
            "scenario_preset_id": self.config.get("scenario_preset_id"),
            "scenario_preset_name": self.config.get("scenario_preset_name"),
            "scenario_run_id": (self._scenario_result or {}).get("run_id"),
            "scenario_status": (self._scenario_result or {}).get("status"),
            "baseline_run_id": (self._baseline_result or {}).get("run_id"),
            "final_run_id": (self._final_result or {}).get("run_id"),
            "interim_measurements": len(self._interim_results),
            "periodic_measurements": self._periodic_trigger_count,
            "cycle_trigger_measurements": self._cycle_trigger_count,
            "baseline_root_success": metric(baseline_summary, "root_success"),
            "baseline_netdb_success": metric(baseline_summary, "netdb_success"),
            "baseline_client_proxy_success": metric(baseline_summary, "client_proxy_success"),
            "final_root_success": metric(final_summary, "root_success"),
            "final_netdb_success": metric(final_summary, "netdb_success"),
            "final_client_proxy_success": metric(final_summary, "client_proxy_success"),
            "baseline_mean_proxy_latency_ms": metric_float(baseline_summary, "mean_client_proxy_latency_ms"),
            "final_mean_proxy_latency_ms": metric_float(final_summary, "mean_client_proxy_latency_ms"),
            "baseline_mean_root_latency_ms": metric_float(baseline_summary, "mean_root_latency_ms"),
            "final_mean_root_latency_ms": metric_float(final_summary, "mean_root_latency_ms"),
            "baseline_mean_netdb_latency_ms": metric_float(baseline_summary, "mean_netdb_latency_ms"),
            "final_mean_netdb_latency_ms": metric_float(final_summary, "mean_netdb_latency_ms"),
            "baseline_mean_proxy_first_byte_ms": metric_float(baseline_summary, "mean_client_proxy_first_byte_ms"),
            "final_mean_proxy_first_byte_ms": metric_float(final_summary, "mean_client_proxy_first_byte_ms"),
            "baseline_full_ready_routers": metric(baseline_summary, "full_ready_routers"),
            "final_full_ready_routers": metric(final_summary, "full_ready_routers"),
            "delta_root_success": metric(final_summary, "root_success") - metric(baseline_summary, "root_success"),
            "delta_netdb_success": metric(final_summary, "netdb_success") - metric(baseline_summary, "netdb_success"),
            "delta_client_proxy_success": metric(final_summary, "client_proxy_success") - metric(baseline_summary, "client_proxy_success"),
            "worst_interim": worst_interim[1] if worst_interim else None,
            "measurement_runs": list(self._stage_measurements),
        }

    def run(self):
        try:
            scenario_cfg = dict(self.config.get("scenario_config") or {})
            measurement_template = dict(self.config.get("measurement_template") or {})
            if not self.config.get("testnet_base"):
                raise RuntimeError("No active testnet base is available for campaign mode.")
            if not scenario_cfg.get("routers"):
                raise RuntimeError("No router inventory is available for campaign mode.")
            if not measurement_template.get("routers"):
                raise RuntimeError("No measurement router inventory is available for campaign mode.")

            self.run_manifest = create_campaign_run_manifest(self.config.get("testnet_base"), self.config)
            self.run_dir = self.run_manifest["run_dir"]
            self.started_run.emit(dict(self.run_manifest))
            self._append_event("campaign_started")
            self._log(f"Campaign started: scenario={scenario_cfg.get('scenario_type')} target={scenario_cfg.get('target_group')} | measurement={measurement_template.get('target_group')}.", event_type="campaign_started_message")

            self._baseline_result = self._run_inline_measurement("baseline", "pre_scenario")
            if not self._running:
                raise RuntimeError("Campaign stopped before the scenario stage began.")

            scenario_started = []
            scenario_finished = []
            scenario_errors = []
            self.scenario_thread = ChurnRunnerThread(scenario_cfg, parent=None)
            self._connect_subthread_common(self.scenario_thread, "[scenario]")
            self.scenario_thread.started_run.connect(lambda manifest: scenario_started.append(dict(manifest or {})))
            self.scenario_thread.progress.connect(lambda payload: self._update_state("running", scenario_progress=dict(payload or {})))
            self.scenario_thread.finished_run.connect(lambda payload: scenario_finished.append(dict(payload or {})))
            self.scenario_thread.failed_run.connect(lambda message: scenario_errors.append(str(message)))
            self.scenario_thread.refresh_requested.connect(self.refresh_requested.emit)
            self.scenario_thread.action_intent.connect(self.action_intent.emit)
            self.scenario_thread.start()

            scenario_run_dir = None
            interval_seconds = max(0.0, float(self.config.get("probe_interval_seconds", 0.0)))
            next_periodic = time.time() + interval_seconds if interval_seconds > 0 else None
            last_cycle_probe_seq = 0
            probe_after_each_cycle = bool(self.config.get("probe_after_each_cycle", True))
            events_path = None

            while self._running and self.scenario_thread.isRunning():
                manifest = dict(getattr(self.scenario_thread, "run_manifest", None) or {})
                if not manifest and scenario_started:
                    manifest = dict(scenario_started[-1] or {})
                if manifest and not scenario_run_dir:
                    scenario_run_dir = manifest.get("run_dir") or getattr(self.scenario_thread, "run_dir", None)
                    if scenario_run_dir:
                        events_path = os.path.join(scenario_run_dir, "events.jsonl")
                        self._update_state("running", scenario_run_id=manifest.get("run_id"), scenario_run_dir=scenario_run_dir)

                if probe_after_each_cycle and events_path and os.path.exists(events_path):
                    cycle_events = [e for e in read_jsonl_records(events_path) if str(e.get("event_type")) == "cycle_complete"]
                    if cycle_events:
                        newest_seq = max(safe_int(e.get("event_seq", 0), 0) for e in cycle_events)
                        if newest_seq > last_cycle_probe_seq:
                            target_event = sorted(cycle_events, key=lambda e: safe_int(e.get("event_seq", 0), 0))[-1]
                            last_cycle_probe_seq = newest_seq
                            self._cycle_trigger_count += 1
                            self._interim_results.append(self._run_inline_measurement(f"cycle-{safe_int(target_event.get('cycle_index', len(self._interim_results) + 1), len(self._interim_results) + 1)}", "cycle_complete", cycle_index=safe_int(target_event.get("cycle_index", 0), 0) or None))
                            if next_periodic is not None:
                                next_periodic = time.time() + interval_seconds

                if next_periodic is not None and time.time() >= next_periodic:
                    self._periodic_trigger_count += 1
                    self._interim_results.append(self._run_inline_measurement(f"periodic-{self._periodic_trigger_count}", "periodic_timer"))
                    next_periodic = time.time() + interval_seconds

                time.sleep(0.25)

            if self.scenario_thread:
                self.scenario_thread.wait(3000)
            self._scenario_result = self._resolve_scenario_result(scenario_started, scenario_finished, scenario_errors)
            if not self._scenario_result:
                raise RuntimeError("Scenario stage did not complete cleanly.")

            settle_seconds = max(0.0, float(self.config.get("post_settle_seconds", 0.0)))
            if settle_seconds > 0 and self._running:
                self._log(f"Waiting {format_seconds_brief(settle_seconds)} before the final post-scenario measurement.", event_type="campaign_post_settle_wait")
                self._sleep_interruptible(settle_seconds, "post_settle")

            if self._running:
                self._final_result = self._run_inline_measurement("post", "post_scenario")

            status = "stopped" if not self._running else "completed"
            summary = self._summarize_campaign()
            payload = {
                "run_id": self.run_manifest.get("run_id") if self.run_manifest else None,
                "run_dir": self.run_manifest.get("run_dir") if self.run_manifest else None,
                "status": status,
                "finished_at_local": now_display(),
                "finished_at_utc": now_iso_utc(),
                "last_message": f"Campaign {status}. Baseline={summary.get('baseline_run_id') or 'n/a'} | final={summary.get('final_run_id') or 'n/a'} | interim={summary.get('interim_measurements', 0)}.",
                "summary": summary,
            }
            payload.update(self._stage_counts())
            if self.run_manifest:
                write_json_atomic(self.run_manifest["files"]["summary"], payload)
            self.last_message = payload["last_message"]
            state_payload = dict(payload)
            state_payload.pop("status", None)
            self._append_event("campaign_finished", status=status, summary=summary)
            self._update_state(status, **state_payload)
            self.finished_run.emit(payload)
        except Exception as e:
            message = str(e)
            if self.run_manifest:
                self.last_message = message
                self._append_event("campaign_failed", error=message)
                self._update_state("failed", error=message)
            self.failed_run.emit(message)


class DeployThread(QThread):
    line = pyqtSignal(str)
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, action, routers=None, floodfill=None, routers_tsv=None, subnets_tsv=None, parent=None):
        super().__init__(parent)
        self.action = action
        self.routers = routers
        self.floodfill = floodfill
        self.routers_tsv = routers_tsv
        self.subnets_tsv = subnets_tsv

    def emit_log(self, text):
        self.line.emit(text)
        deployment_log_write(text)

    def run(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)

            if self.action in {"deploy", "rebuild"}:
                if self.action == "rebuild":
                    deployment_log_reset()
                    self.emit_log("Rebuild requested.")
                    destroy_emulator_runtime()
                elif not (self.routers_tsv and self.subnets_tsv):
                    deployment_log_reset()
                    self.emit_log("Deploy requested.")

                script_path = resolve_deploy_script_path()
                if not os.path.exists(script_path):
                    raise RuntimeError(f"Setup script not found: {script_path}")
                if not os.access(script_path, os.X_OK):
                    os.chmod(script_path, 0o755)

                if self.routers_tsv and self.subnets_tsv:
                    cmd = [
                        "bash", script_path,
                        "--routers-tsv", str(self.routers_tsv),
                        "--subnets-tsv", str(self.subnets_tsv),
                        "--yes",
                    ]
                    self.emit_log(f"Running setup script: {script_path}")
                    self.emit_log(f"Requested topology TSV deploy: routers_tsv={self.routers_tsv}, subnets_tsv={self.subnets_tsv}")
                else:
                    cmd = ["bash", script_path, "--routers", str(self.routers), "--floodfill", str(self.floodfill), "--yes"]
                    self.emit_log(f"Running setup script: {script_path}")
                    self.emit_log(f"Requested topology: routers={self.routers}, floodfill={self.floodfill}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert process.stdout is not None

                for raw in process.stdout:
                    self.emit_log(raw.rstrip("\n"))

                rc = process.wait()
                if rc != 0:
                    raise RuntimeError(f"Setup script failed with exit code {rc}")

                self.done.emit("Deployment completed successfully.")
                return

            if self.action == "stop_emulator":
                deployment_log_reset()
                self.emit_log("Stop emulator requested.")
                stop_emulator_runtime()
                self.done.emit("Emulator stopped successfully.")
                return

            if self.action == "destroy":
                deployment_log_reset()
                self.emit_log("Destroy emulator requested.")
                destroy_emulator_runtime()
                self.done.emit("Emulator destroyed successfully.")
                return

            raise RuntimeError(f"Unknown deployment action: {self.action}")

        except Exception as e:
            self.failed.emit(str(e))


class StatPill(QLabel):
    def __init__(self, title, value="0", parent=None):
        super().__init__(parent)
        self.title = title
        self.setObjectName("StatPill")
        self.setTextFormat(Qt.TextFormat.RichText if PYQT_VER == 6 else Qt.RichText)
        self.set_value(value)

    def set_value(self, value):
        self.setText(
            f"<div style='font-size:11px;color:#8ea7d1;letter-spacing:0.4px'>{self.title}</div>"
            f"<div style='font-size:24px;font-weight:800;color:#f8fafc'>{value}</div>"
        )



class RouterCard(QFrame):
    selected = pyqtSignal(str)
    action_requested = pyqtSignal(str, str)
    open_console_requested = pyqtSignal(str)

    def __init__(self, router, parent=None):
        super().__init__(parent)
        self.router_id = router["id"]
        self._selected = False
        self.setObjectName("RouterCard")
        self.setFrameShape(QFrame.Shape.StyledPanel if PYQT_VER == 6 else QFrame.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor if PYQT_VER == 6 else Qt.PointingHandCursor)
        self.setMinimumWidth(320)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding if PYQT_VER == 6 else QSizePolicy.Expanding,
            QSizePolicy.Policy.Fixed if PYQT_VER == 6 else QSizePolicy.Fixed
    )

        self.title = QLabel()
        self.title.setObjectName("CardTitle")

        self.status_badge = QLabel()
        self.status_badge.setObjectName("StatusBadge")

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.status_badge)

        self.line1 = QLabel()
        self.line2 = QLabel()
        self.line3 = QLabel()
        self.line4 = QLabel()
        for lbl in (self.line1, self.line2, self.line3, self.line4):
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#c8d4ea;font-size:12px;line-height:1.35;")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_restart = QPushButton("Restart")
        self.btn_console = QPushButton("Console")

        for b in (self.btn_start, self.btn_stop, self.btn_restart, self.btn_console):
            b.setCursor(Qt.CursorShape.PointingHandCursor if PYQT_VER == 6 else Qt.PointingHandCursor)
            b.setMinimumHeight(36)
            btn_row.addWidget(b)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(top)
        layout.addSpacing(2)
        layout.addWidget(self.line1)
        layout.addWidget(self.line2)
        layout.addWidget(self.line3)
        layout.addWidget(self.line4)
        layout.addStretch(1)
        layout.addLayout(btn_row)

        self.btn_start.clicked.connect(lambda: self.action_requested.emit("start", self.router_id))
        self.btn_stop.clicked.connect(lambda: self.action_requested.emit("stop", self.router_id))
        self.btn_restart.clicked.connect(lambda: self.action_requested.emit("restart", self.router_id))
        self.btn_console.clicked.connect(lambda: self.open_console_requested.emit(self.router_id))

        self.update_data(router)
        self.set_selected(False)

    def mousePressEvent(self, event):
        self.selected.emit(self.router_id)
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self._selected = bool(selected)
        self.setProperty("selected", self._selected)
        if PYQT_VER == 6:
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            self.style().unpolish(self)
            self.style().polish(self)
        self.update()

    def set_actions_enabled(self, enabled):
        for button in (self.btn_start, self.btn_stop, self.btn_restart):
            button.setEnabled(enabled and button.property("routerActionAllowed") is not False)
        self.btn_console.setEnabled(enabled)

    def update_data(self, router):
        self.router_id = router["id"]
        m = router["metrics"]
        ff = "FF" if str(router.get("floodfill", "")).lower() == "true" else "Router"
        self.title.setText(f"{router['name']} <span style='color:#7f96bb;font-weight:500'>· {ff}</span>")

        self.line1.setText(
            f"Peers: <b>{m['peer_count']}</b>  |  Active: <b>{m['peer_active']}</b>  |  "
            f"Fast: <b>{m['peer_fast']}</b>  |  Known: <b>{m['peer_known']}</b>"
        )
        self.line2.setText(
            f"Tunnels: <b>{m['tunnel_count']}</b>  |  Exploratory: <b>{m['tunnel_exploratory']}</b>  |  "
            f"Client: <b>{m['tunnel_client']}</b>  |  Part.: <b>{m['tunnel_participating']}</b>"
        )
        self.line3.setText(
            f"Reachability: <b>{m['reachability']}</b>  |  Acceptance: <b>{m['tunnel_acceptance']}</b>"
        )
        self.line4.setText(
            f"IP: <b>{router.get('router_ip', 'unknown')}</b>  |  Subnet: <b>{router['parsed'].get('subnet', 'unknown')}</b>  |  Uptime: <b>{m['uptime']}</b>"
        )

        status = router["status"]
        colors = {
            "active": ("#16a34a", "#dcfce7"),
            "starting": ("#ca8a04", "#fef9c3"),
            "stopping": ("#ea580c", "#ffedd5"),
            "stopped": ("#475569", "#e2e8f0"),
            "failed": ("#dc2626", "#fee2e2"),
            "unknown": ("#334155", "#e2e8f0"),
        }
        bg, fg = colors.get(status, colors["unknown"])
        self.status_badge.setText(status.upper())
        self.status_badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:14px; "
            f"padding:5px 12px; font-size:11px; font-weight:800; letter-spacing:0.5px;"
        )

        is_stopped = status in {"stopped", "stopping", "failed"}
        is_running = status in {"active", "starting"}

        self.btn_start.setProperty("routerActionAllowed", not is_running)
        self.btn_stop.setProperty("routerActionAllowed", not is_stopped)
        self.btn_restart.setProperty("routerActionAllowed", not is_stopped)
        self.btn_start.setEnabled(not is_running)
        self.btn_stop.setEnabled(not is_stopped)
        self.btn_restart.setEnabled(not is_stopped)

        self.btn_start.setToolTip("Start this router")
        self.btn_stop.setToolTip("Stop this router")
        self.btn_restart.setToolTip("Restart this router")
        self.btn_console.setToolTip("Open the router console in your browser")



class TopologyCanvas(QWidget):
    router_selected = pyqtSignal(str)

    STATUS_COLORS = {
        "active": ("#16a34a", "#dcfce7"),
        "starting": ("#ca8a04", "#fef9c3"),
        "stopping": ("#ea580c", "#ffedd5"),
        "stopped": ("#475569", "#e2e8f0"),
        "failed": ("#dc2626", "#fee2e2"),
        "unknown": ("#334155", "#e2e8f0"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(TOPOLOGY_MIN_HEIGHT)
        self.setMouseTracking(True)
        self.routers = []
        self.selected_router_id = None
        self.node_regions = []
        self.legend_height = 58
        self._hover_router_id = None

    def set_snapshot(self, routers, selected_router_id=None):
        self.routers = list(routers or [])
        self.selected_router_id = str(selected_router_id) if selected_router_id else None
        self.update()

    def _status_brush(self, status):
        bg, _ = self.STATUS_COLORS.get(status, self.STATUS_COLORS["unknown"])
        return QBrush(QColor(bg))

    def _status_text_color(self, status):
        _, fg = self.STATUS_COLORS.get(status, self.STATUS_COLORS["unknown"])
        return QColor(fg)

    def _compute_node_layout(self):
        rect = self.rect().adjusted(18, 18, -18, -18)
        rect.setTop(rect.top() + self.legend_height)
        routers = self.routers
        if not routers or rect.width() <= 0 or rect.height() <= 0:
            return []

        ordered = sorted(
            routers,
            key=lambda r: (
                0 if str(r.get("floodfill", "")).lower() == "true" else 1,
                0 if r.get("status") == "active" else 1,
                safe_int(r.get("id"), 9999),
            ),
        )

        ff = [r for r in ordered if str(r.get("floodfill", "")).lower() == "true"]
        regular = [r for r in ordered if str(r.get("floodfill", "")).lower() != "true"]
        cx = rect.center().x()
        cy = rect.center().y() + 10
        max_radius = max(90.0, min(rect.width(), rect.height()) / 2.0 - 42.0)
        inner_radius = min(110.0, max_radius * 0.42)
        outer_radius = max(inner_radius + 70.0, max_radius * 0.82)
        node_radius = 26.0 if len(ordered) <= 12 else 22.0 if len(ordered) <= 24 else 18.0
        layouts = []

        def ring_positions(group, radius, angle_offset=-1.57079632679):
            if not group:
                return []
            if len(group) == 1:
                return [(group[0], QPointF(cx, cy))]
            step = (2.0 * 3.141592653589793) / len(group)
            pos = []
            for i, router in enumerate(group):
                ang = angle_offset + i * step
                x = cx + radius * __import__('math').cos(ang)
                y = cy + radius * __import__('math').sin(ang)
                pos.append((router, QPointF(x, y)))
            return pos

        if ff:
            if len(ff) == 1:
                layouts.append((ff[0], QPointF(cx, cy), node_radius + 6.0, True))
            else:
                for router, pos in ring_positions(ff, inner_radius):
                    layouts.append((router, pos, node_radius + 5.0, True))

        if regular:
            for router, pos in ring_positions(regular, outer_radius):
                layouts.append((router, pos, node_radius, False))

        return layouts

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing if PYQT_VER == 6 else QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#020915"))

        title_rect = QRectF(18, 12, self.width() - 36, 28)
        painter.setPen(QColor("#f8fbff"))
        title_font = painter.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(title_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if PYQT_VER == 6 else int(Qt.AlignLeft | Qt.AlignVCenter), "Topology View")

        subtitle_rect = QRectF(18, 32, self.width() - 36, 24)
        subtitle_font = painter.font()
        subtitle_font.setPointSize(9)
        subtitle_font.setBold(False)
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#8ea7d1"))
        painter.drawText(subtitle_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if PYQT_VER == 6 else int(Qt.AlignLeft | Qt.AlignVCenter), "Routers are rendered from the live emulator snapshot. Click any node to select it.")

        if not self.routers:
            painter.setPen(QColor("#8ea7d1"))
            empty_font = painter.font()
            empty_font.setPointSize(11)
            painter.setFont(empty_font)
            painter.drawText(self.rect().adjusted(0, 50, 0, 0), int(Qt.AlignmentFlag.AlignCenter) if PYQT_VER == 6 else int(Qt.AlignCenter), "No routers detected. Deploy or refresh the emulator to populate the topology.")
            return

        layouts = self._compute_node_layout()
        self.node_regions = []

        ff_positions = [pos for router, pos, radius, is_ff in layouts if is_ff]
        regular_positions = [pos for router, pos, radius, is_ff in layouts if not is_ff]

        painter.setPen(QPen(QColor("#193157"), 1.2))
        if ff_positions and regular_positions:
            for src in ff_positions:
                for dst in regular_positions:
                    painter.drawLine(src, dst)
        elif len(regular_positions) > 1:
            for i in range(len(regular_positions)):
                painter.drawLine(regular_positions[i], regular_positions[(i + 1) % len(regular_positions)])

        if len(ff_positions) > 1:
            painter.setPen(QPen(QColor("#3a6df7"), 1.6))
            for i in range(len(ff_positions)):
                painter.drawLine(ff_positions[i], ff_positions[(i + 1) % len(ff_positions)])

        for router, center, radius, is_ff in layouts:
            router_id = str(router["id"])
            status = router.get("status", "unknown")
            metrics = router.get("metrics", {})
            is_selected = router_id == self.selected_router_id
            border_color = QColor("#60a5fa") if is_selected else QColor("#1d4ed8" if is_ff else "#1a2a4a")
            border_width = 3.2 if is_selected else 2.0 if is_ff else 1.4
            rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)

            if is_selected:
                painter.setPen(Qt.PenStyle.NoPen if PYQT_VER == 6 else Qt.NoPen)
                painter.setBrush(QColor(58, 109, 247, 60))
                glow = QRectF(rect.x() - 8, rect.y() - 8, rect.width() + 16, rect.height() + 16)
                painter.drawEllipse(glow)

            painter.setPen(QPen(border_color, border_width))
            painter.setBrush(self._status_brush(status))
            painter.drawEllipse(rect)

            if is_ff:
                painter.setPen(QPen(QColor("#facc15"), 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush if PYQT_VER == 6 else Qt.NoBrush)
                ring = QRectF(rect.x() - 6, rect.y() - 6, rect.width() + 12, rect.height() + 12)
                painter.drawEllipse(ring)

            painter.setPen(self._status_text_color(status))
            id_font = painter.font()
            id_font.setPointSize(11)
            id_font.setBold(True)
            painter.setFont(id_font)
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter) if PYQT_VER == 6 else int(Qt.AlignCenter), f"R{router_id}")

            label_rect = QRectF(rect.x() - 34, rect.bottom() + 8, rect.width() + 68, 34)
            painter.setPen(QColor("#dbe7fb"))
            label_font = painter.font()
            label_font.setPointSize(8)
            label_font.setBold(True)
            painter.setFont(label_font)
            painter.drawText(label_rect, int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop) if PYQT_VER == 6 else int(Qt.AlignHCenter | Qt.AlignTop), f"{router['name']}\n{status.upper()} · Peers {metrics.get('peer_count', '0')}")

            self.node_regions.append((router_id, rect, router))

        legend_y = self.height() - 32
        painter.setFont(subtitle_font)
        items = [
            ("Active", QColor("#16a34a")),
            ("Starting", QColor("#ca8a04")),
            ("Stopped", QColor("#475569")),
            ("Failed", QColor("#dc2626")),
            ("Floodfill Ring", QColor("#facc15")),
        ]
        x = 18
        for label, color in items:
            painter.setPen(Qt.PenStyle.NoPen if PYQT_VER == 6 else Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QRectF(x, legend_y, 10, 10))
            painter.setPen(QColor("#c8d4ea"))
            painter.drawText(QRectF(x + 16, legend_y - 7, 92, 24), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if PYQT_VER == 6 else int(Qt.AlignLeft | Qt.AlignVCenter), label)
            x += 108

    def _router_at(self, pos):
        for router_id, rect, router in reversed(self.node_regions):
            if rect.contains(pos):
                return router_id, router
        return None, None

    def mousePressEvent(self, event):
        point = event.position() if PYQT_VER == 6 else event.posF() if hasattr(event, 'posF') else event.pos()
        router_id, _ = self._router_at(point)
        if router_id:
            self.router_selected.emit(router_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        point = event.position() if PYQT_VER == 6 else event.posF() if hasattr(event, 'posF') else event.pos()
        router_id, router = self._router_at(point)
        if router_id and router:
            if router_id != self._hover_router_id:
                self._hover_router_id = router_id
                m = router.get("metrics", {})
                self.setToolTip(
                    f"{router['name']}\n"
                    f"Status: {router.get('status', 'unknown').upper()}\n"
                    f"Floodfill: {router.get('floodfill', 'unknown')}\n"
                    f"Peers: {m.get('peer_count', '0')} (active {m.get('peer_active', '0')})\n"
                    f"Tunnels: {m.get('tunnel_count', '0')}\n"
                    f"Reachability: {m.get('reachability', 'unknown')}\n"
                    f"IP/Subnet: {router.get('router_ip', 'unknown')} / {router['parsed'].get('subnet', 'unknown')}\n"
                    f"Console: {router.get('console_url', 'unknown')}"
                )
        else:
            self._hover_router_id = None
            self.setToolTip("")
        super().mouseMoveEvent(event)



class RouterMapPage(QWebEnginePage if WEBENGINE_AVAILABLE else object):
    router_selected = pyqtSignal(str)
    console_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        if WEBENGINE_AVAILABLE:
            super().__init__(parent)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if WEBENGINE_AVAILABLE:
            scheme = url.scheme().lower()
            if scheme == "i2prouter":
                action = (url.host() or "").strip().lower()
                router_id = (url.path() or "").strip("/")
                if action == "select" and router_id:
                    self.router_selected.emit(router_id)
                elif action == "console" and router_id:
                    self.console_requested.emit(router_id)
                return False
            return super().acceptNavigationRequest(url, nav_type, is_main_frame)
        return True


class LeafletMapPanel(QFrame):
    router_selected = pyqtSignal(str)
    console_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopologyPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.summary = QLabel("Network map summary will appear here.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color:#8ea7d1;font-size:12px;")
        layout.addWidget(self.summary)

        self._web_loaded = False
        self._pending_payload = None
        self._last_payload_json = ""
        self._payload_seq = 0

        if WEBENGINE_AVAILABLE:
            self.map_view = QWebEngineView(self)
            self.map_page = RouterMapPage(self.map_view)
            self.map_page.router_selected.connect(self.router_selected)
            self.map_page.console_requested.connect(self.console_requested)
            self.map_view.setPage(self.map_page)
            self.map_view.loadFinished.connect(self._on_load_finished)
            layout.addWidget(self.map_view, 1)
            self.map_view.setHtml(self._build_leaflet_html("null"), QUrl("https://local.i2p.testnet/"))
        else:
            self.map_view = None
            self.map_page = None
            self.fallback = QLabel(
                "Qt WebEngine is not available, so the real Leaflet world map cannot be shown.\n"
                "Install the Qt WebEngine package for your PyQt version, then reopen the GUI."
            )
            self.fallback.setWordWrap(True)
            self.fallback.setAlignment(Qt.AlignmentFlag.AlignTop if PYQT_VER == 6 else Qt.AlignTop)
            self.fallback.setStyleSheet("color:#c9d8f5;padding:18px;font-size:14px;")
            layout.addWidget(self.fallback, 1)

    def _build_leaflet_html(self, initial_payload_json="null"):
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>I2P Testnet Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
 integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
html, body, #map {{ height: 100%; margin: 0; background: #081120; color: #e5edf9; }}
.leaflet-container {{ background: #081120; font-family: Segoe UI, Inter, Arial, sans-serif; }}
:root {{ --hud-bg: rgba(8,17,32,.68); --hud-border: rgba(147,197,253,.18); --hud-text:#dbe7fb; }}
.reset-view-btn {{
  position:absolute; z-index:1000; right:12px; top:12px; background:rgba(37,99,235,.92);
  border:1px solid rgba(147,197,253,.35); border-radius:10px; padding:7px 10px; font-size:12px;
  color:#fff; cursor:pointer; box-shadow:0 8px 24px rgba(0,0,0,.22); user-select:none;
}}
.reset-view-btn:hover {{ background:rgba(29,78,216,.96); }}
.country-label-pill {{
  color:#0f172a; font-weight:800; font-size:13px; background:rgba(255,255,255,.90);
  border:1px solid rgba(15,23,42,.18); padding:2px 8px; border-radius:999px;
  box-shadow:0 3px 10px rgba(0,0,0,.12); white-space:nowrap;
}}
.map-legend, .map-controls {{
  background:var(--hud-bg);
  border:1px solid var(--hud-border);
  color:var(--hud-text);
  box-shadow:0 10px 24px rgba(0,0,0,.16);
  backdrop-filter: blur(5px);
}}
.map-legend {{
  position:absolute; z-index:1000; left:12px; bottom:12px;
  border-radius:12px; padding:8px 10px; min-width:184px; max-width:206px;
  max-height:34vh; overflow:auto;
}}
.map-panel-header {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
.map-panel-toggle {{
  border:1px solid rgba(147,197,253,.22); background:rgba(37,99,235,.18); color:#eaf2ff;
  border-radius:8px; padding:2px 7px; font-size:10px; font-weight:800; cursor:pointer;
}}
.map-legend-title, .map-controls-title {{ font-size:11px; font-weight:800; margin:0; color:#f8fbff; }}
.map-panel-body {{ margin-top:6px; }}
.map-panel-body.collapsed {{ display:none; }}
.map-legend-section {{ margin-top:8px; padding-top:8px; border-top:1px solid rgba(148,163,184,.18); }}
.map-legend-section:first-of-type {{ margin-top:0; padding-top:0; border-top:none; }}
.map-legend-section-title {{ font-size:9px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:#93c5fd; margin-bottom:4px; }}
.map-legend-row {{ display:flex; align-items:center; gap:8px; font-size:10px; color:#c8d4ea; margin:4px 0; }}
.map-legend-line {{ width:30px; height:0; border-top-width:3px; border-top-style:solid; display:inline-block; }}
.map-legend-line.subnet {{ border-top-color:#f59e0b; opacity:.9; }}
.map-legend-line.backbone {{ border-top-color:#60a5fa; border-top-style:dashed; opacity:.95; }}
.map-legend-line.peer {{ border-top-color:#22c55e; opacity:.95; }}
.map-legend-swatch {{ width:16px; height:16px; border-radius:999px; display:inline-block; border:2px solid transparent; }}
.map-legend-swatch.exploratory {{ border-color:#a855f7; background:rgba(168,85,247,.12); }}
.map-legend-swatch.client {{ border-color:#06b6d4; background:rgba(6,182,212,.12); }}
.map-legend-swatch.participating {{ border-color:#ec4899; background:rgba(236,72,153,.12); }}
.map-legend-swatch.mixed {{ border-color:#e5e7eb; background:rgba(229,231,235,.12); }}
.map-controls {{
  position:absolute; z-index:1000; left:60px; top:12px;
  border-radius:12px; padding:8px 10px; min-width:184px; max-width:206px;
  max-height:32vh; overflow:auto; pointer-events:auto;
}}
.map-controls-subtitle {{ font-size:9px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:#93c5fd; margin:4px 0 4px; }}
.map-control-row {{ display:flex; align-items:center; gap:7px; margin:4px 0; font-size:10px; color:#c8d4ea; cursor:pointer; user-select:none; }}
.map-control-row input {{ accent-color:#3a6df7; }}
.selected-router-card {{
  position:absolute; z-index:1000; right:12px; top:56px; width:296px; max-width:33vw; max-height:70vh;
  overflow:auto; background:rgba(255,255,255,.93); color:#0f172a; border-radius:14px; padding:12px 13px;
  box-shadow:0 10px 22px rgba(0,0,0,.18); border:1px solid rgba(15,23,42,.10); backdrop-filter: blur(4px);
}}
.selected-router-header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }}
.selected-router-title {{ font-weight:800; font-size:14px; }}
.selected-router-badge {{ border-radius:999px; padding:4px 10px; font-size:11px; font-weight:800; color:#fff; }}
.selected-router-badge.active {{ background:#22c55e; }}
.selected-router-badge.starting {{ background:#f59e0b; }}
.selected-router-badge.failed {{ background:#ef4444; }}
.selected-router-badge.stopped, .selected-router-badge.stopping, .selected-router-badge.unknown {{ background:#64748b; }}
.selected-router-grid {{ font-size:11px; line-height:1.35; }}
.selected-router-section {{ margin-top:8px; padding-top:8px; border-top:1px solid rgba(15,23,42,.08); }}
.selected-router-section-title {{ font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; color:#475569; margin-bottom:5px; }}
.selected-router-chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:5px 0 7px; }}
.selected-router-chip {{ display:inline-block; padding:2px 7px; border-radius:999px; font-size:9px; font-weight:800; background:rgba(15,23,42,.06); color:#0f172a; }}
.selected-router-note {{ color:#64748b; font-size:10px; margin-top:5px; }}
.selected-router-actions {{ margin-top:10px; display:flex; gap:8px; }}
.selected-router-btn {{ display:inline-block; background:#2563eb; color:#fff !important; text-decoration:none; padding:6px 10px; border-radius:9px; font-size:11px; font-weight:700; }}
.selected-router-btn.secondary {{ background:#0f172a; }}
.leaflet-top.leaflet-left {{ top: 12px; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="map-controls" id="map-controls-panel">
  <div class="map-panel-header"><div class="map-controls-title">Layers</div><button id="toggle-controls-panel" class="map-panel-toggle" type="button">Hide</button></div>
  <div class="map-panel-body" id="map-controls-body">
    <label class="map-control-row"><input id="toggle-subnet-links" type="checkbox" checked> Subnet links</label>
    <label class="map-control-row"><input id="toggle-backbone-links" type="checkbox" checked> Floodfill backbone</label>
    <label class="map-control-row"><input id="toggle-peer-links" type="checkbox" checked> Live peer links</label>
    <label class="map-control-row"><input id="toggle-tunnel-activity" type="checkbox" checked> Tunnel activity</label>
    <label class="map-control-row"><input id="toggle-phase3-overlay" type="checkbox" checked> Phase 3 overlay</label>
    <label class="map-control-row"><input id="toggle-inferred-links" type="checkbox" checked> Inferred links</label>
    <label class="map-control-row"><input id="toggle-phase4-trace" type="checkbox" checked> Phase 4 hints</label>
    <label class="map-control-row"><input id="toggle-focus-selected" type="checkbox"> Focus selected</label>
  </div>
</div>
<div class="reset-view-btn" onclick="window.resetRouterMapView()">Reset View</div>
<div id="selected-router-card"></div>
<div class="map-legend" id="map-legend-panel">
  <div class="map-panel-header"><div class="map-legend-title">Legend</div><button id="toggle-legend-panel" class="map-panel-toggle" type="button">Show</button></div>
  <div class="map-panel-body collapsed" id="map-legend-body">
    <div class="map-legend-section">
      <div class="map-legend-section-title">Topology</div>
      <div class="map-legend-row"><span class="map-legend-line subnet"></span><span>Subnet</span></div>
      <div class="map-legend-row"><span class="map-legend-line backbone"></span><span>Backbone</span></div>
      <div class="map-legend-row"><span class="map-legend-line peer"></span><span>Peer link</span></div>
      <div class="map-legend-row"><span class="map-legend-line" style="border-top-color:#e879f9;border-top-style:dashed;"></span><span>Inferred path</span></div>
    </div>
    <div class="map-legend-section">
      <div class="map-legend-section-title">Phase 3</div>
      <div class="map-legend-row"><span class="map-legend-swatch" style="border-color:#22c55e;background:rgba(34,197,94,.12);"></span><span>Stable</span></div>
      <div class="map-legend-row"><span class="map-legend-swatch" style="border-color:#f59e0b;background:rgba(245,158,11,.12);"></span><span>Watch</span></div>
      <div class="map-legend-row"><span class="map-legend-swatch" style="border-color:#ef4444;background:rgba(239,68,68,.12);"></span><span>Unstable</span></div>
    </div>
    <div class="map-legend-section">
      <div class="map-legend-section-title">Phase 4 + activity</div>
      <div class="map-legend-row"><span class="map-legend-swatch" style="border-color:#f43f5e;background:rgba(244,63,94,.18);width:12px;height:12px;"></span><span>P4 marker</span></div>
      <div class="map-legend-row"><span class="map-legend-swatch exploratory"></span><span>Exploratory</span></div>
      <div class="map-legend-row"><span class="map-legend-swatch client"></span><span>Client</span></div>
      <div class="map-legend-row"><span class="map-legend-swatch participating"></span><span>Participating</span></div>
      <div class="map-legend-row"><span class="map-legend-swatch mixed"></span><span>Mixed</span></div>
    </div>
  </div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
 integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
const INITIAL_PAYLOAD = {initial_payload_json};
const STORAGE_KEY = 'i2p-testnet-map-state-v2';

function loadStoredState() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {{}};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {{}};
  }} catch (e) {{
    return {{}};
  }}
}}

function saveStoredState(partial) {{
  try {{
    const state = Object.assign(loadStoredState(), partial || {{}});
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }} catch (e) {{}}
}}

const storedState = loadStoredState();
const initialCenter = Array.isArray(storedState.center) && storedState.center.length === 2 ? storedState.center : [20, 0];
const initialZoom = Number.isFinite(Number(storedState.zoom)) ? Number(storedState.zoom) : 2;
const map = L.map('map', {{worldCopyJump:true, zoomControl:true, preferCanvas:true}}).setView(initialCenter, initialZoom);
const tileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
  maxZoom: 19,
  attribution: 'Tiles &copy; Esri'
}}).addTo(map);

let connectionLayer = L.layerGroup().addTo(map);
let routerLayer = L.layerGroup().addTo(map);
let selectionLayer = L.layerGroup().addTo(map);
let autoFitDone = false;
let userInteracted = false;
let lastLayoutSignature = '';
let lastMarkersForReset = [];
let showSubnetLinks = storedState.showSubnetLinks !== false;
let showBackboneLinks = storedState.showBackboneLinks !== false;
let showPeerLinks = storedState.showPeerLinks !== false;
let showTunnelActivity = storedState.showTunnelActivity !== false;
let showPhase3Overlay = storedState.showPhase3Overlay !== false;
let showInferredLinks = storedState.showInferredLinks !== false;
let showPhase4Trace = storedState.showPhase4Trace !== false;
let focusSelectedRouter = storedState.focusSelectedRouter === true;

const toggleSubnet = document.getElementById('toggle-subnet-links');
const toggleBackbone = document.getElementById('toggle-backbone-links');
const togglePeer = document.getElementById('toggle-peer-links');
const toggleTunnels = document.getElementById('toggle-tunnel-activity');
const togglePhase3 = document.getElementById('toggle-phase3-overlay');
const toggleInferred = document.getElementById('toggle-inferred-links');
const togglePhase4 = document.getElementById('toggle-phase4-trace');
const toggleFocus = document.getElementById('toggle-focus-selected');
if (toggleSubnet) toggleSubnet.checked = showSubnetLinks;
if (toggleBackbone) toggleBackbone.checked = showBackboneLinks;
if (togglePeer) togglePeer.checked = showPeerLinks;
if (toggleTunnels) toggleTunnels.checked = showTunnelActivity;
if (togglePhase3) togglePhase3.checked = showPhase3Overlay;
if (toggleInferred) toggleInferred.checked = showInferredLinks;
if (togglePhase4) togglePhase4.checked = showPhase4Trace;
if (toggleFocus) toggleFocus.checked = focusSelectedRouter;

map.on('zoomstart dragstart movestart', () => {{ userInteracted = true; }});
map.on('moveend zoomend', () => {{
  const c = map.getCenter();
  saveStoredState({{center:[c.lat, c.lng], zoom: map.getZoom()}});
}});

function bindMapControl(id, assign) {{
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('change', () => {{
    assign(Boolean(el.checked));
    saveStoredState({{
      showSubnetLinks: showSubnetLinks,
      showBackboneLinks: showBackboneLinks,
      showPeerLinks: showPeerLinks,
      showTunnelActivity: showTunnelActivity,
      showPhase3Overlay: showPhase3Overlay,
      showInferredLinks: showInferredLinks,
      showPhase4Trace: showPhase4Trace,
      focusSelectedRouter: focusSelectedRouter,
    }});
    renderPayload(INITIAL_PAYLOAD);
  }});
}}

bindMapControl('toggle-subnet-links', (v) => {{ showSubnetLinks = v; }});
bindMapControl('toggle-backbone-links', (v) => {{ showBackboneLinks = v; }});
bindMapControl('toggle-peer-links', (v) => {{ showPeerLinks = v; }});
bindMapControl('toggle-tunnel-activity', (v) => {{ showTunnelActivity = v; }});
bindMapControl('toggle-phase3-overlay', (v) => {{ showPhase3Overlay = v; }});
bindMapControl('toggle-inferred-links', (v) => {{ showInferredLinks = v; }});
bindMapControl('toggle-phase4-trace', (v) => {{ showPhase4Trace = v; }});
bindMapControl('toggle-focus-selected', (v) => {{ focusSelectedRouter = v; }});

const mapControlsEl = document.querySelector('.map-controls');
if (mapControlsEl && window.L && L.DomEvent) {{
  L.DomEvent.disableClickPropagation(mapControlsEl);
  L.DomEvent.disableScrollPropagation(mapControlsEl);
}}
const mapLegendEl = document.querySelector('.map-legend');
if (mapLegendEl && window.L && L.DomEvent) {{
  L.DomEvent.disableClickPropagation(mapLegendEl);
  L.DomEvent.disableScrollPropagation(mapLegendEl);
}}
function bindPanelToggle(buttonId, bodyId, storageKey, defaultCollapsed) {{
  const btn = document.getElementById(buttonId);
  const body = document.getElementById(bodyId);
  if (!btn || !body) return;
  const state = loadStoredState();
  const collapsed = typeof state[storageKey] === 'boolean' ? state[storageKey] : !!defaultCollapsed;
  body.classList.toggle('collapsed', collapsed);
  btn.textContent = collapsed ? 'Show' : 'Hide';
  btn.addEventListener('click', () => {{
    const next = !body.classList.contains('collapsed');
    body.classList.toggle('collapsed', next);
    btn.textContent = next ? 'Show' : 'Hide';
    const patch = {{}};
    patch[storageKey] = next;
    saveStoredState(patch);
  }});
}}
bindPanelToggle('toggle-controls-panel', 'map-controls-body', 'controlsCollapsed', false);
bindPanelToggle('toggle-legend-panel', 'map-legend-body', 'legendCollapsed', true);
const selectedCardEl = document.getElementById('selected-router-card');
if (selectedCardEl && window.L && L.DomEvent) {{
  L.DomEvent.disableClickPropagation(selectedCardEl);
  L.DomEvent.disableScrollPropagation(selectedCardEl);
}}

function activeLinkColor(kind) {{
  if (String(kind) === 'backbone') return '#60a5fa';
  if (String(kind) === 'peer') return '#22c55e';
  return '#f59e0b';
}}

function statusColor(status) {{
  const s = String(status || '').toLowerCase();
  if (s === 'active') return '#22c55e';
  if (s === 'starting') return '#f59e0b';
  if (s === 'failed') return '#ef4444';
  return '#64748b';
}}

function escapeHtml(value) {{
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}}

function fitMarkers(markers, force) {{
  if (!markers.length) {{
    map.setView([20, 0], 2);
    return;
  }}
  if (!force && userInteracted && autoFitDone) return;
  if (markers.length === 1) {{
    map.setView(markers[0].getLatLng(), 6);
    autoFitDone = true;
    return;
  }}
  const bounds = L.featureGroup(markers).getBounds().pad(0.30);
  map.fitBounds(bounds, {{maxZoom: 8, animate: false}});
  autoFitDone = true;
}}

window.resetRouterMapView = function() {{
  userInteracted = false;
  fitMarkers(lastMarkersForReset, true);
}};

function midrange(values) {{
  const nums = values.filter(v => Number.isFinite(v));
  if (!nums.length) return NaN;
  return (Math.min(...nums) + Math.max(...nums)) / 2;
}}

function stackOffsets(count, latStep, lonStep) {{
  if (count <= 1) return [[0, 0]];
  const offsets = [];
  const half = (count - 1) / 2;
  for (let i = 0; i < count; i++) offsets.push([(i - half) * latStep, (i - half) * lonStep]);
  return offsets;
}}

function makeClusteredLayout(routers) {{
  const groups = new Map();
  const result = [];
  routers.forEach((r) => {{
    const lat = Number(r.display_lat);
    const lon = Number(r.display_lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    const country = String(r.country || '').trim();
    const city = String(r.city || '').trim();
    const subnet = String(r.subnet_label || '').trim();
    const locKey = `${{country}}||${{city}}`;
    if (!groups.has(locKey)) groups.set(locKey, {{routers: [], subnetMap: new Map()}});
    const g = groups.get(locKey);
    g.routers.push(r);
    if (!g.subnetMap.has(subnet)) g.subnetMap.set(subnet, []);
    g.subnetMap.get(subnet).push(r);
  }});

  groups.forEach((g) => {{
    const all = g.routers;
    const centerLat = midrange(all.map(r => Number(r.display_lat)));
    const centerLon = midrange(all.map(r => Number(r.display_lon)));
    const subnets = Array.from(g.subnetMap.entries()).sort((a,b) => String(a[0]).localeCompare(String(b[0])));
    const subnetOffsets = stackOffsets(Math.max(subnets.length,1), 0.014, 0.02);
    subnets.forEach(([subnetLabel, subnetRouters], subnetIdx) => {{
      const [dLat, dLon] = subnetOffsets[subnetIdx] || [0,0];
      const subnetLat = centerLat + dLat;
      const subnetLon = centerLon + (dLon / Math.max(Math.cos(centerLat * Math.PI / 180), 0.35));
      const routerOffsets = stackOffsets(Math.max(subnetRouters.length,1), 0.0035, 0.0);
      subnetRouters.sort((a,b) => String(a.id).localeCompare(String(b.id)));
      subnetRouters.forEach((r, ridx) => {{
        const [rdLat, rdLon] = routerOffsets[ridx] || [0,0];
        const plotLat = subnetLat + rdLat;
        const plotLon = subnetLon + (rdLon / Math.max(Math.cos(subnetLat * Math.PI / 180), 0.35));
        result.push({{...r, plot_lat: plotLat, plot_lon: plotLon, country_anchor_lat:centerLat, country_anchor_lon:centerLon}});
      }});
    }});
  }});
  return result;
}}

function buildConnectionIndex(plottedRouters, rawConnections) {{
  const byId = new Map();
  plottedRouters.forEach((r) => byId.set(String(r.id), r));
  const output = [];
  (Array.isArray(rawConnections) ? rawConnections : []).forEach((c) => {{
    const a = byId.get(String(c.from || ''));
    const b = byId.get(String(c.to || ''));
    if (!a || !b) return;
    const aLat = Number(a.plot_lat), aLon = Number(a.plot_lon);
    const bLat = Number(b.plot_lat), bLon = Number(b.plot_lon);
    if (!Number.isFinite(aLat) || !Number.isFinite(aLon) || !Number.isFinite(bLat) || !Number.isFinite(bLon)) return;
    output.push({{
      from: String(c.from), to: String(c.to), kind: String(c.kind || 'subnet'),
      from_name: a.name || ('Router ' + a.id), to_name: b.name || ('Router ' + b.id),
      from_status: String(a.status || 'unknown'), to_status: String(b.status || 'unknown'),
      subnet_label: c.subnet_label || a.subnet_label || b.subnet_label || '',
      state: String(c.state || ''), basis: String(c.basis || ''), points: [[aLat, aLon], [bLat, bLon]]
    }});
  }});
  return output;
}}

function tunnelProfile(router) {{
  const e = Number(router.tunnel_exploratory || 0);
  const c = Number(router.tunnel_client || 0);
  const p = Number(router.tunnel_participating || 0);
  const total = Number(router.tunnel_count || (e + c + p) || 0);
  let dominant = 'mixed';
  const maxv = Math.max(e, c, p, 0);
  const winners = [e === maxv && maxv > 0 ? 'exploratory' : null, c === maxv && maxv > 0 ? 'client' : null, p === maxv && maxv > 0 ? 'participating' : null].filter(Boolean);
  if (winners.length === 1) dominant = winners[0];
  if (total <= 0) dominant = 'none';
  return {{exploratory:e, client:c, participating:p, total:total, dominant:dominant}};
}}

function tunnelColor(kind) {{
  if (kind === 'exploratory') return '#a855f7';
  if (kind === 'client') return '#06b6d4';
  if (kind === 'participating') return '#ec4899';
  if (kind === 'mixed') return '#e5e7eb';
  return '#64748b';
}}

function addTunnelAura(router) {{
  const profile = tunnelProfile(router);
  if (!showTunnelActivity || profile.total <= 0) return;
  const lat = Number(router.plot_lat), lon = Number(router.plot_lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  const color = tunnelColor(profile.dominant);
  const radius = 10 + Math.min(profile.total, 60) * 0.26;
  const fillOpacity = profile.total > 0 ? Math.min(0.08 + profile.total / 320.0, 0.16) : 0.0;
  L.circleMarker([lat, lon], {{
    radius, color, weight: 1.3, opacity: 0.45, fillColor: color, fillOpacity,
    dashArray: profile.dominant === 'mixed' ? '4 6' : null, interactive: false
  }}).addTo(routerLayer);
}}


function phase3TrendColor(router) {{
  const band = String(router.phase3_trend_band || 'stable').toLowerCase();
  if (band === 'unstable') return '#ef4444';
  if (band === 'watch') return '#f59e0b';
  return '#22c55e';
}}

function phase3StageColor(router) {{
  const stage = String(router.phase3_latest_stage || '').toLowerCase();
  if (stage.includes('post')) return '#06b6d4';
  if (stage.includes('scenario')) return '#8b5cf6';
  if (stage.includes('standalone')) return '#94a3b8';
  return '#e879f9';
}}

function phase3RecencyColor(router) {{
  const bucket = String(router.phase3_recency_bucket || '').toLowerCase();
  if (bucket === 'hot') return '#22c55e';
  if (bucket === 'warm') return '#38bdf8';
  if (bucket === 'cool') return '#f59e0b';
  return '#64748b';
}}

function addPhase3Aura(router) {{
  if (!showPhase3Overlay || !router || !router.phase3_has_overlay) return;
  const lat = Number(router.plot_lat), lon = Number(router.plot_lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  const trendColor = phase3TrendColor(router);
  const latestScore = Number(router.phase3_score_latest || 0);
  const radius = 11 + Math.max(0, (100 - latestScore)) * 0.06;
  L.circleMarker([lat, lon], {{
    radius: Math.max(11, Math.min(17, radius)), color: trendColor, weight: 2.6,
    opacity: 0.88, fillOpacity: 0, dashArray: String(router.phase3_trend_band || '').toLowerCase() === 'watch' ? '5 6' : null,
    interactive: false
  }}).addTo(routerLayer);
  L.circleMarker([lat, lon], {{
    radius: Math.max(15, Math.min(20, radius + 3.4)), color: phase3StageColor(router), weight: 1.6,
    opacity: 0.72, fillOpacity: 0, dashArray: '2 6', interactive: false
  }}).addTo(routerLayer);
  L.circleMarker([lat + 0.0016, lon + 0.0016], {{
    radius: 3.2, color: '#ffffff', weight: 1.0, opacity: 0.95,
    fillColor: phase3RecencyColor(router), fillOpacity: 0.95, interactive: false
  }}).addTo(routerLayer);
}}

function phase4ConfidenceColor(router) {{
  const confidence = String(router.phase4_confidence || '').toLowerCase();
  if (confidence === 'high') return '#f43f5e';
  if (confidence === 'medium') return '#fb7185';
  return '#f9a8d4';
}}

function addPhase4TraceAura(router) {{
  if (!showPhase4Trace || !router || !router.phase4_has_trace) return;
  const lat = Number(router.plot_lat), lon = Number(router.plot_lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  const count = Number(router.phase4_related_count || 0);
  const confidence = String(router.phase4_confidence || '').toLowerCase();
  const radius = confidence === 'high' ? 5.0 : confidence === 'medium' ? 4.2 : 3.5;
  const offsetLat = lat + 0.0021;
  const offsetLon = lon - 0.0021;
  L.circleMarker([offsetLat, offsetLon], {{
    radius: radius, color: '#ffffff', weight: 1.2, opacity: 0.92,
    fillColor: phase4ConfidenceColor(router), fillOpacity: 0.96, interactive: false
  }}).addTo(routerLayer);
  if (count > 0) {{
    L.circleMarker([offsetLat, offsetLon], {{
      radius: radius + 2.6 + Math.min(3, count * 0.25), color: phase4ConfidenceColor(router), weight: 1.0,
      opacity: 0.55, fillOpacity: 0, dashArray: '1 4', interactive: false
    }}).addTo(routerLayer);
  }}
}}

function renderSelectedCard(router) {{
  if (!selectedCardEl) return;
  if (!router) {{
    selectedCardEl.innerHTML = '';
    selectedCardEl.style.display = 'none';
    return;
  }}
  const status = String(router.status || 'unknown').toLowerCase();
  selectedCardEl.style.display = 'block';
  selectedCardEl.className = 'selected-router-card';
  selectedCardEl.innerHTML = `
    <div class="selected-router-header">
      <div class="selected-router-title">${{escapeHtml(router.name || ('Router ' + router.id))}}</div>
      <div class="selected-router-badge ${{escapeHtml(status)}}">${{escapeHtml(status.toUpperCase())}}</div>
    </div>
    <div class="selected-router-grid">
      <div class="selected-router-chips">
        <span class="selected-router-chip">${{escapeHtml(String(router.floodfill).toLowerCase() === 'true' ? 'Floodfill' : 'Router')}}</span>
        <span class="selected-router-chip">${{escapeHtml(router.city || 'Unknown')}}, ${{escapeHtml(router.country || 'Unknown')}}</span>
        <span class="selected-router-chip">${{escapeHtml(router.subnet_label || 'unknown')}}</span>
      </div>
      <div><b>IP:</b> ${{escapeHtml(router.router_ip || 'unknown')}} · <b>Peers:</b> ${{escapeHtml(String(router.peer_count || '0'))}} · <b>Tunnels:</b> ${{escapeHtml(String(router.tunnel_count || '0'))}}</div>
      <div><b>Profile:</b> ${{escapeHtml(String(router.tunnel_profile || 'none'))}} · <b>Console:</b> ${{escapeHtml(router.console_url || 'not available')}}</div>

      <div class="selected-router-section">
        <div class="selected-router-section-title">Phase 3 stability</div>
        <div class="selected-router-chips">
          <span class="selected-router-chip">Trend ${{escapeHtml(String(router.phase3_trend_band || 'none').toUpperCase())}}</span>
          <span class="selected-router-chip">Conf ${{escapeHtml(String(router.phase3_confidence || 'n/a').toUpperCase())}}</span>
          <span class="selected-router-chip">Life ${{escapeHtml(String(router.phase3_recency_bucket || 'stale').toUpperCase())}}</span>
        </div>
        <div><b>Score:</b> ${{escapeHtml(String(router.phase3_score_avg ?? 'n/a'))}} / ${{escapeHtml(String(router.phase3_score_latest ?? 'n/a'))}} · <b>Weighted change:</b> ${{escapeHtml(String(router.phase3_weighted_change ?? 'n/a'))}}</div>
        <div><b>Trace:</b> gen ${{escapeHtml(String(router.phase3_latest_generation ?? 'n/a'))}} · ${{escapeHtml(String(router.phase3_latest_stage || 'n/a'))}} · ${{escapeHtml(String(router.phase3_latest_trigger || 'n/a'))}}</div>
        <div class="selected-router-note">${{escapeHtml(String(router.phase3_latest_ts || 'n/a'))}}</div>
      </div>

      <div class="selected-router-section">
        <div class="selected-router-section-title">Phase 4 deep trace</div>
        <div class="selected-router-chips">
          <span class="selected-router-chip">Conf ${{escapeHtml(String(router.phase4_confidence || 'surface-only').toUpperCase())}}</span>
          <span class="selected-router-chip">Related ${{escapeHtml(String(router.phase4_related_count ?? '0'))}}</span>
          <span class="selected-router-chip">Hosts ${{escapeHtml(String(router.phase4_shared_host_count ?? '0'))}}</span>
        </div>
        <div><b>Routers:</b> ${{escapeHtml(String(router.phase4_related_names || 'none'))}}</div>
        <div><b>Evidence:</b> s ${{escapeHtml(String(router.phase4_surface_rows ?? '0'))}} · l ${{escapeHtml(String(router.phase4_lease_rows ?? '0'))}} · log ${{escapeHtml(String(router.phase4_log_rows ?? '0'))}} · corr ${{escapeHtml(String(router.phase4_lease_correlation ?? '0'))}}</div>
        <div><b>Basis:</b> ${{escapeHtml(String(router.phase4_basis || 'surface-only inference'))}}</div>
        <div class="selected-router-note">Surface inference only. Exact per-hop truth is not guaranteed.</div>
      </div>
    </div>
    <div class="selected-router-actions">
      <a class="selected-router-btn secondary" href="i2prouter://select/${{encodeURIComponent(router.id)}}">Select</a>
      <a class="selected-router-btn" href="i2prouter://console/${{encodeURIComponent(router.id)}}">Open Console</a>
    </div>
  `;
}}

function renderPayload(payload) {{
  connectionLayer.clearLayers();
  routerLayer.clearLayers();
  selectionLayer.clearLayers();

  const routers = Array.isArray(payload && payload.routers) ? payload.routers : [];
  const selectedId = String(payload && payload.selected_router_id || '');
  const markers = [];
  const plotted = makeClusteredLayout(routers);
  const signature = plotted.map(r => `${{r.id}}:${{r.country}}:${{r.city}}:${{r.subnet_label}}:${{r.status}}`).sort().join('|');
  const connections = buildConnectionIndex(plotted, payload && payload.connections || []);
  const selectedRouter = plotted.find((r) => String(r.id) === selectedId) || null;
  renderSelectedCard(selectedRouter);

  connections.forEach((conn) => {{
    const kind = String(conn.kind || 'subnet');
    const isBackbone = kind === 'backbone';
    const isPeer = kind === 'peer';
    const isInferred = kind === 'inferred';
    if ((kind === 'subnet' && !showSubnetLinks) || (isBackbone && !showBackboneLinks) || (isPeer && !showPeerLinks) || (isInferred && !showInferredLinks)) return;
    const touchesSelected = selectedId && (String(conn.from) === selectedId || String(conn.to) === selectedId);
    if (focusSelectedRouter && selectedId && !touchesSelected) return;
    const endpointsActive = String(conn.from_status).toLowerCase() === 'active' && String(conn.to_status).toLowerCase() === 'active';
    const baseColor = isInferred ? '#e879f9' : activeLinkColor(kind);
    let weight = isBackbone ? 4.2 : (isPeer ? 3.8 : (isInferred ? 3.1 : 3.4));
    let opacity = isBackbone ? 0.92 : (isPeer ? 0.90 : (isInferred ? 0.78 : 0.88));
    let dashArray = isBackbone ? '10 7' : (isInferred ? '5 8' : null);
    if (!endpointsActive || conn.state === 'degraded') {{ opacity = Math.min(opacity, 0.42); dashArray = dashArray || '5 8'; }}
    if (selectedId && focusSelectedRouter) {{ if (touchesSelected) {{ weight += 1.3; opacity = Math.max(opacity, 0.96); }} }}
    else if (selectedId && touchesSelected) {{ weight += 0.7; opacity = Math.max(opacity, 0.94); }}
    const line = L.polyline(conn.points, {{ color: baseColor, weight, opacity, dashArray, lineCap: 'round', lineJoin: 'round', interactive: true }}).addTo(connectionLayer);
    let relationship = 'Subnet link';
    if (isBackbone) relationship = 'Floodfill backbone';
    if (isPeer) relationship = 'Live peer link';
    if (isInferred) relationship = 'Inferred trace/path relationship';
    const health = isInferred
      ? 'Inference only — not an exact per-hop truth guarantee'
      : (conn.state === 'active' ? 'Active runtime state' : (endpointsActive ? 'Runtime state degraded' : 'Endpoint not fully active'));
    const basis = conn.basis ? `<br>Basis: ${{escapeHtml(conn.basis)}}` : '';
    line.bindTooltip(`${{escapeHtml(conn.from_name)}} ↔ ${{escapeHtml(conn.to_name)}}<br>${{escapeHtml(relationship)}}${{conn.subnet_label ? '<br>' + escapeHtml(conn.subnet_label) : ''}}${{basis}}<br>${{escapeHtml(health)}}`, {{sticky:true}});
  }});

  const nonSelected = plotted.filter((r) => String(r.id) !== selectedId);
  const selectedOnly = plotted.filter((r) => String(r.id) === selectedId);
  const drawRouters = (items, selectedPass) => {{
    items.forEach((r) => {{
      const lat = Number(r.plot_lat), lon = Number(r.plot_lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      const isSelected = selectedPass;
      addTunnelAura(r);
      addPhase3Aura(r);
      addPhase4TraceAura(r);
      if (String(r.floodfill).toLowerCase() === 'true') {{
        L.circleMarker([lat, lon], {{ radius: isSelected ? 14 : 13, color: '#facc15', weight: isSelected ? 3.4 : 3, fillOpacity: 0 }}).addTo(routerLayer);
      }}
      if (isSelected) {{
        L.circleMarker([lat, lon], {{ radius: 16, color: '#60a5fa', weight: 3, fillOpacity: 0 }}).addTo(selectionLayer);
      }}
      const marker = L.circleMarker([lat, lon], {{
        radius: isSelected ? 9 : 8, color: '#d7e3f4', weight: isSelected ? 2.2 : 1.5,
        fillColor: statusColor(r.status), fillOpacity: isSelected ? 1.0 : 0.95
      }}).addTo(routerLayer);
      marker.bindTooltip(`${{escapeHtml(r.name || ('Router ' + r.id))}}<br>${{escapeHtml(r.city || 'Unknown')}}, ${{escapeHtml(r.country || 'Unknown')}}<br>${{escapeHtml(r.subnet_label || 'unknown')}}<br>Status: ${{escapeHtml(String(r.status || 'unknown').toUpperCase())}}<br>Phase 3: ${{escapeHtml(String(r.phase3_trend_band || 'none').toUpperCase())}} · score ${{escapeHtml(String(r.phase3_score_latest ?? 'n/a'))}} · stage ${{escapeHtml(String(r.phase3_latest_stage || 'n/a'))}}<br>Phase 4: ${{escapeHtml(String(r.phase4_confidence || 'surface-only').toUpperCase())}} · related ${{escapeHtml(String(r.phase4_related_count || '0'))}}`, {{direction: 'top', offset: [0, -8]}});
      marker.on('click', () => {{ window.location.href = 'i2prouter://select/' + encodeURIComponent(r.id); }});
      marker.on('dblclick', () => {{ window.location.href = 'i2prouter://console/' + encodeURIComponent(r.id); }});
      markers.push(marker);
    }});
  }};
  drawRouters(nonSelected, false);
  drawRouters(selectedOnly, true);

  lastMarkersForReset = markers;
  if (!autoFitDone || (!userInteracted && signature !== lastLayoutSignature) || selectedOnly.length) fitMarkers(markers, !userInteracted);
  lastLayoutSignature = signature;
}}

window.forceRouterSelection = function(_routerId) {{ return; }};
window.updateRouterMap = function(payload) {{ renderPayload(payload || {{routers:[], connections:[], selected_router_id:''}}); }};
renderPayload(INITIAL_PAYLOAD || {{routers:[], connections:[], selected_router_id:''}});
</script>
</body>
</html>
        """


    def _on_load_finished(self, ok):
        self._web_loaded = bool(ok)
        if self._web_loaded and self._pending_payload is not None:
            payload_json = json.dumps(self._pending_payload, ensure_ascii=False)
            self.map_view.page().runJavaScript(f"window.updateRouterMap({payload_json});")

    def _send_payload(self, payload):
        if not (WEBENGINE_AVAILABLE and self.map_view):
            self._pending_payload = payload
            return
        payload = dict(payload or {})
        payload_json = json.dumps(payload, ensure_ascii=False)
        if payload_json == self._last_payload_json:
            return
        self._last_payload_json = payload_json
        self._pending_payload = payload
        if self._web_loaded:
            self.map_view.page().runJavaScript(f"window.updateRouterMap({payload_json});")
            return
        self.map_view.setHtml(self._build_leaflet_html(payload_json), QUrl("https://local.i2p.testnet/"))

    def build_map_connections(self, mapped_routers):
        connections = []
        seen = set()

        def add_connection(a, b, kind, subnet_label=""):
            a_id = str(a.get("id", ""))
            b_id = str(b.get("id", ""))
            if not a_id or not b_id or a_id == b_id:
                return
            key = tuple(sorted((a_id, b_id))) + (kind,)
            if key in seen:
                return
            seen.add(key)
            connections.append({
                "from": a_id,
                "to": b_id,
                "kind": kind,
                "subnet_label": subnet_label or a.get("subnet_label", "") or b.get("subnet_label", ""),
            })

        subnet_groups = {}
        for router in mapped_routers:
            subnet_groups.setdefault(str(router.get("subnet_label", "")), []).append(router)

        for subnet_label, group in subnet_groups.items():
            ordered = sorted(group, key=lambda r: safe_int(r.get("id"), 9999))
            for i in range(len(ordered)):
                for j in range(i + 1, len(ordered)):
                    add_connection(ordered[i], ordered[j], "subnet", subnet_label)

        floodfills = [r for r in mapped_routers if str(r.get("floodfill", "")).lower() == "true"]
        floodfills = sorted(floodfills, key=lambda r: safe_int(r.get("id"), 9999))
        if len(floodfills) > 1:
            for i in range(len(floodfills) - 1):
                add_connection(floodfills[i], floodfills[i + 1], "backbone")

        return connections

    def build_runtime_peer_links(self, mapped_routers, topology_connections):
        # Phase 3C: best-effort live peer adjacency extraction from router console pages.
        # We inspect the live /peers (and fallback /) HTML for tokens belonging to other routers.
        router_by_id = {str(r.get("id", "")): r for r in mapped_routers}
        runtime_links = []
        seen = set()

        def router_tokens(router):
            tokens = set()
            for key in ("router_ip", "ntcp_host", "udp_host", "console_host"):
                value = str(router.get(key, "") or "").strip()
                if value and value not in {"unknown", "0.0.0.0"}:
                    tokens.add(value)
            for host_key, port_key in (("router_ip", "ntcp_port"), ("ntcp_host", "ntcp_port"), ("udp_host", "udp_port")):
                host = str(router.get(host_key, "") or "").strip()
                port = str(router.get(port_key, "") or "").strip()
                if host and port and host not in {"unknown", "0.0.0.0"} and port not in {"", "unknown", "0"}:
                    tokens.add(f"{host}:{port}")
            return {t for t in tokens if t}

        token_map = {rid: router_tokens(r) for rid, r in router_by_id.items()}

        for src_id, src in router_by_id.items():
            if str(src.get("status", "")).lower() != "active":
                continue
            console_host = src.get("console_host") or src.get("router_ip") or "127.0.0.1"
            console_port = src.get("console_port")
            if not console_port or str(console_port) in {"", "0", "unknown"}:
                continue
            peers_html = fetch_console_page(console_host, console_port, "/peers") or ""
            root_html = fetch_console_page(console_host, console_port, "/") or ""
            combined = peers_html + "\n" + root_html
            if not combined.strip():
                continue
            combined_lower = combined.lower()
            for dst_id, dst in router_by_id.items():
                if dst_id == src_id:
                    continue
                if str(dst.get("status", "")).lower() != "active":
                    continue
                key = tuple(sorted((src_id, dst_id)))
                if key in seen:
                    continue
                match_hits = []
                for token in token_map.get(dst_id, set()):
                    if token and token.lower() in combined_lower:
                        match_hits.append(token)
                if not match_hits:
                    continue
                basis = "console peer page token match"
                if len(match_hits) > 1:
                    basis += f" ({len(match_hits)} matches)"
                runtime_links.append({
                    "from": src_id,
                    "to": dst_id,
                    "kind": "peer",
                    "basis": basis,
                    "subnet_label": src.get("subnet_label", "") if src.get("subnet_label") == dst.get("subnet_label") else "",
                    "state": "active",
                })
                seen.add(key)

        return runtime_links


    def force_selection(self, selected_router_id):
        return

    def update_map(self, snapshot, selected_router_id=None, analytics_payload=None):
        routers = snapshot.get("routers", []) if snapshot else []
        analytics_payload = analytics_payload or {}
        overlay_by_id = analytics_payload.get("router_overlays", {}) if isinstance(analytics_payload, dict) else {}
        inferred_links = list((analytics_payload.get("inferred_links") if isinstance(analytics_payload, dict) else []) or [])
        mapped = []
        countries = set()
        subnets = set()
        active = 0
        floodfill = 0

        for router in routers:
            p = router.get("parsed", {})
            lat = p.get("display_lat", "")
            lon = p.get("display_lon", "")
            try:
                lat_val = float(str(lat).strip())
                lon_val = float(str(lon).strip())
            except Exception:
                continue

            mapped_router = {
                "id": str(router.get("id", "")),
                "name": router.get("name", ""),
                "status": router.get("status", "unknown"),
                "floodfill": router.get("floodfill", "false"),
                "country": p.get("country", ""),
                "country_code": p.get("country_code", ""),
                "city": p.get("city", ""),
                "display_lat": lat_val,
                "display_lon": lon_val,
                "subnet_label": p.get("subnet_label", ""),
                "subnet": p.get("subnet", ""),
                "namespace": p.get("namespace", ""),
                "router_ip": p.get("router_ip", router.get("router_ip", "")),
                "console_url": router.get("console_url", ""),
                "peer_count": router.get("metrics", {}).get("peer_count", "0"),
                "peer_active": router.get("metrics", {}).get("peer_active", "0"),
                "peer_known": router.get("metrics", {}).get("peer_known", "0"),
                "console_host": router.get("console_host", p.get("console_host", "")),
                "console_port": router.get("console_port", p.get("console_port", "")),
                "ntcp_host": p.get("ntcp_host", ""),
                "ntcp_port": p.get("ntcp_port", ""),
                "udp_host": p.get("udp_host", ""),
                "udp_port": p.get("udp_port", ""),
                "tunnel_count": router.get("metrics", {}).get("tunnel_count", "0"),
                "tunnel_exploratory": router.get("metrics", {}).get("tunnel_exploratory", "0"),
                "tunnel_client": router.get("metrics", {}).get("tunnel_client", "0"),
                "tunnel_participating": router.get("metrics", {}).get("tunnel_participating", "0"),
                "tunnel_profile": dominant_tunnel_profile(router.get("metrics", {})),
            }
            overlay = overlay_by_id.get(mapped_router["id"], {})
            mapped_router.update({
                "phase3_has_overlay": bool(overlay),
                "phase3_score_avg": overlay.get("score_avg"),
                "phase3_score_latest": overlay.get("score_latest"),
                "phase3_weighted_change": overlay.get("weighted_change_rate"),
                "phase3_confidence": overlay.get("confidence"),
                "phase3_trend_band": overlay.get("trend_band"),
                "phase3_latest_stage": overlay.get("latest_stage"),
                "phase3_latest_trigger": overlay.get("latest_trigger"),
                "phase3_latest_generation": overlay.get("latest_generation"),
                "phase3_latest_ts": overlay.get("latest_ts"),
                "phase3_recency_bucket": overlay.get("recency_bucket"),
                "phase3_proxy_success_rate": overlay.get("proxy_success_rate"),
                "phase3_instability_recurrence": overlay.get("instability_recurrence"),
                "phase3_avg_severity_weight": overlay.get("avg_severity_weight"),
                "phase4_has_trace": bool(overlay.get("phase4_confidence") or overlay.get("phase4_related_count") or overlay.get("phase4_surface_rows")),
                "phase4_confidence": overlay.get("phase4_confidence"),
                "phase4_related_count": overlay.get("phase4_related_count"),
                "phase4_related_names": ", ".join(overlay.get("phase4_related_names") or []) or "none",
                "phase4_surface_rows": overlay.get("phase4_surface_rows"),
                "phase4_lease_rows": overlay.get("phase4_lease_rows"),
                "phase4_log_rows": overlay.get("phase4_log_rows"),
                "phase4_lease_correlation": overlay.get("phase4_lease_correlation"),
                "phase4_shared_host_count": overlay.get("phase4_shared_host_count"),
                "phase4_basis": overlay.get("phase4_basis"),
            })
            mapped.append(mapped_router)
            if mapped_router["country"]:
                countries.add(mapped_router["country"])
            if mapped_router["subnet_label"]:
                subnets.add(mapped_router["subnet_label"])
            if mapped_router["status"] == "active":
                active += 1
            if str(mapped_router["floodfill"]).lower() == "true":
                floodfill += 1

        topology_connections = self.build_map_connections(mapped)
        runtime_peer_links = self.build_runtime_peer_links(mapped, topology_connections)
        connections = topology_connections + runtime_peer_links + inferred_links
        selected = next((r for r in mapped if r["id"] == str(selected_router_id)), None)
        selected_text = f"Selected: {selected['name']}." if selected else "Selected: none."
        country_text = ", ".join(sorted(countries)) if countries else "none"
        tunnel_total = sum(safe_int(r.get("tunnel_count", 0)) for r in mapped)
        tunnel_active_routers = sum(1 for r in mapped if safe_int(r.get("tunnel_count", 0)) > 0)
        trend_counts = {"stable": 0, "watch": 0, "unstable": 0}
        phase4_counts = {"high": 0, "medium": 0, "surface-only": 0}
        hot_count = 0
        for r in mapped:
            band = str(r.get("phase3_trend_band") or "").lower()
            if band in trend_counts:
                trend_counts[band] += 1
            conf = str(r.get("phase4_confidence") or "surface-only").lower()
            if conf in phase4_counts:
                phase4_counts[conf] += 1
            if str(r.get("phase3_recency_bucket") or "").lower() == "hot":
                hot_count += 1
        self.summary.setText(
            f"Map view shows {len(mapped)}/{len(routers)} routers mapped, {active} active, {floodfill} floodfill, "
            f"across {len(countries)} country/countries and {len(subnets)} subnet(s), with {len(topology_connections)} topology link(s), {len(runtime_peer_links)} live peer link(s), "
            f"{len(inferred_links)} inferred trace link(s), and {tunnel_total} total tunnels across {tunnel_active_routers} router(s). "
            f"Phase 3 overlay: stable {trend_counts['stable']}, watch {trend_counts['watch']}, unstable {trend_counts['unstable']}, hot lifecycle markers {hot_count}. "
            f"Phase 4 deep trace: high {phase4_counts['high']}, medium {phase4_counts['medium']}, surface-only {phase4_counts['surface-only']}. "
            f"Countries: {country_text}. {selected_text}"
        )
        if WEBENGINE_AVAILABLE:
            self._send_payload({
                "selected_router_id": str(selected_router_id or ""),
                "routers": mapped,
                "connections": connections,
                "phase3_meta": {
                    "inferred_links": len(inferred_links),
                    "overlay_routers": sum(1 for r in mapped if r.get("phase3_has_overlay")),
                },
                "phase4_meta": {
                    "high": sum(1 for r in mapped if str(r.get("phase4_confidence") or "").lower() == "high"),
                    "medium": sum(1 for r in mapped if str(r.get("phase4_confidence") or "").lower() == "medium"),
                    "surface_only": sum(1 for r in mapped if str(r.get("phase4_confidence") or "surface-only").lower() == "surface-only"),
                },
            })


class TopologyPanel(QFrame):
    router_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopologyPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.summary = QLabel("Topology summary will appear here.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color:#8ea7d1;font-size:12px;")
        layout.addWidget(self.summary)

        self.canvas = TopologyCanvas(self)
        self.canvas.router_selected.connect(self.router_selected)
        layout.addWidget(self.canvas, 1)

    def update_topology(self, snapshot, selected_router_id=None):
        routers = snapshot.get("routers", []) if snapshot else []
        total = len(routers)
        active = sum(1 for r in routers if r.get("status") == "active")
        ff = sum(1 for r in routers if str(r.get("floodfill", "")).lower() == "true")
        selected = next((r for r in routers if str(r.get("id")) == str(selected_router_id)), None)
        selected_text = f"Selected: {selected['name']}" if selected else "Selected: none"
        self.summary.setText(
            f"Topology snapshot shows {total} router(s), {active} active, {ff} floodfill. "
            f"Floodfill routers are highlighted with an outer ring. {selected_text}."
        )
        self.canvas.set_snapshot(routers, selected_router_id)

class TopologyBuilderPanel(QFrame):
    deploy_requested = pyqtSignal(str, str, str, int, int)
    summary_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopologyPanel")
        self._loading_form = False
        self._preview_notice = ""
        self.topology = {"version": 1, "locations": []}
        self.paths = builder_generated_paths()
        self._selected_kind = None
        self._selected_location_index = None
        self._selected_subnet_index = None
        self.build_ui()
        self.load_from_file(resolve_local_path("topology.sample.json"), quiet=True)

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("New Topology")
        self.btn_load_sample = QPushButton("Load Sample")
        self.btn_load_json = QPushButton("Load JSON")
        self.btn_save_json = QPushButton("Save JSON")
        self.btn_validate = QPushButton("Validate")
        self.btn_generate = QPushButton("Export Files")
        self.btn_deploy = QPushButton("Deploy Network")
        for btn in (self.btn_new, self.btn_load_sample, self.btn_load_json, self.btn_save_json, self.btn_validate, self.btn_generate, self.btn_deploy):
            toolbar.addWidget(btn)
        toolbar.addStretch(1)
        root.addLayout(toolbar)
        self.btn_validate.setVisible(False)
        self.btn_generate.setVisible(False)

        self.summary = QLabel("Topology Builder ready.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color:#8ea7d1;font-size:12px;")
        root.addWidget(self.summary)

        splitter = QSplitter(Qt.Orientation.Horizontal if PYQT_VER == 6 else Qt.Horizontal)
        root.addWidget(splitter, 1)

        # left
        left = QFrame()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        actions = QHBoxLayout()
        self.btn_add_location = QPushButton("Add Location")
        self.btn_add_subnet = QPushButton("Add Subnet")
        self.btn_remove_selected = QPushButton("Remove Selected")
        actions.addWidget(self.btn_add_location)
        actions.addWidget(self.btn_add_subnet)
        actions.addWidget(self.btn_remove_selected)
        left_layout.addLayout(actions)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Topology", "Value"])
        self.tree.setAlternatingRowColors(False)
        left_layout.addWidget(self.tree, 1)
        splitter.addWidget(left)

        # right
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.form_stack = QStackedWidget()
        right_layout.addWidget(self.form_stack)

        self.page_blank = QWidget()
        blank_layout = QVBoxLayout(self.page_blank)
        blank_layout.addWidget(QLabel("Select a location or subnet to edit its properties."))
        blank_layout.addStretch(1)
        self.form_stack.addWidget(self.page_blank)


        self.page_location = QWidget()
        loc_form = QFormLayout(self.page_location)
        loc_form.setContentsMargins(8, 8, 8, 8)
        loc_form.setSpacing(10)
        self._all_country_names = get_all_country_names()
        self._country_popup_timer = None
        self._city_popup_timer = None
        self._city_choice_names = []

        self.loc_country = QComboBox()
        self.loc_country.setEditable(True)
        self.loc_country.setView(QListView())
        self.loc_country.setMaxVisibleItems(24)
        if PYQT_VER == 6:
            self.loc_country.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        else:
            self.loc_country.setInsertPolicy(QComboBox.NoInsert)
        if self.loc_country.lineEdit() is not None:
            self.loc_country.lineEdit().setPlaceholderText("Type a country name to filter the list")
        self.loc_city = QComboBox()
        self.loc_city.setEditable(True)
        self.loc_city.setView(QListView())
        self.loc_city.setMaxVisibleItems(24)
        if PYQT_VER == 6:
            self.loc_city.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        else:
            self.loc_city.setInsertPolicy(QComboBox.NoInsert)
        if self.loc_city.lineEdit() is not None:
            self.loc_city.lineEdit().setPlaceholderText("Type a city name to filter the list")
        self.loc_country_model = QStringListModel(self._all_country_names)
        self.loc_country_completer = QCompleter(self.loc_country_model, self)
        self.loc_country_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive if PYQT_VER == 6 else Qt.CaseInsensitive)
        self.loc_country_completer.setFilterMode(Qt.MatchFlag.MatchStartsWith if PYQT_VER == 6 else Qt.MatchStartsWith)
        self.loc_country_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion if PYQT_VER == 6 else QCompleter.PopupCompletion)
        if self.loc_country.lineEdit() is not None:
            self.loc_country.lineEdit().setCompleter(self.loc_country_completer)
        self.loc_city_model = QStringListModel([])
        self.loc_city_completer = QCompleter(self.loc_city_model, self)
        self.loc_city_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive if PYQT_VER == 6 else Qt.CaseInsensitive)
        self.loc_city_completer.setFilterMode(Qt.MatchFlag.MatchStartsWith if PYQT_VER == 6 else Qt.MatchStartsWith)
        self.loc_city_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion if PYQT_VER == 6 else QCompleter.PopupCompletion)
        if self.loc_city.lineEdit() is not None:
            self.loc_city.lineEdit().setCompleter(self.loc_city_completer)
        self.loc_code = QLineEdit()
        self.loc_code.setReadOnly(True)
        self.loc_code.setPlaceholderText("Auto")
        self.btn_loc_resolve = QPushButton("Auto Fill Location")
        self.btn_loc_advanced = QPushButton("Show Advanced Placement")
        self.btn_loc_advanced.setCheckable(True)
        self.loc_lat = QLineEdit()
        self.loc_lon = QLineEdit()
        self.loc_spread = QLineEdit()
        self.loc_lat.setPlaceholderText("Auto")
        self.loc_lon.setPlaceholderText("Auto")
        self.loc_spread.setPlaceholderText("Auto")
        self.loc_auto_status = QLabel("Choose a country and city. The builder will auto-fill map placement from the offline catalog and only use online geocoding if you type a city that is not in the catalog.")
        self.loc_auto_status.setWordWrap(True)
        self.loc_auto_status.setStyleSheet("color:#8ea7d1;font-size:11px;")
        tool_row_widget = QWidget()
        tool_row = QHBoxLayout(tool_row_widget)
        tool_row.setContentsMargins(0, 0, 0, 0)
        tool_row.setSpacing(8)
        tool_row.addWidget(self.btn_loc_resolve)
        tool_row.addWidget(self.btn_loc_advanced)
        tool_row.addStretch(1)
        self.loc_advanced_frame = QFrame()
        self.loc_advanced_frame.setVisible(False)
        adv_form = QFormLayout(self.loc_advanced_frame)
        adv_form.setContentsMargins(0, 0, 0, 0)
        adv_form.setSpacing(8)
        adv_form.addRow("Center Latitude", self.loc_lat)
        adv_form.addRow("Center Longitude", self.loc_lon)
        adv_form.addRow("Map Spread", self.loc_spread)
        self.loc_helper = QLabel("Advanced placement overrides are optional. They only change visual placement on the map. The builder now auto-fills country code, latitude, longitude, and spread from the selected country/city.")
        self.loc_helper.setWordWrap(True)
        self.loc_helper.setStyleSheet("color:#8ea7d1;font-size:11px;")
        loc_form.addRow("Country", self.loc_country)
        loc_form.addRow("City", self.loc_city)
        loc_form.addRow("Country Code", self.loc_code)
        loc_form.addRow("", tool_row_widget)
        loc_form.addRow("Auto placement", self.loc_auto_status)
        loc_form.addRow("", self.loc_advanced_frame)
        loc_form.addRow("", self.loc_helper)
        self.form_stack.addWidget(self.page_location)

        self.page_subnet = QWidget()
        subnet_form = QFormLayout(self.page_subnet)
        subnet_form.setContentsMargins(8, 8, 8, 8)
        subnet_form.setSpacing(10)
        self.sub_label = QLineEdit()
        self.sub_cidr = QLineEdit()
        self.sub_routers = QSpinBox()
        self.sub_routers.setRange(1, 1024)
        self.sub_floodfill = QSpinBox()
        self.sub_floodfill.setRange(0, 1024)
        subnet_form.addRow("Subnet Label", self.sub_label)
        subnet_form.addRow("CIDR", self.sub_cidr)
        subnet_form.addRow("Routers", self.sub_routers)
        subnet_form.addRow("Floodfill", self.sub_floodfill)
        self.form_stack.addWidget(self.page_subnet)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(240)
        right_layout.addWidget(self.preview, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([460, 760])

        self.btn_new.clicked.connect(self.new_topology)
        self.btn_load_sample.clicked.connect(lambda: self.load_from_file(resolve_local_path("topology.sample.json")))
        self.btn_load_json.clicked.connect(self.choose_load_json)
        self.btn_save_json.clicked.connect(self.save_json_dialog)
        self.btn_validate.clicked.connect(self.validate_topology_ui)
        self.btn_generate.clicked.connect(self.generate_tsv_ui)
        self.btn_deploy.clicked.connect(self.deploy_topology_ui)
        self.btn_add_location.clicked.connect(self.add_location)
        self.btn_add_subnet.clicked.connect(self.add_subnet)
        self.btn_remove_selected.clicked.connect(self.remove_selected)
        self.tree.currentItemChanged.connect(self.on_tree_selection_changed)


        for widget in (self.loc_lat, self.loc_lon, self.loc_spread, self.sub_label, self.sub_cidr):
            widget.textChanged.connect(self.on_form_changed)
        for widget in (self.sub_routers, self.sub_floodfill):
            widget.valueChanged.connect(self.on_form_changed)
        self.sub_routers.valueChanged.connect(self.sync_subnet_limits)
        self.loc_country.currentIndexChanged.connect(self.on_location_country_selected)
        if self.loc_country.lineEdit() is not None:
            self.loc_country.lineEdit().editingFinished.connect(self.on_location_country_edited)
            self.loc_country.lineEdit().textEdited.connect(self.on_location_country_live_edit)
            try:
                self.loc_country.lineEdit().returnPressed.connect(self.on_location_country_edited)
            except Exception:
                pass
        self.loc_city.currentIndexChanged.connect(self.on_location_city_selected)
        if self.loc_city.lineEdit() is not None:
            self.loc_city.lineEdit().editingFinished.connect(self.on_location_city_edited)
            self.loc_city.lineEdit().textEdited.connect(self.on_location_city_live_edit)
            try:
                self.loc_city.lineEdit().returnPressed.connect(self.on_location_city_edited)
            except Exception:
                pass
        try:
            self.loc_country_completer.activated[str].connect(self.on_country_completer_activated)
        except Exception:
            try:
                self.loc_country_completer.activated.connect(self.on_country_completer_activated)
            except Exception:
                pass
        try:
            self.loc_city_completer.activated[str].connect(self.on_city_completer_activated)
        except Exception:
            try:
                self.loc_city_completer.activated.connect(self.on_city_completer_activated)
            except Exception:
                pass
        self.btn_loc_resolve.clicked.connect(self.resolve_selected_location)
        self.btn_loc_advanced.toggled.connect(self.toggle_location_advanced)
        self._reset_country_choices()
        self._reset_city_choices()

    def set_busy(self, busy):
        for btn in (self.btn_new, self.btn_load_sample, self.btn_load_json, self.btn_save_json, self.btn_validate, self.btn_generate, self.btn_deploy,
                    self.btn_add_location, self.btn_add_subnet, self.btn_remove_selected):
            btn.setEnabled(not busy)
        self.tree.setEnabled(not busy)

        for widget in (
            self.loc_country, self.loc_city, self.loc_code, self.btn_loc_resolve, self.btn_loc_advanced,
            self.loc_lat, self.loc_lon, self.loc_spread, self.sub_label, self.sub_cidr, self.sub_routers, self.sub_floodfill
        ):
            widget.setEnabled(not busy)

    def new_topology(self):
        self.topology = {"version": 1, "locations": []}
        self._preview_notice = "Created a new empty topology."
        self.refresh_all()

    def choose_load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, APP_NAME, resolve_local_path("."), "JSON Files (*.json);;All Files (*)")
        if path:
            self.load_from_file(path)

    def load_from_file(self, path, quiet=False):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise RuntimeError("Topology root must be a JSON object.")
            if "version" not in data:
                data["version"] = 1
            if "locations" not in data:
                data["locations"] = []
            self.topology = data
            self._preview_notice = f"Loaded topology file: {path}"
            self.refresh_all()
            if not quiet:
                QMessageBox.information(self, APP_NAME, f"Loaded topology from:\n{path}")
        except Exception as e:
            if not quiet:
                QMessageBox.critical(self, APP_NAME, f"Failed to load topology JSON:\n{e}")

    def save_json_dialog(self):
        default_path = self.paths["json"]
        path, _ = QFileDialog.getSaveFileName(self, APP_NAME, default_path, "JSON Files (*.json);;All Files (*)")
        if path:
            self.write_topology_json(path)
            QMessageBox.information(self, APP_NAME, f"Topology JSON saved to:\n{path}")

    def write_topology_json(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.topology, f, indent=2)

    def topology_summary(self):
        try:
            from topology_model import summarize_topology
            return summarize_topology(self.topology)
        except Exception:
            routers = 0
            floodfill = 0
            subnets = 0
            for loc in self.topology.get("locations", []):
                subnets += len(loc.get("subnets", []))
                for subnet in loc.get("subnets", []):
                    routers += safe_int(subnet.get("routers"), 0)
                    floodfill += safe_int(subnet.get("floodfill"), 0)
            return {"locations": len(self.topology.get("locations", [])), "subnets": subnets, "routers": routers, "floodfill": floodfill}

    def validate_topology(self, silent=False):
        try:
            from topology_model import topology_debug_report
            report = topology_debug_report(self.topology)
            self._preview_notice = "Validation succeeded."
            self.refresh_preview(extra=report)
            if not silent:
                QMessageBox.information(self, APP_NAME, "Topology validation succeeded.")
            return True, report
        except Exception as e:
            self._preview_notice = f"Validation failed: {e}"
            self.refresh_preview(extra=str(e))
            if not silent:
                QMessageBox.critical(self, APP_NAME, f"Topology validation failed:\n{e}")
            return False, str(e)

    def validate_topology_ui(self):
        try:
            from topology_model import topology_debug_report
            report = topology_debug_report(self.topology)
            self._preview_notice = "Validation succeeded."
            self.refresh_preview(extra=report)
            QMessageBox.information(self, APP_NAME, "Topology validation succeeded.")
            return True
        except Exception as e:
            self._preview_notice = f"Validation failed: {e}"
            self.refresh_preview(extra=str(e))
            QMessageBox.critical(self, APP_NAME, f"Topology validation failed:\n{e}")
            return False

    def generate_tsv_files(self):
        self.write_topology_json(self.paths["json"])
        exporter = resolve_local_path("export_subnet_tables.py")
        if not os.path.exists(exporter):
            raise RuntimeError(f"export_subnet_tables.py not found: {exporter}")
        cmd = [
            python_executable(), exporter, self.paths["json"],
            "--routers-out", self.paths["routers_tsv"],
            "--subnets-out", self.paths["subnets_tsv"],
        ]
        out, err, rc = run_cmd(cmd, timeout=30)
        if rc != 0:
            raise RuntimeError(err or out or "TSV generation failed.")
        return self.paths["json"], self.paths["routers_tsv"], self.paths["subnets_tsv"], out

    def generate_tsv_ui(self):
        ok, _ = self.validate_topology(silent=True)
        if not ok:
            QMessageBox.critical(self, APP_NAME, "Topology validation failed. Fix the highlighted topology details, then try again.")
            return
        try:
            json_path, routers_tsv, subnets_tsv, output = self.generate_tsv_files()
            self._preview_notice = f"Generated deployment files. JSON={json_path}, routers TSV={routers_tsv}, subnets TSV={subnets_tsv}"
            self.refresh_preview(extra=output)
            QMessageBox.information(self, APP_NAME, f"Deployment files generated successfully.\n\n{routers_tsv}\n{subnets_tsv}")
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"Failed to generate deployment files:\n{e}")

    def deploy_topology_ui(self):
        ok, _ = self.validate_topology(silent=True)
        if not ok:
            QMessageBox.critical(self, APP_NAME, "Topology validation failed. Fix the topology details, then deploy again.")
            return
        try:
            json_path, routers_tsv, subnets_tsv, output = self.generate_tsv_files()
            summary = self.topology_summary()
            self._preview_notice = f"Generated and queued topology deployment from {json_path}"
            self.refresh_preview(extra=output)
            self.deploy_requested.emit(json_path, routers_tsv, subnets_tsv, summary.get("routers", 0), summary.get("floodfill", 0))
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"Failed to prepare topology deployment:\n{e}")


    def _set_location_status(self, text, level="info"):
        colors = {
            "info": "#8ea7d1",
            "ok": "#7bd88f",
            "warn": "#e6c07b",
            "error": "#ff6b6b",
        }
        self.loc_auto_status.setText(str(text or ""))
        self.loc_auto_status.setStyleSheet(f"color:{colors.get(level, '#8ea7d1')};font-size:11px;")

    def _popup_combo(self, combo):
        try:
            combo.showPopup()
        except Exception:
            pass

    def _set_combo_items(self, combo, items, placeholder, typed_text="", keep_popup=False):
        items = [str(item).strip() for item in (items or []) if str(item).strip()]
        combo.blockSignals(True)
        try:
            current_text = str(typed_text or (combo.currentText() if combo.isEditable() else "") or "").strip()
            combo.clear()
            combo.addItems(items)
            if combo is self.loc_country and getattr(self, "loc_country_model", None) is not None:
                self.loc_country_model.setStringList(items)
            if combo is self.loc_city and getattr(self, "loc_city_model", None) is not None:
                self.loc_city_model.setStringList(items)
            if combo.lineEdit() is not None:
                combo.lineEdit().setPlaceholderText(placeholder)
                combo.lineEdit().setText(current_text)
                combo.lineEdit().setCursorPosition(len(combo.lineEdit().text()))
        finally:
            combo.blockSignals(False)
        if keep_popup and items:
            QTimer.singleShot(0, lambda: self._popup_combo(combo))

    def _reset_country_choices(self, typed_text=""):
        self._set_combo_items(
            self.loc_country,
            self._all_country_names,
            "Choose country...",
            typed_text=typed_text,
            keep_popup=False,
        )

    def _reset_city_choices(self, typed_text=""):
        self._set_combo_items(
            self.loc_city,
            self._city_choice_names,
            "Start typing a city or choose from the list",
            typed_text=typed_text,
            keep_popup=False,
        )

    def _filter_prefix_items(self, items, prefix):
        prefix_n = normalize_preset_text(prefix)
        if not prefix_n:
            return list(items)
        starts = [item for item in items if normalize_preset_text(item).startswith(prefix_n)]
        contains = [item for item in items if prefix_n in normalize_preset_text(item) and item not in starts]
        return starts + contains

    def _show_filtered_country_popup(self, typed_text):
        text = str(typed_text or "").strip()
        if getattr(self, "loc_country_completer", None) is None:
            return
        self.loc_country_completer.setCompletionPrefix(text)
        if self.loc_country.lineEdit() is not None:
            self.loc_country.lineEdit().setCursorPosition(len(self.loc_country.lineEdit().text()))
        QTimer.singleShot(0, self.loc_country_completer.complete)

    def _show_filtered_city_popup(self, typed_text):
        text = str(typed_text or "").strip()
        if getattr(self, "loc_city_completer", None) is None:
            return
        self.loc_city_completer.setCompletionPrefix(text)
        if self.loc_city.lineEdit() is not None:
            self.loc_city.lineEdit().setCursorPosition(len(self.loc_city.lineEdit().text()))
        QTimer.singleShot(0, self.loc_city_completer.complete)

    def _choose_exact_or_prefix(self, typed_text, items):

        typed = str(typed_text or "").strip()
        if not typed:
            return ""
        typed_n = normalize_preset_text(typed)
        exact = [item for item in items if normalize_preset_text(item) == typed_n]
        if exact:
            return exact[0]
        prefix = [item for item in items if normalize_preset_text(item).startswith(typed_n)]
        if len(prefix) == 1:
            return prefix[0]
        return typed

    def _commit_country_text(self, text, show_warn=True):
        if self._loading_form or self._selected_kind != "location" or self._selected_location_index is None:
            return False
        chosen = self._choose_exact_or_prefix(text, self._all_country_names)
        record = canonical_country_record(chosen)
        loc = self.topology["locations"][self._selected_location_index]
        typed = str(text or "").strip()
        if record is None and typed:
            loc["country"] = typed
            loc["country_code"] = ""
            loc["city"] = ""
            self.loc_code.setText("")
            self._city_choice_names = []
            self._loading_form = True
            try:
                self._set_combo_text(self.loc_country, typed)
                self._reset_city_choices("")
            finally:
                self._loading_form = False
            self._set_location_status("Country not recognized yet. Choose one from the list or type a valid full country name.", "warn" if show_warn else "info")
            self.refresh_all(keep_selection=True)
            return False
        country_name = record.get("name", "") if record else ""
        loc["country"] = country_name
        loc["country_code"] = record.get("code", "") if record else ""
        self.loc_code.setText(loc["country_code"])
        self._loading_form = True
        try:
            self._set_combo_text(self.loc_country, country_name)
        finally:
            self._loading_form = False
        # selecting a country should populate the city list and code,
        # but it should not silently auto-switch the location to the capital.
        loc["city"] = ""
        self._populate_city_choices(country_name, preferred_city="")
        self._loading_form = True
        try:
            self._set_combo_text(self.loc_city, "")
            self.loc_lat.setText(str(loc.get("center", {}).get("lat", 0.0)))
            self.loc_lon.setText(str(loc.get("center", {}).get("lon", 0.0)))
            self.loc_spread.setText(str(loc.get("map_spread", BUILDER_DEFAULT_MAP_SPREAD)))
        finally:
            self._loading_form = False
        if country_name:
            self._set_location_status(f"Country selected: {country_name}. Choose or type a city, then press Auto Fill Location.", "info")
        else:
            self._set_location_status("Choose a country and city. The builder will auto-fill map placement automatically.", "info")
        self.refresh_all(keep_selection=True)
        return True

    def _commit_city_text(self, text, allow_online=True):
        if self._loading_form or self._selected_kind != "location" or self._selected_location_index is None:
            return False
        typed = str(text or "").strip()
        chosen = self._choose_exact_or_prefix(typed, self._city_choice_names) if self._city_choice_names else typed
        loc = self.topology["locations"][self._selected_location_index]
        loc["city"] = chosen
        self._loading_form = True
        try:
            self._set_combo_text(self.loc_city, chosen)
        finally:
            self._loading_form = False
        if not chosen:
            self._set_location_status("Choose or type a city to auto-fill the map placement.", "info")
            self.refresh_all(keep_selection=True)
            return False
        country = str(loc.get("country", "")).strip()
        resolved = resolve_location_metadata(country, chosen, allow_online=False)
        if resolved and (resolved.get("country") or resolved.get("city")):
            return self._apply_resolved_location(resolved)
        if allow_online:
            return self.resolve_selected_location(allow_online=True, quiet=True)
        self._set_location_status(f"Country selected: {country or 'unknown'}. City coordinates are not resolved yet.", "warn")
        self.refresh_all(keep_selection=True)
        return False

    def _focus_new_location_country(self):
        try:
            self.form_stack.setCurrentWidget(self.page_location)
            self._reset_country_choices("")
            self.loc_country.setFocus()
            if self.loc_country.lineEdit() is not None:
                self.loc_country.lineEdit().clear()
            QTimer.singleShot(0, lambda: self._popup_combo(self.loc_country))
        except Exception:
            pass

    def on_country_completer_activated(self, text):
        self._commit_country_text(text, show_warn=True)

    def on_city_completer_activated(self, text):
        self._commit_city_text(text, allow_online=True)

    def toggle_location_advanced(self, checked):
        self.loc_advanced_frame.setVisible(bool(checked))
        self.btn_loc_advanced.setText("Hide Advanced Placement" if checked else "Show Advanced Placement")

    def _current_country_text(self):
        return str(self.loc_country.currentText() or "").strip()

    def _current_city_text(self):
        return str(self.loc_city.currentText() or "").strip()

    def _set_combo_text(self, combo, text):
        text = str(text or "").strip()
        if not text:
            if combo.isEditable() and combo.lineEdit() is not None:
                combo.lineEdit().clear()
            if combo.count() > 0:
                combo.setCurrentIndex(-1)
            return
        idx = -1
        for i in range(combo.count()):
            if normalize_preset_text(combo.itemText(i)) == normalize_preset_text(text):
                idx = i
                break
        if idx >= 0:
            combo.setCurrentIndex(idx)
            if combo.isEditable() and combo.lineEdit() is not None:
                combo.lineEdit().setText(combo.itemText(idx))
        elif combo.isEditable() and combo.lineEdit() is not None:
            combo.lineEdit().setText(text)

    def _populate_city_choices(self, country_name, preferred_city=""):
        entries = get_location_entries_for_country(country_name)
        self._city_choice_names = [entry.get("city", "") for entry in entries if entry.get("city")]
        current_city = str(preferred_city or self._current_city_text() or "").strip()
        self._loading_form = True
        try:
            self._reset_city_choices(current_city)
        finally:
            self._loading_form = False

    def _apply_resolved_location(self, resolved, keep_notice=True):
        if self._selected_kind != "location" or self._selected_location_index is None or not resolved:
            return False
        loc = self.topology["locations"][self._selected_location_index]
        loc["country"] = resolved.get("country", "")
        loc["country_code"] = str(resolved.get("country_code", "") or "").upper()
        loc["city"] = resolved.get("city", "")
        loc.setdefault("center", {})["lat"] = float(resolved.get("lat", 0.0))
        loc.setdefault("center", {})["lon"] = float(resolved.get("lon", 0.0))
        loc["map_spread"] = float(resolved.get("spread", BUILDER_DEFAULT_MAP_SPREAD))
        self._loading_form = True
        try:
            self._set_combo_text(self.loc_country, loc["country"])
            self._populate_city_choices(loc["country"], loc["city"])
            self._set_combo_text(self.loc_city, loc["city"])
            self.loc_code.setText(loc["country_code"])
            self.loc_lat.setText(str(loc["center"]["lat"]))
            self.loc_lon.setText(str(loc["center"]["lon"]))
            self.loc_spread.setText(str(loc["map_spread"]))
        finally:
            self._loading_form = False
        self._set_location_status(describe_location_resolution(resolved), "ok")
        if keep_notice:
            self._preview_notice = f"Resolved location automatically: {loc['city']}, {loc['country']}"
        self.refresh_all(keep_selection=True)
        return True

    def _location_status_from_model(self, loc):
        country = str(loc.get("country", "")).strip()
        city = str(loc.get("city", "")).strip()
        code = str(loc.get("country_code", "")).strip().upper()
        center = loc.get("center", {}) or {}
        lat = center.get("lat", 0.0)
        lon = center.get("lon", 0.0)
        spread = loc.get("map_spread", BUILDER_DEFAULT_MAP_SPREAD)
        if not country and not city:
            self._set_location_status("Choose a country and city. The builder will auto-fill map placement automatically.", "info")
            return
        resolved = resolve_location_metadata(country, city, allow_online=False)
        if resolved:
            same_lat = abs(float(resolved.get("lat", 0.0)) - float(lat or 0.0)) < 1e-6
            same_lon = abs(float(resolved.get("lon", 0.0)) - float(lon or 0.0)) < 1e-6
            same_spread = abs(float(resolved.get("spread", BUILDER_DEFAULT_MAP_SPREAD)) - float(spread or BUILDER_DEFAULT_MAP_SPREAD)) < 1e-6
            if same_lat and same_lon and same_spread and normalize_preset_text(resolved.get("country_code")) == normalize_preset_text(code):
                self._set_location_status(describe_location_resolution(resolved), "ok")
                return
        self._set_location_status("Loaded custom or legacy placement. You can keep it as-is or use Auto Fill Location to refresh the coordinates.", "warn")

    def resolve_selected_location(self, allow_online=True, quiet=False):
        if self._selected_kind != "location" or self._selected_location_index is None:
            return False
        country = self._current_country_text()
        city = self._current_city_text()
        self._commit_country_text(country, show_warn=False)
        country = self._current_country_text() or country
        if city:
            self._commit_city_text(city, allow_online=False)
            city = self._current_city_text() or city
        resolved = resolve_location_metadata(country, city, allow_online=allow_online)
        if resolved and (resolved.get("country") or resolved.get("city")):
            return self._apply_resolved_location(resolved)
        loc = self.topology["locations"][self._selected_location_index]
        record = canonical_country_record(country)
        loc["country"] = record.get("name") if record else country
        loc["country_code"] = record.get("code", "") if record else ""
        loc["city"] = city
        self.loc_code.setText(loc["country_code"])
        self._set_location_status("Could not resolve that city automatically. Keep the typed city or open Advanced Placement to set coordinates manually.", "warn")
        self.refresh_all(keep_selection=True)
        if not quiet:
            QMessageBox.warning(self, APP_NAME, "The selected city could not be resolved automatically.\n\nYou can keep the typed city and optionally use Advanced Placement to override the map coordinates.")
        return False

    def on_location_country_live_edit(self, text):
        if self._loading_form:
            return
        self._show_filtered_country_popup(text)

    def on_location_city_live_edit(self, text):
        if self._loading_form:
            return
        self._show_filtered_city_popup(text)

    def on_location_country_selected(self, index):
        if self._loading_form or self._selected_kind != "location" or self._selected_location_index is None or index < 0:
            return
        text = self.loc_country.itemText(index)
        if text:
            self._commit_country_text(text, show_warn=False)

    def on_location_country_edited(self):
        if self._loading_form or self._selected_kind != "location" or self._selected_location_index is None:
            return
        self._commit_country_text(self._current_country_text(), show_warn=True)

    def on_location_city_selected(self, index):
        if self._loading_form or self._selected_kind != "location" or self._selected_location_index is None or index < 0:
            return
        text = self.loc_city.itemText(index)
        if text:
            self._commit_city_text(text, allow_online=False)

    def on_location_city_edited(self):
        if self._loading_form or self._selected_kind != "location" or self._selected_location_index is None:
            return
        self._commit_city_text(self._current_city_text(), allow_online=False)

    def add_location(self):
        self.topology["locations"].append({
            "country": "",
            "country_code": "",
            "city": "",
            "center": {"lat": 0.0, "lon": 0.0},
            "map_spread": BUILDER_DEFAULT_MAP_SPREAD,
            "subnets": [],
        })
        new_index = len(self.topology["locations"]) - 1
        self._selected_kind = "location"
        self._selected_location_index = new_index
        self._selected_subnet_index = None
        self.refresh_all(keep_selection=True)
        try:
            item = self.tree.topLevelItem(new_index)
            if item is not None:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
        except Exception:
            pass
        QTimer.singleShot(0, self._focus_new_location_country)


    def add_subnet(self):
        loc_idx = self._selected_location_index
        if self._selected_kind == "subnet":
            loc_idx = self._selected_location_index
        if loc_idx is None or loc_idx >= len(self.topology.get("locations", [])):
            QMessageBox.information(self, APP_NAME, "Select a location first, then add a subnet.")
            return
        location = self.topology["locations"][loc_idx]
        subnet_idx = len(location.get("subnets", [])) + 1
        location.setdefault("subnets", []).append({
            "label": f"{location.get('country_code', 'XX').upper()}-{subnet_idx}",
            "cidr": f"10.{loc_idx + 10}.{subnet_idx}.0/24",
            "routers": 1,
            "floodfill": 0,
        })
        self.refresh_tree(select=("subnet", loc_idx, len(location["subnets"]) - 1))
        self.refresh_all(keep_selection=True)

    def remove_selected(self):
        if self._selected_kind == "subnet" and self._selected_location_index is not None and self._selected_subnet_index is not None:
            try:
                del self.topology["locations"][self._selected_location_index]["subnets"][self._selected_subnet_index]
            except Exception:
                return
        elif self._selected_kind == "location" and self._selected_location_index is not None:
            try:
                del self.topology["locations"][self._selected_location_index]
            except Exception:
                return
        else:
            return
        self._selected_kind = None
        self._selected_location_index = None
        self._selected_subnet_index = None
        self.refresh_all()

    def on_tree_selection_changed(self, current, _previous):
        if current is None:
            self._selected_kind = None
            self._selected_location_index = None
            self._selected_subnet_index = None
            self.form_stack.setCurrentWidget(self.page_blank)
            return
        data = current.data(0, Qt.ItemDataRole.UserRole if PYQT_VER == 6 else Qt.UserRole)
        if not data:
            self.form_stack.setCurrentWidget(self.page_blank)
            return
        self._selected_kind, self._selected_location_index, self._selected_subnet_index = data
        self.load_form_from_selection()

    def load_form_from_selection(self):
        self._loading_form = True
        try:
            if self._selected_kind == "location":
                loc = self.topology["locations"][self._selected_location_index]
                center = loc.setdefault("center", {"lat": 0.0, "lon": 0.0})
                country_val = str(loc.get("country", ""))
                city_val = str(loc.get("city", ""))
                self._reset_country_choices(country_val)
                self._set_combo_text(self.loc_country, country_val)
                self._populate_city_choices(country_val, city_val)
                self._set_combo_text(self.loc_city, city_val)
                self.loc_code.setText(str(loc.get("country_code", "")))
                lat_val = center.get("lat", 0.0)
                lon_val = center.get("lon", 0.0)
                spread_val = loc.get("map_spread", BUILDER_DEFAULT_MAP_SPREAD)
                self.loc_lat.setText(str(lat_val))
                self.loc_lon.setText(str(lon_val))
                self.loc_spread.setText(str(spread_val))
                self._location_status_from_model(loc)
                self.form_stack.setCurrentWidget(self.page_location)
            elif self._selected_kind == "subnet":
                subnet = self.topology["locations"][self._selected_location_index]["subnets"][self._selected_subnet_index]
                self.sub_label.setText(str(subnet.get("label", "")))
                self.sub_cidr.setText(str(subnet.get("cidr", "")))
                self.sub_routers.setValue(max(1, safe_int(subnet.get("routers"), 1)))
                self.sub_floodfill.setValue(max(0, safe_int(subnet.get("floodfill"), 0)))
                self.sync_subnet_limits()
                self.form_stack.setCurrentWidget(self.page_subnet)
            else:
                self.form_stack.setCurrentWidget(self.page_blank)
        finally:
            self._loading_form = False

    def sync_subnet_limits(self):
        self.sub_floodfill.setMaximum(self.sub_routers.value())
        if self.sub_floodfill.value() > self.sub_routers.value():
            self.sub_floodfill.setValue(self.sub_routers.value())

    def on_form_changed(self, *_args):
        if self._loading_form:
            return

        if self._selected_kind == "location" and self._selected_location_index is not None:
            loc = self.topology["locations"][self._selected_location_index]
            country = self._current_country_text()
            record = canonical_country_record(country)
            loc["country"] = record.get("name") if record else country
            loc["country_code"] = record.get("code", "") if record else self.loc_code.text().strip().upper()
            loc["city"] = self._current_city_text()
            try:
                lat = parse_builder_float(self.loc_lat.text(), minimum=-90.0, maximum=90.0)
                lon = parse_builder_float(self.loc_lon.text(), minimum=-180.0, maximum=180.0)
                spread = parse_builder_float(self.loc_spread.text(), minimum=0.0, maximum=10.0)
            except Exception:
                return
            loc.setdefault("center", {})["lat"] = lat
            loc.setdefault("center", {})["lon"] = lon
            loc["map_spread"] = spread
            self._set_location_status("Using advanced placement overrides for this location.", "warn")
        elif self._selected_kind == "subnet" and self._selected_location_index is not None and self._selected_subnet_index is not None:
            subnet = self.topology["locations"][self._selected_location_index]["subnets"][self._selected_subnet_index]
            subnet["label"] = self.sub_label.text().strip()
            subnet["cidr"] = self.sub_cidr.text().strip()
            subnet["routers"] = int(self.sub_routers.value())
            subnet["floodfill"] = int(self.sub_floodfill.value())
        self.refresh_all(keep_selection=True)

    def refresh_tree(self, select=None):
        self.tree.blockSignals(True)
        try:
            self.tree.clear()
            for loc_idx, location in enumerate(self.topology.get("locations", [])):
                country_text = str(location.get("country", "") or "").strip()
                city = str(location.get("city", "")).strip()
                label = country_text or f"(new location {loc_idx + 1})"
                city_suffix = f" · {city}" if city else ""
                value_text = f"{location.get('country_code', '')}{city_suffix}".strip() or "Select country and city"
                loc_item = QTreeWidgetItem([label, value_text])
                loc_item.setData(0, Qt.ItemDataRole.UserRole if PYQT_VER == 6 else Qt.UserRole, ("location", loc_idx, None))
                self.tree.addTopLevelItem(loc_item)
                for subnet_idx, subnet in enumerate(location.get("subnets", [])):
                    subnet_item = QTreeWidgetItem([
                        str(subnet.get("label", "(unnamed subnet)")),
                        f"{subnet.get('cidr', '')} · R{subnet.get('routers', 0)} · FF{subnet.get('floodfill', 0)}",
                    ])
                    subnet_item.setData(0, Qt.ItemDataRole.UserRole if PYQT_VER == 6 else Qt.UserRole, ("subnet", loc_idx, subnet_idx))
                    loc_item.addChild(subnet_item)
                loc_item.setExpanded(True)
            if select is not None:
                kind, loc_idx, subnet_idx = select
                if kind == "location" and 0 <= loc_idx < self.tree.topLevelItemCount():
                    item = self.tree.topLevelItem(loc_idx)
                    self.tree.setCurrentItem(item)
                    if item is not None:
                        self.tree.scrollToItem(item)
                elif kind == "subnet" and 0 <= loc_idx < self.tree.topLevelItemCount():
                    parent = self.tree.topLevelItem(loc_idx)
                    if parent and 0 <= subnet_idx < parent.childCount():
                        item = parent.child(subnet_idx)
                        self.tree.setCurrentItem(item)
                        if item is not None:
                            self.tree.scrollToItem(item)
        finally:
            self.tree.blockSignals(False)

    def refresh_preview(self, extra=None):
        summary = self.topology_summary()
        self.summary.setText(
            f"Builder topology: {summary.get('locations', 0)} location(s), {summary.get('subnets', 0)} subnet(s), "
            f"{summary.get('routers', 0)} router(s), {summary.get('floodfill', 0)} floodfill. "
            f"Outputs: {self.paths['json']}, {self.paths['routers_tsv']}, {self.paths['subnets_tsv']}"
        )
        self.summary_changed.emit(summary.get("routers", 0), summary.get("floodfill", 0))
        preview_chunks = []
        if self._preview_notice:
            preview_chunks.append(self._preview_notice)
        if extra:
            preview_chunks.append(str(extra).strip())
        topology_json = json.dumps(self.topology, indent=2)
        lines = topology_json.splitlines()
        if len(lines) > BUILDER_PREVIEW_MAX_LINES:
            topology_json = "\n".join(lines[:BUILDER_PREVIEW_MAX_LINES]) + "\n..."
        preview_chunks.append("Current topology JSON\n=====================")
        preview_chunks.append(topology_json)
        self.preview.setPlainText("\n\n".join(chunk for chunk in preview_chunks if chunk))

    def refresh_all(self, keep_selection=False):
        selection = None
        if keep_selection and self._selected_kind is not None:
            selection = (self._selected_kind, self._selected_location_index, self._selected_subnet_index)
        self.refresh_tree(select=selection)
        self.refresh_preview()
        if selection is not None:
            self.load_form_from_selection()
        elif self.tree.currentItem() is None:
            self.form_stack.setCurrentWidget(self.page_blank)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1720, 980)

        self.snapshot = {"routers": []}
        self.selected_router_id = None
        self.router_cards = {}
        self.action_thread = None
        self.deploy_thread = None
        self.scenario_thread = None
        self.measurement_thread = None
        self.campaign_thread = None
        self._busy = False
        self.scenario_state = {
            "status": "idle",
            "run_id": None,
            "run_dir": None,
            "completed_cycles": 0,
            "requested_cycles": 0,
            "actions_executed": 0,
            "last_message": "No scenario run yet.",
            "scenario_type": "random_stop_start",
            "target_group": "non_floodfill",
            "target_mode": "random_pool",
            "selected_router_ids": [],
            "seed": 0,
        }
        self.measurement_state = {
            "status": "idle",
            "run_id": None,
            "run_dir": None,
            "completed_probes": 0,
            "requested_probes": 0,
            "last_message": "No measurement run yet.",
            "target_group": "active_all",
            "fetch_timeout": MEASUREMENT_FETCH_TIMEOUT_DEFAULT,
            "summary": {},
        }
        self.campaign_state = {
            "status": "idle",
            "run_id": None,
            "run_dir": None,
            "scenario_run_id": None,
            "baseline_run_id": None,
            "final_run_id": None,
            "interim_measurements": 0,
            "cycle_trigger_measurements": 0,
            "periodic_measurements": 0,
            "last_message": "No campaign run yet.",
            "summary": {},
        }
        self._last_grid_cols = 0
        self._detail_cache = {
            "router_id": None,
            "config_text": "",
            "config_loaded_at": 0.0,
            "logs_text": "",
            "logs_loaded_at": 0.0,
        }
        self._topology_sync_enabled = True
        self._last_applied_topology = None
        self._pending_requested_topology = None
        self._pending_requested_tsv = None
        self._post_deploy_state = None
        self.telemetry = TelemetrySessionManager()

        self.build_ui()
        self.apply_styles()
        self.start_monitor()

        self.deploy_log_timer = QTimer(self)
        self.deploy_log_timer.timeout.connect(self.refresh_deployment_log)
        self.deploy_log_timer.start(1200)

        self.requested_router_count = 0
        self.requested_floodfill_count = 0

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel("I2P Private Testnet Emulator")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Native PyQt control center for deployment, live monitoring, router control, logs, configuration review, and scenario operations")
        subtitle.setObjectName("HeaderSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box)
        header_layout.addStretch(1)

        self.stat_total = StatPill("Routers", "0")
        self.stat_active = StatPill("Active", "0")
        self.stat_stopped = StatPill("Stopped", "0")
        self.stat_failed = StatPill("Failed", "0")
        self.stat_ff = StatPill("Floodfill", "0")
        self.stat_base = StatPill("Testnet Base", "not found")

        for stat in (self.stat_total, self.stat_active, self.stat_stopped, self.stat_failed, self.stat_ff, self.stat_base):
            stat.setMinimumWidth(118)
            header_layout.addWidget(stat)

        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal if PYQT_VER == 6 else Qt.Horizontal)
        root.addWidget(splitter, 1)

        splitter.addWidget(self.build_left_panel())
        splitter.addWidget(self.build_center_panel())
        splitter.addWidget(self.build_right_panel())

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([330, 980, 430])
        self.main_splitter = splitter

    def build_left_panel(self):
        panel = QFrame()
        panel.setObjectName("SidePanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        control_box = QGroupBox("Emulator Control")
        control_layout = QVBoxLayout(control_box)
        control_layout.setSpacing(10)

        row1 = QHBoxLayout()
        self.btn_stop_emulator = QPushButton("Stop Emulator")
        self.btn_destroy = QPushButton("Destroy")
        row1.addWidget(self.btn_stop_emulator)
        row1.addWidget(self.btn_destroy)
        control_layout.addLayout(row1)

        self.deploy_status = QLabel(
            "Builder-driven deployment is the primary workflow. "
            "Use the Builder tab to validate, generate TSV files, and deploy the network."
        )
        self.deploy_status.setWordWrap(True)
        self.deploy_status.setStyleSheet("color:#c8d4ea;")
        control_layout.addWidget(self.deploy_status)

        global_box = QGroupBox("Fleet Actions")
        global_layout = QVBoxLayout(global_box)
        r1 = QHBoxLayout()
        self.btn_start_all = QPushButton("Start All Routers")
        self.btn_stop_all = QPushButton("Stop All Routers")
        r1.addWidget(self.btn_start_all)
        r1.addWidget(self.btn_stop_all)

        r2 = QHBoxLayout()
        self.btn_restart_all = QPushButton("Restart All Routers")
        self.btn_refresh = QPushButton("Refresh Now")
        r2.addWidget(self.btn_restart_all)
        r2.addWidget(self.btn_refresh)

        global_layout.addLayout(r1)
        global_layout.addLayout(r2)

        log_box = QGroupBox("Deployment Log")
        log_layout = QVBoxLayout(log_box)
        self.deployment_log = QPlainTextEdit()
        self.deployment_log.setReadOnly(True)
        self.deployment_log.setMinimumHeight(300)
        log_layout.addWidget(self.deployment_log)

        layout.addWidget(control_box)
        layout.addWidget(global_box)
        layout.addWidget(log_box, 1)

        self.btn_stop_emulator.clicked.connect(lambda: self.start_deploy_action("stop_emulator"))
        self.btn_destroy.clicked.connect(lambda: self.start_deploy_action("destroy"))

        self.btn_refresh.clicked.connect(self.refresh_now)
        self.btn_start_all.clicked.connect(lambda: self.run_bulk_action("start"))
        self.btn_stop_all.clicked.connect(lambda: self.run_bulk_action("stop"))
        self.btn_restart_all.clicked.connect(lambda: self.run_bulk_action("restart"))

        return panel

    def build_center_panel(self):
        panel = QFrame()
        panel.setObjectName("CenterPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.info_line = QLabel("Waiting for network snapshot...")
        self.info_line.setStyleSheet("color:#8ea7d1;font-size:12px;")
        self.info_line.setWordWrap(True)
        layout.addWidget(self.info_line)

        self.center_tabs = QTabWidget()
        layout.addWidget(self.center_tabs, 1)

        fleet_page = QWidget()
        fleet_layout = QVBoxLayout(fleet_page)
        fleet_layout.setContentsMargins(0, 0, 0, 0)
        fleet_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame if PYQT_VER == 6 else QFrame.NoFrame)
        self.router_scroll = scroll

        wrapper = QWidget()
        self.router_grid_wrapper = wrapper
        self.router_grid = QGridLayout(wrapper)
        self.router_grid.setContentsMargins(CARD_GRID_MARGIN, CARD_GRID_MARGIN, CARD_GRID_MARGIN, CARD_GRID_MARGIN)
        self.router_grid.setHorizontalSpacing(CARD_GRID_SPACING)
        self.router_grid.setVerticalSpacing(CARD_GRID_SPACING)
        scroll.setWidget(wrapper)
        fleet_layout.addWidget(scroll, 1)

        self.builder_panel = TopologyBuilderPanel()
        self.builder_panel.deploy_requested.connect(self.start_topology_builder_deploy)
        self.builder_panel.summary_changed.connect(self.on_builder_summary_changed)

        self.topology_panel = TopologyPanel()
        self.topology_panel.router_selected.connect(self.select_router)

        self.scenario_panel = self.build_scenario_panel()
        self.history_panel = self.build_history_panel()
        self.measurement_panel = self.build_measurement_panel()

        self.map_panel = LeafletMapPanel()
        self.map_panel.router_selected.connect(self.select_router)
        self.map_panel.console_requested.connect(self.open_console_by_id)

        self.center_tabs.addTab(fleet_page, "Fleet")
        self.center_tabs.addTab(self.builder_panel, "Topology Builder")
        self.center_tabs.addTab(self.topology_panel, "Topology")
        self.center_tabs.addTab(self.scenario_panel, "Scenarios")
        self.center_tabs.addTab(self.history_panel, "Scenario History")
        self.center_tabs.addTab(self.measurement_panel, "Measurements")
        self.center_tabs.addTab(self.map_panel, "Network Map")

        return panel

    def build_scenario_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame if PYQT_VER == 6 else QFrame.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header_box = QGroupBox("Scenario Operations")
        header_layout = QHBoxLayout(header_box)
        header_label = QLabel("Configure churn in Setup, run it from Execution, and use Campaign for baseline → scenario → post-scenario probe orchestration.")
        header_label.setWordWrap(True)
        header_layout.addWidget(header_label, 1)
        layout.addWidget(header_box)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        setup_page = QWidget()
        setup_layout = QVBoxLayout(setup_page)
        setup_layout.setContentsMargins(8, 8, 8, 8)
        setup_layout.setSpacing(10)

        config_box = QGroupBox("Scenario Setup")
        form = QFormLayout(config_box)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow if PYQT_VER == 6 else QFormLayout.AllNonFixedFieldsGrow)

        self.scenario_preset_combo = QComboBox()
        self.scenario_preset_combo.addItem("Custom (manual)", "custom")
        for preset_id, preset in SCENARIO_PRESETS.items():
            self.scenario_preset_combo.addItem(preset.get("name", preset_id), preset_id)

        self.btn_apply_scenario_preset = QPushButton("Apply Preset")
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.scenario_preset_combo, 1)
        preset_row.addWidget(self.btn_apply_scenario_preset)

        self.scenario_experiment_label = QLineEdit()
        self.scenario_experiment_label.setPlaceholderText("scenario label")

        self.scenario_type_combo = QComboBox()
        self.scenario_type_combo.addItem("Random stop/start churn", "random_stop_start")
        self.scenario_type_combo.addItem("Random restart churn", "random_restart")

        self.scenario_target_combo = QComboBox()
        self.scenario_target_combo.addItem("Non-floodfill only", "non_floodfill")
        self.scenario_target_combo.addItem("All routers", "all")
        self.scenario_target_combo.addItem("Floodfill only", "floodfill_only")

        self.scenario_target_mode_combo = QComboBox()
        self.scenario_target_mode_combo.addItem("Random eligible router each event", "random_pool")
        self.scenario_target_mode_combo.addItem("Selected routers (one-at-a-time round-robin)", "selected_routers")

        self.scenario_selected_routers = QLineEdit()
        self.scenario_selected_routers.setPlaceholderText("e.g. 2,4,7")
        self.scenario_selected_routers.setToolTip("Comma- or space-separated router IDs used only when target mode is set to selected routers.")

        self.scenario_min_interval = QDoubleSpinBox()
        self.scenario_min_interval.setRange(1.0, 3600.0)
        self.scenario_min_interval.setDecimals(1)
        self.scenario_min_interval.setSingleStep(1.0)
        self.scenario_min_interval.setValue(SCENARIO_DEFAULT_MIN_INTERVAL)
        self.scenario_min_interval.setSuffix(" s")

        self.scenario_max_interval = QDoubleSpinBox()
        self.scenario_max_interval.setRange(1.0, 3600.0)
        self.scenario_max_interval.setDecimals(1)
        self.scenario_max_interval.setSingleStep(1.0)
        self.scenario_max_interval.setValue(SCENARIO_DEFAULT_MAX_INTERVAL)
        self.scenario_max_interval.setSuffix(" s")

        self.scenario_downtime = QDoubleSpinBox()
        self.scenario_downtime.setRange(1.0, 3600.0)
        self.scenario_downtime.setDecimals(1)
        self.scenario_downtime.setSingleStep(1.0)
        self.scenario_downtime.setValue(SCENARIO_DEFAULT_DOWNTIME)
        self.scenario_downtime.setSuffix(" s")

        self.scenario_cycles = QSpinBox()
        self.scenario_cycles.setRange(1, 10000)
        self.scenario_cycles.setValue(SCENARIO_DEFAULT_MAX_CYCLES)

        self.scenario_seed_input = QLineEdit()
        self.scenario_seed_input.setPlaceholderText("leave blank for random")
        self.scenario_seed_input.setToolTip("Optional integer seed for repeatable random-mode churn.")

        self.scenario_help = QLabel(
            "Each churn event acts on one router. In selected-router mode, routers are processed one at a time in round-robin order. "
            "Downtime is how long the router stays stopped before restart. Min/Max interval is the wait before the next event."
        )
        self.scenario_help.setWordWrap(True)
        self.scenario_help.setStyleSheet("color:#9fb1d1;font-size:12px;")

        form.addRow("Scenario preset", preset_row)
        form.addRow("Experiment label", self.scenario_experiment_label)
        form.addRow("Scenario type", self.scenario_type_combo)
        form.addRow("Eligible router pool", self.scenario_target_combo)
        form.addRow("Target mode", self.scenario_target_mode_combo)
        form.addRow("Selected routers", self.scenario_selected_routers)
        form.addRow("Min interval", self.scenario_min_interval)
        form.addRow("Max interval", self.scenario_max_interval)
        form.addRow("Downtime", self.scenario_downtime)
        form.addRow("Churn events", self.scenario_cycles)
        form.addRow("Seed", self.scenario_seed_input)
        form.addRow(self.scenario_help)
        setup_layout.addWidget(config_box)
        tabs.addTab(setup_page, "Setup")

        execution_page = QWidget()
        execution_layout = QVBoxLayout(execution_page)
        execution_layout.setContentsMargins(8, 8, 8, 8)
        execution_layout.setSpacing(10)

        run_box = QGroupBox("Scenario Execution")
        run_form = QFormLayout(run_box)
        run_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow if PYQT_VER == 6 else QFormLayout.AllNonFixedFieldsGrow)
        execution_help = QLabel("Use the current Setup values to start or stop one churn scenario. Status and activity are shown below for easier monitoring.")
        execution_help.setWordWrap(True)
        execution_help.setStyleSheet("color:#9fb1d1;font-size:12px;")
        run_form.addRow(execution_help)
        btn_row = QHBoxLayout()
        self.btn_scenario_start = QPushButton("Start Scenario")
        self.btn_scenario_stop = QPushButton("Stop Scenario")
        btn_row.addWidget(self.btn_scenario_start)
        btn_row.addWidget(self.btn_scenario_stop)
        run_form.addRow("Run control", btn_row)
        execution_layout.addWidget(run_box)

        summary_box = QGroupBox("Scenario Status")
        summary_layout = QVBoxLayout(summary_box)
        self.scenario_summary = QPlainTextEdit()
        self.scenario_summary.setReadOnly(True)
        configure_compact_text_view(self.scenario_summary, min_height=140, max_height=220)
        summary_layout.addWidget(self.scenario_summary)
        execution_layout.addWidget(summary_box)

        log_box = QGroupBox("Scenario Activity Log")
        log_layout = QVBoxLayout(log_box)
        self.scenario_log = QPlainTextEdit()
        self.scenario_log.setReadOnly(True)
        configure_compact_text_view(self.scenario_log, min_height=180, max_height=260)
        log_layout.addWidget(self.scenario_log)
        execution_layout.addWidget(log_box)
        tabs.addTab(execution_page, "Execution")

        campaign_page = QWidget()
        campaign_layout = QVBoxLayout(campaign_page)
        campaign_layout.setContentsMargins(8, 8, 8, 8)
        campaign_layout.setSpacing(10)

        campaign_box = QGroupBox("Scenario Campaign")
        campaign_form = QFormLayout(campaign_box)
        campaign_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow if PYQT_VER == 6 else QFormLayout.AllNonFixedFieldsGrow)

        self.campaign_probe_interval = QDoubleSpinBox()
        self.campaign_probe_interval.setRange(0.0, 3600.0)
        self.campaign_probe_interval.setDecimals(1)
        self.campaign_probe_interval.setSingleStep(1.0)
        self.campaign_probe_interval.setValue(15.0)
        self.campaign_probe_interval.setSuffix(" s")
        try:
            self.campaign_probe_interval.setSpecialValueText("Off")
        except Exception:
            pass

        self.campaign_post_settle = QDoubleSpinBox()
        self.campaign_post_settle.setRange(0.0, 600.0)
        self.campaign_post_settle.setDecimals(1)
        self.campaign_post_settle.setSingleStep(1.0)
        self.campaign_post_settle.setValue(8.0)
        self.campaign_post_settle.setSuffix(" s")

        self.campaign_cycle_probe_combo = QComboBox()
        self.campaign_cycle_probe_combo.addItem("Yes", True)
        self.campaign_cycle_probe_combo.addItem("No", False)

        campaign_help = QLabel("Uses the current measurement target group and HTTP fetch timeout for baseline, in-scenario, and post-scenario measurements.")
        campaign_help.setWordWrap(True)
        campaign_help.setStyleSheet("color:#9fb1d1;font-size:12px;")
        campaign_form.addRow(campaign_help)
        campaign_form.addRow("Periodic probe interval", self.campaign_probe_interval)
        campaign_form.addRow("Probe after each event", self.campaign_cycle_probe_combo)
        campaign_form.addRow("Post-scenario settle", self.campaign_post_settle)

        campaign_btn_row = QHBoxLayout()
        self.btn_campaign_start = QPushButton("Start Campaign")
        self.btn_campaign_stop = QPushButton("Stop Campaign")
        campaign_btn_row.addWidget(self.btn_campaign_start)
        campaign_btn_row.addWidget(self.btn_campaign_stop)
        campaign_form.addRow("Campaign control", campaign_btn_row)
        campaign_layout.addWidget(campaign_box)

        campaign_status_box = QGroupBox("Campaign Status")
        campaign_status_layout = QVBoxLayout(campaign_status_box)
        self.campaign_summary = QPlainTextEdit()
        self.campaign_summary.setReadOnly(True)
        configure_compact_text_view(self.campaign_summary, min_height=150, max_height=220)
        campaign_status_layout.addWidget(self.campaign_summary)
        campaign_layout.addWidget(campaign_status_box)

        campaign_log_box = QGroupBox("Campaign Activity Log")
        campaign_log_layout = QVBoxLayout(campaign_log_box)
        self.campaign_log = QPlainTextEdit()
        self.campaign_log.setReadOnly(True)
        configure_compact_text_view(self.campaign_log, min_height=180, max_height=250)
        campaign_log_layout.addWidget(self.campaign_log)
        campaign_layout.addWidget(campaign_log_box)
        tabs.addTab(campaign_page, "Campaign")

        self.btn_apply_scenario_preset.clicked.connect(self.apply_selected_scenario_preset)
        self.btn_scenario_start.clicked.connect(self.start_churn_scenario)
        self.btn_scenario_stop.clicked.connect(self.stop_churn_scenario)
        self.btn_campaign_start.clicked.connect(self.start_campaign_run)
        self.btn_campaign_stop.clicked.connect(self.stop_campaign_run)
        if hasattr(self, "scenario_target_mode_combo"):
            self.scenario_target_mode_combo.currentIndexChanged.connect(self.update_scenario_target_mode_ui)
        if hasattr(self, "scenario_target_combo"):
            self.scenario_target_combo.currentIndexChanged.connect(self.update_scenario_target_mode_ui)
        if not self.scenario_experiment_label.text().strip():
            self.scenario_experiment_label.setText("moderate_churn_non_floodfill")
        self.update_scenario_target_mode_ui()
        self.update_scenario_panel()
        self.update_campaign_panel()
        scroll.setWidget(page)
        return scroll

    def build_history_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame if PYQT_VER == 6 else QFrame.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        controls_box = QGroupBox("Scenario History")
        controls_layout = QHBoxLayout(controls_box)
        controls_layout.addWidget(QLabel("Review high-level outcomes first, then move into analysis and raw records."))
        controls_layout.addStretch(1)
        self.btn_history_refresh = QPushButton("Refresh History")
        controls_layout.addWidget(self.btn_history_refresh)
        layout.addWidget(controls_box)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        overview_page = QWidget()
        overview_layout = QVBoxLayout(overview_page)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        overview_layout.setSpacing(10)

        overview_split = QSplitter(Qt.Orientation.Vertical if PYQT_VER == 6 else Qt.Vertical)

        overview_box = QGroupBox("Scenario Overview")
        overview_box_layout = QVBoxLayout(overview_box)
        self.history_overview_view = QPlainTextEdit()
        self.history_overview_view.setReadOnly(True)
        configure_compact_text_view(self.history_overview_view, min_height=110, max_height=180)
        overview_box_layout.addWidget(self.history_overview_view)
        overview_split.addWidget(overview_box)

        fleet_box = QGroupBox("Fleet Resilience Summary")
        fleet_layout = QVBoxLayout(fleet_box)
        self.history_fleet_view = QPlainTextEdit()
        self.history_fleet_view.setReadOnly(True)
        configure_compact_text_view(self.history_fleet_view, min_height=130, max_height=210)
        fleet_layout.addWidget(self.history_fleet_view)
        overview_split.addWidget(fleet_box)

        latest_run_box = QGroupBox("Latest Scenario Metrics")
        latest_run_layout = QVBoxLayout(latest_run_box)
        self.history_latest_run_view = QPlainTextEdit()
        self.history_latest_run_view.setReadOnly(True)
        configure_compact_text_view(self.history_latest_run_view, min_height=140, max_height=220)
        latest_run_layout.addWidget(self.history_latest_run_view)
        overview_split.addWidget(latest_run_box)
        overview_split.setChildrenCollapsible(False)
        overview_split.setStretchFactor(0, 1)
        overview_split.setStretchFactor(1, 1)
        overview_split.setStretchFactor(2, 1)
        overview_layout.addWidget(overview_split, 1)
        tabs.addTab(overview_page, "Overview")

        analysis_page = QWidget()
        analysis_layout = QVBoxLayout(analysis_page)
        analysis_layout.setContentsMargins(8, 8, 8, 8)
        analysis_layout.setSpacing(10)

        analysis_split = QSplitter(Qt.Orientation.Vertical if PYQT_VER == 6 else Qt.Vertical)

        router_box = QGroupBox("Router Churn Summary")
        router_layout = QVBoxLayout(router_box)
        self.history_router_view = QPlainTextEdit()
        self.history_router_view.setReadOnly(True)
        configure_compact_text_view(self.history_router_view, min_height=150, max_height=230)
        router_layout.addWidget(self.history_router_view)
        analysis_split.addWidget(router_box)

        comparison_box = QGroupBox("Recent Scenario Comparison")
        comparison_layout = QVBoxLayout(comparison_box)
        self.history_comparison_view = QPlainTextEdit()
        self.history_comparison_view.setReadOnly(True)
        configure_compact_text_view(self.history_comparison_view, min_height=150, max_height=230)
        comparison_layout.addWidget(self.history_comparison_view)
        analysis_split.addWidget(comparison_box)
        analysis_split.setChildrenCollapsible(False)
        analysis_split.setStretchFactor(0, 1)
        analysis_split.setStretchFactor(1, 1)
        analysis_layout.addWidget(analysis_split, 1)
        tabs.addTab(analysis_page, "Analysis")

        records_page = QWidget()
        records_layout = QVBoxLayout(records_page)
        records_layout.setContentsMargins(8, 8, 8, 8)
        records_layout.setSpacing(10)

        records_split = QSplitter(Qt.Orientation.Vertical if PYQT_VER == 6 else Qt.Vertical)

        telemetry_box = QGroupBox("Recent Telemetry Sessions")
        telemetry_layout = QVBoxLayout(telemetry_box)
        self.history_telemetry_view = QPlainTextEdit()
        self.history_telemetry_view.setReadOnly(True)
        configure_compact_text_view(self.history_telemetry_view, min_height=150, max_height=230)
        telemetry_layout.addWidget(self.history_telemetry_view)
        records_split.addWidget(telemetry_box)

        scenarios_box = QGroupBox("Recent Scenario Records")
        scenarios_layout = QVBoxLayout(scenarios_box)
        self.history_scenarios_view = QPlainTextEdit()
        self.history_scenarios_view.setReadOnly(True)
        configure_compact_text_view(self.history_scenarios_view, min_height=150, max_height=230)
        scenarios_layout.addWidget(self.history_scenarios_view)
        records_split.addWidget(scenarios_box)
        records_split.setChildrenCollapsible(False)
        records_split.setStretchFactor(0, 1)
        records_split.setStretchFactor(1, 1)
        records_layout.addWidget(records_split, 1)
        tabs.addTab(records_page, "Records")

        self.btn_history_refresh.clicked.connect(self.update_history_panel)
        scroll.setWidget(page)
        self.update_history_panel()
        return scroll

    def build_measurement_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame if PYQT_VER == 6 else QFrame.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        def _wrap_tab_page(content_widget):
            inner = QScrollArea()
            inner.setWidgetResizable(True)
            inner.setFrameShape(QFrame.Shape.NoFrame if PYQT_VER == 6 else QFrame.NoFrame)
            inner.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if PYQT_VER == 6 else Qt.ScrollBarAsNeeded)
            inner.setWidget(content_widget)
            return inner

        header_box = QGroupBox("Measurement Operations")
        header_layout = QHBoxLayout(header_box)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_label = QLabel("Use Runs for measurement execution, Summaries for result review and export, Path Records for authoritative tunnel records, and Path Analysis for comparison and interpretation.")
        header_label.setWordWrap(True)
        header_layout.addWidget(header_label, 1)
        layout.addWidget(header_box)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        runs_page = QWidget()
        runs_layout = QVBoxLayout(runs_page)
        runs_layout.setContentsMargins(8, 8, 8, 8)
        runs_layout.setSpacing(8)

        controls_box = QGroupBox("Run Probes")
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(6)
        controls_help = QLabel("Run one measurement pass against the current testnet state. Use Refresh to reload the latest results from disk.")
        controls_help.setWordWrap(True)
        controls_layout.addWidget(controls_help)

        controls_form = QFormLayout()
        controls_form.setContentsMargins(0, 0, 0, 0)
        controls_form.setSpacing(6)
        self.measurement_target_combo = QComboBox()
        self.measurement_target_combo.addItem("Active routers (all)", "active_all")
        self.measurement_target_combo.addItem("Active non-floodfill", "active_non_floodfill")
        self.measurement_target_combo.addItem("Active floodfill only", "active_floodfill")
        self.measurement_target_combo.addItem("Selected router only", "selected_only")

        self.measurement_fetch_timeout = QDoubleSpinBox()
        self.measurement_fetch_timeout.setRange(0.5, 30.0)
        self.measurement_fetch_timeout.setDecimals(1)
        self.measurement_fetch_timeout.setSingleStep(0.5)
        self.measurement_fetch_timeout.setValue(MEASUREMENT_FETCH_TIMEOUT_DEFAULT)
        self.measurement_fetch_timeout.setSuffix(" s")

        controls_form.addRow("Target group", self.measurement_target_combo)
        controls_form.addRow("HTTP fetch timeout", self.measurement_fetch_timeout)
        controls_layout.addLayout(controls_form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_measurement_start = QPushButton("Run One-Shot Probe")
        self.btn_measurement_start.setMinimumHeight(36)
        self.btn_measurement_refresh = QPushButton("Refresh Results")
        self.btn_measurement_refresh.setMinimumHeight(36)
        btn_row.addWidget(self.btn_measurement_start, 2)
        btn_row.addWidget(self.btn_measurement_refresh, 1)
        controls_layout.addLayout(btn_row)
        runs_layout.addWidget(controls_box)

        status_box = QGroupBox("Run Status")
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(6)
        status_help = QLabel("Current measurement state and completion progress.")
        status_help.setWordWrap(True)
        status_help.setStyleSheet("color:#9fb1d1;font-size:12px;")
        status_layout.addWidget(status_help)
        self.measurement_status_view = QPlainTextEdit()
        self.measurement_status_view.setReadOnly(True)
        configure_compact_text_view(self.measurement_status_view, min_height=120, max_height=170)
        status_layout.addWidget(self.measurement_status_view)
        runs_layout.addWidget(status_box)

        latest_box = QGroupBox("Latest Results")
        latest_layout = QVBoxLayout(latest_box)
        latest_layout.setContentsMargins(8, 8, 8, 8)
        latest_layout.setSpacing(6)
        latest_help = QLabel("Most recent measurement outcome and readiness summary.")
        latest_help.setWordWrap(True)
        latest_help.setStyleSheet("color:#9fb1d1;font-size:12px;")
        latest_layout.addWidget(latest_help)
        self.measurement_latest_view = QPlainTextEdit()
        self.measurement_latest_view.setReadOnly(True)
        configure_compact_text_view(self.measurement_latest_view, min_height=140, max_height=210)
        latest_layout.addWidget(self.measurement_latest_view)
        runs_layout.addWidget(latest_box)

        runs_detail_tabs = QTabWidget()

        recent_page = QWidget()
        recent_layout = QVBoxLayout(recent_page)
        recent_layout.setContentsMargins(4, 4, 4, 4)
        recent_layout.setSpacing(6)
        recent_box = QGroupBox("Recent Runs")
        recent_box_layout = QVBoxLayout(recent_box)
        recent_box_layout.setContentsMargins(8, 8, 8, 8)
        recent_box_layout.setSpacing(6)
        recent_help = QLabel("Use this view to compare recent measurement runs without opening exported files.")
        recent_help.setWordWrap(True)
        recent_help.setStyleSheet("color:#9fb1d1;font-size:12px;")
        recent_box_layout.addWidget(recent_help)
        self.measurement_recent_view = QPlainTextEdit()
        self.measurement_recent_view.setReadOnly(True)
        configure_compact_text_view(self.measurement_recent_view, min_height=150, max_height=220)
        recent_box_layout.addWidget(self.measurement_recent_view)
        recent_layout.addWidget(recent_box)
        runs_detail_tabs.addTab(recent_page, "Recent Runs")

        log_page = QWidget()
        log_page_layout = QVBoxLayout(log_page)
        log_page_layout.setContentsMargins(4, 4, 4, 4)
        log_page_layout.setSpacing(6)
        log_box = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(8, 8, 8, 8)
        log_layout.setSpacing(6)
        log_help = QLabel("Operational messages for the measurement workflow. Keep logs separate from result summaries.")
        log_help.setWordWrap(True)
        log_help.setStyleSheet("color:#9fb1d1;font-size:12px;")
        log_layout.addWidget(log_help)
        self.measurement_log = QPlainTextEdit()
        self.measurement_log.setReadOnly(True)
        configure_compact_text_view(self.measurement_log, min_height=150, max_height=220, wrap=False)
        log_layout.addWidget(self.measurement_log)
        log_page_layout.addWidget(log_box)
        runs_detail_tabs.addTab(log_page, "Activity Log")

        runs_layout.addWidget(runs_detail_tabs)
        tabs.addTab(_wrap_tab_page(runs_page), "Runs")

        summaries_page = QWidget()
        summaries_layout = QVBoxLayout(summaries_page)
        summaries_layout.setContentsMargins(8, 8, 8, 8)
        summaries_layout.setSpacing(8)

        experiment_box = QGroupBox("Measurement Results")
        experiment_layout = QVBoxLayout(experiment_box)
        experiment_layout.setContentsMargins(8, 8, 8, 8)
        experiment_layout.setSpacing(6)
        experiment_btn_row = QHBoxLayout()
        self.btn_experiment_refresh = QPushButton("Refresh Results")
        self.btn_experiment_export_csv = QPushButton("Export Matrix CSV")
        self.btn_experiment_export_json = QPushButton("Export Matrix JSON")
        experiment_btn_row.addWidget(self.btn_experiment_refresh)
        experiment_btn_row.addWidget(self.btn_experiment_export_csv)
        experiment_btn_row.addWidget(self.btn_experiment_export_json)
        experiment_layout.addLayout(experiment_btn_row)
        self.experiment_summary_view = QPlainTextEdit()
        self.experiment_summary_view.setReadOnly(True)
        configure_compact_text_view(self.experiment_summary_view, min_height=180, max_height=260)
        experiment_layout.addWidget(self.experiment_summary_view)
        summaries_layout.addWidget(experiment_box)

        analytics_box = QGroupBox("Measurement Trends")
        analytics_layout = QVBoxLayout(analytics_box)
        analytics_layout.setContentsMargins(8, 8, 8, 8)
        analytics_layout.setSpacing(6)
        analytics_btn_row = QHBoxLayout()
        self.btn_analytics_refresh = QPushButton("Refresh Trends")
        self.btn_analytics_export_csv = QPushButton("Export Trends CSV")
        self.btn_analytics_export_json = QPushButton("Export Trends JSON")
        analytics_btn_row.addWidget(self.btn_analytics_refresh)
        analytics_btn_row.addWidget(self.btn_analytics_export_csv)
        analytics_btn_row.addWidget(self.btn_analytics_export_json)
        analytics_layout.addLayout(analytics_btn_row)
        self.analytics_summary_view = QPlainTextEdit()
        self.analytics_summary_view.setReadOnly(True)
        configure_compact_text_view(self.analytics_summary_view, min_height=180, max_height=260)
        analytics_layout.addWidget(self.analytics_summary_view)
        summaries_layout.addWidget(analytics_box)
        tabs.addTab(_wrap_tab_page(summaries_page), "Summaries")

        path_records_page = QWidget()
        path_records_layout = QVBoxLayout(path_records_page)
        path_records_layout.setContentsMargins(8, 8, 8, 8)
        path_records_layout.setSpacing(8)

        path_records_intro = QGroupBox("Path Records")
        path_records_intro_layout = QHBoxLayout(path_records_intro)
        path_records_intro_layout.setContentsMargins(8, 8, 8, 8)
        path_records_intro_label = QLabel("Automatic ingestion is the standard workflow. When enabled, each completed measurement run is scanned automatically for authoritative hop-chain data from measurement output and run-local source files. Use Scan Now only to force an immediate pass. Manual Path Entry remains available for fallback and validation when authoritative data is unavailable.")
        path_records_intro_label.setWordWrap(True)
        path_records_intro_layout.addWidget(path_records_intro_label, 1)
        path_records_layout.addWidget(path_records_intro)

        path_records_tabs = QTabWidget()
        path_records_layout.addWidget(path_records_tabs, 1)

        records_overview_page = QWidget()
        records_overview_layout = QVBoxLayout(records_overview_page)
        records_overview_layout.setContentsMargins(4, 4, 4, 4)
        records_overview_layout.setSpacing(8)

        hop_history_box = QGroupBox("Observed Path History")
        hop_history_layout = QVBoxLayout(hop_history_box)
        hop_history_btn_row = QHBoxLayout()
        self.btn_phase5_refresh = QPushButton("Refresh Path History")
        self.btn_phase5_export_csv = QPushButton("Export Path History CSV")
        self.btn_phase5_export_json = QPushButton("Export Path History JSON")
        hop_history_btn_row.addWidget(self.btn_phase5_refresh)
        hop_history_btn_row.addWidget(self.btn_phase5_export_csv)
        hop_history_btn_row.addWidget(self.btn_phase5_export_json)
        hop_history_layout.addLayout(hop_history_btn_row)
        self.phase5_summary_view = QPlainTextEdit()
        self.phase5_summary_view.setReadOnly(True)
        configure_compact_text_view(self.phase5_summary_view, min_height=160, max_height=230)
        hop_history_layout.addWidget(self.phase5_summary_view)
        records_overview_layout.addWidget(hop_history_box)

        hop_truth_box = QGroupBox("Tunnel Ground Truth")
        hop_truth_layout = QVBoxLayout(hop_truth_box)
        hop_truth_btn_row = QHBoxLayout()
        self.btn_phase5b_refresh = QPushButton("Refresh Ground Truth")
        self.btn_phase5b_export_csv = QPushButton("Export Ground Truth CSV")
        self.btn_phase5b_export_json = QPushButton("Export Ground Truth JSON")
        hop_truth_btn_row.addWidget(self.btn_phase5b_refresh)
        hop_truth_btn_row.addWidget(self.btn_phase5b_export_csv)
        hop_truth_btn_row.addWidget(self.btn_phase5b_export_json)
        hop_truth_layout.addLayout(hop_truth_btn_row)
        self.phase5b_summary_view = QPlainTextEdit()
        self.phase5b_summary_view.setReadOnly(True)
        configure_compact_text_view(self.phase5b_summary_view, min_height=180, max_height=260)
        hop_truth_layout.addWidget(self.phase5b_summary_view)
        records_overview_layout.addWidget(hop_truth_box)
        path_records_tabs.addTab(records_overview_page, "Overview")

        records_automatic_page = QWidget()
        records_automatic_layout = QVBoxLayout(records_automatic_page)
        records_automatic_layout.setContentsMargins(4, 4, 4, 4)
        records_automatic_layout.setSpacing(8)

        phase5c_box = QGroupBox("Automatic Path Ingestion")
        phase5c_layout = QVBoxLayout(phase5c_box)
        phase5c_layout.addWidget(QLabel("This step ingests authoritative hop-chain data from completed measurement runs and run-local emulator-observed or log-derived source files when they are present. It never invents exact hop order from surface-only traces or cached truth."))
        phase5c_btn_row = QHBoxLayout()
        self.phase5c_auto_mode = QComboBox()
        self.phase5c_auto_mode.addItems(["Enabled", "Disabled"])
        self.btn_phase5c_refresh = QPushButton("Refresh Ingestion Status")
        self.btn_phase5c_run_latest = QPushButton("Scan Now")
        phase5c_btn_row.addWidget(QLabel("Automatic ingestion after measurements"))
        phase5c_btn_row.addWidget(self.phase5c_auto_mode)
        phase5c_btn_row.addWidget(self.btn_phase5c_refresh)
        phase5c_btn_row.addWidget(self.btn_phase5c_run_latest)
        phase5c_layout.addLayout(phase5c_btn_row)
        self.phase5c_summary_view = QPlainTextEdit()
        self.phase5c_summary_view.setReadOnly(True)
        configure_compact_text_view(self.phase5c_summary_view, min_height=130, max_height=190)
        phase5c_layout.addWidget(self.phase5c_summary_view)
        records_automatic_layout.addWidget(phase5c_box)
        self.phase5c_auto_mode.setCurrentText("Enabled")

        hop_truth_producer_box = QGroupBox("Path Record Normalization")
        hop_truth_producer_layout = QVBoxLayout(hop_truth_producer_box)
        hop_truth_producer_btn_row = QHBoxLayout()
        self.btn_phase5b_prod_refresh = QPushButton("Refresh Normalization Status")
        self.btn_phase5b_prod_run = QPushButton("Run Normalization")
        self.btn_phase5b_prod_export_json = QPushButton("Export Normalization Manifest")
        hop_truth_producer_btn_row.addWidget(self.btn_phase5b_prod_refresh)
        hop_truth_producer_btn_row.addWidget(self.btn_phase5b_prod_run)
        hop_truth_producer_btn_row.addWidget(self.btn_phase5b_prod_export_json)
        hop_truth_producer_layout.addWidget(QLabel("Normalization converts newly captured raw path records into the canonical ground-truth dataset used by Path Analysis."))
        hop_truth_producer_layout.addLayout(hop_truth_producer_btn_row)
        self.phase5b_producer_view = QPlainTextEdit()
        self.phase5b_producer_view.setReadOnly(True)
        configure_compact_text_view(self.phase5b_producer_view, min_height=130, max_height=200)
        hop_truth_producer_layout.addWidget(self.phase5b_producer_view)
        records_automatic_layout.addWidget(hop_truth_producer_box)

        capture_maintenance_box = QGroupBox("Ingestion Maintenance")
        capture_maintenance_layout = QHBoxLayout(capture_maintenance_box)
        capture_maintenance_layout.setContentsMargins(8, 8, 8, 8)
        capture_maintenance_help = QLabel("Maintenance actions are rarely needed during normal operation.")
        capture_maintenance_help.setWordWrap(True)
        capture_maintenance_layout.addWidget(capture_maintenance_help, 1)
        self.btn_phase5c_reset_state = QPushButton("Reset Ingestion State")
        capture_maintenance_layout.addWidget(self.btn_phase5c_reset_state)
        records_automatic_layout.addWidget(capture_maintenance_box)
        path_records_tabs.addTab(records_automatic_page, "Ingestion")

        records_fallback_page = QWidget()
        records_fallback_layout = QVBoxLayout(records_fallback_page)
        records_fallback_layout.setContentsMargins(4, 4, 4, 4)
        records_fallback_layout.setSpacing(8)

        fallback_notice_box = QGroupBox("Fallback and Validation")
        fallback_notice_layout = QHBoxLayout(fallback_notice_box)
        fallback_notice_layout.setContentsMargins(8, 8, 8, 8)
        fallback_notice_label = QLabel("Use Manual Path Entry only when automatic ingestion cannot capture authoritative chain data from runtime output or source files, or when you need explicit validation input. This is not the normal measurement workflow.")
        fallback_notice_label.setWordWrap(True)
        fallback_notice_layout.addWidget(fallback_notice_label, 1)
        records_fallback_layout.addWidget(fallback_notice_box)

        hop_capture_box = QGroupBox("Manual Path Entry")
        hop_capture_layout = QVBoxLayout(hop_capture_box)
        hop_capture_layout.addWidget(QLabel("This form records only what you explicitly enter and never infers missing hop order. Use it as a fallback or validation tool, not as the standard workflow."))
        hop_capture_form = QFormLayout()
        self.phase5b_capture_run_id = QLineEdit()
        self.phase5b_capture_scenario_label = QLineEdit()
        self.phase5b_capture_scenario_bucket = QComboBox()
        self.phase5b_capture_scenario_bucket.setEditable(True)
        for _bucket in ["baseline", "moderate_churn", "high_churn", "floodfill_targeted", "adversarial_floodfill", "other"]:
            self.phase5b_capture_scenario_bucket.addItem(_bucket)
        self.phase5b_capture_tunnel_id = QLineEdit()
        self.phase5b_capture_tunnel_direction = QComboBox()
        self.phase5b_capture_tunnel_direction.addItems(["outbound", "inbound", "unknown"])
        self.phase5b_capture_tunnel_kind = QComboBox()
        self.phase5b_capture_tunnel_kind.setEditable(True)
        self.phase5b_capture_tunnel_kind.addItems(["exploratory", "client", "participating", "unknown"])
        self.phase5b_capture_hop_chain = QLineEdit()
        self.phase5b_capture_previous_chain = QLineEdit()
        self.phase5b_capture_phase_stage = QLineEdit()
        self.phase5b_capture_phase_trigger = QLineEdit()
        self.phase5b_capture_source_mode = QComboBox()
        self.phase5b_capture_source_mode.setEditable(True)
        self.phase5b_capture_source_mode.addItems(["emulator-observed", "log-derived-ground-truth", "operator-entered-ground-truth"])
        hop_capture_form.addRow("Run ID", self.phase5b_capture_run_id)
        hop_capture_form.addRow("Scenario label", self.phase5b_capture_scenario_label)
        hop_capture_form.addRow("Scenario bucket", self.phase5b_capture_scenario_bucket)
        hop_capture_form.addRow("Tunnel ID", self.phase5b_capture_tunnel_id)
        hop_capture_form.addRow("Tunnel direction", self.phase5b_capture_tunnel_direction)
        hop_capture_form.addRow("Tunnel kind", self.phase5b_capture_tunnel_kind)
        hop_capture_form.addRow("Hop chain", self.phase5b_capture_hop_chain)
        hop_capture_form.addRow("Previous chain", self.phase5b_capture_previous_chain)
        hop_capture_form.addRow("Phase stage", self.phase5b_capture_phase_stage)
        hop_capture_form.addRow("Trigger reason", self.phase5b_capture_phase_trigger)
        hop_capture_form.addRow("Source mode", self.phase5b_capture_source_mode)
        hop_capture_layout.addLayout(hop_capture_form)
        hop_capture_btn_row = QHBoxLayout()
        self.btn_phase5b_capture_autofill = QPushButton("Fill From Current Context")
        self.btn_phase5b_capture_record = QPushButton("Save Path Record")
        self.btn_phase5b_capture_auto = QPushButton("Save and Refresh Records")
        self.btn_phase5b_capture_clear = QPushButton("Clear Form")
        hop_capture_btn_row.addWidget(self.btn_phase5b_capture_autofill)
        hop_capture_btn_row.addWidget(self.btn_phase5b_capture_record)
        hop_capture_btn_row.addWidget(self.btn_phase5b_capture_auto)
        hop_capture_btn_row.addWidget(self.btn_phase5b_capture_clear)
        hop_capture_layout.addLayout(hop_capture_btn_row)
        self.phase5b_capture_view = QPlainTextEdit()
        self.phase5b_capture_view.setReadOnly(True)
        configure_compact_text_view(self.phase5b_capture_view, min_height=140, max_height=210)
        hop_capture_layout.addWidget(self.phase5b_capture_view)
        records_fallback_layout.addWidget(hop_capture_box)

        fallback_maintenance_box = QGroupBox("Fallback Maintenance")
        fallback_maintenance_layout = QHBoxLayout(fallback_maintenance_box)
        fallback_maintenance_layout.setContentsMargins(8, 8, 8, 8)
        fallback_maintenance_help = QLabel("Destructive maintenance actions are isolated here so they are not part of the normal workflow.")
        fallback_maintenance_help.setWordWrap(True)
        fallback_maintenance_layout.addWidget(fallback_maintenance_help, 1)
        self.btn_phase5b_reset_test_data = QPushButton("Reset Fallback Test Data")
        fallback_maintenance_layout.addWidget(self.btn_phase5b_reset_test_data)
        records_fallback_layout.addWidget(fallback_maintenance_box)
        path_records_tabs.addTab(records_fallback_page, "Fallback")

        self.phase5b_capture_scenario_bucket.setEditText("other")
        self.phase5b_capture_tunnel_kind.setEditText("unknown")
        self.phase5b_capture_source_mode.setEditText("operator-entered-ground-truth")

        tabs.addTab(_wrap_tab_page(path_records_page), "Path Records")

        path_page = QWidget()
        path_layout_page = QVBoxLayout(path_page)
        path_layout_page.setContentsMargins(8, 8, 8, 8)
        path_layout_page.setSpacing(8)

        analysis_intro = QGroupBox("Path Analysis")
        analysis_intro_layout = QHBoxLayout(analysis_intro)
        analysis_intro_layout.setContentsMargins(8, 8, 8, 8)
        analysis_intro_label = QLabel("Use Overview for core authoritative path metrics. Use Trace Comparison when you need deeper comparison details for validation or troubleshooting.")
        analysis_intro_label.setWordWrap(True)
        analysis_intro_layout.addWidget(analysis_intro_label, 1)
        path_layout_page.addWidget(analysis_intro)

        analysis_tabs = QTabWidget()
        path_layout_page.addWidget(analysis_tabs, 1)

        analysis_overview_page = QWidget()
        analysis_overview_layout = QVBoxLayout(analysis_overview_page)
        analysis_overview_layout.setContentsMargins(4, 4, 4, 4)
        analysis_overview_layout.setSpacing(8)

        phase6_box = QGroupBox("Authoritative Path Analysis")
        phase6_layout = QVBoxLayout(phase6_box)
        phase6_btn_row = QHBoxLayout()
        self.btn_phase6_refresh = QPushButton("Refresh Analysis")
        self.btn_phase6_export_csv = QPushButton("Export Path Analysis CSV")
        self.btn_phase6_export_json = QPushButton("Export Path Analysis JSON")
        phase6_btn_row.addWidget(self.btn_phase6_refresh)
        phase6_btn_row.addWidget(self.btn_phase6_export_csv)
        phase6_btn_row.addWidget(self.btn_phase6_export_json)
        phase6_layout.addLayout(phase6_btn_row)
        self.phase6_summary_view = QPlainTextEdit()
        self.phase6_summary_view.setReadOnly(True)
        configure_compact_text_view(self.phase6_summary_view, min_height=180, max_height=250)
        phase6_layout.addWidget(self.phase6_summary_view)
        analysis_overview_layout.addWidget(phase6_box)
        analysis_tabs.addTab(analysis_overview_page, "Overview")

        trace_page = QWidget()
        trace_page_layout = QVBoxLayout(trace_page)
        trace_page_layout.setContentsMargins(4, 4, 4, 4)
        trace_page_layout.setSpacing(8)

        trace_box = QGroupBox("Trace Comparison")
        trace_layout = QVBoxLayout(trace_box)
        trace_btn_row = QHBoxLayout()
        self.btn_tunnel_trace_refresh = QPushButton("Refresh Trace Comparison")
        self.btn_tunnel_trace_export_json = QPushButton("Export Trace Comparison JSON")
        trace_btn_row.addWidget(self.btn_tunnel_trace_refresh)
        trace_btn_row.addWidget(self.btn_tunnel_trace_export_json)
        trace_layout.addLayout(trace_btn_row)
        self.tunnel_trace_view = QPlainTextEdit()
        self.tunnel_trace_view.setReadOnly(True)
        configure_compact_text_view(self.tunnel_trace_view, min_height=180, max_height=250)
        trace_layout.addWidget(self.tunnel_trace_view)
        trace_page_layout.addWidget(trace_box)
        analysis_tabs.addTab(trace_page, "Trace Comparison")

        tabs.addTab(_wrap_tab_page(path_page), "Path Analysis")

        scroll.setWidget(page)

        self.btn_measurement_start.clicked.connect(self.start_measurement_run)
        self.btn_measurement_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_experiment_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_experiment_export_csv.clicked.connect(self.export_experiment_matrix_csv)
        self.btn_experiment_export_json.clicked.connect(self.export_experiment_matrix_json)
        self.btn_analytics_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_analytics_export_csv.clicked.connect(self.export_long_term_analytics_csv)
        self.btn_analytics_export_json.clicked.connect(self.export_long_term_analytics_json)
        self.btn_phase5_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_phase5_export_csv.clicked.connect(self.export_phase5_hop_history_csv)
        self.btn_phase5_export_json.clicked.connect(self.export_phase5_hop_history_json)
        self.btn_phase5b_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_phase5b_export_csv.clicked.connect(self.export_phase5b_hop_truth_csv)
        self.btn_phase5b_export_json.clicked.connect(self.export_phase5b_hop_truth_json)
        self.btn_phase5b_reset_test_data.clicked.connect(self.reset_phase5b_test_data)
        self.btn_phase6_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_phase6_export_csv.clicked.connect(self.export_phase6_exact_hop_analytics_csv)
        self.btn_phase6_export_json.clicked.connect(self.export_phase6_exact_hop_analytics_json)
        self.btn_phase5b_prod_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_phase5b_prod_run.clicked.connect(self.run_phase5b_exact_hop_producer)
        self.btn_phase5b_prod_export_json.clicked.connect(self.export_phase5b_producer_manifest_json)
        self.btn_phase5b_capture_autofill.clicked.connect(self.autofill_phase5b_capture_form)
        self.btn_phase5b_capture_record.clicked.connect(self.record_phase5b_exact_hop_event_from_ui)
        self.btn_phase5b_capture_auto.clicked.connect(self.auto_record_phase5b_exact_hop_event_from_ui)
        self.btn_phase5b_capture_clear.clicked.connect(self.clear_phase5b_capture_form)
        self.btn_phase5c_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_phase5c_run_latest.clicked.connect(self.run_phase5c_auto_extract_latest_measurement)
        self.btn_phase5c_reset_state.clicked.connect(self.reset_phase5c_state)
        self.btn_tunnel_trace_refresh.clicked.connect(self.update_measurement_panel)
        self.btn_tunnel_trace_export_json.clicked.connect(self.export_tunnel_trace_json)
        self.update_measurement_panel()
        return scroll

    def _measurement_list_recent_runs(self, limit=MEASUREMENT_RECENT_RUN_LIMIT):
        runs = []
        for run_dir in list_recent_run_dirs(MEASUREMENT_ROOT_DIR, require_files=["run.json", "state.json", "summary.json"], limit=limit):
            run = read_json_file(os.path.join(run_dir, "run.json"), {})
            state = read_json_file(os.path.join(run_dir, "state.json"), {})
            summary = read_json_file(os.path.join(run_dir, "summary.json"), {})
            runs.append({
                "run_dir": run_dir,
                "run": run,
                "state": state,
                "summary": summary,
                "mtime": os.path.getmtime(run_dir) if os.path.exists(run_dir) else 0.0,
            })
        runs.sort(key=lambda item: item.get("mtime", 0.0), reverse=True)
        return runs

    def _experiment_latest_standalone_measurement(self):
        for rec in self._measurement_list_recent_runs(limit=20):
            summary_wrapper = rec.get("summary") or {}
            state = rec.get("state") or {}
            scenario_corr = summary_wrapper.get("scenario_correlation") or {}
            if state.get("status") != "completed":
                continue
            if scenario_corr and scenario_corr.get("run_id"):
                continue
            summary_payload = summary_wrapper.get("summary") or {}
            return {
                "row_kind": "baseline_measurement",
                "status": state.get("status", "unknown"),
                "experiment_label": "baseline_one_shot",
                "scenario_preset_name": "Baseline one-shot",
                "scenario_type": "baseline",
                "scenario_target_group": "none",
                "scenario_run_id": None,
                "campaign_run_id": None,
                "campaign_run_dir": rec.get("run_dir"),
                "baseline_run_id": state.get("run_id"),
                "final_run_id": state.get("run_id"),
                "interim_measurements": 0,
                "cycle_trigger_measurements": 0,
                "periodic_measurements": 0,
                "baseline_root_success": summary_payload.get("root_success"),
                "baseline_netdb_success": summary_payload.get("netdb_success"),
                "baseline_client_proxy_success": summary_payload.get("client_proxy_success"),
                "baseline_mean_root_latency_ms": summary_payload.get("mean_root_latency_ms"),
                "baseline_mean_netdb_latency_ms": summary_payload.get("mean_netdb_latency_ms"),
                "baseline_mean_proxy_latency_ms": summary_payload.get("mean_client_proxy_latency_ms"),
                "baseline_mean_proxy_first_byte_ms": summary_payload.get("mean_client_proxy_first_byte_ms"),
                "baseline_full_ready_routers": summary_payload.get("full_ready_routers"),
                "final_root_success": summary_payload.get("root_success"),
                "final_netdb_success": summary_payload.get("netdb_success"),
                "final_client_proxy_success": summary_payload.get("client_proxy_success"),
                "final_mean_root_latency_ms": summary_payload.get("mean_root_latency_ms"),
                "final_mean_netdb_latency_ms": summary_payload.get("mean_netdb_latency_ms"),
                "final_mean_proxy_latency_ms": summary_payload.get("mean_client_proxy_latency_ms"),
                "final_mean_proxy_first_byte_ms": summary_payload.get("mean_client_proxy_first_byte_ms"),
                "final_full_ready_routers": summary_payload.get("full_ready_routers"),
                "delta_root_success": 0,
                "delta_netdb_success": 0,
                "delta_client_proxy_success": 0,
                "worst_interim_run_id": None,
                "worst_interim_client_proxy_success": None,
                "worst_interim_mean_proxy_latency_ms": None,
                "mtime": rec.get("mtime", 0.0),
            }
        return None

    def _measurement_run_index(self, limit=300):
        index = {}
        for rec in self._measurement_list_recent_runs(limit=limit):
            state = rec.get("state") or {}
            run = rec.get("run") or {}
            summary_wrapper = rec.get("summary") or {}
            summary_payload = summary_wrapper.get("summary") or {}
            run_id = str(state.get("run_id") or run.get("run_id") or "").strip()
            if not run_id:
                continue
            index[run_id] = {
                "run_id": run_id,
                "run_dir": rec.get("run_dir"),
                "state": state,
                "run": run,
                "summary_wrapper": summary_wrapper,
                "summary": summary_payload,
                "mtime": rec.get("mtime", 0.0),
            }
        return index

    def _campaign_measurement_runs_index(self, summary_payload):
        index = {}
        for item in list((summary_payload or {}).get("measurement_runs") or []):
            run_id = str(item.get("run_id") or "").strip()
            if not run_id:
                continue
            index[run_id] = dict(item)
        return index

    def _campaign_find_measurement_summary(self, measurement_index, campaign_index, run_id=None, stage_prefix=None):
        run_id = str(run_id or "").strip()
        if run_id:
            local = campaign_index.get(run_id)
            if local:
                return local.get("summary") or {}, local
            external = measurement_index.get(run_id)
            if external:
                return external.get("summary") or {}, external
        if stage_prefix:
            prefix = str(stage_prefix).strip().lower()
            candidates = []
            for item in list(campaign_index.values()):
                stage = str(item.get("stage") or item.get("trigger_reason") or "").strip().lower()
                if stage.startswith(prefix):
                    candidates.append(item)
            if candidates:
                candidates.sort(key=lambda item: str(item.get("finished_at_local") or item.get("run_id") or ""))
                chosen = candidates[-1]
                return chosen.get("summary") or {}, chosen
        return {}, None

    def _campaign_worst_interim_from_measurements(self, campaign_index):
        candidates = []
        for item in list(campaign_index.values()):
            stage = str(item.get("stage") or "").strip().lower()
            if stage.startswith("interim") or stage.startswith("cycle") or stage.startswith("periodic"):
                candidates.append(item)
        if not candidates:
            return None
        def score(item):
            summary = item.get("summary") or {}
            proxy_success = safe_int(summary.get("client_proxy_success"), 0)
            netdb_success = safe_int(summary.get("netdb_success"), 0)
            latency = self._analytics_safe_float(summary.get("mean_client_proxy_latency_ms"))
            if latency is None:
                latency = self._analytics_safe_float(summary.get("mean_root_latency_ms"))
            if latency is None:
                latency = 0.0
            return (proxy_success, netdb_success, -latency)
        candidates.sort(key=score)
        worst = candidates[0]
        return {
            "run_id": worst.get("run_id"),
            "summary": dict(worst.get("summary") or {}),
        }

    def _campaign_apply_measurement_summary_fallbacks(self, row, base_summary=None, final_summary=None, worst_interim=None):
        row = dict(row or {})
        base_summary = base_summary or {}
        final_summary = final_summary or {}
        worst_interim = worst_interim or {}

        def fill(prefix, summary):
            if not summary:
                return
            mapping = {
                f"{prefix}_root_success": summary.get("root_success"),
                f"{prefix}_netdb_success": summary.get("netdb_success"),
                f"{prefix}_client_proxy_success": summary.get("client_proxy_success"),
                f"{prefix}_mean_root_latency_ms": summary.get("mean_root_latency_ms"),
                f"{prefix}_mean_netdb_latency_ms": summary.get("mean_netdb_latency_ms"),
                f"{prefix}_mean_proxy_latency_ms": summary.get("mean_client_proxy_latency_ms"),
                f"{prefix}_mean_proxy_first_byte_ms": summary.get("mean_client_proxy_first_byte_ms"),
                f"{prefix}_full_ready_routers": summary.get("full_ready_routers"),
            }
            for key, value in mapping.items():
                if row.get(key) is None and value is not None:
                    row[key] = value

        fill("baseline", base_summary)
        fill("final", final_summary)

        if row.get("delta_root_success") is None and row.get("baseline_root_success") is not None and row.get("final_root_success") is not None:
            row["delta_root_success"] = safe_int(row.get("final_root_success"), 0) - safe_int(row.get("baseline_root_success"), 0)
        if row.get("delta_netdb_success") is None and row.get("baseline_netdb_success") is not None and row.get("final_netdb_success") is not None:
            row["delta_netdb_success"] = safe_int(row.get("final_netdb_success"), 0) - safe_int(row.get("baseline_netdb_success"), 0)
        if row.get("delta_client_proxy_success") is None and row.get("baseline_client_proxy_success") is not None and row.get("final_client_proxy_success") is not None:
            row["delta_client_proxy_success"] = safe_int(row.get("final_client_proxy_success"), 0) - safe_int(row.get("baseline_client_proxy_success"), 0)

        interim_summary = (worst_interim or {}).get("summary") or {}
        if row.get("worst_interim_run_id") is None and (worst_interim or {}).get("run_id"):
            row["worst_interim_run_id"] = worst_interim.get("run_id")
        if row.get("worst_interim_client_proxy_success") is None and interim_summary.get("client_proxy_success") is not None:
            row["worst_interim_client_proxy_success"] = interim_summary.get("client_proxy_success")
        if row.get("worst_interim_mean_proxy_latency_ms") is None:
            row["worst_interim_mean_proxy_latency_ms"] = interim_summary.get("mean_client_proxy_latency_ms")
        return row

    def _experiment_list_campaign_rows(self, limit=12):
        rows = []
        measurement_index = self._measurement_run_index(limit=max(300, limit * 25))
        baseline_row = self._experiment_latest_standalone_measurement()
        if baseline_row:
            rows.append(baseline_row)

        def pick(*values):
            for value in values:
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                return value
            return None

        for run_dir in list_recent_run_dirs(CAMPAIGN_ROOT_DIR, require_files=["run.json", "state.json", "summary.json"], limit=limit):
            run = read_json_file(os.path.join(run_dir, "run.json"), default={})
            state = read_json_file(os.path.join(run_dir, "state.json"), default={})
            summary_wrapper = read_json_file(os.path.join(run_dir, "summary.json"), default={})
            summary_payload = summary_wrapper.get("summary") or {}
            worst_interim = summary_payload.get("worst_interim") or {}
            config = run.get("config") or {}
            scenario_cfg = config.get("scenario_config") or {}
            row = {
                "row_kind": "campaign",
                "status": state.get("status") or summary_wrapper.get("status") or "unknown",
                "experiment_label": state.get("experiment_label") or config.get("experiment_label") or summary_payload.get("experiment_label") or "n/a",
                "scenario_preset_name": state.get("scenario_preset_name") or config.get("scenario_preset_name") or summary_payload.get("scenario_preset_name") or "Custom",
                "scenario_type": state.get("scenario_type") or scenario_cfg.get("scenario_type") or summary_payload.get("scenario_type") or "unknown",
                "scenario_target_group": state.get("scenario_target_group") or scenario_cfg.get("target_group") or summary_payload.get("scenario_target_group") or "unknown",
                "scenario_run_id": summary_payload.get("scenario_run_id") or state.get("scenario_run_id") or state.get("scenario_run") or None,
                "campaign_run_id": state.get("run_id") or summary_wrapper.get("run_id") or run.get("run_id"),
                "campaign_run_dir": run_dir,
                "baseline_run_id": pick(summary_payload.get("baseline_run_id"), state.get("baseline_run_id")),
                "final_run_id": pick(summary_payload.get("final_run_id"), state.get("final_run_id")),
                "interim_measurements": pick(summary_payload.get("interim_measurements"), state.get("interim_measurements"), 0),
                "cycle_trigger_measurements": pick(summary_payload.get("cycle_trigger_measurements"), state.get("cycle_trigger_measurements"), 0),
                "periodic_measurements": pick(summary_payload.get("periodic_measurements"), state.get("periodic_measurements"), 0),
                "baseline_root_success": pick(summary_payload.get("baseline_root_success"), summary_payload.get("root_success")),
                "baseline_netdb_success": pick(summary_payload.get("baseline_netdb_success"), summary_payload.get("netdb_success")),
                "baseline_client_proxy_success": pick(summary_payload.get("baseline_client_proxy_success"), summary_payload.get("client_proxy_success")),
                "baseline_mean_root_latency_ms": pick(summary_payload.get("baseline_mean_root_latency_ms"), summary_payload.get("mean_root_latency_ms")),
                "baseline_mean_proxy_latency_ms": pick(summary_payload.get("baseline_mean_proxy_latency_ms"), summary_payload.get("mean_client_proxy_latency_ms")),
                "baseline_mean_netdb_latency_ms": pick(summary_payload.get("baseline_mean_netdb_latency_ms"), summary_payload.get("mean_netdb_latency_ms")),
                "baseline_mean_proxy_first_byte_ms": pick(summary_payload.get("baseline_mean_proxy_first_byte_ms"), summary_payload.get("mean_client_proxy_first_byte_ms")),
                "baseline_full_ready_routers": pick(summary_payload.get("baseline_full_ready_routers"), summary_payload.get("full_ready_routers")),
                "final_root_success": pick(summary_payload.get("final_root_success"), summary_payload.get("root_success")),
                "final_netdb_success": pick(summary_payload.get("final_netdb_success"), summary_payload.get("netdb_success")),
                "final_client_proxy_success": pick(summary_payload.get("final_client_proxy_success"), summary_payload.get("client_proxy_success")),
                "final_mean_root_latency_ms": pick(summary_payload.get("final_mean_root_latency_ms"), summary_payload.get("mean_root_latency_ms")),
                "final_mean_proxy_latency_ms": pick(summary_payload.get("final_mean_proxy_latency_ms"), summary_payload.get("mean_client_proxy_latency_ms")),
                "final_mean_netdb_latency_ms": pick(summary_payload.get("final_mean_netdb_latency_ms"), summary_payload.get("mean_netdb_latency_ms")),
                "final_mean_proxy_first_byte_ms": pick(summary_payload.get("final_mean_proxy_first_byte_ms"), summary_payload.get("mean_client_proxy_first_byte_ms")),
                "final_full_ready_routers": pick(summary_payload.get("final_full_ready_routers"), summary_payload.get("full_ready_routers")),
                "delta_root_success": summary_payload.get("delta_root_success"),
                "delta_netdb_success": summary_payload.get("delta_netdb_success"),
                "delta_client_proxy_success": summary_payload.get("delta_client_proxy_success"),
                "worst_interim_run_id": (worst_interim or {}).get("run_id"),
                "worst_interim_client_proxy_success": ((worst_interim or {}).get("summary") or {}).get("client_proxy_success"),
                "worst_interim_mean_proxy_latency_ms": ((worst_interim or {}).get("summary") or {}).get("mean_client_proxy_latency_ms"),
                "mtime": os.path.getmtime(run_dir) if os.path.exists(run_dir) else 0.0,
            }
            campaign_index = self._campaign_measurement_runs_index(summary_payload)
            baseline_summary, _ = self._campaign_find_measurement_summary(measurement_index, campaign_index, row.get("baseline_run_id"), "baseline")
            final_summary, _ = self._campaign_find_measurement_summary(measurement_index, campaign_index, row.get("final_run_id"), "final")
            worst_interim = summary_payload.get("worst_interim") or self._campaign_worst_interim_from_measurements(campaign_index)
            row = self._campaign_apply_measurement_summary_fallbacks(row, baseline_summary, final_summary, worst_interim)
            rows.append(row)
        rows.sort(key=lambda item: item.get("mtime", 0.0), reverse=True)
        return rows

    def _build_experiment_summary_text(self, rows=None):
        rows = rows if rows is not None else self._experiment_list_campaign_rows(limit=12)
        lines = ["Measurement results", "=" * 72]
        if not rows:
            lines.append("No completed baseline/campaign rows found yet.")
            return "\n".join(lines)
        for idx, row in enumerate(rows, 1):
            final_root = row.get("final_root_success")
            final_netdb = row.get("final_netdb_success")
            final_client = row.get("final_client_proxy_success")
            lines.extend([
                f"[{idx}] {row.get('experiment_label', 'n/a')}",
                f"  kind/status         : {row.get('row_kind', 'unknown')} / {row.get('status', 'unknown')}",
                f"  preset/scenario     : {row.get('scenario_preset_name', 'Custom')} | {row.get('scenario_type', 'unknown')} | target={row.get('scenario_target_group', 'unknown')}",
                f"  runs                : campaign={row.get('campaign_run_id', 'n/a')} | scenario={row.get('scenario_run_id', 'n/a')} | baseline={row.get('baseline_run_id', 'n/a')} | final={row.get('final_run_id', 'n/a')}",
                f"  final readiness     : root={final_root if final_root is not None else 'n/a'} | netdb={final_netdb if final_netdb is not None else 'n/a'} | client={final_client if final_client is not None else 'n/a'} | full-ready={row.get('final_full_ready_routers', 'n/a')}",
                f"  latency (base->fin) : root={row.get('baseline_mean_root_latency_ms', 'n/a')} -> {row.get('final_mean_root_latency_ms', 'n/a')} ms | netdb={row.get('baseline_mean_netdb_latency_ms', 'n/a')} -> {row.get('final_mean_netdb_latency_ms', 'n/a')} ms | proxy={row.get('baseline_mean_proxy_latency_ms', 'n/a')} -> {row.get('final_mean_proxy_latency_ms', 'n/a')} ms",
                f"  deltas              : root={row.get('delta_root_success', 'n/a')} | netdb={row.get('delta_netdb_success', 'n/a')} | client={row.get('delta_client_proxy_success', 'n/a')}",
                f"  probes              : interim={row.get('interim_measurements', 0)} | cycle-trigger={row.get('cycle_trigger_measurements', 0)} | periodic={row.get('periodic_measurements', 0)}",
                f"  worst interim       : run={row.get('worst_interim_run_id', 'n/a')} | client={row.get('worst_interim_client_proxy_success', 'n/a')} | proxy={row.get('worst_interim_mean_proxy_latency_ms', 'n/a')} ms",
                f"  run dir             : {row.get('campaign_run_dir', 'n/a')}",
                "",
            ])
        return "\n".join(lines).rstrip()

    def _experiment_export_rows(self, rows=None):
        rows = rows if rows is not None else self._experiment_list_campaign_rows(limit=50)
        export_rows = []
        for row in rows:
            export_rows.append({
                "row_kind": row.get("row_kind"),
                "status": row.get("status"),
                "experiment_label": row.get("experiment_label"),
                "scenario_preset_name": row.get("scenario_preset_name"),
                "scenario_type": row.get("scenario_type"),
                "scenario_target_group": row.get("scenario_target_group"),
                "campaign_run_id": row.get("campaign_run_id"),
                "scenario_run_id": row.get("scenario_run_id"),
                "baseline_run_id": row.get("baseline_run_id"),
                "final_run_id": row.get("final_run_id"),
                "interim_measurements": row.get("interim_measurements"),
                "cycle_trigger_measurements": row.get("cycle_trigger_measurements"),
                "periodic_measurements": row.get("periodic_measurements"),
                "baseline_root_success": row.get("baseline_root_success"),
                "baseline_netdb_success": row.get("baseline_netdb_success"),
                "baseline_client_proxy_success": row.get("baseline_client_proxy_success"),
                "baseline_mean_root_latency_ms": row.get("baseline_mean_root_latency_ms"),
                "baseline_mean_netdb_latency_ms": row.get("baseline_mean_netdb_latency_ms"),
                "baseline_mean_proxy_latency_ms": row.get("baseline_mean_proxy_latency_ms"),
                "baseline_mean_proxy_first_byte_ms": row.get("baseline_mean_proxy_first_byte_ms"),
                "baseline_full_ready_routers": row.get("baseline_full_ready_routers"),
                "final_root_success": row.get("final_root_success"),
                "final_netdb_success": row.get("final_netdb_success"),
                "final_client_proxy_success": row.get("final_client_proxy_success"),
                "final_mean_root_latency_ms": row.get("final_mean_root_latency_ms"),
                "final_mean_netdb_latency_ms": row.get("final_mean_netdb_latency_ms"),
                "final_mean_proxy_latency_ms": row.get("final_mean_proxy_latency_ms"),
                "final_mean_proxy_first_byte_ms": row.get("final_mean_proxy_first_byte_ms"),
                "final_full_ready_routers": row.get("final_full_ready_routers"),
                "delta_root_success": row.get("delta_root_success"),
                "delta_netdb_success": row.get("delta_netdb_success"),
                "delta_client_proxy_success": row.get("delta_client_proxy_success"),
                "worst_interim_run_id": row.get("worst_interim_run_id"),
                "worst_interim_client_proxy_success": row.get("worst_interim_client_proxy_success"),
                "worst_interim_mean_proxy_latency_ms": row.get("worst_interim_mean_proxy_latency_ms"),
                "campaign_run_dir": row.get("campaign_run_dir"),
            })
        return export_rows

    def _analytics_safe_float(self, value):
        try:
            if value is None or value == "n/a" or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def _analytics_numeric_stats(self, values):
        vals = [self._analytics_safe_float(v) for v in values]
        vals = [v for v in vals if v is not None]
        if not vals:
            return {"count": 0, "avg": None, "min": None, "max": None, "median": None, "p95": None}
        vals.sort()
        n = len(vals)
        def pct(p):
            if n == 1:
                return vals[0]
            idx = max(0, min(n - 1, int(math.ceil((p / 100.0) * n)) - 1))
            return vals[idx]
        if n % 2:
            med = vals[n // 2]
        else:
            med = (vals[(n // 2) - 1] + vals[n // 2]) / 2.0
        return {
            "count": n,
            "avg": round(sum(vals) / n, 3),
            "min": round(vals[0], 3),
            "max": round(vals[-1], 3),
            "median": round(med, 3),
            "p95": round(pct(95), 3),
        }

    def _analytics_bucket_name(self, row):
        label = str(row.get("experiment_label") or "").strip().lower()
        preset = str(row.get("scenario_preset_name") or "").strip().lower()
        scenario_type = str(row.get("scenario_type") or "").strip().lower()
        target = str(row.get("scenario_target_group") or "").strip().lower()
        row_kind = str(row.get("row_kind") or "").strip().lower()
        search_blob = " ".join([label, preset, scenario_type, target]).strip()

        if row_kind == "baseline_measurement" or "baseline" in search_blob or scenario_type == "baseline":
            return "baseline"
        if "adversarial" in search_blob or ("floodfill" in search_blob and "failure" in search_blob):
            return "adversarial_floodfill"
        if "high" in search_blob and "churn" in search_blob:
            return "high_churn"
        if "moderate" in search_blob and "churn" in search_blob:
            return "moderate_churn"
        if "floodfill" in search_blob or target in {"floodfill_only", "floodfill only"}:
            return "floodfill_targeted"
        return "other"

    def _analytics_trace_semantic_signature(self, row):
        row = row or {}
        hosts = []
        for host in (row.get("sample_b32_hosts") or []):
            host_l = str(host or "").strip().lower()
            if host_l and host_l not in hosts:
                hosts.append(host_l)
        hosts.sort()
        keywords = row.get("keyword_counts") or {}
        stable_counts = {
            key: safe_int(keywords.get(key), 0)
            for key in ("inbound", "outbound", "lease", "exploratory", "client", "participating", "peer")
        }
        payload = {
            "hosts": hosts,
            "keywords": {key: (1 if safe_int(value, 0) > 0 else 0) for key, value in stable_counts.items()},
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        if not hosts and not any(stable_counts.values()):
            raw_sig = str(row.get("signature") or "").strip()
            return raw_sig or ""
        return hashlib.sha1(blob.encode("utf-8", errors="ignore")).hexdigest()[:12]

    def _analytics_trace_hosts(self, row):
        hosts = []
        for host in list((row or {}).get("sample_b32_hosts") or []):
            host_l = str(host or "").strip().lower()
            if host_l and host_l not in hosts:
                hosts.append(host_l)
        hosts.sort()
        return hosts

    def _analytics_trace_keyword_profile(self, row):
        keywords = (row or {}).get("keyword_counts") or {}
        profile = {}
        for key in ("inbound", "outbound", "lease", "exploratory", "client", "participating", "peer"):
            profile[key] = 1 if safe_int(keywords.get(key), 0) > 0 else 0
        return profile

    def _analytics_trace_row_quality(self, row):
        row = row or {}
        hosts = self._analytics_trace_hosts(row)
        profile = self._analytics_trace_keyword_profile(row)
        richness = len(hosts) * 4 + sum(profile.values()) * 2
        if row.get("client_proxy_success") is True:
            richness += 2
        if row.get("client_proxy_latency_ms") is not None:
            richness += 1
        if row.get("client_proxy_first_byte_ms") is not None:
            richness += 1
        return richness

    def _analytics_trace_change_detected(self, previous_row, current_row):
        previous_row = previous_row or {}
        current_row = current_row or {}
        prev_hosts = set(self._analytics_trace_hosts(previous_row))
        curr_hosts = set(self._analytics_trace_hosts(current_row))
        if prev_hosts and curr_hosts:
            inter = len(prev_hosts & curr_hosts)
            union = len(prev_hosts | curr_hosts)
            similarity = (inter / union) if union else 1.0
            if similarity >= 0.6:
                return False
            return True
        prev_profile = self._analytics_trace_keyword_profile(previous_row)
        curr_profile = self._analytics_trace_keyword_profile(current_row)
        if any(prev_profile.values()) and any(curr_profile.values()):
            if prev_profile == curr_profile:
                return False
            changed_keys = sum(1 for key in prev_profile if prev_profile.get(key) != curr_profile.get(key))
            return changed_keys >= 2
        prev_sig = str(previous_row.get("semantic_signature") or previous_row.get("signature") or "")
        curr_sig = str(current_row.get("semantic_signature") or current_row.get("signature") or "")
        return bool(prev_sig and curr_sig and prev_sig != curr_sig)

    def _analytics_ts_epoch(self, value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        dt = parse_ts_local(str(value or "")) or parse_display_timestamp(str(value or ""))
        if not dt:
            return 0.0
        try:
            return float(dt.timestamp())
        except Exception:
            return 0.0

    def _analytics_trace_row_severity_weight(self, row):
        row = row or {}
        search_blob = " ".join([
            str(row.get("scenario_label") or ""),
            str(row.get("phase_label") or ""),
            str(row.get("phase_stage") or ""),
            str(row.get("phase_trigger_reason") or ""),
        ]).strip().lower()
        if not search_blob:
            return 1.0
        if "adversarial" in search_blob or "failure" in search_blob:
            return 2.0
        if "high" in search_blob and "churn" in search_blob:
            return 1.55
        if "floodfill" in search_blob:
            return 1.7
        if "moderate" in search_blob and "churn" in search_blob:
            return 1.25
        if any(term in search_blob for term in ("cycle", "interim", "periodic", "scenario-correlated", "recent_completed_scenario", "final")):
            return 1.15
        return 1.0

    def _analytics_phase2_confidence(self, samples):
        samples = safe_int(samples, 0)
        if samples >= 12:
            return "high"
        if samples >= 6:
            return "medium"
        return "low"

    def _analytics_phase2_router_metrics(self, rows):
        rows = list(rows or [])
        if not rows:
            return {
                "score_stats": self._analytics_numeric_stats([]),
                "score_latest": None,
                "change_rate": 0.0,
                "weighted_change_rate": 0.0,
                "proxy_success_rate": None,
                "instability_recurrence": 0,
                "avg_severity_weight": None,
                "confidence": "low",
            }

        ts_values = [self._analytics_ts_epoch(r.get("ts_local") or r.get("ts_utc")) for r in rows]
        latest_epoch = max(ts_values) if ts_values else 0.0
        decay_window_seconds = 4.0 * 3600.0

        changes = 0
        generations = 1
        previous_row = None
        proxy_success_count = 0
        trajectory_scores = []
        severity_values = []
        instability_recurrence = 0
        previous_unstable = False
        weighted_total = 0.0
        weighted_change_penalty = 0.0
        weighted_proxy_penalty = 0.0
        weighted_recent_stable = 0.0

        for idx, row in enumerate(rows):
            changed = False
            if idx > 0 and previous_row is not None:
                changed = self._analytics_trace_change_detected(previous_row, row)
                if changed:
                    changes += 1
                    generations += 1
            row["analytics_changed"] = changed
            row["analytics_generation"] = generations

            proxy_success = row.get("client_proxy_success")
            if proxy_success is True:
                proxy_success_count += 1

            severity_weight = self._analytics_trace_row_severity_weight(row)
            severity_values.append(severity_weight)

            row_epoch = self._analytics_ts_epoch(row.get("ts_local") or row.get("ts_utc"))
            age_seconds = max(0.0, latest_epoch - row_epoch)
            recent_weight = math.exp(-age_seconds / decay_window_seconds) if latest_epoch and row_epoch else 1.0
            effective_weight = max(0.05, recent_weight) * severity_weight
            weighted_total += effective_weight

            unstable = bool(changed) or (proxy_success is False)
            if changed:
                weighted_change_penalty += effective_weight
            if proxy_success is False:
                weighted_proxy_penalty += effective_weight
            if not unstable:
                weighted_recent_stable += effective_weight
            if unstable and not previous_unstable:
                instability_recurrence += 1
            previous_unstable = unstable

            change_component = 1.0 - min(1.0, (weighted_change_penalty / weighted_total)) if weighted_total else 1.0
            proxy_component = 1.0 - min(1.0, (weighted_proxy_penalty / weighted_total)) if weighted_total else 1.0
            recurrence_component = 1.0 - min(1.0, instability_recurrence / max(1, idx + 1))
            recent_component = min(1.0, max(0.0, weighted_recent_stable / weighted_total)) if weighted_total else 1.0

            score = (
                (change_component * 0.35) +
                (proxy_component * 0.30) +
                (recurrence_component * 0.20) +
                (recent_component * 0.15)
            ) * 100.0
            trajectory_scores.append(round(max(0.0, min(100.0, score)), 3))
            previous_row = row

        samples = len(rows)
        return {
            "score_stats": self._analytics_numeric_stats(trajectory_scores),
            "score_latest": trajectory_scores[-1] if trajectory_scores else None,
            "change_rate": round(changes / max(1, samples - 1), 4) if samples > 1 else 0.0,
            "weighted_change_rate": round(min(1.0, weighted_change_penalty / weighted_total), 4) if weighted_total else 0.0,
            "proxy_success_rate": round(proxy_success_count / samples, 4) if samples else None,
            "instability_recurrence": instability_recurrence,
            "avg_severity_weight": round(sum(severity_values) / len(severity_values), 3) if severity_values else None,
            "confidence": self._analytics_phase2_confidence(samples),
        }


    def _phase3_trace_recency_bucket(self, ts_value):
        epoch = self._analytics_ts_epoch(ts_value)
        now_epoch = time.time()
        if not epoch:
            return "stale"
        age = max(0.0, now_epoch - epoch)
        if age <= 15 * 60:
            return "hot"
        if age <= 60 * 60:
            return "warm"
        if age <= 6 * 3600:
            return "cool"
        return "stale"

    def _phase3_trend_band(self, score_latest, weighted_change_rate, proxy_success_rate):
        score_latest = self._analytics_safe_float(score_latest)
        weighted_change_rate = self._analytics_safe_float(weighted_change_rate)
        proxy_success_rate = self._analytics_safe_float(proxy_success_rate)
        if ((score_latest is not None and score_latest < 68.0)
            or (weighted_change_rate is not None and weighted_change_rate >= 0.22)
            or (proxy_success_rate is not None and proxy_success_rate < 0.65)):
            return "unstable"
        if ((score_latest is not None and score_latest < 86.0)
            or (weighted_change_rate is not None and weighted_change_rate >= 0.08)
            or (proxy_success_rate is not None and proxy_success_rate < 0.9)):
            return "watch"
        return "stable"

    def _phase3_inferred_trace_links(self, trace_rows, max_links=24):
        rows = sorted(
            list(trace_rows or []),
            key=lambda r: (
                self._analytics_ts_epoch(r.get("ts_local") or r.get("ts_utc")),
                str(r.get("run_id") or ""),
                str(r.get("router_id") or ""),
            ),
        )
        by_router = {}
        for row in rows:
            router_id = str(row.get("router_id") or "").strip()
            if not router_id:
                continue
            by_router.setdefault(router_id, []).append(row)

        changed_recent = []
        for router_id, router_rows in by_router.items():
            if not router_rows:
                continue
            latest = router_rows[-1]
            prev = router_rows[-2] if len(router_rows) > 1 else None
            changed = bool(prev and self._analytics_trace_change_detected(prev, latest))
            recent_epoch = self._analytics_ts_epoch(latest.get("ts_local") or latest.get("ts_utc"))
            if changed and recent_epoch and (time.time() - recent_epoch) <= 6 * 3600:
                changed_recent.append((router_id, latest))

        links = []
        seen = set()
        changed_recent = sorted(changed_recent, key=lambda item: safe_int(item[0], 999999))
        for idx, (router_id, row) in enumerate(changed_recent):
            for other_id, other_row in changed_recent[idx + 1:]:
                if len(links) >= max_links:
                    break
                phase_a = str(row.get("phase_stage") or row.get("phase_label") or "")
                phase_b = str(other_row.get("phase_stage") or other_row.get("phase_label") or "")
                trigger_a = str(row.get("phase_trigger_reason") or "")
                trigger_b = str(other_row.get("phase_trigger_reason") or "")
                epoch_a = self._analytics_ts_epoch(row.get("ts_local") or row.get("ts_utc"))
                epoch_b = self._analytics_ts_epoch(other_row.get("ts_local") or other_row.get("ts_utc"))
                same_phase = phase_a and phase_a == phase_b
                same_trigger = trigger_a and trigger_a == trigger_b
                close_in_time = abs(epoch_a - epoch_b) <= 180.0 if epoch_a and epoch_b else False
                same_run = str(row.get("run_id") or "") and str(row.get("run_id") or "") == str(other_row.get("run_id") or "")
                if not (same_run or (same_phase and (same_trigger or close_in_time))):
                    continue
                key = tuple(sorted((router_id, other_id)))
                if key in seen:
                    continue
                confidence = "high" if same_run else ("medium" if same_phase and close_in_time else "surface-only")
                basis_parts = ["recent trace co-change"]
                if same_run:
                    basis_parts.append(f"same run {row.get('run_id')}")
                if same_phase:
                    basis_parts.append(f"stage {phase_a}")
                if same_trigger:
                    basis_parts.append(f"trigger {trigger_a}")
                basis_parts.append(f"confidence {confidence}")
                links.append({
                    "from": router_id,
                    "to": other_id,
                    "kind": "inferred",
                    "basis": " | ".join(str(p) for p in basis_parts if p),
                    "state": "inferred",
                    "confidence": confidence,
                })
                seen.add(key)
            if len(links) >= max_links:
                break
        return links

    def _phase4_confidence_rank(self, label):
        label = str(label or "surface-only").strip().lower()
        if label == "high":
            return 3
        if label == "medium":
            return 2
        return 1

    def _phase4_relation_confidence(self, shared_hosts, same_run_hits, close_change_hits, shared_profile):
        if shared_hosts > 0 and close_change_hits > 0:
            return "high"
        if (shared_hosts > 0 and same_run_hits > 0) or close_change_hits > 1 or (same_run_hits > 0 and shared_profile >= 2):
            return "medium"
        return "surface-only"

    def _phase4_deep_trace_payload(self, trace_rows=None, max_neighbors=4):
        trace_rows = list(trace_rows or self._tunnel_trace_recent_rows(limit_runs=60))
        rows_sorted = sorted(
            trace_rows,
            key=lambda r: (
                self._analytics_ts_epoch(r.get("ts_utc") or r.get("ts_local")),
                str(r.get("run_id") or ""),
                str(r.get("router_id") or ""),
            ),
        )
        grouped = {}
        for row in rows_sorted:
            router_id = str(row.get("router_id") or "").strip()
            if not router_id:
                continue
            grouped.setdefault(router_id, []).append(dict(row))

        deduped_by_router = {}
        meta = {}
        for router_id, router_rows in grouped.items():
            grouped_runs = {}
            run_order = []
            for row in router_rows:
                key = str(row.get("run_id") or "") or f"__no_run__::{row.get('ts_local') or ''}"
                norm = dict(row)
                norm["semantic_signature"] = self._analytics_trace_semantic_signature(row)
                current = grouped_runs.get(key)
                if current is None:
                    grouped_runs[key] = norm
                    run_order.append(key)
                else:
                    if self._analytics_trace_row_quality(norm) >= self._analytics_trace_row_quality(current):
                        grouped_runs[key] = norm
            deduped = [grouped_runs[k] for k in run_order][-12:]
            deduped_by_router[router_id] = deduped
            union_hosts = set()
            run_ids = set()
            change_events = []
            lease_rows = 0
            surface_rows = 0
            log_rows = 0
            latest_profile = {}
            prev = None
            for row in deduped:
                for host in self._analytics_trace_hosts(row):
                    union_hosts.add(host)
                profile = self._analytics_trace_keyword_profile(row)
                latest_profile = profile or latest_profile
                if union_hosts or any(profile.values()):
                    surface_rows += 1
                if safe_int((row.get("keyword_counts") or {}).get("lease"), 0) > 0:
                    lease_rows += 1
                if row.get("phase_stage") or row.get("phase_trigger_reason") or row.get("run_id"):
                    log_rows += 1
                run_id = str(row.get("run_id") or "").strip()
                if run_id:
                    run_ids.add(run_id)
                if prev is not None and self._analytics_trace_change_detected(prev, row):
                    change_events.append({
                        "epoch": self._analytics_ts_epoch(row.get("ts_local") or row.get("ts_utc")),
                        "run_id": run_id,
                        "stage": str(row.get("phase_stage") or row.get("phase_label") or ""),
                        "trigger": str(row.get("phase_trigger_reason") or ""),
                    })
                prev = row
            meta[router_id] = {
                "name": grouped[router_id][-1].get("router_name") or f"Router {router_id}",
                "union_hosts": union_hosts,
                "run_ids": run_ids,
                "change_events": change_events,
                "lease_rows": lease_rows,
                "surface_rows": surface_rows,
                "log_rows": log_rows,
                "latest_profile": latest_profile,
            }

        payload = {}
        router_ids = sorted(meta.keys(), key=lambda v: safe_int(v, 999999))
        for router_id in router_ids:
            m = meta[router_id]
            relations = []
            shared_host_total = 0
            lease_corr = 0
            for other_id in router_ids:
                if other_id == router_id:
                    continue
                om = meta[other_id]
                shared_hosts = sorted(m["union_hosts"].intersection(om["union_hosts"]))
                same_runs = sorted(m["run_ids"].intersection(om["run_ids"]))
                shared_profile = sum(1 for k in set(m["latest_profile"].keys()).union(om["latest_profile"].keys()) if m["latest_profile"].get(k) and om["latest_profile"].get(k))
                close_change_hits = 0
                for a in m["change_events"]:
                    for b in om["change_events"]:
                        if a["epoch"] and b["epoch"] and abs(a["epoch"] - b["epoch"]) <= 180.0:
                            if (a["run_id"] and a["run_id"] == b["run_id"]) or (a["stage"] and a["stage"] == b["stage"]) or (a["trigger"] and a["trigger"] == b["trigger"]):
                                close_change_hits += 1
                relation_score = (len(shared_hosts) * 4.0) + (len(same_runs) * 1.5) + (close_change_hits * 2.5) + (shared_profile * 0.75)
                if relation_score < 1.5:
                    continue
                confidence = self._phase4_relation_confidence(len(shared_hosts), len(same_runs), close_change_hits, shared_profile)
                basis_parts = []
                if shared_hosts:
                    basis_parts.append(f"shared hosts {len(shared_hosts)}")
                if same_runs:
                    basis_parts.append(f"same runs {len(same_runs)}")
                if close_change_hits:
                    basis_parts.append(f"co-change {close_change_hits}")
                if shared_profile:
                    basis_parts.append(f"surface overlap {shared_profile}")
                if m["lease_rows"] and om["lease_rows"] and (shared_hosts or same_runs):
                    lease_corr += 1
                shared_host_total += len(shared_hosts)
                relations.append({
                    "router_id": other_id,
                    "router_name": om["name"],
                    "confidence": confidence,
                    "score": round(relation_score, 3),
                    "basis": " | ".join(basis_parts) if basis_parts else "surface-only inference",
                })
            relations.sort(key=lambda item: (-self._phase4_confidence_rank(item.get("confidence")), -item.get("score", 0.0), safe_int(item.get("router_id"), 999999)))
            top_rel = relations[:max_neighbors]
            router_conf = "surface-only"
            if any(r.get("confidence") == "high" for r in top_rel) and m["surface_rows"] >= 3:
                router_conf = "high"
            elif any(r.get("confidence") in {"high", "medium"} for r in top_rel) or m["log_rows"] >= 3 or shared_host_total > 0:
                router_conf = "medium"
            payload[router_id] = {
                "confidence": router_conf,
                "related_count": len(top_rel),
                "related_names": [r.get("router_name") for r in top_rel if r.get("router_name")],
                "surface_rows": m["surface_rows"],
                "lease_rows": m["lease_rows"],
                "log_rows": m["log_rows"],
                "lease_correlation": lease_corr,
                "shared_host_count": shared_host_total,
                "basis": top_rel[0].get("basis") if top_rel else "surface-only inference",
                "relations": top_rel,
                "warning": "Exact per-hop truth is not guaranteed; this mode combines visible tunnel/lease surfaces, recent co-change timing, and scenario context.",
            }
        return payload

    def _phase3_map_overlay_payload(self):
        analytics = self._long_term_analytics_payload()
        overlays = {}
        for row in analytics.get("router_stability", []):
            router_id = str(row.get("router_id") or "").strip()
            if not router_id:
                continue
            score_stats = row.get("stability_score") or {}
            score_avg = self._analytics_safe_float(score_stats.get("avg"))
            score_latest = self._analytics_safe_float(row.get("stability_score_latest"))
            weighted_change = self._analytics_safe_float(row.get("weighted_change_rate"))
            proxy_success_rate = self._analytics_safe_float(row.get("proxy_success_rate"))
            latest_ts = row.get("latest_ts")
            overlays[router_id] = {
                "score_avg": round(score_avg, 3) if score_avg is not None else None,
                "score_latest": round(score_latest, 3) if score_latest is not None else None,
                "weighted_change_rate": round(weighted_change, 4) if weighted_change is not None else None,
                "confidence": row.get("confidence"),
                "latest_stage": row.get("latest_stage"),
                "latest_trigger": row.get("latest_trigger"),
                "latest_generation": row.get("latest_generation"),
                "latest_ts": latest_ts,
                "recency_bucket": self._phase3_trace_recency_bucket(latest_ts),
                "proxy_success_rate": round(proxy_success_rate, 4) if proxy_success_rate is not None else None,
                "instability_recurrence": safe_int(row.get("instability_recurrence"), 0),
                "avg_severity_weight": self._analytics_safe_float(row.get("avg_severity_weight")),
                "trend_band": self._phase3_trend_band(score_latest, weighted_change, proxy_success_rate),
            }

        trace_rows = self._tunnel_trace_recent_rows(limit_runs=40)
        inferred_links = self._phase3_inferred_trace_links(trace_rows)
        phase4 = self._phase4_deep_trace_payload(trace_rows)
        for router_id, info in phase4.items():
            overlays.setdefault(router_id, {}).update({
                "phase4_confidence": info.get("confidence"),
                "phase4_related_count": info.get("related_count"),
                "phase4_related_names": info.get("related_names") or [],
                "phase4_surface_rows": info.get("surface_rows"),
                "phase4_lease_rows": info.get("lease_rows"),
                "phase4_log_rows": info.get("log_rows"),
                "phase4_lease_correlation": info.get("lease_correlation"),
                "phase4_shared_host_count": info.get("shared_host_count"),
                "phase4_basis": info.get("basis"),
            })
        return {
            "router_overlays": overlays,
            "inferred_links": inferred_links,
            "phase4": phase4,
        }

    def _long_term_analytics_payload(self):
        experiment_rows = self._experiment_list_campaign_rows(limit=50)
        recent_runs = self._measurement_list_recent_runs(limit=100)
        trace_rows = self._tunnel_trace_recent_rows(limit_runs=100)
        payload = {
            "generated_at_local": now_display(),
            "measurement_run_count": len(recent_runs),
            "experiment_row_count": len(experiment_rows),
            "trace_row_count": len(trace_rows),
            "overall": {},
            "scenario_buckets": [],
            "router_stability": [],
        }

        def pick(*values):
            for value in values:
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                return value
            return None

        summaries = []
        for rec in recent_runs:
            state = rec.get("state") or {}
            if state.get("status") != "completed":
                continue
            summary = (rec.get("summary") or {}).get("summary") or {}
            summaries.append(summary)

        def sum_metric(key):
            return sum(int(s.get(key) or 0) for s in summaries)

        routers_with_proxy = sum_metric("routers_with_client_proxy")
        routers_probed = sum_metric("routers_probed")
        payload["overall"] = {
            "completed_measurement_runs": len(summaries),
            "root_success_total": sum_metric("root_success"),
            "netdb_success_total": sum_metric("netdb_success"),
            "client_proxy_success_total": sum_metric("client_proxy_success"),
            "client_proxy_connect_success_total": sum_metric("client_proxy_connect_success"),
            "tunnel_trace_success_total": sum_metric("tunnel_trace_success"),
            "routers_probed_total": routers_probed,
            "routers_with_proxy_total": routers_with_proxy,
            "root_success_rate": round((sum_metric("root_success") / routers_probed), 4) if routers_probed else None,
            "netdb_success_rate": round((sum_metric("netdb_success") / routers_probed), 4) if routers_probed else None,
            "client_proxy_success_rate": round((sum_metric("client_proxy_success") / routers_with_proxy), 4) if routers_with_proxy else None,
            "root_latency_ms": self._analytics_numeric_stats([s.get("mean_root_latency_ms") for s in summaries]),
            "netdb_latency_ms": self._analytics_numeric_stats([s.get("mean_netdb_latency_ms") for s in summaries]),
            "proxy_latency_ms": self._analytics_numeric_stats([s.get("mean_client_proxy_latency_ms") for s in summaries]),
            "proxy_first_byte_ms": self._analytics_numeric_stats([s.get("mean_client_proxy_first_byte_ms") for s in summaries]),
            "startup_to_active_s": self._analytics_numeric_stats([s.get("mean_startup_to_active_s") for s in summaries]),
            "startup_to_ok_s": self._analytics_numeric_stats([s.get("mean_startup_to_ok_s") for s in summaries]),
            "startup_to_accepting_s": self._analytics_numeric_stats([s.get("mean_startup_to_accepting_s") for s in summaries]),
        }

        buckets = {}
        for row in experiment_rows:
            bucket = self._analytics_bucket_name(row)
            buckets.setdefault(bucket, []).append(row)
        bucket_sort_order = {"baseline": 0, "moderate_churn": 1, "high_churn": 2, "floodfill_targeted": 3, "adversarial_floodfill": 4, "other": 9}
        for bucket, rows in sorted(buckets.items(), key=lambda item: (bucket_sort_order.get(item[0], 99), item[0])):
            rows_sorted = sorted(
                rows,
                key=lambda r: (
                    float(r.get("mtime") or 0.0),
                    str(r.get("campaign_run_id") or r.get("final_run_id") or r.get("baseline_run_id") or ""),
                ),
                reverse=True,
            )
            final_root = [pick(r.get("final_root_success"), r.get("baseline_root_success")) for r in rows_sorted]
            final_netdb = [pick(r.get("final_netdb_success"), r.get("baseline_netdb_success")) for r in rows_sorted]
            final_client = [pick(r.get("final_client_proxy_success"), r.get("baseline_client_proxy_success")) for r in rows_sorted]
            deltas_client = [r.get("delta_client_proxy_success") for r in rows_sorted]
            payload["scenario_buckets"].append({
                "bucket": bucket,
                "rows": len(rows_sorted),
                "latest_experiment_label": rows_sorted[0].get("experiment_label") if rows_sorted else None,
                "statuses": sorted({str(r.get("status") or "unknown") for r in rows_sorted}),
                "root_success": self._analytics_numeric_stats(final_root),
                "netdb_success": self._analytics_numeric_stats(final_netdb),
                "client_proxy_success": self._analytics_numeric_stats(final_client),
                "mean_root_latency_ms": self._analytics_numeric_stats([pick(r.get("final_mean_root_latency_ms"), r.get("baseline_mean_root_latency_ms")) for r in rows_sorted]),
                "mean_netdb_latency_ms": self._analytics_numeric_stats([pick(r.get("final_mean_netdb_latency_ms"), r.get("baseline_mean_netdb_latency_ms")) for r in rows_sorted]),
                "mean_proxy_latency_ms": self._analytics_numeric_stats([pick(r.get("final_mean_proxy_latency_ms"), r.get("baseline_mean_proxy_latency_ms")) for r in rows_sorted]),
                "mean_proxy_first_byte_ms": self._analytics_numeric_stats([pick(r.get("final_mean_proxy_first_byte_ms"), r.get("baseline_mean_proxy_first_byte_ms")) for r in rows_sorted]),
                "full_ready_routers": self._analytics_numeric_stats([pick(r.get("final_full_ready_routers"), r.get("baseline_full_ready_routers")) for r in rows_sorted]),
                "delta_client_proxy_success": self._analytics_numeric_stats(deltas_client),
                "interim_measurements": self._analytics_numeric_stats([r.get("interim_measurements") for r in rows_sorted]),
            })

        by_router = {}
        for row in trace_rows:
            router_id = str(row.get("router_id") or "").strip()
            name = row.get("router_name") or f"Router {router_id or '?'}"
            by_router.setdefault((router_id, name), []).append(row)

        for (router_id, name), rows in sorted(by_router.items(), key=lambda item: safe_int(item[0][0], 999999)):
            rows_sorted = sorted(
                rows,
                key=lambda r: (
                    self._analytics_ts_epoch(r.get("ts_utc") or r.get("ts_local")),
                    str(r.get("run_id") or ""),
                    str(r.get("signature") or ""),
                ),
            )

            per_run_rows = []
            grouped = {}
            run_order = []
            for row in rows_sorted:
                run_id = str(row.get("run_id") or "")
                key = run_id or f"__no_run__::{row.get('ts_local') or row.get('router_id') or ''}"
                normalized = dict(row)
                normalized["semantic_signature"] = self._analytics_trace_semantic_signature(row)
                current_best = grouped.get(key)
                if current_best is None:
                    grouped[key] = normalized
                    run_order.append(key)
                else:
                    if self._analytics_trace_row_quality(normalized) >= self._analytics_trace_row_quality(current_best):
                        grouped[key] = normalized
            for key in run_order:
                per_run_rows.append(grouped[key])
            deduped = per_run_rows
            if not deduped:
                continue

            latest = deduped[-1]
            latest_scenario_row = None
            for row in deduped:
                if row.get("phase_label") not in {None, "", "standalone"} or row.get("phase_stage") not in {None, "", "standalone"}:
                    latest_scenario_row = row
            latest_stage_row = latest
            if (latest.get("phase_stage") in {None, "", "standalone"} and latest.get("phase_label") in {None, "", "standalone"} and latest_scenario_row is not None):
                latest_stage_row = latest_scenario_row

            phase2 = self._analytics_phase2_router_metrics(deduped)
            latest_generation = latest.get("analytics_generation") or latest.get("path_generation") or 1
            changes_seen = round((phase2.get("change_rate") or 0.0) * max(1, len(deduped) - 1))
            payload["router_stability"].append({
                "router_name": name,
                "router_id": router_id or latest.get("router_id"),
                "samples": len(deduped),
                "changes_seen": safe_int(changes_seen, 0),
                "change_rate": phase2.get("change_rate"),
                "weighted_change_rate": phase2.get("weighted_change_rate"),
                "latest_generation": latest_generation,
                "latest_signature": latest.get("semantic_signature") or latest.get("signature"),
                "latest_proxy_success": latest.get("client_proxy_success"),
                "proxy_success_rate": phase2.get("proxy_success_rate"),
                "stability_score": phase2.get("score_stats") or {},
                "stability_score_latest": phase2.get("score_latest"),
                "instability_recurrence": phase2.get("instability_recurrence"),
                "avg_severity_weight": phase2.get("avg_severity_weight"),
                "confidence": phase2.get("confidence"),
                "latest_stage": latest_stage_row.get("phase_stage") or latest_stage_row.get("phase_label"),
                "latest_trigger": latest_stage_row.get("phase_trigger_reason"),
                "latest_ts": latest.get("ts_local"),
            })

        payload["router_stability"].sort(
            key=lambda item: (
                ((item.get("stability_score") or {}).get("avg") if item.get("stability_score") else 10**9),
                (item.get("stability_score_latest") if item.get("stability_score_latest") is not None else 10**9),
                item.get("router_name") or "",
            )
        )
        return payload

    def _build_long_term_analytics_text(self, payload=None):
        payload = payload if payload is not None else self._long_term_analytics_payload()
        overall = payload.get("overall") or {}
        lines = ["Measurement trends", "=" * 72]
        lines.extend([
            f"Generated at           : {payload.get('generated_at_local', 'unknown')}",
            f"Measurement runs       : {payload.get('measurement_run_count', 0)}",
            f"Experiment rows        : {payload.get('experiment_row_count', 0)}",
            f"Trace rows             : {payload.get('trace_row_count', 0)}",
            "",
            "Overall multi-run measurement statistics",
            "--------------------------------------",
            f"Completed runs         : {overall.get('completed_measurement_runs', 0)}",
            f"Root success rate      : {overall.get('root_success_rate', 'n/a')}",
            f"netDb success rate     : {overall.get('netdb_success_rate', 'n/a')}",
            f"Client proxy rate      : {overall.get('client_proxy_success_rate', 'n/a')}",
            f"Root latency           : avg={((overall.get('root_latency_ms') or {}).get('avg', 'n/a'))} | median={((overall.get('root_latency_ms') or {}).get('median', 'n/a'))} | p95={((overall.get('root_latency_ms') or {}).get('p95', 'n/a'))} ms",
            f"netDb latency          : avg={((overall.get('netdb_latency_ms') or {}).get('avg', 'n/a'))} | median={((overall.get('netdb_latency_ms') or {}).get('median', 'n/a'))} | p95={((overall.get('netdb_latency_ms') or {}).get('p95', 'n/a'))} ms",
            f"Proxy latency          : avg={((overall.get('proxy_latency_ms') or {}).get('avg', 'n/a'))} | median={((overall.get('proxy_latency_ms') or {}).get('median', 'n/a'))} | p95={((overall.get('proxy_latency_ms') or {}).get('p95', 'n/a'))} ms",
            f"Proxy first byte       : avg={((overall.get('proxy_first_byte_ms') or {}).get('avg', 'n/a'))} | median={((overall.get('proxy_first_byte_ms') or {}).get('median', 'n/a'))} | p95={((overall.get('proxy_first_byte_ms') or {}).get('p95', 'n/a'))} ms",
            f"Startup -> active      : avg={((overall.get('startup_to_active_s') or {}).get('avg', 'n/a'))} | p95={((overall.get('startup_to_active_s') or {}).get('p95', 'n/a'))} s",
            f"Startup -> OK          : avg={((overall.get('startup_to_ok_s') or {}).get('avg', 'n/a'))} | p95={((overall.get('startup_to_ok_s') or {}).get('p95', 'n/a'))} s",
            f"Startup -> accepting   : avg={((overall.get('startup_to_accepting_s') or {}).get('avg', 'n/a'))} | p95={((overall.get('startup_to_accepting_s') or {}).get('p95', 'n/a'))} s",
            "",
            "Scenario bucket analytics",
            "-------------------------",
        ])
        buckets = payload.get("scenario_buckets") or []
        if not buckets:
            lines.append("No scenario bucket rows available yet.")
        else:
            for item in buckets:
                lines.extend([
                    f"{item.get('bucket', 'unknown')}  (rows={item.get('rows', 0)})",
                    f"  latest label        : {item.get('latest_experiment_label', 'n/a')}",
                    f"  statuses            : {', '.join(item.get('statuses') or []) or 'n/a'}",
                    f"  root/netdb/client   : avg={((item.get('root_success') or {}).get('avg', 'n/a'))} / {((item.get('netdb_success') or {}).get('avg', 'n/a'))} / {((item.get('client_proxy_success') or {}).get('avg', 'n/a'))}",
                    f"  latency root/netdb  : avg={((item.get('mean_root_latency_ms') or {}).get('avg', 'n/a'))} / {((item.get('mean_netdb_latency_ms') or {}).get('avg', 'n/a'))} ms",
                    f"  latency proxy/fb    : avg={((item.get('mean_proxy_latency_ms') or {}).get('avg', 'n/a'))} / {((item.get('mean_proxy_first_byte_ms') or {}).get('avg', 'n/a'))} ms",
                    f"  full-ready avg      : {((item.get('full_ready_routers') or {}).get('avg', 'n/a'))}",
                    f"  delta client avg    : {((item.get('delta_client_proxy_success') or {}).get('avg', 'n/a'))}",
                    f"  interim probes avg  : {((item.get('interim_measurements') or {}).get('avg', 'n/a'))}",
                    "",
                ])
        lines.extend(["Router long-term stability", "--------------------------"])
        routers = payload.get("router_stability") or []
        if not routers:
            lines.append("No router stability history is available yet.")
        else:
            for item in routers[:10]:
                sc = item.get('stability_score') or {}
                lines.extend([
                    f"{item.get('router_name', 'Router ?')}",
                    f"  samples/change rate  : {item.get('samples', 0)} / {item.get('change_rate', 'n/a')}",
                    f"  weighted change      : {item.get('weighted_change_rate', 'n/a')}",
                    f"  score avg/p95/latest : {sc.get('avg', 'n/a')} / {sc.get('p95', 'n/a')} / {item.get('stability_score_latest', 'n/a')}",
                    f"  proxy success rate   : {item.get('proxy_success_rate', 'n/a')}",
                    f"  recurrence/severity  : {item.get('instability_recurrence', 'n/a')} / {item.get('avg_severity_weight', 'n/a')}",
                    f"  confidence           : {item.get('confidence', 'n/a')}",
                    f"  latest gen/stage     : {item.get('latest_generation', 'n/a')} / {item.get('latest_stage', 'n/a')} / {item.get('latest_trigger', 'n/a')}",
                    f"  latest trace         : {item.get('latest_signature', 'n/a')} @ {item.get('latest_ts', 'n/a')}",
                    "",
                ])
        lines.extend(["Phase 4 deep trace / inferred hop mode", "------------------------------------"])
        phase4_payload = self._phase4_deep_trace_payload(self._tunnel_trace_recent_rows(limit_runs=40))
        if not phase4_payload:
            lines.append("No Phase 4 deep-trace evidence is available yet.")
        else:
            ordered_ids = sorted(phase4_payload.keys(), key=lambda v: safe_int(v, 999999))
            for router_id in ordered_ids[:10]:
                item = phase4_payload.get(router_id) or {}
                lines.extend([
                    f"Router {router_id}",
                    f"  confidence          : {item.get('confidence', 'surface-only')}",
                    f"  related routers     : {', '.join(item.get('related_names') or []) or 'none'}",
                    f"  evidence rows       : surface={item.get('surface_rows', 0)} | lease={item.get('lease_rows', 0)} | log={item.get('log_rows', 0)}",
                    f"  lease correlation   : {item.get('lease_correlation', 0)} | shared hosts={item.get('shared_host_count', 0)}",
                    f"  inference basis     : {item.get('basis', 'surface-only inference')}",
                    "  warning             : exact per-hop truth is not guaranteed",
                    "",
                ])
        lines.extend([
            "",
            "Observed path history",
            "-----------------------------",
        ])
        phase5_payload = self._phase5_hop_history_payload(self._tunnel_trace_recent_rows(limit_runs=80))
        lines.extend([
            f"Routers tracked        : {phase5_payload.get('router_count', 0)}",
            f"Recorded events        : {phase5_payload.get('event_count', 0)}",
            f"Source model           : {', '.join(phase5_payload.get('source_modes') or []) or 'surface-inferred'}",
            "Stores per-router hop-role/path-signature history over time using conservative surface-derived estimates.",
            "This section tracks observed path changes over time. It does not claim exact per-hop ground truth.",
            "",
        ])
        lines.extend([
            "Authoritative hop records",
            "---------------------------------",
        ])
        phase5b_payload = self._phase5b_hop_truth_payload()
        lines.extend([
            f"Exact events           : {phase5b_payload.get('event_count', 0)}",
            f"Tunnels tracked        : {phase5b_payload.get('tunnel_count', 0)}",
            f"Routers tracked        : {phase5b_payload.get('router_count', 0)}",
            f"Source modes           : {', '.join(phase5b_payload.get('source_modes') or []) or 'none'}",
            f"Candidate files        : {phase5b_payload.get('candidate_file_count', 0)}",
            "Stores authoritative hop-chain events when emulator-observed or log-derived truth files are available.",
            "If no authoritative source exists yet, this section remains empty rather than fabricating exact hop truth.",
            "",
        ])
        lines.append("Measurement trends aggregate completed measurement runs, scenario rows, trace history, per-router stability trends, inferred path hints, stored path-history events, and authoritative hop records when available.")
        return "\n".join(lines).rstrip()

    def _long_term_analytics_export_rows(self, payload=None):
        payload = payload if payload is not None else self._long_term_analytics_payload()
        rows = []
        overall = payload.get('overall') or {}
        rows.append({
            'section': 'overall',
            'name': 'all_measurements',
            'runs': overall.get('completed_measurement_runs'),
            'root_success_rate': overall.get('root_success_rate'),
            'netdb_success_rate': overall.get('netdb_success_rate'),
            'client_proxy_success_rate': overall.get('client_proxy_success_rate'),
            'root_latency_avg_ms': ((overall.get('root_latency_ms') or {}).get('avg')),
            'root_latency_p95_ms': ((overall.get('root_latency_ms') or {}).get('p95')),
            'netdb_latency_avg_ms': ((overall.get('netdb_latency_ms') or {}).get('avg')),
            'netdb_latency_p95_ms': ((overall.get('netdb_latency_ms') or {}).get('p95')),
            'proxy_latency_avg_ms': ((overall.get('proxy_latency_ms') or {}).get('avg')),
            'proxy_latency_p95_ms': ((overall.get('proxy_latency_ms') or {}).get('p95')),
            'proxy_first_byte_avg_ms': ((overall.get('proxy_first_byte_ms') or {}).get('avg')),
            'startup_active_avg_s': ((overall.get('startup_to_active_s') or {}).get('avg')),
            'startup_ok_avg_s': ((overall.get('startup_to_ok_s') or {}).get('avg')),
            'startup_accept_avg_s': ((overall.get('startup_to_accepting_s') or {}).get('avg')),
        })
        for item in payload.get('scenario_buckets') or []:
            rows.append({
                'section': 'bucket',
                'name': item.get('bucket'),
                'runs': item.get('rows'),
                'root_success_rate': ((item.get('root_success') or {}).get('avg')),
                'netdb_success_rate': ((item.get('netdb_success') or {}).get('avg')),
                'client_proxy_success_rate': ((item.get('client_proxy_success') or {}).get('avg')),
                'root_latency_avg_ms': ((item.get('mean_root_latency_ms') or {}).get('avg')),
                'root_latency_p95_ms': ((item.get('mean_root_latency_ms') or {}).get('p95')),
                'netdb_latency_avg_ms': ((item.get('mean_netdb_latency_ms') or {}).get('avg')),
                'netdb_latency_p95_ms': ((item.get('mean_netdb_latency_ms') or {}).get('p95')),
                'proxy_latency_avg_ms': ((item.get('mean_proxy_latency_ms') or {}).get('avg')),
                'proxy_latency_p95_ms': ((item.get('mean_proxy_latency_ms') or {}).get('p95')),
                'proxy_first_byte_avg_ms': ((item.get('mean_proxy_first_byte_ms') or {}).get('avg')),
                'startup_active_avg_s': None,
                'startup_ok_avg_s': None,
                'startup_accept_avg_s': None,
            })
        for item in payload.get('router_stability') or []:
            sc = item.get('stability_score') or {}
            rows.append({
                'section': 'router_stability',
                'name': item.get('router_name'),
                'runs': item.get('samples'),
                'root_success_rate': None,
                'netdb_success_rate': None,
                'client_proxy_success_rate': item.get('proxy_success_rate'),
                'root_latency_avg_ms': None,
                'root_latency_p95_ms': None,
                'netdb_latency_avg_ms': None,
                'netdb_latency_p95_ms': None,
                'proxy_latency_avg_ms': None,
                'proxy_latency_p95_ms': None,
                'proxy_first_byte_avg_ms': None,
                'startup_active_avg_s': None,
                'startup_ok_avg_s': None,
                'startup_accept_avg_s': None,
                'stability_score_avg': sc.get('avg'),
                'stability_score_p95': sc.get('p95'),
                'stability_score_latest': item.get('stability_score_latest'),
                'change_rate': item.get('change_rate'),
                'weighted_change_rate': item.get('weighted_change_rate'),
                'instability_recurrence': item.get('instability_recurrence'),
                'avg_severity_weight': item.get('avg_severity_weight'),
                'confidence': item.get('confidence'),
                'latest_generation': item.get('latest_generation'),
                'latest_stage': item.get('latest_stage'),
                'latest_trigger': item.get('latest_trigger'),
                'phase4_confidence': ((self._phase4_deep_trace_payload(self._tunnel_trace_recent_rows(limit_runs=40)).get(str(item.get('router_id') or ''), {}) or {}).get('confidence')),
                'phase4_related_count': ((self._phase4_deep_trace_payload(self._tunnel_trace_recent_rows(limit_runs=40)).get(str(item.get('router_id') or ''), {}) or {}).get('related_count')),
            })
        return rows

    def _experiment_export_path(self, ext):
        ensure_dir(CAMPAIGN_ROOT_DIR)
        timestamp_local = now_display().replace(":", "-").replace(" ", "_")
        return os.path.join(CAMPAIGN_ROOT_DIR, f"experiment-matrix-{timestamp_local}.{ext}")

    def export_experiment_matrix_csv(self):
        rows = self._experiment_export_rows()
        if not rows:
            QMessageBox.information(self, APP_NAME, "No experiment rows are available yet.")
            return
        path = self._experiment_export_path("csv")
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        self.deploy_status.setText(f"Experiment matrix CSV written to: {path}")
        self.append_measurement_log(f"[{now_display()}] Experiment matrix CSV written to: {path}")
        QMessageBox.information(self, APP_NAME, f"Experiment matrix CSV written to:\n{path}")

    def export_experiment_matrix_json(self):
        rows = self._experiment_export_rows()
        if not rows:
            QMessageBox.information(self, APP_NAME, "No experiment rows are available yet.")
            return
        path = self._experiment_export_path("json")
        write_json_atomic(path, rows)
        self.deploy_status.setText(f"Experiment matrix JSON written to: {path}")
        self.append_measurement_log(f"[{now_display()}] Experiment matrix JSON written to: {path}")
        QMessageBox.information(self, APP_NAME, f"Experiment matrix JSON written to:\n{path}")

    def _long_term_analytics_export_path(self, ext):
        ensure_dir(CAMPAIGN_ROOT_DIR)
        timestamp_local = now_display().replace(":", "-").replace(" ", "_")
        return os.path.join(CAMPAIGN_ROOT_DIR, f"long-term-analytics-v1-{timestamp_local}.{ext}")

    def export_long_term_analytics_csv(self):
        payload = self._long_term_analytics_payload()
        rows = self._long_term_analytics_export_rows(payload)
        if not rows:
            QMessageBox.information(self, APP_NAME, "No long-term analytics rows are available yet.")
            return
        path = self._long_term_analytics_export_path("csv")
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        self.deploy_status.setText(f"Measurement trends CSV written to: {path}")
        self.append_measurement_log(f"[{now_display()}] Measurement trends CSV written to: {path}")
        QMessageBox.information(self, APP_NAME, f"Measurement trends CSV written to:\n{path}")

    def export_long_term_analytics_json(self):
        payload = self._long_term_analytics_payload()
        payload["summary_text"] = self._build_long_term_analytics_text(payload)
        payload["flat_rows"] = self._long_term_analytics_export_rows(payload)
        path = self._long_term_analytics_export_path("json")
        write_json_atomic(path, payload)
        self.deploy_status.setText(f"Measurement trends JSON written to: {path}")
        self.append_measurement_log(f"[{now_display()}] Measurement trends JSON written to: {path}")
        QMessageBox.information(self, APP_NAME, f"Measurement trends JSON written to:\n{path}")


    def _phase5_role_estimate(self, row):
        profile = self._analytics_trace_keyword_profile(row)
        if profile.get("lease") or profile.get("client") or profile.get("inbound"):
            return "endpoint"
        if profile.get("participating") or profile.get("peer"):
            return "middle"
        if profile.get("outbound") or profile.get("exploratory"):
            return "entry"
        return "unknown"

    def _phase5_hop_index_estimate(self, row):
        role = self._phase5_role_estimate(row)
        if role == "entry":
            return 1
        if role == "middle":
            return 2
        if role == "endpoint":
            return 3
        return None

    def _phase5_change_type(self, previous_event, current_event):
        if not previous_event:
            return "initial_observation"
        prev_sig = str(previous_event.get("path_signature") or "")
        curr_sig = str(current_event.get("path_signature") or "")
        prev_hop = previous_event.get("hop_index_estimate")
        curr_hop = current_event.get("hop_index_estimate")
        prev_role = str(previous_event.get("role_estimate") or "")
        curr_role = str(current_event.get("role_estimate") or "")
        prev_neighbors = set(previous_event.get("related_router_ids") or [])
        curr_neighbors = set(current_event.get("related_router_ids") or [])
        if prev_hop != curr_hop and curr_hop is not None:
            return "hop_position_changed"
        if prev_role != curr_role and curr_role:
            return "role_changed"
        if prev_sig and curr_sig and prev_sig != curr_sig:
            return "path_signature_changed"
        if prev_neighbors != curr_neighbors:
            return "related_router_set_changed"
        return "stable"

    def _phase5_hop_history_payload(self, trace_rows=None, max_events_per_router=18):
        trace_rows = list(trace_rows or self._tunnel_trace_recent_rows(limit_runs=140))
        rows_sorted = sorted(
            trace_rows,
            key=lambda r: (
                self._analytics_ts_epoch(r.get("ts_utc") or r.get("ts_local")),
                str(r.get("run_id") or ""),
                safe_int(r.get("router_id"), 0),
            ),
        )
        phase4 = self._phase4_deep_trace_payload(rows_sorted)
        grouped = {}
        for row in rows_sorted:
            router_id = str(row.get("router_id") or "").strip()
            if not router_id:
                continue
            grouped.setdefault(router_id, []).append(dict(row))

        router_histories = []
        role_totals = {"entry": 0, "middle": 0, "endpoint": 0, "unknown": 0}
        total_events = 0
        source_modes = set()

        for router_id in sorted(grouped.keys(), key=lambda value: safe_int(value, 999999)):
            router_rows = grouped.get(router_id) or []
            grouped_runs = {}
            run_order = []
            for row in router_rows:
                key = str(row.get("run_id") or "") or f"__no_run__::{row.get('ts_local') or row.get('ts_utc') or ''}"
                norm = dict(row)
                norm["semantic_signature"] = self._analytics_trace_semantic_signature(row)
                current = grouped_runs.get(key)
                if current is None:
                    grouped_runs[key] = norm
                    run_order.append(key)
                else:
                    if self._analytics_trace_row_quality(norm) >= self._analytics_trace_row_quality(current):
                        grouped_runs[key] = norm
            deduped = [grouped_runs[key] for key in run_order]
            phase4_info = phase4.get(str(router_id), {}) or {}
            related_names = list(phase4_info.get("related_names") or [])[:4]
            related_router_ids = [str(value).replace("Router ", "").strip() for value in related_names]
            source_confidence = phase4_info.get("confidence") or "surface-only"
            source_mode = "surface-inferred"
            source_modes.add(source_mode)

            events = []
            path_signatures = []
            neighbor_counts = {}
            role_counts = {"entry": 0, "middle": 0, "endpoint": 0, "unknown": 0}
            hop_counts = {}
            prev_event = None

            for row in deduped[-max_events_per_router:]:
                role_estimate = self._phase5_role_estimate(row)
                hop_index_estimate = self._phase5_hop_index_estimate(row)
                role_counts[role_estimate] = role_counts.get(role_estimate, 0) + 1
                role_totals[role_estimate] = role_totals.get(role_estimate, 0) + 1
                if hop_index_estimate is not None:
                    hop_counts[str(hop_index_estimate)] = hop_counts.get(str(hop_index_estimate), 0) + 1
                for name in related_names:
                    neighbor_counts[name] = neighbor_counts.get(name, 0) + 1

                event = {
                    "ts_local": row.get("ts_local") or row.get("ts_utc"),
                    "ts_utc": row.get("ts_utc"),
                    "run_id": row.get("run_id"),
                    "scenario_label": row.get("scenario_label") or row.get("phase_label") or row.get("phase_stage") or "unknown",
                    "phase_label": row.get("phase_label"),
                    "phase_stage": row.get("phase_stage"),
                    "phase_trigger_reason": row.get("phase_trigger_reason"),
                    "path_signature": row.get("semantic_signature") or self._analytics_trace_semantic_signature(row),
                    "role_estimate": role_estimate,
                    "hop_index_estimate": hop_index_estimate,
                    "sample_b32_hosts": self._analytics_trace_hosts(row),
                    "related_router_ids": related_router_ids,
                    "related_router_names": related_names,
                    "source_mode": source_mode,
                    "source_confidence": source_confidence,
                }
                event["changed_from_previous"] = bool(prev_event and self._analytics_trace_change_detected(prev_event, row))
                event["change_type"] = self._phase5_change_type(prev_event, event)
                events.append(event)
                path_signatures.append(event["path_signature"])
                prev_event = event
                total_events += 1

            unique_signatures = [sig for sig in dict.fromkeys(path_signatures) if sig]
            first_seen = events[0]["ts_local"] if events else None
            last_seen = events[-1]["ts_local"] if events else None

            role_order = [("entry", role_counts.get("entry", 0)), ("middle", role_counts.get("middle", 0)), ("endpoint", role_counts.get("endpoint", 0)), ("unknown", role_counts.get("unknown", 0))]
            role_order.sort(key=lambda item: (-item[1], item[0]))
            most_common_role = role_order[0][0] if role_order and role_order[0][1] > 0 else "unknown"

            hop_order = sorted(hop_counts.items(), key=lambda item: (-item[1], safe_int(item[0], 999)))
            most_common_hop_index = safe_int(hop_order[0][0], 0) if hop_order else None

            neighbor_order = sorted(neighbor_counts.items(), key=lambda item: (-item[1], item[0]))
            most_common_neighbors = [item[0] for item in neighbor_order[:3]]

            path_rebuilds = sum(1 for event in events if event.get("change_type") in ("path_signature_changed", "related_router_set_changed"))
            position_changes = sum(1 for event in events if event.get("change_type") in ("hop_position_changed", "role_changed"))
            appearance_rate = round(len(events) / max(1, len(deduped)), 4) if deduped else 0.0

            router_histories.append({
                "router_id": router_id,
                "router_name": (deduped[-1].get("router_name") if deduped else None) or f"Router {router_id}",
                "source_mode": source_mode,
                "source_confidence": source_confidence,
                "samples": len(events),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "appearance_rate": appearance_rate,
                "role_counts": role_counts,
                "hop_index_counts": hop_counts,
                "most_common_role": most_common_role,
                "most_common_hop_index": most_common_hop_index,
                "path_rebuilds": path_rebuilds,
                "position_changes": position_changes,
                "path_diversity": len(unique_signatures),
                "neighbor_diversity": len(neighbor_counts),
                "most_common_neighbors": most_common_neighbors,
                "recent_path_signatures": unique_signatures[-5:],
                "events": events,
            })

        payload = {
            "generated_at_local": now_display(),
            "generated_at_utc": now_iso_utc(),
            "version": "5A",
            "testnet_base": find_testnet_base(),
            "trace_row_count": len(rows_sorted),
            "router_count": len(router_histories),
            "event_count": total_events,
            "source_modes": sorted(source_modes),
            "role_totals": role_totals,
            "notes": {
                "summary": "Observed path history records per-router path events over time using the existing trace layers.",
                "source_model": "surface-inferred hop history with conservative role and hop-index estimates.",
                "limitation": "It does not claim exact per-hop ground truth unless a stronger router-internal source is added later.",
            },
            "routers": router_histories,
        }
        return payload

    def _build_phase5_hop_history_text(self, payload=None):
        payload = payload if payload is not None else self._phase5_hop_history_payload()
        lines = ["Observed path history", "=" * 72]
        lines.extend([
            f"Generated at           : {payload.get('generated_at_local', 'unknown')}",
            f"Trace rows scanned     : {payload.get('trace_row_count', 0)}",
            f"Routers tracked        : {payload.get('router_count', 0)}",
            f"Recorded events        : {payload.get('event_count', 0)}",
            f"Source model           : {', '.join(payload.get('source_modes') or []) or 'surface-inferred'}",
            "",
            "Role totals",
            "-----------",
        ])
        role_totals = payload.get("role_totals") or {}
        lines.extend([
            f"Entry estimates        : {role_totals.get('entry', 0)}",
            f"Middle estimates       : {role_totals.get('middle', 0)}",
            f"Endpoint estimates     : {role_totals.get('endpoint', 0)}",
            f"Unknown estimates      : {role_totals.get('unknown', 0)}",
            "",
            "Per-router hop history summary",
            "------------------------------",
        ])
        routers = payload.get("routers") or []
        if not routers:
            lines.append("No hop-history events are available yet.")
        else:
            for item in routers[:10]:
                lines.extend([
                    f"{item.get('router_name', 'Router ?')}",
                    f"  source/confidence    : {item.get('source_mode', 'surface-inferred')} / {item.get('source_confidence', 'surface-only')}",
                    f"  samples              : {item.get('samples', 0)} | first={item.get('first_seen', 'n/a')} | last={item.get('last_seen', 'n/a')}",
                    f"  role/hop estimate    : {item.get('most_common_role', 'unknown')} / {item.get('most_common_hop_index', 'n/a')}",
                    f"  rebuilds/position    : {item.get('path_rebuilds', 0)} / {item.get('position_changes', 0)}",
                    f"  path diversity       : {item.get('path_diversity', 0)} | neighbors={item.get('neighbor_diversity', 0)}",
                    f"  common neighbors     : {', '.join(item.get('most_common_neighbors') or []) or 'none'}",
                    f"  signatures           : {', '.join(item.get('recent_path_signatures') or []) or 'none'}",
                    "",
                ])
        lines.extend([
            "Notes",
            "-----",
            "This view stores conservative per-router path history over time.",
            "Role and hop index are estimates derived from visible tunnel/lease surfaces, not exact hop truth.",
        ])
        return "\n".join(lines).rstrip()

    def _phase5_hop_history_export_rows(self, payload=None):
        payload = payload if payload is not None else self._phase5_hop_history_payload()
        rows = []
        for item in payload.get("routers") or []:
            rows.append({
                "router_id": item.get("router_id"),
                "router_name": item.get("router_name"),
                "source_mode": item.get("source_mode"),
                "source_confidence": item.get("source_confidence"),
                "samples": item.get("samples"),
                "first_seen": item.get("first_seen"),
                "last_seen": item.get("last_seen"),
                "appearance_rate": item.get("appearance_rate"),
                "most_common_role": item.get("most_common_role"),
                "most_common_hop_index": item.get("most_common_hop_index"),
                "path_rebuilds": item.get("path_rebuilds"),
                "position_changes": item.get("position_changes"),
                "path_diversity": item.get("path_diversity"),
                "neighbor_diversity": item.get("neighbor_diversity"),
                "most_common_neighbors": ", ".join(item.get("most_common_neighbors") or []),
                "recent_path_signatures": ", ".join(item.get("recent_path_signatures") or []),
            })
        return rows

    def _phase5_export_paths(self):
        ensure_dir(HOP_HISTORY_ROOT_DIR)
        ensure_dir(os.path.join(HOP_HISTORY_ROOT_DIR, "routers"))
        ensure_dir(os.path.join(HOP_HISTORY_ROOT_DIR, "summaries"))
        base = filesystem_safe_name(os.path.basename(find_testnet_base() or "testnet"))
        return {
            "json": os.path.join(HOP_HISTORY_ROOT_DIR, "summaries", f"{base}-phase5a-hop-history.json"),
            "csv": os.path.join(HOP_HISTORY_ROOT_DIR, "summaries", f"{base}-phase5a-hop-history.csv"),
            "routers": os.path.join(HOP_HISTORY_ROOT_DIR, "routers"),
        }

    def export_phase5_hop_history_csv(self):
        payload = self._phase5_hop_history_payload()
        rows = self._phase5_hop_history_export_rows(payload)
        if not rows:
            QMessageBox.information(self, APP_NAME, "No path-history rows are available yet.")
            return
        paths = self._phase5_export_paths()
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        with open(paths["csv"], "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        self.deploy_status.setText(f"Observed path history CSV written to: {paths['csv']}")
        self.append_measurement_log(f"[{now_display()}] Observed path history CSV written to: {paths['csv']}")
        QMessageBox.information(self, APP_NAME, f"Observed path history CSV written to:\n{paths['csv']}")

    def export_phase5_hop_history_json(self):
        payload = self._phase5_hop_history_payload()
        payload["summary_text"] = self._build_phase5_hop_history_text(payload)
        payload["flat_rows"] = self._phase5_hop_history_export_rows(payload)
        paths = self._phase5_export_paths()
        write_json_atomic(paths["json"], payload)
        for item in payload.get("routers") or []:
            router_path = os.path.join(paths["routers"], f"router-{filesystem_safe_name(str(item.get('router_id') or 'unknown'))}-hop-history.json")
            write_json_atomic(router_path, item)
        self.deploy_status.setText(f"Observed path history JSON written to: {paths['json']}")
        self.append_measurement_log(f"[{now_display()}] Observed path history JSON written to: {paths['json']}")
        QMessageBox.information(self, APP_NAME, f"Observed path history JSON written to:\n{paths['json']}")





    def _phase5c_root_dir(self):
        root = os.path.join(HOP_TRUTH_ROOT_DIR, "phase5c")
        ensure_dir(root)
        return root

    def _phase5c_state_path(self):
        return os.path.join(self._phase5c_root_dir(), "auto_extract_state.json")

    def _phase5c_default_state(self):
        return {
            "generated_at_local": now_display(),
            "generated_at_utc": now_iso_utc(),
            "auto_mode": "enabled",
            "runs_scanned": 0,
            "trace_rows_scanned": 0,
            "auto_events_captured": 0,
            "duplicate_rows_skipped": 0,
            "rows_without_authoritative_chain": 0,
            "source_files_scanned": 0,
            "source_records_scanned": 0,
            "trace_events_captured": 0,
            "source_file_events_captured": 0,
            "log_files_scanned": 0,
            "log_lines_scanned": 0,
            "log_source_events_materialized": 0,
            "last_generated_source_path": "",
            "source_contract_path": "",
            "source_example_path": "",
            "source_import_root": "",
            "source_run_import_dir": "",
            "source_authoritative_dir": "",
            "latest_run_id": "",
            "latest_run_dir": "",
            "latest_source_fields": [],
            "last_result": "No automatic truth extraction has run yet.",
            "last_raw_output_path": os.path.join(HOP_TRUTH_ROOT_DIR, "raw", "exact-hop-source.jsonl"),
            "last_scan_trigger": "none",
            "last_scan_started_local": "",
            "last_scan_finished_local": "",
            "last_normalization_started_local": "",
            "last_normalization_finished_local": "",
            "last_normalization_result": "Normalization has not run yet.",
            "last_normalized_event_count": 0,
            "last_normalization_manifest_path": "",
            "last_normalization_jsonl_path": "",
            "seen_keys": [],
        }

    def _phase5c_enabled(self):
        mode_widget = getattr(self, "phase5c_auto_mode", None)
        if not mode_widget:
            return False
        return str(mode_widget.currentText() or "disabled").strip().lower() != "disabled"

    def _phase5c_load_state(self):
        state = read_json_file(self._phase5c_state_path(), default={}) or {}
        base = self._phase5c_default_state()
        base.update(state)
        base["seen_keys"] = list(base.get("seen_keys") or [])[-5000:]
        mode_widget = getattr(self, "phase5c_auto_mode", None)
        if mode_widget:
            base["auto_mode"] = mode_widget.currentText().strip() or base.get("auto_mode", "enabled")
        return base

    def _phase5c_save_state(self, **updates):
        state = self._phase5c_load_state()
        state.update(updates)
        state["generated_at_local"] = now_display()
        state["generated_at_utc"] = now_iso_utc()
        state["seen_keys"] = list(state.get("seen_keys") or [])[-5000:]
        write_json_atomic(self._phase5c_state_path(), state)
        return state

    def reset_phase5c_state(self):
        default = self._phase5c_default_state()
        default["last_result"] = "Automatic path ingestion state was reset."
        write_json_atomic(self._phase5c_state_path(), default)
        self.append_measurement_log(f"[{now_display()}] Automatic path ingestion state reset.")
        self.update_measurement_panel()
        QMessageBox.information(self, APP_NAME, "Automatic path ingestion state reset.")

    def _phase5c_context_from_run_id(self, run_id, raw=None):
        raw = dict(raw or {})
        phase_index = load_recent_campaign_measurement_phase_index()
        info = phase_index.get(str(run_id or "").strip()) or {}
        scenario_label = str(raw.get("scenario_label") or info.get("experiment_label") or "").strip()
        bucket = str(raw.get("scenario_bucket") or "").strip().lower()
        label_l = scenario_label.lower()
        if not bucket:
            if "baseline" in label_l or info.get("is_baseline"):
                bucket = "baseline"
            elif "adversarial" in label_l:
                bucket = "adversarial_floodfill"
            elif "floodfill" in label_l:
                bucket = "floodfill_targeted"
            elif "high" in label_l:
                bucket = "high_churn"
            elif "moderate" in label_l:
                bucket = "moderate_churn"
            else:
                bucket = "other"
        return {
            "scenario_label": scenario_label or f"{bucket}_auto_truth",
            "scenario_bucket": bucket or "other",
            "phase_stage": str(raw.get("phase_stage") or info.get("stage") or raw.get("stage") or "runtime"),
            "phase_trigger_reason": str(raw.get("phase_trigger_reason") or info.get("trigger_reason") or raw.get("trigger") or "phase5c_auto_extract"),
        }

    def _phase5c_extract_authoritative_chain(self, raw):
        if not isinstance(raw, dict):
            return [], ""
        inspected = [
            ("row", raw),
            ("trace", raw.get("trace")),
            ("tunnel_trace", raw.get("tunnel_trace")),
            ("metadata", raw.get("metadata")),
            ("exact_hop_truth", raw.get("exact_hop_truth")),
            ("latest_startup", raw.get("latest_startup")),
        ]
        best_chain = []
        best_source = ""
        for source_name, obj in inspected:
            if obj is None:
                continue
            for chain in phase5c_extract_candidate_chains(obj):
                if len(chain) > len(best_chain):
                    best_chain = list(chain)
                    best_source = source_name
        return best_chain, best_source


    def _phase5c_is_runtime_authoritative_row(self, row, source_field=""):
        row = dict(row or {})
        if not row:
            return False
        explicit_source = str(
            row.get("exact_truth_source")
            or row.get("truth_source")
            or (row.get("metadata") or {}).get("truth_source")
            or (row.get("metadata") or {}).get("source_mode")
            or ""
        ).strip().lower()
        if explicit_source in {"authoritative-cache", "cached-truth", "cache"}:
            return False
        trace = row.get("trace") or row.get("tunnel_trace") or {}
        trace_source = str((trace or {}).get("exact_truth_source") or "").strip().lower()
        if trace_source in {"authoritative-cache", "cached-truth", "cache"}:
            return False
        if str(source_field or "").strip().lower() in {"trace", "tunnel_trace"} and not (explicit_source or trace_source):
            return False
        direct_fields = [key for key in PHASE5C_CHAIN_KEYS if row.get(key)]
        if direct_fields:
            return True
        metadata = row.get("metadata") or {}
        if any(metadata.get(key) for key in PHASE5C_CHAIN_KEYS):
            return True
        exact_truth = row.get("exact_hop_truth") or {}
        if any(exact_truth.get(key) for key in PHASE5C_CHAIN_KEYS):
            return True
        return False


    def _phase5c_import_root(self):
        return ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, "imports"))

    def _phase5c_authoritative_contract_path(self, run_dir):
        run_dir = str(run_dir or "").strip()
        return os.path.join(run_dir, "authoritative-source-contract.json") if run_dir else ""

    def _phase5c_authoritative_example_path(self):
        return os.path.join(self._phase5c_import_root(), "authoritative-hop-events.example.jsonl")

    def _phase5c_write_source_contract(self, run_dir):
        run_meta = self._phase5c_run_metadata(run_dir)
        contract_path = self._phase5c_authoritative_contract_path(run_dir)
        import_root = self._phase5c_import_root()
        example_path = self._phase5c_authoritative_example_path()
        run_import_dir = ensure_dir(os.path.join(import_root, filesystem_safe_name(run_meta.get("run_id") or "latest-run", fallback="latest-run")))
        authoritative_dir = ensure_dir(os.path.join(str(run_dir or "").strip(), "authoritative")) if str(run_dir or "").strip() else ""
        example_record = {
            "ts_utc": now_iso_utc(),
            "run_id": run_meta.get("run_id") or "measurement-run-id",
            "scenario_label": "baseline_or_scenario_label",
            "scenario_bucket": "baseline",
            "phase_stage": "runtime",
            "phase_trigger_reason": "authoritative_source_example",
            "source_mode": "emulator-observed",
            "truth_level": "ground-truth",
            "tunnel_id": "example-tunnel-id",
            "tunnel_direction": "inbound",
            "tunnel_kind": "client",
            "hop_chain_names": ["Router 2", "Router 5", "Router 7"],
            "full_hop_chain": ["Router 2", "Router 5", "Router 7"]
        }
        if not os.path.exists(example_path):
            ensure_dir(os.path.dirname(example_path))
            with open(example_path, 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(example_record, ensure_ascii=False, sort_keys=False) + "\n")
        if contract_path:
            contract_payload = {
                "generated_at_utc": now_iso_utc(),
                "run_id": run_meta.get("run_id") or "",
                "run_dir": run_meta.get("run_dir") or str(run_dir or "").strip(),
                "testnet_base": run_meta.get("testnet_base") or "",
                "contract_version": 1,
                "purpose": "Provide a dedicated authoritative exact-hop source for automatic path ingestion.",
                "accepted_paths": [
                    os.path.join(str(run_dir or "").strip(), "authoritative", "authoritative-hop-events.jsonl") if str(run_dir or "").strip() else "",
                    os.path.join(str(run_dir or "").strip(), "authoritative-hop-events.jsonl") if str(run_dir or "").strip() else "",
                    os.path.join(run_import_dir, "authoritative-hop-events.jsonl"),
                    os.path.join(str(run_meta.get("testnet_base") or "").strip(), "authoritative", "authoritative-hop-events.jsonl") if str(run_meta.get("testnet_base") or "").strip() else "",
                ],
                "required_fields": [
                    "run_id",
                    "source_mode",
                    "tunnel_id",
                    "tunnel_direction",
                    "tunnel_kind",
                    "hop_chain_names or full_hop_chain",
                ],
                "source_modes": [
                    "emulator-observed",
                    "log-derived-ground-truth",
                    "operator-entered-ground-truth",
                ],
                "import_root": import_root,
                "run_import_dir": run_import_dir,
                "authoritative_dir": authoritative_dir,
                "example_source_file": example_path,
                "notes": [
                    "Surface-only traces are not authoritative.",
                    "Cached truth must never be re-ingested as a new authoritative source.",
                    "If no authoritative source exists, automatic ingestion must capture zero events.",
                ],
            }
            write_json_atomic(contract_path, contract_payload)
        return {
            "contract_path": contract_path,
            "example_path": example_path,
            "import_root": import_root,
            "run_import_dir": run_import_dir,
            "authoritative_dir": authoritative_dir,
        }

    def _phase5c_source_candidate_files(self, run_dir):
        run_dir = str(run_dir or "").strip()
        if not run_dir or not os.path.isdir(run_dir):
            return []
        contract_info = self._phase5c_write_source_contract(run_dir)
        run_meta = self._phase5c_run_metadata(run_dir)
        testnet_base = str(run_meta.get("testnet_base") or "").strip()
        patterns = (
            "exact-hop-source.json", "exact-hop-source.jsonl",
            "tunnel-build-events.json", "tunnel-build-events.jsonl",
            "router-hop-events.json", "router-hop-events.jsonl",
            "authoritative-hop-events.json", "authoritative-hop-events.jsonl",
            "ground-truth-hop-events.json", "ground-truth-hop-events.jsonl",
            "exact-hop-raw.json", "exact-hop-raw.jsonl",
            "exact-hop-truth.json", "exact-hop-truth.jsonl",
            "hop_truth.json", "hop_truth.jsonl",
        )
        search_roots = [run_dir]
        authoritative_dir = str(contract_info.get("authoritative_dir") or "").strip()
        if authoritative_dir and os.path.isdir(authoritative_dir):
            search_roots.append(authoritative_dir)
        run_import_dir = str(contract_info.get("run_import_dir") or "").strip()
        if run_import_dir and os.path.isdir(run_import_dir):
            search_roots.append(run_import_dir)
        import_root = str(contract_info.get("import_root") or "").strip()
        if import_root and os.path.isdir(import_root):
            search_roots.append(import_root)
        if testnet_base and os.path.isdir(testnet_base):
            testnet_authoritative = os.path.join(testnet_base, "authoritative")
            if os.path.isdir(testnet_authoritative):
                search_roots.append(testnet_authoritative)
        found = []
        seen = set()
        for root in search_roots:
            for name in patterns:
                for path in glob.glob(os.path.join(root, "**", name), recursive=True):
                    norm = os.path.normpath(path)
                    if os.path.isfile(norm) and norm not in seen:
                        seen.add(norm)
                        found.append(norm)
        found.sort(key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0.0, reverse=True)
        return found

    def _phase5c_authoritative_source_rows(self, run_dir):
        rows = []
        files = self._phase5c_source_candidate_files(run_dir)
        for path in files:
            for item in self._phase5b_parse_truth_file(path):
                if not isinstance(item, dict):
                    continue
                norm = dict(item)
                norm["_source_file"] = path
                rows.append(norm)
        return files, rows

    def _phase5c_generated_source_path(self, run_dir):
        run_dir = str(run_dir or "").strip()
        return os.path.join(run_dir, "authoritative-hop-events.jsonl") if run_dir else ""

    def _phase5c_run_metadata(self, run_dir):
        run_dir = str(run_dir or "").strip()
        run_meta = read_json_file(os.path.join(run_dir, "run.json"), default={}) or {}
        state_meta = read_json_file(os.path.join(run_dir, "state.json"), default={}) or {}
        return {
            "run_id": str(run_meta.get("run_id") or os.path.basename(run_dir) or "").strip(),
            "run_dir": run_dir,
            "testnet_base": str(run_meta.get("testnet_base") or state_meta.get("testnet_base") or "").strip(),
        }

    def _phase5c_log_candidate_files(self, run_dir, limit_files=24):
        meta = self._phase5c_run_metadata(run_dir)
        base = str(meta.get("testnet_base") or "").strip()
        if not base or not os.path.isdir(base):
            return []
        files = []
        seen = set()
        for entry in sorted(os.listdir(base)):
            if not re.fullmatch(r"r\d+", entry):
                continue
            router_id = entry[1:]
            router_dir = os.path.join(base, entry)
            candidates = [
                find_best_log(router_dir, router_id),
                os.path.join(router_dir, "logs", "eventlog.txt"),
                os.path.join(router_dir, "logs", "wrapper.log"),
                os.path.join(router_dir, "logs", "router.log"),
                os.path.join(router_dir, "wrapper.log"),
                os.path.join(router_dir, "stdout.log"),
                os.path.join(router_dir, "bootstrap.log"),
            ]
            try:
                candidates.extend(sorted(glob.glob(os.path.join(router_dir, "logs", "*.jsonl"))))
                candidates.extend(sorted(glob.glob(os.path.join(router_dir, "logs", "*.json"))))
                candidates.extend(sorted(glob.glob(os.path.join(router_dir, "logs", "*.log"))))
            except Exception:
                pass
            for candidate in candidates:
                if not candidate:
                    continue
                norm = os.path.normpath(candidate)
                if os.path.isfile(norm) and norm not in seen:
                    seen.add(norm)
                    files.append(norm)
        files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0.0, reverse=True)
        return files[:max(1, int(limit_files or 1))]

    def _phase5c_parse_authoritative_chain_from_text(self, text):
        blob = str(text or "").strip()
        if not blob:
            return []
        match = PHASE5C_AUTHORITATIVE_CHAIN_TEXT_RE.search(blob)
        if not match:
            return []
        chain_blob = str(match.group(1) or "").strip()
        if not chain_blob:
            return []
        chain_blob = chain_blob.strip().strip("[](){}")
        chain_blob = chain_blob.replace('"', '').replace("'", "")
        chain_blob = re.sub(r"\s*(?:->|=>|>)\s*", ",", chain_blob)
        chain_blob = re.sub(r"\brouter\s*#?(\d+)\b", r"Router \1", chain_blob, flags=re.IGNORECASE)
        return phase5b_parse_hop_chain(chain_blob)

    def _phase5c_parse_authoritative_log_line(self, line, run_meta, source_path):
        text = str(line or "").strip()
        if not text:
            return None
        if text.startswith("{") and text.endswith("}"):
            try:
                payload = json.loads(text)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                chain, _ = self._phase5c_extract_authoritative_chain(payload)
                if chain:
                    record = dict(payload)
                    record.setdefault("run_id", run_meta.get("run_id") or os.path.basename(str(run_meta.get("run_dir") or "")))
                    record.setdefault("source_mode", "log-derived-ground-truth")
                    record.setdefault("phase_trigger_reason", "phase5c_log_scan")
                    record.setdefault("phase_stage", "runtime")
                    record.setdefault("_source_file", source_path)
                    return record
        chain = self._phase5c_parse_authoritative_chain_from_text(text)
        if len(chain) < 2:
            return None
        ts_match = PHASE5C_LOG_TIMESTAMP_RE.search(text)
        ts_value = ts_match.group(1) if ts_match else now_iso_utc()
        tunnel_match = PHASE5C_TUNNEL_ID_RE.search(text)
        direction_match = PHASE5C_DIRECTION_RE.search(text)
        kind_match = PHASE5C_KIND_RE.search(text)
        tunnel_id = tunnel_match.group(1) if tunnel_match else ""
        if not tunnel_id:
            sig = hashlib.sha1((str(source_path) + "|" + ts_value + "|" + phase5c_chain_signature(chain)).encode("utf-8", errors="ignore")).hexdigest()[:12]
            tunnel_id = f"logscan-{sig}"
        return {
            "ts_utc": ts_value,
            "run_id": run_meta.get("run_id") or os.path.basename(str(run_meta.get("run_dir") or "")),
            "scenario_label": "",
            "scenario_bucket": "other",
            "phase_stage": "runtime",
            "phase_trigger_reason": "phase5c_log_scan",
            "source_mode": "log-derived-ground-truth",
            "truth_level": "ground-truth",
            "tunnel_id": tunnel_id,
            "tunnel_direction": direction_match.group(1).lower() if direction_match else "unknown",
            "tunnel_kind": kind_match.group(1).lower() if kind_match else "unknown",
            "hop_chain_names": chain,
            "full_hop_chain": chain,
            "_source_file": source_path,
            "raw_line": text,
        }

    def _phase5c_collect_log_derived_source_records(self, run_dir, max_files=24, tail_lines=1200):
        run_meta = self._phase5c_run_metadata(run_dir)
        files = self._phase5c_log_candidate_files(run_dir, limit_files=max_files)
        records = []
        seen = set()
        log_lines_scanned = 0
        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    lines = handle.readlines()
            except Exception:
                continue
            tail = lines[-max(1, int(tail_lines or 1)):]
            log_lines_scanned += len(tail)
            for raw_line in tail:
                record = self._phase5c_parse_authoritative_log_line(raw_line, run_meta, path)
                if not isinstance(record, dict):
                    continue
                chain, _ = self._phase5c_extract_authoritative_chain(record)
                if len(chain) < 2:
                    chain = phase5b_parse_hop_chain(record.get("hop_chain_names") or record.get("full_hop_chain") or [])
                if len(chain) < 2:
                    continue
                key = (
                    str(record.get("run_id") or run_meta.get("run_id") or ""),
                    str(record.get("tunnel_id") or ""),
                    str(record.get("ts_utc") or record.get("timestamp") or ""),
                    phase5c_chain_signature(chain),
                    str(path),
                )
                if key in seen:
                    continue
                seen.add(key)
                record["hop_chain_names"] = list(chain)
                record["full_hop_chain"] = list(chain)
                record.setdefault("run_id", run_meta.get("run_id") or os.path.basename(str(run_meta.get("run_dir") or "")))
                record.setdefault("source_mode", "log-derived-ground-truth")
                record.setdefault("phase_trigger_reason", "phase5c_log_scan")
                record.setdefault("phase_stage", "runtime")
                records.append(record)
        return {
            "run_meta": run_meta,
            "log_files_scanned": len(files),
            "log_lines_scanned": log_lines_scanned,
            "records": records,
        }

    def _phase5c_materialize_log_derived_source(self, run_dir):
        result = self._phase5c_collect_log_derived_source_records(run_dir)
        output_path = self._phase5c_generated_source_path(run_dir)
        records = list(result.get("records") or [])
        if records:
            ensure_dir(os.path.dirname(output_path))
            with open(output_path, "w", encoding="utf-8") as handle:
                for rec in records:
                    handle.write(json.dumps(rec, ensure_ascii=False, sort_keys=False) + "\n")
        else:
            try:
                if output_path and os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass
        return {
            "generated_source_path": output_path if records else "",
            "record_count": len(records),
            "log_files_scanned": int(result.get("log_files_scanned") or 0),
            "log_lines_scanned": int(result.get("log_lines_scanned") or 0),
        }

    def _phase5c_auto_extract_payload(self, run_dir=None):
        state = self._phase5c_load_state()
        latest = {"run_dir": run_dir} if run_dir else None
        if latest is None:
            runs = self._measurement_list_recent_runs(limit=1)
            latest = runs[0] if runs else None
        if not latest:
            payload = dict(state)
            payload.update({
                "source_example_path": self._phase5c_authoritative_example_path(),
                "source_import_root": self._phase5c_import_root(),
            })
            payload["last_result"] = "No measurement run is available for automatic path ingestion."
            return payload

        run_dir = latest.get("run_dir") or run_dir or ""
        trace_path = os.path.join(run_dir, "trace.jsonl")
        trace_rows = read_jsonl_records(trace_path, limit=2000) if os.path.isfile(trace_path) else []
        log_materialized = self._phase5c_materialize_log_derived_source(run_dir)
        contract_info = self._phase5c_write_source_contract(run_dir)
        source_files, source_rows = self._phase5c_authoritative_source_rows(run_dir)

        seen = set(state.get("seen_keys") or [])
        raw_output_path = self._phase5b_capture_raw_output_path()
        source_fields = []
        captured_from_traces = 0
        captured_from_files = 0
        duplicates = 0
        without_chain = 0
        source_records_scanned = 0
        run_id_fallback = os.path.basename(run_dir) if run_dir else ""

        def _append_capture(raw, chain, source_mode, source_field, source_path=None):
            nonlocal duplicates, captured_from_traces, captured_from_files
            run_id = str(raw.get("run_id") or run_id_fallback or "").strip()
            context = self._phase5c_context_from_run_id(run_id, raw)
            ts_value = str(raw.get("ts_utc") or raw.get("ts_local") or raw.get("timestamp") or now_iso_utc())
            tunnel_id = str(raw.get("tunnel_id") or raw.get("id") or raw.get("trace_id") or raw.get("path_id") or "").strip()
            if not tunnel_id:
                tunnel_id = f"phase5c-{filesystem_safe_name(run_id or 'run')}-{hashlib.sha1((ts_value + '|' + phase5c_chain_signature(chain)).encode('utf-8')).hexdigest()[:12]}"
            dedupe_key = "|".join([run_id, tunnel_id, ts_value, phase5c_chain_signature(chain), str(source_mode)])
            if dedupe_key in seen:
                duplicates += 1
                return
            record = phase5b_build_raw_capture_record(
                run_id=run_id,
                scenario_bucket=context.get("scenario_bucket"),
                scenario_label=context.get("scenario_label"),
                tunnel_id=tunnel_id,
                tunnel_direction=str(raw.get("tunnel_direction") or raw.get("direction") or "unknown"),
                tunnel_kind=str(raw.get("tunnel_kind") or raw.get("kind") or raw.get("tunnel_type") or "unknown"),
                hop_chain=chain,
                source_mode=source_mode,
                phase_stage=context.get("phase_stage"),
                phase_trigger_reason=context.get("phase_trigger_reason"),
                previous_chain=raw.get("previous_hop_chain") or [],
                metadata={
                    "phase5c_auto": True,
                    "source_field": source_field,
                    "trace_signature": ((raw.get("trace") or raw.get("tunnel_trace") or {}) or {}).get("signature"),
                    "source_path": source_path or trace_path,
                    "trace_router_id": raw.get("router_id"),
                    "trace_router_name": raw.get("router_name"),
                },
                ts_utc=ts_value,
            )
            append_jsonl(raw_output_path, record)
            seen.add(dedupe_key)
            if source_path:
                captured_from_files += 1
            else:
                captured_from_traces += 1

        for row in trace_rows:
            if not isinstance(row, dict):
                continue
            chain, source_field = self._phase5c_extract_authoritative_chain(row)
            if len(chain) < 2:
                without_chain += 1
                continue
            if not self._phase5c_is_runtime_authoritative_row(row, source_field=source_field):
                without_chain += 1
                continue
            if source_field:
                source_fields.append(source_field)
            source_mode = str(
                row.get("exact_truth_source")
                or row.get("truth_source")
                or (row.get("metadata") or {}).get("truth_source")
                or (row.get("metadata") or {}).get("source_mode")
                or "emulator-observed"
            ).strip() or "emulator-observed"
            _append_capture(row, chain, source_mode=source_mode, source_field=source_field, source_path=None)

        for row in source_rows:
            if not isinstance(row, dict):
                continue
            source_records_scanned += 1
            chain, source_field = self._phase5c_extract_authoritative_chain(row)
            if len(chain) < 2:
                chain_list = self._phase5b_extract_hop_chain(row)
                chain = [phase5b_normalize_router_name(item.get("router_name") or (f"Router {item.get('router_id')}" if item.get("router_id") else "")) for item in chain_list if (item.get("router_name") or item.get("router_id"))]
                source_field = source_field or "authoritative_file"
            chain = [name for name in phase5b_parse_hop_chain(chain) if name]
            if len(chain) < 2:
                continue
            if source_field:
                source_fields.append(source_field)
            source_mode = str(row.get("source_mode") or row.get("truth_source") or "log-derived-ground-truth").strip() or "log-derived-ground-truth"
            _append_capture(row, chain, source_mode=source_mode, source_field=source_field or "authoritative_file", source_path=row.get("_source_file"))

        source_fields = list(dict.fromkeys(source_fields))
        total_captured = captured_from_traces + captured_from_files
        payload = dict(state)
        payload.update({
            "auto_mode": "enabled" if self._phase5c_enabled() else "disabled",
            "source_contract_path": str(contract_info.get("contract_path") or ""),
            "source_example_path": str(contract_info.get("example_path") or ""),
            "source_import_root": str(contract_info.get("import_root") or ""),
            "source_run_import_dir": str(contract_info.get("run_import_dir") or ""),
            "source_authoritative_dir": str(contract_info.get("authoritative_dir") or ""),
            "runs_scanned": int(state.get("runs_scanned") or 0) + (1 if (trace_rows or source_rows or int(log_materialized.get("log_files_scanned") or 0) > 0) else 0),
            "trace_rows_scanned": int(state.get("trace_rows_scanned") or 0) + len(trace_rows),
            "source_files_scanned": int(state.get("source_files_scanned") or 0) + len(source_files),
            "source_records_scanned": int(state.get("source_records_scanned") or 0) + source_records_scanned,
            "trace_events_captured": int(state.get("trace_events_captured") or 0) + captured_from_traces,
            "source_file_events_captured": int(state.get("source_file_events_captured") or 0) + captured_from_files,
            "auto_events_captured": int(state.get("auto_events_captured") or 0) + total_captured,
            "duplicate_rows_skipped": int(state.get("duplicate_rows_skipped") or 0) + duplicates,
            "rows_without_authoritative_chain": int(state.get("rows_without_authoritative_chain") or 0) + without_chain,
            "log_files_scanned": int(state.get("log_files_scanned") or 0) + int(log_materialized.get("log_files_scanned") or 0),
            "log_lines_scanned": int(state.get("log_lines_scanned") or 0) + int(log_materialized.get("log_lines_scanned") or 0),
            "log_source_events_materialized": int(state.get("log_source_events_materialized") or 0) + int(log_materialized.get("record_count") or 0),
            "last_generated_source_path": str(log_materialized.get("generated_source_path") or ""),
            "latest_run_id": run_id_fallback,
            "latest_run_dir": run_dir,
            "latest_source_fields": source_fields,
            "last_raw_output_path": raw_output_path,
            "seen_keys": list(seen)[-5000:],
        })
        if total_captured:
            parts = []
            if captured_from_traces:
                parts.append(f"{captured_from_traces} from measurement traces")
            if captured_from_files:
                parts.append(f"{captured_from_files} from authoritative source files")
            payload["last_result"] = f"Captured {total_captured} automatic exact-hop raw event(s) in {run_id_fallback} ({'; '.join(parts)})."
        elif (trace_rows or source_rows) and duplicates:
            payload["last_result"] = (
                f"No new automatic exact-hop events were captured for {run_id_fallback}; "
                f"{duplicates} candidate row(s) matched already-recorded authoritative chains."
            )
        elif trace_rows or source_rows or int(log_materialized.get("log_files_scanned") or 0) > 0:
            payload["last_result"] = "Scanned the latest measurement data, authoritative source files, and router/runtime logs, but found no new explicit authoritative hop-chain records to ingest."
        else:
            payload["last_result"] = "No trace rows, authoritative source files, or router/runtime logs were available for automatic path ingestion."
        return payload
    def run_phase5c_auto_extract_latest_measurement(self, notify=True, run_dir=None, trigger_source="manual-scan"):
        prior_state = self._phase5c_load_state()
        prior_total = int(prior_state.get("auto_events_captured") or 0)
        scan_started_local = now_display()
        payload = self._phase5c_auto_extract_payload(run_dir=run_dir)
        current_total = int(payload.get("auto_events_captured") or 0)
        new_events_captured = max(0, current_total - prior_total)
        payload.update({
            "last_scan_trigger": str(trigger_source or "manual-scan"),
            "last_scan_started_local": scan_started_local,
            "last_scan_finished_local": now_display(),
        })

        normalization_result = None
        if new_events_captured > 0:
            normalization_result = self.run_phase5b_exact_hop_producer(notify=False, reason="auto-after-ingestion")
            payload.update({
                "last_normalization_started_local": normalization_result.get("started_at_local") or scan_started_local,
                "last_normalization_finished_local": normalization_result.get("finished_at_local") or now_display(),
                "last_normalization_result": normalization_result.get("result_text") or "Normalization completed.",
                "last_normalized_event_count": normalization_result.get("normalized_event_count") or 0,
                "last_normalization_manifest_path": normalization_result.get("manifest_path") or "",
                "last_normalization_jsonl_path": normalization_result.get("jsonl_path") or "",
            })
            payload["last_result"] = (
                f"{payload.get('last_result')} Normalization refreshed the canonical ground-truth dataset automatically."
            ).strip()
        elif not prior_state.get("last_normalization_result"):
            payload["last_normalization_result"] = "Normalization has not run yet."

        saved_state = self._phase5c_save_state(**payload)
        self.update_measurement_panel()
        self.append_measurement_log(f"[{now_display()}] {saved_state.get('last_result')}")
        if normalization_result:
            self.append_measurement_log(f"[{now_display()}] {saved_state.get('last_normalization_result')}")
        if notify:
            QMessageBox.information(self, APP_NAME, self._build_phase5c_status_text(saved_state))
        return saved_state

    def _build_phase5c_status_text(self, payload=None):
        payload = payload if payload is not None else self._phase5c_load_state()
        lines = ["Automatic path ingestion", "=" * 72]
        lines.append(format_kv("Generated at", payload.get("generated_at_local")))
        lines.append(format_kv("Auto mode", payload.get("auto_mode")))
        lines.append(format_kv("Last scan trigger", payload.get("last_scan_trigger") or "none"))
        lines.append(format_kv("Last scan started", payload.get("last_scan_started_local") or "n/a"))
        lines.append(format_kv("Last scan finished", payload.get("last_scan_finished_local") or "n/a"))
        lines.append(format_kv("Runs scanned", payload.get("runs_scanned", 0)))
        lines.append(format_kv("Trace rows scanned", payload.get("trace_rows_scanned", 0)))
        lines.append(format_kv("Source files scanned", payload.get("source_files_scanned", 0)))
        lines.append(format_kv("Source rows scanned", payload.get("source_records_scanned", 0)))
        lines.append(format_kv("Router logs scanned", payload.get("log_files_scanned", 0)))
        lines.append(format_kv("Log lines scanned", payload.get("log_lines_scanned", 0)))
        lines.append(format_kv("Log events materialized", payload.get("log_source_events_materialized", 0)))
        lines.append(format_kv("Events from traces", payload.get("trace_events_captured", 0)))
        lines.append(format_kv("Events from files", payload.get("source_file_events_captured", 0)))
        lines.append(format_kv("Total events captured", payload.get("auto_events_captured", 0)))
        lines.append(format_kv("Duplicates skipped", payload.get("duplicate_rows_skipped", 0)))
        lines.append(format_kv("Rows without chain", payload.get("rows_without_authoritative_chain", 0)))
        lines.append(format_kv("Latest run id", payload.get("latest_run_id") or "n/a"))
        lines.append(format_kv("Latest source fields", ", ".join(payload.get("latest_source_fields") or []) or "none"))
        lines.append(format_kv("Raw output path", payload.get("last_raw_output_path") or self._phase5b_capture_raw_output_path()))
        lines.append(format_kv("Generated source file", payload.get("last_generated_source_path") or "n/a"))
        lines.append(format_kv("Source contract", payload.get("source_contract_path") or "n/a"))
        lines.append(format_kv("Example source file", payload.get("source_example_path") or "n/a"))
        lines.append(format_kv("Import root", payload.get("source_import_root") or "n/a"))
        lines.append(format_kv("Run import dir", payload.get("source_run_import_dir") or "n/a"))
        lines.append(format_kv("Authoritative dir", payload.get("source_authoritative_dir") or "n/a"))
        lines.append(format_kv("Last normalization", payload.get("last_normalization_finished_local") or "n/a"))
        lines.append(format_kv("Normalized events", payload.get("last_normalized_event_count", 0)))
        lines.append(format_kv("Normalization JSONL", payload.get("last_normalization_jsonl_path") or "n/a"))
        lines.append(format_kv("Normalization manifest", payload.get("last_normalization_manifest_path") or "n/a"))
        lines.extend([
            "",
            "Notes",
            "-----",
            "Automatic path ingestion accepts two authoritative inputs: explicit hop-chain fields in measurement data, and emulator-observed or log-derived source files placed in the run directory.",
            "Step 6 scans real router/runtime logs for explicit chain markers and materializes any matching authoritative records into a run-local source file before ingestion runs.",
            "Step 7 publishes a dedicated authoritative source contract and import locations so emulator-controlled build output can write exact-hop manifests in a stable format.",
            "Surface-only tunnel traces remain non-authoritative. Cached truth is never re-ingested as a new authoritative source.",
            "When new authoritative records are captured, normalization now runs automatically so the canonical ground-truth dataset stays current for Path Analysis.",
            "",
            "Last result",
            "-----------",
            str(payload.get("last_result") or "n/a"),
            "",
            "Last normalization result",
            "-------------------------",
            str(payload.get("last_normalization_result") or "n/a"),
        ])
        return "\n".join(lines)


    def _phase5b_capture_raw_output_path(self):
        root = os.path.join(HOP_TRUTH_ROOT_DIR, "raw")
        ensure_dir(root)
        return os.path.join(root, "exact-hop-source.jsonl")

    def _phase5b_capture_recent_rows(self, limit=20):
        return read_jsonl_records(self._phase5b_capture_raw_output_path(), limit=limit)

    def _phase5b_capture_context_defaults(self):
        latest_campaign = None
        try:
            rows = self._experiment_recent_rows(limit=20)
            latest_campaign = rows[0] if rows else None
        except Exception:
            latest_campaign = None
        run_id = ""
        scenario_label = ""
        scenario_bucket = "other"
        phase_stage = "runtime"
        phase_trigger = "manual_gui_capture"
        if latest_campaign:
            run_id = str(latest_campaign.get("final_run_id") or latest_campaign.get("baseline_run_id") or latest_campaign.get("campaign_run_id") or "")
            scenario_label = str(latest_campaign.get("experiment_label") or "")
            scenario_type = str(latest_campaign.get("scenario_type") or "").strip().lower()
            label_l = scenario_label.lower()
            if "baseline" in label_l or scenario_type == "baseline":
                scenario_bucket = "baseline"
            elif "adversarial" in label_l:
                scenario_bucket = "adversarial_floodfill"
            elif "floodfill" in label_l:
                scenario_bucket = "floodfill_targeted"
            elif "high" in label_l:
                scenario_bucket = "high_churn"
            elif "moderate" in label_l:
                scenario_bucket = "moderate_churn"
            elif scenario_type:
                scenario_bucket = scenario_type
            phase_stage = str(latest_campaign.get("phase_stage") or phase_stage)
            phase_trigger = str(latest_campaign.get("phase_trigger_reason") or phase_trigger)
        if not run_id:
            run_id = f"{filesystem_safe_name(os.path.basename(find_testnet_base() or 'testnet'))}-manual-{now_display().replace(':','-').replace(' ','_')}"
        selected_router = self.find_router(self.selected_router_id) if getattr(self, "selected_router_id", None) else None
        selected_name = selected_router.get("name") if selected_router else ""
        return {
            "run_id": run_id,
            "scenario_label": scenario_label,
            "scenario_bucket": scenario_bucket,
            "phase_stage": phase_stage,
            "phase_trigger_reason": phase_trigger,
            "selected_router_name": selected_name,
        }

    def autofill_phase5b_capture_form(self):
        defaults = self._phase5b_capture_context_defaults()
        self.phase5b_capture_run_id.setText(defaults.get("run_id", ""))
        self.phase5b_capture_scenario_label.setText(defaults.get("scenario_label", ""))
        self.phase5b_capture_scenario_bucket.setEditText(defaults.get("scenario_bucket", "other"))
        if not self.phase5b_capture_tunnel_id.text().strip():
            rid = str(getattr(self, "selected_router_id", "") or "").strip()
            suffix = rid or "manual"
            self.phase5b_capture_tunnel_id.setText(f"exact-hop-{suffix}-{int(time.time())}")
        if not self.phase5b_capture_phase_stage.text().strip():
            self.phase5b_capture_phase_stage.setText(defaults.get("phase_stage", "runtime"))
        if not self.phase5b_capture_phase_trigger.text().strip():
            self.phase5b_capture_phase_trigger.setText(defaults.get("phase_trigger_reason", "manual_gui_capture"))
        if not self.phase5b_capture_hop_chain.text().strip() and defaults.get("selected_router_name"):
            self.phase5b_capture_hop_chain.setText(defaults.get("selected_router_name"))
        if not self.phase5b_capture_scenario_label.text().strip():
            bucket_text = self.phase5b_capture_scenario_bucket.currentText().strip() or "other"
            self.phase5b_capture_scenario_label.setText(f"{bucket_text}_manual_truth")
        self.update_measurement_panel()

    def clear_phase5b_capture_form(self):
        self.phase5b_capture_run_id.clear()
        self.phase5b_capture_scenario_label.clear()
        self.phase5b_capture_scenario_bucket.setEditText("other")
        self.phase5b_capture_tunnel_id.clear()
        self.phase5b_capture_tunnel_direction.setCurrentIndex(0)
        self.phase5b_capture_tunnel_kind.setEditText("unknown")
        self.phase5b_capture_hop_chain.clear()
        self.phase5b_capture_previous_chain.clear()
        self.phase5b_capture_phase_stage.clear()
        self.phase5b_capture_phase_trigger.clear()
        self.phase5b_capture_source_mode.setEditText("operator-entered-ground-truth")
        self.update_measurement_panel()

    def _phase5b_capture_form_payload(self):
        return {
            "run_id": self.phase5b_capture_run_id.text().strip(),
            "scenario_label": self.phase5b_capture_scenario_label.text().strip(),
            "scenario_bucket": self.phase5b_capture_scenario_bucket.currentText().strip() or "other",
            "tunnel_id": self.phase5b_capture_tunnel_id.text().strip(),
            "tunnel_direction": self.phase5b_capture_tunnel_direction.currentText().strip() or "unknown",
            "tunnel_kind": self.phase5b_capture_tunnel_kind.currentText().strip() or "unknown",
            "hop_chain": phase5b_parse_hop_chain(self.phase5b_capture_hop_chain.text()),
            "previous_chain": phase5b_parse_hop_chain(self.phase5b_capture_previous_chain.text()),
            "phase_stage": self.phase5b_capture_phase_stage.text().strip() or "runtime",
            "phase_trigger_reason": self.phase5b_capture_phase_trigger.text().strip() or "manual_gui_capture",
            "source_mode": self.phase5b_capture_source_mode.currentText().strip() or "operator-entered-ground-truth",
            "raw_output_path": self._phase5b_capture_raw_output_path(),
        }

    def _build_phase5b_capture_text(self):
        payload = self._phase5b_capture_form_payload()
        rows = self._phase5b_capture_recent_rows(limit=20)
        lines = ["Manual path entry", "=" * 72]
        lines.append(format_kv("Generated at", now_display()))
        lines.append(format_kv("Raw output path", payload.get("raw_output_path")))
        lines.append(format_kv("Form run id", payload.get("run_id") or "n/a"))
        lines.append(format_kv("Scenario label", payload.get("scenario_label") or "n/a"))
        lines.append(format_kv("Scenario bucket", payload.get("scenario_bucket") or "n/a"))
        lines.append(format_kv("Tunnel id", payload.get("tunnel_id") or "n/a"))
        lines.append(format_kv("Direction / kind", f"{payload.get('tunnel_direction')} / {payload.get('tunnel_kind')}"))
        lines.append(format_kv("Hop chain", ", ".join(payload.get("hop_chain") or []) or "n/a"))
        lines.append(format_kv("Previous chain", ", ".join(payload.get("previous_chain") or []) or "n/a"))
        lines.append(format_kv("Phase / trigger", f"{payload.get('phase_stage')} / {payload.get('phase_trigger_reason')}"))
        lines.append(format_kv("Source mode", payload.get("source_mode") or "n/a"))
        lines.extend(["", "Recent raw events", "-" * 17])
        if not rows:
            lines.append("No raw exact-hop events have been recorded yet from inside the emulator.")
        else:
            for row in reversed(rows[-8:]):
                chain = ", ".join(row.get("hop_chain") or []) or "n/a"
                lines.append(f"[{row.get('ts_utc', 'unknown')}] {row.get('run_id', 'unknown')} | {row.get('tunnel_id', 'unknown')} | {row.get('tunnel_direction', 'unknown')} / {row.get('tunnel_kind', 'unknown')} | {chain}")
        lines.extend(["", "Notes", "-" * 5, "This section writes authoritative raw hop-chain events directly into the manual path-entry store.", "It does not infer hop order from visible tunnel/lease surfaces; it records exactly what you enter here."])
        return "\n".join(lines)

    
    def _phase5b_apply_capture_defaults(self, payload):
        payload = dict(payload or {})
        bucket = str(payload.get("scenario_bucket") or "").strip() or "other"
        label = str(payload.get("scenario_label") or "").strip()
        if not label:
            payload["scenario_label"] = f"{bucket}_manual_truth"
        if not str(payload.get("phase_stage") or "").strip():
            payload["phase_stage"] = "runtime"
        if not str(payload.get("phase_trigger_reason") or "").strip():
            payload["phase_trigger_reason"] = "manual_gui_capture"
        if not str(payload.get("source_mode") or "").strip():
            payload["source_mode"] = "operator-entered-ground-truth"
        return payload

    def record_phase5b_exact_hop_event_from_ui(self, notify=True):
        payload = self._phase5b_apply_capture_defaults(self._phase5b_capture_form_payload())
        missing = []
        if not payload.get("run_id"):
            missing.append("Run ID")
        if not payload.get("scenario_label"):
            missing.append("Scenario label")
        if not payload.get("tunnel_id"):
            missing.append("Tunnel ID")
        if not payload.get("hop_chain"):
            missing.append("Hop chain")
        if missing:
            QMessageBox.critical(self, APP_NAME, "Please fill the required exact-hop capture fields:\n- " + "\n- ".join(missing))
            return False
        record = phase5b_build_raw_capture_record(
            run_id=payload.get("run_id"),
            scenario_bucket=payload.get("scenario_bucket"),
            scenario_label=payload.get("scenario_label"),
            tunnel_id=payload.get("tunnel_id"),
            tunnel_direction=payload.get("tunnel_direction"),
            tunnel_kind=payload.get("tunnel_kind"),
            hop_chain=payload.get("hop_chain"),
            source_mode=payload.get("source_mode"),
            phase_stage=payload.get("phase_stage"),
            phase_trigger_reason=payload.get("phase_trigger_reason"),
            previous_chain=payload.get("previous_chain"),
            metadata={"captured_via": "phase5b_gui_button"},
        )
        append_jsonl(payload.get("raw_output_path"), record)
        self.deploy_status.setText(f"Manual path record written to: {payload.get('raw_output_path')}")
        self.append_measurement_log(f"[{now_display()}] Manual path record written to: {payload.get('raw_output_path')}")
        self.update_measurement_panel()
        if notify:
            QMessageBox.information(self, APP_NAME, f"Exact-hop raw event recorded to:\n{payload.get('raw_output_path')}\n\nRun the path record processor next to normalize it into canonical ground truth.")
        return True

    def auto_record_phase5b_exact_hop_event_from_ui(self):
        ok = self.record_phase5b_exact_hop_event_from_ui(notify=False)
        if not ok:
            return
        self.run_phase5b_exact_hop_producer(notify=False)
        self.update_measurement_panel()
        payload = self._phase5b_hop_truth_payload()
        QMessageBox.information(
            self,
            APP_NAME,
            "Path record pipeline completed.\n\n"
            f"Exact events: {payload.get('event_count', 0)}\n"
            f"Tunnels tracked: {payload.get('tunnel_count', 0)}\n"
            f"Routers tracked: {payload.get('router_count', 0)}"
        )

    def _phase5b_producer_raw_root(self):
        path = os.path.join(HOP_TRUTH_ROOT_DIR, "raw")
        ensure_dir(path)
        return path

    def _phase5b_producer_output_paths(self):
        ensure_dir(HOP_TRUTH_ROOT_DIR)
        ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, "events"))
        ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, "summaries"))
        base = filesystem_safe_name(os.path.basename(find_testnet_base() or "testnet"))
        return {
            "jsonl": os.path.join(HOP_TRUTH_ROOT_DIR, "events", "exact-hop-truth.jsonl"),
            "json": os.path.join(HOP_TRUTH_ROOT_DIR, "events", "exact-hop-truth.json"),
            "manifest": os.path.join(HOP_TRUTH_ROOT_DIR, "summaries", f"{base}-phase5b-producer-manifest.json"),
        }

    def _phase5b_producer_candidate_files(self, limit_files=240):
        files = []
        seen = set()
        patterns = (
            "exact-hop-source.json",
            "exact-hop-source.jsonl",
            "tunnel-build-events.json",
            "tunnel-build-events.jsonl",
            "router-hop-events.json",
            "router-hop-events.jsonl",
            "authoritative-hop-events.json",
            "authoritative-hop-events.jsonl",
            "ground-truth-hop-events.json",
            "ground-truth-hop-events.jsonl",
            "exact-hop-raw.json",
            "exact-hop-raw.jsonl",
        )
        roots = [
            self._phase5b_producer_raw_root(),
            os.path.join(HOP_TRUTH_ROOT_DIR, "imports"),
        ]
        for root in roots:
            if not os.path.isdir(root):
                continue
            for name in patterns:
                for path in glob.glob(os.path.join(root, "**", name), recursive=True):
                    norm = os.path.normpath(path)
                    if norm not in seen:
                        seen.add(norm)
                        files.append(norm)
        for run_dir in list_recent_run_dirs(CAMPAIGN_ROOT_DIR, limit=200):
            for name in patterns:
                path = os.path.join(run_dir, name)
                if os.path.isfile(path):
                    norm = os.path.normpath(path)
                    if norm not in seen:
                        seen.add(norm)
                        files.append(norm)
        files.sort(key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0.0, reverse=True)
        return files[:limit_files]

    def _phase5b_producer_parse_raw_file(self, path):
        return self._phase5b_parse_truth_file(path)

    def _phase5b_producer_normalize_records(self, raw_records):
        normalized = []
        seen = set()
        for raw in raw_records:
            if not isinstance(raw, dict):
                continue
            chain = self._phase5b_extract_hop_chain(raw)
            if not chain:
                continue
            hop_count = len(chain)
            tunnel_id = str(raw.get("tunnel_id") or raw.get("id") or raw.get("trace_id") or raw.get("path_id") or "").strip()
            if not tunnel_id:
                base = json.dumps(raw, sort_keys=True, default=str)
                tunnel_id = "producer-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
            ts_utc = raw.get("ts_utc") or raw.get("timestamp_utc") or raw.get("timestamp") or raw.get("ts")
            ts_local = raw.get("ts_local") or raw.get("timestamp_local") or ts_utc
            run_id = str(raw.get("run_id") or raw.get("campaign_run_id") or raw.get("measurement_run_id") or "").strip()
            scenario_bucket = str(raw.get("scenario_bucket") or raw.get("scenario") or raw.get("bucket") or "").strip()
            scenario_label = str(raw.get("scenario_label") or raw.get("phase_label") or scenario_bucket or "").strip()
            phase_stage = str(raw.get("phase_stage") or raw.get("stage") or "").strip()
            phase_trigger_reason = str(raw.get("phase_trigger_reason") or raw.get("trigger") or "").strip()
            tunnel_direction = str(raw.get("tunnel_direction") or raw.get("direction") or "").strip() or "unknown"
            tunnel_kind = str(raw.get("tunnel_kind") or raw.get("kind") or raw.get("tunnel_type") or "").strip() or "unknown"
            source_mode = str(raw.get("source_mode") or raw.get("truth_source") or "").strip() or "emulator-observed"
            truth_level = str(raw.get("truth_level") or "ground-truth").strip() or "ground-truth"
            chain_names = [phase5b_normalize_router_name(item.get("router_name") or f"Router {item.get('router_id')}") for item in chain]
            chain_ids = [str(item.get("router_id") or "") for item in chain]
            for idx, item in enumerate(chain, start=1):
                rid = str(item.get("router_id") or "").strip()
                rname = phase5b_normalize_router_name(item.get("router_name") or (f"Router {rid}" if rid else ""))
                if not rid and not rname:
                    continue
                prev_name = chain_names[idx - 2] if idx > 1 else ""
                next_name = chain_names[idx] if idx < hop_count else ""
                neighbor_names = [name for name in (prev_name, next_name) if name]
                event = {
                    "ts_utc": ts_utc,
                    "ts_local": ts_local,
                    "run_id": run_id,
                    "scenario_bucket": scenario_bucket,
                    "scenario_label": scenario_label,
                    "phase_stage": phase_stage,
                    "phase_trigger_reason": phase_trigger_reason,
                    "source_mode": source_mode,
                    "truth_level": truth_level,
                    "tunnel_id": tunnel_id,
                    "tunnel_direction": tunnel_direction,
                    "tunnel_kind": tunnel_kind,
                    "hop_count": hop_count,
                    "hop_chain_ids": chain_ids,
                    "hop_chain_names": chain_names,
                    "router_id": rid,
                    "router_name": rname or f"Router {rid}",
                    "role": self._phase5b_role_from_index(idx, hop_count),
                    "hop_index": idx,
                    "neighbor_names": neighbor_names,
                    "_source_file": raw.get("_source_file"),
                }
                dedupe_key = (
                    str(event.get("ts_utc") or event.get("ts_local") or ""),
                    str(event.get("run_id") or ""),
                    str(event.get("tunnel_id") or ""),
                    str(event.get("router_id") or event.get("router_name") or ""),
                    str(event.get("hop_index") or ""),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                normalized.append(event)
        normalized.sort(key=lambda e: (
            self._analytics_ts_epoch(e.get("ts_utc") or e.get("ts_local")),
            str(e.get("run_id") or ""),
            str(e.get("tunnel_id") or ""),
            int(e.get("hop_index") or 0),
        ))
        return normalized

    def _phase5b_producer_manifest_payload(self):
        candidate_files = self._phase5b_producer_candidate_files()
        raw_records = []
        source_modes = set()
        for path in candidate_files:
            for item in self._phase5b_producer_parse_raw_file(path):
                if isinstance(item, dict):
                    norm = dict(item)
                    norm["_source_file"] = path
                    raw_records.append(norm)
                    mode = str(item.get("source_mode") or item.get("truth_source") or "").strip()
                    if mode:
                        source_modes.add(mode)
        normalized_events = self._phase5b_producer_normalize_records(raw_records)
        routers = sorted({str(e.get("router_id") or e.get("router_name") or "") for e in normalized_events if (e.get("router_id") or e.get("router_name"))})
        tunnels = sorted({str(e.get("tunnel_id") or "") for e in normalized_events if e.get("tunnel_id")})
        run_ids = sorted({str(e.get("run_id") or "") for e in normalized_events if e.get("run_id")})
        role_totals = {"entry": 0, "middle": 0, "endpoint": 0, "unknown": 0}
        for e in normalized_events:
            role = str(e.get("role") or "unknown").strip().lower()
            if role not in role_totals:
                role = "unknown"
            role_totals[role] += 1
        if not source_modes:
            source_modes = {str(e.get("source_mode") or "").strip() for e in normalized_events if e.get("source_mode")}
        return {
            "generated_at": now_display(),
            "raw_candidate_files": candidate_files,
            "raw_record_count": len(raw_records),
            "normalized_event_count": len(normalized_events),
            "router_count": len(routers),
            "tunnel_count": len(tunnels),
            "run_ids": run_ids,
            "source_modes": sorted([m for m in source_modes if m]) or ["none"],
            "role_totals": role_totals,
            "normalized_events_preview": normalized_events[:200],
            "summary": "The truth producer normalizes authoritative emulator-observed or log-derived hop events into the canonical hop-record store.",
            "limitation": "This producer does not invent hop truth; it only transforms raw authoritative records when they exist.",
        }

    def _build_phase5b_producer_text(self, payload=None):
        payload = payload if payload is not None else self._phase5b_producer_manifest_payload()
        lines = ["Path record processor", "=" * 72]
        lines.append(format_kv("Generated at", payload.get("generated_at")))
        lines.append(format_kv("Raw candidate files", len(payload.get("raw_candidate_files") or [])))
        lines.append(format_kv("Raw records read", payload.get("raw_record_count")))
        lines.append(format_kv("Normalized events", payload.get("normalized_event_count")))
        lines.append(format_kv("Tunnels tracked", payload.get("tunnel_count")))
        lines.append(format_kv("Routers tracked", payload.get("router_count")))
        lines.append(format_kv("Source modes", ", ".join(payload.get("source_modes") or ["none"])))
        lines.extend([
            "",
            "Role totals",
            "-" * 11,
            format_kv("Entry exact", payload.get("role_totals", {}).get("entry", 0)),
            format_kv("Middle exact", payload.get("role_totals", {}).get("middle", 0)),
            format_kv("Endpoint exact", payload.get("role_totals", {}).get("endpoint", 0)),
            format_kv("Unknown exact", payload.get("role_totals", {}).get("unknown", 0)),
            "",
            "Input locations",
            "-" * 15,
            self._phase5b_producer_raw_root(),
            os.path.join(HOP_TRUTH_ROOT_DIR, "imports"),
            "",
            "Output locations",
            "-" * 16,
            self._phase5b_producer_output_paths().get("jsonl"),
            self._phase5b_producer_output_paths().get("json"),
            self._phase5b_producer_output_paths().get("manifest"),
            "",
            "Notes",
            "-" * 5,
            "The truth producer converts authoritative raw hop-chain records into canonical hop-record files.",
            "Accepted raw filenames include exact-hop-source.json/jsonl, tunnel-build-events.json/jsonl, and ground-truth-hop-events.json/jsonl.",
            "If no authoritative raw files exist yet, the producer reports zero events and does not fabricate exact hop truth.",
        ])
        return "\n".join(lines)

    
    def run_phase5b_exact_hop_producer(self, notify=True, reason="manual"):
        started_local = now_display()
        payload = self._phase5b_producer_manifest_payload()
        paths = self._phase5b_producer_output_paths()
        raw_records = []
        for path in payload.get("raw_candidate_files") or []:
            for item in self._phase5b_producer_parse_raw_file(path):
                if isinstance(item, dict):
                    norm = dict(item)
                    norm["_source_file"] = path
                    raw_records.append(norm)
        full_events = self._phase5b_producer_normalize_records(raw_records)
        write_json_atomic(paths["json"], {"events": full_events, "generated_at": now_display(), "source": "phase5b-producer"})
        with open(paths["jsonl"], "w", encoding="utf-8") as fh:
            for row in full_events:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest = dict(payload)
        manifest["normalized_event_count"] = len(full_events)
        manifest["normalized_events_preview"] = full_events[:200]
        manifest["output_paths"] = paths
        write_json_atomic(paths["manifest"], manifest)
        result = {
            "trigger_reason": str(reason or "manual"),
            "started_at_local": started_local,
            "finished_at_local": now_display(),
            "normalized_event_count": len(full_events),
            "manifest_path": paths["manifest"],
            "json_path": paths["json"],
            "jsonl_path": paths["jsonl"],
            "raw_candidate_file_count": len(payload.get("raw_candidate_files") or []),
            "result_text": f"Normalization refreshed the canonical ground-truth dataset ({len(full_events)} event(s)).",
        }
        self.deploy_status.setText(f"Path record normalization wrote ground-truth files to: {paths['jsonl']}")
        self.append_measurement_log(f"[{now_display()}] Path record normalization wrote ground-truth files to: {paths['jsonl']}")
        self.update_measurement_panel()
        if notify:
            QMessageBox.information(self, APP_NAME, f"Path record normalization completed.\n\nJSONL:\n{paths['jsonl']}\n\nJSON:\n{paths['json']}\n\nManifest:\n{paths['manifest']}")
        return result

    def export_phase5b_producer_manifest_json(self):
        payload = self._phase5b_producer_manifest_payload()
        payload["summary_text"] = self._build_phase5b_producer_text(payload)
        payload["output_paths"] = self._phase5b_producer_output_paths()
        paths = self._phase5b_producer_output_paths()
        write_json_atomic(paths["manifest"], payload)
        self.deploy_status.setText(f"Path record processor manifest written to: {paths['manifest']}")
        self.append_measurement_log(f"[{now_display()}] Path record processor manifest written to: {paths['manifest']}")
        QMessageBox.information(self, APP_NAME, f"Path record processor manifest written to:\n{paths['manifest']}")

    def _phase5b_truth_candidate_files(self, limit_files=240):
        files = []
        seen = set()
        patterns = (
            "exact-hop-truth.json",
            "exact-hop-truth.jsonl",
            "hop_truth.json",
            "hop_truth.jsonl",
            "tunnel_hops.json",
            "tunnel_hops.jsonl",
            "ground_truth_hops.json",
            "ground_truth_hops.jsonl",
            "exact_hops.json",
            "exact_hops.jsonl",
        )
        roots = [
            HOP_TRUTH_ROOT_DIR,
            os.path.join(HOP_TRUTH_ROOT_DIR, "events"),
            os.path.join(HOP_TRUTH_ROOT_DIR, "imports"),
        ]
        for root in roots:
            if not os.path.isdir(root):
                continue
            for name in patterns:
                for path in glob.glob(os.path.join(root, "**", name), recursive=True):
                    norm = os.path.normpath(path)
                    if norm not in seen:
                        seen.add(norm)
                        files.append(norm)
        for run_dir in list_recent_run_dirs(CAMPAIGN_ROOT_DIR, limit=200):
            for name in patterns:
                path = os.path.join(run_dir, name)
                if os.path.isfile(path):
                    norm = os.path.normpath(path)
                    if norm not in seen:
                        seen.add(norm)
                        files.append(norm)
        files.sort(key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0.0, reverse=True)
        return files[:limit_files]

    def _phase5b_parse_truth_file(self, path):
        records = []
        lower = str(path).lower()
        try:
            if lower.endswith(".jsonl"):
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            value = json.loads(line)
                        except Exception:
                            continue
                        if isinstance(value, dict):
                            records.append(value)
            else:
                value = read_json_file(path, {})
                if isinstance(value, list):
                    records.extend([item for item in value if isinstance(item, dict)])
                elif isinstance(value, dict):
                    for key in ("events", "records", "hop_events", "tunnels", "items"):
                        seq = value.get(key)
                        if isinstance(seq, list) and seq:
                            records.extend([item for item in seq if isinstance(item, dict)])
                            break
                    else:
                        if value:
                            records.append(value)
        except Exception:
            return []
        return records

    def _phase5b_normalize_chain_router(self, item):
        if isinstance(item, dict):
            rid = str(item.get("router_id") or item.get("id") or item.get("router") or "").strip()
            name = phase5b_normalize_router_name(item.get("router_name") or item.get("name") or "")
            if rid and not name:
                name = f"Router {rid}"
            if name and not rid:
                match = re.search(r"(\d+)", name)
                if match:
                    rid = match.group(1)
            return {"router_id": rid, "router_name": name or (f"Router {rid}" if rid else "")}
        value = phase5b_normalize_router_name(item)
        if not value:
            return {"router_id": "", "router_name": ""}
        match = re.search(r"(\d+)", value)
        rid = match.group(1) if match else ""
        if rid and not value:
            value = f"Router {rid}"
        return {"router_id": rid, "router_name": value}

    def _phase5b_extract_hop_chain(self, raw):
        chain = raw.get("hop_chain")
        if not isinstance(chain, list) or not chain:
            for key in ("full_hop_chain", "path", "routers", "hops"):
                value = raw.get(key)
                if isinstance(value, list) and value:
                    chain = value
                    break
        if not isinstance(chain, list):
            return []
        normalized = []
        for item in chain:
            norm = self._phase5b_normalize_chain_router(item)
            if norm.get("router_id") or norm.get("router_name"):
                normalized.append(norm)
        return normalized

    def _phase5b_role_from_index(self, hop_index, hop_count):
        if hop_index is None or hop_count <= 0:
            return "unknown"
        if hop_index == 1:
            return "entry"
        if hop_index == hop_count:
            return "endpoint"
        return "middle"

    def _phase5b_change_type(self, previous_event, current_event):
        if not previous_event:
            return "initial_observation"
        prev_chain = previous_event.get("full_hop_chain") or []
        curr_chain = current_event.get("full_hop_chain") or []
        prev_role = str(previous_event.get("role") or "")
        curr_role = str(current_event.get("role") or "")
        prev_hop = previous_event.get("hop_index")
        curr_hop = current_event.get("hop_index")
        prev_neighbors = tuple(previous_event.get("neighbor_names") or [])
        curr_neighbors = tuple(current_event.get("neighbor_names") or [])
        if prev_chain != curr_chain:
            if prev_hop == 1 and curr_hop == 1:
                return "entry_hop_changed"
            if prev_role == "middle" or curr_role == "middle":
                return "middle_hop_changed"
            if prev_role == "endpoint" or curr_role == "endpoint":
                return "endpoint_hop_changed"
            return "full_path_changed"
        if prev_role != curr_role and curr_role:
            return "role_changed"
        if prev_hop != curr_hop and curr_hop is not None:
            return "hop_position_changed"
        if prev_neighbors != curr_neighbors:
            return "neighbor_set_changed"
        if len(prev_chain) != len(curr_chain):
            return "path_length_changed"
        return "stable"


    def _phase5b_is_normalized_truth_event(self, raw):
        if not isinstance(raw, dict):
            return False
        has_router = bool(str(raw.get("router_id") or "").strip() or str(raw.get("router_name") or "").strip())
        has_chain = (
            (isinstance(raw.get("full_hop_chain"), list) and bool(raw.get("full_hop_chain")))
            or (isinstance(raw.get("hop_chain"), list) and bool(raw.get("hop_chain")))
            or (isinstance(raw.get("hop_chain_names"), list) and bool(raw.get("hop_chain_names")))
            or (isinstance(raw.get("routers"), list) and bool(raw.get("routers")))
            or (isinstance(raw.get("hops"), list) and bool(raw.get("hops")))
        )
        has_hop = raw.get("hop_index") is not None or bool(str(raw.get("role") or "").strip())
        return has_router and has_chain and has_hop

    def _phase5b_normalized_event_from_row(self, raw):
        if not isinstance(raw, dict):
            return None
        chain_raw = raw.get("full_hop_chain")
        if not isinstance(chain_raw, list) or not chain_raw:
            chain_raw = raw.get("hop_chain")
        if not isinstance(chain_raw, list) or not chain_raw:
            chain_raw = raw.get("hop_chain_names")
        if not isinstance(chain_raw, list) or not chain_raw:
            chain_raw = raw.get("routers")
        if not isinstance(chain_raw, list) or not chain_raw:
            chain_raw = raw.get("hops")
        if not isinstance(chain_raw, list) or not chain_raw:
            return None
        chain_names = []
        chain_ids = []
        for item in chain_raw:
            norm = self._phase5b_normalize_chain_router(item)
            if norm.get("router_id") or norm.get("router_name"):
                chain_names.append(norm.get("router_name") or (f"Router {norm.get('router_id')}" if norm.get("router_id") else ""))
                chain_ids.append(str(norm.get("router_id") or ""))
        if not chain_names:
            return None
        rid = str(raw.get("router_id") or "").strip()
        rname = phase5b_normalize_router_name(raw.get("router_name") or "")
        if not rname and rid:
            rname = f"Router {rid}"
        hop_count = safe_int(raw.get("hop_count"), len(chain_names)) or len(chain_names)
        hop_index = safe_int(raw.get("hop_index"), 0)
        if hop_index <= 0:
            if rname in chain_names:
                hop_index = chain_names.index(rname) + 1
            elif rid and rid in [x for x in chain_ids if x]:
                hop_index = chain_ids.index(rid) + 1
            else:
                hop_index = 1
        neighbor_names = raw.get("neighbor_names") or raw.get("neighbor_routers") or []
        if not isinstance(neighbor_names, list):
            neighbor_names = []
        neighbor_names = [phase5b_normalize_router_name(x) for x in neighbor_names if phase5b_normalize_router_name(x)]
        if not neighbor_names:
            if hop_index > 1 and hop_index - 2 < len(chain_names):
                neighbor_names.append(chain_names[hop_index - 2])
            if hop_index < len(chain_names):
                neighbor_names.append(chain_names[hop_index])
        tunnel_id = str(raw.get("tunnel_id") or raw.get("id") or raw.get("trace_id") or raw.get("path_id") or "").strip()
        path_signature = str(raw.get("path_signature") or raw.get("signature") or " > ".join([name for name in chain_names if name]) or tunnel_id).strip()
        role = str(raw.get("role") or "").strip() or self._phase5b_role_from_index(hop_index, hop_count)
        return {
            "ts_utc": raw.get("ts_utc") or raw.get("timestamp_utc") or raw.get("timestamp") or raw.get("ts"),
            "ts_local": raw.get("ts_local") or raw.get("timestamp_local") or raw.get("ts_utc") or raw.get("timestamp"),
            "run_id": str(raw.get("run_id") or raw.get("campaign_run_id") or raw.get("measurement_run_id") or "").strip(),
            "scenario_bucket": str(raw.get("scenario_bucket") or raw.get("scenario") or raw.get("bucket") or "").strip(),
            "scenario_label": str(raw.get("scenario_label") or raw.get("phase_label") or raw.get("scenario_bucket") or "").strip(),
            "phase_stage": str(raw.get("phase_stage") or raw.get("stage") or "").strip(),
            "phase_trigger_reason": str(raw.get("phase_trigger_reason") or raw.get("trigger") or "").strip(),
            "source_mode": str(raw.get("source_mode") or raw.get("truth_source") or "").strip() or "emulator-observed",
            "truth_level": str(raw.get("truth_level") or "ground-truth").strip(),
            "tunnel_id": tunnel_id,
            "tunnel_direction": str(raw.get("tunnel_direction") or raw.get("direction") or "").strip() or "unknown",
            "tunnel_kind": str(raw.get("tunnel_kind") or raw.get("kind") or raw.get("tunnel_type") or "").strip() or "unknown",
            "hop_count": hop_count,
            "full_hop_chain": chain_names,
            "full_hop_chain_ids": chain_ids,
            "path_signature": path_signature,
            "router_id": rid,
            "router_name": rname or (f"Router {rid}" if rid else ""),
            "role": role,
            "hop_index": hop_index,
            "neighbor_names": neighbor_names,
            "source_file": raw.get("_source_file"),
        }

    
    def _phase5b_expand_truth_records(self, raw_records):
        events = []
        for raw in raw_records:
            if not isinstance(raw, dict):
                continue
            if self._phase5b_is_normalized_truth_event(raw):
                event = self._phase5b_normalized_event_from_row(raw)
                if event:
                    events.append(event)
                continue
            chain = self._phase5b_extract_hop_chain(raw)
            if not chain:
                continue
            hop_count = len(chain)
            tunnel_id = str(raw.get("tunnel_id") or raw.get("id") or raw.get("trace_id") or raw.get("path_id") or "").strip()
            ts_utc = raw.get("ts_utc") or raw.get("timestamp_utc") or raw.get("timestamp") or raw.get("ts")
            ts_local = raw.get("ts_local") or raw.get("timestamp_local") or ts_utc
            run_id = str(raw.get("run_id") or raw.get("campaign_run_id") or raw.get("measurement_run_id") or "").strip()
            scenario_bucket = str(raw.get("scenario_bucket") or raw.get("scenario") or raw.get("bucket") or "").strip()
            scenario_label = str(raw.get("scenario_label") or raw.get("phase_label") or scenario_bucket or "").strip()
            phase_stage = str(raw.get("phase_stage") or raw.get("stage") or "").strip()
            phase_trigger_reason = str(raw.get("phase_trigger_reason") or raw.get("trigger") or "").strip()
            tunnel_direction = str(raw.get("tunnel_direction") or raw.get("direction") or "").strip() or "unknown"
            tunnel_kind = str(raw.get("tunnel_kind") or raw.get("kind") or raw.get("tunnel_type") or "").strip() or "unknown"
            source_mode = str(raw.get("source_mode") or raw.get("truth_source") or "").strip() or "emulator-observed"
            truth_level = str(raw.get("truth_level") or "ground-truth").strip()
            chain_names = [phase5b_normalize_router_name(item.get("router_name") or f"Router {item.get('router_id')}") for item in chain]
            chain_ids = [str(item.get("router_id") or "") for item in chain]
            path_signature = " > ".join([name for name in chain_names if name]) or str(tunnel_id or "")
            if not path_signature:
                continue
            for idx, item in enumerate(chain, start=1):
                rid = str(item.get("router_id") or "").strip()
                rname = phase5b_normalize_router_name(item.get("router_name") or (f"Router {rid}" if rid else ""))
                if not rid and not rname:
                    continue
                neighbor_names = []
                if idx > 1 and idx - 2 < len(chain_names):
                    neighbor_names.append(chain_names[idx - 2])
                if idx < hop_count and idx < len(chain_names):
                    neighbor_names.append(chain_names[idx])
                events.append({
                    "ts_utc": ts_utc,
                    "ts_local": ts_local,
                    "run_id": run_id,
                    "scenario_bucket": scenario_bucket,
                    "scenario_label": scenario_label,
                    "phase_stage": phase_stage,
                    "phase_trigger_reason": phase_trigger_reason,
                    "source_mode": source_mode,
                    "truth_level": truth_level,
                    "tunnel_id": tunnel_id,
                    "tunnel_direction": tunnel_direction,
                    "tunnel_kind": tunnel_kind,
                    "hop_count": hop_count,
                    "full_hop_chain": chain_names,
                    "full_hop_chain_ids": chain_ids,
                    "path_signature": path_signature,
                    "router_id": rid,
                    "router_name": rname or f"Router {rid}",
                    "role": self._phase5b_role_from_index(idx, hop_count),
                    "hop_index": idx,
                    "neighbor_names": neighbor_names,
                    "source_file": raw.get("_source_file"),
                })
        deduped = []
        seen = set()
        for event in events:
            key = (
                str(event.get("ts_utc") or event.get("ts_local") or ""),
                str(event.get("run_id") or ""),
                str(event.get("tunnel_id") or ""),
                str(event.get("router_id") or event.get("router_name") or ""),
                str(event.get("hop_index") or ""),
                str(event.get("path_signature") or ""),
                str(event.get("source_mode") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        return deduped

    def _phase5b_hop_truth_payload(self, max_events_per_router=30):
        candidate_files = self._phase5b_truth_candidate_files()
        raw_records = []
        for path in candidate_files:
            for item in self._phase5b_parse_truth_file(path):
                if isinstance(item, dict):
                    norm = dict(item)
                    norm["_source_file"] = path
                    raw_records.append(norm)
        events = self._phase5b_expand_truth_records(raw_records)
        deduped = []
        seen_events = set()
        for event in events:
            key = (
                str(event.get("ts_utc") or event.get("ts_local") or ""),
                str(event.get("run_id") or ""),
                str(event.get("tunnel_id") or ""),
                str(event.get("router_id") or event.get("router_name") or ""),
                str(event.get("hop_index") or ""),
                str(event.get("path_signature") or ""),
            )
            if key in seen_events:
                continue
            seen_events.add(key)
            deduped.append(event)
        events = deduped
        events.sort(
            key=lambda e: (
                self._analytics_ts_epoch(e.get("ts_utc") or e.get("ts_local")),
                str(e.get("run_id") or ""),
                str(e.get("tunnel_id") or ""),
                safe_int(e.get("hop_index"), 0),
                safe_int(e.get("router_id"), 0),
            )
        )
        grouped = {}
        source_modes = set()
        role_totals = {"entry": 0, "middle": 0, "endpoint": 0, "unknown": 0}
        hop_index_totals = {}
        tunnel_ids = set()
        for event in events:
            rid = str(event.get("router_id") or "").strip()
            if not rid:
                continue
            grouped.setdefault(rid, []).append(dict(event))
            source_modes.add(str(event.get("source_mode") or "emulator-observed"))
            role = str(event.get("role") or "unknown")
            role_totals[role] = role_totals.get(role, 0) + 1
            hop = str(event.get("hop_index") or "")
            if hop:
                hop_index_totals[hop] = hop_index_totals.get(hop, 0) + 1
            if event.get("tunnel_id"):
                tunnel_ids.add(str(event.get("tunnel_id")))

        routers = []
        for rid in sorted(grouped.keys(), key=lambda value: safe_int(value, 999999)):
            router_events = grouped.get(rid) or []
            prev_event = None
            path_diversity = set()
            neighbor_counts = {}
            role_counts = {"entry": 0, "middle": 0, "endpoint": 0, "unknown": 0}
            hop_counts = {}
            change_counts = {}
            for event in router_events:
                event["changed_from_previous"] = bool(prev_event and prev_event.get("path_signature") != event.get("path_signature"))
                event["change_type"] = self._phase5b_change_type(prev_event, event)
                prev_event = dict(event)
                path_diversity.add(str(event.get("path_signature") or ""))
                role = str(event.get("role") or "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1
                hop = str(event.get("hop_index") or "")
                if hop:
                    hop_counts[hop] = hop_counts.get(hop, 0) + 1
                change = str(event.get("change_type") or "stable")
                change_counts[change] = change_counts.get(change, 0) + 1
                for name in event.get("neighbor_names") or []:
                    neighbor_counts[name] = neighbor_counts.get(name, 0) + 1
            role_order = sorted(role_counts.items(), key=lambda item: (-item[1], item[0]))
            hop_order = sorted(hop_counts.items(), key=lambda item: (-item[1], safe_int(item[0], 999)))
            neighbor_order = sorted(neighbor_counts.items(), key=lambda item: (-item[1], item[0]))
            rebuild_count = sum(change_counts.get(name, 0) for name in ("full_path_changed", "entry_hop_changed", "middle_hop_changed", "endpoint_hop_changed"))
            role_change_count = change_counts.get("role_changed", 0)
            hop_change_count = change_counts.get("hop_position_changed", 0)
            routers.append({
                "router_id": rid,
                "router_name": (router_events[-1].get("router_name") if router_events else None) or f"Router {rid}",
                "source_modes": sorted(set(str(e.get("source_mode") or "emulator-observed") for e in router_events)),
                "samples": len(router_events),
                "first_seen": (router_events[0].get("ts_local") if router_events else None),
                "last_seen": (router_events[-1].get("ts_local") if router_events else None),
                "dominant_role": role_order[0][0] if role_order and role_order[0][1] > 0 else "unknown",
                "dominant_hop_index": safe_int(hop_order[0][0], 0) if hop_order else None,
                "role_counts": role_counts,
                "hop_index_counts": hop_counts,
                "path_diversity": len([sig for sig in path_diversity if sig]),
                "common_neighbors": [item[0] for item in neighbor_order[:3]],
                "neighbor_diversity": len(neighbor_counts),
                "path_rebuilds": rebuild_count,
                "role_changes": role_change_count,
                "hop_position_changes": hop_change_count,
                "recent_paths": list(dict.fromkeys([str(e.get("path_signature") or "") for e in router_events if e.get("path_signature")]))[-5:],
                "events": router_events[-max_events_per_router:],
            })

        payload = {
            "generated_at_local": now_display(),
            "generated_at_utc": now_iso_utc(),
            "version": "5B",
            "testnet_base": find_testnet_base(),
            "candidate_file_count": len(candidate_files),
            "raw_record_count": len(raw_records),
            "event_count": len(events),
            "router_count": len(routers),
            "tunnel_count": len(tunnel_ids),
            "source_modes": sorted(source_modes),
            "role_totals": role_totals,
            "hop_index_totals": hop_index_totals,
            "notes": {
                "summary": "Tunnel ground truth stores authoritative exact-hop truth when emulator-observed or log-derived hop-chain files are present.",
                "source_model": "ground-truth hop recorder",
                "limitation": "No exact events are recorded unless an authoritative hop source file exists; the recorder does not fabricate exact hop truth from surface inference.",
            },
            "candidate_files": candidate_files[:40],
            "routers": routers,
        }
        return payload

    def _build_phase5b_hop_truth_text(self, payload=None):
        payload = payload if payload is not None else self._phase5b_hop_truth_payload()
        lines = ["Authoritative hop records", "=" * 72]
        lines.extend([
            f"Generated at           : {payload.get('generated_at_local', 'unknown')}",
            f"Candidate files        : {payload.get('candidate_file_count', 0)}",
            f"Raw records read       : {payload.get('raw_record_count', 0)}",
            f"Exact events           : {payload.get('event_count', 0)}",
            f"Tunnels tracked        : {payload.get('tunnel_count', 0)}",
            f"Routers tracked        : {payload.get('router_count', 0)}",
            f"Source modes           : {', '.join(payload.get('source_modes') or []) or 'none'}",
            "",
            "Role totals",
            "-----------",
        ])
        role_totals = payload.get("role_totals") or {}
        lines.extend([
            f"Entry exact            : {role_totals.get('entry', 0)}",
            f"Middle exact           : {role_totals.get('middle', 0)}",
            f"Endpoint exact         : {role_totals.get('endpoint', 0)}",
            f"Unknown exact          : {role_totals.get('unknown', 0)}",
            "",
            "Per-router exact hop summary",
            "----------------------------",
        ])
        routers = payload.get("routers") or []
        if not routers:
            lines.extend([
                "No authoritative exact-hop events are available yet.",
                "To populate tunnel ground truth, place emulator-observed or log-derived exact-hop files under:",
                f"  {HOP_TRUTH_ROOT_DIR}",
                "or inside campaign run directories using names like exact-hop-truth.json/jsonl or hop_truth.json/jsonl.",
                "",
            ])
        else:
            for item in routers[:10]:
                lines.extend([
                    f"{item.get('router_name', 'Router ?')}",
                    f"  source modes         : {', '.join(item.get('source_modes') or []) or 'unknown'}",
                    f"  samples              : {item.get('samples', 0)} | first={item.get('first_seen', 'n/a')} | last={item.get('last_seen', 'n/a')}",
                    f"  dominant role/hop    : {item.get('dominant_role', 'unknown')} / {item.get('dominant_hop_index', 'n/a')}",
                    f"  rebuilds/role/hop    : {item.get('path_rebuilds', 0)} / {item.get('role_changes', 0)} / {item.get('hop_position_changes', 0)}",
                    f"  path diversity       : {item.get('path_diversity', 0)} | neighbors={item.get('neighbor_diversity', 0)}",
                    f"  common neighbors     : {', '.join(item.get('common_neighbors') or []) or 'none'}",
                    f"  recent exact paths   : {', '.join(item.get('recent_paths') or []) or 'none'}",
                    "",
                ])
        lines.extend([
            "Notes",
            "-----",
            "Tunnel ground truth records exact hop truth only from authoritative sources.",
            "If exact hop source files are missing, this recorder stays empty instead of estimating hop order from visible tunnel/lease surfaces.",
        ])
        return "\n".join(lines).rstrip()

    def _phase5b_hop_truth_export_rows(self, payload=None):
        payload = payload if payload is not None else self._phase5b_hop_truth_payload()
        rows = []
        for item in payload.get("routers") or []:
            rows.append({
                "router_id": item.get("router_id"),
                "router_name": item.get("router_name"),
                "source_modes": ", ".join(item.get("source_modes") or []),
                "samples": item.get("samples"),
                "first_seen": item.get("first_seen"),
                "last_seen": item.get("last_seen"),
                "dominant_role": item.get("dominant_role"),
                "dominant_hop_index": item.get("dominant_hop_index"),
                "path_rebuilds": item.get("path_rebuilds"),
                "role_changes": item.get("role_changes"),
                "hop_position_changes": item.get("hop_position_changes"),
                "path_diversity": item.get("path_diversity"),
                "neighbor_diversity": item.get("neighbor_diversity"),
                "common_neighbors": ", ".join(item.get("common_neighbors") or []),
                "recent_paths": " || ".join(item.get("recent_paths") or []),
            })
        return rows

    def _phase5b_export_paths(self):
        ensure_dir(HOP_TRUTH_ROOT_DIR)
        ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, "routers"))
        ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, "summaries"))
        base = filesystem_safe_name(os.path.basename(find_testnet_base() or "testnet"))
        return {
            "json": os.path.join(HOP_TRUTH_ROOT_DIR, "summaries", f"{base}-phase5b-hop-truth.json"),
            "csv": os.path.join(HOP_TRUTH_ROOT_DIR, "summaries", f"{base}-phase5b-hop-truth.csv"),
            "routers": os.path.join(HOP_TRUTH_ROOT_DIR, "routers"),
        }

    def reset_phase5b_test_data(self):
        reply = QMessageBox.question(
            self,
            APP_NAME,
            "Reset generated path-record data?\n\nThis removes generated raw exact-hop events, generated ground-truth outputs, and the automatic-detection state. Imported truth files are not touched.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        targets = [
            self._phase5b_capture_raw_output_path(),
            os.path.join(HOP_TRUTH_ROOT_DIR, "raw", "exact-hop-import-manifest.json"),
            os.path.join(HOP_TRUTH_ROOT_DIR, "events", "exact-hop-truth.jsonl"),
            os.path.join(HOP_TRUTH_ROOT_DIR, "events", "exact-hop-truth.json"),
            self._phase5b_producer_output_paths().get("manifest"),
            self._phase5c_state_path(),
        ]
        removed = 0
        for path in targets:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    removed += 1
            except Exception:
                pass
        self.append_measurement_log(f"[{now_display()}] Generated path-record data reset. Removed files: {removed}")
        self.deploy_status.setText("Generated path-record data reset.")
        self.update_measurement_panel()
        QMessageBox.information(self, APP_NAME, f"Generated path-record data reset. Removed files: {removed}")


    def export_phase5b_hop_truth_json(self):
        payload = self._phase5b_hop_truth_payload()
        payload["summary_text"] = self._build_phase5b_hop_truth_text(payload)
        payload["flat_rows"] = self._phase5b_hop_truth_export_rows(payload)
        paths = self._phase5b_export_paths()
        write_json_atomic(paths["json"], payload)
        for item in payload.get("routers") or []:
            router_path = os.path.join(paths["routers"], f"router-{filesystem_safe_name(str(item.get('router_id') or 'unknown'))}-hop-truth.json")
            write_json_atomic(router_path, item)
        self.deploy_status.setText(f"Tunnel ground truth JSON written to: {paths['json']}")
        self.append_measurement_log(f"[{now_display()}] Tunnel ground truth JSON written to: {paths['json']}")
        QMessageBox.information(self, APP_NAME, f"Tunnel ground truth JSON written to:\n{paths['json']}")

    def export_phase5b_hop_truth_csv(self):
        payload = self._phase5b_hop_truth_payload()
        rows = self._phase5b_hop_truth_export_rows(payload)
        if not rows:
            QMessageBox.information(self, APP_NAME, "No tunnel ground-truth rows are available yet.")
            return
        paths = self._phase5b_export_paths()
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        with open(paths["csv"], "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        self.deploy_status.setText(f"Tunnel ground truth CSV written to: {paths['csv']}")
        self.append_measurement_log(f"[{now_display()}] Tunnel ground truth CSV written to: {paths['csv']}")
        QMessageBox.information(self, APP_NAME, f"Tunnel ground truth CSV written to:\n{paths['csv']}")


    def _phase6_exact_hop_analytics_payload(self):
        payload5b = self._phase5b_hop_truth_payload(max_events_per_router=5000)
        routers = payload5b.get("routers") or []
        all_events = []
        seen = set()
        for router in routers:
            for event in router.get("events") or []:
                if not isinstance(event, dict):
                    continue
                key = (
                    str(event.get("ts_utc") or event.get("ts_local") or ""),
                    str(event.get("run_id") or ""),
                    str(event.get("tunnel_id") or ""),
                    str(event.get("router_id") or event.get("router_name") or ""),
                    str(event.get("hop_index") or ""),
                    str(event.get("path_signature") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                all_events.append(dict(event))

        def is_malformed_scenario_bucket(value):
            raw = str(value or "").strip()
            if not raw:
                return False
            lower = raw.lower()
            if "router" in lower and ("," in raw or ">" in raw):
                return True
            if re.search(r"(?i)\brouter\s*\d+\b", raw) and ("," in raw or ">" in raw):
                return True
            return False

        scenario_map = {}
        pair_counts = {}
        path_counts = {}
        source_modes = set(payload5b.get("source_modes") or [])
        ignored_malformed_events = 0
        ignored_malformed_buckets = set()

        def event_change_type(ev):
            return str(ev.get("change_type") or "").strip().lower()

        for event in all_events:
            bucket = str(event.get("scenario_bucket") or "other").strip() or "other"
            label = str(event.get("scenario_label") or "").strip()
            run_id = str(event.get("run_id") or "").strip()
            tunnel_id = str(event.get("tunnel_id") or "").strip()
            role = str(event.get("role") or "unknown").strip() or "unknown"
            path_sig = str(event.get("path_signature") or " > ".join(event.get("full_hop_chain") or [])).strip()
            if path_sig:
                path_counts[path_sig] = path_counts.get(path_sig, 0) + 1

            chain = [phase5b_normalize_router_name(x) for x in (event.get("full_hop_chain") or []) if phase5b_normalize_router_name(x)]
            if len(chain) >= 2:
                for a, b in zip(chain, chain[1:]):
                    pair = tuple(sorted((a, b)))
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

            if is_malformed_scenario_bucket(bucket):
                ignored_malformed_events += 1
                ignored_malformed_buckets.add(bucket)
                continue

            scenario = scenario_map.setdefault(bucket, {
                "bucket": bucket,
                "labels": {},
                "runs": set(),
                "tunnels": set(),
                "routers": set(),
                "role_totals": {"entry": 0, "middle": 0, "endpoint": 0, "unknown": 0},
                "path_counts": {},
                "neighbor_set_counts": {},
                "events": 0,
                "rebuild_events": 0,
                "role_shift_events": 0,
                "hop_shift_events": 0,
                "neighbor_shift_events": 0,
                "changed_events": 0,
            })
            if label:
                scenario["labels"][label] = scenario["labels"].get(label, 0) + 1
            if run_id:
                scenario["runs"].add(run_id)
            if tunnel_id:
                scenario["tunnels"].add(tunnel_id)
            router_name = phase5b_normalize_router_name(event.get("router_name") or (f"Router {event.get('router_id')}" if event.get('router_id') else ""))
            if router_name:
                scenario["routers"].add(router_name)
            scenario["role_totals"][role] = scenario["role_totals"].get(role, 0) + 1
            if path_sig:
                scenario["path_counts"][path_sig] = scenario["path_counts"].get(path_sig, 0) + 1
            neighbor_set = tuple(sorted([phase5b_normalize_router_name(x) for x in (event.get("neighbor_names") or []) if phase5b_normalize_router_name(x)]))
            if neighbor_set:
                scenario["neighbor_set_counts"][neighbor_set] = scenario["neighbor_set_counts"].get(neighbor_set, 0) + 1
            scenario["events"] += 1

            ctype = event_change_type(event)
            if bool(event.get("changed_from_previous")) or ctype not in ("", "stable", "initial_observation"):
                scenario["changed_events"] += 1
            if ctype in ("path_signature_changed", "full_path_changed", "entry_hop_changed", "middle_hop_changed", "endpoint_hop_changed", "path_length_changed"):
                scenario["rebuild_events"] += 1
            if ctype == "role_changed":
                scenario["role_shift_events"] += 1
            if ctype in ("hop_position_changed", "entry_hop_changed", "middle_hop_changed", "endpoint_hop_changed"):
                scenario["hop_shift_events"] += 1
            if ctype == "neighbor_set_changed":
                scenario["neighbor_shift_events"] += 1

        router_rows = []
        for router in routers:
            samples = safe_int(router.get("samples"), 0)
            rebuilds = safe_int(router.get("path_rebuilds"), 0)
            role_changes = safe_int(router.get("role_changes"), 0)
            hop_changes = safe_int(router.get("hop_position_changes"), 0)
            dominant_role = str(router.get("dominant_role") or "unknown")
            dominant_hop = safe_int(router.get("dominant_hop_index"), 0)
            role_counts = router.get("role_counts") or {}
            hop_counts = router.get("hop_index_counts") or {}
            recent_paths = list(dict.fromkeys(router.get("recent_paths") or []))
            dominant_role_count = safe_int(role_counts.get(dominant_role), 0)
            dominant_hop_count = safe_int(hop_counts.get(str(dominant_hop)), 0) if dominant_hop else 0
            persistence_ratio = round(dominant_role_count / samples, 4) if samples else 0.0
            hop_consistency = round(dominant_hop_count / samples, 4) if samples else 0.0
            rebuild_rate = round(rebuilds / max(samples - 1, 1), 4) if samples > 1 else 0.0
            structural_changes = max(rebuilds, role_changes + hop_changes)
            change_rate = round(structural_changes / max(samples - 1, 1), 4) if samples > 1 else 0.0
            router_rows.append({
                "router_id": router.get("router_id"),
                "router_name": phase5b_normalize_router_name(router.get("router_name")),
                "samples": samples,
                "dominant_role": dominant_role,
                "dominant_hop_index": dominant_hop or "",
                "dominant_role_share": persistence_ratio,
                "dominant_hop_share": hop_consistency,
                "path_rebuilds": rebuilds,
                "role_changes": role_changes,
                "hop_position_changes": hop_changes,
                "rebuild_rate": rebuild_rate,
                "change_rate": change_rate,
                "path_diversity": safe_int(router.get("path_diversity"), 0),
                "neighbor_diversity": safe_int(router.get("neighbor_diversity"), 0),
                "common_neighbors": list(router.get("common_neighbors") or []),
                "recent_paths": recent_paths,
                "source_modes": list(router.get("source_modes") or []),
                "first_seen": router.get("first_seen"),
                "last_seen": router.get("last_seen"),
            })

        router_rows.sort(key=lambda r: (-r.get("path_rebuilds", 0), -r.get("change_rate", 0.0), safe_int(r.get("router_id"), 999999)))

        scenario_rows = []
        for bucket, item in sorted(scenario_map.items(), key=lambda kv: kv[0]):
            labels_sorted = sorted(item["labels"].items(), key=lambda kv: (-kv[1], kv[0]))
            top_paths = sorted(item["path_counts"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            top_neighbors = sorted(item["neighbor_set_counts"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            role_totals = item["role_totals"]
            total = max(item["events"], 1)
            dominant_path_count = top_paths[0][1] if top_paths else 0
            dominant_neighbor_count = top_neighbors[0][1] if top_neighbors else 0
            scenario_rows.append({
                "scenario_bucket": bucket,
                "events": item["events"],
                "run_count": len(item["runs"]),
                "tunnel_count": len(item["tunnels"]),
                "router_count": len(item["routers"]),
                "entry": role_totals.get("entry", 0),
                "middle": role_totals.get("middle", 0),
                "endpoint": role_totals.get("endpoint", 0),
                "unknown": role_totals.get("unknown", 0),
                "entry_share": round(role_totals.get("entry", 0) / total, 4),
                "middle_share": round(role_totals.get("middle", 0) / total, 4),
                "endpoint_share": round(role_totals.get("endpoint", 0) / total, 4),
                "top_label": labels_sorted[0][0] if labels_sorted else "",
                "top_paths": [p for p, _ in top_paths],
                "rebuild_events": item["rebuild_events"],
                "rebuild_rate": round(item["rebuild_events"] / total, 4),
                "changed_events": item["changed_events"],
                "change_rate": round(item["changed_events"] / total, 4),
                "role_shift_events": item["role_shift_events"],
                "role_shift_rate": round(item["role_shift_events"] / total, 4),
                "hop_shift_events": item["hop_shift_events"],
                "hop_shift_rate": round(item["hop_shift_events"] / total, 4),
                "neighbor_shift_events": item["neighbor_shift_events"],
                "neighbor_shift_rate": round(item["neighbor_shift_events"] / total, 4),
                "path_persistence": round(dominant_path_count / total, 4) if total else 0.0,
                "neighbor_persistence": round(dominant_neighbor_count / total, 4) if total else 0.0,
                "neighbor_volatility": round(1.0 - (dominant_neighbor_count / total), 4) if total else 0.0,
                "top_neighbor_sets": [" | ".join(ns) for ns, _ in top_neighbors],
            })

        baseline = None
        for row in scenario_rows:
            if row.get("scenario_bucket") == "baseline":
                baseline = row
                break
        for row in scenario_rows:
            if baseline:
                row["delta_rebuild_vs_baseline"] = round(row.get("rebuild_rate", 0.0) - baseline.get("rebuild_rate", 0.0), 4)
                row["delta_persistence_vs_baseline"] = round(row.get("path_persistence", 0.0) - baseline.get("path_persistence", 0.0), 4)
                row["delta_neighbor_vol_vs_baseline"] = round(row.get("neighbor_volatility", 0.0) - baseline.get("neighbor_volatility", 0.0), 4)
            else:
                row["delta_rebuild_vs_baseline"] = None
                row["delta_persistence_vs_baseline"] = None
                row["delta_neighbor_vol_vs_baseline"] = None

        top_pairs = [
            {"router_a": a, "router_b": b, "count": count}
            for (a, b), count in sorted(pair_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        ]
        top_paths = [
            {"path": path, "count": count}
            for path, count in sorted(path_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        ]

        return {
            "generated_at_local": now_display(),
            "generated_at_utc": now_iso_utc(),
            "version": "6.2",
            "source_modes": sorted(source_modes),
            "router_count": len(router_rows),
            "tunnel_count": payload5b.get("tunnel_count", 0),
            "event_count": len(all_events),
            "scenario_count": len(scenario_rows),
            "role_totals": payload5b.get("role_totals") or {},
            "hop_index_totals": payload5b.get("hop_index_totals") or {},
            "routers": router_rows,
            "scenarios": scenario_rows,
            "top_neighbor_pairs": top_pairs,
            "top_paths": top_paths,
            "ignored_malformed_scenario_events": ignored_malformed_events,
            "ignored_malformed_scenario_buckets": sorted(ignored_malformed_buckets),
            "notes": {
                "summary": "Path analysis adds scenario-level exact-hop comparison on top of validated ground truth.",
                "comparison_basis": "Only authoritative exact-hop events from the ground-truth pipeline are included.",
                "limitation": "Scenario comparison reflects only runs/tunnels that currently have authoritative chain data.",
            },
        }

    def _build_phase6_exact_hop_analytics_text(self, payload=None):
        payload = payload if payload is not None else self._phase6_exact_hop_analytics_payload()
        lines = ["Path analysis and scenario comparison", "=" * 72]
        lines.extend([
            format_kv("Generated at", payload.get("generated_at_local")),
            format_kv("Exact events", payload.get("event_count", 0)),
            format_kv("Tunnels tracked", payload.get("tunnel_count", 0)),
            format_kv("Routers tracked", payload.get("router_count", 0)),
            format_kv("Scenarios tracked", payload.get("scenario_count", 0)),
            format_kv("Ignored malformed", payload.get("ignored_malformed_scenario_events", 0)),
            format_kv("Source modes", ", ".join(payload.get("source_modes") or []) or "none"),
            "",
            "Role totals",
            "-----------",
        ])
        role_totals = payload.get("role_totals") or {}
        lines.extend([
            f"Entry exact            : {role_totals.get('entry', 0)}",
            f"Middle exact           : {role_totals.get('middle', 0)}",
            f"Endpoint exact         : {role_totals.get('endpoint', 0)}",
            f"Unknown exact          : {role_totals.get('unknown', 0)}",
            "",
            "Per-router exact-hop trends",
            "---------------------------",
        ])
        routers = payload.get("routers") or []
        if not routers:
            lines.append("No exact-hop analytics are available yet.")
            lines.append("")
        else:
            for item in routers[:10]:
                lines.extend([
                    f"{item.get('router_name', 'Router ?')}",
                    f"  samples / role-hop   : {item.get('samples', 0)} | {item.get('dominant_role', 'unknown')} / {item.get('dominant_hop_index', 'n/a')}",
                    f"  rebuild/change rate  : {item.get('path_rebuilds', 0)} / {item.get('change_rate', 0.0)}",
                    f"  role/hop consistency : {item.get('dominant_role_share', 0.0)} / {item.get('dominant_hop_share', 0.0)}",
                    f"  path/neighbor div.   : {item.get('path_diversity', 0)} / {item.get('neighbor_diversity', 0)}",
                    f"  neighbors            : {', '.join(item.get('common_neighbors') or []) or 'none'}",
                    f"  recent paths         : {', '.join(item.get('recent_paths') or []) or 'none'}",
                    "",
                ])

        lines.extend([
            "Scenario comparison",
            "-------------------",
        ])
        scenarios = payload.get("scenarios") or []
        if not scenarios:
            lines.append("No scenario-tagged exact-hop analytics are available yet.")
            lines.append("")
        else:
            for item in scenarios[:10]:
                lines.extend([
                    f"{item.get('scenario_bucket', 'other')}  (events={item.get('events', 0)})",
                    f"  runs/tunnels/routers : {item.get('run_count', 0)} / {item.get('tunnel_count', 0)} / {item.get('router_count', 0)}",
                    f"  role shares          : entry={item.get('entry_share', 0.0)} | middle={item.get('middle_share', 0.0)} | endpoint={item.get('endpoint_share', 0.0)}",
                    f"  rebuild/change rate  : {item.get('rebuild_rate', 0.0)} / {item.get('change_rate', 0.0)}",
                    f"  role/hop shifts      : {item.get('role_shift_rate', 0.0)} / {item.get('hop_shift_rate', 0.0)}",
                    f"  path persistence     : {item.get('path_persistence', 0.0)} | neighbor volatility={item.get('neighbor_volatility', 0.0)}",
                    f"  delta vs baseline    : rebuild={item.get('delta_rebuild_vs_baseline')} | persistence={item.get('delta_persistence_vs_baseline')} | neighbor_vol={item.get('delta_neighbor_vol_vs_baseline')}",
                    f"  top label            : {item.get('top_label') or 'n/a'}",
                    f"  top paths            : {', '.join(item.get('top_paths') or []) or 'none'}",
                    f"  top neighbor sets    : {', '.join(item.get('top_neighbor_sets') or []) or 'none'}",
                    "",
                ])

        lines.extend([
            "Top neighbor pairs",
            "------------------",
        ])
        pairs = payload.get("top_neighbor_pairs") or []
        if not pairs:
            lines.append("No exact neighbor-pair analytics are available yet.")
            lines.append("")
        else:
            for item in pairs[:10]:
                lines.append(f"{item.get('router_a')} <-> {item.get('router_b')} : {item.get('count', 0)}")
            lines.append("")

        lines.extend([
            "Top exact paths",
            "---------------",
        ])
        top_paths = payload.get("top_paths") or []
        if not top_paths:
            lines.append("No exact path analytics are available yet.")
            lines.append("")
        else:
            for item in top_paths[:10]:
                lines.append(f"{item.get('path')} : {item.get('count', 0)}")
            lines.append("")

        lines.extend([
            "Notes",
            "-----",
            "Path analysis summarizes exact-hop role trends, neighbor pairs, path persistence, and scenario comparison.",
            "Only authoritative exact-hop events from the ground-truth pipeline are included in this analysis.",
        ])
        return "\n".join(lines).rstrip()

    def _phase6_exact_hop_analytics_export_rows(self, payload=None):
        payload = payload if payload is not None else self._phase6_exact_hop_analytics_payload()
        rows = []
        for item in payload.get("routers") or []:
            rows.append({
                "row_type": "router",
                "router_id": item.get("router_id"),
                "router_name": item.get("router_name"),
                "samples": item.get("samples"),
                "dominant_role": item.get("dominant_role"),
                "dominant_hop_index": item.get("dominant_hop_index"),
                "dominant_role_share": item.get("dominant_role_share"),
                "dominant_hop_share": item.get("dominant_hop_share"),
                "path_rebuilds": item.get("path_rebuilds"),
                "role_changes": item.get("role_changes"),
                "hop_position_changes": item.get("hop_position_changes"),
                "rebuild_rate": item.get("rebuild_rate"),
                "change_rate": item.get("change_rate"),
                "path_diversity": item.get("path_diversity"),
                "neighbor_diversity": item.get("neighbor_diversity"),
                "common_neighbors": ", ".join(item.get("common_neighbors") or []),
                "recent_paths": " || ".join(item.get("recent_paths") or []),
                "source_modes": ", ".join(item.get("source_modes") or []),
                "first_seen": item.get("first_seen"),
                "last_seen": item.get("last_seen"),
            })
        for item in payload.get("scenarios") or []:
            rows.append({
                "row_type": "scenario",
                "scenario_bucket": item.get("scenario_bucket"),
                "events": item.get("events"),
                "run_count": item.get("run_count"),
                "tunnel_count": item.get("tunnel_count"),
                "router_count": item.get("router_count"),
                "entry": item.get("entry"),
                "middle": item.get("middle"),
                "endpoint": item.get("endpoint"),
                "unknown": item.get("unknown"),
                "entry_share": item.get("entry_share"),
                "middle_share": item.get("middle_share"),
                "endpoint_share": item.get("endpoint_share"),
                "rebuild_events": item.get("rebuild_events"),
                "rebuild_rate": item.get("rebuild_rate"),
                "changed_events": item.get("changed_events"),
                "change_rate": item.get("change_rate"),
                "role_shift_events": item.get("role_shift_events"),
                "role_shift_rate": item.get("role_shift_rate"),
                "hop_shift_events": item.get("hop_shift_events"),
                "hop_shift_rate": item.get("hop_shift_rate"),
                "neighbor_shift_events": item.get("neighbor_shift_events"),
                "neighbor_shift_rate": item.get("neighbor_shift_rate"),
                "path_persistence": item.get("path_persistence"),
                "neighbor_persistence": item.get("neighbor_persistence"),
                "neighbor_volatility": item.get("neighbor_volatility"),
                "delta_rebuild_vs_baseline": item.get("delta_rebuild_vs_baseline"),
                "delta_persistence_vs_baseline": item.get("delta_persistence_vs_baseline"),
                "delta_neighbor_vol_vs_baseline": item.get("delta_neighbor_vol_vs_baseline"),
                "top_label": item.get("top_label"),
                "top_paths": " || ".join(item.get("top_paths") or []),
                "top_neighbor_sets": " || ".join(item.get("top_neighbor_sets") or []),
            })
        for item in payload.get("top_neighbor_pairs") or []:
            rows.append({
                "row_type": "neighbor_pair",
                "router_a": item.get("router_a"),
                "router_b": item.get("router_b"),
                "count": item.get("count"),
            })
        for item in payload.get("top_paths") or []:
            rows.append({
                "row_type": "path",
                "path": item.get("path"),
                "count": item.get("count"),
            })
        return rows

    def _phase6_export_paths(self):
        ensure_dir(HOP_TRUTH_ROOT_DIR)
        ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, "summaries"))
        base = filesystem_safe_name(os.path.basename(find_testnet_base() or "testnet"))
        return {
            "json": os.path.join(HOP_TRUTH_ROOT_DIR, "summaries", f"{base}-phase6-exact-hop-analytics.json"),
            "csv": os.path.join(HOP_TRUTH_ROOT_DIR, "summaries", f"{base}-phase6-exact-hop-analytics.csv"),
        }

    def export_phase6_exact_hop_analytics_json(self):
        payload = self._phase6_exact_hop_analytics_payload()
        payload["summary_text"] = self._build_phase6_exact_hop_analytics_text(payload)
        payload["flat_rows"] = self._phase6_exact_hop_analytics_export_rows(payload)
        paths = self._phase6_export_paths()
        write_json_atomic(paths["json"], payload)
        self.deploy_status.setText(f"Authoritative path analysis JSON written to: {paths['json']}")
        self.append_measurement_log(f"[{now_display()}] Authoritative path analysis JSON written to: {paths['json']}")
        QMessageBox.information(self, APP_NAME, f"Authoritative path analysis JSON written to:\n{paths['json']}")

    def export_phase6_exact_hop_analytics_csv(self):
        payload = self._phase6_exact_hop_analytics_payload()
        rows = self._phase6_exact_hop_analytics_export_rows(payload)
        if not rows:
            QMessageBox.information(self, APP_NAME, "No authoritative path analysis rows are available yet.")
            return
        paths = self._phase6_export_paths()
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        with open(paths["csv"], "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        self.deploy_status.setText(f"Authoritative path analysis CSV written to: {paths['csv']}")
        self.append_measurement_log(f"[{now_display()}] Authoritative path analysis CSV written to: {paths['csv']}")
        QMessageBox.information(self, APP_NAME, f"Authoritative path analysis CSV written to:\n{paths['csv']}")


    def _build_measurement_status_text(self):
        state = self.measurement_state or {}
        lines = ["Measurement status", "=" * 72]
        lines.extend([
            f"Status                 : {state.get('status', 'idle')}",
            f"Run ID                 : {state.get('run_id', 'none')}",
            f"Run directory          : {state.get('run_dir', 'none')}",
            f"Target group           : {state.get('target_group', 'unknown')}",
            f"HTTP fetch timeout     : {state.get('fetch_timeout', MEASUREMENT_FETCH_TIMEOUT_DEFAULT)} s",
            f"Completed probes       : {state.get('completed_probes', 0)} / {state.get('requested_probes', 0)}",
            "",
            f"Last message           : {state.get('last_message', 'No measurement run yet.')}",
        ])
        return "\n".join(lines)


    def _build_measurement_summary_text(self, record=None):
        lines = ["Latest measurement summary", "=" * 72]
        if not record:
            lines.append("No measurement run is available yet.")
            return "\n".join(lines)
        summary_wrapper = record.get("summary") or {}
        summary_payload = summary_wrapper.get("summary") or {}
        scenario_corr = summary_wrapper.get("scenario_correlation") or {}
        eepsite_target = summary_wrapper.get("eepsite_target") or {}
        state = record.get("state") or {}
        lines.extend([
            f"Run ID                 : {state.get('run_id', 'unknown')}",
            f"Status                 : {state.get('status', 'unknown')}",
            f"Completed probes       : {state.get('completed_probes', 0)} / {state.get('requested_probes', 0)}",
            f"Target group           : {state.get('target_group', 'unknown')}",
            f"Fetch timeout          : {state.get('fetch_timeout', MEASUREMENT_FETCH_TIMEOUT_DEFAULT)} s",
            "",
            f"Routers probed         : {summary_payload.get('routers_probed', 0)}",
            f"Root probe success     : {summary_payload.get('root_success', 0)}",
            f"netDb page success     : {summary_payload.get('netdb_success', 0)}",
            f"Mean root latency      : {summary_payload.get('mean_root_latency_ms', 'n/a')} ms",
            f"Mean netDb latency     : {summary_payload.get('mean_netdb_latency_ms', 'n/a')} ms",
            f"Client proxy success   : {summary_payload.get('client_proxy_success', 0)} / {summary_payload.get('routers_with_client_proxy', 0)}",
            f"Proxy connect success  : {summary_payload.get('client_proxy_connect_success', 0)} / {summary_payload.get('routers_with_client_proxy', 0)}",
            f"Tunnel trace snapshots : {summary_payload.get('tunnel_trace_success', 0)} | changed={summary_payload.get('tunnel_trace_changed_routers', 0)}",
            f"Mean proxy latency     : {summary_payload.get('mean_client_proxy_latency_ms', 'n/a')} ms",
            f"Mean proxy 1st byte    : {summary_payload.get('mean_client_proxy_first_byte_ms', 'n/a')} ms",
            "",
            f"Routers with startup   : {summary_payload.get('routers_with_startup_window', 0)}",
            f"Startup -> active avg  : {summary_payload.get('mean_startup_to_active_s', 'n/a')} s",
            f"Startup -> OK avg      : {summary_payload.get('mean_startup_to_ok_s', 'n/a')} s",
            f"Startup -> accepting   : {summary_payload.get('mean_startup_to_accepting_s', 'n/a')} s",
            f"Startup -> OK count    : {summary_payload.get('startup_to_ok_success_count', 0)}",
            f"Startup -> accept cnt  : {summary_payload.get('startup_to_accepting_success_count', 0)}",
            "",
            f"Control-plane ready    : {summary_payload.get('control_plane_ready_routers', 0)}",
            f"Transaction-ready      : {summary_payload.get('transaction_ready_routers', 0)}",
            f"Tunnel-ready routers   : {summary_payload.get('tunnel_ready_routers', 0)}",
            f"Full-ready routers     : {summary_payload.get('full_ready_routers', 0)}",
        ])
        if eepsite_target:
            lines.extend([
                "",
                "Internal eepsite target",
                "----------------------",
                f"Target URL            : {eepsite_target.get('target_url', 'unknown')}",
                f"Source router         : {eepsite_target.get('router_name', 'unknown')} ({eepsite_target.get('router_id', '?')})",
                f"Spoofed host hint     : {eepsite_target.get('spoofed_host', 'unknown')}",
                f"Discovered from       : {eepsite_target.get('source_path', 'unknown')}",
            ])
        if scenario_corr:
            lines.extend([
                "",
                "Correlated scenario context",
                "---------------------------",
                f"Scenario run           : {scenario_corr.get('run_id', 'unknown')}",
                f"Scenario               : {scenario_corr.get('scenario_type', 'unknown')} | target={scenario_corr.get('target_group', 'unknown')}",
                f"Cycles / actions       : {scenario_corr.get('completed_cycles', 0)}/{scenario_corr.get('requested_cycles', 0)} | actions={scenario_corr.get('actions_executed', 0)}",
                f"Seconds since finish   : {scenario_corr.get('seconds_since_finish', 'n/a')}",
                f"Routers touched        : {scenario_corr.get('routers_touched', 0)}",
                f"Touched recovered      : {scenario_corr.get('recovered_touched_routers', 0)}",
                f"Touched full-ready     : {scenario_corr.get('full_ready_touched_routers', 0)}",
            ])
        slow = summary_payload.get("top_slowest_root") or []
        if slow:
            lines.extend(["", "Slowest root-page probes", "------------------------"])
            for item in slow:
                lines.append(f"{item.get('router_name', 'Router ?'):<18} {item.get('latency_ms', 'n/a')} ms")
        slow_client = summary_payload.get("top_slowest_client_proxy") or []
        if slow_client:
            lines.extend(["", "Slowest client-proxy probes", "--------------------------"])
            for item in slow_client:
                lines.append(f"{item.get('router_name', 'Router ?'):<18} {item.get('latency_ms', 'n/a')} ms  status={item.get('status_code', 'n/a')}")
        recover = summary_payload.get("top_slowest_recovery") or []
        if recover:
            lines.extend(["", "Slowest recovery windows", "-----------------------"])
            for item in recover:
                lines.append(f"{item.get('router_name', 'Router ?'):<18} {item.get('seconds', 'n/a')} s via {item.get('trigger_event', 'unknown')}")
        lines.extend(["", "Note", "----", "v4 adds namespace-scoped HTTP client-proxy transaction probes and correlates the measurement run with the latest completed churn scenario. It still does not perform sustained throughput testing. For application transactions, it now expects an internal eepsite target inside the isolated testnet."])
        return "\n".join(lines)

    def _build_measurement_recent_text(self, runs=None):
        runs = runs if runs is not None else self._measurement_list_recent_runs()
        lines = ["Recent measurement runs", "=" * 72]
        if not runs:
            lines.append("No measurement runs found yet.")
            return "\n".join(lines)
        for idx, rec in enumerate(runs, 1):
            state = rec.get("state") or {}
            summary_wrapper = rec.get("summary") or {}
            summary_payload = summary_wrapper.get("summary") or {}
            scenario_corr = summary_wrapper.get("scenario_correlation") or {}
            eepsite_target = summary_wrapper.get("eepsite_target") or {}
            lines.extend([
                f"[{idx}] {state.get('run_id', 'unknown')}",
                f"  status              : {state.get('status', 'unknown')}",
                f"  target              : {state.get('target_group', 'unknown')}",
                f"  probes              : {state.get('completed_probes', 0)} / {state.get('requested_probes', 0)}",
                f"  root/netdb success  : {summary_payload.get('root_success', 0)} / {summary_payload.get('netdb_success', 0)}",
                f"  client proxy        : {summary_payload.get('client_proxy_success', 0)} / {summary_payload.get('routers_with_client_proxy', 0)}",
                f"  tunnel trace        : {summary_payload.get('tunnel_trace_success', 0)} | changed={summary_payload.get('tunnel_trace_changed_routers', 0)}",
                f"  mean root latency   : {summary_payload.get('mean_root_latency_ms', 'n/a')} ms",
                f"  mean proxy latency  : {summary_payload.get('mean_client_proxy_latency_ms', 'n/a')} ms",
                f"  startup -> active   : {summary_payload.get('mean_startup_to_active_s', 'n/a')} s",
                f"  startup -> OK avg   : {summary_payload.get('mean_startup_to_ok_s', 'n/a')} s",
                f"  startup -> accept   : {summary_payload.get('mean_startup_to_accepting_s', 'n/a')} s",
                f"  full-ready routers  : {summary_payload.get('full_ready_routers', 0)}",
                f"  correlated scenario : {scenario_corr.get('run_id', 'none') if scenario_corr else 'none'}",
                f"  eepsite target      : {eepsite_target.get('target_url', 'none') if eepsite_target else 'none'}",
                f"  run dir             : {rec.get('run_dir', 'unknown')}",
                "",
            ])
        return "\n".join(lines).rstrip()

    def _tunnel_trace_recent_rows(self, limit_runs=TUNNEL_TRACE_RECENT_RUN_LIMIT):
        rows = []
        chronological = list(reversed(self._measurement_list_recent_runs(limit=limit_runs)))
        phase_index = load_recent_campaign_measurement_phase_index()
        raw_rows = []
        for rec in chronological:
            state = rec.get("state") or {}
            summary_wrapper = rec.get("summary") or {}
            scenario_corr = summary_wrapper.get("scenario_correlation") or {}
            run_id = state.get("run_id")
            phase_info = dict(phase_index.get(str(run_id or "")) or {})
            phase_label = phase_info.get("phase_label")
            if not phase_label:
                if phase_info.get("campaign_run_id") or phase_info.get("stage") or phase_info.get("trigger_reason"):
                    phase_label = _classify_campaign_measurement_phase(phase_info.get("stage"), phase_info.get("trigger_reason"))
                elif scenario_corr:
                    phase_label = "standalone"
                    phase_info.setdefault("campaign_run_id", None)
                    phase_info.setdefault("stage", "scenario-correlated")
                    phase_info.setdefault("trigger_reason", "recent_completed_scenario")
                    phase_info.setdefault("cycle_index", None)
                else:
                    phase_label = "standalone"
                    phase_info.setdefault("stage", "standalone")
                    phase_info.setdefault("trigger_reason", "manual_or_one_shot")
                    phase_info.setdefault("cycle_index", None)
            trace_path = os.path.join(rec.get("run_dir", ""), "trace.jsonl")
            trace_records = read_jsonl_records(trace_path)
            if not trace_records:
                probe_records = read_jsonl_records(os.path.join(rec.get("run_dir", ""), "probes.jsonl"))
                for probe in probe_records:
                    trace = probe.get("tunnel_trace") or {}
                    if not trace:
                        continue
                    trace_records.append({
                        "router_id": probe.get("router_id"),
                        "router_name": probe.get("router_name"),
                        "run_id": run_id,
                        "target_url": probe.get("client_target_url"),
                        "client_proxy_success": (probe.get("client_proxy") or {}).get("success"),
                        "client_proxy_latency_ms": (probe.get("client_proxy") or {}).get("latency_ms"),
                        "client_proxy_first_byte_ms": (probe.get("client_proxy") or {}).get("first_byte_ms"),
                        "trace": trace,
                        "ts_local": probe.get("ts_local"),
                        "ts_utc": probe.get("ts_utc"),
                    })
            for item in trace_records:
                trace = item.get("trace") or {}
                raw_rows.append({
                    "run_id": run_id,
                    "run_dir": rec.get("run_dir"),
                    "router_id": str(item.get("router_id") or ""),
                    "router_name": item.get("router_name") or f"Router {item.get('router_id') or '?'}",
                    "scenario_label": (scenario_corr.get("experiment_label") or phase_info.get("experiment_label") or "baseline"),
                    "scenario_run_id": scenario_corr.get("run_id") or phase_info.get("scenario_run_id"),
                    "campaign_run_id": phase_info.get("campaign_run_id"),
                    "phase_label": phase_label,
                    "phase_stage": phase_info.get("stage"),
                    "phase_trigger_reason": phase_info.get("trigger_reason"),
                    "phase_cycle_index": phase_info.get("cycle_index"),
                    "target_url": item.get("target_url"),
                    "client_proxy_success": item.get("client_proxy_success"),
                    "client_proxy_latency_ms": item.get("client_proxy_latency_ms"),
                    "client_proxy_first_byte_ms": item.get("client_proxy_first_byte_ms"),
                    "signature": str(trace.get("signature") or ""),
                    "sample_b32_hosts": trace.get("sample_b32_hosts") or [],
                    "keyword_counts": trace.get("keyword_counts") or {},
                    "trace_note": trace.get("trace_note") or "",
                    "ts_local": item.get("ts_local") or state.get("finished_at_local") or state.get("updated_at_local"),
                    "ts_utc": item.get("ts_utc") or state.get("finished_at_utc") or state.get("updated_at_utc"),
                })
        # compute first/last seen for each router+signature over the loaded timeline
        signature_windows = {}
        for row in raw_rows:
            key = (row.get("router_id"), row.get("signature"))
            win = signature_windows.setdefault(key, {
                "first_seen_local": row.get("ts_local"),
                "first_seen_run_id": row.get("run_id"),
                "last_seen_local": row.get("ts_local"),
                "last_seen_run_id": row.get("run_id"),
                "seen_count": 0,
            })
            win["seen_count"] += 1
            if str(row.get("ts_local") or "") < str(win.get("first_seen_local") or ""):
                win["first_seen_local"] = row.get("ts_local")
                win["first_seen_run_id"] = row.get("run_id")
            if str(row.get("ts_local") or "") >= str(win.get("last_seen_local") or ""):
                win["last_seen_local"] = row.get("ts_local")
                win["last_seen_run_id"] = row.get("run_id")

        last_row_by_router = {}
        generation_by_router = {}
        for row in raw_rows:
            rid = row.get("router_id")
            sig = row.get("signature")
            prev = last_row_by_router.get(rid)
            changed = False
            if prev and sig and prev.get("signature") and prev.get("signature") != sig:
                changed = True
            row["previous_signature"] = (prev or {}).get("signature", "")
            row["previous_run_id"] = (prev or {}).get("run_id")
            row["previous_ts_local"] = (prev or {}).get("ts_local")
            row["previous_phase_label"] = (prev or {}).get("phase_label")
            row["changed"] = changed
            generation = generation_by_router.get(rid, 0)
            if generation == 0:
                generation = 1
            elif changed:
                generation += 1
            generation_by_router[rid] = generation
            row["path_generation"] = generation
            win = signature_windows.get((rid, sig), {})
            row["signature_first_seen_local"] = win.get("first_seen_local")
            row["signature_first_seen_run_id"] = win.get("first_seen_run_id")
            row["signature_last_seen_local"] = win.get("last_seen_local")
            row["signature_last_seen_run_id"] = win.get("last_seen_run_id")
            row["signature_seen_count"] = win.get("seen_count", 0)
            row["is_first_seen_for_signature"] = win.get("first_seen_local") == row.get("ts_local") and win.get("first_seen_run_id") == row.get("run_id")
            row["is_last_seen_for_signature"] = win.get("last_seen_local") == row.get("ts_local") and win.get("last_seen_run_id") == row.get("run_id")
            row["change_summary"] = (
                f"{prev.get('signature')} -> {sig}" if changed and prev else
                (f"stable {sig}" if sig else "n/a")
            )
            last_row_by_router[rid] = row
            rows.append(row)
        rows.sort(key=lambda row: (str(row.get("ts_local") or ""), str(row.get("router_id") or "")), reverse=True)
        return rows

    def _tunnel_trace_stability_score(self, latest_row, change_events=0):
        generation = safe_int((latest_row or {}).get("path_generation"), 1)
        latest_changed = bool((latest_row or {}).get("changed"))
        proxy_success = (latest_row or {}).get("client_proxy_success")
        penalty = max(0, generation - 1) * 20
        penalty += max(0, safe_int(change_events, 0)) * 12
        if latest_changed:
            penalty += 8
        if proxy_success is False:
            penalty += 25
        return max(0, min(100, 100 - penalty))

    def _build_tunnel_trace_comparison_text(self, rows=None):
        rows = rows if rows is not None else self._tunnel_trace_recent_rows()
        lines = ["Tunnel trace comparison summary", "=" * 72]
        if not rows:
            lines.append("No tunnel trace snapshots found yet.")
            return "\n".join(lines)

        routers = {}
        for row in rows:
            rid = str(row.get("router_id") or "")
            if not rid:
                continue
            bucket = routers.setdefault(rid, {"rows": [], "name": row.get("router_name") or f"Router {rid}"})
            bucket["rows"].append(row)

        total_routers = len(routers)
        changed_latest = 0
        stable_latest = 0
        generations_gt1 = 0
        successful_latest = 0
        latest_ts = max((str(r.get("ts_local") or "") for r in rows), default="n/a")
        phase_counts = {}
        stage_counts = {}
        trigger_counts = {}
        detail_rows = []

        for rid, bucket in routers.items():
            ordered = sorted(bucket["rows"], key=lambda r: str(r.get("ts_local") or ""), reverse=True)
            latest = ordered[0]
            latest_changed = bool(latest.get("changed"))
            if latest_changed:
                changed_latest += 1
            else:
                stable_latest += 1
            if int(latest.get("path_generation") or 0) > 1:
                generations_gt1 += 1
            if latest.get("client_proxy_success") is True:
                successful_latest += 1
            phase = str(latest.get("phase_label") or "unknown")
            stage = str(latest.get("phase_stage") or "n/a")
            trig = str(latest.get("phase_trigger_reason") or "n/a")
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            trigger_counts[trig] = trigger_counts.get(trig, 0) + 1
            change_events = sum(1 for r in bucket["rows"] if r.get("changed"))
            score = self._tunnel_trace_stability_score(latest, change_events=change_events)
            detail_rows.append({
                "router_name": bucket["name"],
                "generation": int(latest.get("path_generation") or 0),
                "latest_changed": latest_changed,
                "change_events": change_events,
                "latest_ts": latest.get("ts_local") or "n/a",
                "latest_phase": phase,
                "latest_stage": stage,
                "latest_trigger": trig,
                "client_proxy_success": latest.get("client_proxy_success"),
                "client_proxy_latency_ms": latest.get("client_proxy_latency_ms"),
                "signature": latest.get("signature") or "n/a",
                "previous_signature": latest.get("previous_signature") or "n/a",
                "stability_score": score,
            })

        detail_rows.sort(key=lambda item: (item["stability_score"], -item["change_events"], -item["generation"], item["router_name"]))
        avg_score = round(sum(item["stability_score"] for item in detail_rows) / len(detail_rows), 1) if detail_rows else None
        least_stable = detail_rows[0] if detail_rows else None

        lines.extend([
            f"Routers seen           : {total_routers}",
            f"Latest trace timestamp : {latest_ts}",
            f"Latest changed routers : {changed_latest}",
            f"Latest stable routers  : {stable_latest}",
            f"Generation > 1 routers : {generations_gt1}",
            f"Latest proxy success   : {successful_latest} / {total_routers}",
            (f"Least stable router    : {least_stable['router_name']} (score={least_stable['stability_score']})" if least_stable else "Least stable router    : n/a"),
            f"Average stability score: {avg_score if avg_score is not None else 'n/a'}",
        ])

        lines.extend(["", "Top latest router scores", "------------------------"])
        for item in detail_rows[:3]:
            lines.append(
                f"{item['router_name']:<14} score={item['stability_score']} | gen={item['generation']} | changed={'yes' if item['latest_changed'] else 'no'} | proxy={item['client_proxy_success']}"
            )

        if phase_counts:
            lines.extend(["", "Latest phase distribution", "------------------------"])
            for key, value in sorted(phase_counts.items()):
                lines.append(f"{key:<22} {value}")
        if stage_counts:
            lines.extend(["", "Latest stage distribution", "------------------------"])
            for key, value in sorted(stage_counts.items()):
                lines.append(f"{key:<22} {value}")
        if trigger_counts:
            lines.extend(["", "Latest trigger distribution", "--------------------------"])
            for key, value in sorted(trigger_counts.items()):
                lines.append(f"{key:<22} {value}")

        lines.extend(["", "Per-router latest trace state", "-----------------------------"])
        for item in detail_rows[:12]:
            lines.extend([
                f"{item['router_name']}",
                f"  score={item['stability_score']} | gen={item['generation']} | changed={'yes' if item['latest_changed'] else 'no'} | changes={item['change_events']}",
                f"  phase={item['latest_phase']} | stage={item['latest_stage']} | trigger={item['latest_trigger']}",
                f"  proxy={item['client_proxy_success']} | latency={item['client_proxy_latency_ms']} ms | ts={item['latest_ts']}",
                f"  sig={item['signature']} | prev={item['previous_signature']}",
            ])

        return "\n".join(lines)

    def _build_tunnel_trace_text(self, rows=None):
        rows = rows if rows is not None else self._tunnel_trace_recent_rows()
        lines = ["Tunnel path / lifecycle trace v4", "=" * 72]
        lines.append("This view documents visible tunnel/lease surface changes over time. It adds signature history, first/last seen windows, campaign phase labels, per-router stability scoring, and a compact comparison summary. It still does not guarantee exact per-hop router IDs for each request.")
        if not rows:
            lines.append("No tunnel trace snapshots found yet.")
            return "\n".join(lines)
        # compute change-event counts per router for scoring
        change_counts = {}
        for _row in rows:
            rid = str(_row.get("router_id") or "")
            if not rid:
                continue
            change_counts.setdefault(rid, 0)
            if _row.get("changed"):
                change_counts[rid] += 1
        for idx, row in enumerate(rows[:24], 1):
            hosts = ", ".join((row.get("sample_b32_hosts") or [])[:3]) or "n/a"
            kws = row.get("keyword_counts") or {}
            score = self._tunnel_trace_stability_score(row, change_events=change_counts.get(str(row.get("router_id") or ""), 0))
            lines.extend([
                f"[{idx}] {row.get('ts_local', 'unknown')} | {row.get('router_name', 'unknown')} | phase={row.get('phase_label', 'measurement')} | gen={row.get('path_generation', 'n/a')} | score={score}",
                f"  run/signature       : {row.get('run_id', 'unknown')} | {row.get('signature', 'n/a')}",
                f"  previous signature  : {row.get('previous_signature', 'n/a') or 'n/a'} | at {row.get('previous_ts_local', 'n/a') or 'n/a'} | phase={row.get('previous_phase_label', 'n/a') or 'n/a'}",
                f"  path changed        : {'yes' if row.get('changed') else 'no'} | {row.get('change_summary', 'n/a')}",
                f"  first / last seen   : {row.get('signature_first_seen_local', 'n/a')} -> {row.get('signature_last_seen_local', 'n/a')} | count={row.get('signature_seen_count', 0)}",
                f"  campaign / phase    : {row.get('campaign_run_id', 'none') or 'none'} | stage={row.get('phase_stage', 'n/a') or 'n/a'} | trigger={row.get('phase_trigger_reason', 'n/a') or 'n/a'} | cycle={row.get('phase_cycle_index', 'n/a')}",
                f"  stability score     : {score}",
                f"  target              : {row.get('target_url', 'n/a')}",
                f"  client proxy        : success={row.get('client_proxy_success')} | latency={row.get('client_proxy_latency_ms', 'n/a')} ms | first-byte={row.get('client_proxy_first_byte_ms', 'n/a')} ms",
                f"  visible b32 hosts   : {hosts}",
                f"  surface counts      : in={kws.get('inbound', 0)} | out={kws.get('outbound', 0)} | lease={kws.get('lease', 0)} | expl={kws.get('exploratory', 0)} | client={kws.get('client', 0)} | part={kws.get('participating', 0)}",
            ])
        return "\n".join(lines)

    def export_tunnel_trace_json(self):
        rows = self._tunnel_trace_recent_rows()
        if not rows:
            QMessageBox.information(self, APP_NAME, "No tunnel trace snapshots are available yet.")
            return
        ensure_dir(CAMPAIGN_ROOT_DIR)
        path = os.path.join(CAMPAIGN_ROOT_DIR, f"{filesystem_safe_name(os.path.basename(find_testnet_base() or 'testnet'))}-tunnel-trace-v4.2.json")
        payload = {
            "generated_at_local": now_display(),
            "generated_at_utc": now_iso_utc(),
            "testnet_base": find_testnet_base(),
            "version": 4,
            "notes": {
                "summary": "Tunnel path / lifecycle trace v4 documents visible tunnel/lease surface changes over time and adds comparison summaries.",
                "limitation": "It does not guarantee exact per-hop router IDs for each request.",
            },
            "comparison_summary_text": self._build_tunnel_trace_comparison_text(rows),
            "rows": rows,
        }
        write_json_atomic(path, payload)
        QMessageBox.information(self, APP_NAME, f"Tunnel trace JSON exported to:\n{path}")

    def update_measurement_panel(self):
        runs = self._measurement_list_recent_runs()
        latest = runs[0] if runs else None
        if hasattr(self, 'measurement_status_view'):
            self.measurement_status_view.setPlainText(self._build_measurement_status_text())
        if hasattr(self, 'measurement_latest_view'):
            self.measurement_latest_view.setPlainText(self._build_measurement_summary_text(latest))
        if hasattr(self, 'measurement_recent_view'):
            self.measurement_recent_view.setPlainText(self._build_measurement_recent_text(runs))
        if hasattr(self, 'experiment_summary_view'):
            self.experiment_summary_view.setPlainText(self._build_experiment_summary_text())
        if hasattr(self, 'analytics_summary_view'):
            self.analytics_summary_view.setPlainText(self._build_long_term_analytics_text())
        if hasattr(self, 'phase5_summary_view'):
            self.phase5_summary_view.setPlainText(self._build_phase5_hop_history_text())
        if hasattr(self, 'phase5b_producer_view'):
            self.phase5b_producer_view.setPlainText(self._build_phase5b_producer_text())
        if hasattr(self, 'phase5b_capture_view'):
            self.phase5b_capture_view.setPlainText(self._build_phase5b_capture_text())
        if hasattr(self, 'phase5c_summary_view'):
            self.phase5c_summary_view.setPlainText(self._build_phase5c_status_text())
        if hasattr(self, 'phase5b_summary_view'):
            self.phase5b_summary_view.setPlainText(self._build_phase5b_hop_truth_text())
        if hasattr(self, 'phase6_summary_view'):
            self.phase6_summary_view.setPlainText(self._build_phase6_exact_hop_analytics_text())
        if hasattr(self, 'tunnel_trace_summary_view'):
            self.tunnel_trace_summary_view.setPlainText(self._build_tunnel_trace_comparison_text())
        if hasattr(self, 'tunnel_trace_view'):
            self.tunnel_trace_view.setPlainText(self._build_tunnel_trace_text())

    def append_measurement_log(self, text):
        if not hasattr(self, 'measurement_log'):
            return
        existing = self.measurement_log.toPlainText().splitlines()
        existing.append(text)
        existing = existing[-SCENARIO_LOG_LINE_LIMIT:]
        self.measurement_log.setPlainText("\n".join(existing))
        cursor = self.measurement_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End if PYQT_VER == 6 else cursor.End)
        self.measurement_log.setTextCursor(cursor)

    def build_measurement_config(self):
        snapshot = self.snapshot or {}
        routers = []
        testnet_base = snapshot.get('base') or find_testnet_base()
        for router in snapshot.get('routers', []):
            parsed = router.get('parsed', {}) or {}
            router_id = str(router.get('id'))
            console_host = router.get('console_host') or parsed.get('console_host') or router.get('router_ip') or parsed.get('router_ip') or '127.0.0.1'
            console_port = router.get('console_port', parsed.get('console_port', 'unknown'))
            console_url = router.get('console_url', '')
            if not console_url and console_port not in {'', 'unknown'}:
                console_url = f"http://{console_host}:{console_port}"
            routers.append({
                'id': router_id,
                'name': router.get('name', f"Router {router.get('id')}"),
                'status': router.get('status', 'unknown'),
                'floodfill': router.get('floodfill', 'false'),
                'console_port': console_port,
                'console_host': console_host,
                'console_url': console_url,
                'router_ip': router.get('router_ip', parsed.get('router_ip', 'unknown')),
                'namespace': parsed.get('namespace', router.get('namespace', 'unknown')),
                'client_proxy_port': parsed.get('client_proxy_port', 'unknown'),
                'client_target_destination': parsed.get('client_target_destination', 'unknown'),
                'client_target_url': parsed.get('client_target_url', ''),
                'server_tunnel_type': parsed.get('server_tunnel_type', 'unknown'),
                'server_spoofed_host': parsed.get('server_spoofed_host', 'unknown'),
                'server_privkey_file': parsed.get('server_privkey_file', 'unknown'),
                'server_target_host': parsed.get('server_target_host', 'unknown'),
                'server_target_port': parsed.get('server_target_port', 'unknown'),
                'measurement_eepsite_name': parsed.get('measurement_eepsite_name', 'unknown'),
                'measurement_eepsite_role': parsed.get('measurement_eepsite_role', 'unknown'),
                'testnet_base': testnet_base,
            })
        target_group = self.measurement_target_combo.currentData() if hasattr(self, 'measurement_target_combo') else 'active_all'
        fetch_timeout = float(self.measurement_fetch_timeout.value()) if hasattr(self, 'measurement_fetch_timeout') else MEASUREMENT_FETCH_TIMEOUT_DEFAULT
        return {
            'testnet_base': testnet_base,
            'target_group': target_group,
            'fetch_timeout': fetch_timeout,
            'selected_router_id': self.selected_router_id,
            'telemetry_session_dir': self.telemetry.session_dir if self.telemetry and self.telemetry.has_active_session() else (self._history_load_latest_telemetry_state() or {}).get('session_dir'),
            'routers': routers,
        }

    def start_measurement_run(self):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, 'Another task is already running.')
            return
        config = self.build_measurement_config()
        if not config.get('testnet_base'):
            QMessageBox.critical(self, APP_NAME, 'No testnet base is available for measurements.')
            return
        if not config.get('routers'):
            QMessageBox.critical(self, APP_NAME, 'No router inventory is available for measurements.')
            return
        self.measurement_state = {
            'status': 'starting',
            'run_id': None,
            'run_dir': None,
            'completed_probes': 0,
            'requested_probes': 0,
            'last_message': 'Preparing measurement run...',
            'target_group': config.get('target_group'),
            'fetch_timeout': config.get('fetch_timeout'),
            'summary': {},
        }
        self.measurement_log.setPlainText('')
        self.append_measurement_log(f"[{now_display()}] Preparing measurement run...")
        self.set_busy(True)
        self.measurement_thread = MeasurementProbeThread(config, parent=self)
        self.measurement_thread.log_line.connect(self.append_measurement_log)
        self.measurement_thread.status_changed.connect(lambda msg: self.deploy_status.setText(msg[-140:] if len(msg) > 140 else msg))
        self.measurement_thread.started_run.connect(self.on_measurement_started)
        self.measurement_thread.progress.connect(self.on_measurement_progress)
        self.measurement_thread.finished_run.connect(self.on_measurement_finished)
        self.measurement_thread.failed_run.connect(self.on_measurement_failed)
        self.measurement_thread.start()
        self.center_tabs.setCurrentWidget(self.measurement_panel)

    def on_measurement_started(self, manifest):
        self.measurement_state.update({
            'status': 'running',
            'run_id': manifest.get('run_id'),
            'run_dir': manifest.get('run_dir'),
            'last_message': 'Measurement run started.',
        })
        self.update_measurement_panel()

    def on_measurement_progress(self, payload):
        self.measurement_state.update(payload or {})
        self.update_measurement_panel()

    def on_measurement_finished(self, payload):
        self.measurement_state.update(payload or {})
        self.set_busy(False)
        self.append_measurement_log(f"[{now_display()}] {self.measurement_state.get('last_message', 'Measurement run finished.')}")
        try:
            if self._phase5c_enabled():
                self.run_phase5c_auto_extract_latest_measurement(notify=False, run_dir=self.measurement_state.get("run_dir"), trigger_source="automatic-after-measurement")
        except Exception as e:
            self.append_measurement_log(f"[{now_display()}] Automatic path detection error: {e}")
        self.update_measurement_panel()
        self.measurement_thread = None

    def on_measurement_failed(self, message):
        self.measurement_state.update({
            'status': 'failed',
            'last_message': message,
        })
        self.set_busy(False)
        self.append_measurement_log(f"[{now_display()}] Measurement failed: {message}")
        self.update_measurement_panel()
        self.measurement_thread = None

    def _history_load_latest_telemetry_state(self):
        current = None
        try:
            if self.telemetry and self.telemetry.has_active_session():
                current = {
                    "session_id": self.telemetry.session_id,
                    "session_dir": self.telemetry.session_dir,
                    "testnet_base": self.telemetry.session_base,
                    "started_at_local": self.telemetry.session_started_local,
                    "poll_seconds": self.telemetry.poll_seconds,
                    "sample_count": self.telemetry.sample_count,
                    "router_sample_count": self.telemetry.router_sample_count,
                    "event_count": self.telemetry.event_count,
                    "last_snapshot": self.telemetry.last_snapshot,
                }
        except Exception:
            current = None
        if current:
            return current
        return read_json_file(TELEMETRY_STATE_FILE, default={})

    def _history_list_recent_telemetry_data(self, limit=8):
        session_dirs = list_recent_run_dirs(TELEMETRY_ROOT_DIR, require_files=["session.json", "state.json"], limit=limit)
        records = []
        for session_dir in session_dirs:
            session = read_json_file(os.path.join(session_dir, "session.json"), default={})
            state = read_json_file(os.path.join(session_dir, "state.json"), default={})
            last = state.get("last_snapshot") or {}
            records.append({
                "session_dir": session_dir,
                "session_id": session.get("session_id", os.path.basename(session_dir)),
                "started_at_local": session.get("started_at_local", state.get("started_at_local", "unknown")),
                "started_dt": parse_display_timestamp(session.get("started_at_local", state.get("started_at_local", ""))),
                "testnet_base": session.get("testnet_base", state.get("testnet_base", "unknown")),
                "poll_seconds": session.get("poll_seconds", state.get("poll_seconds", "unknown")),
                "sample_count": state.get("sample_count", 0),
                "router_sample_count": state.get("router_sample_count", 0),
                "event_count": state.get("event_count", 0),
                "last_snapshot": last,
                "last_snapshot_dt": parse_display_timestamp(last.get("generated_at", "")),
            })
        return records

    def _history_find_session_for_run(self, run_record, telemetry_sessions):
        if not run_record:
            return None
        run_start = parse_display_timestamp(run_record.get("started_at_local", ""))
        run_end = parse_display_timestamp(run_record.get("finished_at_local", "")) or run_start
        if not telemetry_sessions:
            return None
        best = None
        for session in telemetry_sessions:
            started = session.get("started_dt")
            ended = session.get("last_snapshot_dt")
            if started and run_start and started <= run_start:
                if ended is None or ended >= run_start:
                    best = session
                    break
        return best or telemetry_sessions[0]

    def _history_filter_events_by_window(self, events, start_dt=None, end_dt=None):
        filtered = []
        for event in events or []:
            ts = parse_display_timestamp(event.get("ts_local", ""))
            if start_dt and (ts is None or ts < start_dt):
                continue
            if end_dt and ts and ts > end_dt:
                continue
            filtered.append(event)
        return filtered

    def _history_collect_router_events(self, session_dir, start_dt=None, end_dt=None):
        path = os.path.join(session_dir or "", "router_events.jsonl")
        events = read_jsonl_records(path)
        if start_dt or end_dt:
            events = self._history_filter_events_by_window(events, start_dt, end_dt)
        return events

    def _history_compute_router_stats(self, events):
        router_stats = {}
        for event in events or []:
            rid = str(event.get("router_id", "")).strip()
            if not rid:
                continue
            stat = router_stats.setdefault(rid, {
                "name": event.get("router_name", f"Router {rid}"),
                "stop_detected": 0,
                "restart_detected": 0,
                "rejoin_detected": 0,
                "downtime_total": 0.0,
                "downtime_count": 0,
                "last_event": None,
            })
            et = str(event.get("event_type", "")).strip()
            if et in {"stop_detected", "restart_detected", "rejoin_detected"}:
                stat[et] += 1
            if et == "rejoin_detected":
                try:
                    dt = float(event.get("downtime_seconds", 0.0) or 0.0)
                except Exception:
                    dt = 0.0
                if dt > 0:
                    stat["downtime_total"] += dt
                    stat["downtime_count"] += 1
            stat["last_event"] = event.get("ts_local") or stat["last_event"]
        return router_stats

    def _history_compute_fleet_summary_text(self, session_dir):
        fleet_path = os.path.join(session_dir or "", "fleet_snapshots.jsonl")
        fleet_records = read_jsonl_records(fleet_path)
        router_events = self._history_collect_router_events(session_dir)
        if not fleet_records and not router_events:
            return "No fleet telemetry data found yet."
        lines = [
            "Fleet resilience summary",
            "=" * 72,
        ]
        if fleet_records:
            active_vals = [safe_int(r.get("active", 0), 0) for r in fleet_records]
            stopped_vals = [safe_int(r.get("stopped", 0), 0) for r in fleet_records]
            failed_vals = [safe_int(r.get("failed", 0), 0) for r in fleet_records]
            total_vals = [max(safe_int(r.get("total", 0), 0), 1) for r in fleet_records]
            availability = []
            for a, t in zip(active_vals, total_vals):
                availability.append((a / t) * 100.0 if t else 0.0)
            lines.extend([
                f"Fleet snapshots        : {len(fleet_records)}",
                f"Active min / max       : {min(active_vals)} / {max(active_vals)}",
                f"Stopped min / max      : {min(stopped_vals)} / {max(stopped_vals)}",
                f"Failed min / max       : {min(failed_vals)} / {max(failed_vals)}",
                f"Average active         : {sum(active_vals)/len(active_vals):.2f}",
                f"Average stopped        : {sum(stopped_vals)/len(stopped_vals):.2f}",
                f"Average availability   : {sum(availability)/len(availability):.2f}%",
            ])
        router_stats = self._history_compute_router_stats(router_events)
        if router_stats:
            total_stops = sum(s["stop_detected"] for s in router_stats.values())
            total_restarts = sum(s["restart_detected"] for s in router_stats.values())
            total_rejoins = sum(s["rejoin_detected"] for s in router_stats.values())
            downtime_total = sum(s["downtime_total"] for s in router_stats.values())
            downtime_count = sum(s["downtime_count"] for s in router_stats.values())
            lines.extend([
                "",
                "Derived churn KPIs",
                "------------------",
                f"Routers touched        : {len(router_stats)}",
                f"Stop events            : {total_stops}",
                f"Restart events         : {total_restarts}",
                f"Rejoin events          : {total_rejoins}",
                f"Downtime total         : {format_optional_seconds(downtime_total) if downtime_count else '0.0s'}",
                f"Downtime average       : {format_optional_seconds(downtime_total / downtime_count) if downtime_count else '0.0s'}",
            ])
            top = sorted(router_stats.items(), key=lambda item: (-item[1]["downtime_total"], -item[1]["stop_detected"], safe_int(item[0], 999999)))[:5]
            if top:
                lines.extend(["", "Top downtime routers", "--------------------"])
                for rid, stat in top:
                    lines.append(f"Router {rid:<3}  downtime={format_optional_seconds(stat['downtime_total']) if stat['downtime_count'] else '0.0s'}  stops={stat['stop_detected']}  rejoins={stat['rejoin_detected']}")
        return "\n".join(lines)

    def _history_compute_run_kpis(self, run_record, telemetry_sessions):
        if not run_record:
            return None
        run_start = parse_display_timestamp(run_record.get("started_at_local", ""))
        run_end = parse_display_timestamp(run_record.get("finished_at_local", ""))
        session = self._history_find_session_for_run(run_record, telemetry_sessions)
        router_events = self._history_collect_router_events((session or {}).get("session_dir"), run_start, run_end)
        router_stats = self._history_compute_router_stats(router_events)
        scenario_events = read_jsonl_records(os.path.join(run_record.get("run_dir", ""), "events.jsonl"))
        touched = set()
        cycle_waits = []
        for ev in scenario_events:
            rid = str(ev.get("router_id", "")).strip()
            if rid:
                touched.add(rid)
            if ev.get("event_type") == "inter_cycle_wait":
                try:
                    cycle_waits.append(float(ev.get("wait_seconds", 0.0) or 0.0))
                except Exception:
                    pass
        downtime_total = sum(s["downtime_total"] for s in router_stats.values())
        downtime_count = sum(s["downtime_count"] for s in router_stats.values())
        total_stops = sum(s["stop_detected"] for s in router_stats.values())
        total_restarts = sum(s["restart_detected"] for s in router_stats.values())
        total_rejoins = sum(s["rejoin_detected"] for s in router_stats.values())
        duration_seconds = None
        if run_start and run_end:
            duration_seconds = max((run_end - run_start).total_seconds(), 0.0)
        completed_cycles = safe_int(run_record.get("completed_cycles", 0), 0)
        actions = safe_int(run_record.get("actions_executed", 0), 0)
        actions_per_min = (actions / (duration_seconds / 60.0)) if duration_seconds and duration_seconds > 0 else 0.0
        return {
            "run": run_record,
            "session": session,
            "router_stats": router_stats,
            "routers_touched": len(touched),
            "stop_events": total_stops,
            "restart_events": total_restarts,
            "rejoin_events": total_rejoins,
            "downtime_total": downtime_total,
            "downtime_avg": (downtime_total / downtime_count) if downtime_count else 0.0,
            "duration_seconds": duration_seconds,
            "actions_per_min": actions_per_min,
            "avg_inter_cycle_wait": (sum(cycle_waits) / len(cycle_waits)) if cycle_waits else 0.0,
            "completed_cycles": completed_cycles,
            "actions": actions,
        }

    def _history_build_latest_run_kpis_text(self, run_kpis):
        lines = ["Latest scenario KPIs", "=" * 72]
        if not run_kpis:
            lines.append("No scenario run is available yet.")
            return "\n".join(lines)
        record = run_kpis["run"]
        lines.extend([
            f"Run ID                 : {record.get('run_id', 'unknown')}",
            f"Scenario               : {record.get('scenario_type', 'unknown')} | target={record.get('target_group', 'unknown')}",
            f"Status                 : {record.get('status', 'unknown')}",
            f"Started / finished     : {record.get('started_at_local', 'unknown')}  ->  {record.get('finished_at_local', 'unknown')}",
            f"Duration               : {format_optional_seconds(run_kpis['duration_seconds']) if run_kpis.get('duration_seconds') is not None else 'unknown'}",
            f"Cycles / actions       : {record.get('completed_cycles', 0)}/{record.get('requested_cycles', 0)} | actions={record.get('actions_executed', 0)}",
            f"Routers touched        : {run_kpis['routers_touched']}",
            f"Stop / restart / rejoin: {run_kpis['stop_events']} / {run_kpis['restart_events']} / {run_kpis['rejoin_events']}",
            f"Downtime total         : {format_optional_seconds(run_kpis['downtime_total']) if run_kpis['rejoin_events'] else '0.0s'}",
            f"Downtime average       : {format_optional_seconds(run_kpis['downtime_avg']) if run_kpis['rejoin_events'] else '0.0s'}",
            f"Actions per minute     : {run_kpis['actions_per_min']:.2f}",
            f"Avg inter-cycle wait   : {format_optional_seconds(run_kpis['avg_inter_cycle_wait']) if run_kpis['avg_inter_cycle_wait'] else '0.0s'}",
            f"Telemetry session      : {(run_kpis.get('session') or {}).get('session_id', 'unknown')}",
            "",
            "Most affected routers",
            "---------------------",
        ])
        ranked = sorted(run_kpis['router_stats'].items(), key=lambda item: (-item[1]['downtime_total'], -item[1]['stop_detected'], safe_int(item[0], 999999)))[:5]
        if not ranked:
            lines.append("No derived router churn events were found for this run window.")
        else:
            for rid, stat in ranked:
                lines.append(f"Router {rid} ({stat['name']})  stops={stat['stop_detected']}  rejoins={stat['rejoin_detected']}  downtime={format_optional_seconds(stat['downtime_total']) if stat['downtime_count'] else '0.0s'}")
        return "\n".join(lines)

    def _history_build_comparison_text(self, scenarios, telemetry_sessions):
        lines = ["Recent scenario comparison", "=" * 72]
        if not scenarios:
            lines.append("No scenario runs found yet.")
            return "\n".join(lines)
        for idx, record in enumerate(scenarios[:5], 1):
            kpis = self._history_compute_run_kpis(record, telemetry_sessions)
            duration = "unknown"
            actions_per_min = "n/a"
            routers_touched = "n/a"
            downtime = "0.0s"
            if kpis:
                duration = format_optional_seconds(kpis['duration_seconds']) if kpis.get('duration_seconds') is not None else "unknown"
                actions_per_min = f"{kpis['actions_per_min']:.2f}"
                routers_touched = str(kpis['routers_touched'])
                downtime = format_optional_seconds(kpis['downtime_total']) if kpis['rejoin_events'] else '0.0s'
            lines.extend([
                f"[{idx}] {record['run_id']}",
                f"  status              : {record['status']}",
                f"  scenario            : {record['scenario_type']} | target={record['target_group']}",
                f"  duration            : {duration}",
                f"  cycles / actions    : {record['completed_cycles']}/{record['requested_cycles']} | actions={record['actions_executed']}",
                f"  routers touched     : {routers_touched}",
                f"  stop/restart/rejoin : {kpis['stop_events'] if kpis else 'n/a'} / {kpis['restart_events'] if kpis else 'n/a'} / {kpis['rejoin_events'] if kpis else 'n/a'}",
                f"  downtime total      : {downtime}",
                f"  actions per minute  : {actions_per_min}",
                "",
            ])
        return "\n".join(lines).rstrip()

    def _history_router_churn_summary(self, session_dir):
        events = self._history_collect_router_events(session_dir)
        if not events:
            return "No router event history found yet."
        router_stats = self._history_compute_router_stats(events)
        if not router_stats:
            return "No router-specific events found in the current telemetry session."
        lines = [
            "Current telemetry session router churn summary",
            "=" * 72,
            f"Routers with events      : {len(router_stats)}",
            "",
            "Per-router counts",
            "-----------------",
        ]
        def sort_key(item):
            rid, stat = item
            return (- (stat["stop_detected"] + stat["restart_detected"] + stat["rejoin_detected"]), safe_int(rid, 999999))
        for rid, stat in sorted(router_stats.items(), key=sort_key):
            avg_down = (stat["downtime_total"] / stat["downtime_count"]) if stat["downtime_count"] else 0.0
            lines.extend([
                f"Router {rid} ({stat['name']})",
                f"  stop_detected        : {stat['stop_detected']}",
                f"  restart_detected     : {stat['restart_detected']}",
                f"  rejoin_detected      : {stat['rejoin_detected']}",
                f"  downtime total       : {format_optional_seconds(stat['downtime_total']) if stat['downtime_count'] else '0.0s'}",
                f"  downtime average     : {format_optional_seconds(avg_down) if stat['downtime_count'] else '0.0s'}",
                f"  last event           : {stat['last_event'] or 'unknown'}",
                "",
            ])
        return "\n".join(lines).rstrip()

    def _history_build_overview_text(self, telemetry_state, recent_scenarios):
        lines = ["Experiment overview", "=" * 72]
        base = self.snapshot.get("base") or (telemetry_state or {}).get("testnet_base") or "not found"
        lines.append(f"Current base           : {base}")
        lines.append(f"Fleet now              : total={self.snapshot.get('total', 0)} | active={self.snapshot.get('active', 0)} | stopped={self.snapshot.get('stopped', 0)} | failed={self.snapshot.get('failed', 0)}")
        lines.append(f"Selected router        : {self.selected_router_id or 'none'}")
        lines.append("")
        lines.append("Telemetry session")
        lines.append("-----------------")
        if telemetry_state:
            last = telemetry_state.get("last_snapshot") or {}
            poll_value = telemetry_state.get("poll_seconds", POLL_SECONDS)
            if isinstance(poll_value, str):
                poll_display = poll_value
            else:
                try:
                    poll_display = f"{float(poll_value):.1f}s"
                except Exception:
                    poll_display = str(poll_value)
            lines.append(f"Session ID             : {telemetry_state.get('session_id', 'unknown')}")
            lines.append(f"Started                : {telemetry_state.get('started_at_local', 'unknown')}")
            lines.append(f"Poll interval          : {poll_display}")
            lines.append(f"Fleet snapshots        : {telemetry_state.get('sample_count', 0)}")
            lines.append(f"Router samples         : {telemetry_state.get('router_sample_count', 0)}")
            lines.append(f"Event count            : {telemetry_state.get('event_count', 0)}")
            if last:
                lines.append(f"Last fleet snapshot    : {last.get('generated_at', 'unknown')} | active={last.get('active', 0)} | stopped={last.get('stopped', 0)} | failed={last.get('failed', 0)}")
        else:
            lines.append("No telemetry session is available yet.")
        lines.append("")
        lines.append("Scenario runs")
        lines.append("-------------")
        if recent_scenarios:
            latest = recent_scenarios[0]
            lines.append(f"Latest run             : {latest.get('run_id', 'unknown')}")
            lines.append(f"Status                 : {latest.get('status', 'unknown')}")
            lines.append(f"Scenario               : {latest.get('scenario_type', 'unknown')} | target={latest.get('target_group', 'unknown')}")
            lines.append(f"Cycles / actions       : {latest.get('completed_cycles', 0)}/{latest.get('requested_cycles', 0)} | actions={latest.get('actions_executed', 0)}")
            lines.append(f"Last message           : {latest.get('last_message', 'unknown')}")
        else:
            lines.append("No scenario runs recorded yet.")
        session_dir = (telemetry_state or {}).get("session_dir")
        fleet_path = os.path.join(session_dir or "", "fleet_snapshots.jsonl")
        fleet_records = read_jsonl_records(fleet_path)
        if fleet_records:
            active_vals = [safe_int(r.get("active", 0), 0) for r in fleet_records]
            stopped_vals = [safe_int(r.get("stopped", 0), 0) for r in fleet_records]
            lines.extend([
                "",
                "Fleet snapshot stats",
                "--------------------",
                f"Samples on disk        : {len(fleet_records)}",
                f"Active min / max       : {min(active_vals)} / {max(active_vals)}",
                f"Stopped min / max      : {min(stopped_vals)} / {max(stopped_vals)}",
                f"Average active         : {sum(active_vals)/len(active_vals):.2f}",
                f"Average stopped        : {sum(stopped_vals)/len(stopped_vals):.2f}",
            ])
        return "\n".join(lines)

    def _history_build_recent_telemetry_text(self, telemetry_sessions=None):
        telemetry_sessions = telemetry_sessions if telemetry_sessions is not None else self._history_list_recent_telemetry_data(limit=8)
        lines = ["Recent telemetry sessions", "=" * 72]
        if not telemetry_sessions:
            lines.append("No telemetry sessions found yet.")
            return "\n".join(lines)
        for idx, session in enumerate(telemetry_sessions, 1):
            last = session.get("last_snapshot") or {}
            lines.extend([
                f"[{idx}] {session.get('session_id', os.path.basename(session.get('session_dir', 'session')))}",
                f"  started             : {session.get('started_at_local', 'unknown')}",
                f"  base                : {session.get('testnet_base', 'unknown')}",
                f"  poll                : {session.get('poll_seconds', 'unknown')}",
                f"  samples / events    : {session.get('sample_count', 0)} fleet | {session.get('router_sample_count', 0)} router | {session.get('event_count', 0)} events",
                f"  last snapshot       : {last.get('generated_at', 'unknown')} | active={last.get('active', 0)} | stopped={last.get('stopped', 0)} | failed={last.get('failed', 0)}",
                f"  session dir         : {session.get('session_dir', 'unknown')}",
                "",
            ])
        return "\n".join(lines).rstrip()

    def _history_build_recent_scenarios_data(self):
        run_dirs = list_recent_run_dirs(SCENARIO_ROOT_DIR, require_files=["run.json", "state.json"], limit=8)
        scenarios = []
        for run_dir in run_dirs:
            run = read_json_file(os.path.join(run_dir, "run.json"), default={})
            state = read_json_file(os.path.join(run_dir, "state.json"), default={})
            scenarios.append({
                "run_id": run.get("run_id", os.path.basename(run_dir)),
                "run_dir": run_dir,
                "scenario_type": state.get("scenario_type", (run.get("config") or {}).get("scenario_type", "unknown")),
                "target_group": state.get("target_group", (run.get("config") or {}).get("target_group", "unknown")),
                "status": state.get("status", "unknown"),
                "completed_cycles": state.get("completed_cycles", 0),
                "requested_cycles": state.get("requested_cycles", (run.get("config") or {}).get("max_cycles", 0)),
                "actions_executed": state.get("actions_executed", 0),
                "seed": state.get("seed", (run.get("config") or {}).get("seed", 0)),
                "started_at_local": run.get("started_at_local", "unknown"),
                "finished_at_local": state.get("finished_at_local", "unknown"),
                "last_message": state.get("last_message", "unknown"),
            })
        return scenarios

    def _history_build_recent_scenarios_text(self, scenarios):
        lines = ["Recent scenario runs", "=" * 72]
        if not scenarios:
            lines.append("No scenario runs found yet.")
            return "\n".join(lines)
        for idx, record in enumerate(scenarios, 1):
            lines.extend([
                f"[{idx}] {record['run_id']}",
                f"  status              : {record['status']}",
                f"  scenario            : {record['scenario_type']} | target={record['target_group']}",
                f"  cycles / actions    : {record['completed_cycles']}/{record['requested_cycles']} | actions={record['actions_executed']}",
                f"  started / finished  : {record['started_at_local']}  ->  {record['finished_at_local']}",
                f"  seed                : {record['seed'] or 'random'}",
                f"  last message        : {record['last_message']}",
                f"  run dir             : {record['run_dir']}",
                "",
            ])
        return "\n".join(lines).rstrip()

    def update_history_panel(self):
        if not hasattr(self, 'history_overview_view'):
            return
        telemetry_state = self._history_load_latest_telemetry_state()
        telemetry_sessions = self._history_list_recent_telemetry_data(limit=8)
        scenarios = self._history_build_recent_scenarios_data()
        latest_kpis = self._history_compute_run_kpis(scenarios[0], telemetry_sessions) if scenarios else None
        self.history_overview_view.setPlainText(self._history_build_overview_text(telemetry_state, scenarios))
        self.history_fleet_view.setPlainText(self._history_compute_fleet_summary_text((telemetry_state or {}).get('session_dir')))
        self.history_latest_run_view.setPlainText(self._history_build_latest_run_kpis_text(latest_kpis))
        self.history_router_view.setPlainText(self._history_router_churn_summary((telemetry_state or {}).get('session_dir')))
        self.history_comparison_view.setPlainText(self._history_build_comparison_text(scenarios, telemetry_sessions))
        self.history_telemetry_view.setPlainText(self._history_build_recent_telemetry_text(telemetry_sessions))
        self.history_scenarios_view.setPlainText(self._history_build_recent_scenarios_text(scenarios))

    def build_right_panel(self):
        panel = QFrame()
        panel.setObjectName("SidePanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.router_title = QLabel("No Router Selected")
        self.router_title.setStyleSheet("font-size:22px;font-weight:800;color:#f8fafc;")
        header.addWidget(self.router_title)
        header.addStretch(1)

        self.btn_open_console = QPushButton("Open Console")
        header.addWidget(self.btn_open_console)
        layout.addLayout(header)

        action_row = QHBoxLayout()
        self.btn_selected_start = QPushButton("Start Router")
        self.btn_selected_stop = QPushButton("Stop Router")
        self.btn_selected_restart = QPushButton("Restart Router")
        action_row.addWidget(self.btn_selected_start)
        action_row.addWidget(self.btn_selected_stop)
        action_row.addWidget(self.btn_selected_restart)
        layout.addLayout(action_row)

        self.tabs = QTabWidget()
        self.summary_view = QPlainTextEdit()
        self.summary_view.setReadOnly(True)
        self.config_view = QPlainTextEdit()
        self.config_view.setReadOnly(True)
        self.logs_view = QPlainTextEdit()
        self.logs_view.setReadOnly(True)
        self.telemetry_view = QPlainTextEdit()
        self.telemetry_view.setReadOnly(True)

        self.tabs.addTab(self.summary_view, "Router Details")
        self.tabs.addTab(self.config_view, "Configuration")
        self.tabs.addTab(self.logs_view, "System Logs")
        self.tabs.addTab(self.telemetry_view, "Telemetry")
        layout.addWidget(self.tabs, 1)

        self.btn_open_console.clicked.connect(self.open_selected_console)
        self.btn_selected_start.clicked.connect(lambda: self.run_selected_action("start"))
        self.btn_selected_stop.clicked.connect(lambda: self.run_selected_action("stop"))
        self.btn_selected_restart.clicked.connect(lambda: self.run_selected_action("restart"))
        self.tabs.currentChanged.connect(self.on_tab_changed)

        return panel

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: #081120;
                color: #e5edf9;
                font-family: Segoe UI, Inter, Arial;
                font-size: 13px;
            }
            QMainWindow, QFrame#CenterPanel {
                background: #081120;
            }
            QFrame#TopologyPanel {
                background: #09142a;
                border: 1px solid #1a2f53;
                border-radius: 14px;
            }
            QFrame#Header, QFrame#SidePanel, QFrame#RouterCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0c1730, stop:1 #0a1326);
                border: 1px solid #1a2a4a;
                border-radius: 18px;
            }
            QFrame#RouterCard[selected="true"] {
                border: 1px solid #3a6df7;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #102040, stop:1 #0c1830);
            }
            QLabel#HeaderTitle {
                font-size: 28px;
                font-weight: 900;
                color: #f8fbff;
            }
            QLabel#HeaderSubtitle {
                font-size: 12px;
                color: #8ea7d1;
            }
            QLabel#StatPill {
                background: #09142a;
                border: 1px solid #193157;
                border-radius: 14px;
                padding: 10px 12px;
            }
            QLabel#CardTitle {
                font-size: 20px;
                font-weight: 800;
                color: #f8fbff;
            }
            QGroupBox {
                border: 1px solid #22385e;
                border-radius: 14px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: 800;
                color: #f8fbff;
                background: #09142a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QPushButton {
                background: #2b5ce6;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 12px;
                font-weight: 800;
                min-height: 20px;
            }
            QPushButton:hover {
                background: #3a6df7;
            }
            QPushButton:pressed {
                background: #2147b8;
            }
            QPushButton:disabled {
                background: #334155;
                color: #94a3b8;
            }
            QSpinBox, QPlainTextEdit, QTabWidget::pane {
                background: #020915;
                border: 1px solid #1a2f53;
                border-radius: 12px;
                color: #e5edf9;
                selection-background-color: #2b5ce6;
            }
            QSpinBox {
                padding: 8px;
                min-height: 22px;
            }
            QPlainTextEdit {
                padding: 10px;
                font-family: Consolas, "Courier New", monospace;
            }
            QTabBar::tab {
                background: #09142a;
                color: #c8d4ea;
                border: 1px solid #1a2f53;
                padding: 10px 14px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #2b5ce6;
                color: white;
            }
            QScrollArea {
                border: none;
            }
            QSplitter::handle {
                background: #10203c;
                width: 6px;
            }
        """)

    def start_monitor(self):
        self.monitor = MonitorThread(self)
        self.monitor.snapshot_ready.connect(self.apply_snapshot)
        self.monitor.error_signal.connect(self.show_nonblocking_error)
        self.monitor.start()

    def closeEvent(self, event):
        try:
            if hasattr(self, "scenario_thread") and self.scenario_thread and self.scenario_thread.isRunning():
                self.scenario_thread.stop()
                self.scenario_thread.wait(3000)
        except Exception:
            pass
        try:
            if hasattr(self, "measurement_thread") and self.measurement_thread and self.measurement_thread.isRunning():
                self.measurement_thread.stop()
                self.measurement_thread.wait(3000)
        except Exception:
            pass
        try:
            if hasattr(self, "campaign_thread") and self.campaign_thread and self.campaign_thread.isRunning():
                self.campaign_thread.stop()
                self.campaign_thread.wait(3000)
        except Exception:
            pass
        try:
            if hasattr(self, "monitor") and self.monitor.isRunning():
                self.monitor.stop()
                self.monitor.wait(1500)
        except Exception:
            pass
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow_router_cards()

    def show_nonblocking_error(self, text):
        self.info_line.setText(f"Monitor warning: {text}")

    def refresh_deployment_log(self):
        current = deployment_log_tail()
        if self.deployment_log.toPlainText() != current:
            self.deployment_log.setPlainText(current)
            cursor = self.deployment_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.End if PYQT_VER == 6 else cursor.End)
            self.deployment_log.setTextCursor(cursor)

    def is_task_running(self):
        return bool(
            (self.action_thread and self.action_thread.isRunning()) or
            (self.deploy_thread and self.deploy_thread.isRunning()) or
            (self.scenario_thread and self.scenario_thread.isRunning()) or
            (self.measurement_thread and self.measurement_thread.isRunning()) or
            (self.campaign_thread and self.campaign_thread.isRunning())
        )

    def set_busy(self, busy):
        self._busy = bool(busy)
        widgets = [
            self.btn_stop_emulator, self.btn_destroy,
            self.btn_start_all, self.btn_stop_all, self.btn_restart_all,
            self.btn_selected_start, self.btn_selected_stop, self.btn_selected_restart,
            self.btn_refresh, self.btn_measurement_start if hasattr(self, "btn_measurement_start") else self.btn_refresh,
            self.btn_measurement_refresh if hasattr(self, "btn_measurement_refresh") else self.btn_refresh,
        ]
        for w in widgets:
            w.setEnabled(not busy)

        for card in self.router_cards.values():
            card.set_actions_enabled(not busy)
        if hasattr(self, "builder_panel"):
            self.builder_panel.set_busy(busy)
        self.update_scenario_panel()
        self.update_campaign_panel()

    def sync_deploy_spinboxes(self):
        return

    def current_requested_topology(self):
        return (self.requested_router_count, self.requested_floodfill_count)

    def set_topology_inputs(self, routers, floodfill):
        routers = max(2, safe_int(routers, 2))
        floodfill = max(0, min(safe_int(floodfill, 0), routers))
        self.requested_router_count = routers
        self.requested_floodfill_count = floodfill
        self._last_applied_topology = (routers, floodfill)

    def on_topology_input_changed(self, *_args):
        return

    def on_builder_summary_changed(self, routers, floodfill):
        if self._busy:
            return
        if routers >= 2:
            self.set_topology_inputs(routers, max(0, floodfill))

    def start_topology_builder_deploy(self, json_path, routers_tsv, subnets_tsv, routers, floodfill):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, "Another task is already running.")
            return
        if not os.path.exists(routers_tsv) or not os.path.exists(subnets_tsv):
            QMessageBox.critical(self, APP_NAME, "Generated TSV files were not found.")
            return
        self._pending_requested_topology = (max(2, safe_int(routers, 2)), max(0, min(safe_int(floodfill, 0), max(2, safe_int(routers, 2)))))
        self._pending_requested_tsv = (json_path, routers_tsv, subnets_tsv)
        self._topology_sync_enabled = True
        self.set_busy(True)
        self.deploy_status.setText("Running topology deployment from Builder...")

        deployment_log_reset()
        deployment_log_write(f"[{now_display()}] [Builder Deploy] Deployment requested.")
        deployment_log_write(f"[{now_display()}] [Builder Deploy] Topology JSON: {json_path}")
        deployment_log_write(f"[{now_display()}] [Builder Deploy] Routers TSV: {routers_tsv}")
        deployment_log_write(f"[{now_display()}] [Builder Deploy] Subnets TSV: {subnets_tsv}")
        deployment_log_write(f"[{now_display()}] [Builder Deploy] Requested routers={routers}, floodfill={floodfill}")
        deployment_log_write("")

        self.deploy_thread = DeployThread("deploy", routers, floodfill, routers_tsv=routers_tsv, subnets_tsv=subnets_tsv, parent=self)
        self.deploy_thread.line.connect(lambda line: self.deploy_status.setText(line[-140:] if len(line) > 140 else line))
        self.deploy_thread.done.connect(self.on_deploy_done)
        self.deploy_thread.failed.connect(self.on_deploy_failed)
        self.deploy_thread.start()
        self.center_tabs.setCurrentWidget(self.topology_panel)

    def clear_router_views(self, message="No router selected."):
        self.router_title.setText("No router selected")
        self.summary_view.setPlainText(message)
        self.config_view.setPlainText(message)
        self.logs_view.setPlainText(message)
        self.update_telemetry_view()
        self.btn_open_console.setEnabled(False)

    def reset_detail_cache(self):
        self._detail_cache = {
            "router_id": None,
            "config_text": "",
            "config_loaded_at": 0.0,
            "logs_text": "",
            "logs_loaded_at": 0.0,
        }

    def refresh_now(self):
        try:
            snapshot = collect_router_snapshot()
            snapshot["_snapshot_source"] = "manual"
            self.apply_snapshot(snapshot)
        except Exception as e:
            self.show_nonblocking_error(str(e))

    def reflow_router_cards(self):
        if not hasattr(self, "router_grid"):
            return

        viewport_width = self.router_scroll.viewport().width() if hasattr(self, "router_scroll") else 0

        if viewport_width <= 0:
            cols = 2
        else:
            usable_width = viewport_width - (2 * CARD_GRID_MARGIN)
            cols = max(1, (usable_width + CARD_GRID_SPACING) // (CARD_MIN_WIDTH + CARD_GRID_SPACING))

        self._last_grid_cols = cols
        cards = [self.router_cards[r["id"]] for r in self.snapshot.get("routers", []) if r["id"] in self.router_cards]

        for i in reversed(range(self.router_grid.count())):
            item = self.router_grid.takeAt(i)
            if item and item.widget():
                item.widget().setParent(self.router_grid_wrapper)

        for idx, card in enumerate(cards):
            self.router_grid.addWidget(card, idx // cols, idx % cols)
            card.show()

        for col in range(cols):
            self.router_grid.setColumnStretch(col, 1)

        for col in range(cols, max(self._last_grid_cols, cols) + 6):
            self.router_grid.setColumnStretch(col, 0)
    
    def apply_snapshot(self, snapshot):
        self.snapshot = snapshot
        self.telemetry.process_snapshot(snapshot)

        total = snapshot.get("total", 0)
        active = snapshot.get("active", 0)
        stopped = snapshot.get("stopped", 0)
        failed = snapshot.get("failed", 0)
        floodfill = snapshot.get("floodfill_count", 0)
        base = snapshot.get("base") or "not found"
        base_name = os.path.basename(base) if snapshot.get("base_available") and base != "not found" else "not found"

        self.stat_total.set_value(total)
        self.stat_active.set_value(active)
        self.stat_stopped.set_value(stopped)
        self.stat_failed.set_value(failed)
        self.stat_ff.set_value(floodfill)
        self.stat_base.set_value(base_name)

        telemetry_suffix = f"  |  Telemetry: {self.telemetry.sample_count} fleet / {self.telemetry.event_count} events"
        self.info_line.setText(f"Snapshot: {snapshot.get('generated_at', 'unknown')}  |  Base: {base}  |  Poll: {POLL_SECONDS:.1f}s{telemetry_suffix}")

        detected_topology = None
        if total >= 2:
            detected_topology = (total, max(0, floodfill))

        if detected_topology:
            if self._pending_requested_topology and detected_topology == self._pending_requested_topology:
                self._topology_sync_enabled = True
                self._pending_requested_topology = None
            if self._topology_sync_enabled and not self._busy:
                self.set_topology_inputs(*detected_topology)
            else:
                self._last_applied_topology = detected_topology

        routers = snapshot.get("routers", [])
        ids_now = set()

        for router in routers:
            rid = router["id"]
            ids_now.add(rid)

            if rid not in self.router_cards:
                card = RouterCard(router)
                card.selected.connect(self.select_router)
                card.action_requested.connect(self.run_router_action)
                card.open_console_requested.connect(self.open_console_by_id)
                self.router_cards[rid] = card

            self.router_cards[rid].update_data(router)
            self.router_cards[rid].set_selected(self.selected_router_id == rid)
            self.router_cards[rid].set_actions_enabled(not self._busy)

        for rid in list(self.router_cards.keys()):
            if rid not in ids_now:
                card = self.router_cards.pop(rid)
                card.setParent(None)
                card.deleteLater()

        self.reflow_router_cards()
        self.topology_panel.update_topology(snapshot, self.selected_router_id)
        if hasattr(self, "map_panel"):
            self.map_panel.update_map(snapshot, self.selected_router_id, analytics_payload=self._phase3_map_overlay_payload())
        self.update_telemetry_view()
        self.update_history_panel()

        if not snapshot.get("base_available"):
            self.selected_router_id = None
            self.reset_detail_cache()
            self.topology_panel.update_topology(snapshot, None)
            self.clear_router_views("No active i2p-testnet-* folder detected.")
            return

        if not routers:
            self.selected_router_id = None
            self.reset_detail_cache()
            self.topology_panel.update_topology(snapshot, None)
            self.clear_router_views("Testnet base exists, but no router directories were found.")
            return

        if not self.selected_router_id or not self.find_router(self.selected_router_id):
            self.select_router(routers[0]["id"])
        else:
            self.update_right_panel()

    def find_router(self, router_id):
        for router in self.snapshot.get("routers", []):
            if router["id"] == str(router_id):
                return router
        return None

    def select_router(self, router_id):
        self.selected_router_id = str(router_id)
        for rid, card in self.router_cards.items():
            card.set_selected(rid == self.selected_router_id)
        if hasattr(self, "topology_panel"):
            self.topology_panel.update_topology(self.snapshot, self.selected_router_id)
        if hasattr(self, "map_panel"):
            self.map_panel.update_map(self.snapshot, self.selected_router_id, analytics_payload=self._phase3_map_overlay_payload())
        self.reset_detail_cache()
        self.update_right_panel(force=True)
        self.update_telemetry_view()
        self.update_history_panel()

    def on_tab_changed(self, _index):
        self.update_right_panel(force=False)
        self.update_telemetry_view()
        self.update_history_panel()

    def update_telemetry_view(self):
        if hasattr(self, "telemetry_view"):
            self.telemetry_view.setPlainText(self.telemetry.build_view_text(self.selected_router_id))

    def update_right_panel(self, force=False):
        router = self.find_router(self.selected_router_id)
        if not router:
            self.clear_router_views("Router not found in current snapshot.")
            return

        self.btn_open_console.setEnabled(bool(router.get("console_url")))
        self.router_title.setText(f"{router['name']} · {router['status'].upper()}")
        self.summary_view.setPlainText(build_summary_text(router))

        now_ts = time.time()
        selected_tab = self.tabs.currentIndex()

        if self._detail_cache["router_id"] != router["id"]:
            self.reset_detail_cache()
            self._detail_cache["router_id"] = router["id"]

        if selected_tab == 1:
            if force or not self._detail_cache["config_text"] or now_ts - self._detail_cache["config_loaded_at"] >= CONFIG_REFRESH_SECONDS:
                self._detail_cache["config_text"] = read_file_safe(router["config_path"], max_lines=500)
                self._detail_cache["config_loaded_at"] = now_ts
            self.config_view.setPlainText(self._detail_cache["config_text"])
        elif not self._detail_cache["config_text"]:
            self.config_view.setPlainText("Open the Config tab to load the latest router configuration.")

        if selected_tab == 2:
            if force or not self._detail_cache["logs_text"] or now_ts - self._detail_cache["logs_loaded_at"] >= LOG_REFRESH_SECONDS:
                self._detail_cache["logs_text"] = build_logs_view(router)
                self._detail_cache["logs_loaded_at"] = now_ts
            self.logs_view.setPlainText(self._detail_cache["logs_text"])
        elif not self._detail_cache["logs_text"]:
            self.logs_view.setPlainText("Open the Logs tab to load the latest service and router logs.")

    def open_console_by_id(self, router_id):
        router = self.find_router(router_id)
        if not router:
            QMessageBox.warning(self, APP_NAME, "Router not found.")
            return
        url = router.get("console_url")
        if not url:
            QMessageBox.warning(self, APP_NAME, "Router console URL is not available.")
            return
        QDesktopServices.openUrl(QUrl(url))

    def open_selected_console(self):
        if not self.selected_router_id:
            QMessageBox.warning(self, APP_NAME, "Select a router first.")
            return
        self.open_console_by_id(self.selected_router_id)

    def append_scenario_log(self, text):
        if not hasattr(self, "scenario_log"):
            return
        existing = self.scenario_log.toPlainText().splitlines()
        existing.append(str(text))
        existing = existing[-SCENARIO_LOG_LINE_LIMIT:]
        self.scenario_log.setPlainText("\n".join(existing))
        cursor = self.scenario_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End if PYQT_VER == 6 else cursor.End)
        self.scenario_log.setTextCursor(cursor)

    def append_campaign_log(self, text):
        if not hasattr(self, "campaign_log"):
            return
        existing = self.campaign_log.toPlainText().splitlines()
        existing.append(str(text))
        existing = existing[-SCENARIO_LOG_LINE_LIMIT:]
        self.campaign_log.setPlainText("\n".join(existing))

        cursor = self.campaign_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End if PYQT_VER == 6 else cursor.End)
        self.campaign_log.setTextCursor(cursor)

    def update_scenario_target_mode_ui(self):
        target_mode = self.scenario_target_mode_combo.currentData() if hasattr(self, "scenario_target_mode_combo") else "random_pool"
        selected_mode = str(target_mode or "random_pool") == "selected_routers"
        if hasattr(self, "scenario_selected_routers"):
            self.scenario_selected_routers.setEnabled(selected_mode)
            if selected_mode:
                self.scenario_selected_routers.setPlaceholderText("e.g. 2,4,7")
            else:
                self.scenario_selected_routers.setPlaceholderText("used only in selected-routers mode")

    def get_selected_scenario_preset(self):
        preset_id = str((self.scenario_preset_combo.currentData() if hasattr(self, "scenario_preset_combo") else "custom") or "custom")
        if preset_id == "custom":
            return preset_id, {}
        return preset_id, dict(SCENARIO_PRESETS.get(preset_id, {}) or {})

    def _default_experiment_label(self, scenario_type, target_group, preset_id=None, preset=None):
        if preset and preset.get("experiment_label"):
            return str(preset.get("experiment_label"))
        return filesystem_safe_name(f"{scenario_type}_{target_group}")

    def apply_selected_scenario_preset(self):
        preset_id, preset = self.get_selected_scenario_preset()
        if not preset:
            if hasattr(self, "scenario_target_mode_combo"):
                combo_set_current_data(self.scenario_target_mode_combo, "random_pool")
            if hasattr(self, "scenario_selected_routers"):
                self.scenario_selected_routers.clear()
            if hasattr(self, "scenario_seed_input"):
                self.scenario_seed_input.clear()
            if hasattr(self, "scenario_experiment_label") and not self.scenario_experiment_label.text().strip():
                self.scenario_experiment_label.setText(
                    self._default_experiment_label(
                        self.scenario_type_combo.currentData() if hasattr(self, "scenario_type_combo") else "random_stop_start",
                        self.scenario_target_combo.currentData() if hasattr(self, "scenario_target_combo") else "non_floodfill",
                    )
                )
            self.update_scenario_target_mode_ui()
            self.update_scenario_panel()
            self.update_campaign_panel()
            return

        combo_set_current_data(self.scenario_type_combo, preset.get("scenario_type", "random_stop_start"))
        combo_set_current_data(self.scenario_target_combo, preset.get("target_group", "non_floodfill"))
        if hasattr(self, "scenario_min_interval"):
            self.scenario_min_interval.setValue(float(preset.get("min_interval_seconds", SCENARIO_DEFAULT_MIN_INTERVAL)))
        if hasattr(self, "scenario_max_interval"):
            self.scenario_max_interval.setValue(float(preset.get("max_interval_seconds", SCENARIO_DEFAULT_MAX_INTERVAL)))
        if hasattr(self, "scenario_downtime"):
            self.scenario_downtime.setValue(float(preset.get("downtime_seconds", SCENARIO_DEFAULT_DOWNTIME)))
        if hasattr(self, "scenario_cycles"):
            self.scenario_cycles.setValue(int(preset.get("max_cycles", SCENARIO_DEFAULT_MAX_CYCLES)))
        if hasattr(self, "scenario_target_mode_combo"):
            combo_set_current_data(self.scenario_target_mode_combo, preset.get("target_mode", "random_pool"))
        if hasattr(self, "scenario_selected_routers"):
            selected_text = ", ".join(str(rid) for rid in (preset.get("selected_router_ids") or []))
            self.scenario_selected_routers.setText(selected_text)
        if hasattr(self, "scenario_seed_input"):
            seed = preset.get("seed")
            self.scenario_seed_input.setText("" if seed in (None, 0, "0", "") else str(seed))
        if hasattr(self, "campaign_probe_interval"):
            self.campaign_probe_interval.setValue(float(preset.get("campaign_probe_interval_seconds", 15.0)))
        if hasattr(self, "campaign_post_settle"):
            self.campaign_post_settle.setValue(float(preset.get("post_settle_seconds", 8.0)))
        if hasattr(self, "campaign_cycle_probe_combo"):
            combo_set_current_data(self.campaign_cycle_probe_combo, bool(preset.get("probe_after_each_cycle", True)))
        if hasattr(self, "scenario_experiment_label"):
            self.scenario_experiment_label.setText(str(preset.get("experiment_label") or preset_id))
        self.update_scenario_target_mode_ui()
        self.update_scenario_panel()
        self.update_campaign_panel()

    def build_scenario_config(self):
        routers = []
        for router in self.snapshot.get("routers", []):
            routers.append({
                "id": str(router.get("id")),
                "name": router.get("name", f"Router {router.get('id')}") ,
                "floodfill": str(router.get("floodfill", "")).lower() == "true",
            })
        preset_id, preset = self.get_selected_scenario_preset()
        scenario_type = self.scenario_type_combo.currentData() if hasattr(self, "scenario_type_combo") else "random_stop_start"
        target_group = self.scenario_target_combo.currentData() if hasattr(self, "scenario_target_combo") else "non_floodfill"
        target_mode = self.scenario_target_mode_combo.currentData() if hasattr(self, "scenario_target_mode_combo") else "random_pool"
        min_interval = float(self.scenario_min_interval.value()) if hasattr(self, "scenario_min_interval") else SCENARIO_DEFAULT_MIN_INTERVAL
        max_interval = float(self.scenario_max_interval.value()) if hasattr(self, "scenario_max_interval") else SCENARIO_DEFAULT_MAX_INTERVAL
        downtime = float(self.scenario_downtime.value()) if hasattr(self, "scenario_downtime") else SCENARIO_DEFAULT_DOWNTIME
        max_cycles = int(self.scenario_cycles.value()) if hasattr(self, "scenario_cycles") else SCENARIO_DEFAULT_MAX_CYCLES
        selected_text = self.scenario_selected_routers.text().strip() if hasattr(self, "scenario_selected_routers") else ""
        selected_router_ids = []
        seen_router_ids = set()
        for token in re.split(r"[\s,;]+", selected_text):
            rid = str(token or "").strip()
            if not rid or rid in seen_router_ids:
                continue
            seen_router_ids.add(rid)
            selected_router_ids.append(rid)
        seed_text = self.scenario_seed_input.text().strip() if hasattr(self, "scenario_seed_input") else ""
        try:
            seed_value = int(seed_text) if seed_text else 0
        except Exception:
            seed_value = 0
        experiment_label = self.scenario_experiment_label.text().strip() if hasattr(self, "scenario_experiment_label") else ""
        if not experiment_label:
            experiment_label = self._default_experiment_label(str(scenario_type or "random_stop_start"), str(target_group or "non_floodfill"), preset_id=preset_id, preset=preset)
        return {
            "scenario_type": str(scenario_type or "random_stop_start"),
            "target_group": str(target_group or "non_floodfill"),
            "target_mode": str(target_mode or "random_pool"),
            "selected_router_ids": selected_router_ids,
            "min_interval_seconds": min(min_interval, max_interval),
            "max_interval_seconds": max(min_interval, max_interval),
            "downtime_seconds": downtime,
            "max_cycles": max_cycles,
            "seed": seed_value if seed_value > 0 else None,
            "routers": routers,
            "testnet_base": self.snapshot.get("base"),
            "scenario_preset_id": None if preset_id == "custom" else preset_id,
            "scenario_preset_name": preset.get("name") if preset else "Custom",
            "experiment_label": experiment_label,
        }

    def build_campaign_config(self):
        scenario_config = self.build_scenario_config()
        measurement_template = self.build_measurement_config()
        measurement_template["experiment_label"] = scenario_config.get("experiment_label")
        measurement_template["scenario_preset_id"] = scenario_config.get("scenario_preset_id")
        measurement_template["scenario_preset_name"] = scenario_config.get("scenario_preset_name")
        probe_interval = float(self.campaign_probe_interval.value()) if hasattr(self, "campaign_probe_interval") else 15.0
        post_settle = float(self.campaign_post_settle.value()) if hasattr(self, "campaign_post_settle") else 8.0
        probe_after_each_cycle = bool(self.campaign_cycle_probe_combo.currentData()) if hasattr(self, "campaign_cycle_probe_combo") else True
        return {
            "testnet_base": self.snapshot.get("base"),
            "scenario_config": scenario_config,
            "measurement_template": measurement_template,
            "probe_interval_seconds": max(0.0, probe_interval),
            "probe_after_each_cycle": probe_after_each_cycle,
            "post_settle_seconds": max(0.0, post_settle),
            "experiment_label": scenario_config.get("experiment_label"),
            "scenario_preset_id": scenario_config.get("scenario_preset_id"),
            "scenario_preset_name": scenario_config.get("scenario_preset_name"),
        }

    def update_scenario_panel(self):
        if not hasattr(self, "scenario_summary"):
            return
        state = dict(self.scenario_state or {})
        status = state.get("status", "idle")
        selected_router_ids = list(state.get("selected_router_ids") or [])
        if not selected_router_ids and hasattr(self, "scenario_selected_routers"):
            selected_router_ids = [part.strip() for part in re.split(r"[\s,;]+", self.scenario_selected_routers.text().strip()) if part.strip()]
        run_dir = state.get("run_dir") or "No active run"
        run_id = state.get("run_id") or "not started"
        requested = safe_int(state.get("requested_cycles", 0), 0)
        completed = safe_int(state.get("completed_cycles", 0), 0)
        actions_executed = safe_int(state.get("actions_executed", 0), 0)
        lines = [
            f"Status              : {status}",
            f"Run ID              : {run_id}",
            f"Run directory       : {run_dir}",
            f"Experiment label    : {state.get('experiment_label') or (self.scenario_experiment_label.text().strip() if hasattr(self, 'scenario_experiment_label') else 'n/a')}",
            f"Scenario preset     : {state.get('scenario_preset_name') or 'Custom'}",
            f"Scenario type       : {state.get('scenario_type', self.scenario_type_combo.currentData() if hasattr(self, 'scenario_type_combo') else 'random_stop_start')}",
            f"Target group        : {state.get('target_group', self.scenario_target_combo.currentData() if hasattr(self, 'scenario_target_combo') else 'non_floodfill')}",
            f"Target mode         : {state.get('target_mode', self.scenario_target_mode_combo.currentData() if hasattr(self, 'scenario_target_mode_combo') else 'random_pool')}",
            f"Selected routers    : {', '.join(selected_router_ids) if selected_router_ids else 'none'}",
            f"Completed cycles    : {completed} / {requested}",
            f"Actions executed    : {actions_executed}",
            f"Seed                : {state.get('seed', 0) or 'random'}",
        ]
        remaining = state.get("remaining_seconds")
        if isinstance(remaining, (int, float)):
            lines.append(f"Remaining wait      : {format_seconds_brief(remaining)}")
        router_name = state.get("router_name") or ""
        if router_name:
            lines.append(f"Current router      : {router_name}")
        action = state.get("action")
        if action:
            lines.append(f"Current action      : {action}")
        lines.extend([
            "",
            f"Last message        : {state.get('last_message', 'No scenario messages yet.')}",
        ])
        self.scenario_summary.setPlainText("\n".join(lines))

        running = bool(self.scenario_thread and self.scenario_thread.isRunning())
        if hasattr(self, "btn_scenario_start"):
            self.btn_scenario_start.setEnabled((not self._busy) and not running)
        if hasattr(self, "btn_scenario_stop"):
            self.btn_scenario_stop.setEnabled(running)

    def update_campaign_panel(self):
        if not hasattr(self, "campaign_summary"):
            return
        state = dict(self.campaign_state or {})
        summary = dict(state.get("summary") or {})
        status = state.get("status", "idle")
        lines = [
            f"Status                 : {status}",
            f"Run ID                 : {state.get('run_id') or 'not started'}",
            f"Run directory          : {state.get('run_dir') or 'No active run'}",
            f"Experiment label       : {state.get('experiment_label') or (self.scenario_experiment_label.text().strip() if hasattr(self, 'scenario_experiment_label') else 'n/a')}",
            f"Scenario preset        : {state.get('scenario_preset_name') or 'Custom'}",
            f"Scenario run           : {state.get('scenario_run_id') or 'n/a'}",
            f"Baseline probe         : {state.get('baseline_run_id') or 'n/a'}",
            f"Final probe            : {state.get('final_run_id') or 'n/a'}",
            f"Interim probes         : {safe_int(state.get('interim_measurements', 0), 0)}",
            f"Cycle-trigger probes   : {safe_int(state.get('cycle_trigger_measurements', 0), 0)}",
            f"Periodic probes        : {safe_int(state.get('periodic_measurements', 0), 0)}",
            f"Scenario type          : {state.get('scenario_type') or (self.scenario_type_combo.currentData() if hasattr(self, 'scenario_type_combo') else 'random_stop_start')}",
            f"Scenario target        : {state.get('scenario_target_group') or (self.scenario_target_combo.currentData() if hasattr(self, 'scenario_target_combo') else 'non_floodfill')}",
            f"Measurement target     : {state.get('measurement_target_group') or (self.measurement_target_combo.currentData() if hasattr(self, 'measurement_target_combo') else 'active_all')}",
            f"Fetch timeout          : {state.get('fetch_timeout', MEASUREMENT_FETCH_TIMEOUT_DEFAULT)} s",
            f"Periodic interval      : {state.get('probe_interval_seconds', 0.0)} s",
            f"Probe after each cycle : {'yes' if state.get('probe_after_each_cycle', True) else 'no'}",
            f"Post-scenario settle   : {state.get('post_settle_seconds', 0.0)} s",
            "",
        ]
        if summary:
            lines.extend([
                "Campaign summary",
                "----------------",
                f"Scenario status        : {summary.get('scenario_status', 'unknown')}",
                f"Baseline client proxy  : {summary.get('baseline_client_proxy_success', 0)}",
                f"Final client proxy     : {summary.get('final_client_proxy_success', 0)}",
                f"Baseline netDb success : {summary.get('baseline_netdb_success', 0)}",
                f"Final netDb success    : {summary.get('final_netdb_success', 0)}",
                f"Baseline root success  : {summary.get('baseline_root_success', 0)}",
                f"Final root success     : {summary.get('final_root_success', 0)}",
                f"Δ client proxy success : {summary.get('delta_client_proxy_success', 0)}",
                f"Δ netDb success        : {summary.get('delta_netdb_success', 0)}",
                f"Δ root success         : {summary.get('delta_root_success', 0)}",
            ])
            if summary.get('baseline_mean_proxy_latency_ms') is not None or summary.get('final_mean_proxy_latency_ms') is not None:
                lines.append(f"Proxy latency baseline/final : {summary.get('baseline_mean_proxy_latency_ms')} ms / {summary.get('final_mean_proxy_latency_ms')} ms")
            worst = summary.get('worst_interim') or {}
            if worst:
                worst_summary = worst.get('summary') or {}
                lines.extend([
                    "",
                    "Worst interim snapshot",
                    "----------------------",
                    f"Stage                  : {worst.get('stage', 'unknown')}",
                    f"Run ID                 : {worst.get('run_id', 'unknown')}",
                    f"Client proxy success   : {worst_summary.get('client_proxy_success', 0)}",
                    f"netDb success          : {worst_summary.get('netdb_success', 0)}",
                    f"Mean proxy latency     : {worst_summary.get('mean_client_proxy_latency_ms')}",
                ])
        lines.extend([
            "",
            f"Last message           : {state.get('last_message', 'No campaign messages yet.')}",
        ])
        self.campaign_summary.setPlainText("\n".join(lines))

        running = bool(self.campaign_thread and self.campaign_thread.isRunning())
        if hasattr(self, "btn_campaign_start"):
            self.btn_campaign_start.setEnabled((not self._busy) and not running)
        if hasattr(self, "btn_campaign_stop"):
            self.btn_campaign_stop.setEnabled(running)

    def start_campaign_run(self):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, "Another task is already running.")
            return
        if not self.snapshot.get("base_available") or not self.snapshot.get("base"):
            QMessageBox.warning(self, APP_NAME, "No active testnet base detected. Start or deploy the emulator first.")
            return
        if not self.snapshot.get("routers"):
            QMessageBox.warning(self, APP_NAME, "No routers detected in the current snapshot.")
            return
        config = self.build_campaign_config()
        self.campaign_log.setPlainText("")
        self.append_campaign_log(f"[{now_display()}] Preparing scenario campaign...")
        self.campaign_state = {
            "status": "preparing",
            "run_id": None,
            "run_dir": None,
            "scenario_run_id": None,
            "baseline_run_id": None,
            "final_run_id": None,
            "interim_measurements": 0,
            "cycle_trigger_measurements": 0,
            "periodic_measurements": 0,
            "experiment_label": config.get("experiment_label"),
            "scenario_preset_id": config.get("scenario_preset_id"),
            "scenario_preset_name": config.get("scenario_preset_name"),
            "scenario_type": (config.get("scenario_config") or {}).get("scenario_type"),
            "scenario_target_group": (config.get("scenario_config") or {}).get("target_group"),
            "measurement_target_group": (config.get("measurement_template") or {}).get("target_group"),
            "fetch_timeout": (config.get("measurement_template") or {}).get("fetch_timeout"),
            "probe_interval_seconds": config.get("probe_interval_seconds", 0.0),
            "probe_after_each_cycle": config.get("probe_after_each_cycle", True),
            "post_settle_seconds": config.get("post_settle_seconds", 0.0),
            "last_message": "Preparing scenario campaign...",
            "summary": {},
        }
        self.update_campaign_panel()
        self.set_busy(True)
        self.deploy_status.setText("Running scenario campaign...")
        self.campaign_thread = ScenarioCampaignThread(config, self)
        self.campaign_thread.log_line.connect(self.append_campaign_log)
        self.campaign_thread.status_changed.connect(lambda msg: self.deploy_status.setText(msg[-140:] if len(msg) > 140 else msg))
        self.campaign_thread.started_run.connect(self.on_campaign_started)
        self.campaign_thread.progress.connect(self.on_campaign_progress)
        self.campaign_thread.finished_run.connect(self.on_campaign_finished)
        self.campaign_thread.failed_run.connect(self.on_campaign_failed)
        self.campaign_thread.refresh_requested.connect(self._handle_scenario_refresh_request)
        self.campaign_thread.action_intent.connect(self._handle_scenario_action_intent)
        self.campaign_thread.start()
        if hasattr(self, "center_tabs") and hasattr(self, "scenario_panel"):
            self.center_tabs.setCurrentWidget(self.scenario_panel)

    def stop_campaign_run(self):
        if not (self.campaign_thread and self.campaign_thread.isRunning()):
            return
        self.campaign_thread.stop()
        self.append_campaign_log(f"[{now_display()}] Stop requested; the campaign will exit after the current sub-step completes.")
        self.campaign_state["status"] = "stopping"
        self.campaign_state["last_message"] = "Stop requested; waiting for the current campaign step to finish."
        self.deploy_status.setText("Stopping scenario campaign...")
        self.update_campaign_panel()

    def on_campaign_started(self, manifest):
        self.campaign_state.update({
            "status": "running",
            "run_id": manifest.get("run_id"),
            "run_dir": manifest.get("run_dir"),
            "last_message": "Campaign started.",
        })
        self.update_campaign_panel()

    def on_campaign_progress(self, payload):
        self.campaign_state.update(payload or {})
        self.update_campaign_panel()

    def on_campaign_finished(self, payload):
        self.campaign_state.update(payload or {})
        self.campaign_state["last_message"] = (payload or {}).get("last_message", "Campaign finished.")
        self.set_busy(False)
        self.append_campaign_log(f"[{now_display()}] {self.campaign_state['last_message']}")
        self.deploy_status.setText(self.campaign_state["last_message"])
        self.campaign_thread = None
        self.refresh_now()
        self.update_campaign_panel()
        self.update_history_panel()

    def on_campaign_failed(self, message):
        self.campaign_state.update({
            "status": "failed",
            "last_message": str(message),
        })
        self.set_busy(False)
        self.append_campaign_log(f"[{now_display()}] Campaign failed: {message}")
        self.deploy_status.setText(f"Campaign failed: {message}")
        self.campaign_thread = None
        self.refresh_now()
        self.update_campaign_panel()
        self.update_history_panel()
        QMessageBox.critical(self, APP_NAME, message)

    def start_churn_scenario(self):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, "Another task is already running.")
            return
        if not self.snapshot.get("base_available") or not self.snapshot.get("base"):
            QMessageBox.warning(self, APP_NAME, "No active testnet base detected. Start or deploy the emulator first.")
            return
        if not self.snapshot.get("routers"):
            QMessageBox.warning(self, APP_NAME, "No routers detected in the current snapshot.")
            return

        config = self.build_scenario_config()
        self.scenario_log.setPlainText("")
        self.append_scenario_log(f"[{now_display()}] Preparing churn scenario...")
        self.scenario_state = {
            "status": "preparing",
            "run_id": None,
            "run_dir": None,
            "completed_cycles": 0,
            "requested_cycles": config.get("max_cycles", 0),
            "actions_executed": 0,
            "last_message": "Preparing churn scenario...",
            "experiment_label": config.get("experiment_label"),
            "scenario_preset_id": config.get("scenario_preset_id"),
            "scenario_preset_name": config.get("scenario_preset_name"),
            "scenario_type": config.get("scenario_type"),
            "target_group": config.get("target_group"),
            "target_mode": config.get("target_mode"),
            "selected_router_ids": list(config.get("selected_router_ids") or []),
            "seed": config.get("seed") or 0,
        }
        self.update_scenario_panel()
        self.update_history_panel()

        self.set_busy(True)
        self.deploy_status.setText("Running churn scenario...")
        self.scenario_thread = ChurnRunnerThread(config, self)
        self.scenario_thread.log_line.connect(self.append_scenario_log)
        self.scenario_thread.status_changed.connect(lambda msg: self.deploy_status.setText(msg))
        self.scenario_thread.started_run.connect(self.on_scenario_started)
        self.scenario_thread.progress.connect(self.on_scenario_progress)
        self.scenario_thread.finished_run.connect(self.on_scenario_finished)
        self.scenario_thread.failed_run.connect(self.on_scenario_failed)
        self.scenario_thread.refresh_requested.connect(self._handle_scenario_refresh_request)
        self.scenario_thread.action_intent.connect(self._handle_scenario_action_intent)
        self.scenario_thread.start()
        if hasattr(self, "center_tabs") and hasattr(self, "scenario_panel"):
            self.center_tabs.setCurrentWidget(self.scenario_panel)

    def stop_churn_scenario(self):
        if not (self.scenario_thread and self.scenario_thread.isRunning()):
            return
        self.scenario_thread.stop()
        self.append_scenario_log(f"[{now_display()}] Stop requested; current action will finish and the runner will exit cleanly.")
        self.scenario_state["status"] = "stopping"
        self.scenario_state["last_message"] = "Stop requested; waiting for the current action to finish."
        self.deploy_status.setText("Stopping churn scenario...")
        self.update_scenario_panel()
        self.update_history_panel()

    def _handle_scenario_action_intent(self, action, router_id, source):
        self.telemetry.note_router_action_intent(action, router_id, source=source)
        self.update_telemetry_view()
        self.update_history_panel()

    def _handle_scenario_refresh_request(self):
        self.refresh_now()
        QTimer.singleShot(1200, self.refresh_now)

    def on_scenario_started(self, manifest):
        self.scenario_state.update({
            "status": "running",
            "run_id": manifest.get("run_id"),
            "run_dir": manifest.get("run_dir"),
            "last_message": "Scenario started.",
        })
        self.update_scenario_panel()
        self.update_history_panel()

    def on_scenario_progress(self, payload):
        self.scenario_state.update(payload or {})
        self.update_scenario_panel()
        self.update_history_panel()

    def on_scenario_finished(self, summary):
        self.scenario_state.update(summary or {})
        self.scenario_state["last_message"] = summary.get("last_message", "Scenario finished.") if summary else "Scenario finished."
        self.scenario_state["router_id"] = None
        self.scenario_state["router_name"] = None
        self.scenario_state["action"] = None
        self.scenario_state["remaining_seconds"] = 0.0
        self.set_busy(False)
        self.deploy_status.setText(self.scenario_state["last_message"])
        self.append_scenario_log(f"[{now_display()}] {self.scenario_state['last_message']}")
        self.scenario_thread = None
        self.refresh_now()
        self.update_scenario_panel()
        self.update_history_panel()

    def on_scenario_failed(self, text):
        self.scenario_state.update({
            "status": "failed",
            "last_message": str(text),
            "router_id": None,
            "router_name": None,
            "action": None,
            "remaining_seconds": 0.0,
        })
        self.set_busy(False)
        self.deploy_status.setText(f"Scenario failed: {text}")
        self.append_scenario_log(f"[{now_display()}] Scenario failed: {text}")
        self.scenario_thread = None
        self.refresh_now()
        self.update_scenario_panel()
        self.update_history_panel()
        QMessageBox.critical(self, APP_NAME, text)

    def run_selected_action(self, action):
        if not self.selected_router_id:
            QMessageBox.warning(self, APP_NAME, "Select a router first.")
            return
        self.run_router_action(action, self.selected_router_id)

    def run_router_action(self, action, router_id):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, "Another task is already running.")
            return

        router = self.find_router(router_id)
        if not router:
            QMessageBox.warning(self, APP_NAME, "Router not found.")
            return

        self.telemetry.note_router_action_intent(action, router_id, source="gui")
        self.update_telemetry_view()

        self.set_busy(True)
        self.deploy_status.setText(f"Running {action} on Router {router_id}...")

        self.action_thread = ActionThread(
            lambda: systemctl_action(action, router_id),
            f"Router {router_id}: {action} completed.",
            self,
        )
        self.action_thread.done.connect(self.on_action_done)
        self.action_thread.failed.connect(self.on_action_failed)
        self.action_thread.start()

    def run_bulk_action(self, action):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, "Another task is already running.")
            return

        router_ids = [r["id"] for r in self.snapshot.get("routers", [])]
        if not router_ids:
            QMessageBox.warning(self, APP_NAME, "No routers detected.")
            return

        def bulk():
            for rid in router_ids:
                systemctl_action(action, rid)

        self.set_busy(True)
        self.deploy_status.setText(f"Running {action} on all routers...")
        self.action_thread = ActionThread(bulk, f"{action.title()} all completed.", self)
        self.action_thread.done.connect(self.on_action_done)
        self.action_thread.failed.connect(self.on_action_failed)
        self.action_thread.start()

    def schedule_post_action_refreshes(self):
        self.refresh_now()
        QTimer.singleShot(1500, self.refresh_now)
        QTimer.singleShot(4000, self.refresh_now)
        QTimer.singleShot(8000, self.refresh_now)

    def on_action_done(self, text):
        self.set_busy(False)
        self.deploy_status.setText(text)
        self.schedule_post_action_refreshes()

    def on_action_failed(self, text):
        self.set_busy(False)
        self.deploy_status.setText(f"Action failed: {text}")
        QMessageBox.critical(self, APP_NAME, text)
        self.schedule_post_action_refreshes()

    def start_deploy_action(self, action):
        if self.is_task_running():
            QMessageBox.information(self, APP_NAME, "Another task is already running.")
            return

        if action not in {"stop_emulator", "destroy"}:
            QMessageBox.information(self, APP_NAME, "Use the Builder tab for all deployments.")
            return

        self.set_busy(True)
        self.deploy_status.setText(f"Running {action.replace('_', ' ')}...")

        self.deploy_thread = DeployThread(action, parent=self)
        self.deploy_thread.line.connect(lambda line: self.deploy_status.setText(line[-140:] if len(line) > 140 else line))
        self.deploy_thread.done.connect(self.on_deploy_done)
        self.deploy_thread.failed.connect(self.on_deploy_failed)
        self.deploy_thread.start()

    def on_deploy_done(self, text):
        self.set_busy(False)
        self.deploy_status.setText(text)
        self.refresh_deployment_log()
        pending_topology = self._pending_requested_topology
        pending_tsv = self._pending_requested_tsv
        if pending_topology:
            self.set_topology_inputs(*pending_topology)

        if pending_tsv and pending_topology:
            json_path, routers_tsv, subnets_tsv = pending_tsv
            expected_total = pending_topology[0]
            expected_floodfill = pending_topology[1]
            expected_base = os.path.join(HOME, f"i2p-testnet-{expected_total}")
            set_preferred_testnet_base(expected_base)
            self._post_deploy_state = {
                "json_path": json_path,
                "routers_tsv": routers_tsv,
                "subnets_tsv": subnets_tsv,
                "expected_total": expected_total,
                "expected_floodfill": expected_floodfill,
                "expected_base": expected_base,
                "attempt": 0,
                "max_attempts": 20,
            }
            self.deploy_status.setText("Deployment completed. Synchronizing live runtime state...")
            self._run_post_deploy_sync()
        else:
            self._pending_requested_topology = None
            self._pending_requested_tsv = None
            self.refresh_now()

    def _run_post_deploy_sync(self):
        state = self._post_deploy_state
        if not state:
            self.refresh_now()
            return

        self.refresh_now()
        state["attempt"] += 1
        snapshot = self.snapshot or {}
        base_ok = snapshot.get("base") == state["expected_base"]
        total_ok = snapshot.get("total") == state["expected_total"]

        if base_ok and total_ok:
            active = snapshot.get("active", 0)
            QMessageBox.information(
                self,
                APP_NAME,
                (
                    "Deployment successful.\n\n"
                    f"Routers: {state['expected_total']}\n"
                    f"Floodfill: {state['expected_floodfill']}\n"
                    f"Active after deploy: {active}/{state['expected_total']}\n"
                    f"Topology JSON: {state['json_path']}\n"
                    f"Routers TSV: {state['routers_tsv']}\n"
                    f"Subnets TSV: {state['subnets_tsv']}\n"
                    f"Testnet base: {state['expected_base']}"
                )
            )
            self.deploy_status.setText("Deployment completed successfully.")
            self._post_deploy_state = None
            self._pending_requested_topology = None
            self._pending_requested_tsv = None
            return

        if state["attempt"] >= state["max_attempts"]:
            active = snapshot.get("active", 0)
            QMessageBox.warning(
                self,
                APP_NAME,
                (
                    "Deployment finished, but the live snapshot did not fully synchronize yet.\n\n"
                    f"Expected base: {state['expected_base']}\n"
                    f"Detected base: {snapshot.get('base', 'not found')}\n"
                    f"Expected routers: {state['expected_total']}\n"
                    f"Detected routers: {snapshot.get('total', 0)}\n"
                    f"Active currently: {active}/{snapshot.get('total', 0) or state['expected_total']}\n\n"
                    "Use Refresh Now and check the deployment log."
                )
            )
            self.deploy_status.setText("Deployment finished, but runtime synchronization is incomplete.")
            self._post_deploy_state = None
            self._pending_requested_topology = None
            self._pending_requested_tsv = None
            return

        QTimer.singleShot(1500, self._run_post_deploy_sync)

    def on_deploy_failed(self, text):
        self.set_busy(False)
        self._pending_requested_tsv = None
        self._pending_requested_topology = None
        self._post_deploy_state = None
        clear_preferred_testnet_base()
        deployment_log_write(f"ERROR: {text}")
        self.refresh_deployment_log()
        self.deploy_status.setText(f"Deployment failed: {text}")
        QMessageBox.critical(self, APP_NAME, text)
        self.refresh_now()

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec() if PYQT_VER == 6 else app.exec_())


if __name__ == "__main__":
    main()
