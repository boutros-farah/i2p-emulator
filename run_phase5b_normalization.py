#!/usr/bin/env python3
import argparse
import json
import os
import sys
import traceback

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from phase5_backend import run_phase5b_normalization


def emit(payload, ok=True):
    out = dict(payload or {})
    out.setdefault('success', bool(ok))
    print(json.dumps(out, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Run Phase 5B normalization in an external process.')
    parser.add_argument('--gui-file', default='')  # compatibility; ignored
    parser.add_argument('--testnet-base', default='')
    parser.add_argument('--reason', default='manual')
    args = parser.parse_args()
    try:
        payload = run_phase5b_normalization(testnet_base=args.testnet_base, reason=args.reason or 'manual')
        emit(payload, ok=bool(payload.get('success')))
        return 0 if payload.get('success') else 1
    except Exception as exc:
        emit({
            'success': False,
            'task': 'phase5b-normalization',
            'result_text': str(exc),
            'traceback': traceback.format_exc(),
        }, ok=False)
        return 1


if __name__ == '__main__':
    sys.exit(main())
