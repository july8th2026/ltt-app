# VPS V4 — Failure and Compensation Matrix

This is the offline implementation checkpoint, not live evidence. `OBSERVED`
always means an independent canonical read-back matched the pinned instance.

| Step | External change | Durable point | Retry rule | Compensation/reconciliation |
|---|---|---|---|---|
| VMID/private IP allocation | DB only | transaction/unique constraint | return same allocation | no external compensation |
| VM create | Proxmox VM | mutation `REQUESTED` committed first | accept only canonical name plus derived SMBIOS UUID; unreadable or mismatch stops | ambiguous response becomes `NEEDS_REVIEW`; never delete by VMID/label alone |
| VM configuration | Proxmox config/NIC | mutation `REQUESTED` first | compare all owned config fields and absence of deleted NICs | mismatch/unknown becomes `NEEDS_REVIEW` |
| DHCP + bandwidth counters | router file/nft sets | mutation `REQUESTED` first | exact MAC→private-IP and counter membership; conflicting MAC/IP stops before write | reconcile router with pinned DB identity; never overwrite a conflicting reservation |
| OVH pool reserve/bind | DB row only | locked conditional state transition | reservation token returns same row | quarantine on ambiguous downstream state; no provider delete |
| Vultr IP reserve | paid provider resource | legacy DB write immediately after response | no automatic POST retry | **open**: durable provider-label read-back journal required before Vultr can accept new production |
| Gateway public mapping | nft/persistence state | mutation `REQUESTED` first | exact public→private read-back | mismatch/unknown `NEEDS_REVIEW`; no auto-delete |
| VM boot | Proxmox power | mutation `REQUESTED` first | observed `running` prevents duplicate start | unknown state `NEEDS_REVIEW` |
| Final DB success | none beyond already-observed resources | each completed external step remains `OBSERVED` | rerun reads each step before continuing | injected final business-transaction failure rolls back app state; retry adopts durable readback evidence and does not repeat provider mutation |
| Destroy / public-IP cleanup | VM, DHCP, mapping/provider | profile and identity guard precede calls; VM destroy journal is durable | exact ownership/absence read-back required | cleanup ambiguity keeps public/private association and `QUARANTINED`; no address reuse |

## Invariants

- VM100–107 never reach a network call.
- A default change never changes an existing instance pin.
- A disabled profile blocks the next normal mutation.
- `NEEDS_REVIEW`, `FAILED` and `COMPENSATED` are not automatic retry states.
- Provider/SSH exception bodies are not persisted or shown to the browser.
- No reconciliation finding sets `auto_delete=true`.

## Remaining closure work

Actual OVH `gwnat` persistence cannot be implemented from labels alone. It needs
a fresh canonical `anh-xa-ip.txt`/nft baseline and a scoped generator that proves
all protected VM100–107 mappings are byte-for-byte preserved. Dynamic Vultr IP
reserve/bind/release still needs durable provider-label recovery before that
profile may accept new production instances. The OVH static-pool lifecycle and
destroy path are journaled; final-business-commit injection now passes and does
not repeat the provider mutation on retry.
