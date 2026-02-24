# rss2twt

RSS 피드를 모니터링하여 새로운 게시물이 감지되면 자동으로 Mastodon에 포스트하는 봇입니다.

## 개요

`rss2twt`는 [feeder.ini](feeder.ini)에 등록된 RSS 피드 목록을 주기적으로 확인하고, 이전 실행 이후 새로 게시된 항목이 있으면 Mastodon 인스턴스에 자동으로 상태 게시물(toot)을 발송합니다. 각 피드별로 마지막으로 확인한 타임스탬프를 [late.st](late.st) 파일에 저장하여 중복 발송을 방지합니다.

## 요구 사항

- Python >= 3.14
- [feedparser](https://pypi.org/project/feedparser/) >= 6.0.12
- [Mastodon.py](https://pypi.org/project/Mastodon.py/) >= 2.1.4

## 설치

```sh
# 저장소 클론
git clone https://github.com/dazeemdas/rss2twt
cd rss2twt

# 의존성 설치
pip install feedparser mastodon.py
```

## 설정

### 1. Mastodon API 키 설정

[tweetkey.ini](tweetkey.ini) 파일에 Mastodon 인스턴스의 액세스 토큰과 API 기본 URL을 입력합니다.

```ini
access_token="YOUR_ACCESS_TOKEN"
api_base_url="https://your.mastodon.instance/"
```

### 2. RSS 피드 등록

[feeder.ini](feeder.ini) 파일에 감시할 RSS 피드를 등록합니다. 각 행의 형식은 다음과 같습니다:

```ini
index="1" prefix="표시이름" name="식별명" RSS="https://example.com/rss" filter="정규표현식"
```

| 필드 | 필수 | 설명 |
|------|------|------|
| `index` | ✅ | 고유 식별 번호 (정수, 중복 불가) |
| `RSS` | ✅ | RSS 피드 URL |
| `name` | ❌ | 피드 식별명 (로그 등에 사용) |
| `prefix` | ❌ | 포스트 제목 앞에 붙는 텍스트 (`\n`으로 줄바꿈 가능) |
| `suffix` | ❌ | 포스트 제목 뒤에 붙는 텍스트 (`\n`으로 줄바꿈 가능) |
| `filter` | ❌ | 제목에 적용할 정규표현식 필터 (기본값: `.*`, 모든 항목 통과) |

- `#`으로 시작하는 행은 주석으로 처리됩니다.
- `index` 필드가 없는 행은 무시됩니다.

#### 예시

```ini
# 모든 게시물을 포스트
index="1" prefix="작성자이름\n" name="작성자이름" RSS="https://example.com/rss?rss=2.0"

# 특정 키워드가 포함된 게시물만 포스트
index="2" prefix="작성자이름\n" name="작성자이름" RSS="https://example.com/rss?rss=2.0" filter=".*(키워드1|키워드2).*"
```

## 사용법

```sh
python main.py
```

스크립트를 실행하면 다음 순서로 동작합니다:

1. [feeder.ini](feeder.ini)에서 감시 대상 RSS 피드 목록을 읽어옵니다. ([`read_rss_watchlist`](main.py))
2. [late.st](late.st)에서 각 피드의 마지막 확인 타임스탬프를 불러옵니다. ([`read_latest_date`](main.py))
3. [tweetkey.ini](tweetkey.ini)의 정보로 Mastodon에 로그인합니다. ([`mastodon_login`](main.py))
4. 각 피드의 RSS를 파싱하여 새로운 게시물이 있는지 확인합니다. ([`rss2compare`](main.py))
5. 새 게시물이 있으면 필터를 적용한 뒤 Mastodon에 포스트합니다. ([`Write_Post`](main.py))
6. 변경 사항이 있으면 [late.st](late.st) 파일을 갱신합니다. ([`write_latest_date`](main.py))

### 주기적 실행

cron이나 systemd timer 등을 사용하여 주기적으로 실행할 수 있습니다.

```sh
# crontab 예시: 10분마다 실행
*/10 * * * * cd /path/to/Replace_twitterfeed && python main.py
```

## 프로젝트 구조

```
├── main.py            # 메인 스크립트 (Mastodon 연동)
├── feeder.ini         # RSS 피드 감시 목록
├── late.st            # 피드별 마지막 확인 타임스탬프 (자동 생성)
├── tweetkey.ini       # Mastodon API 인증 정보
├── event.log          # 실행 로그 (자동 생성, 최대 1MB × 5개)
├── pyproject.toml     # 프로젝트 메타데이터 및 의존성
└── .github/
    └── copilot-instructions.md
```

## 주요 클래스 및 함수

| 이름 | 설명 |
|------|------|
| [`RSSFeedList`](main.py) | RSS 피드의 정보(index, name, prefix, suffix, RSS URL, filter)를 담는 클래스 |
| [`CustomError`](main.py) | 중복 인덱스, RSS 누락 등 유효성 검증용 사용자 정의 예외 |
| [`read_rss_watchlist`](main.py) | `feeder.ini`를 파싱하여 `RSSFeedList` 목록을 반환 |
| [`read_latest_date`](main.py) | `late.st`를 파싱하여 피드별 마지막 타임스탬프 딕셔너리를 반환 |
| [`write_latest_date`](main.py) | 갱신된 타임스탬프 딕셔너리를 `late.st`에 기록 |
| [`rss2compare`](main.py) | RSS 피드를 파싱하여 새 게시물 여부를 판단하고 포스트 발송 |
| [`Write_Post`](main.py) | 필터를 적용한 뒤 Mastodon에 상태 게시물을 발송 |
| [`mastodon_login`](main.py) | `tweetkey.ini`에서 인증 정보를 읽어 Mastodon 세션을 반환 |

## 로깅

실행 로그는 `event.log` 파일에 기록됩니다.
- 최대 크기: 1MB
- 최대 백업 파일 수: 5개 (로테이팅 로그)
- 로그 형식: `%(asctime)s|%(levelname)s > %(message)s`

## 라이선스

이 프로젝트는 MIT License로 제공됩니다.
