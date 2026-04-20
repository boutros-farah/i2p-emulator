#!/usr/bin/env python3
import argparse
import json
import os
import sys
import traceback

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from phase5_backend import run_phase5c_scan


def emit(payload, ok=True):
    out = dict(payload or {})
    out.setdefault('success', bool(ok))
    print(json.dumps(out, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Run Phase 5C scan/import in an external process.')
    parser.add_argument('--gui-file', default='')  # accepted for compatibility; ignored
    parser.add_argument('--project-root', default='')
    parser.add_argument('--testnet-base', default='')
    parser.add_argument('--run-dir', default='')
    parser.add_argument('--trigger-source', default='manual-scan')
    parser.add_argument('--run-normalization', action='store_true')
    parser.add_argument('--run-change-detection', action='store_true')
    args = parser.parse_args()
    try:
        payload = run_phase5c_scan(
            testnet_base=args.testnet_base,
            run_dir=args.run_dir,
            trigger_source=args.trigger_source,
            project_root=args.project_root or SCRIPT_DIR,
            run_normalization=bool(args.run_normalization),
            run_change_detection=bool(args.run_change_detection),
        )
        emit(payload, ok=bool(payload.get('success')))
        return 0 if payload.get('success') else 1
    except Exception as exc:
        emit({
            'success': False,
            'task': 'phase5c-scan',
            'result_text': str(exc),
            'traceback': traceback.format_exc(),
        }, ok=False)
        return 1


if __name__ == '__main__':
    sys.exit(main())
