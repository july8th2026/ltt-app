# VPS V4 — Final Red-Team Questions (offline checkpoint)

This is an offline software verdict. `PASS` means a behavior test or a
fail-closed implementation exists on this branch; it is not live OVH evidence.

| §68 question | Verdict | Independent evidence / remaining gate |
|---|---|---|
| Can changing default move an existing VPS accidentally? | PASS | Existing instances retain `infrastructure_profile_id`; selector/default tests in `test_1010` and pinned-job tests in `test_1013`. |
| Can two jobs receive the same IPv4? | PASS offline | Conditional locked allocation plus unique reservation token; SQLite behavior and opt-in two-worker PostgreSQL tests in `test_1011`/`test_1010`. |
| Can an OVH IP be paid for but forgotten by DB? | BLOCKED live, fail-closed | Normal OVH provisioning only reserves a pre-owned DB pool row. Provider ordering is absent and remains a separate audited D10/P7 operation; no code may claim a paid-IP purchase yet. |
| Can a provider timeout create a duplicate resource? | PASS for OVH static path; BLOCKED for dynamic Vultr | OVH has no provider-create call and external mutations use durable intent/read-back. Dynamic Vultr purchase lacks exact label recovery, therefore Vultr remains STANDBY/not accepting new production. |
| Can gateway mapping point at the wrong VM? | PASS offline | `PUBLIC_MAPPING` journals exact public/private pair and requires canonical gateway read-back; ambiguous result becomes `NEEDS_REVIEW`. |
| Can a disabled profile still receive new VPS? | PASS | Selector excludes it and mutation coordinator rechecks profile status immediately around external mutations (`test_1021`). |
| Can a customer force a `profile_id`? | PASS | Customer POST does not accept infrastructure profile/provider/gateway; server resolves and pins it (`test_1016`, browser regression). |
| Can an API key create VPS? | PASS | VPS is explicitly `WEB_ONLY`; route/catalog/API-key tests in `test_1016`. |
| Can Vultr still work after the abstraction? | PASS adapter / STANDBY rollout | Existing client operations are wrapped by contract tests in `test_1011`; dynamic acquisition is deliberately not enabled for new production until timeout recovery closes. |
| Can OVH operate without a Vultr-specific assumption? | PASS contract; BLOCKED live gateway | Static pool source has no Vultr field/operation (`test_1011`). Actual `gwnat` adapter waits for B06 baseline and cannot use legacy nft map names. |
| Can Machine B go stale while App thinks it is healthy? | PASS | Strict four-artifact generation/schema/freshness checks; future/mixed/stale/inconsistent revision cases fail closed (`test_1012`, `test_1014`). |
| Can worker death leave a paid IP orphan? | BLOCKED for paid acquisition | OVH provisioning uses pre-owned rows and quarantine. Paid acquisition is not exposed; dynamic Vultr stays STANDBY until provider-label recovery is durable. |
| Can destroy remove the wrong IP? | PASS offline | Pinned profile, VM ownership, pool-row/resource selection and reservation ownership are checked; ambiguous cleanup retains both addresses as `QUARANTINED` (`test_1013`, `test_1023`). |
| Can VM100–VM107 be touched by the test? | PASS offline | Protected-range guard executes before inventory/network mutation and has negative tests in `test_1023`; no live VM/IP has been created. |
| Can secrets appear in logs or commits? | PASS current V4 paths | Mutation/admin/SSH/provider failure bodies are redacted; paired behavior tests require a stable code+exception class while rejecting the raw provider URL/body. Post-freeze scans: 3,283 files/790,918 then 790,922 lines after annotation; both zero findings. |

## P0/P1 software verdict

No known P0 defect exists in the enabled OVH static-pool software path. The two
paid-provider questions remain explicit rollout blockers, not waived findings:
Vultr cannot accept new production instances and OVH acquisition cannot be
implemented or invoked until the actual provider mechanism and fresh inventory
are verified. B02–B07 in `09_BLOCKERS.md` continue to block live acceptance and
canonical integration.
