"""VMID/name are labels, not permission to mutate someone else's machine."""
from types import SimpleNamespace

import pytest

from apps.vps.services import dinh_danh


class Client:
    config = SimpleNamespace(node="test-node")

    def __init__(self, config):
        self.vm_config = config
        self.calls = []

    def danh_sach_vm(self):
        return [{"vmid": 210}]

    def _goi(self, method, path):
        self.calls.append((method, path))
        return self.vm_config


@pytest.mark.parametrize("config", [
    {"name": "vps-instance"},
    {"name": "vps-instance", "smbios1": dinh_danh.smbios1("different-owner")},
    {"name": "other-machine", "smbios1": dinh_danh.smbios1("instance-1")},
])
def test_existing_vmid_or_matching_name_alone_is_not_ownership(config):
    from apps.vps.services.vm_ownership import owned_vm_exists
    from apps.vps.services.backends.contracts import BackendConflict
    with pytest.raises(BackendConflict):
        owned_vm_exists(Client(config), SimpleNamespace(id="instance-1", vmid=210))


def test_uuid_and_canonical_name_confirm_ownership_without_mutation():
    from apps.vps.services.vm_ownership import owned_vm_exists
    client = Client({"name": "vps-instance", "smbios1": dinh_danh.smbios1("instance-1")})
    assert owned_vm_exists(client, SimpleNamespace(id="instance-1", vmid=210)) is True
    assert client.calls == [("GET", "/nodes/test-node/qemu/210/config")]


def test_protected_vmid_blocks_even_matching_uuid_before_network():
    from apps.vps.services.vm_ownership import owned_vm_exists
    from apps.vps.services.backends.contracts import BackendConflict
    client = Client({"name": "vps-instance", "smbios1": dinh_danh.smbios1("instance-1")})
    with pytest.raises(BackendConflict):
        owned_vm_exists(client, SimpleNamespace(id="instance-1", vmid=100))
    assert client.calls == []
