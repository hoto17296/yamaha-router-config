# YAMAHA Router Config
YAMAHA Router as Code

## Setup
Create a `.devcontainer/compose.env.yaml` file like the one below and open this repository in Dev Containers.

```
services:
  workspace:
    environment:
      USER_PASSWORD:
      ADMIN_PASSWORD:
      SMTP_HOST:
      SMTP_USERNAME:
      SMTP_PASSWORD:
      MAIL_TO_ADDR:
```

## Usage
1. `python src/RTX1300.py > config.txt`
2. Import the file into your router
