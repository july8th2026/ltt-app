"""VPS V4 R20 — the console bridge must use the same pinned CA + exact TLS name
as every Proxmox API call.

Measured 16/09 on production: the bridge used the system trust store, the TLS
handshake failed ("unable to get local issuer certificate") and the customer's
console closed immediately. This test builds a private CA and a local TLS
server whose certificate names only `pve`, like the real node.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import ipaddress
import socket
import ssl
import threading
from types import SimpleNamespace

import pytest

x509 = pytest.importorskip("cryptography.x509")
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402


def _pki(tmp_path):
    now = datetime.now(timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fixture pve root")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(1)
          .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
                         critical=False)
          .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                                       key_encipherment=False, data_encipherment=False,
                                       key_agreement=False, key_cert_sign=True, crl_sign=True,
                                       encipher_only=False, decipher_only=False), critical=True)
          .sign(ca_key, hashes.SHA256()))
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pve")]))
            .issuer_name(ca_name).public_key(key.public_key()).serial_number(2)
            .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("pve")]), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(
                ca_key.public_key()), critical=False)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                           critical=False)
            .sign(ca_key, hashes.SHA256()))
    ca_file, cert_file, key_file = (tmp_path / "ca.pem", tmp_path / "leaf.pem", tmp_path / "leaf.key")
    ca_file.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_file.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                           serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    return ca_file, cert_file, key_file


@pytest.fixture()
def tls_server(tmp_path):
    ca_file, cert_file, key_file = _pki(tmp_path)
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(cert_file, key_file)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    stop = threading.Event()

    def serve():
        listener.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except OSError:
                continue
            try:
                with server_ctx.wrap_socket(conn, server_side=True):
                    pass
            except (ssl.SSLError, OSError):
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield listener.getsockname()[1], str(ca_file)
    stop.set()
    thread.join(timeout=2)
    listener.close()


def _handshake(port, ctx, server_hostname):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
        with ctx.wrap_socket(raw, server_hostname=server_hostname) as tls:
            return tls.version()


def test_console_bridge_tls_matches_pinned_ca_and_exact_name(tls_server):
    from apps.vps.services.console import tls_cho_cau_console

    port, ca_file = tls_server
    config = SimpleNamespace(ca_bundle=ca_file, tls_name="pve", verify=ca_file)
    ctx, server_hostname = tls_cho_cau_console(config)
    assert server_hostname == "pve"
    assert _handshake(port, ctx, server_hostname).startswith("TLS")


def test_previous_system_trust_store_fails_like_production(tls_server):
    port, _ca_file = tls_server
    with pytest.raises(ssl.SSLCertVerificationError):
        _handshake(port, ssl.create_default_context(), "127.0.0.1")


def test_pinned_ca_with_ip_hostname_still_fails(tls_server):
    port, ca_file = tls_server
    with pytest.raises(ssl.SSLCertVerificationError):
        _handshake(port, ssl.create_default_context(cafile=ca_file),
                   str(ipaddress.ip_address("127.0.0.1")))
