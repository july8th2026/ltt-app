# Third-Party Notices — LTT Nexus

LTT Nexus distributes and operates third-party software. This file lists that
software, its license, and where to obtain its Corresponding Source, as required
by those licenses.

> Decision context: Q97 (`docs/QUYET_DINH_NEN_TANG.md`) — LTT Nexus uses the
> RustDesk engine **unmodified**. Because the program is not modified, AGPL-3.0
> §13 imposes no additional network-source obligation; the remaining duty is the
> §§4–6 conveying obligation, satisfied by this notice plus the source pointers
> below. If a future decision moves to a **modified** RustDesk client (Q97 "Rổ
> 2"), this file must be extended with an offer of the modified fork's source.

---

## RustDesk (remote-control engine)

- **Component:** `rustdesk/rustdesk` — the client/engine that captures the
  screen, receives input, negotiates NAT traversal, and transports the session.
- **License:** GNU Affero General Public License v3.0 (AGPL-3.0).
- **Version / commit:** `1.4.9` (2026-07-06), commit
  `6c578292e8ebbbec708b76986ba8c4bc7c509747`.
- **Source:** https://github.com/rustdesk/rustdesk (pinned at the commit above).
- **Modifications by LTT:** **none.** The binary is distributed and run as
  published upstream. LTT supplies server configuration (rendezvous/relay
  address and public key) from outside the program; it does not alter the
  program.

## RustDesk Server — hbbs / hbbr (rendezvous + relay)

- **Component:** `rustdesk/rustdesk-server` — the self-hosted rendezvous (hbbs)
  and relay (hbbr) that LTT runs on its own infrastructure.
- **License:** AGPL-3.0.
- **Version / commit:** `1.1.16` (2026-07-20), commit
  `73523b31cfd25d77dee862e6fc9f5e1fb5e485ef`.
- **Source:** https://github.com/rustdesk/rustdesk-server (pinned at the commit
  above).
- **Modifications by LTT:** **none.** Run unmodified; §13 is therefore not
  triggered for the server either.

---

## Full license text

The complete AGPL-3.0 license text applies to both components above and is
available at:

- https://www.gnu.org/licenses/agpl-3.0.txt
- and in the `LICENCE` file inside each RustDesk repository at the pinned commit.

## Obtaining the source

For each component, the Corresponding Source is the upstream repository at the
exact commit listed above. Because LTT distributes these components **unmodified**,
the Corresponding Source is the upstream source itself — no LTT-specific patches
exist to publish. Anyone who receives an LTT Nexus binary that includes these
components may obtain the source from the URLs above.

## Not covered here

- **Transitive dependencies** of RustDesk (Rust crates, Flutter libraries) are
  **not yet inventoried** (`docs/nexus/03_OSS_LICENSE.md` §2, §6 item 4). Some
  may carry other licenses. This must be completed before commercial release;
  it is recorded as *not done*, not as *no issue*.
- The **LTT Nexus Agent** and control plane are LTT's own proprietary software,
  are not derived from RustDesk, run in a separate process communicating only
  over a local IPC contract, and are not covered by this notice.
