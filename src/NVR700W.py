from ipaddress import IPv4Address, IPv4Network
from os import environ
from typing import NamedTuple

from yamaha_router_config_builder import YamahaRouterConfigBuilder
from yamaha_router_config_builder.utils import addr_range, counter

config = YamahaRouterConfigBuilder("NVR700W")

LAN_ADDR = IPv4Network("192.168.57.0/24")
LAN_GUEST_ADDR = IPv4Network("192.168.2.0/24")

PRIVATE_ADDRS = [
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
    IPv4Network("100.64.0.0/10"),  # CGNAT
    IPv4Network("169.254.0.0/16"),  # リンクローカル
]

LAN_IF = "lan1"
LAN_GUEST_IF = "lan1/1"
WAN_IF = "onu1"
WAN_PREFIX = f"dhcp-prefix@{WAN_IF}"

interface_counter = counter(1)
IPIP6_TUNNEL_ID = next(interface_counter)

# 不正アクセス検知するタイプ
IDS_TYPES = ["ip", "ip-option", "fragment", "icmp", "udp", "tcp"]


class Device(NamedTuple):
    mac_addr: str
    ipv4_addr: IPv4Address


# ネットワークに接続されるデバイスと設定
DEVICES: list[Device] = [
    Device("2c:cf:67:11:40:cd", LAN_ADDR[4]),  # Raspberry Pi 5 (Wi-Fi)
    Device("18:c0:4d:dd:e2:40", LAN_ADDR[5]),  # EVOLV
    Device("20:0b:74:c5:dc:aa", LAN_ADDR[6]),  # プリンタ
    Device("90:09:d0:56:a3:b4", LAN_ADDR[8]),  # NAS
]


with config.section("User"):
    # ログインパスワード設定
    config.add(f"login password {environ['USER_PASSWORD']}")
    config.add(f"administrator password {environ['ADMIN_PASSWORD']}")

    # ログインセッションの期限を1時間に設定
    config.add(f"user attribute login-timer={60 * 60}")

with config.section("Route"):
    # IPv4 デフォルト経路設定
    with config.ip_route("default") as route:
        route.gateway(f"tunnel {IPIP6_TUNNEL_ID}")

    # IPv6 デフォルト経路設定
    with config.ipv6_route("default") as route:
        route.gateway(f"dhcp {WAN_IF}")

with config.section("LAN"):
    # LAN インタフェースの IPv4 アドレスの設定
    config.add(f"ip {LAN_IF} address {LAN_ADDR[1]}/{LAN_ADDR.prefixlen}")

    # LAN インタフェースの IPv6 アドレスの設定
    config.add(f"ipv6 {LAN_IF} address {WAN_PREFIX}::1/64")

    # ルーター広告する IPv6 プレフィックスの設定
    IPV6_PREFIX_ID = 1
    config.add(f"ipv6 prefix {IPV6_PREFIX_ID} {WAN_PREFIX}::/64")

    # ルーター広告の設定
    # o_flag=on: アドレス以外の情報をホストに自動取得させる (ゲートウェイとか？？よくわかってない)
    config.add(f"ipv6 {LAN_IF} rtadv send {IPV6_PREFIX_ID} o_flag=on")

    # LAN 方向に DHCPv6 サーバとして動作させる
    config.add(f"ipv6 {LAN_IF} dhcp service server")

    # 不正アクセスを検知したらパケットを drop する
    config.add(f"ip {LAN_IF} intrusion detection in on")
    for t in IDS_TYPES:
        # ICMP は iOS の通信が ICMP too large として不正アクセス検知されてしまうため有効にしない
        if t == "icmp":
            continue
        config.add(f"ip {LAN_IF} intrusion detection in {t} on reject=on")
    config.add(f"ip {LAN_IF} intrusion detection in default off")

with config.section("WAN"):
    # WAN 方向に DHCPv6 クライアントとして動作させる
    config.add(f"ipv6 {WAN_IF} dhcp service client")

    # WAN インタフェースの IPv6 アドレスは DHCP で取得する
    config.add(f"ipv6 {WAN_IF} address dhcp")

    # インタフェースがリンクダウンした際に DHCP サーバから得ていた情報をリリースする
    config.add("dhcp client release linkdown on")

    # NGN 網に接続する
    config.add(f"ngn type {WAN_IF} ntt")

    # WAN インタフェースのフィルタリング設定 (IN)
    config.ipv6_filter(
        WAN_IF,
        "in",
        static=[
            "pass * * icmp6 * *",
            # DHCPv6 サーバ (リンクローカルの 547 番ポート) からの応答のみ許可
            "pass fe80::/10 * udp 547 546",
            # IPv4 over IPv6 (MAP-E) のパケットはルータの MAP-E アドレス宛てのみ許可
            "pass * map-e 4",
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

    # 不正アクセスを検知したらパケットを drop する
    config.add(f"ip {WAN_IF} intrusion detection in on")
    for t in IDS_TYPES:
        config.add(f"ip {WAN_IF} intrusion detection in {t} on reject=on")
    config.add(f"ip {WAN_IF} intrusion detection in default off")

# IPv4 over IPv6 トンネル設定
with config.section("IPIP6"):
    with config.interface("tunnel", IPIP6_TUNNEL_ID):
        # IPIP6 の方式は MAP-E (v6プラス)
        config.add("tunnel encapsulation map-e")
        config.add("tunnel map-e type v6plus")

        # MTU 設定
        config.add("ip tunnel mtu 1460")

        # TCP の MSS をトンネルの MTU に合わせて自動調整する (カプセル化によるパケットサイズ超過対策)
        config.add("ip tunnel tcp mss limit auto")

        # 不正アクセスを検知したらパケットを drop する
        config.add("ip tunnel intrusion detection in on")
        for t in IDS_TYPES:
            # ICMP は iOS の通信が ICMP too large として不正アクセス検知されてしまうため有効にしない
            if t == "icmp":
                continue
            config.add(f"ip tunnel intrusion detection in {t} on reject=on")
        config.add("ip tunnel intrusion detection in default off")

        # トンネルインタフェースのフィルタリング設定 (IN)
        # 参考: https://network.yamaha.com/setting/router_firewall/security/wan_side/ip_filter_wizard_explain-nvr500
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

        # NAT 設定
        with config.nat("tunnel", "masquerade") as nat:
            # NAT 時の外側アドレスは MAP-E で自動生成されたアドレスを使う
            nat.add(f"nat descriptor address outer {nat.descriptor} map-e")

# VLAN (ゲストネットワーク)
with config.section("VLAN"):
    VLAN_ID = 2
    VLAN_NAME = "guest"

    config.add(f"vlan {LAN_GUEST_IF} 802.1q vid={VLAN_ID} name={VLAN_NAME}")
    config.add(f"ip {LAN_GUEST_IF} address {LAN_GUEST_ADDR[1]}/{LAN_GUEST_ADDR.prefixlen}")

    # ゲストネットワークからはルータへの DNS / DHCP とインターネットへのアクセスのみ許可
    config.ip_filter(
        LAN_GUEST_IF,
        "in",
        static=[
            f"pass {LAN_GUEST_ADDR} {LAN_GUEST_ADDR[1]} udp,tcp * domain",
            # DHCP の最初の要求は 0.0.0.0 → 255.255.255.255 で送られるため送信元・宛先とも * にする
            # bootpc / bootps のニーモニックは受け付けられないためポート番号で指定する
            "pass * * udp 68 67",
            *[f"reject * {addr} * * *" for addr in PRIVATE_ADDRS],
            f"pass {LAN_GUEST_ADDR} * * * *",
        ],
    )

    # メインネットワークからゲストネットワークへの通信の戻りパケットを動的フィルタで通す
    config.ip_filter(
        LAN_GUEST_IF,
        "out",
        static=["pass * * * * *"],
        dynamic=["* * tcp", "* * udp", "* * ping"],
    )

# DHCP 設定
with config.section("DHCP"):
    DHCP_SCOPE = 1  # メインネットワーク
    DHCP_SCOPE_GUEST = 2  # ゲストネットワーク

    # DHCP サーバを動作させる設定
    config.add("dhcp service server")

    # DHCP で払い出すアドレス範囲の設定
    config.add(f"dhcp scope {DHCP_SCOPE} {addr_range(LAN_ADDR, 2, 249)}")
    config.add(f"dhcp scope {DHCP_SCOPE_GUEST} {addr_range(LAN_GUEST_ADDR, 2, 249)}")

    # ゲストに通知する DNS サーバをゲスト側のルータアドレスにする (デフォルトではメイン側のアドレスになる)
    config.add(f"dhcp scope option {DHCP_SCOPE_GUEST} dns={LAN_GUEST_ADDR[1]}")

    # クライアント識別に Client-Identifier を使用しない
    config.add("dhcp server rfc2131 compliant except use-clientid")

    # DHCP 固定割り当て
    for device in DEVICES:
        config.add(f"dhcp scope bind {DHCP_SCOPE} {device.ipv4_addr} {device.mac_addr}")

# DNS 設定
with config.section("DNS"):
    # LAN からの DNS アクセスを許可する
    config.add(f"dns host {LAN_IF} {LAN_GUEST_IF}")

    # 名前解決は IPv6 を優先し、IPv6 で名前解決できない場合に IPv4 へフォールバックする
    config.add("dns service fallback on")

    # WAN の DHCP から DNS サーバのアドレスを取得して問い合わせに使用する
    config.add(f"dns server dhcp {WAN_IF} edns=on")

    # プライベートアドレスに対する問い合わせを上位サーバに転送しない
    config.add("dns private address spoof on")

# メール通知設定
with config.section("Mail"):
    SMTP_HOST = environ["SMTP_HOST"]
    SMTP_USERNAME = environ["SMTP_USERNAME"]
    SMTP_PASSWORD = environ["SMTP_PASSWORD"]
    MAIL_TO_ADDR = environ["MAIL_TO_ADDR"]

    # メールサーバの設定
    MAIL_SERVER_ID = 1
    config.add(f"mail server name {MAIL_SERVER_ID} default")
    config.add(f"mail server smtp {MAIL_SERVER_ID} {SMTP_HOST} smtp-auth {SMTP_USERNAME} {SMTP_PASSWORD} smtps")

    # メールテンプレートの設定
    MAIL_TEMPLATE_ID = 1
    config.add(f"mail template {MAIL_TEMPLATE_ID} {MAIL_SERVER_ID} From:{SMTP_USERNAME} To:{MAIL_TO_ADDR}")

    # メール通知項目の設定
    config.add(f"mail notify 1 {MAIL_TEMPLATE_ID} trigger lan-map")  # LANマップの異常検知
    config.add(f"mail notify 2 {MAIL_TEMPLATE_ID} trigger intrusion * in/out")  # 不正アクセス検知
    config.add(f"mail notify 3 {MAIL_TEMPLATE_ID} trigger status interface")  # 本体状態の手動通知

# その他
with config.section("Other"):
    # Syslog を NAS に保存
    config.add(f"syslog host {LAN_ADDR[8]}")

    # NOTICE レベルのログ (IP フィルタで reject したパケットなど) を出力する
    config.add("syslog notice on")

    # 管理画面へのアクセスは LAN からのみ許可する (ゲストネットワークからは許可しない)
    config.add(f"httpd host {LAN_IF}")

    # Telnet アクセスを無効化
    config.add("telnetd service off")

    # L2MS を有効にする (配下の YAMAHA 機器を管理する機能)
    config.add(f"switch control use {LAN_IF} on terminal=on")

    # 毎日6時に時刻同期する
    config.add("schedule at 1 */* 06:00:00 * ntpdate ntp.nict.jp syslog")

    # トラフィックと NAT のデータを取る
    config.add("statistics traffic on")
    config.add("statistics nat on")

if __name__ == "__main__":
    print(config.build())
