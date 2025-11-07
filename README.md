# Linkedin Automation

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=eracle/linkedin&type=Date)](https://star-history.com/#eracle/linkedin&Date)

### Join our [Telegram Group](https://t.me/+Y5bh9Vg8UVg5ODU0).

---

# LinkedIn Automation Tool Functionalities

- **Automation Engine**: Using Playwright for browser automation, including login, navigation, and interactions on
  LinkedIn, with stealth features to avoid detection.
- **Campaigns**: Support creation and execution of action sequences (e.g., search profiles, send personalized
  connections, follow-ups) via configurable YAML.
- **Future Planning/Scheduling**: Implement time-based action queuing (e.g., drip campaigns, recurring tasks) using
  async libraries, with persistence for resuming interrupted sessions.
- **Local Database**: Use DuckDB (or fallback to SQLite) for storing scraped data, campaign logs, schedules, and
  metrics; leverage DuckDB's analytical capabilities for queries.
- **Personalized Messages with AI**: Integrate open AI models to generate customized messages based on scraped profile
  data.
- **Strong Analytics**: Track metrics like action success rates, engagement (accepts, replies), and errors dashboards.

## Installation and Setup

You will need the following:

- Docker and docker compose
- A VNC viewer (e.g., Vinagre for Ubuntu)

### Steps

1. **Prepare your environment**: Install Docker from the [official website](https://www.docker.com/). If you don't have
   a VNC viewer, install one. For Ubuntu, you can use Vinagre:

```bash
sudo apt-get update
sudo apt-get install vinagre
```

## Legal Disclaimer

This code is not affiliated with, authorized, maintained, sponsored, or endorsed by LinkedIn or any of its affiliates or
subsidiaries. This is an independent and unofficial project. Use at your own risk.

This project violates LinkedIn's User Agreement Section 8.2. As a result, LinkedIn may temporarily or permanently ban
your account. We are not responsible for any actions taken by LinkedIn in response to the use of this tool.

---
