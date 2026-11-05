#!/usr/bin/env python3
"""Exercise real NUT dummy-ups -> upsd -> upsc; no physical UPS or control commands."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time


def main():
    # Refuse to overlap an existing NUT service; never signal foreign processes.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 3493))
    checks = []
    processes = []
    logs = []
    report = Path(os.environ.get('NUT_CI_REPORT', 'test-artifacts/nut-report.json'))
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ups-menu-bar-nut-') as temporary:
        root = Path(temporary)
        env = dict(os.environ, NUT_CONFPATH=str(root), NUT_STATEPATH=str(root),
                   NUT_ALTPIDPATH=str(root), NUT_QUIET_INIT_UPSCLI='1')
        username = subprocess.check_output(['id', '-un'], text=True).strip()
        upsc = shutil.which('upsc')
        # Debian/Ubuntu /usr/sbin/upsd can be a service-mode wrapper which
        # ignores NUT_CONFPATH. Invoke the packaged server binary directly.
        upsd = next((p for p in ['/usr/lib/nut/upsd', '/lib/nut/upsd'] if Path(p).exists()), None)
        driver = next((p for p in ['/usr/lib/nut/dummy-ups', '/lib/nut/dummy-ups'] if Path(p).exists()), None)
        if not upsc or not driver or not upsd:
            raise RuntimeError('Install nut-client and nut-server; dummy-ups is required')

        def start(argv, name):
            log = open(root / (name + '.log'), 'w+')
            logs.append((name, log))
            process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            processes.append(process)
            return process

        def query(name, variable=None):
            args = [upsc, name + '@127.0.0.1:3493']
            if variable:
                args.append(variable)
            return subprocess.run(args, env=env, text=True, capture_output=True, timeout=5)

        def values(name):
            result = query(name)
            if result.returncode:
                return None
            return dict(line.split(': ', 1) for line in result.stdout.splitlines() if ': ' in line)

        def await_values(name, predicate, seconds=15):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                data = values(name)
                if data is not None and predicate(data):
                    return data
                time.sleep(.25)
            raise AssertionError('NUT scenario did not become ready: ' + name)

        def check(name, condition):
            if not condition:
                raise AssertionError(name)
            checks.append(name)
            print('PASS:', name, flush=True)

        fixtures = {
            'online': 'ups.status: OL\ninput.voltage: 227.2\nups.load: 3\nbattery.voltage: 13.5\n',
            'battery': 'ups.status: OB\ninput.voltage: 0\nups.load: 25\nbattery.voltage: 12.4\nbattery.charge: 75\nbattery.runtime: 600\n',
            'low': 'ups.status: OB LB\ninput.voltage: 0\nups.load: 25\nbattery.charge: 10\nbattery.runtime: 60\n',
            'zero': 'ups.status: OL\ninput.voltage: 230\nups.load: 0\nbattery.charge: 0\nbattery.runtime: 0\n',
            'cycle': 'ups.status: OL\ninput.voltage: 230\nups.load: 10\nTIMER 4\nups.status: OB\ninput.voltage: 0\nTIMER 4\nups.status: OL\ninput.voltage: 230\nTIMER 4\n',
        }
        config = ['pollinterval = 1']
        for name, data in fixtures.items():
            source = root / (name + ('.seq' if name == 'cycle' else '.dev'))
            source.write_text(data)
            mode = 'dummy-loop' if name == 'cycle' else 'dummy-once'
            config.append(f'[{name}]\n driver = dummy-ups\n port = {source}\n mode = {mode}\n')
        (root / 'ups.conf').write_text('\n'.join(config))
        (root / 'upsd.conf').write_text(f'LISTEN 127.0.0.1 3493\nSTATEPATH {root}\n')
        (root / 'upsd.users').write_text('# No login or write/control user in this test server.\n')
        error = None
        try:
            for name in fixtures:
                start([driver, '-F', '-u', username, '-g', username, '-a', name], 'driver-' + name)
            server = start([upsd, '-F', '-u', username], 'upsd')
            online = await_values('online', lambda d: d.get('ups.status') == 'OL')
            check('online voltage and load preserved', float(online['input.voltage']) == 227.2 and float(online['ups.load']) == 3)
            check('missing charge/runtime remain absent', 'battery.charge' not in online and 'battery.runtime' not in online)
            battery = await_values('battery', lambda d: d.get('ups.status') == 'OB')
            check('on battery telemetry', float(battery['battery.charge']) == 75 and float(battery['battery.runtime']) == 600)
            low = await_values('low', lambda d: 'LB' in d.get('ups.status', '').split())
            check('low battery flags', set(low['ups.status'].split()) == {'OB', 'LB'})
            zero = await_values('zero', lambda d: d.get('ups.status') == 'OL')
            check('real zero is not missing', all(float(zero[k]) == 0 for k in ['ups.load', 'battery.charge', 'battery.runtime']))
            check('unknown UPS fails explicitly', query('not-configured').returncode != 0)
            await_values('cycle', lambda d: d.get('ups.status') == 'OB', seconds=20)
            await_values('cycle', lambda d: d.get('ups.status') == 'OL', seconds=20)
            check('mains returns after battery state', True)
            server.terminate()
            server.wait(timeout=5)
            check('connection loss fails explicitly', query('online').returncode != 0)
            start([upsd, '-F', '-u', username], 'upsd-restarted')
            await_values('online', lambda d: d.get('ups.status') == 'OL')
            check('connection recovers after server restart', True)
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            for name, log in logs:
                log.seek(0)
                if error:
                    print(name + ':\n' + log.read()[-6000:])
                log.close()
            report.write_text(json.dumps({'passed': error is None, 'checks': checks, 'error': error,
                                          'scope': 'Real NUT transport smoke test; no Linux GUI or macOS app tests.'}, indent=2) + '\n')
    print('NUT CI PASS:', len(checks), 'checks')


if __name__ == '__main__':
    main()
