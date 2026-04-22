# Critical Section Simulator
### Lamport's Bakery Algorithm — FastAPI + WebSocket + Vanilla JS

A real-time simulator for the Critical Section Problem (N processes) with a terminal-style UI.

---

## Project Structure

```
critical-section/
├── main.py              ← FastAPI backend (Bakery Algorithm + WebSocket)
├── requirements.txt     ← Python dependencies
├── static/
│   └── index.html       ← Frontend (HTML/CSS/JS)
└── README.md
```

---

## Quick Start

### 1. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open your browser
```
http://localhost:8000
```

---

## Deploy to the Web (free options)

### Render.com
1. Push this folder to a GitHub repo.
2. Go to https://render.com → New → Web Service.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Done — live URL provided instantly.

### Railway.app
1. Push to GitHub, connect Railway, set start command above.

### Fly.io
```bash
fly launch
fly deploy
```

---

## How It Works

### Lamport's Bakery Algorithm (backend — main.py)

```
ENTRY PROTOCOL for process i:
  1. choosing[i] = True
  2. ticket[i]   = max(all tickets) + 1
  3. choosing[i] = False
  4. For every other process j:
       wait while choosing[j]
       wait while (ticket[j] < ticket[i])
            OR  (ticket[j] == ticket[i] AND j < i)
  → Process i enters Critical Section

EXIT PROTOCOL:
  ticket[i] = 0
```

**Guarantees:**
- ✅ Mutual Exclusion — only one process in CS at a time
- ✅ Progress — if CS is free, a waiting process will enter
- ✅ Bounded Waiting — max wait = N−1 turns (no starvation)

### WebSocket API

| Client → Server | Description |
|---|---|
| `{"cmd":"start"}` | Begin simulation |
| `{"cmd":"pause"}` | Pause simulation |
| `{"cmd":"reset","n":4}` | Reset with N processes |
| `{"cmd":"set_n","n":5}` | Change process count |
| `{"cmd":"set_speed","speed":3}` | Set simulation speed |

| Server → Client | Description |
|---|---|
| `{"type":"state", ...}` | Full state snapshot every tick |

---

## API Docs

FastAPI auto-generates docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc:       `http://localhost:8000/redoc`
