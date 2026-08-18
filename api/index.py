"""
Vercel Serverless Function Entrypoint
FastAPI 앱을 Vercel 클라우드 환경에서 직접 실행합니다.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

# 상위 및 scripts 경로 추가
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "scripts"))

from notion_client import NotionClient

load_dotenv()

app = FastAPI(
    title="Notion Quick Schedule API",
    description="아이폰 전용 노션 퀵 일정 등록 Vercel 배포 API",
    version="1.0.0"
)

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

    start_val = req.start_date.strip()
    end_val = req.end_date.strip() if req.end_date else None

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
