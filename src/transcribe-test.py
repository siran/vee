import base64
import sys
import whisper
import openai
import boto3
import os

def get_private_key():
    ssm = boto3.client("ssm")
    keyname = "/openai/key"

    value = ssm.get_parameter(
        Name=keyname,
        WithDecryption=True,
    )

    print(value)

    return str(value['Parameter']['Value'])


fname = "test.m4a"
private_key = get_private_key()
openai.api_key = private_key
os.environ["OPENAI_API_KEY"] = private_key

# transcribing
model = whisper.load_model("base")
os.chdir('assets')
transcription = model.transcribe(fname)
transcription_text = transcription["text"]

messages = [
    {"role": "system", "content": f"Please reply with one message consistint only of the summary in one sentence of the following message. The message is: {transcription_text},"},
    # {"role": "assistant", "content": "OK"},
    {"role": "user", "content": f"Please reply with one message consistint only of the summary in one sentence of the following message. The message is: {transcription_text}"},
]

r = openai.ChatCompletion.create(
    # model="gpt-3.5-turbo",
    model="gpt-3.5-turbo-0301",
    messages=messages,
    temperature=0,
)
subject = r['choices'][0]['message']['content']


print(subject)
print(transcription_text)
