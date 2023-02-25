from yamaha.builder import YamahaRouterConfigBuilder
from utils import Env, IPv4Addr

ENV = Env(".env")

config = YamahaRouterConfigBuilder("NVR700W")

LAN_ADDR = IPv4Addr("192.168.57.0/24")

LAN_IF = "lan1"
WAN_IF = "onu1"

IPV6_PREFIX_ID = 1

# トンネル ID
IPIP6_TUNNEL_ID = 1

# DHCP 固定割り当てテーブル
DHCP_STATIC_TABLE: list[tuple[int, str]] = [
    (2, "ac:44:f2:aa:6f:61"),
    (3, "f0:9f:c2:73:2a:26"),
    (4, "94:83:c4:03:83:46"),
    (6, "38:9d:92:bc:e0:cf"),
    (7, "00:01:2e:71:c4:cf"),
    (8, "00:11:32:71:e5:07"),
    (9, "1c:69:7a:6a:66:8f"),
    (100, "3c:f8:62:49:66:c8"),
]

with config.section("User"):
    # ログインパスワード設定
    config.add(f"login password {ENV.USER_PASSWORD}")
    config.add(f"administrator password {ENV.ADMIN_PASSWORD}")

    # ログインセッションの期限を1時間に設定
    config.add("user attribute login-timer=3600")

with config.section("IPv4"):
    # IPv4 デフォルト経路設定
    with config.ip_route("default") as route:
        # VPN 通信は PPPoE に流す
        # route.gateway(
        #     f"pp 1",
        #     filters=[
        #         "pass * * esp",
        #         "pass * * udp 500 *",
        #         "pass * * udp 4500 *",
        #     ],
        # )
        # それ以外は MAP-E トンネルに流す
        route.gateway(f"tunnel {IPIP6_TUNNEL_ID}")

    # LAN インタフェースの IPv4 アドレスの設定
    config.add(f"ip {LAN_IF} address {LAN_ADDR(1, prefix=True)}")

    # 外 (VPN) からアクセスがあった時に応答出来るよう代理 ARP を有効化 (よくわかってない)
    config.add(f"ip {LAN_IF} proxyarp on")

with config.section("IPv6"):
    # IPv6 デフォルト経路設定
    with config.ipv6_route("default") as route:
        route.gateway(f"dhcp {WAN_IF}")

    # LAN インタフェースの IPv6 アドレスの設定
    config.add(f"ipv6 {LAN_IF} address dhcp-prefix@{WAN_IF}::1/64")

    # ルーター広告する IPv6 プレフィックスの設定
    config.add(f"ipv6 prefix {IPV6_PREFIX_ID} dhcp-prefix@{WAN_IF}::/64")

    # ルーター広告の設定
    # o_flag=on: アドレス以外の情報をホストに自動取得させる (ゲートウェイとか？？よくわかってない)
    config.add(f"ipv6 {LAN_IF} rtadv send {IPV6_PREFIX_ID} o_flag=on")

    # LAN 方向に DHCPv6 サーバとして動作させる
    config.add(f"ipv6 {LAN_IF} dhcp service server")

    # WAN インタフェースの名前を設定
    config.add(f"description {WAN_IF} OCN")

    # WAN インタフェースの IPv4 アドレスは DHCP で取得する
    config.add(f"ip {WAN_IF} address dhcp")

    # WAN インタフェースの IPv6 アドレスは DHCP で取得する
    config.add(f"ipv6 {WAN_IF} address dhcp")

    # WAN インタフェースのフィルタリング設定 (IN)
    config.ipv6_filter(
        WAN_IF,
        "in",
        static=[
            "pass * * icmp6 * *",
            "pass * * tcp * ident",
            "pass * * udp * 546",
            "pass * * 4",
        ],
    )

    # WAN インタフェースのフィルタリング設定 (OUT)
    config.ipv6_filter(
        WAN_IF,
        "out",
        static=["pass * * * * *"],
        dynamic=[
            "* * domain",
            "* * www",
            "* * tcp",
            "* * udp",
        ],
    )

    # WAN 方向に DHCPv6 クライアントとして動作させる
    config.add(f"ipv6 {WAN_IF} dhcp service client")

    # NGN 網に接続する
    config.add(f"ngn type {WAN_IF} ntt")

# IPv4 over IPv6 トンネル設定
with config.section("IPIP6 tunnel"):
    with config.interface("tunnel", IPIP6_TUNNEL_ID):

        # トンネルの種別を MAP-E として設定
        config.add("tunnel encapsulation map-e")

        # MAP-E の種別を OCN バーチャルコネクトとして設定
        config.add("tunnel map-e type ocn")

        # MTU 設定
        config.add("ip tunnel mtu 1460")

        # トンネルインタフェースのフィルタリング設定 (IN)
        config.ip_filter(
            "tunnel",
            "in",
            static=[
                f"reject {LAN_ADDR} * * * *",  # IP スプーフィング対策
                "reject * * udp,tcp 135 *",
                "reject * * udp,tcp * 135",
                "reject * * udp,tcp netbios_ns-netbios_ssn *",
                "reject * * udp,tcp * netbios_ns-netbios_ssn",
                "reject * * udp,tcp 445 *",
                "reject * * udp,tcp * 445",
                f"pass * {LAN_ADDR} icmp * *",
                f"pass {LAN_ADDR} tcp * ident",
            ],
        )

        # トンネルインタフェースのフィルタリング設定 (OUT)
        config.ip_filter(
            "tunnel",
            "out",
            static=[
                f"reject * {LAN_ADDR} * * *",  # IP スプーフィング対策
                "reject * * udp,tcp 135 *",
                "reject * * udp,tcp * 135",
                "reject * * udp,tcp netbios_ns-netbios_ssn *",
                "reject * * udp,tcp * netbios_ns-netbios_ssn",
                "reject * * udp,tcp 445 *",
                "reject * * udp,tcp * 445",
                "pass * * * * *",
            ],
            dynamic=[
                "* * domain",
                "* * www",
                "* * tcp",
                "* * udp",
            ],
        )

        with config.nat("tunnel", "masquerade") as nat:
            nat.add(f"nat descriptor address outer {nat.descriptor} map-e")


# PPPoE 設定
with config.section("PPPoE tunnel"):
    with config.interface("pp", 1):
        config.add(f"description pp {ENV.PPPOE_DESCRIPTION}")
        config.add("pp keepalive interval 30 retry-interval=30 count=12")
        config.add("pp always-on on")
        config.add(f"pppoe use {WAN_IF}")
        config.add("pppoe auto disconnect off")
        config.add("pp auth accept pap chap")
        config.add(f"pp auth myname {ENV.PPPOE_USERNAME} {ENV.PPPOE_PASSWORD}")
        config.add("ppp lcp mru on 1454")
        config.add("ppp ipcp ipaddress on")
        config.add("ppp ipcp msext on")
        config.add("ppp ccp type none")
        config.ip_filter(
            "pp",
            "in",
            static=[
                f"reject {LAN_ADDR} * * * *",  # IP スプーフィング対策
                "reject * * udp,tcp 135 *",
                "reject * * udp,tcp * 135",
                "reject * * udp,tcp netbios_ns-netbios_ssn *",
                "reject * * udp,tcp * netbios_ns-netbios_ssn",
                "reject * * udp,tcp 445 *",
                "reject * * udp,tcp * 445",
                f"pass * {LAN_ADDR} icmp * *",
                f"pass * {LAN_ADDR} tcp * ident",
                # 以下 VPN 用
                # f"pass * * esp",
                # f"pass * * udp * 500",
                # f"pass * * udp * 4500",
            ],
        )
        config.ip_filter(
            "pp",
            "out",
            static=[
                f"reject * {LAN_ADDR} * * *",  # IP スプーフィング対策
                "reject * * udp,tcp 135 *",
                "reject * * udp,tcp * 135",
                "reject * * udp,tcp netbios_ns-netbios_ssn *",
                "reject * * udp,tcp * netbios_ns-netbios_ssn",
                "reject * * udp,tcp 445 *",
                "reject * * udp,tcp * 445",
                "pass * * * * *",
            ],
            dynamic=[
                "* * domain",
                "* * www",
                "* * tcp",
                "* * udp",
            ],
        )

        with config.nat("pp", "masquerade") as nat:
            nat.add(f"nat descriptor masquerade static {nat.descriptor} 1 {LAN_ADDR(1)} esp")  # VPN 用
            nat.add(f"nat descriptor masquerade static {nat.descriptor} 2 {LAN_ADDR(1)} udp 500")  # VPN 用
            nat.add(f"nat descriptor masquerade static {nat.descriptor} 3 {LAN_ADDR(1)} udp 4500")  # VPN 用

# DHCP 設定
with config.section("DHCP"):
    # DHCP サーバ設定
    config.add(f"dhcp service server")
    config.add(f"dhcp server rfc2131 compliant except use-clientid")
    config.add(f"dhcp scope 1 {LAN_ADDR(2)}-{LAN_ADDR(239)}/{LAN_ADDR.prefix()}")
    for n, macaddr in DHCP_STATIC_TABLE:
        config.add(f"dhcp scope bind 1 {LAN_ADDR(n)} {macaddr}")

    # DHCP クライアント設定
    config.add(f"dhcp client release linkdown on")

# DNS 設定
with config.section("DNS"):
    config.add(f"dns host {LAN_IF}")
    config.add(f"dns service fallback on")
    config.add(f"dns server dhcp {WAN_IF} edns=on")
    config.add(f"dns private address spoof on")
    config.add(f"dns private name setup.netvolante.jp")

# その他
with config.section("Other"):
    # Syslog を NAS に保存
    config.add(f"syslog host {LAN_ADDR(8)}")

    # Telnet アクセスを無効化
    config.add("telnetd service off")

    # L2MS を有効にする (配下の YAMAHA 機器を管理する機能)
    config.add(f"switch control use {LAN_IF} on terminal=on")

    # DDNS 設定
    config.add(f"netvolante-dns hostname host pp server=1 {ENV.HOSTNAME}")

    # 毎日6時に時刻同期する
    config.add("schedule at 1 */* 06:00:00 * ntpdate ntp.nict.jp syslog")

    # トラフィックの統計データを取る
    config.add("statistics traffic on")

# VPN
# with config.interface("tunnel", 2):
#     GW_ID = 2
#     SA_POLICY_ID = 2
#     config.add(f"tunnel encapsulation ipsec")
#     config.add(f"ipsec tunnel {SA_POLICY_ID}")
#     config.add(f"ipsec sa policy {SA_POLICY_ID} {GW_ID} esp")
#     config.add(f"ipsec ike version {GW_ID} 2")
#     config.add(f"ipsec ike keepalive log {GW_ID} off")
#     config.add(f"ipsec ike keepalive use {GW_ID} on rfc4306 10 3")
#     config.add(f"ipsec ike local name {GW_ID} {ENV.HOSTNAME} fqdn")
#     config.add(f"ipsec ike nat-traversal {GW_ID} on")
#     config.add(f"ipsec ike pre-shared-key {GW_ID} text {ENV.VPN_PSK}")
#     config.add(f"ipsec ike remote name {GW_ID} hoto fqdn")
#     config.add(f"ipsec ike mode-cfg address {GW_ID} 1")
#     config.add(f"ipsec auto refresh {GW_ID} off")
# config.add(f"ipsec ike mode-cfg address pool 1 {LAN_ADDR(240)}-{LAN_ADDR(254)}/{LAN_ADDR.prefix()}")

if __name__ == "__main__":
    print(config.build())
