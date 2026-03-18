import json
import time
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st


st.set_page_config(page_title="My AI Chat", layout="wide")
st.title("My AI Chat")

hf_token = st.secrets.get("HF_TOKEN", "").strip()
if not hf_token:
    st.error(
        "Missing Hugging Face token. Add HF_TOKEN to .streamlit/secrets.toml "
        "and restart the app."
    )
    st.stop()

CHATS_DIR = Path("chats")
MEMORY_FILE = Path("memory.json")


def ensure_chats_dir():
    CHATS_DIR.mkdir(parents=True, exist_ok=True)


def chat_file_path(chat_id: str) -> Path:
    return CHATS_DIR / f"{chat_id}.json"


def save_chat(chat: dict) -> None:
    ensure_chats_dir()
    data = {
        "id": chat["id"],
        "title": chat["title"],
        "created_at": chat["created_at"].isoformat(),
        "messages": chat["messages"],
    }
    chat_file_path(chat["id"]).write_text(json.dumps(data, indent=2))


def load_chats() -> dict:
    ensure_chats_dir()
    chats = {}
    for path in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            chat_id = data.get("id") or path.stem
            created_at = data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            else:
                created_at = datetime.now()
            chats[chat_id] = {
                "id": chat_id,
                "title": data.get("title", "New Chat"),
                "created_at": created_at,
                "messages": data.get("messages", []),
            }
        except (OSError, json.JSONDecodeError, ValueError):
            st.warning(f"Skipped unreadable chat file: {path.name}")
    return chats


def delete_chat_file(chat_id: str) -> None:
    path = chat_file_path(chat_id)
    if path.exists():
        path.unlink()


def load_memory() -> dict:
    if not MEMORY_FILE.exists():
        return {}
    try:
        return json.loads(MEMORY_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_memory(memory: dict) -> None:
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))


def merge_memory(existing: dict, updates: dict) -> dict:
    merged = dict(existing)
    for key, value in updates.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_memory(merged[key], value)
        elif isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = list(dict.fromkeys(merged[key] + value))
        else:
            merged[key] = value
    return merged


def build_messages(memory: dict, messages: list[dict]) -> list[dict]:
    if not memory:
        return messages
    system_prompt = (
        "You are a helpful assistant. Use the following user memory to "
        "personalize responses when relevant. If it is not relevant, ignore it.\n"
        f"User memory (JSON): {json.dumps(memory)}"
    )
    return [{"role": "system", "content": system_prompt}] + messages


if "chats_loaded" not in st.session_state:
    st.session_state.chats = load_chats()
    st.session_state.active_chat_id = (
        next(iter(st.session_state.chats.keys()), None)
        if st.session_state.chats
        else None
    )
    st.session_state.chats_loaded = True
if "memory" not in st.session_state:
    st.session_state.memory = load_memory()


def create_chat():
    chat_id = f"chat_{int(datetime.utcnow().timestamp() * 1000)}"
    chat = {
        "id": chat_id,
        "title": "New Chat",
        "created_at": datetime.now(),
        "messages": [],
    }
    st.session_state.chats[chat_id] = chat
    st.session_state.active_chat_id = chat_id
    save_chat(chat)


with st.sidebar:
    st.header("Chats")
    if st.button("New Chat"):
        create_chat()

    if st.session_state.chats:
        for chat_id, chat in list(st.session_state.chats.items()):
            is_active = chat_id == st.session_state.active_chat_id
            indicator = "●" if is_active else "○"
            label = f"{indicator} {chat['title']} ({chat['created_at'].strftime('%b %d, %I:%M %p')})"

            row = st.columns([0.85, 0.15])
            if row[0].button(label, key=f"select_{chat_id}"):
                st.session_state.active_chat_id = chat_id
            if row[1].button("✕", key=f"delete_{chat_id}"):
                del st.session_state.chats[chat_id]
                delete_chat_file(chat_id)
                if st.session_state.active_chat_id == chat_id:
                    remaining = list(st.session_state.chats.keys())
                    st.session_state.active_chat_id = remaining[0] if remaining else None
                st.rerun()
    else:
        st.info("No chats yet. Create one to get started.")

    st.divider()
    st.subheader("User Memory")
    if st.button("Clear Memory"):
        st.session_state.memory = {}
        save_memory(st.session_state.memory)
    with st.expander("View Memory", expanded=True):
        st.json(st.session_state.memory)


active_chat_id = st.session_state.active_chat_id
if not active_chat_id:
    st.info("Select a chat from the sidebar or create a new one.")
    st.stop()

active_chat = st.session_state.chats[active_chat_id]

for msg in active_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Type a message and press Enter")
if user_input:
    active_chat["messages"].append({"role": "user", "content": user_input})
    if active_chat["title"] == "New Chat":
        active_chat["title"] = user_input[:30]
    save_chat(active_chat)

    with st.chat_message("user"):
        st.write(user_input)

    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "model": "meta-llama/Llama-3.2-1B-Instruct",
        "messages": build_messages(st.session_state.memory, active_chat["messages"]),
        "max_tokens": 512,
    }

    try:
        payload["stream"] = True
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
            stream=True,
        )
        if response.status_code != 200:
            st.error(
                f"API request failed ({response.status_code}). "
                "Please check your token or try again later."
            )
        else:
            full_reply = ""
            with st.chat_message("assistant"):
                placeholder = st.empty()

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[len("data: ") :]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if delta:
                            full_reply += delta
                            placeholder.write(full_reply)
                            time.sleep(0.02)

            if not full_reply:
                st.error("API response was missing the model message.")
            else:
                active_chat["messages"].append(
                    {"role": "assistant", "content": full_reply}
                )
                save_chat(active_chat)
                extract_payload = {
                    "model": "meta-llama/Llama-3.2-1B-Instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Extract any personal traits or preferences from the "
                                "user message and return ONLY a JSON object. If none, "
                                "return {}."
                            ),
                        },
                        {"role": "user", "content": user_input},
                    ],
                    "max_tokens": 128,
                }
                try:
                    extract_response = requests.post(
                        "https://router.huggingface.co/v1/chat/completions",
                        headers=headers,
                        json=extract_payload,
                        timeout=30,
                    )
                    if extract_response.status_code == 200:
                        extract_data = extract_response.json()
                        extract_text = (
                            extract_data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "{}")
                        )
                        extracted = json.loads(extract_text)
                        if isinstance(extracted, dict):
                            st.session_state.memory = merge_memory(
                                st.session_state.memory, extracted
                            )
                            save_memory(st.session_state.memory)
                except (requests.RequestException, json.JSONDecodeError):
                    pass
    except requests.RequestException:
        st.error("Network error contacting Hugging Face. Please try again.")
