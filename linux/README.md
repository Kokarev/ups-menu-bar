# Linux console prototype

Experimental read-only client, not a graphical Linux release. Python 3.9+ and
NUT's `upsc` are required (`nut-client` on Debian/Ubuntu). No Python packages,
root access, USB access or changes to the NUT server are required.

One sample (one JSON object, UTC timestamp):

```sh
python3 linux/ups_menu_bar.py --ups myups --host 127.0.0.1 --once
```

Continuous polling, every 5 seconds, with a new Linux-only CSV:

```sh
python3 linux/ups_menu_bar.py --ups myups --host nut.example.org \
  --rated-watts 400 --csv ./linux-history.csv
```

Replace the name, server and nominal output watts with the actual configuration.
Omit `--rated-watts` when unknown: estimated watts and energy will remain absent.
Use Ctrl+C to stop, or `--count 12` for twelve poll attempts. `--port`, `--interval`,
`--timeout` and `--upsc /absolute/path` are available; see `--help`.

Successful samples include OL/OB/LB status, voltage/load, available battery
values, frequency and temperature. Absent optional values are JSON null / empty
CSV cells, never fabricated zeros. Each failure prints connected=false with an
error and no stale telemetry; continuous mode retries. --once exits 1 on failure,
0 on success; bounded polling exits according to its last attempt. Invalid
arguments exit 2. Ctrl+C exits 130.

Energy uses trapezoidal integration of estimated watts with monotonic elapsed
time. The first sample and the first sample after any failed poll have no energy
interval. It is an estimate of UPS output energy, not a wall energy meter.
CSV has the same eight columns as macOS history, but must use a separate file.
Existing headers are validated; a nonblocking advisory lock prevents two copies
of this prototype writing the same file. Historical intervals are not backfilled
across restarts. No outage event log, daily/monthly totals or GUI is included yet.

Host accepts IPv4 addresses/DNS; IPv6 and authenticated/TLS NUT are not supported
by this prototype. Use a trusted local network or an existing secure tunnel;
do not expose a NUT server to the public internet to run this client.

CI runs parser/energy/CSV tests plus this actual CLI against real dummy-ups and
upsd, including a live server disconnect/restart and CSV recovery. It does not
certify physical UPS compatibility or the macOS GUI.
