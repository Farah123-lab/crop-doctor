import base64
import io
import json
import os
import urllib.error
import urllib.request

import streamlit as st
from PIL import Image

MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]

# Somali name -> English name (the AI understands the English name better)
CROPS = {
    "Ma garanayo": "unknown",
    "Galay": "maize",
    "Hadhuudh": "sorghum",
    "Sisin": "sesame",
    "Yaanyo": "tomato",
    "Muuse": "banana",
    "Basal": "onion",
    "Digir": "cowpea",
    "Khudaar kale": "other vegetable",
}

LANGS = {"Soomaali": "Somali", "English": "English"}


def build_system(lang, crop):
    text = (
        "You are a friendly plant doctor and farming helper for small farmers in Somalia. "
        f"Always answer in simple {lang}. "
        "Use very simple words and short answers. "
        "If there is a plant photo: name the crop, say if it is healthy, name the disease "
        "or problem, give the cause, then cheap and safe treatment steps, then prevention tips. "
        "Use these short headings with emojis, written in the answer language: "
        "🌿 Crop, 🦠 Problem, ❓ Cause, 💊 Treatment, 🛡️ Prevention. "
        "If you are not sure, say so and ask a short question. "
        "If the problem looks serious, tell the farmer to also ask a local agriculture expert. "
        "If the photo is not a plant, say so politely."
    )
    if crop != "unknown":
        text += f" The farmer says the crop is {crop}."
    return text


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


def shrink(data, mime):
    """Make the photo smaller so it is faster on weak internet."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((1024, 1024))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return data, mime or "image/jpeg"


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


def build_parts(m, with_image=True):
    parts = []
    if with_image and m.get("image"):
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


def ask(key, history, lang, crop):
    recent = history[-6:]
    if recent and recent[0]["role"] != "user":
        recent = recent[1:]
    contents = []
    last_index = len(recent) - 1
    for i, m in enumerate(recent):
        role = "user" if m["role"] == "user" else "model"
        # Send only the newest photo (faster and cheaper)
        contents.append({"role": role, "parts": build_parts(m, with_image=(i == last_index))})
    body = {
        "systemInstruction": {"parts": [{"text": build_system(lang, crop)}]},
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


def handle(msg, key, lang, crop):
    st.session_state.chat.append(msg)
    show(msg)

    answer = None
    with st.chat_message("assistant"):
        with st.spinner("Waan fekerayaa..."):
            try:
                answer = ask(key, st.session_state.chat, lang, crop)
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
    return answer


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

if "chat" not in st.session_state:
    st.session_state.chat = []
if "cam_n" not in st.session_state:
    st.session_state.cam_n = 0

st.title("🌱 Dhakhtarka Dalagga")
st.caption("Ku soo dhawaaw dhakhtarka dalagga! Sawir qaad ama weydii su'aal, oo hel talo degdeg ah.")

with st.sidebar:
    st.header("🌿 Ku saabsan")
    st.write(
        "Dhakhtarka Dalagga waxa uu caawiyaa beeralayda Soomaaliyeed. "
        "Soo geli sawirka dalag jirran, oo waxaad heli doontaa cudurka, "
        "sababta, daawaynta iyo ka-hortagga."
    )

    st.subheader("⚙️ Dejinta")
    crop_label = st.selectbox("Dalagga (ikhtiyaari)", list(CROPS.keys()))
    lang_label = st.radio("Luuqadda jawaabta", list(LANGS.keys()))
    crop = CROPS[crop_label]
    lang = LANGS[lang_label]

    last_answer = next(
        (m["text"] for m in reversed(st.session_state.chat) if m["role"] == "assistant"),
        None,
    )
    if last_answer:
        st.download_button(
            "⬇️ Kaydi talada",
            data=last_answer,
            file_name="talada-dalagga.txt",
        )

    if st.button("Bilow wada hadal cusub"):
        st.session_state.chat = []
        st.rerun()

    st.info(
        "⚠️ Tani waa caawimo degdeg ah. Haddii cudurku weyn yahay, "
        "la tasho khabiir beeraha."
    )

key = load_key()
if not key:
    st.error("Furaha API lama helin. Geli furaha faylka key.txt (ama Secrets haddii ay online tahay).")
    st.stop()

for m in st.session_state.chat:
    show(m)


# ---------- Chat box (text + upload) ----------
prompt = st.chat_input(
    "Weydii su'aal... (riix + si aad sawir ugu darto)",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if prompt:
    msg = {"role": "user", "text": prompt.text or "", "image": None, "mime": None}
    if prompt.files:
        f = prompt.files[0]
        msg["image"], msg["mime"] = shrink(f.getvalue(), f.type)
        if not msg["text"]:
            msg["text"] = "Fadlan eeg sawirkan." if lang == "Somali" else "Please look at this photo."
    handle(msg, key, lang, crop)
