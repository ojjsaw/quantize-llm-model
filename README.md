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
python convert.py --model_id Intel/neural-chat-7b-v3-3 --output_dir models/neural-chat-7b-v3-3-INT4_ASYM-0.8-128 --compress_weights INT4_ASYM --ratio 0.8 --group_size 128

python convert.py --model_id Intel/neural-chat-7b-v3-3 --output_dir models/neural-chat-7b-v3-3-INT4_SYM --compress_weights INT4_SYM
```

```bash
decoder; t5; falcon; gpt-; gpt2; aquila; mpt; open-llama; openchat; neural-chat; llama; tiny-llama; tinyllama; opt-; pythia-; stablelm-; stable-zephyr-; rocket-; blenderbot; vicuna; dolly; bloom; red-pajama; chatglm; xgen; longchat; jais; orca-mini; baichuan; qwen; zephyr; mistral; mixtral; yi-; phi-
```

```bash
akAKIA4UQN57YSV4JW5CWD
skC2vvI9eykH8/Ar3z9djhszxX8bkyswRFlY0HldGI
```

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

aws configure

upload:
aws s3 sync openvino.genai/llm_bench/python/models s3://llmragstore

download:
aws s3 sync s3://llmragstore data


```