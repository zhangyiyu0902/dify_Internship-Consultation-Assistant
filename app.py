import streamlit as st
import requests
import json
import time

# ================== 1. 基础配置与界面美化 ==================
st.set_page_config(
    page_title="实习生入职小助手",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 实习生入职小助手")
st.markdown("---")

# ================== 2. API 配置 (核心部分) ==================
# 建议：本地测试可直接填入，部署到 Streamlit Cloud 时请使用 Secrets 管理
# https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

# 👈👈👈 请在此处填入你的 Dify API 配置 👈👈👈
DIFY_API_KEY = st.secrets.get("DIFY_API_KEY", "sk-YOUR_ACTUAL_DIFY_API_KEY_HERE")
DIFY_BASE_URL = st.secrets.get("DIFY_BASE_URL", "https://api.dify.ai/v1")

# 检查 Key 是否配置
if DIFY_API_KEY == "sk-YOUR_ACTUAL_DIFY_API_KEY_HERE" or not DIFY_API_KEY:
    st.error("⚠️ 未配置 Dify API Key。请在代码中修改或在 Streamlit Secrets 中设置 `DIFY_API_KEY`。")
    st.stop()

# ================== 3. Session State 初始化 ==================
# 用于存储聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 用于存储 Dify 的会话 ID (实现多轮对话记忆)
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


# ================== 4. Dify API 调用函数 (流式) ==================
def fetch_dify_stream(query, conversation_id=None):
    """
    调用 Dify Chat-Messages API (streaming 模式)
    """
    url = f"{DIFY_BASE_URL}/chat-messages"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": {},  # 如果 Dify 应用有变量，填在这里
        "query": query,
        "response_mode": "streaming",
        "user": "streamlit_user",  # 必须参数，区分用户
        "conversation_id": conversation_id or ""  # 核心：传入 ID 实现记忆
    }

    try:
        # 发送 POST 请求，开启 stream=True
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API 连接失败: {str(e)}")
        return None


def process_stream_response(response, message_placeholder):
    """
    解析 Dify 返回的 SSE 流数据并实时渲染到界面
    """
    full_response = ""
    new_conversation_id = None

    # 迭代读取流数据
    for line in response.iter_lines():
        if line:
            # 解码行数据
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data:"):
                json_str = decoded_line[5:]  # 去掉 "data:" 前缀
                try:
                    chunk = json.loads(json_str)
                    event_type = chunk.get("event")

                    # 只有当事件类型为 'message' 时才包含文本
                    if event_type == "message":
                        answer_piece = chunk.get("answer", "")
                        full_response += answer_piece
                        # 实时更新 Streamlit 界面上的文本
                        message_placeholder.markdown(full_response + "▌")

                    # 当对话结束时，获取最终的 conversation_id
                    elif event_type == "message_end":
                        new_conversation_id = chunk.get("conversation_id")

                except json.JSONDecodeError:
                    continue

    # 移除光标符号
    message_placeholder.markdown(full_response)
    return full_response, new_conversation_id


# ================== 5. 界面渲染逻辑 ==================

# 渲染历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理用户输入
if prompt := st.chat_input("在这里输入您的问题..."):
    # 1. 添加用户消息到历史并渲染
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用 Dify API 并处理流式回复
    with st.chat_message("assistant"):
        # 创建一个空占位符，用于实时填入 AI 的回答
        message_placeholder = st.empty()

        # 2a. 发起请求
        response_stream = fetch_dify_stream(prompt, st.session_state.conversation_id)

        if response_stream:
            # 2b. 解析流并渲染
            final_ans, new_cid = process_stream_response(response_stream, message_placeholder)

            if final_ans:
                # 3. 将 AI 回答添加到历史
                st.session_state.messages.append({"role": "assistant", "content": final_ans})
                # 4. 更新会话 ID (核心：保存记忆)
                if new_cid:
                    st.session_state.conversation_id = new_cid

# ================== 6. 底部工具栏 (可选) ==================
with st.sidebar:
    st.subheader("会话管理")
    st.write(f"当前会话 ID: `{st.session_state.conversation_id or '新对话'}`")
    if st.button("🚀 开启新对话"):
        # 清空所有状态
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()  # 重新运行 App

    st.markdown("---")
    st.info("基于 Dify 对话流 API 和 Streamlit 构建。")