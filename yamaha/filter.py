from typing import Literal


def uniq(arr: list[str]) -> list[str]:
    """順序を保ちつつ unique なリストを作る"""
    return list(dict.fromkeys(arr).keys())


class Filter:
    def __init__(self, proto: Literal["ip", "ipv6"], dynamic: bool, filter_num_base: int):
        self.proto = proto
        self.dynamic = dynamic
        self.filter_num_base = filter_num_base
        self.defs: list[str] = []

    def add(self, defs: list[str]):
        self.defs = uniq(self.defs + defs)

    def build_table(self) -> dict[str, str]:
        return {_def: str(self.filter_num_base + idx) for idx, _def in enumerate(self.defs)}

    def build_commands(self) -> list[str]:
        return [
            f"{self.proto} filter{' dynamic' if self.dynamic else ''} {num} {_def}"
            for _def, num in self.build_table().items()
        ]
