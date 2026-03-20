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
DIFY_API_KEY = "app-ADmZYJd0twdGWCC7DzL2Bs7L"  # 你的 Dify API 密钥
DIFY_BASE_URL = "http://10.101.50.17/v1"  # 内网地址
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

# 渲染所有历史对话
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(format_md(message["content"]))

# 处理新输入
if prompt := st.chat_input("入职材料有哪些？"):
    # 1. 用户提问展示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI 回复展示
    with st.chat_message("assistant"):
        # --- 新增：显示思考状态 ---
        with st.status("🔍 正在检索知识库并思考...", expanded=True) as status:
            placeholder = st.empty()
            full_response = ""

            response = fetch_dify_stream(prompt, st.session_state.conversation_id)

            if response:
                # 只要 API 有响应并开始迭代，就代表思考结束，准备输出
                for line in response.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith("data:"):
                            try:
                                # 第一次收到有效数据时，更新状态栏
                                if not full_response:
                                    status.update(label="✅ 思考完成，正在生成回答...", state="running", expanded=False)

                                chunk = json.loads(decoded[5:])
                                if chunk.get("event") == "message":
                                    answer = chunk.get("answer", "")
                                    full_response += answer
                                    # 实时渲染
                                    placeholder.markdown(format_md(full_response) + "▌")

                                elif chunk.get("event") == "message_end":
                                    st.session_state.conversation_id = chunk.get("conversation_id")
                            except:
                                continue

                # 回答完成后，彻底隐藏/完成状态栏
                status.update(label="✨ 回答已生成", state="complete", expanded=False)
            else:
                status.update(label="❌ 出错啦，请检查网络", state="error")

        # 渲染最终版本并保存到 session_state
        if full_response:
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