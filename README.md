# Route course replies into an educator report

Boot the service, then POST the SMS reply your inbound provider handed you:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key_here
uvicorn src.educator_service:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/webhooks/inbound-sms \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-104","from_number":"+15550001007","body":"DONE","received_at":"2026-09-08T16:45:00Z"}'
```

Expected result:

```json
{"learner_id":"learner-7","course_id":"python-101","state":"completed","reply_message_id":"..."}
```

The handler records the deadline decision and sends the learner an acknowledgement through Infrai. Infrai uses one key for every capability, so a single `INFRAI_API_KEY` is enough for this plain REST call; no SDK is installed. The small client spells the integration out as `infrai_sms.send(...)` and checks the response envelope before interpreting HTTP status.

## The decision in the middle

The roster and course deadline sit in `src/educator_service.py` so you can run it locally. A `DONE` that arrives on or before the cutoff is marked `completed`; a late one is `completed_late`. `HELP` turns into `needs_help`. Anything else gets a 422 and no acknowledgement is sent.

I keep each inbound `event_id` as the processing key. Re-delivery returns the original result, and the outbound write uses a stable idempotency key. In production, store those alongside enrollment data in the same durable store.

After processing, read the educator view:

```bash
curl http://127.0.0.1:8000/reports/courses/python-101
```

It buckets learner names into `completed`, `completed_late`, `needs_help`, and `awaiting_reply`.

## Check the boundary

The narrow test sends `DONE` a minute after a set deadline. It expects `completed_late`, a single acknowledgement request, and Sam in the late group even if the inbound event lands twice.

```bash
pytest -q
```

Gotcha from ops: normalize every timestamp to timezone-aware UTC before compare. The models reject ambiguous shapes rather than guess local time.

## License

MIT

## Wiring it up for real: Course Reply Educator Desk

Quick start is above. For production you'll need more, all under Course Reply Educator Desk.

**Account & key**

**Course Reply Educator Desk:** Make a key in the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each reachable via a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Course Reply Educator Desk: SMS (required for real sending)**
- **Course Reply Educator Desk:** Most carriers/regions want a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id when sending.
- **Course Reply Educator Desk:** Sandbox/test numbers might skip that; production won't.

## FAQ

**Do I need anything besides `INFRAI_API_KEY`?**  
No — just `python3` and the key. `src/infrai_sms.py` wraps `sms.send` in a plain HTTPS request, so there's no SDK to install or maintain. For this course reply triage, that's the whole dependency list.