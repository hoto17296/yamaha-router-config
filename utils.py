from dataclasses import dataclass, field


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

    def build(self) -> str:
        commands = []

        # IPv4 static filter
        ip_filter_table = convert_filter_table([c.ip_filter_list for c in self.command_list], 1000)
        for filter_def, filter_num in ip_filter_table.items():
            commands.append(f"ip filter {filter_num} {filter_def}")
        # IPv4 dynamic filter
        ip_dynamic_filter_table = convert_filter_table([c.ip_dynamic_filter_list for c in self.command_list], 1000)
        for filter_def, filter_num in ip_dynamic_filter_table.items():
            commands.append(f"ip filter dynamic {filter_num} {filter_def}")
        # IPv6 static filter
        ipv6_filter_table = convert_filter_table([c.ipv6_filter_list for c in self.command_list], 1000)
        for filter_def, filter_num in ipv6_filter_table.items():
            commands.append(f"ipv6 filter {filter_num} {filter_def}")
        # IPv6 dynamic filter
        ipv6_dynamic_filter_table = convert_filter_table([c.ipv6_dynamic_filter_list for c in self.command_list], 1000)
        for filter_def, filter_num in ipv6_dynamic_filter_table.items():
            commands.append(f"ipv6 filter dynamic {filter_num} {filter_def}")

        for c in self.command_list:
            command = c.command
            for f in c.ip_filter_list:
                command += f" {ip_filter_table[f]}"
            commands.append(command)
        return "\n".join(commands)
