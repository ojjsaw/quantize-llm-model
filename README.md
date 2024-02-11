# quantize-llm-model

alter carbon
elite
class

```bash
git clone https://github.com/openvinotoolkit/openvino.genai.git
cd openvino.genai/llm_bench/python
pip install -r requirements.txt
```

```bash
python convert.py --model_id 'Intel/neural-chat-7b-v3-3' --output_dir models/neural-chat-7b-v3-3 --compress_weights INT4_ASYM --ratio 0.8 --group_size 128
```

```bash
decoder; t5; falcon; gpt-; gpt2; aquila; mpt; open-llama; openchat; neural-chat; llama; tiny-llama; tinyllama; opt-; pythia-; stablelm-; stable-zephyr-; rocket-; blenderbot; vicuna; dolly; bloom; red-pajama; chatglm; xgen; longchat; jais; orca-mini; baichuan; qwen; zephyr; mistral; mixtral; yi-; phi-
```