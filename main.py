from flask import Flask, request
from twilio.rest import Client as TwilioClient
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# OpenAI setup
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Flask setup
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        incoming_msg = request.values.get("Body", "").strip()
        from_number = request.values.get("From", "")

        if not incoming_msg:
            return "No message received", 400

        # ChatGPT reply
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": incoming_msg}
            ]
        )
        reply = completion.choices[0].message.content.strip()

        # Send reply back to user via WhatsApp
        twilio_client.messages.create(
            body=reply,
            from_=TWILIO_NUMBER,
            to=from_number
        )

        return "OK", 200
    except Exception as e:
        print("Error:", e)
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
