# Weather-Bot

![image](https://github.com/Len-PGH/Weather-Bot/assets/13131198/4010e5c6-bea1-4455-98b7-b810a88bc00b)


## Exploring the SignalWire Weather Bot AI Configuration JSON

In this exploration, we examine a detailed JSON configuration structured to enable AI-powered interactions, focusing on communication and information retrieval tasks. This configuration is rich in functionalities, including voice recording, customizable AI behavior, and specialized tasks such as sending messages and fetching weather information. For the full [SWML example click here](https://github.com/Len-PGH/Weather-Bot/blob/main/swml.md).

## Sections Overview

The configuration is structured under a sections key, encapsulating different operational blocks within the main array. Each block serves a unique purpose, ranging from voice recording settings to complex AI operations.

## Answer Block

```json

{
  "answer": {}
}


```

* Description: This block Answers the call.

---------------------

## Record Call Block

```json

{
  "record_call": {
    "format": "wav",
    "stereo": "true"
  }
}


```

* Description: This section instructs the system to record calls in WAV format with stereo audio quality. It's crucial for applications that require audio analysis, quality assurance, or legal compliance.

----------------------------

Diving deeper into the AI Configuration Block, we'll explore each component in detail, focusing on how each part contributes to the overall functionality of the AI system.

## AI Configuration Block Detailed Breakdown

## Post-Prompt Configuration

```json
"post_prompt_url": "https://webhook.site/a6196db2-75c2-4c36-98bf-e31245"

```
```json
"post_prompt_auth_password": "this-is-optional-password"
```
```json
"post_prompt_auth_user": "this-is-an-optional-user"
```

* Description: These configurations define the endpoint (`post_prompt_url`) and the authentication details (`post_prompt_auth_password`, `post_prompt_auth_user`) for the AI to communicate with after executing the prompt's instructions, ensuring secured data transmission.


----------------------------

## (params) Parameters

```json
"params": {
  "verbose_logs": "true",
  "debug_webhook_url": "https://this-is-an-optional-user:this-is-optional-password@webhook.site/a6196db2-75c2-4c36-98bf-e31245"
}
```

* Description: Enables detailed logging (`verbose_logs`) for debugging and specifies a webhook URL (`debug_webhook_url`) for sending debug information. This setup is crucial for monitoring and troubleshooting the AI's operations.


----------------------------

## (post_prompt) Prompt 

```json
"post_prompt": {
  "top_p": 0.6,
  "temperature": 0.6,
  "text": "Summarize the conversation"
}
```
* Description: Dictates the AI's task to summarize the conversation, adjusting creativity and randomness with `top_p` and `temperature`. This guides the AI in generating concise summaries of interactions.


----------------------------

## (pronounce) Pronunciation Adjustments

```json
"pronounce": [
  {
    "ignore_case": 0,
    "with": "miles per hour",
    "replace": "mph"
  }
]
```

* Description: Customizes how the AI interprets and vocalizes "mph," ensuring clarity in pronunciation by expanding abbreviations where necessary.


----------------------------

## Hints

```json
"hints": [
  "weather",
  "forecast"
]
```

* Description: Provides contextual hints to the AI, focusing its responses and capabilities around weather-related queries and information.


----------------------------

## Languages

```json
"languages": [
  {
    "code": "en-US",
    "voice": "Rachel",
    "name": "English",
    "fillers": [
      "one moment",
      "one moment please"
    ],
    "engine": "elevenlabs"
  }
]
```

* Description: Configures the AI's language settings, including dialect, voice, and phrases for natural interactions, utilizing the elevenlabs engine for speech synthesis. When a function executes the AI Agent will say one of the fillers.


----------------------------

## SWAIG Defaults

```json
"SWAIG": {
  "defaults": {
    "web_hook_url": "https://webhook.site/a6196db2-75c2-4c36-98bf-e31245",
    "web_hook_auth_password": "this-is-optional-password",
    "web_hook_auth_user": "this-is-an-optional-user"
  }
}
```

* Description: Sets default webhook configurations for the AI, streamlining external communications for all functions defined within the SWAIG framework.


----------------------------

## Function: Send Text Message

* **Name:**`send_message`

```json
{
  "purpose": "use to send text messages to a user",
  "argument": {
    "type": "object",
    "properties": {
      "to": {
        "type": "string",
        "description": "The users number in e.164 format"
      },
      "message": {
        "description": "the message to send to the user",
        "type": "string"
      }
    }
  },
  "data_map": {
    "expressions": [
      {
        "string": "${args.message}",
        "output": {
          "response": "Message sent.",
          "action": [
            {
              "SWML": {
                "version": "1.0.0",
                "sections": {
                  "main": [
                    {
                      "send_sms": {
                        "to_number": "${args.to}",
                        "region": "us",
                        "body": "${args.message}, Reply STOP to stop.",
                        "from_number": "+19184052049"
                      }
                    }
                  ]
                }
              }
            }
          ]
        },
        "pattern": ".*"
      }
    ]
  },
  "function": "send_message"
}
```

* Description: This function allows the AI to send SMS messages to users, leveraging user inputs for the recipient's phone number and message content. It showcases the use of SignalWire Markup Language (SWML) to structure the message sending action.


----------------------------

## Function: Send Multimedia Message

* **Name:**`send_mms`

```json
{
  "purpose": "use to send text messages to a user",
  "argument": {
    "properties": {
      "to": {
        "description": "The users number in e.164 format",
        "type": "string"
      },
      "message": {
        "description": "the message to send to the user",
        "type": "string"
      },
      "media": {
        "description": "the media URL to send to the user",
        "type": "string"
      }
    },
    "type": "object"
  },
  "function": "send_mms",
  "data_map": {
    "expressions": [
      {
        "pattern": ".*",
        "output": {
          "action": [
            {
              "SWML": {
                "version": "1.0.0",
                "sections": {
                  "main": [
                    {
                      "send_sms": {
                        "to_number": "${args.to}",
                        "media": ["${args.media}"],
                        "body": "${args.message}, Reply STOP to stop.",
                        "region": "us",
                        "from_number": "+19184052049"
                      }
                    }
                  ]
                }
              }
            }
          ],
          "response": "Message sent."
        },
        "string": "${args.message}"
      }
    ]
  }
}
```

* Description: Expands upon the SMS functionality to include the capability of sending multimedia content along with text messages. It demonstrates how to include media URLs in the message payload for a more engaging user experience.


----------------------------

## Function: Get Latitude and Longitude

* **Name:**`get_lat_lon`

```json
{
  "function": "get_lat_lon",
  "data_map": {
    "webhooks": [
      {
        "method": "GET",
        "output": {
          "response": "The latitude is ${array[0].lat}, longitude is ${array[0].lon} for ${input.args.city}, ${input.args.state}",
          "action": [
            {
              "back_to_back_functions": "true"
            }
          ]
        },
        "url": "https://nominatim.openstreetmap.org/search?format=json&q=${enc:args.city}%2C${enc:args.state}"
      }
    ]
  },
  "purpose": "latitude and longitude for any city or state",
  "argument": {
    "properties": {
      "state": {
        "type": "string",
        "description": "Two letter US state code"
      },
      "city": {
        "type": "string",
        "description": "City name"
      }
    },
    "type": "object"
  }
}
```

* Description: Fetches geographic coordinates (`latitude and longitude`) for a given city or state. This function showcases the integration with external APIs (OpenStreetMap) to retrieve location data, essential for weather-related inquiries.


----------------------------

## Function: Get Weather Point

* **Name:**`get_weather_point`

```json
{
  "function": "get_weather_point",
  "data_map": {
    "webhooks": [
      {
        "url": "https://api.weather.gov/points/${enc:args.lat},${enc:args.lon}",
        "output": {
          "action": [
            {
              "back_to_back_functions": "true"
            }
          ],
          "response": "Now use get_weather_detailed_forecast function to get the forecast using this URL ${properties.forecast} as the argument."
        },
        "method": "GET"
      }
    ]
  },
  "purpose": "latitude and longitude for any city",
  "argument": {
    "properties": {
      "lon": {
        "type": "string",
        "description": "Longitude to four decimal places."
      },
      "lat": {
        "description": "Latitude to four decimal places.",
        "type": "string"
      }
    },
    "type": "object"
  }
}
```

* Description: Utilizes the geographic coordinates to fetch a specific weather forecast point from the National Weather Service. This function serves as a bridge to obtaining detailed weather forecasts by providing a URL for further querying.


----------------------------

## Function: Get Weather Detailed Forecast

* **Name:**`get_weather_detailed_forecast`

```json
{
  "function": "get_weather_detailed_forecast",
  "data_map": {
    "webhooks": [
      {
        "url": "${args.url}",
        "method": "GET",
        "output": {
          "response": "${properties.periods[0].detailedForecast}"
        }
      }
    ]
  },
  "purpose": "get detailed forecast for a location using forecast URL",
  "argument": {
    "properties": {
      "url": {
        "type": "string",
        "description": "complete forecast URL"
      }
    },
    "type": "object"
  }
}
```
* Description: This function directly queries a detailed forecast for a specific location using a URL obtained from the previous step (`get_weather_point`). It exemplifies how to navigate from obtaining latitude and longitude to fetching and presenting a detailed weather forecast to the user.


----------------------------

-----------------------------

### SignalWire

#### SignalWire’s AI Agent for Voice allows you to build and deploy your own digital employee. Powered by advanced natural language processing (NLP) capabilities, your digital employee will understand caller intent, retain context, and generally behave in a way that feels “human-like”.  In fact, you may find that it behaves exactly like your best employee, elevating the customer experience through efficient, intelligent, and personalized interactions.


