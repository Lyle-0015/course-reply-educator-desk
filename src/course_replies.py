from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ReplyState(str, Enum):
    completed = "completed"
    completed_late = "completed_late"
    needs_help = "needs_help"


class Course(BaseModel):
    course_id: str
    title: str
    deadline: datetime

    @field_validator("deadline")
    @classmethod
    def deadline_needs_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("deadline must include a timezone")
        return value


class Learner(BaseModel):
    learner_id: str
    name: str
    phone: str
    course_id: str


class InboundSms(BaseModel):
    event_id: str = Field(min_length=1)
    from_number: str = Field(min_length=5)
    body: str = Field(min_length=1, max_length=320)
    received_at: datetime

    @field_validator("received_at")
    @classmethod
    def received_at_needs_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("received_at must include a timezone")
        return value


class ReplyResult(BaseModel):
    learner_id: str
    course_id: str
    state: ReplyState
    reply_message_id: str


class CourseReport(BaseModel):
    course_id: str
    completed: list[str]
    completed_late: list[str]
    needs_help: list[str]
    awaiting_reply: list[str]


class CourseReplyWorkflow:
    def __init__(self, courses: list[Course], learners: list[Learner], sms: Any) -> None:
        self.courses = {course.course_id: course for course in courses}
        self.learners = {learner.phone: learner for learner in learners}
        self.sms = sms
        self.states: dict[str, ReplyState] = {}
        self.results: dict[str, ReplyResult] = {}

    async def handle(self, inbound: InboundSms) -> ReplyResult:
        if inbound.event_id in self.results:
            return self.results[inbound.event_id]

        learner = self.learners.get(inbound.from_number)
        if learner is None:
            raise ValueError("phone number is not on the course roster")
        course = self.courses[learner.course_id]
        received_at = inbound.received_at.astimezone(timezone.utc)
        deadline = course.deadline.astimezone(timezone.utc)

        normalized = inbound.body.strip().upper()
        if normalized == "DONE":
            state = ReplyState.completed if received_at <= deadline else ReplyState.completed_late
            reply = (
                f"Recorded: {course.title} is complete."
                if state == ReplyState.completed
                else f"Recorded after the deadline: {course.title}. Your educator can review it."
            )
        elif normalized == "HELP":
            state = ReplyState.needs_help
            reply = f"Your help request for {course.title} is with your educator."
        else:
            raise ValueError("reply must be DONE or HELP")

        delivery = await self.sms.send(
            to=learner.phone,
            body=reply,
            idempotency_key=f"course-reply-{inbound.event_id}",
        )
        result = ReplyResult(
            learner_id=learner.learner_id,
            course_id=course.course_id,
            state=state,
            reply_message_id=str(delivery["message_id"]),
        )
        self.states[learner.learner_id] = state
        self.results[inbound.event_id] = result
        return result

    def report(self, course_id: str) -> CourseReport:
        if course_id not in self.courses:
            raise KeyError(course_id)
        roster = [item for item in self.learners.values() if item.course_id == course_id]
        grouped = {state: [] for state in ReplyState}
        awaiting: list[str] = []
        for learner in roster:
            state = self.states.get(learner.learner_id)
            (grouped[state] if state else awaiting).append(learner.name)
        return CourseReport(
            course_id=course_id,
            completed=grouped[ReplyState.completed],
            completed_late=grouped[ReplyState.completed_late],
            needs_help=grouped[ReplyState.needs_help],
            awaiting_reply=awaiting,
        )
