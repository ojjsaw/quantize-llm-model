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

os.environ['HF_TOKEN'] = "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"

store_dir = 'data/VectorStores/20240130_213318'
model_id = 'data/neural-chat-7b-v3-3-INT4_SYM/pytorch/dldt/compressed_weights/OV_FP32-INT4_SYM'
embeddings_model = 'jinaai/jina-embeddings-v2-base-en'
max_new_tokens = 300

warnings.filterwarnings("ignore")

def process_response(data, duration):
    response_data = { 
        'qs': data['question'], 
        'ans': data['answer'], 
        'sources': [],
        'duration': f'{duration:.2f} sec'}
    
    for doc in data['context']:
        if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
            metadata = doc.metadata
            url_dict = {'title': metadata['title'], 'url': metadata['source']}
            if not any(source['url'] == url_dict['url'] for source in response_data['sources']):
                if 'Glossary' not in url_dict['title']:
                    response_data['sources'].append(url_dict)
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

while True:
    question = input("Enter your question (or 'exit' to quit): ")
    if question.lower() == 'exit':
        print("Exiting...")
        break

    start_time = time.time()
    result = rag_chain.invoke(question)
    end_time = time.time()
    duration = end_time - start_time

    response = process_response(result, duration)
    pprint(response)
