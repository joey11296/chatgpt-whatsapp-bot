from flask import Flask, request
from gtts import gTTS
from pydub import AudioSegment
import os
import uuid
import requests
from twilio.rest import Client
from openai import OpenAI

# === Setup ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

app = Flask(__name__)
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

@app.route('/')
def home():
    return "ChatGPT WhatsApp bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    sender = request.form.get("From")
    media_url = request.form.get("MediaUrl0")

    if not media_url:
        return "No voice message found", 200

    # === Download audio ===
    media_dir = os.path.join("static", "media")
    os.makedirs(media_dir, exist_ok=True)

    audio_filename = f"{uuid.uuid4()}.ogg"
    audio_path = os.path.join(media_dir, audio_filename)
    audio_data = requests.get(media_url).content

    with open(audio_path, "wb") as f:
        f.write(audio_data)

    # === Convert to MP3 ===
    mp3_path = audio_path.replace(".ogg", ".mp3")
    AudioSegment.from_file(audio_path).export(mp3_path, format="mp3")
    os.remove(audio_path)

    # === Transcribe ===
    with open(mp3_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        ).text
    os.remove(mp3_path)

    # === Generate reply ===
    chat_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": transcription}]
    )
    reply_text = chat_response.choices[0].message.content

    # === TTS reply ===
    reply_audio = gTTS(reply_text)
    reply_filename = f"{uuid.uuid4()}.mp3"
    reply_path = os.path.join(media_dir, reply_filename)
    reply_audio.save(reply_path)

    public_url = request.url_root + reply_path

    # === Send back via Twilio ===
    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=sender,
        body="Here is your AI reply 🎤",
        media_url=[public_url]
    )

    return "OK", 200

if __name__ == '__main__':
    os.makedirs("static/media", exist_ok=True)
    app.run(debug=True)
