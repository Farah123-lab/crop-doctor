import base64
import io
import json
import os
import urllib.error
import urllib.request

import streamlit as st
from PIL import Image

MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]
MAX_PHOTOS = 4

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
        "If there are several photos, they may show the same plant from different sides "
        "or different plants. Look at all of them. If they are different plants, "
        "answer for each one with a short title (Photo 1, Photo 2...). "
        "Use these short headings with emojis, written in the answer language: "
        "🌿 Crop, 🦠 Problem, ❓ Cause, 💊 Treatment, 🛡️ Prevention. "
        "If you are not sure, say so and ask a short question. "
        "If the problem looks serious, tell the farmer to also ask a local agriculture expert. "
        "If a photo is not a plant, say so politely."
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
            with urllib.request.urlopen(req, timeout=40) as resp:
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


def build_parts(m, with_images=True):
    parts = []
    if with_images:
        for data, mime in m.get("images", []):
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime,
                        "data": base64.b64encode(data).decode(),
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
        # Send photos only for the newest message (faster and cheaper)
        contents.append({"role": role, "parts": build_parts(m, with_images=(i == last_index))})
    body = {
        "systemInstruction": {"parts": [{"text": build_system(lang, crop)}]},
        "contents": contents,
    }
    return call_gemini(key, body)


def show(m):
    with st.chat_message(m["role"]):
        images = m.get("images", [])
        if images:
            if len(images) == 1:
                st.image(images[0][0], width=260)
            else:
                cols = st.columns(len(images))
                for col, (data, _) in zip(cols, images):
                    col.image(data, use_container_width=True)
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


# ---------------------------------------------------------------- page setup
st.set_page_config(
    page_title="Dhakhtarka Dalagga",
    page_icon="🌱",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    .block-container {padding-top: 2rem; max-width: 800px;}
    h1 {text-align: center; margin-bottom: 0;}
    .tagline {text-align: center; opacity: 0.75; margin-bottom: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "chat" not in st.session_state:
    st.session_state.chat = []

st.title("🌱 Dhakhtarka Dalagga")
st.markdown(
    '<p class="tagline">Sawir qaad dalagaaga, hel talo degdeg ah oo Soomaali ah.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------- about + settings (main page)
with st.expander("🌿 Ku saabsan"):
    st.write(
        "Dhakhtarka Dalagga waxa uu caawiyaa beeralayda Soomaaliyeed. "
        "Soo geli sawirka dalag jirran, oo waxaad heli doontaa cudurka, "
        "sababta, daawaynta iyo ka-hortagga."
    )
    st.info(
        "⚠️ Tani waa caawimo degdeg ah. Haddii cudurku weyn yahay, "
        "la tasho khabiir beeraha."
    )

with st.expander("⚙️ Dejinta"):
    c1, c2 = st.columns(2)
    crop_label = c1.selectbox("Dalagga (ikhtiyaari)", list(CROPS.keys()))
    lang_label = c2.radio("Luuqadda jawaabta", list(LANGS.keys()), horizontal=True)
crop = CROPS[crop_label]
lang = LANGS[lang_label]

key = load_key()
if not key:
    st.error("Furaha API lama helin. Geli furaha faylka key.txt (ama Secrets haddii ay online tahay).")
    st.stop()

# ---------------------------------------------------------------- welcome / actions
if not st.session_state.chat:
    s1, s2, s3 = st.columns(3)
    with s1.container(border=True):
        st.markdown("**1️⃣ Sawir qaad**")
        st.caption(f"Riix ➕ hoose. Dalagga jirran sawir ka qaad (ilaa {MAX_PHOTOS} sawir).")
    with s2.container(border=True):
        st.markdown("**2️⃣ Dir**")
        st.caption("Riix fallaadhka si aad u dirto.")
    with s3.container(border=True):
        st.markdown("**3️⃣ Hel talo**")
        st.caption("Cudurka, daawaynta iyo ka-hortagga.")
else:
    last_answer = next(
        (m["text"] for m in reversed(st.session_state.chat) if m["role"] == "assistant"),
        None,
    )
    b1, b2 = st.columns(2)
    if b1.button("🔄 Wada hadal cusub", use_container_width=True):
        st.session_state.chat = []
        st.rerun()
    if last_answer:
        b2.download_button(
            "⬇️ Kaydi talada",
            data=last_answer,
            file_name="talada-dalagga.txt",
            use_container_width=True,
        )

for m in st.session_state.chat:
    show(m)

# ---------------------------------------------------------------- chat box
prompt = st.chat_input(
    "Weydii su'aal... (riix ➕ si aad sawir ugu darto)",
    accept_file="multiple",
    file_type=["jpg", "jpeg", "png"],
)

if prompt:
    files = list(prompt.files or [])
    if len(files) > MAX_PHOTOS:
        st.warning(f"Ilaa {MAX_PHOTOS} sawir ayaa la qaadanayaa. Kuwa kale waa laga tagay.")
        files = files[:MAX_PHOTOS]

    images = [shrink(f.getvalue(), f.type) for f in files]
    text = prompt.text or ""
    if images and not text:
        if lang == "Somali":
            text = "Fadlan eeg sawirka." if len(images) == 1 else "Fadlan eeg sawirada."
        else:
            text = "Please look at this photo." if len(images) == 1 else "Please look at these photos."

    handle({"role": "user", "text": text, "images": images}, key, lang, crop)

st.caption("🌱 Dhakhtarka Dalagga · AI-ga waxa uu qaldami karaa. Khabiir la tasho marka cudurku weyn yahay.")
