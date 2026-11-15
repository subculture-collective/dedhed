# Public audio core deployment

The production recipe serves the two reviewed pilot recordings through the pinned
Arkhiv audio core. The frontend image and its API paths stay unchanged. This
cutover adopts current Dedhed source's corrected venue/date filters and stricter
validation, as selected by the owner; it does not reproduce those older live bugs.

On Almaz, `/mnt/spektr/server/data/dedhed-core/compose.yml` is installed from
[the Compose recipe](../deploy/core-compose.yml). Its private database uses the
owner role `core`; the public server uses only `arkhiv_reader`. Both media mounts
are read-only. The copied originals live under `originals/`; the already reviewed
derivatives stay in `~/.local/state/dedhed-public-20261004/media`.

The host-owned `.env` selects the immutable engine pin, derivative root and
private subnet. Credentials are mounted files beneath `runtime/`; never copy
them into Git. The core database subnet is 10.254.70.0/24. The external, internal
Docker network `dedhed-core-public` uses 10.254.71.0/24. It gives the core the
`api` alias expected by the unchanged frontend. The web container also retains
its `media` network for the public reverse proxy.

## Qualification and activation

The November 15 rehearsal compared 116 route pairs with current Dedhed source,
verified multipart audio bodies, and observed 60 successful station polls.
The unchanged production web image passed full-recording, Set II, station,
calendar and date-page browser checks. A fresh legacy fingerprint matched the
rehearsal; the dedicated core restore matched all 46 tables and 33 original files.

Before switching the web container's API network, retain its legacy Compose
configuration and receiver profile in the host cutover directory. Connect
`dedhed-core-public`, disconnect `dedhed-public-20261004_catalog`, and reload
nginx to clear cached API addresses. Update the frontend receiver's Compose
network and runtime guard to the same shape so later frontend deployments retain
the selected backend. Check the public version, readiness, catalog, audio ranges,
station timeline, calendar, date pages and actual browser playback.

## Automatic updates

[Deploy](../.github/workflows/deploy.yml) deploys the pinned engine through the
separate `dedhed-core` fleet receiver and `HOMELAB_CORE_DEPLOY_KEY`. Enable
`CORE_DEPLOY_ENABLED=true` only after registering the host profile and qualifying
the public route. Each update backs up the core database, runs additive migrations
with the owner role, activates the image and checks public readiness and version.
The [wrapper](../deploy/core.Dockerfile) changes labels only; CI verifies that its
layers equal the pinned image and records successful core deployments.

The key belongs to the homelab operator and is restricted to tailnet addresses
and the Dedhed core receiver. Rotate by 2027-02-03: install a replacement restricted
key, update the GitHub Actions secret, prove a successful deployment, then remove
only the superseded Dedhed key. Never reuse the general operator SSH identity.

## Scheduled operations and recovery

Install [core_runtime.py](../scripts/core_runtime.py) in the production root.
The existing five-minute monitor invokes its `monitor` action. The 00:25 Central
replay timer invokes `replay`, which runs `renew-public-audio` with the explicit
two-recording `runtime/selection.json` and a 168-hour horizon. Renewal verifies
current approvals and audio integrity; it neither discovers nor acquires media.
The imported timeline remains unchanged at cutover; the next scheduled renewal
has the same deliberate refresh behavior as the legacy daily job.

The shared 00:30 Central archive backup includes the dedicated Dedhed core
database and copies it to NUC. The existing 00:45 Dedhed backup retains the legacy
database and reviewed derivatives. Preserved originals and the original recovery
checkpoint remain independently backed up. The receiver also runs
[the pre-deployment backup](../deploy/core-predeploy-backup.sh).

For rollback, disable core deployment and stop the replay timer, reconnect the
web container to `dedhed-public-20261004_catalog`, disconnect
`dedhed-core-public`, and reload nginx. Restore the saved frontend receiver
Compose/profile pair so subsequent web deployments retain legacy routing.
Restore the legacy monitor/replay service definitions, then enable those timers.
The legacy API, database, media and imported schedule are retained. If the legacy
schedule has expired, renew its same two-recording selection before resuming
station service. No core database restore is needed to return to legacy.

Record live cutover, rollback exercise, automatic deployment and off-host restore
results in the private homelab report. Source checks, CI and browser playback are
separate evidence; a successful image build alone is not a completed deployment.

