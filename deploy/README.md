# Running Jarvis 24/7

Your laptop sleeps. If you want the morning brief to actually arrive at 7am and
the bot to answer while you're out, Jarvis needs to live somewhere that doesn't.

The cheapest workable option is a $5/month VPS (Hetzner, DigitalOcean, Vultr).
Any Ubuntu 22.04+ box will do; Jarvis is not demanding.

```bash
# on the VPS, as root
adduser --disabled-password --gecos "" jarvis
apt update && apt install -y python3-venv git
su - jarvis

git clone <your repo url> gex-levels && cd gex-levels
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env        # paste your keys
.venv/bin/python -m jarvis --doctor      # confirm before daemonising

exit                                     # back to root
cp /home/jarvis/gex-levels/deploy/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now jarvis-bot jarvis-scheduler
journalctl -u jarvis-bot -f
```

Two things people get wrong:

**Timezone.** The scheduler uses the machine's local time, and a fresh VPS is
almost always UTC. Your 07:00 brief will land at the wrong hour until you run
`sudo timedatectl set-timezone Europe/Amsterdam` (or wherever you are).

**The .env file.** It holds live API keys and never belongs in git — it's
already in `.gitignore`. Copy it to the server by hand. `chmod 600 .env` so
other users on the box can't read it.
