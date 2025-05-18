# Gradio 기반 채팅 애플리케이션

Anthropic Claude API를 사용하여 대화형 인터페이스를 제공하는 Gradio 기반 채팅 애플리케이션입니다.

## 기능

- Gradio를 이용한 직관적인 대화형 UI
- Anthropic Claude 3.7 Sonnet 모델 통합
- 실시간 스트리밍 응답 지원
- 환경 변수를 이용한 API 키 관리

## 설치 방법

1. 저장소 클론

```bash
git clone <repository-url>
cd mcp-client
```

2. 가상 환경 설정 및 종속성 설치 (uv 사용)

```bash
uv venv

# 가상환경 활성화
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 의존성 파일(requirements.txt 또는 pyproject.toml)로부터 패키지 동기화
uv sync

# 또는 개발 모드로 현재 패키지 설치
uv pip install -e .
```

3. 환경 설정

`.env.example` 파일을 `.env`로 복사하고 Anthropic API 키를 설정하세요:

```bash
cp .env.example .env
# .env 파일을 편집하여 ANTHROPIC_API_KEY 값을 설정
```

## 실행 방법

```bash
# 가상 환경이 활성화된 상태에서
python app.py
```

브라우저에서 `http://localhost:7860`으로 접속하여 애플리케이션을 사용할 수 있습니다.

## 프로젝트 구조

```
mcp-client/
├── app.py              # 메인 애플리케이션 코드
├── .env                # 환경 변수 (API 키 등)
├── .env.example        # 환경 변수 예시 파일
├── pyproject.toml      # 프로젝트 메타데이터 및 종속성
└── README.md           # 프로젝트 설명서
```

## 기술 스택

- Python 3.10+
- Gradio: 웹 인터페이스 프레임워크
- Anthropic Python SDK: Claude AI 모델 연동
- python-dotenv: 환경 변수 관리
