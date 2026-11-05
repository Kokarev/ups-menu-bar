#!/usr/bin/env python3
"""Read-only Linux CLI prototype. Requires Python 3.9+ and NUT's upsc."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HEADER = ['timestamp', 'status', 'input_V', 'output_V', 'load_percent',
          'estimated_W', 'delta_Wh', 'battery_V']


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be a finite positive number')
    return number


def parse_reading(raw):
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError('expected a flat NUT object')
    except json.JSONDecodeError:
        if raw.lstrip().startswith('{'):
            raise ValueError('malformed NUT JSON')
        data = dict(line.split(':', 1) for line in raw.splitlines() if ':' in line)
    def number(key, required=False):
        value = data.get(key)
        if value is None:
            if required:
                raise ValueError('missing ' + key)
            return None
        try:
            parsed = float(value)
        except (ValueError, TypeError):
            parsed = float('nan')
        if isinstance(value, bool) or not math.isfinite(parsed):
            if required:
                raise ValueError('invalid ' + key)
            return None
        return parsed
    status = data.get('ups.status')
    if not isinstance(status, str) or not status.strip():
        raise ValueError('missing ups.status')
    result = {'status': status.strip(), 'input_V': number('input.voltage', True),
              'output_V': number('output.voltage'), 'load_percent': number('ups.load', True),
              'battery_V': number('battery.voltage'), 'battery_charge_percent': number('battery.charge'),
              'battery_runtime_s': number('battery.runtime'), 'temperature_C': number('ups.temperature'),
              'frequency_Hz': number('input.frequency')}
    if not 0 <= result['load_percent'] <= 100:
        raise ValueError('ups.load must be between 0 and 100')
    return result


class NutClient:
    def __init__(self, executable, target, timeout):
        self.executable, self.target, self.timeout = executable, target, timeout
        self.json_supported = True

    def run(self, json_mode):
        args = [self.executable] + (['-j'] if json_mode else []) + [self.target]
        return subprocess.run(args, text=True, capture_output=True, timeout=self.timeout)

    def read(self):
        if self.json_supported:
            result = self.run(True)
            message = (result.stderr + result.stdout).lower()
            unsupported = any(x in message for x in ['invalid option', 'illegal option',
                              'unknown option', 'unrecognized option', 'usage:'])
            if unsupported:
                self.json_supported = False
            elif result.returncode:
                raise RuntimeError(result.stderr.strip() or 'upsc failed')
            elif result.stdout.lstrip().startswith('{'):
                try:
                    return parse_reading(result.stdout)
                except ValueError:
                    # Retry damaged JSON once in text mode; probe JSON next time.
                    pass
            else:
                self.json_supported = False
        result = self.run(False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'upsc failed')
        return parse_reading(result.stdout)


class Energy:
    def __init__(self, rating):
        self.rating = rating
        self.previous = None

    def gap(self):
        self.previous = None

    def update(self, sample, monotonic):
        watts = None if self.rating is None else self.rating * sample['load_percent'] / 100
        delta = None
        if self.previous is not None and watts is not None:
            before, power = self.previous
            if monotonic > before:
                delta = (power + watts) / 2 * (monotonic - before) / 3600
        self.previous = None if watts is None else (monotonic, watts)
        return dict(sample, estimated_W=watts, delta_Wh=delta)


def open_csv(path):
    # Separate file: never point the Linux prototype at a live macOS history.
    handle = open(path, 'a+', newline='', encoding='utf-8')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.seek(0)
        existing = next(csv.reader(handle), None)
        if existing is not None and existing != HEADER:
            raise ValueError('CSV header differs; use a new file')
        handle.seek(0, 2)
        writer = csv.writer(handle)
        if existing is None:
            writer.writerow(HEADER)
            handle.flush()
        return handle, writer
    except Exception:
        handle.close()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ups', required=True, help='UPS name in ups.conf')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3493)
    parser.add_argument('--upsc', default='upsc', help='upsc executable name or path')
    parser.add_argument('--timeout', type=positive, default=3.0)
    parser.add_argument('--interval', type=positive, default=5.0)
    parser.add_argument('--rated-watts', type=positive)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--count', type=int, default=0, help='poll attempts, 0 means continuous')
    parser.add_argument('--csv', type=Path, help='optional new Linux history file')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', args.ups):
        parser.error('invalid UPS name')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', args.host):
        parser.error('host must be an IPv4 address or DNS name (IPv6 not yet supported)')
    if not 1 <= args.port <= 65535 or args.count < 0:
        parser.error('invalid port or count')
    if args.rated_watts is not None and not 1 <= args.rated_watts <= 100000:
        parser.error('rated watts must be between 1 and 100000')
    executable = shutil.which(args.upsc)
    if not executable:
        parser.error('upsc is not installed or not executable')
    target = f'{args.ups}@{args.host}:{args.port}'
    client = NutClient(executable, target, args.timeout)
    energy = Energy(args.rated_watts)
    handle, writer = open_csv(args.csv) if args.csv else (None, None)
    attempts, failed = 0, False
    try:
        while True:
            started = time.monotonic()
            try:
                sample = energy.update(client.read(), time.monotonic())
                timestamp = datetime.now(timezone.utc).isoformat()
                sample = dict(sample, timestamp=timestamp)
                if writer:
                    writer.writerow(['' if sample[k] is None else sample[k] for k in HEADER])
                    handle.flush()
                event = dict(sample, connected=True, target=target)
                failed = False
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                energy.gap()
                event = {'timestamp': datetime.now(timezone.utc).isoformat(), 'connected': False,
                         'target': target, 'error': str(exc)}
                failed = True
            print(json.dumps(event, ensure_ascii=False, allow_nan=False), flush=True)
            attempts += 1
            if args.once or (args.count and attempts >= args.count):
                return 1 if failed else 0
            time.sleep(max(0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        return 130
    finally:
        if handle:
            handle.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
