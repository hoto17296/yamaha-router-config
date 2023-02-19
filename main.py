from utils import YamahaRouterConfigBuilder

config = YamahaRouterConfigBuilder()

LAN_CIDR = "192.168.57.0/24"

config.add(
    "ip tunnel secure filter in",
    ip_filter_list=[
        f"reject {LAN_CIDR} * * * *",
        "reject * * udp,tcp 135 *",
        "reject * * udp,tcp * 135",
        "reject * * udp,tcp netbios_ns-netbios_ssn *",
        "reject * * udp,tcp * netbios_ns-netbios_ssn",
        "reject * * udp,tcp 445 *",
        "reject * * udp,tcp * 445",
        f"pass * {LAN_CIDR} icmp * *",
        f"pass {LAN_CIDR} tcp * ident",
    ],
)

if __name__ == "__main__":
    print(config.build())
