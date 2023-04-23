import json
import os
import re
import traceback
import uuid
import base64
import shutil
import time
import urllib.parse
from textwrap import dedent
import pathlib

import openai
import whisper
from flask import Flask, request

from TimerNs import TimerNs
import auth

auth.auth_opeai()

app = Flask(__name__)
model = whisper.load_model("base")
timer = TimerNs()

# configuration variables
path_content_b64 = "assets"
audio_file_extensions = ['m4a', 'mp4', 'ogg']

@app.route("/", methods = ['POST', 'GET'])
def root():
    """Handle requests to /. Check if there is POST data or information and routes accordingly."""

    content_type = request.headers.get('Content-Type')
    if not (content_type == 'application/json'):
        return 'No JSON payload provided'

        # we got some JSON
        payload = request.json
        # fname_content = save_json_payload(payload)

        if not (content_b64 := request.json.get('content')):
            return 'No content was provided'

        content = base64.b64decode(content_b64)
        fname_content = save_content(content)

        if not is_audio(fname_content):
            return 'Sorry, only processing audio for the moment'

        transcription_text = transcribe_audio(fname_content)
        print(f"{transcription_text=}")

        if payload.get('type') == 'chat':
            return reply_chat(transcription_text)

        summary_eml = dedent(
            f"""
            # transcription_text
            {transcription_text}

            ---
            # fname
            {fname_content=}
            """)

        summary_eml_fname = f"{fname_content}.md"
        with open(summary_eml_fname, 'w') as fp:
            fp.write(summary_eml)

        return get_email_url(transcription_text)

    # return 'googlegmail:///co?subject=test&body=test&to=anmichel@gmail.com'
    # return "I saved the content you shared. Please, tell me your instructions."

    # Default response
    return 'Hi! Vee here.'

def save_json_payload(payload):
    """Inspects payload and save files as per configuration variables"""


    rjson = payload
    try:
        content = base64.b64decode(rjson.get('content'))
    except:
        return False

    return save_content(content)

def get_email_url(transcription_text):
    # determine language
    language = get_language(transcription_text)


    # summarizing
    timer.tic('summ')
    prompt = f"Summarize in six words or less using language {language}: {transcription_text}"
    subject = prompt_llm(prompt)
    timer.toc('summ end')

    timer.tic('joke')
    prompt = f"Please write a short joke about the following message in language {language}: {transcription_text}."
    joke = prompt_llm(prompt)
    timer.tic('joke end')

    timer.tic('recipient')
    prompt = f"Please determine name of recipient from the following message. If you can't determine the recipient please reply with NO: {transcription_text}."
    recipient = prompt_llm(prompt)
    if "no" in recipient.lower():
        recipient = None
    timer.tic('end recipient')

    timer.tic('action')
    prompt = f"Please determine if the user is giving a command from this message. If you can't determine the recipient please reply with NO: {transcription_text}."
    command = prompt_llm(prompt)
    if "no" in command.lower():
        command = None
    timer.tic('end command')

    print(f'{command=}')
    print(f'{recipient=}')
    print(f'{subject=}')
    print(f'{joke=}')
    # print(transcription_text)

    email='anmichel@gmail.com'
    # subject= ''
    body=urllib.parse.quote(dedent(
        f"""{transcription_text}


        ---
        via veemail.me

        ... {joke}
        """))

    # 'to' can be inferred from the audio content!
    # ret = f'googlegmail:///co?subject={subject}&body={body}&to={email}

    # preparing gmail url scheme
    # email_url = urllib.parse.quote(f'googlegmail:///co?subject={subject}&body={body}&to={recipient}')
    email_url = f'googlegmail:///co?subject={urllib.parse.quote(subject)}&body={body}'

    return email_url

def get_language(transcription_text):
    """Returns transcript's English language name"""

    timer.tic('lang')
    prompt = f"Please in one word specify the language of this message: {transcription_text}"

    language = prompt_llm(prompt)
    timer.toc('lang end')
    return language

def prompt_llm(prompt, system_prompt=None, messages=None):
    timer.tic('prompt start')

    system_prompt = system_prompt or prompt
    messages = messages or []

    if system_prompt != '':
        messages.extend([
            {"role": "system", "content": system_prompt},
        ])

    messages.extend([
        {"role": "user", "content": prompt},
    ])

    r = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo",
        model="gpt-3.5-turbo-0301",
        messages=messages,
        temperature=0,
    )
    response = r['choices'][0]['message']['content']

    timer.toc('prompt end')

    return response

def transcribe_audio(fname_content):
    timer.tic('transc')
    transcription = model.transcribe(fname_content)
    transcription_text = transcription["text"]
    timer.toc('transc end')
    return transcription_text

def is_audio(fname):
    extension = pathlib.Path(fname).suffix
    return extension[1:] in audio_file_extensions

def get_content_type(content):
    content100 = content[0:100]
    valid_extensions = audio_file_extensions
    for ext in valid_extensions:
        if ext in str(content100).lower():
            break
    else:
        ext = 'b64'

    return ext

def save_content(content):
    """ Saves content with a valid extension if possible """

    content_id = str(time.time_ns())
    ext = get_content_type(content)
    fname_content = os.path.join(path_content_b64, f"{content_id}.{ext}")
    # renaming with valid extension
    with open(fname_content, 'bw') as fp:
        fp.write(content)

    return fname_content

def fuzzy_intent(intent_a, intent_b):
    """Uses LLM to try to derminar if A ~ B """

    prompt = f"Please answer YES or NO if these messages have the same intent? Message 1: {intent_a}; Message 2: {intent_b}"
    response = prompt_llm(prompt)

    if "yes" in response.lower():
        return True
    elif "no" in response.lower():
        return False

    return None

def reply_chat(transcription_text):

        fname = 'messages.jsonl'
        fpmode = "a+"

        if fuzzy_intent(transcription_text, "clear message history"):
            uuidstr = str(uuid.uuid1())
            shutil.copyfile(fname, f"{fname}.{uuidstr}.memory")
            # mode = "w"
            # old_memory = fp.read()
            os.unlink(fname)
            return "memory cleared"


        timer.tic('reading old messages')
        with open(fname, 'a+', encoding='utf-8') as fp:
            fp.seek(0)
            messages_txt = fp.read()

        messages = json.loads(f"[{messages_txt[:-1]}]")
        try:
            response = prompt_llm(prompt=transcription_text, system_prompt='', messages=messages)
        except Exception as error:
            traceback.print_exc()

            if error.code == "context_length_exceeded":
                # messages = summarize_messages(messages)

                return 'Please clear messages'

            return 'An error occurred, please try again later'

        # remove first sentence
        sentences = response.split('.')
        new_response = []
        unwanted_phrases = [
            "openai",
            "language model",
            "como una inteligencia articial",
            "estoy programada para",
            "no tengo emociones como los seres humanos",

            "have no feelings",
            "am programmed",
            "m programmed",
            "don't have emotions",
            "do not have emotions",
            # "programmed"
        ]
        for sentence in sentences:
            for phrase in unwanted_phrases:
                if phrase.lower() in sentence.lower():
                    print(f"phrase discarded {sentence=}")
                    break
            else:
                new_response.append(sentence)
                print(f"sentence accepted {sentence=}")


        response = ".".join(new_response) or ' - '

        messages.append({"role": "assistant", "content": response})
        with open(fname, mode=fpmode, encoding='utf-8') as fp:
            for m in messages[-2:]:
                messages = fp.write('\n' + json.dumps(m) + ',')
            # [
            #     {"role": "user", "content": transcription_text},
            #     {"role": "assistant", "content": transcription_text},
            # ]
        timer.toc('summ end')

        return response

def summarize_messages(messages):
    parts = [messages[0:len(messages)//2], messages[len(messages)//2+1:]]

    new_messages = []
    for part in parts:
        message = [{"role": "user", "content": f"Please summarize this conversation. Keep the same JSON format. Reply only with a valid JSON. Thanks: {json.dumps(part)}"}]
        r = openai.ChatCompletion.create(
            # model="gpt-3.5-turbo",
            model="gpt-3.5-turbo-0301",
            messages=message,
            temperature=0,
        )
        response = r['choices'][0]['message']['content']
        new_messages.extend(json.loads(response))

    return new_messages

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4200, debug=True)

    # js = request.json
    # print(js)
    # return {"ok":str(js)}