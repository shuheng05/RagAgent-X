from flask import Flask, request, jsonify
import yaml
import os

app = Flask(__name__)

CONFIG_PATH = 'gpt_sovits_config.yaml'

@app.route('/update-gpt-sovits-config', methods=['POST'])
def update_gpt_sovits_config():
    data = request.json
    ref_audio_path = data.get("ref_audio_path")
    prompt_text = data.get("prompt_text")

    if not ref_audio_path and not prompt_text:
        return jsonify({"error": "Nothing to update"}), 400

    # 加载原始配置（如果存在）
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {"gpt_sovits_tts": {}}

    # 更新字段
    if ref_audio_path:
        config['gpt_sovits_tts']['ref_audio_path'] = ref_audio_path
    if prompt_text:
        config['gpt_sovits_tts']['prompt_text'] = prompt_text

    # 保存配置
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, allow_unicode=True)

    return jsonify({'status': 'success', 'message': '配置文件更新成功'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)