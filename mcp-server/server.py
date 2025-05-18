#!/usr/bin/env python
"""
MCP 서버 - 이미지 생성 기능 제공
"""
from fastmcp import FastMCP
from mcp.types import TextContent, ImageContent
import base64
import os
import time
from pathlib import Path
from typing import Optional
from gradio_client import Client as GradioClient

# MCP 서버 초기화
mcp = FastMCP(name="이미지 생성 MCP 서버")

# Gradio 클라이언트 인스턴스 (게으른 초기화 위해 전역 변수로 선언)
gradio_client = None

def get_gradio_client():
    """게으른 초기화 패턴으로 Gradio 클라이언트 생성"""
    global gradio_client
    if gradio_client is None:
        gradio_client = GradioClient("ysharma/SanaSprint")
    return gradio_client

@mcp.tool()
def generate_image(prompt: str) -> list:
    """
    텍스트 프롬프트를 기반으로 이미지를 생성합니다.
    
    Args:
        prompt: 이미지 생성을 위한 텍스트 프롬프트
        
    Returns:
        생성된 이미지 컨텐츠
    """
    # 시작 시간 기록
    start_time = time.time()
    
    # 기본 매개변수 설정
    width = 256
    height = 256
    model_size = "1.6B"
    guidance_scale = 4.5
    num_inference_steps = 2
    randomize_seed = True
    seed_value = 0
    
    # 응답 생성용 텍스트
    response_text = f"'{prompt}'에 대한 이미지 생성 요청. 크기: {width}x{height} 픽셀, 모델: {model_size}"
    
    try:
        # Gradio 클라이언트로 SANA SPRINT API 호출
        client = get_gradio_client()
        result = client.predict(
            prompt=prompt,
            model_size=model_size,
            seed=seed_value,
            randomize_seed=randomize_seed,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            api_name="/infer"
        )
        
        # API 응답에서 이미지 파일 경로와 사용된 시드 추출
        image_path, used_seed = result
        
        # 이미지 파일 타입 확인
        mime_type, _ = os.path.splitext(image_path)
        if not mime_type or mime_type == "":
            mime_type = "image/jpeg"  # 기본값
        else:
            mime_type = f"image/{mime_type.strip('.').lower()}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"
        
        # 이미지 파일 읽기 및 base64 인코딩
        with open(image_path, "rb") as f:
            image_data = f.read()
            base64_image = base64.b64encode(image_data).decode("utf-8")
        
        # 이미지 생성 성공 메시지
        generation_time = time.time() - start_time
        success_text = f"{response_text}\n생성 완료! (소요 시간: {generation_time:.2f}초)"
        
        return [
            TextContent(type="text", text=success_text),
            ImageContent(type="image", data=base64_image, mimeType=mime_type)
        ]
    
    except Exception as e:
        # 이미지 생성 실패 시 에러 메시지만 반환
        error_text = f"{response_text}\n생성 실패: {str(e)}"
        return [TextContent(type="text", text=error_text)]

if __name__ == "__main__":
    # STDIO 트랜스포트를 사용하여 서버 실행
    mcp.run(transport="stdio") 