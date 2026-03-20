Kevin - The AI Bartender
-------------------

<div align="center">
  <img src="https://github.com/user-attachments/assets/a909652f-6d3c-4a60-903d-850ec97aaba8" alt="your-image-description" width="200"/>
</div>


### Introducing Kevin, the Digital Employee for Bartending

Meet Kevin, the digital employee designed to serve as your personal bartender. Kevin is equipped with smart functions and structured responses to enhance the user experience, especially when it comes to crafting the perfect drink.

 
#### Key Features:
1. `Call Recording`: Kevin records conversations in high-quality stereo `.wav` format, ensuring that important details are captured for future reference.
2. `Conversational Abilities`: Kevin engages in dynamic conversations, asking the right questions and providing accurate answers based on available data.
    - `Customizable Prompts`: Kevin's responses follow a structured prompt system. He greets users, asks what drink they'd like to make, and provides clear instructions. 
    - `Post-Prompt Handling`: After the conversation, Kevin summarizes the interaction and can send a message with the details to the user.
    - `Language Support`: Kevin can communicate in multiple languages, powered by the OpenAI engine. In English, Kevin uses fillers like "one moment, please" to keep the conversation flowing naturally.
 
 3. `SWAIG Functions`: Kevin is integrated with ``send_message`` and `get_vector_data` functions to deliver information and perform actions seamlessly.
    - `Send Text Messages`: Kevin can send messages with drink instructions or summaries of the conversation directly to the user's phone.
    - `Get Vector Data`: The `get_vector_data` function is a powerful feature that allows Kevin to retrieve specific information from a vectorized PDF based on user queries. When a user asks a question, Kevin references the vectorized data and provides an accurate answer, ensuring he doesn't fabricate details. This function is especially useful for situations where Kevin needs to rely on predefined processes or detailed procedures.
 
 4. `Digital Employee Precision`: With customizable parameters like verbosity, temperature, and top-p, Kevin is designed to interact in a professional, reliable manner that mirrors human interactions—perfect for following strict processes and procedures.
 
By leveraging the `get_vector_data` function using the SignalWire Datasphere API is, Kevin ensures that every answer is grounded in accurate data, making him an indispensable digital employee for any business looking to automate tasks with precision and confidence, and a great co-worker.

### [DataSphere API](https://developer.signalwire.com/rest/signalwire-rest/guides/datasphere/curl-usage/)

Kevin is using SignalWire's new Datasphere API in a custom-built Retrieval-Augmented Generation (RAG) stack empowering developers to upload, manipulate, and retrieve information in the context of a SignalWire application. Click here for more information on [SignalWire's Datasphere API](https://developer.signalwire.com/rest/signalwire-rest/guides/datasphere/curl-usage/)


get_vector_data
-----------------

### `get_vector_data` Function:

This JSON block defines a function called `get_vector_data`, which is designed to retrieve and use vectorized data from a specific document via a webhook call.

#### 1. **Function Name: `get_vector_data`**
   - The function is responsible for fetching vectorized data based on a user’s question.

#### 2. **Fillers**
   - **Purpose**: These are placeholder texts or responses used by the system when this function is triggered. 
   - **Filler Example**: "This is the get vector data function firing" — this will be spoken or displayed when the function starts running.

#### 3. **Data Map**
   - The **data map** is where the function sends a request to an external service (webhook) to retrieve data.
   - **Webhook Configuration**:
     - **Method**: The HTTP method used is `POST`, meaning the function will send data to the webhook.
     - **URL**: `https://space_name.signalwire.com/api/datasphere/documents/search` — the API endpoint to which the request is sent.
     - **Headers**: Metadata for the API call:
       - `Content-Type`: Specifies that the data sent in the body of the request is in JSON format.
       - `Authorization`: Uses a `Basic` authentication header. The `Project_ID` and `API_KEY` should be base64-encoded to create proper credentials for this API call.
   - **Params**: Parameters included in the POST request:
     - `query_string`: The user’s question that is passed in.
     - `document_id`: A specific ID (`694ced7b-b656-417e-bc86-ce22549b4562`) that identifies which document to search for the query.
     - `count`: Specifies the maximum number of results to return (in this case, 5).
   - **Output**:
     - **Response**: The function will extract specific data from the response of the webhook call. In this case, it returns the first chunk of text from the search results and its corresponding `document_id`.
     - **Action**: This field is an empty array, you could use another SWML here to send a sms or trigger a call etc.

#### 4. **Purpose**
   - This section describes the purpose of the function: to handle the question a user asks and retrieve relevant vectorized data from the specified document.

#### 5. **Argument**
   - **Type**: Object — the function expects an object-type argument.
   - **Properties**:
     - **`user_question`**: 
       - **Type**: string — the function accepts the user’s question as a string input.
       - **Description**: The user’s question .




```json

{
  "function": "get_vector_data",
  "fillers": {
    "en-US": [
      "This is the get vector data function firing"
    ]
  },
  "data_map": {
    "webhooks": [
      {
        "method": "POST",
        "url": "https://space_name.signalwire.com/api/datasphere/documents/search",
        "headers": {
          "Content-Type": "application/json",
          "Authorization": "Basic OGVhMjI0YzktM--USE--Project_ID:API_KEY--TO-BASE64-ENCODE--NkYjFh"
        },
        "params": {
          "query_string": "${args.user_question}",
          "document_id": "694ced7b-b656-417e-bc86-ce22549b4562",
          "count": 1
        },
        "output": {
          "response": "Use this information to answer the user's query, only provide answers from this information and do not make up anything: ${chunks[0].text} and ${chunks[0].document_id}",
          "action": []
        }
      }
    ]
  },
  "purpose": "The question the user will ask",
  "argument": {
    "properties": {
      "user_question": {
        "type": "string",
        "description": "The question the user will ask."
      }
    },
    "type": "object"
  }
}

```
