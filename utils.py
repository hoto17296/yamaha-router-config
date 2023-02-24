from dataclasses import dataclass, field
from contextlib import contextmanager


def convert_filter_table(values: list[list[str]], base: int = 0) -> dict[str, str]:
    """フィルタなどの定義の一覧を受け取って重複を排除して連番を振って dict として返す"""
    uniq_items = dict.fromkeys(sum(values, [])).keys()
    return {item: str(base + idx) for idx, item in enumerate(uniq_items)}


@dataclass
class YamahaRouterCommand:
    command: str
    ip_filter_list: list[str] = field(default_factory=list)
    ip_dynamic_filter_list: list[str] = field(default_factory=list)
    ipv6_filter_list: list[str] = field(default_factory=list)
    ipv6_dynamic_filter_list: list[str] = field(default_factory=list)


class YamahaRouterConfigBuilder:
    def __init__(self):
        self.command_list: list[YamahaRouterCommand] = []

    def add(self, *args, **kwargs):
        self.command_list.append(YamahaRouterCommand(*args, **kwargs))

    @contextmanager
    def interface(self, interface: str, id: int):
        self.add(f"{interface} select {id}")
        try:
            yield
        finally:
            self.add(f"{interface} enable {id}")

    def build(self) -> str:
        commands = []

        filter_types: list[(str, bool, int)] = [
            ("ip", False, 1000),
            ("ip", True, 2000),
            ("ipv6", False, 3000),
            ("ipv6", True, 4000),
        ]
        filter_tables = {}
        for proto, dynamic, filter_num_base in filter_types:
            items = [getattr(c, f"{proto}{'_dynamic' if dynamic else ''}_filter_list") for c in self.command_list]
            uniq_items = dict.fromkeys(sum(items, [])).keys()
            filter_tables[(proto, dynamic)] = {item: str(filter_num_base + idx) for idx, item in enumerate(uniq_items)}
            for filter_def, filter_num in filter_tables[(proto, dynamic)].items():
                commands.append(f"{proto} filter{' dynamic' if dynamic else ''} {filter_num} {filter_def}")

        for c in self.command_list:
            command = c.command

            for proto, dynamic, filter_num_base in filter_types:
                filter_list = getattr(c, f"{proto}{'_dynamic' if dynamic else ''}_filter_list")
                if dynamic and len(filter_list) > 0:
                    command += " dynamic"
                for f in filter_list:
                    command += f" {filter_tables[(proto, dynamic)][f]}"

            commands.append(command)

        return "\n".join(commands)


class IPv4Addr:
    def __init__(self, cidr: str):
        self.addr, self.mask = cidr2int(cidr)

    def __call__(self, i: int, prefix: bool = False) -> str:
        cidr = int2cidr((self.addr & self.mask) + i, self.mask)
        return cidr if prefix else cidr.split("/")[0]

    def __str__(self) -> str:
        return self.cidr()

    def cidr(self) -> str:
        return int2cidr(self.addr & self.mask, self.mask)

    def prefix(self) -> int:
        return bin(self.mask).count("1")


def cidr2int(cidr: str) -> tuple[int, int]:
    cidr = cidr.split("/", 1)
    cidr[0] = cidr[0].split(".")
    assert len(cidr[0]) == 4
    addr = 0
    for i, octet in enumerate(cidr[0]):
        assert 0 <= int(octet) <= 0xFF
        addr += int(octet) * 0x100 ** (3 - i)
    prefix = int(cidr[1])
    assert 0 <= prefix <= 32
    mask = 0xFFFFFFFF >> (32 - prefix) << (32 - prefix)
    return addr, mask


def int2cidr(addr: int, mask: int) -> str:
    assert 0 <= addr <= 0xFFFFFFFF
    assert 0 <= mask <= 0xFFFFFFFF
    octets = reversed([(addr & (0xFF * 0x100**i)) >> (i * 8) for i in range(4)])
    return f"{'.'.join([str(octet) for octet in octets])}/{bin(mask).count('1')}"
