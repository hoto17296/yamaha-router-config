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
                for f in getattr(c, f"{proto}{'_dynamic' if dynamic else ''}_filter_list"):
                    command += f" {filter_tables[(proto, dynamic)][f]}"

            commands.append(command)

        return "\n".join(commands)
