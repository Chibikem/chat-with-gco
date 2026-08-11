import os
import time
import streamlit as st
from tools import generate_image
from openai import OpenAI
from dotenv import load_dotenv
from memory import (
    save_fact, build_system_prompt, extract_memory,
    save_session, get_all_sessions, load_session,
    get_user_memory, clear_user_data,
    generate_title, save_session_title, get_all_session_titles,
    delete_session
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.gco-header {
    padding: 0.5rem 0 1.2rem 0;
}
.gco-title {
    font-family: 'Fraunces', serif;
    font-weight: 700;
    font-size: 2.4rem;
    color: #1B2A4A;
    margin-bottom: 0.2rem;
}
.gco-underline {
    width: 64px;
    height: 4px;
    background: #C9A227;
    border-radius: 2px;
    margin-bottom: 0.7rem;
}
.gco-caption {
    color: #6B7280;
    font-size: 1rem;
}

[data-testid="stChatMessage"] {
    border-radius: 14px;
    padding: 0.4rem 0.6rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 1px 3px rgba(27,42,74,0.08);
}

[data-testid="stSidebar"] {
    background-color: #F7F3E9;
    border-right: 1px solid #E8E0CC;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    font-family: 'Fraunces', serif;
    color: #1B2A4A;
}

button[kind="secondary"], .stButton button {
    border-radius: 10px !important;
    border: 1px solid #C9A227 !important;
    color: #1B2A4A !important;
}
.stButton button:hover {
    background-color: #C9A227 !important;
    color: #FFFFFF !important;
}
</style>

<div class="gco-header">
    <div class="gco-title">💬 Chat with GCO</div>
    <div class="gco-underline"></div>
    <div class="gco-caption">Your AI companion that remembers what matters to you — powered by Groq, so it thinks fast.</div>
</div>
""", unsafe_allow_html=True)

user_id = "demo_user"

if "session_id" not in st.session_state:
    st.session_state.session_id = str(int(time.time()))
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar ---
with st.sidebar:
    st.header("💬 Past Chats")

    if st.button("➕ New Chat"):
        st.session_state.session_id = str(int(time.time()))
        st.session_state.messages = []
        st.rerun()

    st.divider()

    past_sessions = get_all_sessions(user_id)
    session_titles = get_all_session_titles(user_id)

    for sid in past_sessions:
        label = session_titles.get(sid, time.strftime("%b %d, %I:%M %p", time.localtime(int(sid))))
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(label, key=f"session_{sid}", use_container_width=True):
                st.session_state.session_id = sid
                st.session_state.messages = load_session(user_id, sid)
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{sid}"):
                delete_session(user_id, sid)
                if st.session_state.session_id == sid:
                    st.session_state.session_id = str(int(time.time()))
                    st.session_state.messages = []
                st.rerun()

    st.divider()
    st.subheader("🔒 Your Privacy")
    st.caption("GCO remembers facts you share to make future chats better.")

    if st.button("🗑️ Clear my data"):
        st.session_state.confirm_clear = True

    if st.session_state.get("confirm_clear"):
        st.warning("This deletes everything GCO remembers about you, permanently.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, clear it"):
                clear_user_data(user_id)
                st.session_state.messages = []
                st.session_state.session_id = str(int(time.time()))
                st.session_state.confirm_clear = False
                st.success("All your data has been cleared.")
                time.sleep(1)
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state.confirm_clear = False
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


def after_message_save():
    save_session(user_id, st.session_state.session_id, st.session_state.messages)
    if len(st.session_state.messages) == 2:
        title = generate_title(st.session_state.messages[0]["content"])
        save_session_title(user_id, st.session_state.session_id, title)


# --- Warm intro on empty chat ---
if not st.session_state.messages:
    st.chat_message("assistant", avatar="🤖").write(
        "Hey, I'm GCO 👋 I remember what you tell me, so the more we talk, the more helpful I get. What's on your mind?"
    )

    st.write("Or try one of these:")
    col1, col2, col3 = st.columns(3)
    starter_clicked = None
    with col1:
        if st.button("Tell me about yourself"):
            starter_clicked = "Tell me a bit about yourself."
    with col2:
        if st.button("What do you remember about me?"):
            starter_clicked = "What do you remember about me so far?"
    with col3:
        if st.button("Help me think through something"):
            starter_clicked = "I want to think through something with you."

    if starter_clicked:
        st.chat_message("user", avatar="🧑‍💻").write(starter_clicked)
        with st.spinner("💭 GCO is thinking..."):
            reply = chat(starter_clicked)
        st.chat_message("assistant", avatar="🤖").write(reply)

        facts_before = set(get_user_memory(user_id).keys())
        new_facts = extract_memory(starter_clicked)
        for k, v in new_facts.items():
            save_fact(user_id, k, str(v))
        facts_after = set(get_user_memory(user_id).keys())
        newly_saved = facts_after - facts_before
        if newly_saved:
            st.toast(f"🧠 Remembered: {', '.join(newly_saved)}", icon="🧠")

        after_message_save()
        st.rerun()

# --- Display existing conversation ---
for msg in st.session_state.messages:
    avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

# --- Chat input ---
if prompt := st.chat_input("Say something... (try /image a sunset over mountains)"):
    st.chat_message("user", avatar="🧑‍💻").write(prompt)

    if prompt.lower().startswith("/image "):
        image_prompt = prompt[7:]
        with st.spinner("🎨 GCO is creating your image..."):
            image_data = generate_image(image_prompt)
        if image_data:
            st.chat_message("assistant", avatar="🤖").image(image_data, caption=image_prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": f"[Generated image: {image_prompt}]"})
        else:
            st.chat_message("assistant", avatar="🤖").write("Sorry, I couldn't generate that image — try rephrasing it.")
    else:
        with st.spinner("💭 GCO is thinking..."):
            reply = chat(prompt)
        st.chat_message("assistant", avatar="🤖").write(reply)

        facts_before = set(get_user_memory(user_id).keys())
        new_facts = extract_memory(prompt)
        for k, v in new_facts.items():
            save_fact(user_id, k, str(v))
        facts_after = set(get_user_memory(user_id).keys())
        newly_saved = facts_after - facts_before
        if newly_saved:
            st.toast(f"🧠 Remembered: {', '.join(newly_saved)}", icon="🧠")

    after_message_save()

    facts_before = set(get_user_memory(user_id).keys())
    new_facts = extract_memory(prompt)
    for k, v in new_facts.items():
        save_fact(user_id, k, str(v))
    facts_after = set(get_user_memory(user_id).keys())
    newly_saved = facts_after - facts_before
    if newly_saved:
        st.toast(f"🧠 Remembered: {', '.join(newly_saved)}", icon="🧠")

    after_message_save()