from ipaddress import IPv4Network
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


def addr_range(network: IPv4Network, min: int, max: int) -> str:
    """ネットワーク内の min 番目から max 番目までのアドレス範囲を
    "192.168.10.2-192.168.10.100/24" 形式で表す"""
    return f"{network[min]}-{network[max]}/{network.prefixlen}"
