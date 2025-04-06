import yaml
from pydantic import BaseModel

CONFIG_PATH = 'gpt_sovits_config.yaml'

class DynamicGPTConfig(BaseModel):
    api_url: str
    text_lang: str
    ref_audio_path: str
    prompt_lang: str
    prompt_text: str
    text_split_method: str
    batch_size: str
    media_type: str
    streaming_mode: str

    @classmethod
    def load_from_yaml(cls, path: str = CONFIG_PATH) -> "DynamicGPTConfig":
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tts_config = config.get("gpt_sovits_tts", {})
        return cls(**tts_config)
