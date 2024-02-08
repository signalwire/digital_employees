```
{
  "sections": {
    "main": [
      {
        "answer": {}
      },
      {
        "record_call": {
          "stereo": "true",
          "format": "wav"
        }
      },
      {
        "ai": {
          "post_prompt_auth_password": "change-me",
          "post_prompt_url": "https://change-me.tld",
          "post_prompt": {
            "top_p": 0.1,
            "text": "Summerize the conversation",
            "temperature": 0.1
          },
          "agent_meta_data": {
            "agent_id": "43"
          },
          "languages": [
            {
              "voice": "josh",
              "fillers": [
                "one moment",
                "one moment please"
              ],
              "code": "en-US",
              "engine": "elevenlabs",
              "name": "English"
            }
          ],
          "params": {
            "swaig_post_swml_vars": "true",
            "swaig_post_conversation": "true",
            "swaig_allow_settings": "true",
            "debug_webhook_url": "https://change-me:change-me@change-me.tld",
            "openai_asr_engine": "deepgram",
            "swaig_allow_swml": "true",
            "local_tz": "America/New_York"
          },
          "prompt": {
            "temperature": 0.1,
            "text": "# Personality and Introduction\r\n\r\nYour name is Ziggy a digital employee for Ziggy's attic temperature and humidity sensor powered by SignalWire. Greet the user with that information\r\n\r\n# Your Functions, Skills, Knowledge, and Behavior\r\nDHT11 sensor\r\nESP8266\r\n\r\n# Numbers\r\nAlways use E.164 format\r\n\r\n# Step 1\r\n\r\nGet the temperature and humidity values\r\n\r\n# Step 2\r\n\r\nIf the users asks, send a message with the temperature and humidity",
            "top_p": 0.1
          },
          "SWAIG": {
            "defaults": {
              "web_hook_auth_password": "change-me",
              "web_hook_url": "https://change-me.tld",
              "web_hook_auth_user": "change-me"
            },
            "functions": [
              {
                "active": "true",
                "argument": {
                  "properties": {
                    "query": {
                      "type": "string",
                      "description": "what you're asking for"
                    }
                  },
                  "type": "object"
                },
                "function": "sensor_data",
                "purpose": "Get temperature and humidity"
              },
              {
                "argument": {
                  "properties": {
                    "to": {
                      "type": "string",
                      "description": "The users number in e.164 format"
                    },
                    "message": {
                      "type": "string",
                      "description": "the message to send to the user"
                    }
                  },
                  "type": "object"
                },
                "function": "send_message",
                "data_map": {
                  "expressions": [
                    {
                      "pattern": ".*",
                      "output": {
                        "action": [
                          {
                            "SWML": {
                              "sections": {
                                "main": [
                                  {
                                    "send_sms": {
                                      "body": "${args.message}, Reply STOP to stop.",
                                      "from_number": "+16814853669",
                                      "to_number": "${args.to}"
                                    }
                                  }
                                ]
                              },
                              "version": "1.0.0"
                            }
                          }
                        ],
                        "response": "Message sent."
                      },
                      "string": "${args.message}"
                    }
                  ]
                },
                "purpose": "use to send text messages to a user"
              }
            ]
          },
          "post_prompt_auth_user": "change-me"
        }
      }
    ]
  },
  "version": "1.0.0"
}
```
