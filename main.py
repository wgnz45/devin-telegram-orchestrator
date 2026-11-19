import os
import hmac
import hashlib
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException, status
from pydantic import BaseModel
from tasks import dispatch_devin_reproduction

app = FastAPI(title="Devin Telegram-GitHub Orchestrator API")

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "mock_secret")

class TelegramPayload(BaseModel):
    update_id: int
    message: dict | None = None

@app.get("/")
def health_check():
    return {"status": "ok", "service": "devin-orchestrator"}

@app.post("/webhook/telegram")
async def telegram_webhook(payload: TelegramPayload, background_tasks: BackgroundTasks):
    if not payload.message or "text" not in payload.message:
        return {"status": "ignored", "reason": "no text payload"}
    
    chat_id = payload.message["chat"]["id"]
    text = payload.message["text"]
    
    # 将任务异步交由 Celery 队列处理，实现非阻塞
    dispatch_devin_reproduction.delay(
        chat_id=chat_id,
        issue_title="Telegram Bug Report",
        issue_body=text
    )
    
    return {"status": "queued", "chat_id": chat_id}

@app.post("/webhook/github")
async def github_webhook(request: Request):
    event = request.headers.get("X-GitHub-Event")
    payload = await request.json()
    
    if event == "pull_request" and payload.get("action") == "opened":
        # 监听 Devin 提交的 Draft PR 并广播状态
        return {"status": "pr_registered_awaiting_review"}
    
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
