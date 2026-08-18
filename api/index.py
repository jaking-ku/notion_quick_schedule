"""
Vercel Serverless Function API Entrypoint
Notion API 클라이언트가 통합된 독립형 백엔드 엔드포인트
"""

import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

app = FastAPI(
    title="Notion Quick Schedule API",
    description="아이폰 전용 노션 퀵 일정 등록 Vercel Serverless API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_DATABASE_ID = "0fbc41b344c08355a22701537a4715b2"
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def get_notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

def get_database_id() -> str:
    raw_id = os.getenv("NOTION_DATABASE_ID", DEFAULT_DATABASE_ID).strip()
    return raw_id.replace("_", "").replace("-", "")

def get_token() -> str:
    return os.getenv("NOTION_TOKEN", "").strip()

def find_memo_prop_name(token: str, db_id: str) -> str:
    try:
        url = f"{NOTION_API_URL}/databases/{db_id}"
        res = requests.get(url, headers=get_notion_headers(token), timeout=5)
        if res.status_code == 200:
            props = res.json().get("properties", {})
            for name, info in props.items():
                if info.get("type") == "rich_text" and name.strip().startswith("1"):
                    return name
    except Exception:
        pass
    return "1. "

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
    token = get_token()
    db_id = get_database_id()

    if not token:
        return {
            "status": "online",
            "notion_configured": False,
            "notion_status": {"success": False, "error": "NOTION_TOKEN이 설정되지 않았습니다."}
        }

    url = f"{NOTION_API_URL}/databases/{db_id}"
    try:
        response = requests.get(url, headers=get_notion_headers(token), timeout=8)
        if response.status_code == 200:
            data = response.json()
            title_list = data.get("title", [])
            title_text = title_list[0].get("plain_text", "데이터베이스") if title_list else "데이터베이스"
            return {
                "status": "online",
                "notion_configured": True,
                "notion_status": {"success": True, "title": title_text, "id": db_id}
            }
        else:
            return {
                "status": "online",
                "notion_configured": True,
                "notion_status": {"success": False, "status_code": response.status_code, "error": response.text}
            }
    except Exception as e:
        return {
            "status": "online",
            "notion_configured": True,
            "notion_status": {"success": False, "error": str(e)}
        }

@app.post("/api/schedule")
async def create_schedule(req: ScheduleRequest):
    """모바일에서 전송된 일정을 노션 todolist 2 DB에 등록"""
    token = get_token()
    db_id = get_database_id()

    if not token:
        raise HTTPException(status_code=500, detail="NOTION_TOKEN 환경 변수가 설정되지 않았습니다.")

    if not req.title.strip():
        raise HTTPException(status_code=400, detail="일정 제목을 입력해주세요.")

    start_val = req.start_date.strip()
    end_val = req.end_date.strip() if req.end_date else None

    if not req.is_all_day:
        if "T" in start_val and len(start_val) == 16:
            start_val = f"{start_val}:00+09:00"
        if end_val and "T" in end_val and len(end_val) == 16:
            end_val = f"{end_val}:00+09:00"

    date_payload: Dict[str, Any] = {"start": start_val}
    if end_val:
        date_payload["end"] = end_val

    properties: Dict[str, Any] = {
        "이름": {
            "title": [
                {
                    "text": {
                        "content": req.title.strip()
                    }
                }
            ]
        },
        "상태": {
            "select": {
                "name": req.category
            }
        },
        "완료": {
            "checkbox": False
        },
        "마감일": {
            "date": date_payload
        }
    }

    if req.memo and req.memo.strip():
        memo_prop = find_memo_prop_name(token, db_id)
        properties[memo_prop] = {
            "rich_text": [
                {
                    "text": {
                        "content": req.memo.strip()
                    }
                }
            ]
        }

    payload = {
        "parent": {
            "database_id": db_id
        },
        "properties": properties
    }

    try:
        res = requests.post(f"{NOTION_API_URL}/pages", headers=get_notion_headers(token), json=payload, timeout=10)
        if res.status_code in [200, 201]:
            data = res.json()
            return JSONResponse(status_code=200, content={
                "success": True,
                "page_id": data.get("id"),
                "url": data.get("url"),
                "message": "노션에 일정이 정상 등록되었습니다."
            })
        else:
            return JSONResponse(status_code=400, content={
                "success": False,
                "status_code": res.status_code,
                "error": res.text
            })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e)
        })
