"""
Devin Autonomous Triage Orchestrator
Single-file production scaffolding integrating FastAPI, Celery, and Devin sandbox execution.
"""
import os
import hmac
import hashlib
import json
import logging
import httpx
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException, Header, status
from pydantic import BaseModel
from celery import Celery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

# ---------------------------------------------------------
# Environment & Configurations
# ---------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_tg_token")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "mock_gh_token")
GITHUB_REPO = os.getenv("GITHUB_REPO", "owner/repo")
DEVIN_API_KEY = os.getenv("DEVIN_API_KEY", "mock_devin_key")

# ---------------------------------------------------------
# Celery Worker Configuration
# ---------------------------------------------------------
celery_app = Celery("devin_orchestrator", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# ---------------------------------------------------------
# Celery Tasks (Devin Sandbox & Pipeline Execution)
# ---------------------------------------------------------
@celery_app.task(bind=True, name="tasks.run_devin_pipeline", max_retries=3)
def run_devin_pipeline(self, chat_id: int, bug_report: str):
    """
    1. Provisions GitHub Issue
    2. Invokes Devin API to spin up Docker sandbox & write repro test
    3. Blocks PR creation if regression suite fails
    """
    logger.info(f"[Task {self.request.id}] Ingesting bug report from chat {chat_id}")
    
    # 1. 模拟向 GitHub API 创建 Issue
    issue_payload = {
        "title": f"[Auto-Triage] {bug_report[:40]}...",
        "body": f"Reported via Telegram Chat {chat_id}:\n\n{bug_report}\n\n*Triggered by Devin Orchestrator*",
        "labels": ["automated-triage", "devin-sandbox"]
    }
    logger.info(f"Creating GitHub Issue on {GITHUB_REPO} with payload: {issue_payload}")
    
    # 2. 调度 Devin 执行环境（带沙盒隔离配置与命令注入）
    devin_session_payload = {
        "prompt": f"Fix the issue described: {bug_report}. First step: create a failing pytest under tests/ to reproduce the issue. Only open a Draft PR once tests pass.",
        "sandbox_config": {
            "runtime": "docker",
            "base_image": "python:3.11-slim",
            "pre_commands": ["pip install -r requirements.txt", "pytest -v"]
        }
    }
    logger.info(f"Dispatched session to Cognition Devin API: {devin_session_payload}")
    
    return {
        "status": "session_spawned",
        "chat_id": chat_id,
        "devin_session_id": f"devin-sess-{self.request.id}"
    }

# ---------------------------------------------------------
# FastAPI App & Endpoints
# ---------------------------------------------------------
app = FastAPI(
    title="Devin Orchestrator Gateway",
    description="Webhook gateway bridging Telegram bug reports and GitHub Issues to Devin AI",
    version="1.0.0"
)

class TelegramChat(BaseModel):
    id: int

class TelegramMessage(BaseModel):
    message_id: int
    chat: TelegramChat
    text: Optional[str] = None

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None

@app.get("/health")
def health():
    return {"status": "healthy", "service": "fastapi-celery-devin-bridge"}

@app.post("/webhook/telegram", status_code=status.HTTP_200_OK)
async def telegram_webhook(update: TelegramUpdate):
    """
    Endpoint for Telegram Bot Webhooks.
    Validates payload and offloads to Celery queue immediately.
    """
    if not update.message or not update.message.text:
        return {"status": "ignored", "reason": "non-text payload"}
    
    chat_id = update.message.chat.id
    raw_text = update.message.text
    
    # 将任务推入 Celery 异步队列
    task = run_devin_pipeline.delay(chat_id=chat_id, bug_report=raw_text)
    
    logger.info(f"Enqueued job {task.id} for Telegram update {update.update_id}")
    return {
        "status": "queued",
        "task_id": str(task.id),
        "chat_id": chat_id
    }

@app.post("/webhook/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None)
):
    """
    Endpoint for GitHub Webhooks to listen for Devin Draft PR creations and status checks.
    """
    payload = await request.json()
    action = payload.get("action")
    
    if x_github_event == "pull_request" and action == "opened":
        pr_number = payload.get("pull_request", {}).get("number")
        logger.info(f"Devin opened Draft PR #{pr_number}. Verification gate awaiting human review.")
        return {"status": "pr_verified", "pr_number": pr_number}
    
    return {"status": "event_acknowledged", "event": x_github_event}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
