from yamaha_router_config_builder import YamahaRouterConfigBuilder


def test_builder_basic_add():
    builder = YamahaRouterConfigBuilder("TestDevice", "1.2.3")
    builder.add("test command")
    config = builder.build()
    assert "# YAMAHA TestDevice config (version 1.2.3)" in config
    assert "test command" in config


def test_builder_section_context():
    builder = YamahaRouterConfigBuilder()
    with builder.section("TestSection"):
        builder.add("section command")
    config = builder.build()
    assert "# TestSection" in config
    assert "section command" in config


def test_builder_ip_filter_and_route():
    builder = YamahaRouterConfigBuilder()
    builder.ip_filter("lan1", "in", static=["pass * * * * *"])
    with builder.ip_route("192.168.1.0/24") as route:
        route.gateway("192.168.1.1")
    config = builder.build()
    assert "ip lan1 secure filter in" in config
    assert "ip route 192.168.1.0/24 gateway 192.168.1.1" in config


def test_builder_nat_context():
    builder = YamahaRouterConfigBuilder()
    with builder.nat("lan1", "masquerade") as nat:
        nat.add("nat descriptor address outer 1 auto")
    config = builder.build()
    assert "nat descriptor type 1 masquerade" in config
    assert "nat descriptor address outer 1 auto" in config
    assert "ip lan1 nat descriptor 1" in config


def test_builder_interface_context():
    builder = YamahaRouterConfigBuilder()
    with builder.interface("lan1", 10):
        builder.add("ip address 192.0.2.1/24")
    config = builder.build()
    assert "lan1 select 10" in config
    assert "ip address 192.0.2.1/24" in config
    assert "lan1 enable 10" in config
