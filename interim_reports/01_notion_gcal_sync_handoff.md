# 노션 및 구글 캘린더 연동 프로젝트 인수인계서

## 1. 프로젝트 개요 및 배경

* 목적: 노션(Notion)의 할 일(To do) 및 일정 관리 데이터베이스를 구글 캘린더(Google Calendar)와 연동하여 모바일 월간 뷰(Month View) 및 위젯(Widget) 환경에서 편리하게 확인하도록 구현.
* 배경: 노션 모바일 어플리케이션의 일정 확인 편의성 한계를 보완하기 위해, 노션 데이터를 단방향(Notion → Google Calendar)으로 자동 동기화함.
* 개발 목표: Antigravity IDE 환경에서 독립 실행형 파이프라인(스크립트 또는 웹 서비스)으로 자체 구현.

***

## 2. 노션 데이터베이스 명세

* 데이터베이스 명칭: todolist 2
* 데이터베이스 ID: cb6c41b3_44c0_83cc_8edb_8768e5452fd0
* 페이지 URL: https://jungle_sleet_d1b.notion.site/0fbc41b344c08355a22701537a4715b2

### 속성(Property) 스키마 상세

1. 이름 (title): 일정 및 할 일 제목 (문자열)
2. 마감일 (date): 일정 일시 또는 기간 (start, end, time_zone)
3. 상태 (select): 5가지 분류 상태값
4. 완료 (checkbox): 완료 여부 (True / False)
5. 구글 이벤트 ID (rich_text): 구글 캘린더 이벤트 고유 식별자(ID)
6. 누구와 (multi_select): 대상 태그 목록
7. 1. ~ 5. (rich_text): 상세 메모 및 티켓 링크

***

## 3. 핵심 비즈니스 로직 및 규칙

### 3.1 종일(All day) 일정의 종료일(+1일) 처리 규칙
* 구글 캘린더 API 특성: 종일 일정 등록 시 종료일(end.date)은 실제 종료일의 다음 날(Exclusive End Date)로 전달되어야 정상 기간으로 인식됨.
* 규칙:
  * 시간 포함 일정: 시작 시간과 종료 시간을 그대로 전달.
  * 종일 일정: 노션 종료일이 존재하면 (종료일 + 1일)을 전달하고, 종료일이 없으면 (시작일 + 1일)을 전달.

### 3.2 분류(상태)별 구글 캘린더 색상(Color ID) 매핑
사용자 정의 5대 분류에 따른 구글 캘린더 색상 식별자:

* 회사 : 작업 → Color ID: "11" (토마토 / 빨강)
* 회사 : 사무 → Color ID: "9" (블루베리 / 파랑)
* LIFE → Color ID: "10" (바질 / 초록)
* 분류대기 → Color ID: "8" (흑연 / 회색)
* 업무보류 → Color ID: "1" (라벤더 / 연보라)
* 기본값(미지정 시) → Color ID: "8" (회색)

***

## 4. Antigravity IDE 구현 아키텍처 제안

### 4.1 권장 디렉터리 구성
* scripts/01_sync_notion_to_gcal.py : 노션 변경 사항 감지 및 구글 캘린더 동기화 메인 스크립트
* scripts/notion_client.py : 노션 API 연동 헬퍼 모듈
* scripts/gcal_client.py : 구글 캘린더 API 연동 헬퍼 모듈
* primary_data/ : 동기화 로그 및 백업 데이터
* intermediate_results/ : 상태 캐시 및 매핑 테이블 저장

### 4.2 실행 파이프라인 흐름
1. 노션 데이터베이스에서 최근 변경된 항목 조회 (Last Edited Time 기준)
2. 구글 이벤트 ID 존재 여부 검사:
   * ID 부재 시: 구글 캘린더 이벤트 신규 생성 → 발급된 Event ID를 노션의 구글 이벤트 ID 필드에 업데이트
   * ID 존재 시: 구글 캘린더의 해당 Event ID 일정을 최신 데이터로 업데이트
3. 완료 체크박스가 True인 경우: 구글 캘린더 제목에 [완료] 표기 또는 색상 변경 처리 (선택 사양)
