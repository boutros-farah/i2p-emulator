from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

HOME = str(Path.home())
I2P_GUI_ROOT = os.path.join(HOME, 'i2p-gui', 'logs')
HOP_TRUTH_ROOT_DIR = os.path.join(I2P_GUI_ROOT, 'hop_truth')
MEASUREMENTS_ROOT = os.path.join(I2P_GUI_ROOT, 'measurements')
CAMPAIGN_ROOT_DIR = os.path.join(I2P_GUI_ROOT, 'campaigns')
PHASE5C_ROOT = os.path.join(HOP_TRUTH_ROOT_DIR, 'phase5c')
TESTNET_GLOB = os.path.join(HOME, 'i2p-testnet-*')
APP_NAME = 'I2P Testnet Emulator'


# ---------- generic utils ----------

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def now_display() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def now_iso_utc() -> str:
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def read_json_file(path: str, default=None):
    if not path or not os.path.isfile(path):
        return {} if default is None else default
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {} if default is None else default


def write_json_atomic(path: str, payload: Any) -> None:
    ensure_dir(os.path.dirname(path))
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    os.replace(tmp, path)


def append_jsonl(path: str, record: dict) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=False))
        fh.write('\n')


def read_jsonl_records(path: str, limit: Optional[int] = None) -> List[dict]:
    rows: List[dict] = []
    if not path or not os.path.isfile(path):
        return rows
    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                rows.append(value)
                if limit and len(rows) >= limit:
                    break
    return rows


def filesystem_safe_name(value: str) -> str:
    value = str(value or '').strip()
    if not value:
        return 'item'
    out = []
    for ch in value:
        if ch.isalnum() or ch in ('-', '_', '.'):
            out.append(ch)
        else:
            out.append('-')
    text = ''.join(out).strip('-')
    return text or 'item'


def find_testnet_base(explicit: str = '') -> str:
    explicit = str(explicit or '').strip()
    if explicit and os.path.isdir(explicit):
        return explicit
    candidates = [p for p in glob.glob(TESTNET_GLOB) if os.path.isdir(p)]
    if not candidates:
        return ''
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def list_recent_run_dirs(root: str, limit: int = 100, require_files: Optional[List[str]] = None) -> List[str]:
    require_files = require_files or []
    if not os.path.isdir(root):
        return []
    entries = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if require_files and not all(os.path.exists(os.path.join(path, req)) for req in require_files):
            continue
        entries.append(path)
    entries.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return entries[:limit]


def parse_iso_or_display_ts(text: str) -> float:
    text = str(text or '').strip()
    if not text:
        return 0.0
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()
    except Exception:
        return 0.0


def format_kv(label: str, value: Any, width: int = 22) -> str:
    return f"{label:<{width}} : {value}"


def find_script_near(name: str, project_root: str = '') -> str:
    candidates = []
    if project_root:
        candidates.append(os.path.join(project_root, name))
    candidates.extend([
        os.path.join(os.getcwd(), name),
        os.path.join(HOME, 'Desktop', 'i2p_emulator', name),
    ])
    seen = set()
    for path in candidates:
        path = os.path.abspath(path)
        if path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path):
            return path
    return os.path.abspath(candidates[0]) if candidates else name


# ---------- phase5c state ----------

def phase5c_root_dir() -> str:
    return ensure_dir(PHASE5C_ROOT)


def phase5c_state_path() -> str:
    return os.path.join(phase5c_root_dir(), 'auto_extract_state.json')


def phase5c_default_state() -> dict:
    return {
        'generated_at_local': now_display(),
        'generated_at_utc': now_iso_utc(),
        'auto_mode': 'enabled',
        'runs_scanned': 0,
        'trace_rows_scanned': 0,
        'auto_events_captured': 0,
        'duplicate_rows_skipped': 0,
        'rows_without_authoritative_chain': 0,
        'source_files_scanned': 0,
        'source_records_scanned': 0,
        'trace_events_captured': 0,
        'source_file_events_captured': 0,
        'log_files_scanned': 0,
        'log_lines_scanned': 0,
        'log_source_events_materialized': 0,
        'last_generated_source_path': '',
        'source_contract_path': '',
        'source_example_path': '',
        'source_import_root': '',
        'source_run_import_dir': '',
        'source_authoritative_dir': '',
        'source_producer_drop_file': '',
        'source_producer_hook': '',
        'source_producer_status': '',
        'source_producer_readme': '',
        'producer_rows_published': 0,
        'producer_published_path': '',
        'latest_run_id': '',
        'latest_run_dir': '',
        'latest_source_fields': [],
        'last_result': 'No automatic truth extraction has run yet.',
        'last_raw_output_path': os.path.join(HOP_TRUTH_ROOT_DIR, 'raw', 'exact-hop-source.jsonl'),
        'last_scan_trigger': 'none',
        'last_scan_started_local': '',
        'last_scan_finished_local': '',
        'last_normalization_started_local': '',
        'last_normalization_finished_local': '',
        'last_normalization_result': 'Normalization has not run yet.',
        'last_normalized_event_count': 0,
        'last_normalization_manifest_path': '',
        'last_normalization_jsonl_path': '',
        'last_change_detection_started_local': '',
        'last_change_detection_finished_local': '',
        'last_change_detection_result': 'Change detection has not run yet.',
        'last_change_manifest_path': '',
        'last_change_event_count': 0,
        'last_change_stream_count': 0,
        'last_java_import_started_local': '',
        'last_java_import_finished_local': '',
        'last_java_import_result': 'Java authoritative import has not run yet.',
        'last_java_import_manifest_path': '',
        'last_java_import_rows_imported': 0,
        'last_java_import_rows_skipped': 0,
        'last_java_import_rows_read': 0,
        'last_java_import_files_scanned': 0,
        'last_java_import_dir': '',
        'last_java_output_jsonl': '',
        'seen_keys': [],
    }


def phase5c_load_state() -> dict:
    state = read_json_file(phase5c_state_path(), default={}) or {}
    base = phase5c_default_state()
    base.update(state)
    base['seen_keys'] = list(base.get('seen_keys') or [])[-5000:]
    return base


def phase5c_save_state(**updates) -> dict:
    state = phase5c_load_state()
    state.update(updates)
    state['generated_at_local'] = now_display()
    state['generated_at_utc'] = now_iso_utc()
    state['seen_keys'] = list(state.get('seen_keys') or [])[-5000:]
    write_json_atomic(phase5c_state_path(), state)
    return state


# ---------- helpers ----------

def phase5b_normalize_router_name(value: Any) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    if text.lower().startswith('router '):
        suffix = text.split(' ', 1)[1].strip()
        if suffix.isdigit():
            return f'Router {int(suffix)}'
    return text


def phase5b_parse_hop_chain(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                name = phase5b_normalize_router_name(item.get('router_name') or (f"Router {item.get('router_id')}" if item.get('router_id') else ''))
            else:
                name = phase5b_normalize_router_name(item)
            if name:
                out.append(name)
        return out
    text = str(value).strip()
    if not text:
        return []
    parts = [phase5b_normalize_router_name(p.strip()) for p in text.replace('>', ',').split(',')]
    return [p for p in parts if p]


def phase5b_chain_signature(chain: Iterable[str]) -> str:
    return ' > '.join([phase5b_normalize_router_name(x) for x in chain if phase5b_normalize_router_name(x)])


def phase5b_build_raw_capture_record(
    run_id: str,
    scenario_bucket: str,
    scenario_label: str,
    tunnel_id: str,
    tunnel_direction: str,
    tunnel_kind: str,
    hop_chain: Iterable[str],
    source_mode: str,
    phase_stage: str,
    phase_trigger_reason: str,
    previous_chain: Optional[Iterable[str]] = None,
    metadata: Optional[dict] = None,
    ts_utc: Optional[str] = None,
) -> dict:
    chain = phase5b_parse_hop_chain(list(hop_chain or []))
    previous = phase5b_parse_hop_chain(list(previous_chain or []))
    return {
        'ts_utc': ts_utc or now_iso_utc(),
        'ts_local': ts_utc or now_iso_utc(),
        'run_id': str(run_id or '').strip(),
        'scenario_bucket': str(scenario_bucket or 'other').strip() or 'other',
        'scenario_label': str(scenario_label or '').strip(),
        'tunnel_id': str(tunnel_id or '').strip(),
        'tunnel_direction': str(tunnel_direction or 'unknown').strip() or 'unknown',
        'tunnel_kind': str(tunnel_kind or 'unknown').strip() or 'unknown',
        'hop_chain': chain,
        'hop_chain_names': chain,
        'full_hop_chain': chain,
        'previous_chain': previous,
        'source_mode': str(source_mode or 'emulator-observed').strip() or 'emulator-observed',
        'truth_level': 'ground-truth',
        'phase_stage': str(phase_stage or 'runtime').strip() or 'runtime',
        'phase_trigger_reason': str(phase_trigger_reason or 'phase5c_auto_extract').strip() or 'phase5c_auto_extract',
        'path_signature': phase5b_chain_signature(chain),
        'metadata': dict(metadata or {}),
    }


def phase5b_parse_truth_file(path: str) -> List[dict]:
    rows: List[dict] = []
    if not path or not os.path.isfile(path):
        return rows
    lower = path.lower()
    if lower.endswith('.jsonl'):
        return read_jsonl_records(path)
    payload = read_json_file(path, default=None)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get('records'), list):
            return [item for item in payload.get('records') if isinstance(item, dict)]
        return [payload]
    return rows


def phase5b_normalize_chain_router(item: Any) -> dict:
    if isinstance(item, dict):
        rid = str(item.get('router_id') or '').strip()
        rname = phase5b_normalize_router_name(item.get('router_name') or (f'Router {rid}' if rid else ''))
        return {'router_id': rid, 'router_name': rname}
    name = phase5b_normalize_router_name(item)
    rid = ''
    if name.lower().startswith('router '):
        suffix = name.split(' ', 1)[1].strip()
        if suffix.isdigit():
            rid = suffix
    return {'router_id': rid, 'router_name': name}


def phase5b_extract_hop_chain(raw: dict) -> List[dict]:
    for key in ('full_hop_chain', 'hop_chain', 'hop_chain_names', 'routers', 'hops'):
        value = raw.get(key)
        if isinstance(value, list) and value:
            chain = [phase5b_normalize_chain_router(item) for item in value]
            chain = [item for item in chain if item.get('router_id') or item.get('router_name')]
            if chain:
                return chain
    return []


def phase5b_role_from_index(index: int, hop_count: int) -> str:
    if hop_count <= 1:
        return 'entry'
    if index <= 1:
        return 'entry'
    if index >= hop_count:
        return 'endpoint'
    return 'middle'


def analytics_ts_epoch(value: Any) -> float:
    return parse_iso_or_display_ts(str(value or ''))


# ---------- phase5c scan/import ----------

def phase5c_import_root() -> str:
    return ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, 'imports'))


def phase5c_run_import(testnet_base: str = '', project_root: str = '') -> dict:
    script_path = find_script_near('import_java_authoritative_truth.py', project_root=project_root)
    if not os.path.isfile(script_path):
        return {
            'success': False,
            'result_text': f'Helper script not found: {script_path}',
            'files_scanned': 0,
            'rows_read': 0,
            'rows_written': 0,
            'rows_skipped': 0,
            'import_dir': '',
            'output_jsonl': '',
            'manifest_path': '',
        }
    cmd = [sys.executable or 'python3', script_path]
    testnet_base = find_testnet_base(testnet_base)
    if testnet_base:
        cmd.extend(['--testnet-base', testnet_base])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stdout = proc.stdout or ''
    stderr = proc.stderr or ''
    parsed = {}
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            parsed = json.loads(line)
        except Exception:
            continue
        if isinstance(parsed, dict):
            break
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    if parsed.get('success'):
        # maintain a stable "current" import view used by existing data files
        current_dir = ensure_dir(os.path.join(phase5c_import_root(), 'live-java-authoritative-current'))
        out_jsonl = parsed.get('output_jsonl') or ''
        manifest_path = parsed.get('manifest_path') or ''
        if out_jsonl and os.path.isfile(out_jsonl):
            shutil.copy2(out_jsonl, os.path.join(current_dir, 'authoritative-hop-events.jsonl'))
        live_manifest = {
            'generated_at_local': now_display(),
            'source_import_dir': parsed.get('import_dir') or '',
            'output_jsonl': os.path.join(current_dir, 'authoritative-hop-events.jsonl'),
            'upstream_manifest_path': manifest_path,
            'rows_written': parsed.get('rows_written', 0),
            'rows_read': parsed.get('rows_read', 0),
            'rows_skipped': parsed.get('rows_skipped', 0),
            'files_scanned': parsed.get('files_scanned', 0),
        }
        write_json_atomic(os.path.join(current_dir, 'live-java-authoritative-manifest.json'), live_manifest)
    if stderr and not parsed.get('stderr'):
        parsed['stderr'] = stderr.strip()
    return parsed


def phase5c_find_latest_measurement_run(explicit_run_dir: str = '') -> Tuple[str, str]:
    explicit_run_dir = str(explicit_run_dir or '').strip()
    if explicit_run_dir and os.path.isdir(explicit_run_dir):
        return os.path.basename(explicit_run_dir), explicit_run_dir
    runs = list_recent_run_dirs(MEASUREMENTS_ROOT, limit=200)
    if not runs:
        return '', ''
    return os.path.basename(runs[0]), runs[0]


def run_phase5c_scan(testnet_base: str = '', run_dir: str = '', trigger_source: str = 'manual-scan',
                     project_root: str = '', run_normalization: bool = False, run_change_detection: bool = False) -> dict:
    prior = phase5c_load_state()
    latest_run_id, latest_run_dir = phase5c_find_latest_measurement_run(run_dir)
    started = now_display()
    import_result = phase5c_run_import(testnet_base=testnet_base, project_root=project_root)

    payload = dict(prior)
    payload.update({
        'auto_mode': prior.get('auto_mode', 'enabled'),
        'last_scan_trigger': str(trigger_source or 'manual-scan'),
        'last_scan_started_local': started,
        'last_scan_finished_local': now_display(),
        'latest_run_id': latest_run_id,
        'latest_run_dir': latest_run_dir,
        'source_import_root': phase5c_import_root(),
        'source_run_import_dir': import_result.get('import_dir') or '',
        'source_authoritative_dir': os.path.join(latest_run_dir, 'authoritative') if latest_run_dir else '',
        'source_producer_drop_file': os.path.join(find_testnet_base(testnet_base), 'authoritative', 'authoritative-hop-events.jsonl') if find_testnet_base(testnet_base) else '',
        'source_producer_hook': os.path.join(find_testnet_base(testnet_base), 'authoritative', 'emit-authoritative-hop-event.sh') if find_testnet_base(testnet_base) else '',
        'source_producer_status': os.path.join(find_testnet_base(testnet_base), 'authoritative', 'producer-status.json') if find_testnet_base(testnet_base) else '',
        'source_producer_readme': os.path.join(find_testnet_base(testnet_base), 'authoritative', 'README.txt') if find_testnet_base(testnet_base) else '',
        'producer_rows_published': safe_int(import_result.get('rows_written'), 0),
        'producer_published_path': import_result.get('output_jsonl') or '',
        'runs_scanned': safe_int(prior.get('runs_scanned'), 0) + (1 if latest_run_dir else 0),
        'source_files_scanned': safe_int(import_result.get('files_scanned'), 0),
        'source_records_scanned': safe_int(import_result.get('rows_read'), 0),
        'source_file_events_captured': safe_int(prior.get('source_file_events_captured'), 0) + safe_int(import_result.get('rows_written'), 0),
        'auto_events_captured': safe_int(prior.get('auto_events_captured'), 0) + safe_int(import_result.get('rows_written'), 0),
        'last_generated_source_path': import_result.get('output_jsonl') or '',
        'last_java_import_started_local': started,
        'last_java_import_finished_local': now_display(),
        'last_java_import_result': import_result.get('result_text') or ('Java authoritative import completed.' if import_result.get('success') else 'Java authoritative import failed.'),
        'last_java_import_manifest_path': import_result.get('manifest_path') or '',
        'last_java_import_rows_imported': safe_int(import_result.get('rows_written'), 0),
        'last_java_import_rows_skipped': safe_int(import_result.get('rows_skipped'), 0),
        'last_java_import_rows_read': safe_int(import_result.get('rows_read'), 0),
        'last_java_import_files_scanned': safe_int(import_result.get('files_scanned'), 0),
        'last_java_import_dir': import_result.get('import_dir') or '',
        'last_java_output_jsonl': import_result.get('output_jsonl') or '',
    })

    if import_result.get('success'):
        payload['last_result'] = import_result.get('result_text') or 'Imported Java authoritative rows successfully.'
    else:
        payload['last_result'] = import_result.get('result_text') or 'No authoritative rows were imported.'

    normalization_result = None
    change_result = None
    if run_normalization and import_result.get('success'):
        normalization_result = run_phase5b_normalization(reason='auto-after-ingestion')
        payload.update({
            'last_normalization_started_local': normalization_result.get('started_at_local') or started,
            'last_normalization_finished_local': normalization_result.get('finished_at_local') or now_display(),
            'last_normalization_result': normalization_result.get('result_text') or 'Normalization completed.',
            'last_normalized_event_count': safe_int(normalization_result.get('normalized_event_count'), 0),
            'last_normalization_manifest_path': normalization_result.get('manifest_path') or '',
            'last_normalization_jsonl_path': normalization_result.get('jsonl_path') or '',
        })
        if run_change_detection:
            change_result = run_phase5d_change_detection(reason='auto-after-normalization')
            payload.update({
                'last_change_detection_started_local': change_result.get('started_at_local') or started,
                'last_change_detection_finished_local': change_result.get('finished_at_local') or now_display(),
                'last_change_detection_result': change_result.get('result_text') or 'Change detection completed.',
                'last_change_manifest_path': change_result.get('manifest_path') or '',
                'last_change_event_count': safe_int(change_result.get('change_event_count'), 0),
                'last_change_stream_count': safe_int(change_result.get('stream_count'), 0),
            })
    elif not payload.get('last_normalization_result'):
        payload['last_normalization_result'] = 'Normalization has not run yet.'

    state = phase5c_save_state(**payload)
    return {
        'success': bool(import_result.get('success')),
        'task': 'phase5c-scan',
        'result_text': state.get('last_result'),
        'run_id': latest_run_id,
        'last_scan_finished_local': state.get('last_scan_finished_local'),
        'last_normalization_result': state.get('last_normalization_result'),
        'last_change_detection_result': state.get('last_change_detection_result'),
        'state': state,
        'import_result': import_result,
        'normalization_result': normalization_result,
        'change_result': change_result,
    }


# ---------- phase5b normalization ----------

def phase5b_raw_root() -> str:
    return ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, 'raw'))


def phase5b_output_paths(testnet_base: str = '') -> dict:
    ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, 'events'))
    ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, 'summaries'))
    base = filesystem_safe_name(os.path.basename(find_testnet_base(testnet_base) or 'testnet'))
    return {
        'jsonl': os.path.join(HOP_TRUTH_ROOT_DIR, 'events', 'exact-hop-truth.jsonl'),
        'json': os.path.join(HOP_TRUTH_ROOT_DIR, 'events', 'exact-hop-truth.json'),
        'manifest': os.path.join(HOP_TRUTH_ROOT_DIR, 'summaries', f'{base}-phase5b-producer-manifest.json'),
    }


def phase5b_candidate_files(limit_files: int = 240) -> List[str]:
    files: List[str] = []
    seen = set()
    patterns = (
        'exact-hop-source.json', 'exact-hop-source.jsonl', 'tunnel-build-events.json', 'tunnel-build-events.jsonl',
        'router-hop-events.json', 'router-hop-events.jsonl', 'authoritative-hop-events.json', 'authoritative-hop-events.jsonl',
        'ground-truth-hop-events.json', 'ground-truth-hop-events.jsonl', 'exact-hop-raw.json', 'exact-hop-raw.jsonl',
    )
    roots = [phase5b_raw_root(), os.path.join(HOP_TRUTH_ROOT_DIR, 'imports')]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in patterns:
            for path in glob.glob(os.path.join(root, '**', name), recursive=True):
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
    files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0.0, reverse=True)
    return files[:limit_files]


def phase5b_is_normalized_truth_event(raw: dict) -> bool:
    has_router = bool(str(raw.get('router_id') or '').strip() or str(raw.get('router_name') or '').strip())
    has_chain = (
        (isinstance(raw.get('full_hop_chain'), list) and bool(raw.get('full_hop_chain')))
        or (isinstance(raw.get('hop_chain'), list) and bool(raw.get('hop_chain')))
        or (isinstance(raw.get('hop_chain_names'), list) and bool(raw.get('hop_chain_names')))
        or (isinstance(raw.get('routers'), list) and bool(raw.get('routers')))
        or (isinstance(raw.get('hops'), list) and bool(raw.get('hops')))
    )
    has_hop = raw.get('hop_index') is not None or bool(str(raw.get('role') or '').strip())
    return has_router and has_chain and has_hop


def phase5b_normalized_event_from_row(raw: dict) -> Optional[dict]:
    chain_raw = raw.get('full_hop_chain')
    if not isinstance(chain_raw, list) or not chain_raw:
        chain_raw = raw.get('hop_chain')
    if not isinstance(chain_raw, list) or not chain_raw:
        chain_raw = raw.get('hop_chain_names')
    if not isinstance(chain_raw, list) or not chain_raw:
        chain_raw = raw.get('routers')
    if not isinstance(chain_raw, list) or not chain_raw:
        chain_raw = raw.get('hops')
    if not isinstance(chain_raw, list) or not chain_raw:
        return None
    chain_names: List[str] = []
    chain_ids: List[str] = []
    for item in chain_raw:
        norm = phase5b_normalize_chain_router(item)
        if norm.get('router_id') or norm.get('router_name'):
            chain_names.append(norm.get('router_name') or (f"Router {norm.get('router_id')}" if norm.get('router_id') else ''))
            chain_ids.append(str(norm.get('router_id') or ''))
    if not chain_names:
        return None
    rid = str(raw.get('router_id') or '').strip()
    rname = phase5b_normalize_router_name(raw.get('router_name') or '')
    if not rname and rid:
        rname = f'Router {rid}'
    hop_count = safe_int(raw.get('hop_count'), len(chain_names)) or len(chain_names)
    hop_index = safe_int(raw.get('hop_index'), 0)
    if hop_index <= 0:
        if rname in chain_names:
            hop_index = chain_names.index(rname) + 1
        elif rid and rid in [x for x in chain_ids if x]:
            hop_index = chain_ids.index(rid) + 1
        else:
            hop_index = 1
    neighbor_names = raw.get('neighbor_names') or raw.get('neighbor_routers') or []
    if not isinstance(neighbor_names, list):
        neighbor_names = []
    neighbor_names = [phase5b_normalize_router_name(x) for x in neighbor_names if phase5b_normalize_router_name(x)]
    if not neighbor_names:
        if hop_index > 1 and hop_index - 2 < len(chain_names):
            neighbor_names.append(chain_names[hop_index - 2])
        if hop_index < len(chain_names):
            neighbor_names.append(chain_names[hop_index])
    tunnel_id = str(raw.get('tunnel_id') or raw.get('id') or raw.get('trace_id') or raw.get('path_id') or '').strip()
    path_signature = str(raw.get('path_signature') or raw.get('signature') or ' > '.join([name for name in chain_names if name]) or tunnel_id).strip()
    role = str(raw.get('role') or '').strip() or phase5b_role_from_index(hop_index, hop_count)
    return {
        'ts_utc': raw.get('ts_utc') or raw.get('timestamp_utc') or raw.get('timestamp') or raw.get('ts'),
        'ts_local': raw.get('ts_local') or raw.get('timestamp_local') or raw.get('ts_utc') or raw.get('timestamp'),
        'run_id': str(raw.get('run_id') or raw.get('campaign_run_id') or raw.get('measurement_run_id') or '').strip(),
        'scenario_bucket': str(raw.get('scenario_bucket') or raw.get('scenario') or raw.get('bucket') or '').strip(),
        'scenario_label': str(raw.get('scenario_label') or raw.get('phase_label') or raw.get('scenario_bucket') or '').strip(),
        'phase_stage': str(raw.get('phase_stage') or raw.get('stage') or '').strip(),
        'phase_trigger_reason': str(raw.get('phase_trigger_reason') or raw.get('trigger') or '').strip(),
        'source_mode': str(raw.get('source_mode') or raw.get('truth_source') or '').strip() or 'emulator-observed',
        'truth_level': str(raw.get('truth_level') or 'ground-truth').strip(),
        'tunnel_id': tunnel_id,
        'tunnel_direction': str(raw.get('tunnel_direction') or raw.get('direction') or '').strip() or 'unknown',
        'tunnel_kind': str(raw.get('tunnel_kind') or raw.get('kind') or raw.get('tunnel_type') or '').strip() or 'unknown',
        'hop_count': hop_count,
        'full_hop_chain': chain_names,
        'full_hop_chain_ids': chain_ids,
        'hop_chain_names': chain_names,
        'hop_chain_ids': chain_ids,
        'path_signature': path_signature,
        'router_id': rid,
        'router_name': rname or (f'Router {rid}' if rid else ''),
        'role': role,
        'hop_index': hop_index,
        'neighbor_names': neighbor_names,
        '_source_file': raw.get('_source_file') or raw.get('source_file'),
        '_java_local_router_hash': raw.get('_java_local_router_hash'),
        '_java_destination_hash': raw.get('_java_destination_hash'),
        '_java_pool_name': raw.get('_java_pool_name'),
    }


def phase5b_expand_truth_records(raw_records: List[dict]) -> List[dict]:
    events: List[dict] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        if phase5b_is_normalized_truth_event(raw):
            event = phase5b_normalized_event_from_row(raw)
            if event:
                events.append(event)
            continue
        chain = phase5b_extract_hop_chain(raw)
        if not chain:
            continue
        hop_count = len(chain)
        tunnel_id = str(raw.get('tunnel_id') or raw.get('id') or raw.get('trace_id') or raw.get('path_id') or '').strip()
        ts_utc = raw.get('ts_utc') or raw.get('timestamp_utc') or raw.get('timestamp') or raw.get('ts')
        ts_local = raw.get('ts_local') or raw.get('timestamp_local') or ts_utc
        run_id = str(raw.get('run_id') or raw.get('campaign_run_id') or raw.get('measurement_run_id') or '').strip()
        scenario_bucket = str(raw.get('scenario_bucket') or raw.get('scenario') or raw.get('bucket') or '').strip()
        scenario_label = str(raw.get('scenario_label') or raw.get('phase_label') or scenario_bucket or '').strip()
        phase_stage = str(raw.get('phase_stage') or raw.get('stage') or '').strip()
        phase_trigger_reason = str(raw.get('phase_trigger_reason') or raw.get('trigger') or '').strip()
        tunnel_direction = str(raw.get('tunnel_direction') or raw.get('direction') or '').strip() or 'unknown'
        tunnel_kind = str(raw.get('tunnel_kind') or raw.get('kind') or raw.get('tunnel_type') or '').strip() or 'unknown'
        source_mode = str(raw.get('source_mode') or raw.get('truth_source') or '').strip() or 'emulator-observed'
        truth_level = str(raw.get('truth_level') or 'ground-truth').strip()
        chain_names = [phase5b_normalize_router_name(item.get('router_name') or f"Router {item.get('router_id')}") for item in chain]
        chain_ids = [str(item.get('router_id') or '') for item in chain]
        path_signature = ' > '.join([name for name in chain_names if name]) or str(tunnel_id or '')
        if not path_signature:
            continue
        for idx, item in enumerate(chain, start=1):
            rid = str(item.get('router_id') or '').strip()
            rname = phase5b_normalize_router_name(item.get('router_name') or (f'Router {rid}' if rid else ''))
            if not rid and not rname:
                continue
            neighbor_names = []
            if idx > 1 and idx - 2 < len(chain_names):
                neighbor_names.append(chain_names[idx - 2])
            if idx < hop_count and idx < len(chain_names):
                neighbor_names.append(chain_names[idx])
            events.append({
                'ts_utc': ts_utc,
                'ts_local': ts_local,
                'run_id': run_id,
                'scenario_bucket': scenario_bucket,
                'scenario_label': scenario_label,
                'phase_stage': phase_stage,
                'phase_trigger_reason': phase_trigger_reason,
                'source_mode': source_mode,
                'truth_level': truth_level,
                'tunnel_id': tunnel_id,
                'tunnel_direction': tunnel_direction,
                'tunnel_kind': tunnel_kind,
                'hop_count': hop_count,
                'full_hop_chain': chain_names,
                'full_hop_chain_ids': chain_ids,
                'hop_chain_names': chain_names,
                'hop_chain_ids': chain_ids,
                'path_signature': path_signature,
                'router_id': rid,
                'router_name': rname or f'Router {rid}',
                'role': phase5b_role_from_index(idx, hop_count),
                'hop_index': idx,
                'neighbor_names': neighbor_names,
                '_source_file': raw.get('_source_file') or raw.get('source_file'),
                '_java_local_router_hash': raw.get('_java_local_router_hash'),
                '_java_destination_hash': raw.get('_java_destination_hash'),
                '_java_pool_name': raw.get('_java_pool_name'),
            })
    deduped: List[dict] = []
    seen = set()
    for event in events:
        key = (
            str(event.get('ts_utc') or event.get('ts_local') or ''),
            str(event.get('run_id') or ''),
            str(event.get('tunnel_id') or ''),
            str(event.get('router_id') or event.get('router_name') or ''),
            str(event.get('hop_index') or ''),
            str(event.get('path_signature') or ''),
            str(event.get('source_mode') or ''),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    deduped.sort(key=lambda e: (
        analytics_ts_epoch(e.get('ts_utc') or e.get('ts_local')),
        str(e.get('run_id') or ''),
        str(e.get('tunnel_id') or ''),
        safe_int(e.get('hop_index'), 0),
    ))
    return deduped


def phase5b_manifest_payload(testnet_base: str = '') -> dict:
    candidate_files = phase5b_candidate_files()
    raw_records: List[dict] = []
    source_modes = set()
    for path in candidate_files:
        for item in phase5b_parse_truth_file(path):
            if isinstance(item, dict):
                norm = dict(item)
                norm['_source_file'] = path
                raw_records.append(norm)
                mode = str(item.get('source_mode') or item.get('truth_source') or '').strip()
                if mode:
                    source_modes.add(mode)
    normalized_events = phase5b_expand_truth_records(raw_records)
    routers = sorted({str(e.get('router_id') or e.get('router_name') or '') for e in normalized_events if (e.get('router_id') or e.get('router_name'))})
    tunnels = sorted({str(e.get('tunnel_id') or '') for e in normalized_events if e.get('tunnel_id')})
    run_ids = sorted({str(e.get('run_id') or '') for e in normalized_events if e.get('run_id')})
    role_totals = {'entry': 0, 'middle': 0, 'endpoint': 0, 'unknown': 0}
    for e in normalized_events:
        role = str(e.get('role') or 'unknown').strip().lower()
        if role not in role_totals:
            role = 'unknown'
        role_totals[role] += 1
    if not source_modes:
        source_modes = {str(e.get('source_mode') or '').strip() for e in normalized_events if e.get('source_mode')}
    return {
        'generated_at': now_display(),
        'started_at_local': now_display(),
        'raw_candidate_files': candidate_files,
        'raw_record_count': len(raw_records),
        'normalized_event_count': len(normalized_events),
        'router_count': len(routers),
        'tunnel_count': len(tunnels),
        'run_ids': run_ids,
        'source_modes': sorted([m for m in source_modes if m]) or ['none'],
        'role_totals': role_totals,
        'normalized_events_preview': normalized_events[:200],
        'normalized_events': normalized_events,
        'summary': 'The truth producer normalizes Java-router authoritative, approved log-derived, and explicitly entered validation records into the canonical exact-hop store.',
        'limitation': 'This producer does not invent hop truth; it only transforms raw authoritative records when they exist.',
    }


def run_phase5b_normalization(testnet_base: str = '', reason: str = 'manual') -> dict:
    started = now_display()
    payload = phase5b_manifest_payload(testnet_base=testnet_base)
    paths = phase5b_output_paths(testnet_base=testnet_base)
    events = payload.pop('normalized_events', [])
    write_json_atomic(paths['json'], {'events': events, 'generated_at_local': now_display(), 'event_count': len(events)})
    ensure_dir(os.path.dirname(paths['jsonl']))
    with open(paths['jsonl'], 'w', encoding='utf-8') as fh:
        for row in events:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write('\n')
    manifest = dict(payload)
    manifest.update({
        'reason': reason,
        'started_at_local': started,
        'finished_at_local': now_display(),
        'jsonl_path': paths['jsonl'],
        'json_path': paths['json'],
        'manifest_path': paths['manifest'],
    })
    write_json_atomic(paths['manifest'], manifest)

    state = phase5c_load_state()
    state.update({
        'last_normalization_started_local': started,
        'last_normalization_finished_local': manifest['finished_at_local'],
        'last_normalization_result': f"Normalization refreshed the canonical ground-truth dataset ({manifest['normalized_event_count']} event(s)).",
        'last_normalized_event_count': manifest['normalized_event_count'],
        'last_normalization_manifest_path': paths['manifest'],
        'last_normalization_jsonl_path': paths['jsonl'],
    })
    phase5c_save_state(**state)
    return {
        'success': True,
        'task': 'phase5b-normalization',
        'started_at_local': started,
        'finished_at_local': manifest['finished_at_local'],
        'normalized_event_count': manifest['normalized_event_count'],
        'router_count': manifest['router_count'],
        'tunnel_count': manifest['tunnel_count'],
        'source_modes': manifest['source_modes'],
        'jsonl_path': paths['jsonl'],
        'json_path': paths['json'],
        'manifest_path': paths['manifest'],
        'result_text': f"Normalization refreshed the canonical ground-truth dataset ({manifest['normalized_event_count']} event(s)).",
    }


# ---------- phase5d change detection ----------

def phase5d_output_paths(testnet_base: str = '') -> dict:
    ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, 'events'))
    ensure_dir(os.path.join(HOP_TRUTH_ROOT_DIR, 'summaries'))
    base = filesystem_safe_name(os.path.basename(find_testnet_base(testnet_base) or 'testnet'))
    return {
        'jsonl': os.path.join(HOP_TRUTH_ROOT_DIR, 'events', 'exact-hop-change-events.jsonl'),
        'json': os.path.join(HOP_TRUTH_ROOT_DIR, 'events', 'exact-hop-change-events.json'),
        'manifest': os.path.join(HOP_TRUTH_ROOT_DIR, 'summaries', f'{base}-phase5d-change-manifest.json'),
    }


def phase5d_load_truth_events() -> List[dict]:
    path = phase5b_output_paths().get('jsonl')
    return read_jsonl_records(path)


def phase5d_group_snapshots(events: List[dict]) -> List[dict]:
    grouped: Dict[Tuple[str, str, str, str], List[dict]] = defaultdict(list)
    for row in events:
        if str(row.get('source_mode') or '') != 'java-router-authoritative':
            continue
        key = (
            str(row.get('run_id') or ''),
            str(row.get('tunnel_id') or ''),
            str(row.get('ts_utc') or row.get('ts_local') or ''),
            str(row.get('_source_file') or row.get('source_file') or ''),
        )
        grouped[key].append(row)
    snapshots: List[dict] = []
    for key, rows in grouped.items():
        rows.sort(key=lambda r: safe_int(r.get('hop_index'), 0))
        first = rows[0]
        hop_chain_names = list(first.get('hop_chain_names') or first.get('full_hop_chain') or [])
        hop_chain_ids = list(first.get('hop_chain_ids') or first.get('full_hop_chain_ids') or [])
        hop_count = safe_int(first.get('hop_count'), len(hop_chain_names)) or len(hop_chain_names)
        direction = str(first.get('tunnel_direction') or 'unknown')
        if direction == 'inbound':
            creator_router_name = hop_chain_names[-1] if hop_chain_names else ''
            creator_router_id = hop_chain_ids[-1] if hop_chain_ids else ''
        else:
            creator_router_name = hop_chain_names[0] if hop_chain_names else ''
            creator_router_id = hop_chain_ids[0] if hop_chain_ids else ''
        snapshots.append({
            'ts_utc': first.get('ts_utc') or first.get('ts_local'),
            'ts_local': first.get('ts_local') or first.get('ts_utc'),
            'run_id': first.get('run_id') or '',
            'source_mode': first.get('source_mode') or '',
            'truth_level': first.get('truth_level') or 'ground-truth',
            'tunnel_id': first.get('tunnel_id') or '',
            'tunnel_direction': direction,
            'tunnel_kind': str(first.get('tunnel_kind') or 'unknown'),
            'hop_count': hop_count,
            'hop_chain_ids': hop_chain_ids,
            'hop_chain_names': hop_chain_names,
            'path_signature': ' > '.join(hop_chain_names),
            'creator_router_id': creator_router_id,
            'creator_router_name': creator_router_name,
            'destination_hash': first.get('_java_destination_hash') or first.get('destination_hash') or '',
            'pool_name': first.get('_java_pool_name') or first.get('pool_name') or '',
            'local_router_hash': first.get('_java_local_router_hash') or '',
            'source_file': first.get('_source_file') or first.get('source_file') or '',
        })
    snapshots.sort(key=lambda s: (analytics_ts_epoch(s.get('ts_utc') or s.get('ts_local')), s.get('tunnel_id') or '', s.get('path_signature') or ''))
    return snapshots


def phase5d_stream_key(snapshot: dict) -> str:
    parts = [
        str(snapshot.get('source_mode') or 'java-router-authoritative'),
        str(snapshot.get('creator_router_id') or snapshot.get('creator_router_name') or '?'),
        str(snapshot.get('tunnel_direction') or 'unknown'),
        str(snapshot.get('tunnel_kind') or 'unknown'),
        str(snapshot.get('destination_hash') or ''),
        str(snapshot.get('pool_name') or ''),
    ]
    return '|'.join(parts)


def phase5d_change_events_from_snapshots(snapshots: List[dict]) -> Tuple[List[dict], dict]:
    by_stream: Dict[str, List[dict]] = defaultdict(list)
    for snap in snapshots:
        by_stream[phase5d_stream_key(snap)].append(snap)
    change_events: List[dict] = []
    initial_count = 0
    type_counts = Counter()
    creator_counts = Counter()
    for stream_key, items in by_stream.items():
        items.sort(key=lambda s: (analytics_ts_epoch(s.get('ts_utc') or s.get('ts_local')), s.get('tunnel_id') or '', s.get('path_signature') or ''))
        prev = None
        for snap in items:
            if prev is None:
                initial_count += 1
                change_type = 'initial_snapshot'
                type_counts[change_type] += 1
                creator_counts[snap.get('creator_router_name') or snap.get('creator_router_id') or '?'] += 1
                change_events.append({
                    'change_ts_utc': snap.get('ts_utc'),
                    'change_ts_local': snap.get('ts_local'),
                    'run_id': snap.get('run_id') or '',
                    'stream_key': stream_key,
                    'stream_label': f"{snap.get('creator_router_name') or 'Router ?'} | {snap.get('tunnel_direction')} | {snap.get('tunnel_kind')} | {str(snap.get('destination_hash') or '')[:16]}... | {snap.get('pool_name') or ''}".strip(),
                    'source_mode': snap.get('source_mode') or '',
                    'truth_level': snap.get('truth_level') or 'ground-truth',
                    'creator_router_id': snap.get('creator_router_id') or '',
                    'creator_router_name': snap.get('creator_router_name') or '',
                    'tunnel_direction': snap.get('tunnel_direction') or 'unknown',
                    'tunnel_kind': snap.get('tunnel_kind') or 'unknown',
                    'destination_hash': snap.get('destination_hash') or '',
                    'pool_name': snap.get('pool_name') or '',
                    'change_type': change_type,
                    'previous_tunnel_id': '',
                    'current_tunnel_id': snap.get('tunnel_id') or '',
                    'previous_hop_count': 0,
                    'current_hop_count': snap.get('hop_count') or 0,
                    'previous_hop_chain_ids': [],
                    'current_hop_chain_ids': snap.get('hop_chain_ids') or [],
                    'previous_hop_chain_names': [],
                    'current_hop_chain_names': snap.get('hop_chain_names') or [],
                    'previous_path_signature': '',
                    'current_path_signature': snap.get('path_signature') or '',
                    'local_router_hash': snap.get('local_router_hash') or '',
                    'source_file': snap.get('source_file') or '',
                })
                prev = snap
                continue
            path_changed = (snap.get('path_signature') or '') != (prev.get('path_signature') or '')
            hop_changed = safe_int(snap.get('hop_count'), 0) != safe_int(prev.get('hop_count'), 0)
            if not path_changed and not hop_changed:
                prev = snap
                continue
            if path_changed and hop_changed:
                change_type = 'path_and_hop_count_changed'
            elif hop_changed:
                change_type = 'hop_count_changed'
            else:
                change_type = 'path_changed'
            type_counts[change_type] += 1
            creator_counts[snap.get('creator_router_name') or snap.get('creator_router_id') or '?'] += 1
            change_events.append({
                'change_ts_utc': snap.get('ts_utc'),
                'change_ts_local': snap.get('ts_local'),
                'run_id': snap.get('run_id') or '',
                'stream_key': stream_key,
                'stream_label': f"{snap.get('creator_router_name') or 'Router ?'} | {snap.get('tunnel_direction')} | {snap.get('tunnel_kind')} | {str(snap.get('destination_hash') or '')[:16]}... | {snap.get('pool_name') or ''}".strip(),
                'source_mode': snap.get('source_mode') or '',
                'truth_level': snap.get('truth_level') or 'ground-truth',
                'creator_router_id': snap.get('creator_router_id') or '',
                'creator_router_name': snap.get('creator_router_name') or '',
                'tunnel_direction': snap.get('tunnel_direction') or 'unknown',
                'tunnel_kind': snap.get('tunnel_kind') or 'unknown',
                'destination_hash': snap.get('destination_hash') or '',
                'pool_name': snap.get('pool_name') or '',
                'change_type': change_type,
                'previous_tunnel_id': prev.get('tunnel_id') or '',
                'current_tunnel_id': snap.get('tunnel_id') or '',
                'previous_hop_count': prev.get('hop_count') or 0,
                'current_hop_count': snap.get('hop_count') or 0,
                'previous_hop_chain_ids': prev.get('hop_chain_ids') or [],
                'current_hop_chain_ids': snap.get('hop_chain_ids') or [],
                'previous_hop_chain_names': prev.get('hop_chain_names') or [],
                'current_hop_chain_names': snap.get('hop_chain_names') or [],
                'previous_path_signature': prev.get('path_signature') or '',
                'current_path_signature': snap.get('path_signature') or '',
                'local_router_hash': snap.get('local_router_hash') or '',
                'source_file': snap.get('source_file') or '',
            })
            prev = snap
    manifest_stats = {
        'stream_count': len(by_stream),
        'initial_snapshot_count': initial_count,
        'change_event_count': len(change_events),
        'change_type_counts': dict(type_counts),
        'top_creators': creator_counts.most_common(10),
    }
    return change_events, manifest_stats


def run_phase5d_change_detection(testnet_base: str = '', reason: str = 'manual') -> dict:
    started = now_display()
    events = phase5d_load_truth_events()
    snapshots = phase5d_group_snapshots(events)
    change_events, stats = phase5d_change_events_from_snapshots(snapshots)
    paths = phase5d_output_paths(testnet_base=testnet_base)
    write_json_atomic(paths['json'], {'events': change_events, 'generated_at_local': now_display(), 'event_count': len(change_events)})
    ensure_dir(os.path.dirname(paths['jsonl']))
    with open(paths['jsonl'], 'w', encoding='utf-8') as fh:
        for row in change_events:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write('\n')
    manifest = {
        'generated_at_local': now_display(),
        'started_at_local': started,
        'finished_at_local': now_display(),
        'reason': reason,
        'canonical_truth_path': phase5b_output_paths(testnet_base=testnet_base)['jsonl'],
        'snapshot_count': len(snapshots),
        'stream_count': stats['stream_count'],
        'initial_snapshot_count': stats['initial_snapshot_count'],
        'change_event_count': stats['change_event_count'],
        'change_type_counts': stats['change_type_counts'],
        'top_creators': stats['top_creators'],
        'jsonl_path': paths['jsonl'],
        'json_path': paths['json'],
        'manifest_path': paths['manifest'],
        'notes': {
            'summary': 'Change detection compares authoritative Java-router tunnel snapshots over time and emits only real path changes for the same creator-side stream.',
            'limitation': 'Only java-router-authoritative events from canonical truth are included.',
        },
    }
    write_json_atomic(paths['manifest'], manifest)
    state = phase5c_load_state()
    state.update({
        'last_change_detection_started_local': started,
        'last_change_detection_finished_local': manifest['finished_at_local'],
        'last_change_detection_result': f"Authoritative path change detection refreshed ({manifest['change_event_count']} change event(s)).",
        'last_change_manifest_path': paths['manifest'],
        'last_change_event_count': manifest['change_event_count'],
        'last_change_stream_count': manifest['stream_count'],
    })
    phase5c_save_state(**state)
    return {
        'success': True,
        'task': 'phase5d-change-detection',
        'started_at_local': started,
        'finished_at_local': manifest['finished_at_local'],
        'change_event_count': manifest['change_event_count'],
        'stream_count': manifest['stream_count'],
        'initial_snapshot_count': manifest['initial_snapshot_count'],
        'manifest_path': paths['manifest'],
        'jsonl_path': paths['jsonl'],
        'json_path': paths['json'],
        'result_text': f"Authoritative path change detection refreshed ({manifest['change_event_count']} change event(s)).",
    }
