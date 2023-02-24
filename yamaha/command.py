from abc import ABCMeta, abstractmethod
from typing import Literal, Any
from .filter import Filter


class YamahaRouterCommand(metaclass=ABCMeta):
    @abstractmethod
    def build(self, filter_tables: dict[str, dict[str, str]]) -> str:
        raise NotImplementedError


class BasicCommand(YamahaRouterCommand):
    def __init__(self, command: str):
        self.command = command

    def build(self, filter_tables):
        return self.command


class FilterCommand(YamahaRouterCommand):
    def __init__(
        self,
        filters: dict[str, Filter],
        proto: Literal["ip", "ipv6"],
        interface: str,
        direction: Literal["in", "out"],
        static_filters: list[str] = [],
        dynamic_filters: list[str] = [],
    ):
        self.proto = proto
        self.interface = interface
        self.direction = direction
        self.static_filters = static_filters
        self.dynamic_filters = dynamic_filters
        filters[f"{proto}_filter"].add(static_filters)
        filters[f"{proto}_dynamic_filter"].add(dynamic_filters)

    def build(self, filter_tables):
        command = f"{self.proto} {self.interface} secure filter {self.direction}"
        for filter_def in self.static_filters:
            command += f" {filter_tables[f'{self.proto}_filter'][filter_def]}"
        if len(self.dynamic_filters) > 0:
            command += " dynamic"
        for filter_def in self.dynamic_filters:
            command += f" {filter_tables[f'{self.proto}_dynamic_filter'][filter_def]}"
        return command


class RouteCommand(YamahaRouterCommand):
    def __init__(self, filters: dict[str, Filter], proto: Literal["ip", "ipv6"], network: str):
        self.filters = filters
        self.proto = proto
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
        self.gateways.append(Gateway(self.proto, gateway, filters, **kwargs))
        self.filters[f"{self.proto}_filter"].add(filters)

    def build(self, filter_tables):
        command = f"{self.proto} route {self.network}"
        for gateway in self.gateways:
            command += f" {gateway.build(filter_tables)}"
        return command


class Gateway:
    def __init__(self, proto: Literal["ip", "ipv6"], gateway: str, filters: list[str], **kwargs):
        self.proto = proto
        self.gateway = gateway
        self.filters = filters
        self.parameters: dict[str, Any] = kwargs

    def build(self, filter_tables: dict[str, dict[str, str]]) -> str:
        command = f"gateway {self.gateway}"
        if len(self.filters) > 0:
            command += " filter"
        for filter_def in self.filters:
            command += f" {filter_tables[f'{self.proto}_filter'][filter_def]}"
        for key, val in self.parameters.items():
            if type(val) is bool:
                if val:
                    command += f" {key}"
            else:
                command += f" {key} {val}"
        return command
