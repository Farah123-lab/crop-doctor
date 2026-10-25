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


MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]


def call_gemini(key, body):
    last_error = "Gemini waa mashquul yahay hadda."
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            last_error = e.read().decode("utf-8", errors="ignore")
            if e.code in (404, 429, 500, 503):
                continue
            raise RuntimeError(last_error)
        except (TimeoutError, urllib.error.URLError):
            continue
    raise RuntimeError(last_error)
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

    /* put the + button inside the chat box, on the left */
    [data-testid="stChatInput"] textarea {padding-left: 3.4rem !important;}
    [data-testid="stBottom"] [data-testid="stElementContainer"]:has([data-testid="stPopover"]) {
        position: relative;
        height: 0;
        z-index: 1000;
    }
    [data-testid="stBottom"] [data-testid="stPopover"] button {
        position: absolute;
        left: 0.6rem;
        top: 1.5rem;
        width: 2.4rem;
        height: 2.4rem;
        min-height: 0;
        padding: 0;
        border: none;
        background: transparent;
        font-size: 1.7rem;
        line-height: 1;
        border-radius: 50%;
    }
    [data-testid="stBottom"] [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        display: none;
    }
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
        "Soo geli sawirka dalag jirran, oo waxaad heli doontaa cudurka, "
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

if "pic_n" not in st.session_state:
    st.session_state.pic_n = 0
n = st.session_state.pic_n

# ➕ button next to the chat box: Camera or Drag & drop
bottom = st._bottom if hasattr(st, "_bottom") else st.container()
with bottom:
    with st.popover("＋"):
        way = st.radio(
            "Dooro",
            ["📷 Kamarad", "🖼️ Soo geli (drag & drop)"],
            key=f"way_{n}",
        )
        if way.startswith("📷"):
            photo = st.camera_input("Sawir qaad", key=f"cam_{n}")
        else:
            photo = st.file_uploader(
                "Soo jiid sawirka halkan",
                type=["jpg", "jpeg", "png"],
                key=f"upl_{n}",
            )
        if photo is not None and st.button("✅ Dir sawirka", type="primary", key=f"send_{n}"):
            st.session_state.pending = (photo.getvalue(), photo.type)

prompt = st.chat_input("Weydii su'aal...")

msg = None
pending = st.session_state.pop("pending", None)
if pending:
    st.session_state.pic_n += 1  # reset camera and uploader
    msg = {
        "role": "user",
        "text": "Fadlan eeg sawirkan.",
        "image": pending[0],
        "mime": pending[1] or "image/jpeg",
    }
elif prompt:
    msg = {"role": "user", "text": prompt, "image": None, "mime": None}

if msg:
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
