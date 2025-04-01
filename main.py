import os
from flask import Flask, request
from twilio.rest import Client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Setup Twilio + OpenAI
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "")
    
    if not incoming_msg:
        return "No message received", 400

    # Send message to ChatGPT
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": incoming_msg}]
        )
        reply_text = completion.choices[0].message.content.strip()
    except Exception as e:
        reply_text = "Sorry, there was an error with OpenAI: " + str(e)

    # Send the response back via WhatsApp
    try:
        twilio_client.messages.create(
            body=reply_text,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=from_number
        )
    except Exception as e:
        return f"Failed to send message: {str(e)}", 500

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
