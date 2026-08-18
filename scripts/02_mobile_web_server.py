"""
모바일 퀵 일정 등록 웹앱 백엔드 서버 (FastAPI)
아이폰에서 접속 가능한 웹 인터페이스 제공 및 노션 API 연동 처리
"""

import os
import sys
import socket
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from notion_client import NotionClient

load_dotenv()

app = FastAPI(
    title="Notion Quick Schedule Mobile Server",
    description="아이폰 전용 노션 퀵 일정 등록 웹앱 백엔드 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

notion = NotionClient()

class ScheduleRequest(BaseModel):
    title: str = Field(..., description="일정 제목")
    category: str = Field(..., description="5대 분류")
    is_all_day: bool = Field(True, description="종일 일정 여부")
    start_date: str = Field(..., description="시작 일시")
    end_date: Optional[str] = Field(None, description="종료 일시")
    memo: Optional[str] = Field(None, description="상세 메모")

@app.get("/api/health")
async def check_health():
    """서버 상태 및 노션 API 연동 여부 확인"""
    connection_status = notion.verify_connection()
    return {
        "status": "online",
        "notion_configured": bool(notion.token),
        "notion_status": connection_status
    }

@app.post("/api/schedule")
async def create_schedule(req: ScheduleRequest):
    """모바일에서 전송된 일정을 노션 todolist 2 DB에 등록"""
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="일정 제목을 입력해주세요.")

    # 날짜 포맷 정리 (종일 일정 vs 시간 포함 일정)
    start_val = req.start_date.strip()
    end_val = req.end_date.strip() if req.end_date else None

    # 시간 포함 일정인 경우 ISO 포맷 타임존(+09:00) 보정
    if not req.is_all_day:
        if "T" in start_val and len(start_val) == 16:
            start_val = f"{start_val}:00+09:00"
        if end_val and "T" in end_val and len(end_val) == 16:
            end_val = f"{end_val}:00+09:00"

    result = notion.create_schedule_item(
        title=req.title.strip(),
        category=req.category,
        start_date=start_val,
        end_date=end_val,
        memo=req.memo
    )

    if result.get("success"):
        return JSONResponse(status_code=200, content=result)
    else:
        return JSONResponse(status_code=400, content=result)

# 프론트엔드 정적 파일 서빙
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "web/index.html 파일을 찾을 수 없습니다."}

def get_local_ip() -> str:
    """로컬 네트워크 Wi Fi IP 주소 획득"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    print("=" * 60)
    print("🚀 Notion Quick Schedule 모바일 웹앱 서버 실행")
    print(f"📱 아이폰(동일 Wi Fi) 접속 주소: http://{local_ip}:{port}")
    print(f"💻 로컬 PC 브라우저 접속 주소:   http://localhost:{port}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)
