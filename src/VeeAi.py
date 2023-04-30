from dataclasses import dataclass, field
import base64
import json
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

import identity

@dataclass
class Device:
    messages : list[dict] = field(default_factory=list[dict])
    # messages = [
    #     {"role": "system", "content": system_prompt},
    #     {"role": "user", "content": user_prompt},
    #     {"role": "assistant", "content": assistant_prompt},
    # ]
    name = None
    device_name = None
    device_password = None
    device_authenticated= False


@dataclass
class VeeAI:
    """Contral control structure for Vees behavior"""

    path_content_b64 = "src/assets"
    path_devices = "src/devices"

    audio_file_extensions = ['m4a', 'mp4', 'ogg']

    device: Device = None

    fname_messages = 'messages.jsonl'
    fname_device_metadata = "device_info.json"

    fname_content = None

    whisper_model = None

    def __post_init__(self):
        # Set the API key
        identity.auth_opeai()
        self.device = Device()
        self.whisper_model = whisper.load_model("base")

    def greet_request(self, json_payload):
        """Greets request"""


        device_name = json_payload.get('deviceName')
        inputb64 = json_payload.get('inputb64')
        input = None
        transcription_text = None
        fname_input = None
        prompt = None

        if inputb64 and (input := base64.b64decode(inputb64)):
            fname_input = self.save_content(input)

        if fname_input and not self.is_audio(fname_input):
            return 'Sorry, only processing audio for the moment'

        if fname_input:
            transcription_text = self.transcribe_audio(fname_input)
            self.save_transcript(fname_input, transcription_text)
            prompt = transcription_text


        if not device_name and not prompt:
            return "Hello, there. How can I help?"

        if device_name and not prompt:
            self.device.device_name = device_name
            return self.greet_device(prompt)


        intent = self.determine_intent(prompt)

        create_archive = self.fuzzy_intent(
            prompt,
            "create or create an archive"
        )

        if create_archive:
            self.create_archive()
            return "OK, created archive. Thank you. Please set a password. Please command me like 'I want to create a password' or anything of the sort."

        return self.prompt_llm(prompt=prompt)

    def determine_intent(self, prompt):
        """Uses an LLM to return a JSON object with the 'intent' of User"""

        system_prompt = "Please analize the following message and return a valid JSON object that summarizes the intent of the user. Neccesary keys are: action, action_body, recipients_of_action. You can include other keys relevant to the message."

        json_intent = self.prompt_llm(
            prompt=prompt,
            system_prompt=system_prompt,
        )
        print(json_intent)
        a=1

    def create_archive(self):
        """Makes archive path"""

        if os.path.exists(self.device_path):
            return False

        os.mkdir(self.device_path)

        return True

    def get_device_path(self):
        """Return path for device's assets"""

        self.device_path = os.path.join(self.path_devices, self.device.device_name)
        return self.device_path

    def authenticate(self):
        self.device.device_authenticated = True
        return True

    def greet_device(self, prompt):
        """Checks if device has:
            - an 'archive' (path in FS)
                - a password
            - just record a message
        """

        devicePath = self.get_device_path()

        if not os.path.exists(devicePath):
            msg = "Hi, you don't seem to have an archive. Do you want to create one or just record a message? Please let me know next what you want to do. I'll try to help."
            return msg

        if not self.device.device_password:
            self.authenticate()

        if not self.device.device_authenticated:
            return "Sorry, you don't seem to be authenticated. Please try again."

        # at this point:
        #   devicePath exists
        #   device is authenticated

        self.get_device_info()

        instructions = self.load_instructions()

        params = dict(
            prompt="Hi, I am user, please do as SYSTEM says. Thank you.",
            system_prompt=instructions
        )

        return self.prompt_llm(**params)

    def load_instructions(self):
        with open('src/instructions_system_prompt.txt', 'r', encoding="utf-8") as fp:
            instructions = fp.read()

        return instructions

    def get_device_info(self):
        """Get metadata information stored from device in devices archive"""

        llm_responses = []
        metainfo_fname = os.path.join(self.device_path, self.fname_device_metadata)

        if not os.path.exists(metainfo_fname):
            return False

        metainfo = json.load(open(metainfo_fname))

        self.name = metainfo.get('name')
        if not self.name:
            prompt = f"Please reply with a simple and funny one word alias for this device_name or come up with an original one word alias: {self.device.device_name}"
            self.name_autogenerated = self.prompt_llm(prompt=prompt)
            self.name = self.alias_autogenerated

            llm_responses.append(f"It appears you have not told me your name. For simplicity I'll call you {self.name}. Remember you can always instruct me to call you however you want." )

        self.device.messages = metainfo.get('name')

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
        if not fname:
            return False

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
            return self.clear_messages()

        messages = self.load_user_messages()
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

    def clear_messages(self):
        uuidstr = str(uuid.uuid1())
        shutil.copyfile(self.fname_messages, f"{self.fname_messages}.{uuidstr}.memory")
            # mode = "w"
            # old_memory = fp.read()
        os.unlink(self.fname_messages)

        return "Memory cleared."

    def load_user_messages(self):
        """Return JSON user's message history from self.fname_messages"""

        if os.path.exists(self.fname_messages):
            with open(self.fname_messages, 'a+', encoding='utf-8') as fp:
                fp.seek(0)
                self.device.messages = fp.read()
                messages_txt = self.device.messages

                self.device.messages = json.loads(f"[{messages_txt[:-1]}]")

        return self.device.messages

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

        if system_prompt:
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
