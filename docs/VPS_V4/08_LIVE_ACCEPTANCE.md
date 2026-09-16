# VPS V4 — Live Acceptance Runbook

Cập nhật 2026-09-16 (tối): **VPS thật `d96b66f3` (VM 204) đã tạo với một IPv4 OVH
(đơn 22703620)**; bước 1–4 đạt, bước 5/7 phát hiện R20/R21 (đã sửa, chờ deploy),
bước 6/8/9 còn lại — theo dõi ở `14_KE_HOACH_VAN_HANH_TOI_UU.md` §6 G7. Mô tả
dưới đây là trạng thái lúc kích hoạt.

Trạng thái: **ACTIVATION COMMITTED 2026-09-15T17:29:03Z — OVH 0402 ACTIVE +
DEFAULT (config v3, backend `ovh_static_pool`, mapping `ovh_gwnat`), Vultr 0401
STANDBY (v2, accept_new off); 6×HEALTHY preflight persisted in one audited
transaction; gateway helper installed. No IP/VM or mapping created yet.
Browser E2E driver built and armed; awaiting the test-account credential file;
live cart `f99ebe5c` expires 2026-09-16T11:54:01Z.**

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
  **Superseded:** expired without checkout; the live Layer-2 cart is
  `f99ebe5c-ce11-4af4-9ec3-383706ed8508` (item 91826398, qty 1, USD,
  with_tax_minor 239, fingerprint `3d6ddf49…69`, expires
  `2026-09-16T11:54:01Z`), recorded as `adopt_ip_cart_id` in the committed
  OVH profile provider_config.
- [ ] Q130 automatic guarded checkout/payment and exact provider delivery via
  the paid web provisioning job. Finish integration before enabling; revalidate
  the existing cart and enforce the one-IP live limit, never blind-retry checkout.
- [x] Install the fail-closed `ltt-gwnat` helper on the live gateway. Health
  returned `ok`; protected removal returned RC 5; a conflicting ensure returned
  RC 4. Both protected mapping files retained SHA-256
  `5ebaf20b44b74fc7a3379e2d2a7dca2357f70b85f6b33f281fd75ad813241766`.

## Activation

- [ ] Import/register intended IP as FREE with provider read-back. (Pending —
  the IP is acquired live by `checkout_cart` during the E2E create, not before.)
- [x] Run OVH profile preflight and persist component results. 6×HEALTHY rows
  for profile 0402 committed at `2026-09-15T17:29:03Z`; re-verified read-only
  at the same minute.
- [x] Set OVH ACTIVE/default and Vultr STANDBY in one audited transaction.
  Single commit at `2026-09-15T17:29:03Z`: 0402 ACTIVE, accept_new on, default,
  config v3, backend `ovh_static_pool`, mapping `ovh_gwnat`; 0401 STANDBY v2,
  accept_new off, not default.
- [ ] Confirm owner-only/authenticated policy from a normal-user session.
  (Covers E2E steps 1–3 as user `akakenly.design@gmail.com`.)

## Browser E2E

**Protocol override (owner, 2026-09-16, UTC+7):** the agent launches Chrome
itself via Playwright, obtains the test account from the system and logs in
itself. The driver
(`D:/LTTSTUDIOSAPP-runtime/vps-v4-e2e-drive.mjs`) reads the credential from
`C:/LTTPlatform/secrets/ltt_d09_pass.txt` (line 1 = email
`akakenly.design@gmail.com`, line 2 = password, UTF-8 no BOM) or from
`LTT_SMOKE_USER`/`LTT_SMOKE_PASS`, substitutes it only at fill time, and never
writes it to any log, screenshot or report. The previous "PO starts the smoke
command" procedure is superseded. After authenticated state is available, the
run must:

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

LOCKED by PO 2026-09-14: retain exactly the acceptance VM stopped, retain its IP
BOUND to that VM and preserve its mapping for continued inspection. Verify PVE
stopped state, DB/UI state and exact IP ownership/read-back. Destruction,
unbind/release or deletion is not authorized by test completion.

## Evidence artifact

Record IDs, timestamps, states and sanitized screenshots. Public IP may be
recorded in the restricted operational artifact if necessary, but final report
should prefer resource ID/redacted address. Never record credentials.
