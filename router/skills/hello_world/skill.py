from libs.base_skill import BaseSkill


class HelloWorldSkill(BaseSkill):
    def execute(self, params: dict):
        print("executing router command HELLO_WORLD and return STATUS Executed!")
        return {"status": "Executed", "text": "Hello World!"}
