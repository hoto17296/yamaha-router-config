from yamaha_router_config_builder.utils import IPv4Addr


def test_ipv4addr_basic():
    addr = IPv4Addr("192.168.1.0/24")
    assert addr.addr == 0xC0A80100
    assert addr.mask == 0xFFFFFF00


def test_ipv4addr_call():
    addr = IPv4Addr("10.0.0.0/24")
    assert addr(1) == "10.0.0.1"
    assert addr(5) == "10.0.0.5"
    assert addr(1, prefix=True) == "10.0.0.1/24"


def test_ipv4addr_str_and_cidr():
    addr = IPv4Addr("172.16.5.0/28")
    assert str(addr) == "172.16.5.0/28"
    assert addr.cidr() == "172.16.5.0/28"


def test_ipv4addr_prefix():
    addr = IPv4Addr("192.168.0.0/16")
    assert addr.prefix() == 16


def test_ipv4addr_range():
    addr = IPv4Addr("192.168.10.0/24")
    assert addr.range(2, 100) == "192.168.10.2-192.168.10.100/24"


def test_ipv4addr_edge_cases():
    addr = IPv4Addr("0.0.0.0/0")
    assert addr(0) == "0.0.0.0"
    assert addr.prefix() == 0
