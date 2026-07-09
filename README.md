# 📨 Message API

A **production-ready** FastAPI application for sending text messages to **Telegram** and **WhatsApp** using their official APIs.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Dual Platform** | Telegram Bot API + Meta WhatsApp Cloud API |
| **Async I/O** | `asyncio` + `httpx` for non-blocking requests |
| **Auto-retry** | Exponential back-off on failures (configurable) |
| **Timeout Handling** | Configurable per-request timeouts |
| **Input Validation** | Pydantic v2 models with strict constraints |
| **Structured Logging** | Every request logged with context |
| **API Docs** | Swagger UI at `/docs`, ReDoc at `/redoc` |
| **Health Check** | `GET /health` endpoint |
| **CORS Enabled** | Ready for frontend integration |
| **Full Test Suite** | Unit + integration tests with mocked APIs |

---

## 📂 Project Structure

```
MESSAGE API/
├── app/
│   ├── __init__.py        # Package marker
│   ├── main.py            # FastAPI app factory & lifespan
│   ├── config.py          # Settings from .env via pydantic-settings
│   ├── models.py          # Pydantic request/response models
│   ├── routes.py          # API endpoint definitions
│   ├── telegram.py        # Telegram Bot API service
│   ├── whatsapp.py        # WhatsApp Cloud API service
│   └── utils.py           # Logging, HTTP client, retry logic
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Shared fixtures (mock settings, test client)
│   ├── test_telegram.py   # Telegram service tests
│   ├── test_whatsapp.py   # WhatsApp service tests
│   └── test_routes.py     # API route integration tests
│
├── .env                   # Your secrets (git-ignored)
├── .env.example           # Template for .env
├── .gitignore
├── requirements.txt
├── pyproject.toml         # Pytest configuration
├── postman_collection.json
├── run.py                 # Entry point
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.12+**
- A **Telegram Bot** token (create one via [@BotFather](https://t.me/BotFather))
- A **Meta Developer** account with WhatsApp Cloud API access

### 2. Clone & Install

```bash
cd "MESSAGE API"

# Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Credentials

Copy the example file and fill in your real credentials:

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=7123456789:AAF...your-token
TELEGRAM_CHAT_ID=123456789

WHATSAPP_ACCESS_TOKEN=EAAG...your-token
WHATSAPP_PHONE_NUMBER_ID=100000000000000
WHATSAPP_RECIPIENT_NUMBER=+1234567890
```

### 4. Run the Server

```bash
python run.py
```

The API is live at **http://localhost:8000**

- 📄 Swagger UI → [http://localhost:8000/docs](http://localhost:8000/docs)
- 📘 ReDoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 API Reference

### `POST /send`

Send a message to Telegram or WhatsApp.

**Request Body:**

```json
{
  "platform": "telegram",
  "message": "Hello World"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `platform` | string | ✅ | `telegram` or `whatsapp` |
| `message` | string | ✅ | 1 – 4096 characters |

**Success Response (200):**

```json
{
  "success": true,
  "platform": "telegram",
  "message": "Message sent via Telegram successfully.",
  "details": { ... }
}
```

**Error Responses:**

| Status | Meaning |
|---|---|
| `422` | Validation error (bad platform, empty message) |
| `502` | Upstream API error |
| `504` | Upstream API timeout |

### `GET /health`

```json
{ "status": "healthy" }
```

---

## 🧪 Example `curl` Commands

### Send to Telegram

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{"platform": "telegram", "message": "Hello from curl! 🚀"}'
```

### Send to WhatsApp

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{"platform": "whatsapp", "message": "Hello from curl! 🚀"}'
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Windows PowerShell

```powershell
Invoke-RestMethod -Uri http://localhost:8000/send `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"platform":"telegram","message":"Hello from PowerShell!"}'
```

---

## 📬 Postman

Import `postman_collection.json` into Postman. The collection includes:

1. **Health Check** — `GET /health`
2. **Send Telegram Message** — `POST /send`
3. **Send WhatsApp Message** — `POST /send`
4. **Invalid Platform** — expects `422`
5. **Empty Message** — expects `422`

> The `{{base_url}}` variable defaults to `http://localhost:8000`.

---

## 🧪 Running Tests

```bash
pytest -v
```

Tests run entirely offline — all external API calls are mocked.

---

## 🔧 Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Target chat/group/channel ID |
| `WHATSAPP_ACCESS_TOKEN` | ✅ | — | Meta Graph API access token |
| `WHATSAPP_PHONE_NUMBER_ID` | ✅ | — | Sender phone number ID |
| `WHATSAPP_RECIPIENT_NUMBER` | ✅ | — | Recipient in E.164 format |
| `API_TIMEOUT` | ❌ | `30` | HTTP timeout (seconds) |
| `MAX_RETRIES` | ❌ | `3` | Max retry attempts |
| `LOG_LEVEL` | ❌ | `INFO` | Python log level |

---

## 🏗️ Architecture

```
Client Request
     │
     ▼
┌──────────┐
│  FastAPI  │  ← routes.py (validation, error mapping)
└────┬─────┘
     │
     ├──► telegram.py  ──► Telegram Bot API
     │
     └──► whatsapp.py  ──► Meta Graph API
```

**Key design decisions:**

- **Service layer separation** — `telegram.py` / `whatsapp.py` know nothing about HTTP status codes or FastAPI; `routes.py` maps service errors to HTTP responses.
- **Retry at the service level** — The `@with_retry()` decorator wraps each service function, so retries happen transparently below the route handler.
- **Config validation at startup** — If any credential is missing, the app fails immediately with a clear Pydantic validation error instead of crashing mid-request.

---

## 📜 How to Get API Credentials

### Telegram

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. Send `/newbot` and follow the prompts.
3. Copy the **bot token** → `TELEGRAM_BOT_TOKEN`.
4. Send a message to your bot, then visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
5. Find `chat.id` in the response → `TELEGRAM_CHAT_ID`.

### WhatsApp

1. Go to [Meta for Developers](https://developers.facebook.com/).
2. Create a new app → select **Business** type.
3. Add the **WhatsApp** product.
4. In **API Setup**, copy:
   - **Temporary access token** → `WHATSAPP_ACCESS_TOKEN`
   - **Phone number ID** → `WHATSAPP_PHONE_NUMBER_ID`
5. Add a test recipient number → `WHATSAPP_RECIPIENT_NUMBER`

---

## 📄 License

MIT — use it however you like.
