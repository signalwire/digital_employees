Kevin - The AI Bartender
-------------------

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
 
By leveraging the `get_vector_data` function, Kevin ensures that every answer is grounded in accurate data, making him an indispensable digital employee for any business looking to automate tasks with precision and confidence, and a great co-worker.


### Function Fillers

A function filler is triggered when a specific function is executed. In this example, it specifies what happens when the function is called. The filler text can be customized to create a more personalized interaction with the end user. If defined, this custom filler will override the default filler array, making the interaction more dynamic and engaging.

```json
                "function": "get_vector_data",
                "fillers": {
                  "en-US": [
                    "This is the get vector data function firing"
                  ]
                },
```
