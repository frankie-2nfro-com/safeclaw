import json

from libs.base_skill import BaseSkill


class MongchoiUpdateSkill(BaseSkill):
    """MONGCHOI_UPDATE: print whole request and return."""

    def execute(self, params: dict):
        request_info = {"action": "MONGCHOI_UPDATE", "params": params}
        print(json.dumps(request_info, indent=2, ensure_ascii=False))
        return {"status": "Executed", "text": "Mongchoi update executed."}
