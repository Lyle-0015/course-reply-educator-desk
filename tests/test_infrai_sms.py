import httpx
import pytest

from src.infrai_sms import InfraiError, InfraiSms


@pytest.mark.asyncio
async def test_client_reads_business_error_envelope_before_http_status() -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(
            400,
            json={"ok": False, "data": None, "error": {"code": "recipient"}, "metadata": {}},
        )

    client = InfraiSms(api_key="test-key", transport=httpx.MockTransport(reject))

    with pytest.raises(InfraiError) as caught:
        await client.send(to="+15550001111", body="Recorded.", idempotency_key="reply-1")

    assert caught.value.code == "recipient"
    assert caught.value.status_code == 400
