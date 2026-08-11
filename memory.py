import os
import json
import time
import redis
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

r = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)


def save_fact(user_id, key, value):
    r.hset(f"user:{user_id}", key, str(value))


def get_user_memory(user_id):
    return r.hgetall(f"user:{user_id}")


def build_system_prompt(user_id):
    memory = get_user_memory(user_id)
    base_identity = "You are GCO, a warm and helpful AI companion who remembers what matters to the people you talk to."
    if memory:
        facts = "\n".join([f"- {k}: {v}" for k, v in memory.items()])
        return f"{base_identity}\nKnown facts about this user:\n{facts}"
    return base_identity


def extract_memory(conversation_snippet):
    prompt = f"""Extract any facts about the user worth remembering long-term
(preferences, personal details, recurring topics). Return as JSON key-value pairs,
or an empty object if nothing is worth saving.

Conversation: {conversation_snippet}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)


def save_session(user_id, session_id, messages):
    r.set(f"session:{user_id}:{session_id}", json.dumps(messages))
    r.zadd(f"sessions:{user_id}", {session_id: time.time()})


def get_all_sessions(user_id):
    return r.zrevrange(f"sessions:{user_id}", 0, -1)


def load_session(user_id, session_id):
    data = r.get(f"session:{user_id}:{session_id}")
    return json.loads(data) if data else []