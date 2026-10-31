# ui.py - everything the farmer sees on the screen

import base64

import streamlit as st

from avatars import DOCTOR_PICTURE, FARMER_PICTURE

HIDE_MENU_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}

/* The sidebar open and close buttons: always visible, shown as three lines */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {
    visibility: visible !important;
}
[data-testid="stExpandSidebarButton"] > *,
[data-testid="stSidebarCollapsedControl"] button > *,
[data-testid="stSidebarCollapseButton"] button > * {
    display: none !important;
}
[data-testid="stExpandSidebarButton"]::after,
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="stSidebarCollapseButton"] button::after {
    content: "\\2630";
    font-size: 1.8rem;
    line-height: 1;
    color: #9AA4B2;
}
</style>
"""

# Chat profile pictures.
# Streamlit's own picture option needs a library (numpy) that is blocked on
# some computers, so we draw the pictures with CSS instead. The pictures
# themselves are saved inside avatars.py.
AVATAR_CSS = """
<style>
[data-testid="stChatMessageAvatarUser"],
[data-testid="chatAvatarIcon-user"] {
    background-color: transparent !important;
    background-image: url("__FARMER__") !important;
    background-size: cover !important;
    background-position: center !important;
}
[data-testid="stChatMessageAvatarAssistant"],
[data-testid="chatAvatarIcon-assistant"] {
    background-color: transparent !important;
    background-image: url("__DOCTOR__") !important;
    background-size: cover !important;
    background-position: center !important;
}
[data-testid="stChatMessageAvatarUser"] > *,
[data-testid="chatAvatarIcon-user"] > *,
[data-testid="stChatMessageAvatarAssistant"] > *,
[data-testid="chatAvatarIcon-assistant"] > * {
    display: none !important;
}
</style>
""".replace("__FARMER__", FARMER_PICTURE).replace("__DOCTOR__", DOCTOR_PICTURE)

# Dark mode colors. Change the color codes here if you want a different look.
DARK_CSS = """
<style>
.stApp, [data-testid="stHeader"],
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
    background-color: #0E1117 !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #161B22 !important;
}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp li,
.stApp label, .stApp span, .stApp strong {
    color: #E6EDF3 !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    color: #8B949E !important;
}
[data-testid="stChatMessage"] {
    background-color: #161B22 !important;
}
[data-testid="stChatInput"], [data-testid="stChatInput"] div {
    background-color: #161B22 !important;
    border-color: #30363D !important;
}
[data-testid="stChatInput"] button {
    color: #E6EDF3 !important;
}
[data-testid="stChatInputSubmitButton"] {
    background-color: #21262D !important;
}
[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
    color: #E6EDF3 !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #8B949E !important;
}
.stButton > button {
    background-color: #21262D !important;
    color: #E6EDF3 !important;
    border-color: #30363D !important;
}
</style>
"""

# Big text mode: easier to read from far away (for a projector).
BIG_TEXT_CSS = """
<style>
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    font-size: 1.45rem !important;
    line-height: 1.7 !important;
}
.stApp h1 {
    font-size: 3rem !important;
}
[data-testid="stCaptionContainer"] p {
    font-size: 1.1rem !important;
}
</style>
"""

# We use the default Streamlit avatar and the CSS above changes how it looks.
USER_AVATAR = None
AI_AVATAR = None


def avatar_for(role):
    return USER_AVATAR if role == "user" else AI_AVATAR


def setup_page():
    st.set_page_config(
        page_title="Dhakhtarka Dalagga",
        page_icon="🌱",
        initial_sidebar_state="expanded",
    )
    st.markdown(HIDE_MENU_CSS, unsafe_allow_html=True)
    st.markdown(AVATAR_CSS, unsafe_allow_html=True)

    # Dark mode is ON when the app opens. Change True to False for light mode.
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True

    # The switches are in the sidebar. Their values are kept in session_state.
    if st.session_state.get("dark_mode"):
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    if st.session_state.get("big_text"):
        st.markdown(BIG_TEXT_CSS, unsafe_allow_html=True)

    st.title("🌱 Dhakhtarka Dalagga")
    st.caption(
        "Ku soo dhawaaw dhakhtarka dalagga! Weydii su'aal, oo hel talo degdeg ah."
    )


def show_sidebar():
    with st.sidebar:
        st.header("🌿 Ku saabsan")
        st.write(
            "Dhakhtarka Dalagga waxa uu caawiyaa beeralayda Soomaaliyeed. "
            "Soo geli sawirka dalag jirran, oo waxaad heli doontaa cudurka, "
            "sababta, daawaynta iyo ka-hortagga."
        )

        st.subheader("📋 Sida loo isticmaalo")
        st.markdown(
            "1. Riix calaamadda **+** hoose\n"
            "2. Dooro sawirka caleenta jirran\n"
            "3. Riix fallaadhka ⬆️ oo sug jawaabta"
        )

        st.subheader("⚙️ Muuqaalka")
        st.toggle("🌙 Habka mugdiga (Dark)", key="dark_mode")
        st.toggle("🔎 Far weyn (Big text)", key="big_text")

        # Button to clear the chat
        if st.button("Bilow wada hadal cusub"):
            st.session_state.chat = []
            st.rerun()


def show_message(message):
    with st.chat_message(message["role"], avatar=avatar_for(message["role"])):
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