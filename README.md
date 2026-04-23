# dfinery1-bigdata-export

DFINERY 콘솔의 빅데이터 Raw Data Export를 자동화합니다.

## 설치 및 실행

```bash
# 환경변수 설정
export DFINERY_EMAIL="your@email.com"
export DFINERY_PASSWORD="your_password"
export DFINERY_APPKEY="your_appkey"
export DFINERY_ACCOUNT_ID="your_account_id"

# 실행 (설치 자동)
uvx dfinery1-bigdata-export --template "내 템플릿"
```

> `uvx`가 없으면: `pip install uv && uvx dfinery1-bigdata-export ...`
> Chromium 브라우저는 첫 실행 시 자동 설치됩니다.

## 사용법

```bash
# 전체 실행 (생성 → 대기 → 다운로드)
uvx dfinery1-bigdata-export --template "내 템플릿"

# 2단계 분리 실행 (권장)
uvx dfinery1-bigdata-export --template "내 템플릿" --mode create      # 06:00
uvx dfinery1-bigdata-export --template "내 템플릿" --mode download    # 07:00

# 어제 데이터
uvx dfinery1-bigdata-export --template "내 템플릿" --date-offset -1

# 확인만
uvx dfinery1-bigdata-export --template "내 템플릿" --dry-run
```

## 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--template` | (필수) | Export 템플릿 이름 |
| `--mode` | `all` | `create` / `download` / `all` |
| `--date-offset` | `0` | 날짜 오프셋 (0=오늘, -1=어제) |
| `-o`, `--output-dir` | `./output` | 다운로드 저장 디렉토리 |
| `--dry-run` | - | 실행 없이 확인만 |
| `--max-wait` | `600` | 최대 대기 시간(초) |

## 사전 준비

1. DFINERY 콘솔에서 추출 조건을 설정한 **Export 템플릿을 1회 수동 생성**
2. 콘솔 URL에서 APPKEY, ACCOUNT_ID 확인:
   ```
   https://console.dfinery.io/{ACCOUNT_ID}/data-studio/{APPKEY}/raw-data-export
   ```

> 상세 가이드는 [GUIDE.md](GUIDE.md)를 참조하세요.
