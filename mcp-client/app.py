#!/usr/bin/env python
"""
Gradio 기반 채팅 애플리케이션
Anthropic Claude API를 사용하여 대화형 인터페이스 제공
"""
import os
import gradio as gr
import anthropic
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Anthropic API 키 가져오기
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# Anthropic 클라이언트 초기화
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def predict(message, history):
    """
    스트리밍 방식으로 응답을 생성합니다.
    
    Args:
        message: 사용자의 메시지
        history: 지금까지의 대화 내역
        
    Returns:
        생성된 응답 텍스트
    """
    # 메시지가 비어있는 경우 처리
    if not message or message.strip() == "":
        return "메시지를 입력해주세요."
    
    # 대화 내역을 Anthropic 형식으로 변환
    messages = []
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        messages.append({"role": "assistant", "content": assistant})
    
    # 현재 사용자 메시지 추가
    messages.append({"role": "user", "content": message})
    
    try:
        # Claude API를 스트리밍 방식으로 호출
        stream = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=messages,
            stream=True
        )
        
        # 스트리밍 응답을 점진적으로 반환
        chunks = []
        for chunk in stream:
            if chunk.type == "content_block_delta" and hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                chunks.append(chunk.delta.text or "")
                yield "".join(chunks)
    
    except Exception as e:
        yield f"오류가 발생했습니다: {str(e)}"

# Gradio 인터페이스 설정
with gr.Blocks(theme="soft") as demo:
    gr.Markdown("# Claude 챗봇")
    gr.Markdown("Anthropic의 Claude 3.7 Sonnet 모델을 이용한 대화형 인터페이스입니다.")
    
    chatbot = gr.ChatInterface(
        fn=predict,
        examples=["안녕하세요!", "파이썬으로 간단한 웹 서버를 만드는 방법을 알려주세요."],
        title="",
    )

if __name__ == "__main__":
    # Gradio 앱 실행
    demo.launch() 