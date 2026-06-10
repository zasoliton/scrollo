# Market Matrix Scroller

`Market Matrix Scroller` is a Raspberry Pi friendly fullscreen dashboard that borrows the feel of a HUB75 ticker wall while targeting a 1080p HDMI display instead of an LED matrix.

It includes:

- A `pygame` renderer for fullscreen stock and headline scrolling.
- A `FastAPI` web panel for configuring stocks, RSS feeds, and colors.
- JSON-backed settings persistence so changes survive reboots.
- Background refresh services for stock quotes and RSS feeds.

## Features

- Fullscreen 1080p display for a portable monitor connected to a Raspberry Pi.
- LED-inspired visual style with bright ticker colors on a dark background.
- Horizontal headline marquee with adjustable speed.
- Multi-symbol stock board with live price and daily percentage move.
- Web admin panel for editing:
  - app title
  - stock symbols
  - RSS feeds
  - refresh timing
  - theme colors
- Sensible defaults so the project boots with useful data immediately.
- Automatic fallback for stock quotes if the primary source rejects requests.

## Quick Start

1. Create a virtual environment and install the app:

```bash
make install
```

2. Run the scroller:

```bash
make run
```

3. Open the config panel from another device on the same network:

```text
http://<raspberry-pi-ip>:8787
```

The app stores settings in `data/settings.json` by default.

If you prefer the explicit commands instead of `make`, you can still use:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
market-matrix-scroller
```

## Raspberry Pi Notes

- Raspberry Pi OS Bookworm with Python 3.11 works well for this stack.
- For the best kiosk feel, configure the Pi to auto-login to the desktop or console and launch the app via `systemd`.
- If you are using a 1080p portable display, leave fullscreen enabled and the renderer will use the current display mode automatically.
- The stock quote layer tries a lightweight Yahoo Finance request first and falls back to `stockprices.dev` if Yahoo rejects the request. Both are unofficial convenience sources, so if you want a more durable production deployment later, the service layer is isolated so we can swap in a paid API easily.

## Suggested `systemd` Service

Create `/etc/systemd/system/market-matrix.service`:

```ini
[Unit]
Description=Market Matrix Scroller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/market-matrix-scroller
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/market-matrix-scroller/.venv/bin/market-matrix-scroller
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now market-matrix.service
```

## Project Layout

```text
src/scroller_app/
  app.py          Runtime entrypoint
  config.py       JSON settings persistence
  data_sources.py RSS and stock integrations
  models.py       Config and data models
  renderer.py     Fullscreen pygame UI
  services.py     Background refresh coordinator
  state.py        Shared thread-safe app state
  web.py          FastAPI admin panel
  templates/      Admin UI HTML
  static/         Admin UI CSS
tests/
  test_config_store.py
```

## Development

Run the tests:

```bash
make test
```
