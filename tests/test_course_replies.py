from datetime import datetime, timezone

import pytest

from src.course_replies import Course, CourseReplyWorkflow, InboundSms, Learner, ReplyState


class RecordingSms:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def send(self, *, to: str, body: str, idempotency_key: str) -> dict:
        self.calls.append({"to": to, "body": body, "idempotency_key": idempotency_key})
        return {"message_id": "sms-test-42"}


@pytest.mark.asyncio
async def test_done_after_deadline_is_reported_late_and_acknowledged_once() -> None:
    sms = RecordingSms()
    workflow = CourseReplyWorkflow(
        courses=[
            Course(
                course_id="algebra",
                title="Algebra Foundations",
                deadline=datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
            )
        ],
        learners=[
            Learner(learner_id="l-1", name="Sam", phone="+15550001111", course_id="algebra")
        ],
        sms=sms,
    )
    inbound = InboundSms(
        event_id="evt-9",
        from_number="+15550001111",
        body=" done ",
        received_at=datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
    )

    first = await workflow.handle(inbound)
    second = await workflow.handle(inbound)

    assert first.state == ReplyState.completed_late
    assert second == first
    assert sms.calls == [
        {
            "to": "+15550001111",
            "body": "Recorded after the deadline: Algebra Foundations. Your educator can review it.",
            "idempotency_key": "course-reply-evt-9",
        }
    ]
    assert workflow.report("algebra").completed_late == ["Sam"]

