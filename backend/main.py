import os
import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

load_dotenv()

from backend.pipeline import run_pipeline
from backend.scraper import get_douyin_feed_by_category

app = FastAPI(
    title="Douyin Scraper & Translator API",
    description="Full-stack API cào video Douyin, dịch tiếng Việt, lồng tiếng và phát SSE realtime.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lưu trữ queue các sự kiện tiến trình theo task_id
task_queues: Dict[str, asyncio.Queue] = {}
task_states: Dict[str, Dict[str, Any]] = {}

class TranslateRequest(BaseModel):
    douyin_url: str
    target_voice: Optional[str] = None

@app.get("/api/feed")
async def get_feed(category: str = Query("food", description="Thể loại: food (Ẩm thực) hoặc funny (Hài hước)")):
    """Lấy danh sách 10-15 video Douyin theo thể loại."""
    try:
        videos = get_douyin_feed_by_category(category=category, limit=15)
        return {
            "category": category,
            "count": len(videos),
            "videos": videos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải feed video: {str(e)}")

@app.post("/api/translate")
async def start_translate(req: TranslateRequest, background_tasks: BackgroundTasks):
    if not req.douyin_url or not req.douyin_url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp link Douyin.")

    target_voice = req.target_voice or os.getenv("TARGET_VOICE", "vi-VN-HoaiMyNeural")
    task_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()
    task_queues[task_id] = queue
    task_states[task_id] = {
        "task_id": task_id,
        "percent": 0,
        "step": "Đang khởi động task...",
        "status": "pending",
        "data": None
    }

    async def report_progress(step: str, percent: int, data: dict = None):
        state = {
            "task_id": task_id,
            "step": step,
            "percent": percent,
            "status": "completed" if percent == 100 else "processing",
            "data": data
        }
        task_states[task_id] = state
        await queue.put(state)

    async def task_runner():
        try:
            await run_pipeline(task_id, req.douyin_url, target_voice, report_progress)
        except Exception as e:
            err_state = {
                "task_id": task_id,
                "step": f"Lỗi: {str(e)}",
                "percent": task_states.get(task_id, {}).get("percent", 0),
                "status": "failed",
                "error": str(e)
            }
            task_states[task_id] = err_state
            await queue.put(err_state)

    background_tasks.add_task(task_runner)
    return {"task_id": task_id, "message": "Task đã được tạo thành công.", "target_voice": target_voice}

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id not in task_queues:
        if task_id in task_states:
            async def single_event():
                yield {"data": json.dumps(task_states[task_id], ensure_ascii=False)}
            return EventSourceResponse(single_event())
        raise HTTPException(status_code=404, detail="Task không tồn tại.")

    queue = task_queues[task_id]

    async def event_generator():
        current_state = task_states.get(task_id)
        if current_state:
            yield {"data": json.dumps(current_state, ensure_ascii=False)}

        while True:
            try:
                state = await asyncio.wait_for(queue.get(), timeout=60.0)
                yield {"data": json.dumps(state, ensure_ascii=False)}
                if state.get("status") in ["completed", "failed"]:
                    break
            except asyncio.TimeoutError:
                yield {"comment": "keep-alive"}

    return EventSourceResponse(event_generator())

@app.get("/api/video/{task_id}")
async def get_video(task_id: str):
    video_path = Path("workspace/tasks") / task_id / "output_vi.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video thành phẩm không tồn tại hoặc chưa hoàn thành.")
    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=f"douyin_translated_{task_id}.mp4"
    )

# Static files cho frontend
frontend_dir = Path("frontend")
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
