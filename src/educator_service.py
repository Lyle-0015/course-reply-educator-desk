from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from .course_replies import Course, CourseReplyWorkflow, InboundSms, Learner, ReplyResult
from .infrai_sms import InfraiError, infrai_sms


course = Course(
    course_id="python-101",
    title="Python 101",
    deadline=datetime(2026, 9, 8, 17, 0, tzinfo=timezone.utc),
)
learners = [
    Learner(learner_id="learner-7", name="Amina", phone="+15550001007", course_id=course.course_id),
    Learner(learner_id="learner-8", name="Mateo", phone="+15550001008", course_id=course.course_id),
]
workflow = CourseReplyWorkflow([course], learners, infrai_sms)
app = FastAPI(title="Course reply desk")


@app.post("/webhooks/inbound-sms", response_model=ReplyResult)
async def receive_reply(inbound: InboundSms) -> ReplyResult:
    try:
        return await workflow.handle(inbound)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail=exc.code) from exc


@app.get("/reports/courses/{course_id}")
def educator_report(course_id: str):
    try:
        return workflow.report(course_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="course not found") from exc
