let jwtToken = '';
let server_url = 'https://localhost:8000'
function toggleChatWindow() {
    const chatContent = document.getElementById('chat-content');
    chatContent.style.display = chatContent.style.display === 'none' ? 'block' : 'none';
}

async function loginAndGetToken() {
    // Replace with your login API URL and credentials
    user_id = Date.now().toString()
    const login_url = '/api/login?user_id=' + user_id;
    const response = await fetch(login_url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: user_id }),
        credentials: 'include'
    });

    if (response.ok) {
        displayMessage('Login success.' + user_id, 'bot');
        console.log("success login")
    }else{
        console.log("fail login")
    }
    
    // const data = await response.json();
    // jwtToken = data.jwtToken;  // Adjust based on your API response structure
}

async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value;
    userInput.value = '';  // Clear input field

    const encodedQuestion = encodeURIComponent(message);
    const ask_url = '/api/ask?question=' + encodedQuestion;
    console.log(ask_url)
    const questionResponse = await fetch(ask_url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({question: message}),
        credentials: 'include'
    });

    if (!questionResponse.ok) {
        displayMessage('Error sending message.', 'bot');
        return;
    }

    // Simulate thinking animation
    displayMessage('...', 'bot');

    // Extract question_id from the response
    const data = await questionResponse.json();
    console.log(data)

    const question_id = encodeURIComponent(data.identifier);
    
    const answer_url = '/api/response?question_id=' + question_id;
    console.log(answer_url)
    // Function to poll for the answer
    const getAnswer = async () => {
        const answerResponse = await fetch(answer_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({question_id: question_id}),
            credentials: 'include'
        });

        if (!answerResponse.ok) {
            displayMessage('Error getting answer.', 'bot');
            return;
        }

        const answerData = await answerResponse.json();
        console.log(answerData)
        // Check if answer is available, if not, keep polling
        if (answerData.answer_found) { // Adjust condition based on how your API indicates answer is ready
            displayMessage(answerData.answer, 'bot'); // Display the answer
        } else {
            // If answer not yet available, poll again after 30 seconds
            setTimeout(getAnswer, 20000);
        }
    };

    // Start polling for the answer
    getAnswer();
}

function displayMessage(message, sender) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.textContent = message;
    messageDiv.className = sender;  // Use this class to style messages differently
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;  // Scroll to the latest message
}

// Call loginAndGetToken when the script loads
loginAndGetToken();
