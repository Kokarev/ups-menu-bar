# Linux NUT test environment

This tests the Python Linux console prototype in `linux/` and its NUT transport.
It is **not a build of the macOS Swift app**. The GUI still depends on AppKit.
The Python Tk desktop preview is tested using Xvfb. Swift portability, actual
UPS hardware, shutdown policy and production NUT services are not validated.

`xvfb-run -a python3 ci/nut_smoke.py` runs the GUI and real packaged `dummy-ups`, `upsd`, and `upsc` as the
current non-root user. Install `nut-server`, `nut-client`, and Python 3 first.
It uses temporary configs, loopback port 3493, no USB device and no control user.
It checks OL/OB/LB, voltage/load, absent versus zero battery values, a timed
OB-to-OL transition, unknown UPS, disconnected server and reconnection. It also
runs the actual Linux CLI, checks JSON output and CSV, and observes its recovery
after a live server restart without integrating energy across the gap. All its
processes stop on completion; `test-artifacts/nut-report.json` records results.
An existing server on port 3493 is an error; never stop it to run this test.

## ParserDev runner

Repository runner `ups-menu-bar-parserdev` uses `ci/runner/Dockerfile`, based on
the official GitHub runner image. One job at a time. Container limits: 1 CPU,
2 GiB RAM, 256 PIDs; no host paths, Docker socket, published ports, host network,
host credentials or extra Linux capabilities. Only its own Docker-managed home
volume persists. Docker logs rotate (3 x 10 MiB). No changes to parser services.

Only trusted `main` pushes affecting CI or the Linux prototype and manual runs from `main` are enabled.
There are deliberately no pull_request, pull_request_target, issue-comment or
workflow_run triggers. Never run fork/PR code on ParserDev. This is not a VM
security boundary; anyone allowed to change trusted workflows must be trusted
with the runner. No repository secrets are needed. The job token is read-only
and checkout does not store credentials. Review future workflow changes for
these restrictions. Do not add privileged mode or mount the Docker socket.

Container name: `ups-menu-bar-ci-runner`; image: `ups-menu-bar-ci:2.338.2-gui`;
volume: `ups-menu-bar-ci-home`. Runner updates are disabled inside jobs: rebuild
with a supported official runner image and recreate the container deliberately
before GitHub's runner version expiry. Docker restart policy is unless-stopped.
The latest GUI screenshot is overwritten at `/home/runner/ups-preview/linux-gui.png`
inside this container; no GitHub artifact or cache storage is used. The container
uses Docker's `--init` to reap children and handle virtual-display signals.

Read status: `docker logs --tail 30 ups-menu-bar-ci-runner` and GitHub Settings →
Actions → Runners. Stop only this runner: `docker stop ups-menu-bar-ci-runner`.
Do not remove its volume without explicitly retiring the registration.

The image build and registration are infrastructure administration steps;
workflows cannot build containers or reach the host Docker daemon.
