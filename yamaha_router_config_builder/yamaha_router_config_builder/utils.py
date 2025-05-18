from typing import Any, Generator, NoReturn

type Counter = Generator[int, Any, NoReturn]


def counter(initial: int = 0) -> Counter:
    n = initial
    while True:
        yield n
        n += 1


def uniq(arr: list[str]) -> list[str]:
    """順序を保ちつつ unique なリストを作る"""
    return list(dict.fromkeys(arr).keys())


class IPv4Addr:
    def __init__(self, cidr: str):
        self.addr, self.mask = _cidr2int(cidr)

    def __call__(self, i: int, prefix: bool = False) -> str:
        cidr = _int2cidr((self.addr & self.mask) + i, self.mask)
        return cidr if prefix else cidr.split("/")[0]

    def __str__(self) -> str:
        return self.cidr()

    def cidr(self) -> str:
        return _int2cidr(self.addr & self.mask, self.mask)

    def prefix(self) -> int:
        return bin(self.mask).count("1")

    def range(self, min: int, max: int) -> str:
        return f"{self(min)}-{self(max)}/{self.prefix()}"


def _cidr2int(cidr: str) -> tuple[int, int]:
    _addr, prefix = cidr.split("/", 1)
    _addr = _addr.split(".")
    assert len(_addr) == 4
    prefix = int(prefix)
    assert 0 <= prefix <= 32

    addr = 0
    for i, octet in enumerate(_addr):
        assert 0 <= int(octet) <= 0xFF
        addr += int(octet) * 0x100 ** (3 - i)
    mask = 0xFFFFFFFF >> (32 - prefix) << (32 - prefix)
    return addr, mask


def _int2cidr(addr: int, mask: int) -> str:
    assert 0 <= addr <= 0xFFFFFFFF
    assert 0 <= mask <= 0xFFFFFFFF
    octets = reversed([(addr & (0xFF * 0x100**i)) >> (i * 8) for i in range(4)])
    return f"{'.'.join([str(octet) for octet in octets])}/{bin(mask).count('1')}"
