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
        
        # 도구 정보 출력
        print(f"도구 정보 디버깅: {tool_info}")
        
        # 필드 이름은 camelCase와 snake_case 모두 지원하기 위해 두 가지 버전을 확인
        input_schema = None
        if hasattr(tool_info, "inputSchema"):
            input_schema = tool_info.inputSchema
            print(f"inputSchema(camelCase) 발견: {input_schema}")
        elif hasattr(tool_info, "input_schema"):
            input_schema = tool_info.input_schema
            print(f"input_schema(snake_case) 발견: {input_schema}")
        
        # input_schema가 있는 경우 처리
        if input_schema:
            if isinstance(input_schema, dict):
                # 중간 디버깅 정보 출력
                print(f"input_schema 내용: {input_schema}")
                
                # properties 가져오기
                if "properties" in input_schema:
                    properties = input_schema["properties"]
                    print(f"properties 발견: {properties}")
                
                # required 가져오기
                if "required" in input_schema:
                    required = input_schema["required"]
                    print(f"required 발견: {required}")
        
        # 파라미터가 있는 경우 처리 (파이썬 타입 어노테이션 기반)
        parameters = getattr(tool_info, "parameters", None)
        if parameters and not properties:
            print(f"파라미터 발견: {len(parameters)}개")
            for param in parameters:
                param_name = getattr(param, "name", "")
                param_type = "string"  # 기본값
                param_desc = getattr(param, "description", "")
                param_required = getattr(param, "required", False)
                
                print(f"파라미터 분석: {param_name}, 타입: {getattr(param, 'type', 'unknown')}")
                
                # 매개변수 유형 매핑
                if hasattr(param, "type"):
                    if param.type == "string" or param.type == "str":
                        param_type = "string"
                    elif param.type in ["integer", "int"]:
                        param_type = "integer"
                    elif param.type in ["number", "float"]:
                        param_type = "number"
                    elif param.type == "boolean" or param.type == "bool":
                        param_type = "boolean"
                    elif param.type in ["array", "list"]:
                        param_type = "array"
                    elif param.type == "object" or param.type == "dict":
                        param_type = "object"
                        
                # 매개변수 정의 생성
                param_def = {
                    "type": param_type,
                    "description": param_desc
                }
                
                # 배열 유형인 경우 items 추가
                if param_type == "array":
                    param_def["items"] = {"type": "string"}
                    
                # enum 값이 있는 경우 추가
                if hasattr(param, "enum") and param.enum:
                    param_def["enum"] = param.enum
                    
                properties[param_name] = param_def
                
                # 필수 매개변수 처리
                if param_required:
                    required.append(param_name)
        
        # 함수 시그니처에서 파라미터 추출 (파라미터 리스트가 없는 경우)
        if not properties and hasattr(tool_info, "signature"):
            print(f"함수 시그니처 발견: {tool_info.signature}")
            signature = tool_info.signature
            
            if hasattr(signature, "parameters"):
                sig_params = signature.parameters
                for param_name, param_info in sig_params.items():
                    # self 파라미터 제외
                    if param_name == "self":
                        continue
                        
                    param_type = "string"  # 기본값
                    param_desc = f"{param_name} 파라미터"
                    
                    # 파라미터 타입 추론
                    if hasattr(param_info, "annotation") and param_info.annotation != param_info.empty:
                        annotation = param_info.annotation
                        if annotation == str:
                            param_type = "string"
                        elif annotation == int:
                            param_type = "integer"
                        elif annotation == float:
                            param_type = "number"
                        elif annotation == bool:
                            param_type = "boolean"
                        elif annotation == list:
                            param_type = "array"
                        elif annotation == dict:
                            param_type = "object"
                    
                    # 매개변수 정의 생성
                    param_def = {
                        "type": param_type,
                        "description": param_desc
                    }
                    
                    properties[param_name] = param_def
                    
                    # 기본값이 없는 파라미터는 필수로 간주
                    if param_info.default == param_info.empty:
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
        print(f"매개변수: {properties}")
        print(f"필수 필드: {required}")
        return claude_tool
    except Exception as e:
        print(f"도구 변환 오류: {str(e)}")
        import traceback
        traceback.print_exc()
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
        도구 실행 결과와 이미지 데이터(있는 경우)
    """
    global mcp_client
    
    # MCP 클라이언트 연결 상태 확인
    if not mcp_client:
        return {
            "type": "tool_result",
            "tool_use_id": getattr(tool_calls[0], "id", "unknown_id"),
            "content": "MCP 서버가 연결되지 않았습니다.",
            "is_error": True
        }, None
    
    results = []
    image_data = None
    
    for tool_call in tool_calls:
        try:
            tool_name = tool_call.name
            tool_use_id = getattr(tool_call, "id", "unknown_id")
            tool_input = getattr(tool_call, "input", {})
            
            # JSON 문자열 형태인 경우 딕셔너리로 변환
            if isinstance(tool_input, str):
                tool_input = json.loads(tool_input)
            
            print(f"도구 호출: {tool_name}, ID: {tool_use_id}, 입력: {tool_input}")
            
            # MCP 클라이언트를 통해 도구 호출
            result = await mcp_client.call_tool(tool_name, tool_input)
            
            print(f"도구 호출 결과 타입: {type(result)}")
            
            # 도구 실행 결과를 Claude API 형식으로 변환
            # 텍스트 및 이미지 컨텐츠 처리
            result_content = ""
            
            # 이미지 데이터 있는지 확인 (배열인 경우)
            if isinstance(result, list):
                print(f"결과 리스트 길이: {len(result)}")
                for i, item in enumerate(result):
                    print(f"결과 항목 {i} 타입: {type(item)}")
                    # TextContent 처리
                    if hasattr(item, "type") and item.type == "text":
                        print(f"텍스트 콘텐츠 발견: {item.text[:50]}...")
                        result_content += item.text + "\n"
                    
                    # ImageContent 처리
                    if hasattr(item, "type") and item.type == "image":
                        print(f"이미지 콘텐츠 발견")
                        # 이미지 데이터 추출
                        if hasattr(item, "data"):
                            print(f"이미지 데이터 길이: {len(item.data[:50])}...")
                            image_data = {
                                "data": item.data,
                                "mime_type": getattr(item, "mimeType", "image/jpeg")
                            }
            else:
                # 단일 결과인 경우
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
                "tool_use_id": tool_use_id,
                "content": result_content
            })
        except Exception as e:
            print(f"도구 호출 처리 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "type": "tool_result",
                "tool_use_id": getattr(tool_call, "id", "unknown_id") if 'tool_call' in locals() else "unknown_id",
                "content": f"도구 실행 오류: {str(e)}",
                "is_error": True
            })
    
    # 결과와 이미지 데이터 반환
    return results[0] if len(results) == 1 else results, image_data

async def predict(message, history, mcp_server_path, mcp_status, image_output):
    """
    사용자 메시지에 대한 응답을 생성합니다.
    
    Args:
        message: 사용자의 메시지
        history: 지금까지의 대화 내역 (튜플 형식)
        mcp_server_path: MCP 서버 경로
        mcp_status: MCP 서버 연결 상태
        image_output: 이미지 출력 컴포넌트
        
    Returns:
        생성된 응답 텍스트와 이미지 데이터(있는 경우)
    """
    global mcp_client, mcp_tools
    
    # 메시지가 비어있는 경우 처리
    if not message or message.strip() == "":
        return "메시지를 입력해주세요.", None
    
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
            "messages": messages
        }
        
        if mcp_client and mcp_tools:
            api_params["tools"] = mcp_tools
            print(f"도구 정보 포함: {len(mcp_tools)}개")
        
        # 응답 처리를 위한 변수
        full_response = ""
        should_continue = True
        final_image = None
        
        while should_continue:
            # API 호출 정보 출력
            print(f"Claude API 호출 시작 - 메시지 수: {len(messages)}")
            
            try:
                # Claude API 호출
                response = client.messages.create(**api_params)
                
                # 일반 텍스트 응답 처리
                text_content = ""
                tool_use_blocks = []
                
                # 응답 내용 분석
                if hasattr(response, "content"):
                    for content_block in response.content:
                        if hasattr(content_block, "type"):
                            if content_block.type == "text":
                                text_content += content_block.text
                            elif content_block.type == "tool_use":
                                tool_use_blocks.append(content_block)
                
                # 현재까지의 응답 업데이트
                if text_content:
                    full_response += text_content
                
                # 도구 호출이 없는 경우 종료
                if not tool_use_blocks or not hasattr(response, "stop_reason") or response.stop_reason != "tool_use":
                    print("도구 호출 없음 - 응답 완료")
                    should_continue = False
                    return full_response, final_image
                
                print(f"도구 호출 감지: {len(tool_use_blocks)}개")
                
                # 도구 호출 처리 (이미지 데이터도 함께 반환)
                tool_results, image_data = await handle_tool_calls(tool_use_blocks)
                
                # 이미지 데이터가 있으면 저장
                if image_data:
                    final_image = (image_data["data"], image_data["mime_type"])
                
                # 도구 실행 결과를 메시지에 추가
                tool_use_message = {
                    "role": "assistant",
                    "content": []
                }
                
                # 텍스트 내용이 있으면 추가
                if text_content:
                    tool_use_message["content"].append({"type": "text", "text": text_content})
                
                # 도구 사용 블록 추가
                for tool_use in tool_use_blocks:
                    tool_use_message["content"].append(tool_use)
                
                messages.append(tool_use_message)
                
                # 단일 도구 결과인 경우 리스트로 변환
                if not isinstance(tool_results, list):
                    tool_results = [tool_results]
                
                # 도구 결과 메시지 추가
                for result in tool_results:
                    messages.append({
                        "role": "user", 
                        "content": [result]
                    })
                
                # API 파라미터 업데이트
                api_params["messages"] = messages
                
                # 도구 사용 중임을 표시
                full_response += "\n\n[도구 사용 중...]\n"
                
            except Exception as api_error:
                print(f"API 호출 중 오류 발생: {str(api_error)}")
                return f"API 오류가 발생했습니다: {str(api_error)}", None
        
        return full_response, final_image
        
    except Exception as e:
        print(f"전체 처리 중 오류 발생: {str(e)}")
        return f"오류가 발생했습니다: {str(e)}", None

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
            connect_button = gr.Button("연결", variant="primary")
        with gr.Column(scale=1):
            mcp_status = gr.Textbox(label="연결 상태", value="연결되지 않음", interactive=False)
    
    connect_result = gr.Textbox(label="연결 결과", interactive=False)
    
    with gr.Row():
        with gr.Column(scale=3):
            # 채팅 인터페이스
            chatbot = gr.Chatbot(
                height=500, 
                type="messages",
                show_copy_button=True,
                avatar_images=("👤", "🤖")
            )
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="메시지를 입력하세요...",
                    show_label=False,
                    container=False,
                    scale=9
                )
                submit_btn = gr.Button("전송", variant="primary", scale=1)
            clear_btn = gr.Button("대화 초기화", variant="secondary")
        
        with gr.Column(scale=2, visible=True):
            # 이미지 표시 영역
            gr.Markdown("### 생성된 이미지")
            image_output = gr.Image(
                type="filepath", 
                label="생성된 이미지",
                height=400,
                container=True
            )
            gr.Markdown("""
            **이미지 생성 프롬프트 예시:**
            - "아름다운 장미꽃, 선명한 빨간색"
            - "바다 풍경, 일몰, 아름다운 노을"
            - "귀여운 강아지, 웰시코기"
            """)

    # 이벤트 핸들러 함수
    def user_input(message, history):
        # messages 형식으로 변환 (role/content 구조)
        if message.strip() != "":
            return "", history + [{"role": "user", "content": message}]
        return "", history
    
    async def bot_response(history, mcp_server_path, mcp_status, image_output):
        if history and history[-1]["role"] == "user":
            user_message = history[-1]["content"]
            
            # 이전 대화 내역을 튜플 형식으로 변환 (predict 함수 호환성 유지)
            previous_pairs = []
            for i in range(0, len(history) - 1):
                if history[i]["role"] == "user" and i+1 < len(history) and history[i+1]["role"] == "assistant":
                    previous_pairs.append((history[i]["content"], history[i+1]["content"]))
            
            # 응답 생성
            bot_message, image_data = await predict(user_message, previous_pairs, mcp_server_path, mcp_status, image_output)
            
            # 응답 추가
            history.append({"role": "assistant", "content": bot_message})
            
            # 이미지 데이터가 있으면 이미지 컴포넌트 업데이트
            if image_data:
                base64_data, mime_type = image_data
                if mime_type.startswith("image/"):
                    # Base64 이미지 데이터 디코딩
                    import base64
                    import tempfile
                    
                    # 임시 파일에 이미지 저장
                    img_bytes = base64.b64decode(base64_data)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                        f.write(img_bytes)
                        temp_img_path = f.name
                    
                    return history, temp_img_path
            
            return history, None
        return history, None
    
    # 메시지 초기화 함수
    def clear_history():
        return [], None
    
    # 이벤트 연결
    msg.submit(user_input, [msg, chatbot], [msg, chatbot]).then(
        bot_response, [chatbot, mcp_server_path, mcp_status, image_output], [chatbot, image_output]
    )
    
    submit_btn.click(user_input, [msg, chatbot], [msg, chatbot]).then(
        bot_response, [chatbot, mcp_server_path, mcp_status, image_output], [chatbot, image_output]
    )
    
    clear_btn.click(clear_history, [], [chatbot, image_output])
    
    # 서버 연결 버튼 클릭 이벤트 처리
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