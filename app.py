# Dhakhtarka Dalagga - Plant Doctor App
# This app lets a farmer send a plant photo or a question,
# and Gemini AI answers in simple Somali.

import base64
import json
import os
import urllib.error
import urllib.request

import streamlit as st


# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------

# The models we try, in order. If the first one fails, we try the next one.
MODEL_LIST = [
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

# Instructions that tell the AI how to behave
SYSTEM_TEXT = (
    "You are a friendly plant doctor and farming helper for small farmers in Somalia. "
    "Always answer in simple Somali, unless the user writes in English. "
    "Use very simple words and short answers. "
    "If there is a plant photo: name the crop, say if it is healthy, name the disease "
    "or problem, give the cause, then cheap and safe treatment steps, then prevention tips. "
    "If you are not sure, say so and ask a short question. "
    "If the photo is not a plant, say so politely."
)

# How many old messages we send to the AI (keeps it fast and cheap)
MAX_HISTORY = 6

# How many seconds we wait for Gemini before giving up
WAIT_SECONDS = 25


# ------------------------------------------------------------
# 2. GET THE API KEY
# ------------------------------------------------------------

def get_api_key():
    # First: look in the computer environment
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()

    # Second: look in Streamlit secrets (used when the app is online)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        pass

    # Third: look in a file called key.txt
    if os.path.exists("key.txt"):
        with open("key.txt", encoding="utf-8") as file:
            return file.read().strip()

    # No key found
    return None


# ------------------------------------------------------------
# 3. TALK TO GEMINI
# ------------------------------------------------------------

def send_to_gemini(api_key, body):
    last_error = "Gemini waa mashquul yahay hadda."

    # Try each model until one works
    for model_name in MODEL_LIST:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model_name
            + ":generateContent"
        )

        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=WAIT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
            # Get the answer text from the reply
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except urllib.error.HTTPError as error:
            last_error = error.read().decode("utf-8", errors="ignore")
            # These errors mean "try another model"
            if error.code in (404, 429, 500, 503):
                continue
            # Other errors are real problems, so we stop
            raise RuntimeError(last_error)

        except (TimeoutError, urllib.error.URLError):
            # Internet is slow or down, try the next model
            continue

    # All models failed
    raise RuntimeError(last_error)


def make_parts(message):
    # A message can have a photo and/or text.
    # Gemini wants them as a list of "parts".
    parts = []

    if message.get("image"):
        image_text = base64.b64encode(message["image"]).decode()
        parts.append(
            {
                "inline_data": {
                    "mime_type": message["mime"],
                    "data": image_text,
                }
            }
        )

    if message.get("text"):
        parts.append({"text": message["text"]})

    return parts


def ask_ai(api_key, history):
    # Only use the last few messages
    recent = history[-MAX_HISTORY:]

    # Gemini needs the first message to be from the user
    if recent and recent[0]["role"] != "user":
        recent = recent[1:]

    # Change our messages to the format Gemini understands
    contents = []
    for message in recent:
        if message["role"] == "user":
            role = "user"
        else:
            role = "model"
        contents.append({"role": role, "parts": make_parts(message)})

    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_TEXT}]},
        "contents": contents,
    }

    return send_to_gemini(api_key, body)


# ------------------------------------------------------------
# 4. SHOW A MESSAGE ON THE SCREEN
# ------------------------------------------------------------

def show_message(message):
    with st.chat_message(message["role"]):
        # Show the photo if there is one
        if message.get("image"):
            image_text = base64.b64encode(message["image"]).decode()
            st.markdown(
                f'<img src="data:{message["mime"]};base64,{image_text}" width="250">',
                unsafe_allow_html=True,
            )
        # Show the text if there is some
        if message.get("text"):
            st.write(message["text"])


# ------------------------------------------------------------
# 5. PAGE DESIGN
# ------------------------------------------------------------

st.set_page_config(page_title="Dhakhtarka Dalagga", page_icon="🌱")

# Hide the Streamlit menu, footer and toolbar
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
st.caption("Ku soo dhawaaw dhakhtarka dalagga! Weydii su'aal, oo hel talo degdeg ah.")

# Side bar
with st.sidebar:
    st.header("🌿 Ku saabsan")
    st.write(
        "Dhakhtarka Dalagga waxa uu caawiyaa beeralayda Soomaaliyeed. "
        "Soo geli sawirka dalag jirran, oo waxaad heli doontaa cudurka, "
        "sababta, daawaynta iyo ka-hortagga."
    )
    # Button to clear the chat
    if st.button("Bilow wada hadal cusub"):
        st.session_state.chat = []
        st.rerun()


# ------------------------------------------------------------
# 6. CHECK THE KEY
# ------------------------------------------------------------

api_key = get_api_key()

if not api_key:
    st.error(
        "Furaha API lama helin. Geli furaha faylka key.txt "
        "(ama Secrets haddii ay online tahay)."
    )
    st.stop()


# ------------------------------------------------------------
# 7. CHAT MEMORY
# ------------------------------------------------------------

# Make an empty chat list the first time the app opens
if "chat" not in st.session_state:
    st.session_state.chat = []

# Show all old messages
for old_message in st.session_state.chat:
    show_message(old_message)


# ------------------------------------------------------------
# 8. WHEN THE USER SENDS SOMETHING
# ------------------------------------------------------------

user_input = st.chat_input(
    "Weydii su'aal... (riix + si aad sawir ugu darto)",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    # Make the new message
    new_message = {
        "role": "user",
        "text": user_input.text or "",
        "image": None,
        "mime": None,
    }

    # If the user added a photo, save it
    if user_input.files:
        photo = user_input.files[0]
        new_message["image"] = photo.getvalue()
        new_message["mime"] = photo.type or "image/jpeg"

    # Save and show the message
    st.session_state.chat.append(new_message)
    show_message(new_message)

    # Ask the AI
    answer = None
    with st.chat_message("assistant"):
        with st.spinner("Waan fekerayaa..."):
            try:
                answer = ask_ai(api_key, st.session_state.chat)
            except Exception as error:
                st.error(
                    "Waan ka xumahay, cilad ayaa dhacday. "
                    "Fadlan dhawr ilbiriqsi kadib isku day mar kale."
                )
                st.caption(f"Faahfaahin: {str(error)[:300]}")

        # Show the answer
        if answer:
            st.write(answer)

    # Save the answer, or remove the user message if it failed
    if answer:
        st.session_state.chat.append({"role": "assistant", "text": answer})
    else:
        st.session_state.chat.pop()
