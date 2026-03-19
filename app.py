import streamlit as st
import requests
import json
import re  # 导入正则表达式库，用于修复 Markdown 格式

# ================== 1. 页面配置与美化 ==================
st.set_page_config(
    page_title="实习生入职小助手",
    page_icon="🎓",
    layout="centered"
)

# 自定义 CSS 让聊天气泡更美观
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stMarkdown p { line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎓 实习生入职小助手")
st.caption("基于 Dify 工作流驱动的智能入职指引")
st.markdown("---")

# ================== 2. API 配置 (从 Secrets 读取) ==================
# 请确保在 Streamlit Cloud 的 Settings -> Secrets 中配置了这两个键
DIFY_API_KEY = st.secrets.get("DIFY_API_KEY", "")
DIFY_BASE_URL = st.secrets.get("DIFY_BASE_URL", "https://api.dify.ai/v1")

if not DIFY_API_KEY:
    st.error("❌ 未检测到 DIFY_API_KEY。请在 Streamlit Secrets 中配置。")
    st.stop()

# ================== 3. Session State 初始化 ==================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


# ================== 4. 核心功能函数 ==================

def format_markdown(text):
    """
    针对 Streamlit 渲染优化 Markdown 格式
    """
    # 1. 修复列表：确保数字序号 (1. 2.) 后面有空格
    text = re.sub(r'(\d+\.)([^\s])', r'\1 \2', text)
    # 2. 修复列表：确保横杠列表 (- ) 后面有空格
    text = re.sub(r'(\-)([^\s])', r'\1 \2', text)
    # 3. 增强换行：将单换行符替换为双换行符，强制 Markdown 识别段落
    # 但要避免对已有的双换行符进行重复操作
    text = text.replace('\n', '\n\n').replace('\n\n\n', '\n\n')
    return text


def fetch_dify_stream(query, conversation_id=None):
    url = f"{DIFY_BASE_URL}/chat-messages"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "user": "streamlit_user",
        "conversation_id": conversation_id or ""
    }
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        return response
    except Exception as e:
        st.error(f"⚠️ 连接 Dify 失败: {str(e)}")
        return None


def process_stream_response(response, message_placeholder):
    full_response = ""
    new_conversation_id = None

    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data:"):
                try:
                    chunk = json.loads(decoded_line[5:])
                    event = chunk.get("event")

                    if event == "message":
                        full_response += chunk.get("answer", "")
                        # 实时修复格式并渲染
                        display_text = format_markdown(full_response)
                        message_placeholder.markdown(display_text + "▌")

                    elif event == "message_end":
                        new_conversation_id = chunk.get("conversation_id")
                except:
                    continue

    # 最终渲染去掉光标
    message_placeholder.markdown(format_markdown(full_response))
    return full_response, new_conversation_id


# ================== 5. 聊天界面逻辑 ==================

# 渲染历史记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(format_markdown(message["content"]))

# 用户输入
if prompt := st.chat_input("您可以问：入职需要准备哪些材料？"):
    # 展示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 展示 AI 回复
    with st.chat_message("assistant"):
        placeholder = st.empty()
        response = fetch_dify_stream(prompt, st.session_state.conversation_id)

        if response:
            final_ans, new_cid = process_stream_response(response, placeholder)
            if final_ans:
                st.session_state.messages.append({"role": "assistant", "content": final_ans})
                st.session_state.conversation_id = new_cid

# ================== 6. 侧边栏 ==================
with st.sidebar:
    st.header("⚙️ 会话管理")
    if st.button("🗑️ 清空对话历史"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()

    st.markdown("---")
    st.info("""
    **使用提示：**
    如果发现 AI 回答没有换行，请尝试重新提问或点击“清空对话”。
    """)