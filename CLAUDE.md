# DFINERY 빅데이터 Export 자동화 — Claude 설정 가이드

이 도구는 DFINERY 콘솔의 Raw Data Export를 자동화합니다.
사용자가 "빅데이터 익스포트 설정해줘", "Export 자동화 해줘" 등을 요청하면 아래 순서로 안내하세요.

---

## 설정 플로우 (대화형으로 한 단계씩 진행)

### Step 1. 설치

```bash
pip install uv
uvx --from "dfinery1-bigdata-export @ git+https://github.com/mike-igaw/dfinery1-bigdata-export.git" dfinery1-bigdata-export --help
```

첫 실행 시 Chromium 브라우저가 자동 설치됩니다 (약 150MB, 1회만).
설치 오류가 발생하면 `pip install playwright && playwright install chromium`을 수동 실행하세요.

### Step 2. 사용자에게 필요한 정보 수집

아래 정보를 **한 번에 다 묻지 말고, 단계별로 하나씩** 질문하세요:

#### 2-1. DFINERY 콘솔 로그인 정보
> "DFINERY 콘솔에 로그인할 때 사용하는 **이메일 주소**를 알려주세요."

> "해당 계정의 **비밀번호**를 알려주세요."

⚠️ 비밀번호는 .env 파일에 저장하고 .gitignore에 반드시 포함하세요.

#### 2-2. APPKEY와 ACCOUNT_ID
> "DFINERY 콘솔 → 데이터 스튜디오 → Raw Data Export 페이지에 접속해주세요.
> 브라우저 주소창의 URL이 이런 형태입니다:
> `https://console.dfinery.io/{ACCOUNT_ID}/data-studio/{APPKEY}/raw-data-export`
> URL을 복사해서 보내주시면 제가 추출할게요."

URL을 받으면 ACCOUNT_ID와 APPKEY를 파싱하세요.

#### 2-3. Export 템플릿
> "추출하려는 데이터의 Export 템플릿이 이미 만들어져 있나요?
> 콘솔의 Raw Data Export 목록에서 사용할 템플릿 이름을 알려주세요.
> (아직 없다면, 콘솔에서 원하는 조건으로 Export를 1회 수동 생성해주세요.
> 이벤트 종류, 필터, 컬럼 등을 설정하고 이름을 지정하면 됩니다.
> 날짜 범위는 아무 값이나 넣어도 괜찮습니다 — 도구가 자동으로 덮어씁니다.)"

#### 2-4. 추출 스케줄
> "데이터 추출을 얼마나 자주 실행할까요?
> - 매일 (가장 일반적)
> - 매주 월요일
> - 매주 특정 요일
> - 수동 실행만 (자동화 없음)
>
> 실행 시각은 보통 새벽 6시~7시를 추천드립니다 (전일 데이터 확정 후)."

#### 2-5. 다운로드 위치
> "다운로드한 파일을 어디에 저장할까요?
> - 특정 폴더 경로 (예: ~/Downloads/dfinery-export, ~/data 등)
> - Google Drive 동기화 폴더
> - 기본값 (./output)
>
> 원하는 경로를 알려주세요."

### Step 3. 환경변수 설정

수집한 정보로 `.env` 파일을 생성하세요:

```bash
cat > .env << 'EOF'
DFINERY_EMAIL=수집한이메일
DFINERY_PASSWORD=수집한비밀번호
DFINERY_APPKEY=파싱한앱키
DFINERY_ACCOUNT_ID=파싱한계정ID
EOF
```

`.gitignore`에 `.env`가 포함되어 있는지 반드시 확인하세요.

### Step 4. 테스트 (dry-run)

```bash
source .env
export DFINERY_EMAIL DFINERY_PASSWORD DFINERY_APPKEY DFINERY_ACCOUNT_ID
uvx dfinery1-bigdata-export --template "템플릿이름" --dry-run
```

성공 시 출력 예시:
```
[AUTH] 토큰 획득 완료
[LIST] N개 Export
[TEMPLATE] '템플릿이름'
[DRY-RUN] 생성될 이름: 템플릿이름 - 20260424
```

실패 시 대처:
- `auth 토큰 획득 실패` → 이메일/비밀번호 확인
- `템플릿을 찾을 수 없음` → 콘솔에서 정확한 이름 확인

### Step 5. 실제 실행 테스트

```bash
uvx dfinery1-bigdata-export --template "템플릿이름" -o "다운로드경로"
```

### Step 6. 자동화 설정 (사용자가 원한 경우)

사용자가 선택한 스케줄에 따라 crontab을 설정하세요:

```bash
crontab -e
```

**매일 실행 (2단계 분리 — 권장):**
```cron
DFINERY_EMAIL=이메일
DFINERY_PASSWORD=비밀번호
DFINERY_APPKEY=앱키
DFINERY_ACCOUNT_ID=계정ID

0 6 * * * uvx dfinery1-bigdata-export --template "템플릿" --mode create >> /tmp/dfinery_create.log 2>&1
0 7 * * * uvx dfinery1-bigdata-export --template "템플릿" --mode download -o "경로" >> /tmp/dfinery_download.log 2>&1
```

**매주 월요일:**
```cron
0 6 * * 1 uvx dfinery1-bigdata-export --template "템플릿" --mode create >> /tmp/dfinery_create.log 2>&1
0 7 * * 1 uvx dfinery1-bigdata-export --template "템플릿" --mode download -o "경로" >> /tmp/dfinery_download.log 2>&1
```

### Step 7. 완료 안내

> "설정이 모두 완료되었습니다! 정리하면:
> - 템플릿: {이름}
> - 스케줄: {주기}
> - 저장 위치: {경로}
> - 실행 시각: {시각}
>
> 문제가 생기면 로그를 확인하세요: `cat /tmp/dfinery_create.log`
> 수동 실행: `uvx dfinery1-bigdata-export --template "{이름}" -o "{경로}"`"

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `auth 토큰 획득 실패` | 이메일/비밀번호 오류 | 환경변수 확인, 콘솔 로그인 가능 여부 확인 |
| 템플릿을 찾을 수 없음 | 이름 불일치 | `--dry-run`으로 목록 확인 |
| download에서 "미완료" | 추출 진행 중 | 시간 간격을 더 두고 재시도, 또는 `--max-wait 1800` |
| Chromium 설치 실패 | 권한/디스크 | `playwright install chromium` 수동 실행 |
| `No module named 'playwright'` | 의존성 미설치 | `pip install playwright && playwright install chromium` |

---

## 주의사항

- 비밀번호는 절대 git에 커밋하지 마세요 (.env + .gitignore)
- 데이터 양이 많으면 create → download 분리 실행을 권장합니다 (all 모드는 타임아웃 위험)
- 날짜 오프셋: `--date-offset 0` = 오늘, `-1` = 어제 (기본값: 0)
