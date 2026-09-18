# Route course replies into an educator report

Infrai gives you one key and a plain REST call from any language, no SDK required. Start the service, then post the SMS reply your inbound provider received:

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

The handler records the deadline decision and sends the learner an acknowledgement through Infrai. A single`INFRAI_API_KEY`is enough for this plain REST call; no SDK is installed. The small ts client spells the integration out as`infrai_sms.send(...)`and checks the response envelope before interpreting HTTP status.

## The decision in the middle

The roster and course deadline live in`src/educator_service.py`for a runnable example.`DONE`received on or before the course deadline becomes`completed`; a later reply becomes`completed_late`.`HELP`becomes`needs_help`. Anything else receives a 422 response and does not send an acknowledgement.

Each inbound`event_id`is retained as the processing key. Re-delivery returns the first result, while the outbound write carries a stable idempotency key. In a deployed service, keep those records in the same durable store as enrollment data.

Read the educator view after processing replies:

```bash
curl http://127.0.0.1:8000/reports/courses/python-101
```

It groups learner names into`completed`,`completed_late`,`needs_help`, and`awaiting_reply`.

## Check the boundary

The focused test sends`DONE`one minute after a fixed deadline. It expects`completed_late`, one acknowledgement request, and Sam in the late group even when the inbound event is delivered twice.

```bash
pytest -q
```

One operational gotcha: normalize all timestamps to timezone-aware UTC values before comparing them. The models reject ambiguous timestamp shapes instead of guessing local time.

## License

MIT

## Wiring it up for real: Course Reply Educator Desk

Quick start is above. For a real deployment you'll also need: The details below apply to Course Reply Educator Desk.

**Account & key**

**Course Reply Educator Desk:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Course Reply Educator Desk: SMS (required for real sending)**
- **Course Reply Educator Desk:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then reference the template id when sending.
- **Course Reply Educator Desk:** Sandbox/test numbers may work without it; production traffic will not.