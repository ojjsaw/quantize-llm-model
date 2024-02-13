import uuid
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Union, Optional
from pydantic import BaseModel
import boto3
import json
import time
from fastapi.staticfiles import StaticFiles

# Init SQS & define urls
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
table_name = 'llmrag'
table = dynamodb.Table(table_name)

source_queue_url = 'WorkItem.fifo'
target_queue_url = 'WorkItemProgress.fifo'

app = FastAPI(
    title='OpenVINO Docs Q&A API',
    description='<ul> <li> Quantized INT4 LLM model with convert.py from openvino.genai repo. </li> \
    <li> optimum-intel[openvino] with langchain_community for RAG </li> \
    <li> Chroma used as vector db containing all content OpenVINO 2023.3 documentation (~5k pages). </li> </ul> \
    <p>This is a hybrid deployment with FastAPI (anywhere-client) \
    -> AWS SQS (Workitems Queue) -> (User Query) On-Prem Processing (Response) -> AWS SQS (WorkitemsResults Queue) -> AWS Lambda Function Trigger -> \
    AWS DynamoDB (NoSQL Q&A store).</p>'
)

app.mount("/static", StaticFiles(directory="static"), name="static")

def generate_unique_id():
    # Current timestamp in a readable format (you can adjust the format as needed)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # Generate a random UUID and convert to a string
    random_uuid = str(uuid.uuid4())
    # Combine timestamp and a portion of the UUID to increase uniqueness
    unique_id = f"{timestamp}-{random_uuid.split('-')[0]}"
    return unique_id

SECRET_KEY = "a_very_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.post("/api/login", tags=["Session"])
def login(user_id: str, response: Response):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user_id}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {"message": "Login successful"}

@app.post("/api/ask", tags=["Q&A"])
def ask_question(request: Request, question: str):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Not authenticated")
    token = token.split(" ")[1]  # Remove "Bearer" prefix
    user_id = verify_token(token)
    question_id = generate_unique_id()
    data = { 'usr': user_id, 'qs': question, 'id': question_id}

    message_group_id = question_id
    message_deduplication_id = question_id

    response = sqs.send_message(
        QueueUrl=source_queue_url,
        MessageBody=json.dumps(data),
        MessageGroupId=message_group_id,
        MessageDeduplicationId=message_deduplication_id
    )

    data = {"user": user_id, "question": question, "identifier": question_id}
    return data

@app.post("/api/response", tags=["Q&A"])
def check_response(request: Request, question_id: str):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Not authenticated")
    token = token.split(" ")[1]  # Remove "Bearer" prefix
    user_id = verify_token(token)
    
    response = table.get_item(
        Key={
            'id': question_id
        }
    )
    item = response.get('Item', {})
    
    if item:
        print(user_id)
        print(item['messageBody'])
        if item['messageBody']['usr'] != user_id:
            raise HTTPException(status_code=400, detail=f"Response is not intended for user {user_id}")
        return {"answer_found": True, "data": item['messageBody']}
    else:
        return {"answer_found": False, "question_id": question_id, "status": "queued or processing"}

@app.post("/api/logout", tags=["Session"])
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}

@app.get("/api/is_valid_session", tags=["Troubleshoot"])
def read_users_me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Not authenticated")
    token = token.split(" ")[1]  # Remove "Bearer" prefix
    user_id = verify_token(token)
    return {"user_id": user_id}

@app.get("/static", tags=["Troubleshoot"])
async def root():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)