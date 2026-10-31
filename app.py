# app.py - Dhakhtarka Dalagga (Plant Doctor)
# Main file. Run with: streamlit run app.py

import streamlit as st

from api_key import get_api_key
from gemini_client import ask_ai
from ui import AI_AVATAR, setup_page, show_message, show_sidebar

# 1. Page design
setup_page()
show_sidebar()

# 2. Check the key
api_key = get_api_key()
if not api_key:
    st.error(
        "Furaha API lama helin. Geli furaha faylka key.txt "
        "(ama Secrets haddii ay online tahay)."
    )
    st.stop()

# 3. Chat memory
if "chat" not in st.session_state:
    st.session_state.chat = []

for old_message in st.session_state.chat:
    show_message(old_message)

# 4. When the user sends something
user_input = st.chat_input(
    "Weydii su'aal... (riix + si aad sawir ugu darto)",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    new_message = {
        "role": "user",
        "text": user_input.text or "",
        "image": None,
        "mime": None,
    }

    if user_input.files:
        photo = user_input.files[0]
        new_message["image"] = photo.getvalue()
        new_message["mime"] = photo.type or "image/jpeg"

    st.session_state.chat.append(new_message)
    show_message(new_message)

    answer = None
    with st.chat_message("assistant", avatar=AI_AVATAR):
        with st.spinner("Waan fekerayaa..."):
            try:
                answer = ask_ai(api_key, st.session_state.chat)
            except Exception as error:
                st.error(
                    "Waan ka xumahay, cilad ayaa dhacday. "
                    "Fadlan dhawr ilbiriqsi kadib isku day mar kale."
                )
                st.caption(f"Faahfaahin: {str(error)[:300]}")

        if answer:
            st.write(answer)

    # Save the answer, or remove the user message if it failed
    if answer:
        st.session_state.chat.append({"role": "assistant", "text": answer})
    else:
        st.session_state.chat.pop()