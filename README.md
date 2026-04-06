# selenium-mcp

A **production-ready MCP (Model Context Protocol) server** that exposes Selenium 4 browser automation as MCP tools. Supports Chrome and Firefox with full BiDi (Bidirectional API) event streaming.

---

## Architecture

```
selenium-mcp/
├── server.py               # MCP entrypoint (JSON-RPC 2.0 over stdio)
├── config/
│   ├── settings.py         # ENV + YAML config loader (singleton)
│   ├── default.yaml        # Default configuration values
│   └── logging_config.py   # Structured logging setup
├── driver/
│   ├── factory.py          # WebDriver factory (Chrome / Firefox + BiDi)
│   ├── session.py          # BrowserSession – wraps a single WebDriver
│   └── session_manager.py  # Registry of all active sessions
├── events/
│   ├── dispatcher.py       # Async pub/sub event dispatcher (asyncio.Queue)
│   ├── bidi_listeners.py   # BiDi WebSocket event listeners
│   └── network_interceptor.py  # CDP/BiDi network interception
├── tools/
│   ├── base.py             # BaseTool + error-screenshot decorator
│   ├── navigation_tools.py # open_page, navigate_back/forward, get_dom
│   ├── interaction_tools.py# click, type_text, get_text, wait_for
│   ├── script_tools.py     # execute_js, screenshot
│   ├── log_tools.py        # get_console_logs, get_network_logs, intercept_requests
│   ├── session_tools.py    # create_session, close_session, list_sessions
│   └── registry.py         # Tool name → callable map + MCP descriptors
└── models/
    ├── session.py          # SessionInfo, BrowserType, SessionStatus
    ├── events.py           # BrowserEvent, ConsoleLogEvent, NetworkRequestEvent, …
    ├── network.py          # NetworkLog, ConsoleLog, InterceptRule, PerformanceMetrics
    └── exceptions.py       # Custom exception hierarchy
```

### Layered design

```
MCP Client (Claude / any MCP host)
        ↕  JSON-RPC 2.0 / stdio
    server.py  (MCPServer)
        ↕
    tools/registry.py  →  tools/*.py  (business logic)
        ↕
    driver/session_manager.py  →  driver/session.py
        ↕                               ↕
    driver/factory.py           events/bidi_listeners.py
    (WebDriver creation)        (BiDi / CDP event capture)
        ↕                               ↕
    Selenium 4 WebDriver       events/dispatcher.py
    (Chrome / Firefox)         (async pub/sub)
```

---

## Quick start

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Chrome / ChromeDriver | latest stable |
| Firefox / GeckoDriver | latest stable (optional) |

### Installation

```bash
# 1. Clone / enter the project
git clone <repo> selenium-mcp
cd selenium-mcp

# 2. Create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) install as editable package
pip install -e .
```

### Run the server

```bash
# Stdio mode (standard MCP transport)
python server.py

# Or via the installed entry-point
selenium-mcp
```

The server reads JSON-RPC 2.0 messages from **stdin** and writes responses to **stdout**.

---

## Configuration

Configuration is loaded in priority order:
1. **Environment variables** (`SMCP_*`)
2. **YAML file** (`SMCP_CONFIG_FILE` env var or `config/default.yaml`)
3. **Built-in defaults**

### Key settings

| ENV variable | YAML key | Default | Description |
|---|---|---|---|
| `SMCP_BROWSER` | `browser.default` | `chrome` | Default browser (`chrome`/`firefox`) |
| `SMCP_HEADLESS` | `browser.headless` | `true` | Run headless |
| `SMCP_MAX_SESSIONS` | `browser.max_sessions` | `5` | Max concurrent sessions |
| `SMCP_BIDI_ENABLED` | `bidi.enabled` | `true` | Enable BiDi WebSocket |
| `SMCP_LOG_LEVEL` | `server.log_level` | `INFO` | Log level |
| `SMCP_DEBUG` | `server.debug` | `false` | Verbose debug logging |
| `SMCP_SCREENSHOT_ON_ERROR` | `screenshot.on_error` | `true` | Auto-screenshot on errors |
| `SMCP_SCREENSHOT_DIR` | `screenshot.directory` | `screenshots/` | Screenshot output dir |

### Custom YAML config

```bash
SMCP_CONFIG_FILE=/path/to/my-config.yaml python server.py
```

Example `my-config.yaml`:
```yaml
browser:
  default: firefox
  headless: false
  max_sessions: 3
bidi:
  enabled: true
screenshot:
  on_error: true
  directory: /tmp/mcp-screenshots
```

---

## MCP Tools reference

### Session management

| Tool | Description | Key params |
|---|---|---|
| `create_session` | Open a new browser | `browser`, `headless` |
| `close_session` | Close a session | `session_id` |
| `list_sessions` | List active sessions | — |
| `get_session_info` | Get session metadata | `session_id` |

### Navigation

| Tool | Description | Key params |
|---|---|---|
| `open_page` | Navigate to URL | `url` |
| `navigate_back` | History back | — |
| `navigate_forward` | History forward | — |
| `get_dom` | Full page HTML | — |

### Element interaction

| Tool | Description | Key params |
|---|---|---|
| `click` | Click a CSS selector | `selector` |
| `type_text` | Type into an input | `selector`, `text` |
| `get_text` | Get element text | `selector` |
| `wait_for` | Wait until visible | `selector`, `timeout` |
| `wait_for_dom_stable` | Smart DOM-stability wait | `timeout` |

### Script & media

| Tool | Description | Key params |
|---|---|---|
| `execute_js` | Run JavaScript | `script` |
| `screenshot` | Capture viewport (base64 PNG) | — |

### Logs & network

| Tool | Description | Key params |
|---|---|---|
| `get_console_logs` | Browser console entries | — |
| `get_network_logs` | Network request/response log | — |
| `get_performance_metrics` | Page timing data | — |
| `intercept_requests` | Register URL intercept rule | `pattern`, `action` |

---

## Connecting to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "selenium": {
      "command": "python",
      "args": ["/absolute/path/to/selenium-mcp/server.py"],
      "env": {
        "SMCP_HEADLESS": "false",
        "SMCP_BROWSER": "chrome"
      }
    }
  }
}
```

---

## BiDi / Event system

When `bidi.enabled: true` the server attaches BiDi WebSocket listeners to each session:

- **Console events** – `console.log`, `console.error`, etc. are captured and stored per-session. Retrieved via `get_console_logs`.
- **JS errors** – JavaScript runtime errors are captured as `error`-level console entries.
- **Network events** – CDP `Network.enable` (Chrome) captures request/response data. Retrieved via `get_network_logs`.
- **Event dispatcher** – All events flow through an `asyncio.Queue`-backed pub/sub hub (`events/dispatcher.py`). Custom async handlers can be registered per event type for real-time streaming use cases.

---

## Error handling

All tools wrap failures in a typed exception hierarchy:

| Exception | Trigger |
|---|---|
| `SessionNotFoundError` | Invalid `session_id` |
| `SessionLimitError` | Too many concurrent sessions |
| `ElementNotFoundError` | CSS selector matched nothing |
| `ElementInteractionError` | Element not clickable/typeable |
| `NavigationError` | `get()` / history navigation failed |
| `ScriptExecutionError` | JavaScript threw or timed out |
| `TimeoutError` | `wait_for` condition not met |
| `NetworkInterceptionError` | CDP interception setup failed |
| `BiDiNotSupportedError` | BiDi requested but unavailable |

When `screenshot.on_error: true`, a PNG is saved to `screenshot.directory` automatically on any `SeleniumMCPError`.

---

## Development

```bash
# Lint
ruff check .

# Type check
mypy .

# Tests
pytest tests/ -v
```

---

## Retry mechanism

All element interactions use an internal `_retry()` helper that retries on `StaleElementReferenceException` and transient `WebDriverException`. Configurable via:

```yaml
retry:
  max_attempts: 3
  backoff_seconds: 1.0
```
