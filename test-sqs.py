import boto3
import json
import time

# Init SQS & define urls
sqs = boto3.client('sqs')
source_queue_url = 'WorkItem.fifo'
target_queue_url = 'WorkItemProgress.fifo'
response_test_data = {
  "src": [
    {"txt":"my title1", "url":"https://myurl1"},
    {"txt":"my title2", "url":"https://myurl2"}
  ],
  "qs": "my dummy question",
  "ans": "my dummy answer",
  "ts": "120 sec",
  "id": "myuniqueid",
  "usr": "myusr"
}

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
        continue  # Skip to the next iteration of the loop

    for message in messages:
        try:
            print(message)
            # Process the message (example: extract and transform data)
            message_body = json.loads(message['Body'])

            #print(message_body)
            user = message_body['usr']
            question = message_body['qs']
            question_id = message['MessageId']

            #### testing purposes
            new_response_body = response_test_data
            new_response_body['id'] = question_id
            new_response_body['usr'] = user
            new_response_body['qs'] = question

            # simulate 120sec work
            time.sleep(90)
            
            message_group_id = 'messageGroup1'
            message_deduplication_id = 'uniqueMessageId123'

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
