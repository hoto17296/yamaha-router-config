from .types import NetProtocol
from .utils import uniq


class Filter:
    def __init__(self, protocol: NetProtocol, dynamic: bool, filter_num_base: int):
        self.protocol: NetProtocol = protocol
        self.dynamic = dynamic
        self.filter_num_base = filter_num_base
        self.defs: list[str] = []

    def add(self, defs: list[str]):
        self.defs = uniq(self.defs + defs)

    def build_table(self) -> dict[str, str]:
        return {_def: str(self.filter_num_base + idx) for idx, _def in enumerate(self.defs)}

    def build_commands(self) -> list[str]:
        return [
            f"{self.protocol} filter{' dynamic' if self.dynamic else ''} {num} {_def}"
            for _def, num in self.build_table().items()
        ]
