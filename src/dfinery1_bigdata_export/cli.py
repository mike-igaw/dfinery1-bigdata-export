"""
DFINERY 빅데이터 익스포트 자동화 도구

콘솔에 로그인 → 템플릿 찾기 → 날짜 조정 → 복사 생성 → 실행 → 완료 대기 → 다운로드

2단계 분리 실행 (권장):
  06:00  --mode create   → 로그인 → 템플릿 복사(당일 날짜) → 추출 실행
  07:00  --mode download → 로그인 → 완료 확인 → 파일 다운로드

일괄 실행:
  --mode all  → create + 폴링 대기 + download (기본값)

사용법:
    # 환경변수 설정 (.env 파일 참조)
    export DFINERY_EMAIL="your@email.com"
    export DFINERY_PASSWORD="your_password"
    export DFINERY_APPKEY="your_appkey"
    export DFINERY_ACCOUNT_ID="your_account_id"

    # 전체 실행
    python3 dfinery_export.py --template "내 익스포트 템플릿"

    # 생성만 (크론 06:00)
    python3 dfinery_export.py --template "내 익스포트 템플릿" --mode create

    # 다운로드만 (크론 07:00)
    python3 dfinery_export.py --template "내 익스포트 템플릿" --mode download --output-dir ./downloads

    # 어제 데이터 추출
    python3 dfinery_export.py --template "내 익스포트 템플릿" --date-offset -1

    # 확인만 (실행 안 함)
    python3 dfinery_export.py --template "내 익스포트 템플릿" --dry-run
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests

# ── 기본 설정 ──────────────────────────────────────────────
API_BASE = "https://api-console.adbrix.io"
CONSOLE_URL = "https://console.dfinery.io"
KST = timezone(timedelta(hours=9))

# Create 요청 시 제외할 필드 (서버 자동 생성)
_EXCLUDE_FROM_CREATE = {
    "export_param", "created_user_name", "created_user_email",
    "created_user_id", "created_datetime", "created_user_ip",
    "last_updated_user_name", "last_updated_user_email",
    "last_updated_user_id", "last_updated_datetime",
    "last_updated_user_ip", "_key", "raw_data_id",
}


# ── 인증 ───────────────────────────────────────────────────

def login_and_get_token(email: str, password: str, account_id: str, appkey: str) -> str:
    """Playwright로 콘솔 로그인 후 auth 토큰을 추출한다."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] playwright 미설치. 아래 명령어로 설치하세요:")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    # Chromium 미설치 시 자동 설치
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True
        )
        if "chromium" not in result.stdout and result.returncode != 0:
            print("[AUTH] Chromium 브라우저 설치 중...")
            subprocess.run(["python3", "-m", "playwright", "install", "chromium"],
                           check=True, capture_output=True)
    except Exception:
        pass  # dry-run 미지원 버전은 그냥 진행

    auth_token = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_request(request):
            nonlocal auth_token
            if auth_token:
                return
            auth_header = request.headers.get("auth")
            if auth_header and "api-console.adbrix.io" in request.url:
                auth_token = auth_header

        page.on("request", on_request)

        target_url = f"{CONSOLE_URL}/{account_id}/data-studio/{appkey}/raw-data-export"
        page.goto(target_url, wait_until="networkidle", timeout=30000)

        email_input = page.query_selector('input[type="email"], input[name="email"]')
        if email_input:
            email_input.fill(email)
            pw_input = page.query_selector('input[type="password"]')
            if pw_input:
                pw_input.fill(password)
            submit = page.query_selector('button[type="submit"]')
            if submit:
                submit.click()
                try:
                    page.wait_for_url("**/data-studio/**", timeout=15000)
                except Exception:
                    pass
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_timeout(2000)

        browser.close()

    if not auth_token:
        print("[ERROR] auth 토큰 획득 실패. 로그인 정보를 확인하세요.")
        sys.exit(1)

    print(f"[AUTH] 토큰 획득 완료")
    return auth_token


# ── API 호출 공통 ──────────────────────────────────────────

def _headers(auth_token: str, appkey: str, account_id: str) -> dict:
    return {
        "auth": auth_token,
        "language-type": "KO",
        "client-guid": str(uuid.uuid4()),
        "date-time-offset": "540",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{CONSOLE_URL}/",
        "client-route-path": "/{ACCOUNT_ID}/data-studio/{APPKEY}/raw-data-export",
        "client-route-payload": json.dumps({"ACCOUNT_ID": account_id, "APPKEY": appkey}),
        "client-version": "1.21.54.9948",
    }


def _parse(data: dict):
    return data.get("data", data.get("result", []))


# ── API 함수 ──────────────────────────────────────────────

def list_exports(headers: dict, appkey: str) -> list:
    resp = requests.get(f"{API_BASE}/api/v1/DataStudio/Export/RawData/List",
                        headers=headers, params={"appkey": appkey, "show_type": "active"}, timeout=30)
    resp.raise_for_status()
    return _parse(resp.json())


def find_template(exports: list, name: str) -> dict | None:
    n = name.strip()
    for item in exports:
        if item.get("name", "").strip() == n:
            return item
    for item in exports:
        if item.get("name", "").strip().startswith(n):
            return item
    return None


def find_by_name(exports: list, exact_name: str) -> dict | None:
    for item in exports:
        if item.get("name", "").strip() == exact_name.strip():
            return item
    return None


def create_export(headers: dict, template: dict, appkey: str, target_date: datetime) -> str:
    date_str = target_date.strftime("%Y%m%d")
    begin = target_date.strftime("%Y-%m-%dT00:00:00")
    end = target_date.strftime("%Y-%m-%dT23:59:59")

    # 기본 이름 추출 (날짜 접미사 제거)
    base_name = template["name"].strip()
    for sep in (" - 2", " -2"):
        idx = base_name.find(sep)
        if idx > 0:
            base_name = base_name[:idx].strip()
            break

    new_name = f"{base_name} - {date_str}"

    payload = {k: v for k, v in template.items() if k not in _EXCLUDE_FROM_CREATE}
    payload["name"] = new_name
    payload["appkey"] = appkey
    if "sql_param" in payload:
        sql_param = dict(payload["sql_param"])
        sql_param["begin_date"] = begin
        sql_param["end_date"] = end
        payload["sql_param"] = sql_param

    resp = requests.post(f"{API_BASE}/api/v1/DataStudio/Export/RawData/Create",
                         headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    result = _parse(resp.json())
    new_id = result.get("raw_data_id", "") if isinstance(result, dict) else ""

    print(f"[CREATE] {new_name} (ID: {new_id})")
    print(f"[CREATE] 기간: {begin} ~ {end}")
    return new_id


def run_task(headers: dict, appkey: str, raw_data_id: str):
    resp = requests.post(f"{API_BASE}/api/v1/DataStudio/Export/RawData/TaskRun",
                         headers=headers,
                         json={"appkey": appkey, "raw_data_id": raw_data_id,
                               "console_url": CONSOLE_URL},
                         timeout=60)
    resp.raise_for_status()
    print("[RUN] 태스크 실행 완료")


def wait_for_completion(headers: dict, appkey: str, raw_data_id: str,
                        max_wait: int = 600, poll_interval: int = 10) -> dict:
    elapsed = 0
    while elapsed < max_wait:
        exports = list_exports(headers, appkey)
        for item in exports:
            if item.get("raw_data_id") == raw_data_id:
                status = item.get("export_param", {}).get("status", "")
                if status == "completed":
                    print(f"[STATUS] 완료! ({elapsed}초 경과)")
                    return item
                elif status in ("failed", "error"):
                    msg = item.get("export_param", {}).get("status_error_message", "")
                    print(f"[ERROR] 태스크 실패: {msg}")
                    sys.exit(1)
                else:
                    print(f"[STATUS] {status} ({elapsed}초)")
        time.sleep(poll_interval)
        elapsed += poll_interval

    print(f"[ERROR] {max_wait}초 초과")
    sys.exit(1)


def download_export(headers: dict, raw_data_id: str, export_name: str,
                     s3_url: str, output_path: str) -> str:
    # 임시 다운로드 URL 생성
    dl_headers = dict(headers)
    dl_headers["isTrusted"] = "true"
    resp = requests.post(f"{API_BASE}/api/v1/TemporaryDownload/",
                         headers=dl_headers,
                         json=[{"file_name": f"{export_name}({raw_data_id})_1",
                                "s3_url": s3_url, "is_json_req": True}],
                         timeout=60)
    resp.raise_for_status()
    result = _parse(resp.json())

    if isinstance(result, list) and result:
        url = result[0].get("download_url", result[0].get("url", ""))
    elif isinstance(result, dict):
        url = result.get("download_url", result.get("url", ""))
    else:
        url = str(result)

    # 파일 다운로드
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[DOWNLOAD] {output_path} ({size_mb:.2f} MB)")
    return output_path


# ── 모드별 실행 ───────────────────────────────────────────

def do_create(headers, appkey, template_name, target_date, exports):
    template = find_template(exports, template_name)
    if not template:
        print(f"[ERROR] 템플릿 '{template_name}' 없음. 목록:")
        for e in exports:
            print(f"  - {e.get('name', '')}")
        sys.exit(1)
    print(f"[TEMPLATE] '{template['name']}'")
    new_id = create_export(headers, template, appkey, target_date)
    if not new_id:
        print("[ERROR] 생성 실패")
        sys.exit(1)
    run_task(headers, appkey, new_id)
    return new_id


def do_download(headers, appkey, template_name, target_date, exports, output_dir):
    date_str = target_date.strftime("%Y%m%d")
    expected = f"{template_name} - {date_str}"
    export = find_by_name(exports, expected)
    if not export:
        print(f"[ERROR] '{expected}' 없음. 목록:")
        for e in exports:
            print(f"  - {e.get('name', '')}")
        sys.exit(1)

    rid = export.get("raw_data_id", "")
    ep = export.get("export_param", {})
    status = ep.get("status", "")
    print(f"[FOUND] '{expected}' (상태: {status})")

    if status != "completed":
        print(f"[ERROR] 미완료 (상태: {status})")
        sys.exit(1)

    file_list = ep.get("file_info", {}).get("file_list", [])
    if not file_list:
        print("[ERROR] 파일 없음")
        sys.exit(1)

    base = template_name.replace(" ", "_")
    downloaded = []
    for i, fi in enumerate(file_list):
        out = os.path.join(output_dir, f"{base}_{date_str}_{i}.csv")
        download_export(headers, rid, expected, fi.get("s3_url", ""), out)
        downloaded.append(out)
    return downloaded


# ── main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DFINERY 빅데이터 Export 자동화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 전체 실행 (생성 → 대기 → 다운로드)
  python3 dfinery_export.py --template "내 템플릿"

  # 크론 분리 실행
  # 06:00
  python3 dfinery_export.py --template "내 템플릿" --mode create
  # 07:00
  python3 dfinery_export.py --template "내 템플릿" --mode download -o ./downloads

  # 어제 데이터
  python3 dfinery_export.py --template "내 템플릿" --date-offset -1
        """)
    parser.add_argument("--template", required=True, help="Export 템플릿 이름")
    parser.add_argument("--mode", choices=["create", "download", "all"], default="all",
                        help="create: 생성+실행 / download: 다운로드 / all: 전체 (기본)")
    parser.add_argument("--date-offset", type=int, default=0,
                        help="날짜 오프셋 (0=오늘, -1=어제)")
    parser.add_argument("-o", "--output-dir", default="./output",
                        help="다운로드 저장 디렉토리 (기본: ./output)")
    parser.add_argument("--dry-run", action="store_true", help="실행 없이 확인만")
    parser.add_argument("--max-wait", type=int, default=600,
                        help="최대 대기(초, all 모드, 기본: 600)")
    parser.add_argument("--auth-token", default="", help="auth 토큰 직접 지정")
    args = parser.parse_args()

    # 환경변수 확인
    email = os.environ.get("DFINERY_EMAIL", "")
    password = os.environ.get("DFINERY_PASSWORD", "")
    appkey = os.environ.get("DFINERY_APPKEY", "")
    account_id = os.environ.get("DFINERY_ACCOUNT_ID", "")

    missing = []
    if not email: missing.append("DFINERY_EMAIL")
    if not password: missing.append("DFINERY_PASSWORD")
    if not appkey: missing.append("DFINERY_APPKEY")
    if not account_id: missing.append("DFINERY_ACCOUNT_ID")
    if missing and not args.auth_token:
        print(f"[ERROR] 환경변수 미설정: {', '.join(missing)}")
        print("  .env 파일을 참조하여 설정하세요.")
        sys.exit(1)

    target_date = datetime.now(KST) + timedelta(days=args.date_offset)
    date_str = target_date.strftime("%Y%m%d")

    print(f"=== DFINERY Export ({args.mode}) ===")
    print(f"템플릿: {args.template}")
    print(f"대상 날짜: {target_date.strftime('%Y-%m-%d')} (offset: {args.date_offset})")

    # 인증
    if args.auth_token:
        token = args.auth_token
    else:
        token = login_and_get_token(email, password, account_id, appkey)

    hdrs = _headers(token, appkey, account_id)
    exports = list_exports(hdrs, appkey)
    print(f"[LIST] {len(exports)}개 Export")

    if args.dry_run:
        tmpl = find_template(exports, args.template)
        if tmpl:
            print(f"[TEMPLATE] '{tmpl['name']}'")
        expected = f"{args.template} - {date_str}"
        ex = find_by_name(exports, expected)
        if ex:
            print(f"[EXISTING] '{expected}' (상태: {ex.get('export_param',{}).get('status','')})")
        else:
            print(f"[DRY-RUN] 생성될 이름: {expected}")
        return

    if args.mode == "create":
        do_create(hdrs, appkey, args.template, target_date, exports)
        print("\n=== create 완료 ===")

    elif args.mode == "download":
        files = do_download(hdrs, appkey, args.template, target_date, exports, args.output_dir)
        print(f"\n=== download 완료: {files} ===")

    else:
        new_id = do_create(hdrs, appkey, args.template, target_date, exports)
        wait_for_completion(hdrs, appkey, new_id, max_wait=args.max_wait)
        exports = list_exports(hdrs, appkey)
        files = do_download(hdrs, appkey, args.template, target_date, exports, args.output_dir)
        print(f"\n=== 완료: {files} ===")


if __name__ == "__main__":
    main()
