from os import environ

from yamaha_router_config_builder import YamahaRouterConfigBuilder
from yamaha_router_config_builder.utils import IPv4Addr

config = YamahaRouterConfigBuilder("NVR700W")

LAN_ADDR = IPv4Addr("192.168.57.0/24")
LAN_GUEST_ADDR = IPv4Addr("192.168.2.0/24")

LAN_IF = "lan1"
LAN_GUEST_IF = "lan1/1"
WAN_IF = "onu1"

IPIP6_TUNNEL_ID = 1

# 不正アクセス検知するタイプ
IDS_TYPES = ["ip", "ip-option", "fragment", "icmp", "udp", "tcp"]

with config.section("User"):
    # ログインパスワード設定
    config.add(f"login password {environ["USER_PASSWORD"]}")
    config.add(f"administrator password {environ["ADMIN_PASSWORD"]}")

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
    config.add(f"ip {LAN_IF} address {LAN_ADDR(1, prefix=True)}")

    # LAN インタフェースの IPv6 アドレスの設定
    config.add(f"ipv6 {LAN_IF} address dhcp-prefix@{WAN_IF}::1/64")

    # ルーター広告する IPv6 プレフィックスの設定
    IPV6_PREFIX_ID = 1
    config.add(f"ipv6 prefix {IPV6_PREFIX_ID} dhcp-prefix@{WAN_IF}::/64")

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

    # WAN インタフェースの IPv4 アドレスは DHCP で取得する
    config.add(f"ip {WAN_IF} address dhcp")  # IPoE って IPv4 アドレスもらえるのか？

    # WAN インタフェースの IPv6 アドレスは DHCP で取得する
    config.add(f"ipv6 {WAN_IF} address dhcp")

    # インタフェースがリンクダウンした際に DHCP サーバから得ていた情報をリリースする
    config.add(f"dhcp client release linkdown on")

    # NGN 網に接続する
    config.add(f"ngn type {WAN_IF} ntt")

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

    # 不正アクセスを検知したらパケットを drop する
    config.add(f"ip {WAN_IF} intrusion detection in on")
    for t in IDS_TYPES:
        config.add(f"ip {WAN_IF} intrusion detection in {t} on reject=on")
    config.add(f"ip {WAN_IF} intrusion detection in default off")

# IPv4 over IPv6 トンネル設定
with config.section("IPIP6"):
    with config.interface("tunnel", IPIP6_TUNNEL_ID):
        # トンネルの種別を MAP-E として設定
        config.add("tunnel encapsulation map-e")

        # MAP-E の種別を OCN バーチャルコネクトとして設定
        config.add("tunnel map-e type ocn")

        # MTU 設定
        config.add("ip tunnel mtu 1460")

        # 不正アクセスを検知したらパケットを drop する
        config.add(f"ip tunnel intrusion detection in on")
        for t in IDS_TYPES:
            # ICMP は iOS の通信が ICMP too large として不正アクセス検知されてしまうため有効にしない
            if t == "icmp":
                continue
            config.add(f"ip tunnel intrusion detection in {t} on reject=on")
        config.add(f"ip tunnel intrusion detection in default off")

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

        # NAT 設定
        with config.nat("tunnel", "masquerade") as nat:
            # NAT 時の外側アドレスは MAP-E で自動生成されたアドレスを使う
            nat.add(f"nat descriptor address outer {nat.descriptor} map-e")

# VLAN (ゲストネットワーク)
with config.section("VLAN"):
    VLAN_ID = 2
    VLAN_NAME = "guest"

    config.add(f"vlan {LAN_GUEST_IF} 802.1q vid={VLAN_ID} name={VLAN_NAME}")
    config.add(f"ip {LAN_GUEST_IF} address {LAN_GUEST_ADDR(1, True)}")

    # ゲストネットワークからプライベートアドレスへのアクセスを拒否
    config.ip_filter(
        LAN_GUEST_IF,
        "in",
        static=[
            f"reject {LAN_GUEST_ADDR} {LAN_ADDR}",
            "pass * * * * *",
        ],
    )

# DHCP 設定
with config.section("DHCP"):
    DHCP_SCOPE = 1  # メインネットワーク
    DHCP_SCOPE_GUEST = 2  # ゲストネットワーク

    # DHCP サーバを動作させる設定
    config.add(f"dhcp service server")

    # DHCP で払い出すアドレス範囲の設定
    config.add(f"dhcp scope {DHCP_SCOPE} {LAN_ADDR.range(2, 239)}")
    config.add(f"dhcp scope {DHCP_SCOPE_GUEST} {LAN_GUEST_ADDR.range(2, 239)}")

    # クライアント識別に Client-Identifier を使用しない
    config.add(f"dhcp server rfc2131 compliant except use-clientid")

    # DHCP 固定割り当て
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(4)} 2c:cf:67:11:40:cd")  # Raspberry Pi 5 (Wi-Fi)
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(5)} 18:c0:4d:dd:e2:40")  # EVOLV
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(6)} 38:9d:92:bc:e0:cf")  # プリンタ
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(8)} 90:09:d0:56:a3:b4")  # NAS

# DNS 設定
with config.section("DNS"):
    # LAN からの DNS アクセスを許可する
    config.add(f"dns host {LAN_IF} {LAN_GUEST_IF}")

    # 名前解決は IPv6 を優先し、IPv6 で名前解決できない場合に IPv4 へフォールバックする
    config.add(f"dns service fallback on")

    # WAN の DHCP から DNS サーバのアドレスを取得して問い合わせに使用する
    config.add(f"dns server dhcp {WAN_IF} edns=on")

    # プライベートアドレスに対する問い合わせを上位サーバに転送しない
    config.add(f"dns private address spoof on")

# メール通知設定
with config.section("Mail"):
    SMTP_HOST = environ.get("SMTP_HOST")
    SMTP_USERNAME = environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = environ.get("SMTP_PASSWORD")
    MAIL_TO_ADDR = environ.get("MAIL_TO_ADDR")

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
    config.add(f"syslog host {LAN_ADDR(8)}")

    # 管理画面へのアクセスは LAN からのみ許可する (ゲストネットワークからは許可しない)
    config.add(f"httpd host {LAN_IF}")

    # Telnet アクセスを無効化
    config.add("telnetd service off")

    # L2MS を有効にする (配下の YAMAHA 機器を管理する機能)
    config.add(f"switch control use {LAN_IF} on terminal=on")

    # 毎日6時に時刻同期する
    config.add("schedule at 1 */* 06:00:00 * ntpdate ntp.nict.jp syslog")

    # トラフィックの統計データを取る
    config.add("statistics traffic on")

    # ネットボランチ DNS を設定
    NETVOLANTE_DNS_HOST = environ.get("NETVOLANTE_DNS_HOST")
    config.add(f"netvolante-dns hostname host {WAN_IF} {NETVOLANTE_DNS_HOST} ipv6 address")

if __name__ == "__main__":
    print(config.build())
