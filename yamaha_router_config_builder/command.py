from abc import ABCMeta, abstractmethod
from typing import Any

from .filter import Filter
from .types import Direction, NetProtocol


class YamahaRouterCommand(metaclass=ABCMeta):
    @abstractmethod
    def build(self, filter_tables: dict[str, dict[str, str]]) -> list[str]:
        raise NotImplementedError


class BasicCommand(YamahaRouterCommand):
    def __init__(self, command: str):
        self.command = command

    def build(self, filter_tables):
        return [self.command]


class FilterCommand(YamahaRouterCommand):
    def __init__(
        self,
        filters: dict[str, Filter],
        protocol: NetProtocol,
        interface: str,
        direction: Direction,
        static_filters: list[str] = [],
        dynamic_filters: list[str] = [],
    ):
        self.protocol: NetProtocol = protocol
        self.interface = interface
        self.direction = direction
        self.static_filters = static_filters
        self.dynamic_filters = dynamic_filters
        filters[f"{protocol}_filter"].add(static_filters)
        filters[f"{protocol}_dynamic_filter"].add(dynamic_filters)

    def build(self, filter_tables):
        command = f"{self.protocol} {self.interface} secure filter {self.direction}"
        for filter_def in self.static_filters:
            command += f" {filter_tables[f'{self.protocol}_filter'][filter_def]}"
        if len(self.dynamic_filters) > 0:
            command += " dynamic"
        for filter_def in self.dynamic_filters:
            command += f" {filter_tables[f'{self.protocol}_dynamic_filter'][filter_def]}"
        return [command]


class RouteCommand(YamahaRouterCommand):
    def __init__(self, filters: dict[str, Filter], protocol: NetProtocol, network: str):
        self.filters = filters
        self.protocol: NetProtocol = protocol
        self.network = network
        self.gateways: list[Gateway] = []

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, trace):
        if ex_value:
            raise ex_value

    def gateway(self, gateway: str, filters: list[str] = [], **kwargs):
        """
        経路情報を追加する
        静的フィルターおよび各種パラメータを指定できるが、DPI フィルタには未対応
        """
        self.gateways.append(Gateway(self.protocol, gateway, filters, **kwargs))
        self.filters[f"{self.protocol}_filter"].add(filters)

    def build(self, filter_tables):
        command = f"{self.protocol} route {self.network}"
        for gateway in self.gateways:
            command += f" {gateway.build(filter_tables)}"
        return [command]


class Gateway:
    def __init__(self, protocol: NetProtocol, gateway: str, filters: list[str], **kwargs):
        self.protocol: NetProtocol = protocol
        self.gateway = gateway
        self.filters = filters
        self.parameters: dict[str, Any] = kwargs

    def build(self, filter_tables: dict[str, dict[str, str]]) -> str:
        option = f"gateway {self.gateway}"
        if len(self.filters) > 0:
            option += " filter"
        for filter_def in self.filters:
            option += f" {filter_tables[f'{self.protocol}_filter'][filter_def]}"
        for key, val in self.parameters.items():
            if type(val) is bool:
                if val:
                    option += f" {key}"
            else:
                option += f" {key} {val}"
        return option
