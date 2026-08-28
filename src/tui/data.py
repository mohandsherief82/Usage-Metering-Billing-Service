import os
import random

import time

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from enum import Enum

import httpx

API_BASE_URL = os.environ.get("BILLING_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 1.5
RETRY_LIVE_EVERY = 15.0


class SourceMode(str, Enum):
    LIVE = "LIVE"
    DEMO = "DEMO"
    CONNECTING = "CONNECTING"


@dataclass
class UsageEvent:
    id: str
    tenant_id: str
    event_type: str
    quantity: int
    created_at: datetime


@dataclass
class TenantUsage:
    tenant_id: str
    tenant_name: str
    plan_name: str
    status: str  # active | past_due | canceled
    used: int
    limit: int
    cost_cents: int
    history: list[int] = field(default_factory=list)

    @property
    def pct(self) -> float:
        if self.limit <= 0:
            return 0.0

        return min(self.used / self.limit, 1.5)


class ApiClient:
    def __init__(self, base_url: str = API_BASE_URL) -> None:
        self._base_url = base_url

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                r = await client.get(f"{self._base_url}/health")

                return r.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def list_tenants_usage(self) -> list[TenantUsage]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"{self._base_url}/usage")
            r.raise_for_status()
   
            payload = r.json()

        return [
            TenantUsage(
                tenant_id=t["tenant_id"],
                tenant_name=t["tenant_name"],

                plan_name=t["plan_name"],
                status=t["status"],

                used=t["used"],
                limit=t["limit"],

                cost_cents=t["cost_cents"],
                history=t.get("history", []),
            )

            for t in payload
        ]

    async def recent_events(self, limit: int = 50) -> list[UsageEvent]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"{self._base_url}/usage/events", params={"limit": limit})
            r.raise_for_status()

            payload = r.json()

        return [
            UsageEvent(
                id=e["id"],
  
                tenant_id=e["tenant_id"],
                event_type=e["event_type"],
     
	            quantity=e["quantity"],
                created_at=datetime.fromisoformat(e["created_at"]),
            )
           
		    for e in payload
        ]


class DemoDataSource:
    """
    	Self-contained mock data — no network, no backend.
    """

    _PLANS = {
        "free": 1_000,
        "starter": 25_000,
        "pro": 250_000,
        "scale": 2_000_000,
    }

    _EVENT_TYPES = ["input_tokens", "cached_input_tokens", "reasoning_tokens", "output_tokens", "api_call"]

    def __init__(self) -> None:
        self._rng = random.Random(42)

        self._tenants: dict[str, TenantUsage] = {
            "acme": TenantUsage("acme", "Acme Robotics", "scale", "active", 1_240_000, 2_000_000, 184_302, []),
            "nile-labs": TenantUsage("nile-labs", "Nile Labs", "pro", "active", 238_900, 250_000, 41_205, []),
            "kite": TenantUsage("kite", "Kite Analytics", "starter", "active", 24_100, 25_000, 6_980, []),
            "sandbox-co": TenantUsage("sandbox-co", "Sandbox & Co", "free", "past_due", 980, 1_000, 210, []),
            "orbit": TenantUsage("orbit", "Orbit Systems", "pro", "active", 91_400, 250_000, 15_760, []),
        }

        for t in self._tenants.values():
            t.history = [max(0, t.used - self._rng.randint(0, t.limit // 12) * i) for i in range(11, -1, -1)]

        self._events: list[UsageEvent] = []
        self._seed_events()

    def _seed_events(self) -> None:
        now = datetime.now(timezone.utc)

        for i in range(30):
            tid = self._rng.choice(list(self._tenants))

            self._events.append(
                UsageEvent(
                    id=f"evt_seed_{i}",

                    tenant_id=tid,
                    event_type=self._rng.choice(self._EVENT_TYPES),

                    quantity=self._rng.randint(1, 4000),
                    created_at=now - timedelta(seconds=(30 - i) * 7),
                )
            )

    def _tick(self) -> None:
        for t in self._tenants.values():
            if t.status == "past_due":
                continue

            step = self._rng.randint(0, max(1, t.limit // 400))

            t.used = min(int(t.limit * 1.2), t.used + step)
            t.cost_cents += step * self._rng.randint(1, 3)

            t.history.append(t.used)
            t.history = t.history[-12:]

            if step > 0:
                self._events.append(
                    UsageEvent(
                        id=f"evt_{int(time.time() * 1000)}_{t.tenant_id}",

                        tenant_id=t.tenant_id,
                        event_type=self._rng.choice(self._EVENT_TYPES),

                        quantity=step,
                        created_at=datetime.now(timezone.utc),
                    )
                )

        self._events = self._events[-200:]

    async def list_tenants_usage(self) -> list[TenantUsage]:
        self._tick()

        return list(self._tenants.values())

    async def recent_events(self, limit: int = 50) -> list[UsageEvent]:
        return sorted(self._events, key=lambda e: e.created_at, reverse=True)[:limit]


class BillingDataSource:
    """
    Facade the TUI actually depends on. Owns the LIVE/DEMO decision and the
    background reconnect-retry, so screens never need to know which one is
    backing them.
    """

    def __init__(self) -> None:
        self._api = ApiClient()
        self._demo = DemoDataSource()

        self.mode: SourceMode = SourceMode.CONNECTING
        self._last_live_check = 0.0

    async def _maybe_check_live(self) -> None:
        now = time.monotonic()

        if self.mode == SourceMode.LIVE:
            return
        if now - self._last_live_check < RETRY_LIVE_EVERY:
            return

        self._last_live_check = now

        alive = await self._api.ping()

        self.mode = SourceMode.LIVE if alive else SourceMode.DEMO

    async def list_tenants_usage(self) -> list[TenantUsage]:
        await self._maybe_check_live()

        if self.mode == SourceMode.LIVE:
            try:
                return await self._api.list_tenants_usage()
            except (httpx.HTTPError, OSError):
                self.mode = SourceMode.DEMO

        return await self._demo.list_tenants_usage()

    async def recent_events(self, limit: int = 50) -> list[UsageEvent]:
        if self.mode == SourceMode.LIVE:
            try:
                return await self._api.recent_events(limit=limit)
            except (httpx.HTTPError, OSError):
                self.mode = SourceMode.DEMO

        return await self._demo.recent_events(limit=limit)
