""" VeeMail """
from typing import Union

from fastapi import FastAPI

from VeeAi import VeeAI

app = FastAPI()


@app.get("/")
def read_root():
    # prompt = request.headers.get('prompt') or "silence?"
    return {"Hello": "Mom!"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"x_item_id": item_id, "q": q}