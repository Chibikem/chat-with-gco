import os
import time
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from memory import save_fact, build_system_prompt, extract_memory, save_session, get_all_sessions, load_session

load_dotenv()
st.write(f"DEBUG - Redis URL length: {len(os.getenv('REDIS_URL', 'MISSING'))}")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

st.title("💬 GCO's Chatbot")
st.caption("Your AI companion that remembers what matters to you.")

user_id = "demo_user"

if "session_id" not in st.session_state:
    st.session_state.session_id = str(int(time.time()))
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("💬 Past Chats")

    if st.button("➕ New Chat"):
        st.session_state.session_id = str(int(time.time()))
        st.session_state.messages = []
        st.rerun()

    st.divider()

    past_sessions = get_all_sessions(user_id)
    for sid in past_sessions:
        label = time.strftime("%b %d, %I:%M %p", time.localtime(int(sid)))
        if st.button(label, key=f"session_{sid}"):
            st.session_state.session_id = sid
            st.session_state.messages = load_session(user_id, sid)
            st.rerun()


def chat(user_input):
    system_prompt = build_system_prompt(user_id)
    full_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages[-10:]
    full_messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_messages
    )
    reply = response.choices[0].message.content

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": reply})
    return reply


for msg in st.session_state.messages:
    avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if prompt := st.chat_input("Say something..."):
    st.chat_message("user", avatar="🧑‍💻").write(prompt)
    reply = chat(prompt)
    st.chat_message("assistant", avatar="🤖").write(reply)

    new_facts = extract_memory(prompt)
    for k, v in new_facts.items():
        save_fact(user_id, k, str(v))

    save_session(user_id, st.session_state.session_id, st.session_state.messages)