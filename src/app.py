from TimerNs import TimerNs
timer = TimerNs()

timer.toc('start')
import base64
import shutil
import time
import urllib.parse
from textwrap import dedent

import openai
import whisper
timer.toc('whisper')

from flask import Flask, request
app = Flask(__name__)
timer.toc('flask')

model = whisper.load_model("base")
timer.toc('model base')

with open('private.key') as fp:
    openai.api_key = fp.read()

@app.route("/", methods = ['POST', 'GET'])
def root():
    # print("ok")
    # print(request.headers)
    timestamp = str(time.time_ns())
    content_type = request.headers.get('Content-Type')
    print(f'{content_type=}')
    if (content_type == 'application/json'):
        rjson = request.json
        if content_b64 := rjson.get('content'):
            fname_timestamp = f"assets/{timestamp}.b64"
            with open(fname_timestamp, 'w') as fp:
                fp.write(content_b64)

            content = base64.b64decode(content_b64)
            fname = f"{fname_timestamp}.decoded"
            with open(fname, 'bw') as fp:
                fp.write(content)

            # saving with valid extension
            valid_extensions = ['m4a', 'mp4']
            for ext in valid_extensions:
                if ext in str(content[0:100]).lower():
                    fname_content = f"{fname_timestamp}.{ext}"
                    shutil.copy(fname, fname_content)
                    break

            # transcribing
            timer.tic('model base')
            transcription = model.transcribe(fname_content)
            timer.toc('model base')

            print(transcription["text"])

            email='anmichel@gmail.com'
            subject='test'
            body=urllib.parse.quote(dedent(
                f"""

                {transcription}



                This email was generated from a voice transcription by VeeMail.

                Want to receive the original audio? Forward this email to register@veemail.me and we'll send it to you. (Soon)

                """))

            # 'to' can be inferred from the audio content!
            # ret = f'googlegmail:///co?subject={subject}&body={body}&to={email}

            ret = f'googlegmail:///co?subject={subject}&body={body}'
            return ret

            # return 'googlegmail:///co?subject=test&body=test&to=anmichel@gmail.com'
            # return "I saved the content you shared. Please, tell me your instructions."

        return 'Hi! Vee here.'

        # print(rjson)
    else:
        return 'Sorry, this Content-Type not supported for now. Please try again.'

    # js = request.json
    # print(js)
    # return {"ok":str(js)}