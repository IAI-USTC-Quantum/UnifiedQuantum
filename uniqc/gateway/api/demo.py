"""Local-only demonstration API; it does not create backend tasks."""

from fastapi import APIRouter

from uniqc.gateway.demo import DemoRequest, run_demo

router = APIRouter()


@router.post("/simulate")
def simulate(request: DemoRequest):
    return run_demo(request)
