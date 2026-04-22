from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncio
import json
import random

app = FastAPI(title="Critical Section Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ─── Lamport's Bakery Algorithm (pure Python) ───────────────────────────────

class BakerySimulator:
    def __init__(self, n: int = 4):
        self.n = n
        self.reset()

    def reset(self, n: int = None):
        if n:
            self.n = n
        self.choosing   = [False] * self.n
        self.ticket     = [0]     * self.n
        self.in_cs      = -1
        self.p_state    = ["idle"] * self.n   # idle | choosing | waiting | running | leaving
        self.p_timer    = [0]     * self.n
        self.p_idle_timer = [random.randint(4, 12) for _ in range(self.n)]
        self.p_cs_count = [0]     * self.n
        self.ticks      = 0
        self.entries    = 0
        self.violations = 0
        self.log        = []

    def _add_log(self, msg: str, kind: str = "info"):
        self.log.append({"tick": self.ticks, "msg": msg, "kind": kind})
        if len(self.log) > 80:
            self.log.pop(0)

    def step(self):
        self.ticks += 1
        for i in range(self.n):
            state = self.p_state[i]

            if state == "idle":
                self.p_idle_timer[i] -= 1
                if self.p_idle_timer[i] <= 0:
                    self.p_state[i]  = "choosing"
                    self.p_timer[i]  = 2
                    self.choosing[i] = True

            elif state == "choosing":
                self.p_timer[i] -= 1
                if self.p_timer[i] <= 0:
                    # Bakery: ticket = max of all tickets + 1
                    self.ticket[i]   = max(self.ticket) + 1
                    self.choosing[i] = False
                    self.p_state[i]  = "waiting"
                    self._add_log(f"P{i} takes ticket #{self.ticket[i]}", "wait")

            elif state == "waiting":
                # Entry protocol check
                can_enter = True
                for j in range(self.n):
                    if j == i:
                        continue
                    if self.choosing[j]:
                        can_enter = False
                        break
                    if self.ticket[j] != 0 and (
                        self.ticket[j] < self.ticket[i] or
                        (self.ticket[j] == self.ticket[i] and j < i)
                    ):
                        can_enter = False
                        break

                if can_enter:
                    if self.in_cs >= 0:
                        self.violations += 1
                        self._add_log(f"VIOLATION! P{i} entered while P{self.in_cs} in CS", "wait")
                    self.p_state[i]    = "running"
                    self.p_timer[i]    = random.randint(6, 12)
                    self.in_cs         = i
                    self.entries      += 1
                    self.p_cs_count[i] += 1
                    self._add_log(f"P{i} ENTERS critical section (ticket #{self.ticket[i]})", "enter")

            elif state == "running":
                self.p_timer[i] -= 1
                if self.p_timer[i] <= 0:
                    self.p_state[i] = "leaving"
                    self.p_timer[i] = 1
                    self._add_log(f"P{i} EXITS critical section", "exit")

            elif state == "leaving":
                self.p_timer[i] -= 1
                if self.p_timer[i] <= 0:
                    self.ticket[i]    = 0
                    self.in_cs        = -1
                    self.p_state[i]   = "idle"
                    self.p_idle_timer[i] = random.randint(4, 14)

    def get_state(self) -> dict:
        return {
            "choosing":   self.choosing,
            "ticket":     self.ticket,
            "in_cs":      self.in_cs,
            "p_state":    self.p_state,
            "p_timer":    self.p_timer,
            "p_cs_count": self.p_cs_count,
            "ticks":      self.ticks,
            "entries":    self.entries,
            "violations": self.violations,
            "log":        self.log[-10:],
            "n":          self.n,
        }


sim = BakerySimulator(n=4)


# ─── WebSocket endpoint ──────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    running = False
    speed   = 3           # steps per second multiplier

    async def send_state():
        await ws.send_text(json.dumps({"type": "state", **sim.get_state()}))

    await send_state()

    try:
        while True:
            # Non-blocking receive with timeout
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=0.05)
                msg = json.loads(raw)
                cmd = msg.get("cmd")

                if cmd == "start":
                    running = True
                elif cmd == "pause":
                    running = False
                elif cmd == "reset":
                    running = False
                    sim.reset(msg.get("n", sim.n))
                    await send_state()
                elif cmd == "set_n":
                    running = False
                    sim.reset(int(msg["n"]))
                    await send_state()
                elif cmd == "set_speed":
                    speed = int(msg["speed"])
            except asyncio.TimeoutError:
                pass

            if running:
                steps = max(1, speed)
                for _ in range(steps):
                    sim.step()
                await send_state()
                await asyncio.sleep(0.25)

    except WebSocketDisconnect:
        pass
