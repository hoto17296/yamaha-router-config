from yamaha.builder import YamahaRouterConfigBuilder
from utils import Env, IPv4Addr

ENV = Env(".env")

config = YamahaRouterConfigBuilder("NVR700W")

LAN_ADDR = IPv4Addr("192.168.57.0/24")

LAN_IF = "lan1"
WAN_IF = "onu1"

IPIP6_TUNNEL_ID = 1

with config.section("User"):
    # ログインパスワード設定
    config.add(f"login password {ENV.USER_PASSWORD}")
    config.add(f"administrator password {ENV.ADMIN_PASSWORD}")

    # ログインセッションの期限を1時間に設定
    config.add(f"user attribute login-timer={60 * 60}")

with config.section("Route"):
    # IPv4 デフォルト経路設定
    with config.ip_route("default") as route:
        # VPN 通信は PPPoE に流す
        route.gateway(
            f"pp 1",
            filters=[
                "pass * * esp",
                "pass * * udp 500 *",
                "pass * * udp 4500 *",
            ],
        )
        # それ以外は IPIP6 トンネルに流す
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
    config.add(f"ip {LAN_IF} intrusion detection in on reject=on")
    config.add(f"ip {LAN_IF} intrusion detection out on reject=on")

    # iOS 15 以降の iPhone が何らかのタイミングで巨大 ping を送信する挙動によって不正アクセスとして検知されてしまうため、
    # よい対策を思いつくまでの間は ICMP の不正アクセス検知を無効にする
    config.add(f"ip {LAN_IF} intrusion detection in icmp off")

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
    config.add(f"ip {WAN_IF} intrusion detection in on reject=on")
    config.add(f"ip {WAN_IF} intrusion detection out on reject=on")

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
        config.add("ip tunnel intrusion detection in on reject=on")
        config.add("ip tunnel intrusion detection out on reject=on")

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

        # NAT 設定
        with config.nat("tunnel", "masquerade") as nat:

            # NAT 時の外側アドレスは MAP-E で自動生成されたアドレスを使う
            nat.add(f"nat descriptor address outer {nat.descriptor} map-e")

# PPPoE 設定
with config.section("PPPoE"):
    with config.interface("pp", 1):
        config.add(f"description pp {ENV.PPPOE_DESCRIPTION}")
        config.add("pp keepalive interval 30 retry-interval=30 count=12")

        # 常時接続する
        config.add("pp always-on on")

        # WAN インタフェースを使用
        config.add(f"pppoe use {WAN_IF}")

        # PPPoE セッションを自動切断しない
        config.add("pppoe auto disconnect off")

        # 認証タイプとして PAP と CHAP を受け入れる
        config.add("pp auth accept pap chap")

        # 認証情報
        config.add(f"pp auth myname {ENV.PPPOE_USERNAME} {ENV.PPPOE_PASSWORD}")

        # MRU の設定
        config.add("ppp lcp mru on 1454")

        # 接続相手と IP アドレスのネゴシエーションをする
        config.add("ppp ipcp ipaddress on")

        # IPCP の MS 拡張オプションを使う (DNS サーバアドレスを受け取れるようにする)
        config.add("ppp ipcp msext on")

        # パケットを圧縮しない
        config.add("ppp ccp type none")

        # 不正アクセスを検知したらパケットを drop する
        config.add("ip pp intrusion detection in on reject=on")
        config.add("ip pp intrusion detection out on reject=on")

        # PP インタフェースのフィルタリング設定 (IN)
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

        # PP インタフェースのフィルタリング設定 (OUT)
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

        # NAT 設定
        with config.nat("pp", "masquerade") as nat:

            # VPN 通信ではポート番号変換を行わない
            nat.add(f"nat descriptor masquerade static {nat.descriptor} 1 {LAN_ADDR(1)} esp")
            nat.add(f"nat descriptor masquerade static {nat.descriptor} 2 {LAN_ADDR(1)} udp 500")
            nat.add(f"nat descriptor masquerade static {nat.descriptor} 3 {LAN_ADDR(1)} udp 4500")

    # DDNS 設定
    config.add(f"netvolante-dns hostname host pp server=1 {ENV.HOSTNAME}")

# DHCP 設定
with config.section("DHCP"):
    DHCP_SCOPE = 1

    # DHCP サーバを動作させる設定
    config.add(f"dhcp service server")

    # DHCP で払い出すアドレス範囲の設定
    config.add(f"dhcp scope {DHCP_SCOPE} {LAN_ADDR.range(2, 239)}")

    # クライアント識別に Client-Identifier を使用しない
    config.add(f"dhcp server rfc2131 compliant except use-clientid")

    # DHCP 固定割り当て
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(6)} 38:9d:92:bc:e0:cf")  # プリンタ
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(7)} 00:01:2e:71:c4:cf")  # サーバ (ZBOX)
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(8)} 00:11:32:71:e5:07")  # NAS
    config.add(f"dhcp scope bind {DHCP_SCOPE} {LAN_ADDR(9)} 1c:69:7a:6a:66:8f")  # サーバ (NUC)

# DNS 設定
with config.section("DNS"):
    # LAN からの DNS アクセスを許可する
    config.add(f"dns host {LAN_IF}")

    # 名前解決は IPv6 を優先し、IPv6 で名前解決できない場合に IPv4 へフォールバックする
    config.add(f"dns service fallback on")

    # WAN の DHCP から DNS サーバのアドレスを取得して問い合わせに使用する
    config.add(f"dns server dhcp {WAN_IF} edns=on")

    # プライベートアドレスに対する問い合わせを上位サーバに転送しない
    config.add(f"dns private address spoof on")

# その他
with config.section("Other"):
    # Syslog を NAS に保存
    config.add(f"syslog host {LAN_ADDR(8)}")

    # Telnet アクセスを無効化
    config.add("telnetd service off")

    # L2MS を有効にする (配下の YAMAHA 機器を管理する機能)
    config.add(f"switch control use {LAN_IF} on terminal=on")

    # 毎日6時に時刻同期する
    config.add("schedule at 1 */* 06:00:00 * ntpdate ntp.nict.jp syslog")

    # トラフィックの統計データを取る
    config.add("statistics traffic on")

if __name__ == "__main__":
    print(config.build())
