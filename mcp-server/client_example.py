#!/usr/bin/env python
"""
MCP 서버 테스트를 위한 클라이언트 예제
"""
import asyncio
import base64
from pathlib import Path
from fastmcp import Client

# 결과 이미지를 저장할 디렉토리
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

async def test_image_generation():
    """이미지 생성 서버에 연결하고 테스트합니다."""
    
    # 서버 스크립트 경로
    server_script = str(Path(__file__).parent / "server.py")
    
    print(f"서버 스크립트에 연결: {server_script}")
    
    # 클라이언트 생성 및 서버 연결
    async with Client(server_script) as client:
        # 사용 가능한 도구 목록 확인
        tools = await client.list_tools()
        print("\n사용 가능한 도구:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
        
        # 이미지 생성 도구 호출
        # prompt = "푸른 하늘 아래 산과 호수가 있는 아름다운 풍경"
        prompt = "an anime illustration of an alien parrot"
        print(f"\n이미지 생성 중: '{prompt}'")
        
        # prompt만 전달
        results = await client.call_tool("generate_image", {"prompt": prompt})
        
        # 결과 처리
        print(f"결과 수신: {len(results)} 항목")
        for i, result in enumerate(results):
            if result.type == "text":
                print(f"\nText: {result.text}")
            elif result.type == "image":
                # 이미지 데이터 저장
                output_path = OUTPUT_DIR / f"generated_image_{i}.jpg"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(result.data))
                print(f"\n이미지 저장됨: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_image_generation()) 