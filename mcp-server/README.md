# 이미지 생성 MCP 서버

Model Context Protocol (MCP)을 사용하여 SANA SPRINT 이미지 생성 기능을 제공하는 서버입니다.

## 기능

- 텍스트 프롬프트를 기반으로 이미지 생성 (SANA SPRINT API 활용)
- STDIO 통신 프로토콜 지원
- FastMCP 라이브러리 사용

## 설치 및 실행

### 환경 설정

```bash
# uv를 사용하여 가상환경 생성
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

### 서버 실행

```bash
# 직접 실행
python server.py

# 또는 fastmcp CLI 사용
fastmcp run server.py
```

## 도구 목록

1. `generate_image` - 텍스트 프롬프트를 기반으로 이미지를 생성합니다.
    - 매개변수:
        - `prompt`: 이미지 생성에 사용할 텍스트 설명 (필수)

## 테스트 방법

1. 서버 시작

    ```bash
    python server.py
    ```

2. 클라이언트 실행 (다른 터미널에서)
    ```bash
    python client_example.py
    ```

## 사용된 기술

- FastMCP: Model Context Protocol 구현을 위한 Python SDK
- Gradio Client: SANA SPRINT API 호출을 위한 클라이언트 라이브러리

## 목업 이미지 추가

서버가 테스트 목적으로 사용할 목업 이미지를 추가하려면 `mock_images` 디렉토리에 이미지 파일(JPG, PNG)을 저장하세요.
