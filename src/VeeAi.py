from dataclasses import dataclass
import json
import math
import openai


@dataclass
class VeeAI:
    messages = []
    # messages = [
    #     {"role": "system", "content": system_prompt},
    #     # {"role": "assistant", "content": "OK"},
    #     {"role": "user", "content": user_prompt},
    # ]

    def __post_init__(self):
        # Set the API key
        with open('private.key') as fp:
            openai.api_key = fp.read()

        # # optional initial prompt
        # with open('prompts.md', encoding="utf-8") as fp:
        #     self.instructions = fp.read()
        # self.chat_add(role="system", content=self.instructions)
        # self.chat_add(role="user", content=self.instructions)
        # self.chat_send()


    def chat_add(self, role, content):
        self._length_message += len(content)
        # if self._length_message > 3000:
        #     self.summarize_messages()
        jsonl = {
            "role": role,
            "content": content
        }

        print(f'\n{role} says: {content}\n')

        self.messages.append(jsonl)
        if "restart" in content and role == "user":
            self.messages = []
            return

        with open('memory.jsonl', 'a', encoding='utf-8') as fp:
            json.dump(jsonl, fp)
            fp.write("\n")

        a=1

    def chat_send(self):

        try:
            r = openai.ChatCompletion.create(
                # model="gpt-3.5-turbo",
                model="gpt-3.5-turbo-0301",
                messages=self.messages,
                temperature=1,
            )
            ans = r['choices'][0]['message']['content']
        except:
            # try again with fewer messages
            nmsg = len(self.messages)
            self.messages = self.messages[math.ceil(nmsg*2/3):]
            ans = "Oh, la vejez es una cosa seria. ¿Podrías repetir, por favor?"


        # if print_response:
            # print(f'(assistant says): {ans}')

        self.chat_add("assistant", ans)

        return ans
