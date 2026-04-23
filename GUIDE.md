# DFINERY Export 자동화 — 설정 가이드

## 1. 사전 준비

### 1-1. DFINERY 콘솔에서 Export 템플릿 생성

이 도구는 기존 Export 템플릿의 **설정(이벤트 종류, 필터, 컬럼 등)을 복사**하여 날짜만 변경해서 실행합니다.
먼저 콘솔에서 원하는 조건의 Export를 1회 수동으로 생성하세요.

1. DFINERY 콘솔 접속: `https://console.dfinery.io`
2. 좌측 메뉴 → **데이터 스튜디오** → **Raw Data Export**
3. **+ 새 Export 만들기**
4. 원하는 조건 설정 (이벤트 타입, 세그먼트, 필터 등)
5. 이름을 지정하고 저장 (예: `일별 구매 이벤트`)

> 날짜 범위는 아무 값이나 넣어도 됩니다. 도구가 실행 시 자동으로 덮어씁니다.

### 1-2. APPKEY와 ACCOUNT_ID 확인

콘솔 Raw Data Export 페이지의 URL에서 확인:

```
https://console.dfinery.io/{ACCOUNT_ID}/data-studio/{APPKEY}/raw-data-export
                            ^^^^^^^^^^^              ^^^^^^
```

---

## 2. 설치

### uv가 없는 경우

```bash
pip install uv
```

### 실행 (설치 자동)

```bash
export DFINERY_EMAIL="your@email.com"
export DFINERY_PASSWORD="your_password"
export DFINERY_APPKEY="your_appkey"
export DFINERY_ACCOUNT_ID="your_account_id"

uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --dry-run
```

> 첫 실행 시 Chromium 브라우저가 자동 설치됩니다 (약 150MB, 1회만).

---

## 3. 실행 방법

### 3-1. 테스트 (dry-run)

```bash
uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --dry-run
```

정상 출력 예시:
```
=== DFINERY Export (all) ===
템플릿: 일별 구매 이벤트
대상 날짜: 2026-04-24 (offset: 0)
[AUTH] 토큰 획득 완료
[LIST] 5개 Export
[TEMPLATE] '일별 구매 이벤트'
[DRY-RUN] 생성될 이름: 일별 구매 이벤트 - 20260424
```

### 3-2. 전체 실행

```bash
uvx dfinery1-bigdata-export --template "일별 구매 이벤트" -o ./downloads
```

### 3-3. 2단계 분리 실행 (권장)

데이터 양이 많으면 추출에 시간이 걸립니다:

```bash
# 1단계: 생성 + 실행 (예: 06:00)
uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --mode create

# 2단계: 다운로드 (예: 07:00)
uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --mode download -o ./downloads
```

### 3-4. 어제/그저께 데이터

```bash
uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --date-offset -1
```

---

## 4. 자동화 (크론)

```bash
crontab -e
```

```cron
# 환경변수
DFINERY_EMAIL=your@email.com
DFINERY_PASSWORD=your_password
DFINERY_APPKEY=your_appkey
DFINERY_ACCOUNT_ID=your_account_id

# 매일 06:00 생성, 07:00 다운로드
0 6 * * * uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --mode create >> /tmp/dfinery_create.log 2>&1
0 7 * * * uvx dfinery1-bigdata-export --template "일별 구매 이벤트" --mode download -o ~/downloads >> /tmp/dfinery_download.log 2>&1
```

---

## 5. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `auth 토큰 획득 실패` | 이메일/비밀번호 오류 | 환경변수 확인, 콘솔에서 로그인 가능한지 확인 |
| 템플릿을 찾을 수 없음 | 이름 불일치 | `--dry-run`으로 목록 확인, 정확한 이름 사용 |
| download에서 "미완료" | 추출 진행 중 | 시간을 더 두고 재시도 |
| all 모드 타임아웃 | 데이터 대량 | `--max-wait 1800` 또는 분리 실행 |
| Chromium 설치 실패 | 권한/디스크 | `playwright install chromium` 수동 실행 |

---

## 6. 업데이트

```bash
uvx --reinstall dfinery1-bigdata-export --template "..."
```
