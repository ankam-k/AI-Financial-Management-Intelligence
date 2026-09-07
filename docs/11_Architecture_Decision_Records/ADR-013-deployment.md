# ADR-013 — Docker Compose, single-host deployment for V1

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** PDR-002, PDR-024, NFR-7 · **Closes:** D-18

## Decision

Deploy as a **Docker Compose stack on a single host**: API, PostgreSQL, Ollama, and a reverse proxy serving the static frontend. No orchestrator, no managed services, no cloud provider dependency.

## Context

PDR-024 requires user financial data to remain private, and ADR-008 places model inference locally for that reason. That decision largely settles deployment: if inference must be local, the stack must run somewhere we control, and the host needs enough RAM for a 7B model.

V1 has no scale requirement. The workload is per-user analysis runs on modest data volumes.

## Alternatives

**A. Managed PaaS + hosted model API.** Least operational work. Rejected: the hosted model conflicts with PDR-024/PDR-034🟠, and ADR-008 already foreclosed it.

**B. Kubernetes.** Right answer at scale, real HA, rolling deploys. Wrong answer here — a cluster to run one API, one database and one model server is precisely the over-engineering PDR-004 warns against, and PDR-002 names maintainability as the tiebreaker.

**C. Docker Compose, single host.** One file describes the whole system. Trivially reproducible locally and in production. No HA; the host is a single point of failure.

**D. Bare-metal systemd services.** No container overhead, fastest inference. Poor reproducibility; environment drift between dev and prod is the classic failure.

**E. Compose now, with a documented migration path.** C plus explicit acknowledgement of what changes when scale arrives.

## Tradeoffs

| Gain | Cost |
|---|---|
| Dev and prod run the identical Compose file — no drift | No high availability; host failure is total outage |
| Model stays on our infrastructure (PDR-024) | Host must provide ~16GB RAM for the 7B model |
| One artifact a reviewer can run with a single command | Manual deploys; no rolling updates |
| No cloud lock-in; portable to any Linux host | Vertical scaling only |
| Backup is a `pg_dump` and a volume snapshot | Backup/restore is operator-run, not managed |

## Final Choice

**E — Docker Compose on a single host, with the scale-out path documented rather than built.**

The reviewer-experience argument carries real weight given this project's secondary audience: `docker compose up` producing a working system with seeded synthetic data (PDR-012) is a materially better demonstration than a cluster nobody can run.

## Consequences

- `docker/docker-compose.yml` defines: `api`, `db` (PostgreSQL 16), `ollama`, `proxy` (Caddy or nginx serving the frontend bundle and terminating TLS).
- Ollama pulls the model on first start; documented as a one-time setup cost.
- Database migrations run via an Alembic entrypoint before the API starts.
- Synthetic datasets seed automatically on first run, so the app is explorable immediately (PDR-012, FR-1.10).
- Secrets come from environment/`.env`, never committed.
- Backups are documented operator procedures in `10_Deployment.md`, not automated in V1.
- The API is stateless, so horizontal scaling later requires only moving Postgres and Ollama to their own hosts — no application change.
- Health checks on all four services; the API reports the model as degraded rather than failing when Ollama is unreachable (NFR-7).
