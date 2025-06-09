# 作業メモ

## 操作
### DHCP
- 一覧を見る `show status dhcp summary`

### IP フィルタ
- ログを出力する `syslog notice on`

### NAT
- NAT セッションテーブル確認 `show nat descriptor address`
  - → `参照NATディスクリプタ : 1, 適用インタフェース : TUNNEL[2](1)` は存在するが、そこにクライアントの IP がない
- NAT ディレクトリのログ出力 `nat descriptor log on`

### ネットボランチ DNS
- 一覧を見る `netvolante-dns get hostname list all`
- 削除する `netvolante-dns delete go {INTERFACE} {HOSTNAME}`


## VPN うまくいかない問題
iOS 18 から VPN 接続した際にインターネットに接続できない

- ローカルネットワーク (NAS, 192.168.57.8) には接続できる
- IP フィルタによってブロックされていることが原因ではないっぽい？
  - IP フィルタをすべて無効にしても通らなかったので
- NAT できていないっぽい
  - NAT セッションテーブルにクライアントに払い出した IP アドレスが存在しないので
- DNS (UDP 53) だけはインターネットに出ることができている？
  - NAT ログを出力すると DNS (53) は Bound で外に出ているログがあるが、HTTPS (443) などはログに存在しない
  - `ip tunnel nat descriptor 1` すると DNS の Bound ログすら出なくなる
- tunnel 2 の MTU を下げてみたが変化なかった
  - 1500 (デフォルト) から 1400-1280 まで試したけどダメだった

### 参考
- [iPhoneでIPv6のリモートアクセスVPNをIKEv2でつなげたお話。【RTX830】 – かなぽんの備忘録Vol.2](https://www.kanapon.me/archives/2908)
  - IPv6 + IKEv2 の参考例
- [YAMAHA RTX1210でリモートアクセスVPN (IKEv2)環境を作る（Mac/iPhone対応） - Qiita](https://qiita.com/yyasuda/items/2d7ef460064a6a4b6699)
  - iOS 18 で IKEv2 接続時に認証が失敗する問題があったが、この記事を参考に Apple Configurator を使用して DH グループ14を要求するように設定したところ、接続できるようになった
- [はじめての「ヤマハ vRX さくらのクラウド版」（7）NAT（IPマスカレード、NAPT）の適用 | さくらのナレッジ](https://knowledge.sakura.ad.jp/41625/)
  - NAT ログ, パケットフィルタログ の見方