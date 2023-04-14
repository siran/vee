import base64
import whisper

import os
fname = "test.m4a"

# transcribing
model = whisper.load_model("base")
os.chdir('assets')
transcription = model.transcribe(fname)

print(transcription["text"])
