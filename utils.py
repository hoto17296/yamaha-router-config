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
