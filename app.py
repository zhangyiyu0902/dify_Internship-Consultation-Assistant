import streamlit as st
import requests
import json
import re

# ================== 1. 页面配置 ==================
st.set_page_config(
    page_title="实习生入职小助手",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 实习生入职小助手")
st.markdown("---")

# ================== 2. API 配置 ==================
# 修改点：将默认URL从公网地址改为内网地址
DIFY_API_KEY = st.secrets.get("DIFY_API_KEY", "app-ADmZYJd0twdGWCC7DzL2Bs7L")
DIFY_BASE_URL = st.secrets.get("DIFY_BASE_URL", "http://10.101.50.17/v1")  # 修改这里

# ================== 3. Session State 初始化 ==================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


# ================== 4. 格式化工具 ==================
def format_md(text):
    """
    强制修复 Markdown 格式：确保分点序号后面有空格，且有换行。
    """
    # 确保 1. 后面有空格
    text = re.sub(r'(\d\.)([^\s])', r'\1 \2', text)
    # 确保 - 后面有空格
    text = re.sub(r'(\-)([^\s])', r'\1 \2', text)
    # 增加双换行以确保分段
    return text.replace("\n", "\n\n").replace("\n\n\n", "\n\n")


# ================== 5. Dify API 调用 ==================
def fetch_dify_stream(query, conversation_id=None):
    # 注意：这里会自动使用修改后的 DIFY_BASE_URL
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
        return requests.post(url, headers=headers, json=payload, stream=True)
    except Exception as e:
        st.error(f"❌ 连接失败: {str(e)}")
        return None


# ================== 6. 聊天界面逻辑 ==================

# 【核心：首先渲染所有历史对话】
# 这样即使在 AI 思考时，之前的聊天内容也会稳稳地留在屏幕上
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(format_md(message["content"]))

# 【处理新输入】
if prompt := st.chat_input("入职材料有哪些？"):
    # 1. 用户提问展示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI 回复展示
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        response = fetch_dify_stream(prompt, st.session_state.conversation_id)

        if response:
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data:"):
                        try:
                            chunk = json.loads(decoded[5:])
                            if chunk.get("event") == "message":
                                answer = chunk.get("answer", "")
                                full_response += answer
                                # 实时渲染修复后的 Markdown
                                placeholder.markdown(format_md(full_response) + "▌")

                            elif chunk.get("event") == "message_end":
                                # 保存会话 ID
                                st.session_state.conversation_id = chunk.get("conversation_id")
                        except:
                            continue

            # 渲染最终版本并保存
            final_content = format_md(full_response)
            placeholder.markdown(final_content)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

# ================== 7. 侧边栏 ==================
with st.sidebar:
    st.subheader("会话管理")
    if st.button("🚀 开启新对话"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()