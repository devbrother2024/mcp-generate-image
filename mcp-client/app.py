#!/usr/bin/env python
"""
Gradio 기반 채팅 애플리케이션
Anthropic Claude API와 MCP 서버의 도구를 통합하여 대화형 인터페이스 제공
"""
import os
import json
import asyncio
import gradio as gr
import anthropic
import fastmcp
from fastmcp.client.transports import PythonStdioTransport
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Anthropic API 키 가져오기
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# Anthropic 클라이언트 초기화
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# MCP 클라이언트 및 도구 상태 관리
mcp_client = None
mcp_tools = []

async def connect_to_mcp_server(server_path):
    """
    MCP 서버에 연결하고 사용 가능한 도구 목록을 가져옵니다.
    
    Args:
        server_path: MCP 서버 실행 파일 경로
        
    Returns:
        성공/실패 메시지와 연결된 도구 수
    """
    global mcp_client, mcp_tools
    
    try:
        # 기존 클라이언트가 있으면 종료
        if mcp_client:
            await mcp_client.close()
            mcp_client = None
            mcp_tools = []
        
        # 경로가 비어있는 경우 처리
        if not server_path or server_path.strip() == "":
            return "서버 경로를 입력해주세요.", "연결되지 않음"
        
        # PythonStdioTransport를 사용하여 MCP 서버 연결
        print(f"서버 경로: {server_path}")
        try:
            transport = PythonStdioTransport(script_path=server_path)
            print("Transport 생성 완료")
            mcp_client = fastmcp.Client(transport)
            print("Client 생성 완료")
        except Exception as transport_error:
            print(f"Transport/Client 생성 오류: {str(transport_error)}")
            raise Exception(f"MCP 클라이언트 초기화 실패: {str(transport_error)}")
        
        # 비동기 컨텍스트 관리자를 통해 클라이언트에 연결
        try:
            print("클라이언트 연결 시도")
            await mcp_client.__aenter__()
            print("클라이언트 연결 성공")
        except Exception as connect_error:
            print(f"클라이언트 연결 오류: {str(connect_error)}")
            raise Exception(f"MCP 서버 연결 실패: {str(connect_error)}")
        
        # MCP 클라이언트에서 도구 목록 가져오기
        tools_info = await mcp_client.list_tools()
        
        # 도구 목록 변환 및 저장
        mcp_tools = [convert_mcp_tool_to_claude_format(tool) for tool in tools_info]
        
        print(f"도구 목록 변환 완료: {len(mcp_tools)}개")
        print(f"도구 형식 검사: {type(mcp_tools)}")
        if mcp_tools:
            print(f"첫 번째 도구 샘플: {mcp_tools[0]}")
        
        return f"MCP 서버 연결 성공: {server_path}", f"연결됨 (도구 {len(mcp_tools)}개)"
    except Exception as e:
        if mcp_client:
            try:
                await mcp_client.__aexit__(None, None, None)
            except:
                pass
        mcp_client = None
        mcp_tools = []
        return f"MCP 서버 연결 실패: {str(e)}", "연결되지 않음"

def convert_mcp_tool_to_claude_format(tool_info):
    """
    MCP 도구 정보를 Claude API 도구 형식으로 변환합니다.
    
    Args:
        tool_info: MCP 서버에서 가져온 도구 정보
        
    Returns:
        Claude API 형식의 도구 정의
    """
    try:
        # 매개변수 스키마 처리
        properties = {}
        required = []
        
        # 매개변수 정보가 있는 경우 처리
        parameters = getattr(tool_info, "parameters", None)
        if parameters:
            for param in parameters:
                param_name = getattr(param, "name", "")
                param_type = "string"  # 기본값
                param_desc = getattr(param, "description", "")
                param_required = getattr(param, "required", False)
                
                # 매개변수 유형 매핑
                if hasattr(param, "type"):
                    if param.type == "string":
                        param_type = "string"
                    elif param.type in ["integer", "int"]:
                        param_type = "integer"
                    elif param.type in ["number", "float"]:
                        param_type = "number"
                    elif param.type == "boolean":
                        param_type = "boolean"
                    elif param.type in ["array", "list"]:
                        param_type = "array"
                        
                # 매개변수 정의 생성
                param_def = {
                    "type": param_type,
                    "description": param_desc
                }
                
                # 배열 유형인 경우 items 추가
                if param_type == "array":
                    param_def["items"] = {"type": "string"}
                    
                properties[param_name] = param_def
                
                # 필수 매개변수 처리
                if param_required:
                    required.append(param_name)
        
        # Claude API 형식으로 변환
        claude_tool = {
            "name": getattr(tool_info, "name", ""),
            "description": getattr(tool_info, "description", ""),
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
        
        print(f"도구 변환 결과: {claude_tool['name']}")
        return claude_tool
    except Exception as e:
        print(f"도구 변환 오류: {str(e)}")
        # 최소한의 도구 정보 반환
        return {
            "name": getattr(tool_info, "name", "unknown_tool"),
            "description": "도구 변환 중 오류가 발생했습니다.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

async def handle_tool_calls(tool_calls):
    """
    Claude API의 도구 호출 요청을 처리합니다.
    
    Args:
        tool_calls: Claude API가 요청한 도구 호출 정보
        
    Returns:
        도구 실행 결과
    """
    global mcp_client
    
    if not mcp_client:
        return {
            "type": "tool_result",
            "tool_name": tool_calls[0].name,
            "content": "MCP 서버가 연결되지 않았습니다."
        }
    
    results = []
    
    for tool_call in tool_calls:
        try:
            tool_name = tool_call.name
            tool_params = tool_call.parameters if hasattr(tool_call, "parameters") else {}
            
            # JSON 문자열 형태인 경우 딕셔너리로 변환
            if isinstance(tool_params, str):
                tool_params = json.loads(tool_params)
            
            print(f"도구 호출: {tool_name}, 매개변수: {tool_params}")
            
            # MCP 클라이언트를 통해 도구 호출
            result = await mcp_client.call_tool(tool_name, tool_params)
            
            print(f"도구 호출 결과: {result}")
            
            # 도구 실행 결과를 Claude API 형식으로 변환
            # 결과 가공 - .text 또는 .content 속성을 파악하여 처리
            result_content = ""
            if hasattr(result, "text"):
                result_content = result.text
            elif hasattr(result, "content"):
                if isinstance(result.content, list):
                    result_content = "\n".join([str(item) for item in result.content])
                else:
                    result_content = str(result.content)
            else:
                result_content = str(result)
            
            results.append({
                "type": "tool_result",
                "tool_name": tool_name,
                "content": result_content
            })
        except Exception as e:
            results.append({
                "type": "tool_result",
                "tool_name": tool_name if 'tool_name' in locals() else "unknown_tool",
                "content": f"도구 실행 오류: {str(e)}"
            })
    
    return results[0] if len(results) == 1 else results

async def predict(message, history, mcp_server_path, mcp_status):
    """
    스트리밍 방식으로 응답을 생성합니다.
    
    Args:
        message: 사용자의 메시지
        history: 지금까지의 대화 내역
        mcp_server_path: MCP 서버 경로
        mcp_status: MCP 서버 연결 상태
        
    Returns:
        생성된 응답 텍스트
    """
    global mcp_client, mcp_tools
    
    # 메시지가 비어있는 경우 처리
    if not message or message.strip() == "":
        yield "메시지를 입력해주세요."
        return
    
    # 대화 내역을 Anthropic 형식으로 변환
    messages = []
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        messages.append({"role": "assistant", "content": assistant})
    
    # 현재 사용자 메시지 추가
    messages.append({"role": "user", "content": message})
    
    try:
        # 도구가 연결된 경우에만 tools 매개변수 추가
        api_params = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 1000,
            "messages": messages,
            "stream": True
        }
        
        if mcp_client and mcp_tools:
            api_params["tools"] = mcp_tools
            print(f"도구 정보 포함: {len(mcp_tools)}개")
        
        # 현재 메시지와 도구 호출 추적을 위한 변수
        current_message = ""
        should_continue = True
        
        while should_continue:
            # 처음 응답을 받기 전에 API 호출 정보 출력
            print(f"Claude API 호출 시작 - 메시지 수: {len(messages)}")
            
            try:
                # Claude API 호출
                stream = client.messages.create(**api_params)
                
                # 스트리밍 응답 처리
                chunks = []
                tool_calls = None
                
                print("스트림 처리 시작")
                for chunk in stream:
                    # 청크 타입 확인 및 텍스트 델타 처리
                    if chunk.type == "content_block_delta" and hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                        text = chunk.delta.text or ""
                        chunks.append(text)
                        current_message = "".join(chunks)
                        yield current_message
                    
                    # 메시지 종료 이벤트 처리
                    elif chunk.type == "message_stop":
                        print(f"메시지 종료 이벤트 감지: {chunk}")
                        # 메시지에 도구 사용 정보가 있는지 확인
                        if hasattr(chunk, "message"):
                            print("메시지 속성 있음")
                            if hasattr(chunk.message, "stop_reason") and chunk.message.stop_reason == "tool_use":
                                print("도구 사용 이유로 메시지 종료됨")
                                if hasattr(chunk.message, "content") and len(chunk.message.content) > 0:
                                    content = chunk.message.content[0]
                                    if hasattr(content, "tool_calls"):
                                        print("도구 호출 정보 발견")
                                        tool_calls = content.tool_calls
                        break
                
                # 도구 호출이 없는 경우 종료
                if not tool_calls:
                    print("도구 호출 없음 - 응답 완료")
                    should_continue = False
                    break
                
                print(f"도구 호출 감지: {tool_calls}")
                
                # 도구 호출 처리
                tool_results = await handle_tool_calls(tool_calls)
                
                # 도구 실행 결과를 메시지 리스트에 추가
                messages.append({
                    "role": "assistant",
                    "content": [{"type": "tool_calls", "tool_calls": tool_calls}]
                })
                
                # 단일 도구 결과인 경우 리스트로 변환
                if not isinstance(tool_results, list):
                    tool_results = [tool_results]
                
                # 도구 실행 결과 메시지 추가
                for result in tool_results:
                    messages.append({
                        "role": "user", 
                        "content": [result]
                    })
                
                # 현재까지의 응답 표시
                yield current_message + "\n\n[도구 사용 중...]\n"
                
                # API 파라미터 업데이트 (도구 정보는 그대로 유지)
                api_params["messages"] = messages
                
            except Exception as api_error:
                print(f"API 호출 중 오류 발생: {str(api_error)}")
                yield f"API 오류가 발생했습니다: {str(api_error)}"
                should_continue = False
        
    except Exception as e:
        print(f"전체 처리 중 오류 발생: {str(e)}")
        yield f"오류가 발생했습니다: {str(e)}"

# Gradio 인터페이스 설정
with gr.Blocks(theme="soft") as demo:
    gr.Markdown("# Claude 챗봇 + MCP 도구 통합")
    gr.Markdown("Anthropic의 Claude 3.7 Sonnet 모델과 MCP 서버의 도구를 통합한 대화형 인터페이스입니다.")
    
    with gr.Row():
        with gr.Column(scale=4):
            mcp_server_path = gr.Textbox(
                label="MCP 서버 경로",
                placeholder="MCP 서버 실행 파일 경로를 입력하세요 (예: ./my_mcp_server.py)",
                interactive=True
            )
        with gr.Column(scale=1):
            connect_button = gr.Button("연결")
        with gr.Column(scale=1):
            mcp_status = gr.Textbox(label="연결 상태", value="연결되지 않음", interactive=False)
    
    connect_result = gr.Textbox(label="연결 결과", interactive=False)
    
    chatbot = gr.ChatInterface(
        fn=predict,
        additional_inputs=[mcp_server_path, mcp_status],
        examples=[
            ["안녕하세요!", "", ""],
            ["파이썬으로 간단한 웹 서버를 만드는 방법을 알려주세요.", "", ""]
        ],
        title="",
    )
    
    # 연결 버튼 클릭 이벤트 처리
    connect_button.click(
        fn=connect_to_mcp_server,
        inputs=[mcp_server_path],
        outputs=[connect_result, mcp_status]
    )

if __name__ == "__main__":
    # Gradio 앱 실행
    try:
        demo.launch()
    finally:
        # 앱 종료 시 MCP 클라이언트가 존재하면 정리
        if 'mcp_client' in globals() and mcp_client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(mcp_client.__aexit__(None, None, None))
            except:
                pass 