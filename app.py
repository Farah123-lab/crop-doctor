import base64
import json
import os
import time
import urllib.error
import urllib.request

import streamlit as st

MODEL = "gemini-3.8-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM = (
    "You are a friendly plant doctor and farming helper for small farmers in Somalia. "
    "Always answer in simple Somali, unless the user writes in English. "
    "Use very simple words and short answers. "
    "If there is a plant photo: name the crop, say if it is healthy, name the disease "
    "or problem, give the cause, then cheap and safe treatment steps, then prevention tips. "
    "If you are not sure, say so and ask a short question. "
    "If the photo is not a plant, say so politely."
)


def load_key():
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        pass
    if os.path.exists("key.txt"):
        with open("key.txt", encoding="utf-8") as f:
            return f.read().strip()
    return None


def call_gemini(key, body):
    for attempt in range(3):
        req = urllib.request.Request(
            URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code in (500, 503) and attempt < 2:
                time.sleep(2)
                continue
            raise RuntimeError(e.read().decode("utf-8", errors="ignore"))
        except (TimeoutError, urllib.error.URLError):
            if attempt < 2:
                continue
            raise RuntimeError("fadlan isku day mar kale.")
def build_parts(m):
    parts = []
    if m.get("image"):
        parts.append(
            {
                "inline_data": {
                    "mime_type": m["mime"],
                    "data": base64.b64encode(m["image"]).decode(),
                }
            }
        )
    if m.get("text"):
        parts.append({"text": m["text"]})
    return parts


def ask(key, history):
    recent = history[-6:]
    if recent and recent[0]["role"] != "user":
        recent = recent[1:]
    contents = []
    for m in recent:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": build_parts(m)})
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": contents,
    }
    return call_gemini(key, body)


def show(m):
    with st.chat_message(m["role"]):
        if m.get("image"):
            b64 = base64.b64encode(m["image"]).decode()
            st.markdown(
                f'<img src="data:{m["mime"]};base64,{b64}" width="250">',
                unsafe_allow_html=True,
            )
        if m.get("text"):
            st.write(m["text"])


st.set_page_config(page_title="Dhakhtarka Dalagga", page_icon="🌱")
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌱 Dhakhtarka Dalagga")
st.caption(
    "Ku soo dhawaaw dhakhtarka dallaga!, weydii su'aal, oo hel talo degdeg ah. "
)

with st.sidebar:
    st.header("🌿 Ku saabsan")
    st.write(
        "Dhakhtarka Dalagga waxa uu caawiyaa beeralayda Soomaaliyeed. "
        "Soo geli sawirka caleen jirran, oo waxaad heli doontaa cudurka, "
        "sababta, daawaynta iyo ka-hortagga."
    )
    if st.button("Bilow wada hadal cusub"):
        st.session_state.chat = []
        st.rerun()

key = load_key()
if not key:
    st.error("Furaha API lama helin. Geli furaha faylka key.txt (ama Secrets haddii ay online tahay).")
    st.stop()

if "chat" not in st.session_state:
    st.session_state.chat = []

for m in st.session_state.chat:
    show(m)

prompt = st.chat_input(
    "Weydii su'aal... (riix + si aad sawir ugu darto)",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if prompt:
    msg = {"role": "user", "text": prompt.text or "", "image": None, "mime": None}
    if prompt.files:
        f = prompt.files[0]
        msg["image"] = f.getvalue()
        msg["mime"] = f.type or "image/jpeg"
    st.session_state.chat.append(msg)
    show(msg)

    answer = None
    with st.chat_message("assistant"):
        with st.spinner("Waan fekerayaa..."):
            try:
                answer = ask(key, st.session_state.chat)
            except Exception as e:
                st.error(
                    "Waan ka xumahay, cilad ayaa dhacday. "
                    "Fadlan dhawr ilbiriqsi kadib isku day mar kale."
                )
                st.caption(f"Faahfaahin: {str(e)[:300]}")
        if answer:
            st.write(answer)

    if answer:
        st.session_state.chat.append({"role": "assistant", "text": answer})
    else:
        st.session_state.chat.pop()
