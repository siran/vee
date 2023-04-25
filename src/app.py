import base64
from flask import Flask, request

from VeeAi import VeeAI
Vee = VeeAI()

app = Flask(__name__)

@app.route("/", methods = ['POST', 'GET'])
def root():
    """Handle requests to /. Check if there is POST data or information and routes accordingly."""

    content_type = request.headers.get('Content-Type')
    if not (content_type == 'application/json'):
        return 'No JSON payload provided'

    payload = request.json

    if not (content_b64 := payload.get('content')):
        return 'No content was provided'

    content = base64.b64decode(content_b64)
    fname_content = Vee.save_content(content)
    if not Vee.is_audio(fname_content):
        return 'Sorry, only processing audio for the moment'

    transcription_text = Vee.transcribe_audio(fname_content)
    Vee.save_transcript(fname_content, transcription_text)

    if payload.get('type') == 'chat':
        return Vee.reply_chat(transcription_text)

    # default behavior
    return Vee.get_email_url(transcription_text)

# def save_json_payload(payload):
#     """Inspects payload and save files as per configuration variables"""


#     rjson = payload
#     try:
#         content = base64.b64decode(rjson.get('content'))
#     except:
#         return False

#     return Vee.save_content(content)



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4200, debug=True)

    # js = request.json
    # print(js)
    # return {"ok":str(js)}