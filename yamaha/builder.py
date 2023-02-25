from contextlib import contextmanager
from typing import Literal
from .command import YamahaRouterCommand, BasicCommand, FilterCommand, RouteCommand
from .filter import Filter
from .nat import Nat


def counter(initial: int = 0):
    n = initial
    while True:
        yield n
        n += 1


class YamahaRouterConfigBuilder:
    def __init__(self, device: str = None, version: str = None):
        self.device = device or "Router"
        self.version = version or "0.0.0"
        self.commands: list[YamahaRouterCommand] = []
        self.filters: dict[str, Filter] = {
            "ip_filter": Filter("ip", False, 1000),
            "ip_dynamic_filter": Filter("ip", True, 2000),
            "ipv6_filter": Filter("ipv6", False, 3000),
            "ipv6_dynamic_filter": Filter("ipv6", True, 4000),
        }
        self.nat_descriptor_counter = counter(1)
        self.nat_descriptions: list[Nat] = []

    @contextmanager
    def section(self, title: str):
        self.add(f"\n# {title}")
        yield

    def add(self, command):
        self.commands.append(BasicCommand(command))

    def ip_filter(self, interface, direction: Literal["in", "out"], static: list[str] = [], dynamic: list[str] = []):
        self.commands.append(FilterCommand(self.filters, "ip", interface, direction, static, dynamic))

    def ipv6_filter(self, interface, direction: Literal["in", "out"], static: list[str] = [], dynamic: list[str] = []):
        self.commands.append(FilterCommand(self.filters, "ipv6", interface, direction, static, dynamic))

    def ip_route(self, network: str):
        """
        IP の経路情報の設定
        http://www.rtpro.yamaha.co.jp/RT/manual/rt-common/ip/ip_route.html
        """
        route = RouteCommand(self.filters, "ip", network)
        self.commands.append(route)
        return route

    def ipv6_route(self, network: str):
        """
        IPv6 の経路情報の設定
        http://www.rtpro.yamaha.co.jp/RT/manual/rt-common/ipv6/ipv6_route.html
        """
        route = RouteCommand(self.filters, "ipv6", network)
        self.commands.append(route)
        return route

    @contextmanager
    def interface(self, interface: str, id: str):
        self.add(f"{interface} select {id}")
        try:
            yield
        finally:
            self.add(f"{interface} enable {id}")

    @contextmanager
    def nat(self, interface: str, type: str = "none"):
        nat = Nat(next(self.nat_descriptor_counter), type)
        self.nat_descriptions.append(nat)
        self.add(f"ip {interface} nat descriptor {nat.descriptor}")
        yield nat

    def build(self) -> str:
        commands = [
            f"# YAMAHA {self.device} config (version {self.version})",
            "# This file is auto-generated by YamahaRouterConfigBuilder",
            "# See also: https://github.com/hoto17296/yamaha-router-config",
        ]

        if len(self.filters) > 0:
            commands.append("\n# Filter")
        filter_tables = {}
        for name, filter in self.filters.items():
            commands += filter.build_commands()
            filter_tables[name] = filter.build_table()

        if len(self.nat_descriptions) > 0:
            commands.append("\n# NAT")
        for nat_description in self.nat_descriptions:
            commands += nat_description.commands

        for command in self.commands:
            commands += command.build(filter_tables)

        return "\n".join(commands)
