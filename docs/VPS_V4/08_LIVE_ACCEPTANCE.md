# VPS V4 — Live Acceptance Runbook

Trạng thái: **PREFLIGHT PARTIAL; GATEWAY HELPER INSTALLED; ONE UNPAID OVH CART
PREPARED; NO IP/VM OR MAPPING CREATED**.

## Hard guards

- Maximum one new OVH IPv4 and one new test VM.
- Refuse VMID 100–107 and refuse any IP/mapping currently associated with them.
- New resources carry a unique V4 acceptance label and journal operation ID.
- No secret appears in command output, screenshot, log or report.
- Stop at login/MFA/CAPTCHA, unexpected billing quote, downtime/reboot/WAN-cut,
  restore boot, or ambiguous destructive ownership.

## Read-only preflight

- [ ] Record deployed app SHA/schema and Machine B SHA.
- [x] Access `H:\PROXMOX`; run canonical collector from that tree. One coherent
  success generation was published at `2026-09-14T03:06:29Z`. A later manual
  refresh hung in the PVE read step and was terminated without publication or
  mutation; freshness must therefore be repeated at activation.
- [x] Verify supported schema, one generation and completed collector semantics:
  exit 0/1/2 are completed health verdicts; exit 3 is collector failure.
- [x] Verify PVE CA/host identity and read compute/storage/network/WG/gateway.
  TLS chain/name probe reached HTTP 401 with an intentionally invalid token.
- [x] Query OVH service and Additional IP inventory; all eight failover IPv4 are
  routed and already mapped, leaving zero intended FREE IP.
- [x] Read back VM100–107 and their eight exact mappings unchanged/protected.
- [x] Resolve exactly one canonical user for the approved email; count is one
  and only its canonical ID was returned. No credential/email list was emitted.
- [x] Prepare exactly one D10 order without checkout. Cart
  `efae624e-6114-46b9-ace5-3063f9fc1580` contains quantity 1 of
  `ip-failover-arin`, location SG/SGP, routed to the current gateway service;
  provider quote was USD 2.39 including tax and the response confirmed
  `checkout_performed=false`. The cart expires `2026-09-15T08:53:23Z`.
- [ ] Manual checkout/payment and provider delivery. The agent must not create a
  replacement cart or submit checkout automatically.
- [x] Install the fail-closed `ltt-gwnat` helper on the live gateway. Health
  returned `ok`; protected removal returned RC 5; a conflicting ensure returned
  RC 4. Both protected mapping files retained SHA-256
  `5ebaf20b44b74fc7a3379e2d2a7dca2357f70b85f6b33f281fd75ad813241766`.

## Activation

- [ ] Import/register intended IP as FREE with provider read-back.
- [ ] Run OVH profile preflight and persist component results.
- [ ] Set OVH ACTIVE/default and Vultr STANDBY in one audited transaction.
- [ ] Confirm owner-only/authenticated policy from a normal-user session.

## Browser E2E

The PO starts the canonical smoke command with `LTT_SMOKE_USER` and
`LTT_SMOKE_PASS`; the agent reads the generated report. The agent does not type
the password. After authenticated state is available, Playwright must:

1. Open real `/vps`, select region/plan/OS, submit create.
2. Assert no provider/profile/gateway control or request field.
3. Observe operation/job and owner/profile IDs from authorized UI/admin evidence.
4. Await PVE task/read-back, private address, one OVH public IP and verified map.
5. Open console; capture Windows installer and visible disk.
6. Verify public ingress, guest outbound public identity, private path, WG and no
   unintended home-ISP egress.
7. Stop, start and restart; for each compare operation, UPID, task result,
   actual PVE state, DB state and UI.
8. Switch default OVH→Vultr without provisioning, prove instance profile remains
   OVH, then restore OVH default/Vultr standby.
9. Inspect browser console and failed network requests.

## Cleanup gate

Default proposal is retain the VM stopped until the PO completes/abandons manual
Windows installation. If PO selects destroy, verify in order: exact ownership,
VM absent, DHCP/private IP released, nft mapping absent, public IP FREE (not
deleted unless explicitly authorized), DB state terminal and reconciliation
clean. Never infer cleanup permission from test completion.

## Evidence artifact

Record IDs, timestamps, states and sanitized screenshots. Public IP may be
recorded in the restricted operational artifact if necessary, but final report
should prefer resource ID/redacted address. Never record credentials.
