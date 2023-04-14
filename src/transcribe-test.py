import base64

import whisper

import os
timestamp="1681410347459064600"
fname = f"{timestamp}.b64.m4a"

# transcribing
model = whisper.load_model("base")
os.chdir('assets')
transcription = model.transcribe(fname)

print(transcription["text"])
