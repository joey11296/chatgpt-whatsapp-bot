from flask import Flask, request
from gtts import gTTS
from pydub import AudioSegment
import os
import uuid
import requests
from twilio.rest import Client
from openai import OpenAI

# === CONFIG ===
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

app = Flask(__name__)

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
    audio_filename = f"{uuid.uuid4()}.ogg"
    audio_path = os.path.join("static/media", audio_filename)
    audio_data = requests.get(media_url).content

    if not os.path.exists("static/media"):
        os.makedirs("static/media")

    with open(audio_path, "wb") as f:
        f.write(audio_data)

    # === Convert to MP3 for Whisper ===
    mp3_path = audio_path.replace(".ogg", ".mp3")
    audio = AudioSegment.from_file(audio_path)
    audio.export(mp3_path, format="mp3")
    os.remove(audio_path)

    # === Transcribe with Whisper ===
    with open(mp3_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        ).text
    os.remove(mp3_path)

    # === Get response from ChatGPT ===
    chat_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": transcription}]
    )
    reply_text = chat_response.choices[0].message.content

    # === Convert to voice ===
    reply_audio = gTTS(reply_text)
    reply_path = f"static/media/{uuid.uuid4()}.mp3"
    reply_audio.save(reply_path)

    # === Send voice reply via Twilio ===
    public_url = request.url_root + reply_path
    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=sender,
        body="Here's your AI reply 👇",
        media_url=[public_url]
    )

    return "OK", 200

if __name__ == '__main__':
    if not os.path.exists("static/media"):
        os.makedirs("static/media")
    app.run()
