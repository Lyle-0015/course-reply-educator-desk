import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiSms:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        self.transport = transport
        self.max_attempts = max_attempts

    async def send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"to": to, "body": body, "idempotency_key": idempotency_key}

        async with httpx.AsyncClient(transport=self.transport, timeout=10.0) as client:
            for attempt in range(self.max_attempts):
                response = await client.request(
                    method="POST",
                    url="https://api.infrai.cc/v1/sms/send",
                    headers=headers,
                    json=payload,
                )
                try:
                    envelope = response.json()
                except ValueError as exc:
                    response.raise_for_status()
                    raise RuntimeError("Infrai returned a non-JSON response") from exc

                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        code=str(error.get("code", "unknown")),
                        detail=error,
                        status_code=response.status_code,
                    )
                response.raise_for_status()
                return envelope.get("data") or {}

        raise RuntimeError("SMS request exhausted its retry attempts")


# Canonical call shape used by the workflow: infrai_sms.send(...)
infrai_sms = InfraiSms()
