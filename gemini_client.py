# gemini_client.py - talk to Gemini AI

import base64
import json
import urllib.error
import urllib.request

from config import MAX_HISTORY, MODEL_LIST, SYSTEM_TEXT, WAIT_SECONDS


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
        role = "user" if message["role"] == "user" else "model"
        contents.append({"role": role, "parts": make_parts(message)})

    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_TEXT}]},
        "contents": contents,
    }

    return send_to_gemini(api_key, body)
