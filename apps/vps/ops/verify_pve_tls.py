"""Verify the PVE TLS transport without using a production API token.

An HTTP response (normally 401 for the deliberately invalid token) proves that
CA-chain and certificate-name validation completed.  The command never prints
response bodies, credentials, or exception text.
"""
from __future__ import annotations

import argparse

from apps.vps.services.proxmox import ProxmoxClient, ProxmoxConfig, ProxmoxError


def verify_tls(url: str, ca_bundle: str, tls_name: str) -> tuple[bool, str]:
    config = ProxmoxConfig(
        base_url=url.rstrip("/"),
        token_id="tls-probe@pve!transport",
        token_secret="deliberately-invalid",
        ca_bundle=ca_bundle,
        tls_name=tls_name,
    )
    try:
        ProxmoxClient(config).phien_ban()
    except ProxmoxError as exc:
        if exc.status is not None:
            return True, f"http={exc.status}"
        return False, "transport_error"
    return True, "http=200"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--ca", required=True)
    parser.add_argument("--tls-name", required=True)
    args = parser.parse_args()
    ok, detail = verify_tls(args.url, args.ca, args.tls_name)
    print(f"PVE_TLS_{'PASS' if ok else 'FAIL'} {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
