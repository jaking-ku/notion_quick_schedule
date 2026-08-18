"""
노션 API 연동 클라이언트 모듈
todolist 2 데이터베이스와의 통신 및 일정 생성을 담당합니다.
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_ID = "0fbc41b344c08355a22701537a4715b2"
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

class NotionClient:
    def __init__(self, token: Optional[str] = None, database_id: Optional[str] = None):
        self._manual_token = token
        self._manual_db_id = database_id

    @property
    def token(self) -> str:
        if self._manual_token:
            return self._manual_token
        load_dotenv(override=True)
        return os.getenv("NOTION_TOKEN", "").strip()

    @property
    def database_id(self) -> str:
        if self._manual_db_id:
            raw_id = self._manual_db_id
        else:
            load_dotenv(override=True)
            raw_id = os.getenv("NOTION_DATABASE_ID", DEFAULT_DATABASE_ID).strip()
        return raw_id.replace("_", "").replace("-", "")

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION
        }

    def verify_connection(self) -> Dict[str, Any]:
        """노션 데이터베이스 접근 권한 및 유효성 확인"""
        if not self.token:
            return {"success": False, "error": "NOTION_TOKEN 환경 변수가 설정되지 않았습니다."}
        
        url = f"{NOTION_API_URL}/databases/{self.database_id}"
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                data = response.json()
                title_list = data.get("title", [])
                title_text = title_list[0].get("plain_text", "데이터베이스") if title_list else "데이터베이스"
                return {"success": True, "title": title_text, "id": self.database_id}
            else:
                return {"success": False, "status_code": response.status_code, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_memo_property_name(self) -> str:
        """데이터베이스에서 메모를 기록할 첫 번째 메모 필드(1. 등) 탐색"""
        try:
            url = f"{NOTION_API_URL}/databases/{self.database_id}"
            res = requests.get(url, headers=self.get_headers(), timeout=5)
            if res.status_code == 200:
                props = res.json().get("properties", {})
                # 1. 또는 1. 으로 시작하는 rich_text 필드 찾기
                for name, info in props.items():
                    if info.get("type") == "rich_text" and name.strip().startswith("1"):
                        return name
                # 없으면 1.  반환
                return "1. "
        except Exception:
            pass
        return "1. "

    def create_schedule_item(
        self,
        title: str,
        category: str,
        start_date: str,
        end_date: Optional[str] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        노션 todolist 2 데이터베이스에 신규 일정 생성
        """
        if not self.token:
            return {"success": False, "error": "NOTION_TOKEN 설정이 필요합니다."}

        url = f"{NOTION_API_URL}/pages"
        
        # 날짜 속성 구성
        date_payload: Dict[str, Any] = {"start": start_date}
        if end_date:
            date_payload["end"] = end_date

        properties: Dict[str, Any] = {
            "이름": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "상태": {
                "select": {
                    "name": category
                }
            },
            "완료": {
                "checkbox": False
            },
            "마감일": {
                "date": date_payload
            }
        }

        # 메모 속성이 있는 경우 안전하게 필드명 감지 후 추가
        if memo and memo.strip():
            memo_prop_name = self._find_memo_property_name()
            properties[memo_prop_name] = {
                "rich_text": [
                    {
                        "text": {
                            "content": memo.strip()
                        }
                    }
                ]
            }

        payload = {
            "parent": {
                "database_id": self.database_id
            },
            "properties": properties
        }

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=10)
            if response.status_code in [200, 201]:
                res_data = response.json()
                return {
                    "success": True,
                    "page_id": res_data.get("id"),
                    "url": res_data.get("url"),
                    "message": "노션에 일정이 정상 등록되었습니다."
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
