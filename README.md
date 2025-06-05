# YAMAHA Router Config
YAMAHA Router as Code

## Setup
Create `.env` file

```
USER_PASSWORD=
ADMIN_PASSWORD=
SMTP_HOST=
SMTP_USERNAME=
SMTP_PASSWORD=
MAIL_TO_ADDR=
NETVOLANTE_DNS_HOST=example.aa0.netvolante.jp
VPN_CLIENTS=foo,bar
VPN_PSK=
VPN_GW_ID_DOMAIN=example.com
```

## Usage
1. `python main.py > config.txt`
2. Import the file into your router
