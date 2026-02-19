from libs.base_skill import BaseSkill


class HelloWorldSkill(BaseSkill):
    def execute(self, params: dict):
        return {"status": "Executed", "text": "Hello World!"}
