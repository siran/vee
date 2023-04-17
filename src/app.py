import os
import sys
from TimerNs import TimerNs
timer = TimerNs()

timer.toc('start')
import base64
import shutil
import time
import urllib.parse
from textwrap import dedent

import boto3
import openai
import whisper
timer.toc('whisper')

from flask import Flask, request
app = Flask(__name__)
timer.toc('flask')

model = whisper.load_model("base")
timer.toc('model base')

default_html = """<!DOCTYPE html>
<html>
<head>
<style>
body{font-family:sans-serif;}
h1,h2{margin:0;}
section{margin:20px 0;}
a{color:#06c;text-decoration:none;}
#top{position:fixed;top:5px;right:5px;font-size:14px;}
</style>
</head>
<body>
<h1>VeeMail.me</h1>
<section>
    <h2>AI-Powered, Voice-Email integration</h2>
    <p>Just tap and talk. Meta intelligence at its finest.</p>
</section>
<section>
    <h2>Smart Compose & Reply</h2>
    <p>Auto subject line summarizes your voice-email. And more.</p>
</section>
<section>
    <h2>Free and open-source</h2>
    <p>It's free and open source. This means transparence, improved security and no ads. Ever. (Unless you want them :)</p>
</section>
<footer>
    <p>E: contact@veemail.me</p>
    <p>T: @veemailme</p>
    <p>Copyright &copy; 2023</p>
</footer>
<a id="top" href="#">&#x2191; Top</a>
</body>
</html>
"""

default_html =  "Content not supported yet."

def get_private_key():
    ssm = boto3.client("ssm")
    keyname = "/openai/key"

    value = ssm.get_parameter(
        Name=keyname,
        WithDecryption=True,
    )

    return str(value['Parameter']['Value'])

private_key = get_private_key()
openai.api_key = private_key
os.environ["OPENAI_API_KEY"] = private_key

@app.route("/", methods = ['POST', 'GET'])
def root():
    # print("ok")
    # print(request.headers)
    timestamp = str(time.time_ns())
    content_type = request.headers.get('Content-Type')
    # print(f'{content_type=}')
    if (content_type == 'application/json'):
        rjson = request.json
        if content_b64 := rjson.get('content'):
            fname_timestamp = f"/home/ubuntu/repos/vee/src/assets/{timestamp}.b64"
            with open(fname_timestamp, 'w') as fp:
                fp.write(content_b64)

            content = base64.b64decode(content_b64)
            fname = f"{fname_timestamp}.decoded"
            with open(fname, 'bw') as fp:
                fp.write(content)

            # saving with valid extension
            valid_extensions = ['m4a', 'mp4', 'ogg']
            for ext in valid_extensions:
                if ext in str(content[0:100]).lower():
                    fname_content = f"{fname_timestamp}.{ext}"
                    shutil.copy(fname, fname_content)
                    break

            # transcribing
            timer.tic('transc')
            transcription = model.transcribe(fname_content)
            transcription_text = transcription["text"]
            timer.toc('transc end')

            # determine language
            timer.tic('lang')
            prompt = f"Please in one word specify the language of this message: {transcription_text}"

            messages = [
                {"role": "system", "content": "Reply in only one Enlish word"},
                {"role": "user", "content": prompt},
            ]
            r = openai.ChatCompletion.create(
                # model="gpt-3.5-turbo",
                model="gpt-3.5-turbo-0301",
                messages=messages,
                temperature=0,
            )
            language = urllib.parse.quote(r['choices'][0]['message']['content'])
            timer.toc('lang end')


            # summarizing
            timer.tic('summ')
            prompt = f"Summarize in six words or less using language {language}: {transcription_text}"

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": prompt},
            ]
            r = openai.ChatCompletion.create(
                # model="gpt-3.5-turbo",
                model="gpt-3.5-turbo-0301",
                messages=messages,
                temperature=0,
            )
            subject = urllib.parse.quote(r['choices'][0]['message']['content'])
            timer.toc('summ end')

            prompt = f"Please write a short joke about the following message in language {language}: {transcription_text}."

            timer.tic('summ')
            messages.extend([
                {"role": "system", "content": prompt},
                {"role": "user", "content": prompt},
            ])

            r = openai.ChatCompletion.create(
                # model="gpt-3.5-turbo",
                model="gpt-3.5-turbo-0301",
                messages=messages,
                temperature=1,
            )
            joke = r['choices'][0]['message']['content']
            timer.toc('summ end')


            print(subject)
            print(transcription_text)
            print(joke)

            email='anmichel@gmail.com'
            # subject= ''
            body=urllib.parse.quote(dedent(
                f"""{transcription_text}


                ---
                This email was generated by VeeMail, an AI-powered voice-email integration (and more).
                W: https://veemail.me

                AI-generated joke: {joke}
                """))

            # 'to' can be inferred from the audio content!
            # ret = f'googlegmail:///co?subject={subject}&body={body}&to={email}

            ret = f'googlegmail:///co?subject={subject}&body={body}'

            summary_eml = dedent(
                f"""
                {body}

                ---
                # Audio Timestamp
                {timestamp}
                """)

            summary_eml_fname = f"/home/ubuntu/repos/vee/src/assets/{timestamp}.eml.md"
            with open(summary_eml_fname, 'w') as fp:
                fp.write(summary_eml)

            return ret

            # return 'googlegmail:///co?subject=test&body=test&to=anmichel@gmail.com'
            # return "I saved the content you shared. Please, tell me your instructions."

        return 'Hi! Vee here.'

        # print(rjson)
    else:
        # static content
        return default_html

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4200, debug=True)

    # js = request.json
    # print(js)
    # return {"ok":str(js)}