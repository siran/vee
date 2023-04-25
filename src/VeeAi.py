from dataclasses import dataclass
import json
import math
import os
import re
import shutil
from textwrap import dedent
import traceback
import uuid
import openai
import pathlib
import time
import urllib3
import urllib
# from TimerNs import TimerNs
import whisper

import auth

@dataclass
class VeeAI:
    """Contral control structure for Vees behavior"""

    path_content_b64 = "assets"
    audio_file_extensions = ['m4a', 'mp4', 'ogg']
    fname_messages = 'messages.jsonl'

    fname_content = None

    whisper_model = None

    messages = []
    # messages = [
    #     {"role": "system", "content": system_prompt},
    #     {"role": "user", "content": user_prompt},
    #     {"role": "assistant", "content": assistant_prompt},
    # ]
    def __post_init__(self):
        # Set the API key
        auth.auth_opeai()
        self.whisper_model = whisper.load_model("base")

    def get_content_type(self, content):
        content100 = content[0:100]
        valid_extensions = self.audio_file_extensions
        for ext in valid_extensions:
            if ext in str(content100).lower():
                break
        else:
            ext = 'b64'

        return ext


    def save_content(self, content):
        """ Saves content with a valid extension if possible """

        content_id = str(time.time_ns())
        ext = self.get_content_type(content)
        fname_content = os.path.join(self.path_content_b64, f"{content_id}.{ext}")
        # renaming with valid extension
        with open(fname_content, 'bw') as fp:
            fp.write(content)

        self.fname_content = fname_content

        return fname_content

    def is_audio(self, fname):
        extension = pathlib.Path(fname).suffix
        return extension[1:] in self.audio_file_extensions

    def transcribe_audio(self, fname_content):
        # TimerNs.tic('transc')
        transcription = self.whisper_model.transcribe(fname_content)
        transcription_text = transcription["text"]
        # TimerNs.toc('transc end')
        return transcription_text

    def save_transcript(self, fname_content, transcription_text):
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

    def fuzzy_intent(self, intent_a, intent_b):
        """Uses LLM to try to derminar if A ~ B """

        prompt = f"Please answer YES or NO if these messages have the same intent? Message 1: {intent_a}; Message 2: {intent_b}"
        response = self.prompt_llm(prompt)

        if "yes" in response.lower():
            return True
        elif "no" in response.lower():
            return False

        return None

    def reply_chat(self, transcription_text):

        if self.fuzzy_intent(transcription_text, "clear message history"):
            uuidstr = str(uuid.uuid1())
            shutil.copyfile(self.fname_messages, f"{self.fname_messages}.{uuidstr}.memory")
            # mode = "w"
            # old_memory = fp.read()
            os.unlink(self.fname_messages)
            return "memory cleared"


        ## timer.tic('reading old messages')
        with open(self.fname_messages, 'a+', encoding='utf-8') as fp:
            fp.seek(0)
            messages_txt = fp.read()

        messages = json.loads(f"[{messages_txt[:-1]}]")
        try:
            response = self.prompt_llm(
                prompt=transcription_text,
                system_prompt='',
                messages=messages)
        except Exception as error:
            traceback.print_exc()

            if error.code == "context_length_exceeded":
                # messages = summarize_messages(messages)

                return 'Please clear messages'

            return 'An error occurred, please try again later.'

        response = self.filter_response(response)
        role = "assistant"
        ## timer.toc('update convo')
        self.update_messages(role=role, message=response, messages=messages)

        return response

    def get_email_url(self, transcription_text):

        language = self.get_language(transcription_text)
        subject = self.summarize(transcription_text, language, words_number='six')
        joke = self.joke(transcription_text, language, joke_type='short')
        recipient = self.get_recipients(transcription_text)
        command = self.get_command(transcription_text)

        if "no" in recipient.lower():
            recipient = None
        if "no" in command.lower():
            command = None

        print(f'{command=}')
        print(f'{recipient=}')
        print(f'{subject=}')
        print(f'{joke=}')

        body=urllib.parse.quote(dedent(
            f"""{transcription_text}


            ---
            via veemail.me

            ... {joke}
            """))

        email_url = f'googlegmail:///co?subject={urllib.parse.quote(subject)}&body={body}'
        # email_url = urllib.parse.quote(f'googlegmail:///co?subject={subject}&body={body}&to={recipient}')

        return email_url

    def get_command(self, transcription_text):
        prompt = f"Please determine if the user is giving a command from this message. If you can't determine the recipient please reply with NO: {transcription_text}."
        command = self.prompt_llm(prompt)
        return command

    def get_recipients(self, transcription_text):
        """Return name of recipien or 'NO'"""
        prompt = f"Please determine name of recipient from the following message. If you can't determine the recipient please reply with NO: {transcription_text}."
        recipient = self.prompt_llm(prompt)
        return recipient

    def joke(self, transcription_text, language, joke_type='short'):
        prompt = f"Please write a {joke_type} joke about the following message in language {language}: {transcription_text}."
        joke = self.prompt_llm(prompt)
        return joke

    def summarize(self, transcription_text, language, words_number='six'):
        prompt = f"Summarize in six words or less using language {language}: {transcription_text}"
        subject = re.sub('\.[ ]*$','', self.prompt_llm(prompt))
        return subject

    def get_language(self, transcription_text):
        """Returns transcript's English language name"""

        ## timer.tic('lang')
        prompt = f"Please in one word specify the language of this message: {transcription_text}"

        language = self.prompt_llm(prompt)
        ## timer.toc('lang end')
        return language

    def prompt_llm(self, prompt, system_prompt=None, messages=None):
        ## timer.tic('prompt start')

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

        ## timer.toc('prompt end')

        return response

    def update_messages(self, role, message, messages):
        messages.append({"role": role, "content": message})
        fname = self.fname_messages
        with open(fname, mode="a+", encoding='utf-8') as fp:
            for m in messages[-2:]:
                messages = fp.write('\n' + json.dumps(m) + ',')
        ## timer.toc('update convo end')

    def filter_response(self, response):
        """Removes ome of ChatGPT's safety boilerplate"""
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
        return response

    def summarize_messages(self, messages):
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
