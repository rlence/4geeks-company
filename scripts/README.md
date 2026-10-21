# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

> _Spanish version: [README.es.md](./README.es.md)._

## Nightly telemetry export

`nightly_export.py` exports the previous UTC day's telemetry to a private CSV,
runs the existing weekly Prefect pipeline as a subprocess, and records status in
`public.job_runs`. It is invoked outside FastAPI by system cron. Setup, retries,
and validation: [`docs/telemetry/nightly-job.md`](../docs/telemetry/nightly-job.md).
