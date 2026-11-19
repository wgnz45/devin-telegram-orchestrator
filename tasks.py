import os
import httpx
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

celery_app = Celery("orchestrator_tasks", broker=REDIS_URL, backend=REDIS_URL)

@celery_app.task(name="tasks.dispatch_devin_reproduction")
def dispatch_devin_reproduction(chat_id: int, issue_title: str, issue_body: str):
    """
    Executes in background:
    1. Simulates GitHub Issue creation
    2. Dispatches Devin session in an isolated Docker sandbox
    3. Triggers reproduction test run before generating PR
    """
    print(f"[Celery] Processing triage from chat {chat_id}: {issue_title}")
    
    # 模拟沙盒与 Devin 任务调度
    sandbox_config = {
        "image": "python:3.11-slim",
        "workdir": "/workspace",
        "entrypoint": "pytest tests/reproduce_issue.py",
        "isolated": True
    }
    
    # 模拟向 Devin Session 发送触发请求
    print(f"[Devin Bridge] Environment provisioned: {sandbox_config}")
    return {
        "status": "in_progress",
        "chat_id": chat_id,
        "devin_session_id": "devin-live-sess-48h-mvp"
    }
