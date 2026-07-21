# 📨 Message API

A **production-ready** FastAPI application for sending text messages to **Telegram** using both the official **Telegram Bot API** and **Telegram Client API (Telethon)**. Includes a built-in interactive **Web Dashboard UI**, automatic phone-number resolution, smart fallback routing, and auto-retry mechanics.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Dual Transport Routing** | Support for **Telegram Bot API** (Chat ID / Username) and **Telethon Client API** (Phone Numbers) |
| **Phone-to-Chat Resolution** | Auto-detects E.164 phone numbers (`+<digits>`), resolves numeric Telegram Chat IDs, and routes messages seamlessly |
| **Smart Fallback** | Attempts Bot API delivery first after resolving phone numbers; falls back to Telethon Client API if the bot is unstarted or blocked |
| **Interactive Web Dashboard** | Web UI served at `/` (`static/index.html`) featuring live health status, custom recipient targeting, and real-time response previews |
| **Async I/O Architecture** | Powered by `asyncio` + `httpx` for non-blocking HTTP requests |
| **Resilient Retries** | Exponential back-off on network failures via `tenacity` |
| **Strict Data Validation** | Pydantic v2 models with auto-generated OpenAPI schemas |
| **Interactive API Documentation** | Swagger UI at `/docs` and ReDoc at `/redoc` |
| **Health Check Endpoint** | `GET /health` monitoring endpoint for uptime probes |
| **Fully Testable** | Comprehensive pytest test suite using `respx` for offline API mocking |

---

## 📂 Project Structure

```
MESSAGE API/
├── app/
│   ├── __init__.py        # Package marker
│   ├── main.py            # FastAPI app factory, lifespan & middleware
│   ├── config.py          # Application settings loaded via pydantic-settings
│   ├── models.py          # Pydantic request/response models & Enums
│   ├── routes.py          # API route definitions (/send, /health)
│   ├── telegram.py        # Telegram transport router & Bot API client
│   ├── telegram_client.py # Telethon client API for phone number messaging
│   └── utils.py           # Logging, HTTP client factory, retry decorators
│
├── static/                # Built-in Interactive Web Dashboard
│   ├── index.html         # Dashboard HTML structure
│   ├── style.css          # Modern dashboard styling & dark theme
│   └── app.js             # Frontend API request handler & UI interaction
│
├── tests/                 # Test Suite
│   ├── __init__.py
│   ├── conftest.py        # Test fixtures & auto-mocked settings
│   ├── test_routes.py     # Endpoint integration tests
│   └── test_telegram.py   # Telegram service unit tests
│
├── .env                   # Environment secrets (git-ignored)
├── .env.example           # Template for environment variables
├── .gitignore
├── app.py                 # Convenience server launcher
├── auth_telethon.py       # One-time interactive Telethon session authenticator
├── postman_collection.json# Pre-configured Postman API collection
├── pyproject.toml         # Pytest & project tool configurations
├── requirements.txt       # Python dependencies
├── run.py                 # Main application entry point
└── README.md              # Project documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.12+**
- A **Telegram Bot Token** (obtainable from [@BotFather](https://t.me/BotFather))
- *(Optional for Phone Number Messaging)* **Telegram API ID & Hash** (obtainable from [my.telegram.org](https://my.telegram.org))

### 2. Clone & Install

```bash
cd Message-API-main

# Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Credentials

Create a `.env` file from the provided example template:

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

Edit `.env` with your credentials:

```env
# Required: Telegram Bot API
TELEGRAM_BOT_TOKEN=7123456789:AAF...your-bot-token
TELEGRAM_CHAT_ID=123456789

# Optional: Telethon Client API (Required ONLY for sending to phone numbers)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_PHONE=+919876543210
```

### 4. Authenticate Telethon (Optional — For Phone Number Delivery)

If you intend to send messages directly to phone numbers:

```bash
python auth_telethon.py
```

Follow the interactive prompts to enter the OTP code sent to your Telegram app. A local `.session` file will be generated for persistent session reuse.

### 5. Launch the Server

Run either entry point:

```bash
python run.py
# or
python app.py
```

The API server will start at **http://localhost:8000**:

- 💻 **Web Dashboard** → [http://localhost:8000/](http://localhost:8000/)
- 📄 **Swagger UI Docs** → [http://localhost:8000/docs](http://localhost:8000/docs)
- 📘 **ReDoc** → [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 API Reference

### `POST /send`

Sends a text message to Telegram. Automatically selects the transport based on the `recipient` format.

**Request Body:**

```json
{
  "platform": "telegram",
  "message": "Hello World",
  "recipient": "+919876543210"
}
```

| Field | Type | Required | Description / Constraints |
|---|---|---|---|
| `platform` | string | ✅ | Must be `"telegram"` |
| `message` | string | ✅ | Text content (1 – 4096 characters) |
| `recipient` | string | ❌ | Target Chat ID, `@username`, or Phone Number (`+<digits>`). Defaults to `TELEGRAM_CHAT_ID` if omitted. |

**Recipient Transport Rules:**
- **Numeric Chat ID** (e.g. `123456789`) or **Username** (e.g. `@username`) → Dispatched via **Telegram Bot API**.
- **Phone Number** in E.164 format (e.g. `+919876543210`) → Resolved to a Chat ID and dispatched via Bot API, falling back automatically to Telethon Client API if needed.

**Success Response (200 OK):**

```json
{
  "success": true,
  "platform": "telegram",
  "message": "Message sent via Telegram successfully.",
  "details": {
    "ok": true,
    "result": {
      "message_id": 105,
      "chat": { "id": 123456789 }
    }
  }
}
```

**Error Responses:**

| Status Code | Reason |
|---|---|
| `422 Unprocessable Entity` | Validation error (e.g., empty message, unsupported platform) |
| `502 Bad Gateway` | Upstream Telegram API error or unreachable service |
| `504 Gateway Timeout` | Telegram API request timeout after retries |

---

### `GET /health`

Health monitoring probe.

**Response (200 OK):**

```json
{
  "status": "healthy"
}
```

---

## 🧪 Example Commands

### Send to Default Chat ID

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{"platform": "telegram", "message": "Hello from curl! 🚀"}'
```

### Send to Phone Number

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{"platform": "telegram", "message": "Hello via phone number!", "recipient": "+919876543210"}'
```

### PowerShell (Windows)

```powershell
Invoke-RestMethod -Uri http://localhost:8000/send `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"platform":"telegram","message":"Hello from PowerShell!","recipient":"@username"}'
```

---

## 🧪 Running Tests

The test suite runs completely offline with mocked API handlers.

```bash
pytest -v
# or
python -m pytest -v
```

---

## 🔧 Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Telegram Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Default target Chat ID / Group / Channel ID |
| `TELEGRAM_API_ID` | ❌ | — | Telegram App API ID from my.telegram.org (For Telethon) |
| `TELEGRAM_API_HASH` | ❌ | — | Telegram App API Hash from my.telegram.org (For Telethon) |
| `TELEGRAM_PHONE` | ❌ | — | Phone number associated with your Telegram Client session |
| `API_TIMEOUT` | ❌ | `30` | HTTP request timeout in seconds |
| `MAX_RETRIES` | ❌ | `3` | Maximum retry attempts for HTTP calls |
| `LOG_LEVEL` | ❌ | `"INFO"` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 📬 Postman Collection

Import `postman_collection.json` into Postman to test pre-configured requests:

1. **Health Check** — `GET /health`
2. **Send Telegram Message** — `POST /send`
3. **Invalid Platform / Validation Check** — expects `422`

---

## 📄 License

MIT License — free to use and modify.
