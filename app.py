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

# 使用 CSS 稍微美化一下消息气泡的间距
st.markdown("""
    <style>
    .stChatMessage { margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎓 实习生入职小助手")
st.info("欢迎入职！我是你的 AI 助手，有关入职流程、办公设置的问题都可以问我。")

# ================== 2. API 配置 ==================
# 建议在生产环境使用 st.secrets 存储 API Key
DIFY_API_KEY = st.secrets.get("DIFY_API_KEY", "app-ADmZYJd0twdGWCC7DzL2Bs7L")
DIFY_BASE_URL = "http://10.101.50.17/v1"

# ================== 3. Session State 初始化 ==================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


# ================== 4. 格式化工具 ==================
def format_md(text):
    """
    改进的 Markdown 修复：处理换行符并保留原始格式的整洁。
    """
    if not text: return ""
    # 修复序号后缺少空格的问题 (1.内容 -> 1. 内容)
    text = re.sub(r'(\d\.)([^\s])', r'\1 \2', text)
    # 修复列表符后缺少空格
    text = re.sub(r'(^|\n)([-\*\+])([^\s])', r'\1\2 \3', text)
    return text


# ================== 5. Dify API 调用 ==================
def fetch_dify_stream(query, conversation_id=None):
    url = f"{DIFY_BASE_URL}/chat-messages"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},  # 如果 Dify 工作流有变量，在此添加
        "query": query,
        "response_mode": "streaming",
        "user": "streamlit_user",
        "conversation_id": conversation_id or ""
    }
    try:
        # 设置超时时间，防止内网请求挂起
        return requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
    except requests.exceptions.RequestException as e:
        st.error(f"🌐 网络连接异常: {e}")
        return None


# ================== 6. 聊天界面逻辑 ==================

# 渲染历史对话
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(format_md(message["content"]))

# 处理新输入
if prompt := st.chat_input("入职材料有哪些？"):
    # 展示用户输入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 展示 AI 回复
    with st.chat_message("assistant"):
        # 优化点 1：使用更简洁的状态机逻辑
        full_response = ""
        with st.status("🔍 正在检索知识库...", expanded=True) as status:
            placeholder = st.empty()
            response = fetch_dify_stream(prompt, st.session_state.conversation_id)

            if response and response.status_code == 200:
                for line in response.iter_lines():
                    if not line:
                        continue

                    line_str = line.decode('utf-8')
                    if line_str.startswith("data:"):
                        try:
                            # 过滤掉非 JSON 字符
                            data = json.loads(line_str[5:])
                            event = data.get("event")

                            # 逻辑 A: 收到消息片段
                            if event == "message":
                                if not full_response:  # 收到首字，关闭状态栏收缩
                                    status.update(label="✨ 正在生成回答...", state="running", expanded=False)

                                answer = data.get("answer", "")
                                full_response += answer
                                # 优化点 2：实时渲染使用 Markdown 避免闪烁
                                placeholder.markdown(format_md(full_response) + "▌")

                            # 逻辑 B: 收到引用源 (Dify 知识库特有)
                            elif event == "metadata":
                                # 如果你想展示引用了哪些文档，可以从 data.get("metadata") 里提取
                                pass

                            # 逻辑 C: 消息结束
                            elif event == "message_end":
                                st.session_state.conversation_id = data.get("conversation_id")
                                status.update(label="✅ 回答生成完毕", state="complete")

                            # 逻辑 D: 出现错误
                            elif event == "error":
                                st.error(f"API 报错: {data.get('message')}")

                        except json.JSONDecodeError:
                            continue
            else:
                status.update(label="❌ 无法连接到 Dify 服务", state="error")
                if response: st.error(f"错误码: {response.status_code}")

        # 渲染最终无光标的版本
        if full_response:
            placeholder.markdown(format_md(full_response))
            st.session_state.messages.append({"role": "assistant", "content": full_response})

# ================== 7. 侧边栏 ==================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1042/1042390.png", width=100)  # 加个 Logo
    st.subheader("会话管理")
    if st.button("🚀 开启新对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()

    st.divider()
    st.caption("注：本助手基于内网知识库，信息仅供参考。")