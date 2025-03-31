import yaml
import os


class AnythingLLMConfig:
    def __init__(self, config_path="anything_llm.yaml"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, config_path)
        self.config = self._load_config(config_path)

    def _load_config(self, config_path):
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    @property
    def url(self):
        return self.config.get("anything_llm", {}).get("url", "")

    @property
    def api_key(self):
        return self.config.get("anything_llm", {}).get("api_key", "")

    @property
    def workspace_model(self):
        return self.config.get("anything_llm", {}).get("workspace_model", "")
