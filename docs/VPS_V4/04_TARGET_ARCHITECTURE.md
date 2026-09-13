# VPS V4 — Target Architecture

```text
customer request(region, plan, OS)
  -> ProfileSelector (ACTIVE + accept_new + healthy + region)
  -> persist VpsInstance.infrastructure_profile_id
  -> enqueue
  -> ProvisioningCoordinator (always loads pinned profile)
       |-> ComputeBackend: ProxmoxComputeBackend
       |-> PublicIpBackend: VultrReservedIpBackend | OvhStaticIpPoolBackend
       `-> GatewayBackend: NftGatewayBackend
  -> external mutation journal + read-back + reconciliation
```

## Durable model

### `VpsInfrastructureProfile`

Relational fields: `id`, unique `slug`, `name`, `region`, `environment`,
`status`, `accept_new`, `is_default`, three backend type discriminators,
`credential_ref`, timestamps, `last_health_at`, `config_version`.

Backend-specific, non-secret config may live in three JSON objects
(`compute_config`, `network_config`, `provider_config`) because keys differ by
backend. Selector/state/default/identity fields remain relational. Config stores
service identifiers, paths and secret *references*, never secret values.

DB invariants:

- partial unique index allows 0/1 row where `is_default=true`;
- check: default implies ACTIVE and `accept_new=true`;
- check: non-ACTIVE cannot accept new; ACTIVE may be fail-closed with
  `accept_new=false` after health/config failure;
- service transaction locks candidate/default rows, runs fresh preflight and
  fails closed before activation/default.

### Instance pin

Add nullable-at-migration `vps_instance.infrastructure_profile_id` with FK and
index. Backfill proven legacy Vultr rows. New create service requires non-null
before enqueue. A later migration may make it NOT NULL only after production
inventory has zero `NEEDS_REVIEW`; the first additive migration must not guess.

### Public IP inventory

Evolve `vps_ip` additively with `infrastructure_profile_id`,
`backend_resource_id`, lifecycle (`FREE/RESERVED/BOUND/QUARANTINED`),
`reservation_token`, `reserved_at`, `bound_at`, `last_observed_at`, cost metadata
and sanitized provider metadata. Preserve `vultr_id` until verified migration.

PostgreSQL constraints/indexes enforce one live instance per address/profile and
one live public IP per instance. Reservation takes a locked FREE row
(`FOR UPDATE SKIP LOCKED`) then commits a unique token before returning. SQLite
tests use an atomic conditional update equivalent.

### External mutation journal

`VpsExternalMutation`: operation/instance/profile, step, deterministic
`idempotency_key`, state (`INTENT/REQUESTED/OBSERVED/COMPENSATED/FAILED/
NEEDS_REVIEW`), request fingerprint, sanitized external reference, attempts,
timestamps and last sanitized error. Unique idempotency key prevents a retry
from forgetting the first attempt.

### Profile health

Latest per-component observations are durable: component (`compute/ip/gateway/
network/capacity/runtime`), status (`UNKNOWN/STALE/HEALTHY/DEGRADED/CRITICAL`),
observed/generated timestamps, sanitized summary and provenance. Aggregate
health is computed per profile; one profile cannot poison another.

## Backend contracts

- `ComputeBackend`: create/configure/start/stop/restart/destroy/status/snapshot/
  restore/capacity. Proxmox wrapper delegates to current proven client.
- `PublicIpBackend`: reserve/bind/unbind/release/get/list/health/capabilities.
  OVH static pool has no dynamic purchase capability; a separate operator
  acquisition service may order at most D10 and journals cart/checkout/readback.
- `GatewayBackend`: ensure/remove/get/list/verify mapping/health. nft commands
  stay inside current gateway client wrapper.

Capability differences are explicit, not faked. Unsupported snapshot/restore
may return a typed unsupported result and the contract test records why.

## State behavior

| State | New instances | Existing lifecycle | Health/reconcile | Normal background mutation |
|---|---|---|---|---|
| ACTIVE | allowed iff `accept_new` and healthy | yes | yes | yes |
| DRAINING | no | yes | yes | yes for pinned instances |
| STANDBY | no | controlled existing only | yes | yes for pinned resources |
| DISABLED | no | blocked except emergency/explicit operator recovery | read-only checks yes | no |

If DISABLED appears mid-job, coordinator stops before the next mutation and
records a recoverable blocked state. Already-created resources are not silently
deleted; reconciliation/explicit compensation remains possible.

## Provision ordering and crash safety

1. Validate owner/region/plan/OS; ignore/reject profile/provider input.
2. Select healthy ACTIVE profile in a locked transaction.
3. Persist instance + profile ID; enqueue.
4. Capacity/preflight read-back; allocate VMID.
5. Journal intent, create blank VM, read back VM identity.
6. Journal/configure private network and DHCP, read back.
7. Reserve one pre-owned public IP transactionally.
8. Ensure gateway mapping, verify exact public→private identity.
9. Boot, await task, observe actual state.
10. Finalize operation and instance.

This orders scarce-but-pre-owned IP after compute/network creation, minimizing
long reservations, and maps before boot so a booted customer VM cannot escape
through an unintended path. No dynamic paid IP order occurs inside this flow.

## Machine B contract

App reads Machine B artifacts through a configured read-only integration path.
It requires supported schema, matching generation timestamp across inventory/
health/capabilities, collector success, and freshness. It exposes app SHA,
Machine B SHA, schema and generated time to operators. Collector logic remains
in the infrastructure repo.

## Access and API

- Authenticated-only MVP and canonical user-ID allowlist.
- Admin remains permitted by platform convention.
- No request model accepts profile/provider/gateway.
- No VPS ToolSpec/public API route/catalog entry; API keys cannot mutate VPS.
- C01 approved a generic `AppManifest.admin_nav` extension. Request-scoped app
  context renders exact `ADMIN > VPS > Cổng hạ tầng`; server has no VPS import.
