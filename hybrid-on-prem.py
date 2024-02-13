import time
import warnings
import os
from pprint import pprint
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import AutoModel
from langchain_community.vectorstores.chroma import Chroma
from transformers import AutoTokenizer, pipeline
from optimum.intel.openvino import OVModelForCausalLM
from langchain.llms.huggingface_pipeline import HuggingFacePipeline
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain import hub
import json
import boto3

# Initialize SQS client
sqs = boto3.client('sqs')

# Specify your SQS queue URLs
source_queue_url = 'WorkItem.fifo'
target_queue_url = 'WorkItemProgress.fifo'


os.environ['HF_TOKEN'] = "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"

store_dir = 'data/VectorStores/20240130_213318'
model_id = 'data/neural-chat-7b-v3-3-INT4_SYM/pytorch/dldt/compressed_weights/OV_FP32-INT4_SYM'
embeddings_model = 'jinaai/jina-embeddings-v2-base-en'
max_new_tokens = 300

warnings.filterwarnings("ignore")

def get_cpu_name():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    # The CPU model name is on this line, split by colon
                    return line.split(":")[1].strip()
    except FileNotFoundError:
        return "CPU information not available"
    
def process_response(data, duration, user: str, question_id: str):
    response_data = { 
        "qs": data['question'], 
        "ans": data['answer'], 
        "src": [],
        "ts": f'{duration:.2f} sec',
        "usr": user,
        "id": question_id
    }
    
    for doc in data['context']:
        if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
            metadata = doc.metadata
            orig_title = metadata['title']
            mod_title = orig_title.replace("— OpenVINO™  documentation","")
            url_dict = {"txt": mod_title, "url": metadata['source']}
            if not any(source['url'] == url_dict['url'] for source in response_data['src']):
                if 'Glossary' not in url_dict['txt']:
                    response_data['src'].append(url_dict)
    return response_data

### Load embeddings
model = AutoModel.from_pretrained(embeddings_model, trust_remote_code=True)
embeddings = HuggingFaceEmbeddings(
    model_name = embeddings_model,
    model_kwargs = {'device':'cpu', 'trust_remote_code':True},
    encode_kwargs = {'normalize_embeddings': True}
)

### prompt and vector store load
vector_store = Chroma(persist_directory=store_dir, embedding_function=embeddings)
retriever = vector_store.as_retriever()
prompt = hub.pull("rlm/rag-prompt")

### llm model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = OVModelForCausalLM.from_pretrained(
    model_id=model_id, 
    device='CPU', 
    ov_config={"PERFORMANCE_HINT": "LATENCY"}
    )
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=max_new_tokens)
llm = HuggingFacePipeline(pipeline=pipe)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

### with sources
rag_chain_from_docs = (
    RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
    | prompt
    | llm
    | StrOutputParser()
)
rag_chain = RunnableParallel(
    {"context": retriever, "question": RunnablePassthrough()}
).assign(answer=rag_chain_from_docs)

cpu_name = get_cpu_name()

while True:
    # Receive a message from the "workitem" queue
    response = sqs.receive_message(
        QueueUrl=source_queue_url,
        MaxNumberOfMessages=1,  # Adjust as needed
        WaitTimeSeconds=20  # Long polling
    )

    messages = response.get('Messages', [])
    
    if not messages:
        print("No messages to process. Waiting for new messages...")
        #time.sleep(1)
        continue  # Skip to the next iteration of the loop

    for message in messages:
        try:
            # Process the message (example: extract and transform data)
            message_body = json.loads(message['Body'])

            print(message_body)
            user = message_body['usr']
            question = message_body['qs']
            question_id = message_body['id']

            start_time = time.time()
            result = rag_chain.invoke(question)
            end_time = time.time()
            duration = end_time - start_time

            new_response_body = process_response(result, duration, user, question_id)
            new_response_body['hw'] = cpu_name
        
            message_group_id = question_id
            message_deduplication_id = question_id

            # Send processed message to "workitem-progress" queue
            sqs.send_message(
                QueueUrl=target_queue_url,
                MessageBody=json.dumps(new_response_body),
                MessageGroupId=message_group_id,
                MessageDeduplicationId=message_deduplication_id
            )
            
            # Delete the processed message from the "workitem" queue
            sqs.delete_message(
                QueueUrl=source_queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            
            print(f"Processed and deleted message {message['MessageId']}")
            
        except Exception as e:
            print(f"Error processing message {message['MessageId']}: {str(e)}")
            # Handle the error (optional: could involve logging or retries)

    time.sleep(1)
