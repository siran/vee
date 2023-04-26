""" authenticates to modules """

import os

import boto3
import openai

def auth_opeai():
    """ Set's authentication for OpenAI libraries """

    private_key = get_openai_private_key()

    openai.api_key = private_key
    os.environ["OPENAI_API_KEY"] = private_key


def get_openai_private_key():
    """Fetches value from SSM"""

    ssm = boto3.client("ssm")
    keyname = "/openai/key"

    value = ssm.get_parameter(
        Name=keyname,
        WithDecryption=True,
    )

    return str(value['Parameter']['Value'])