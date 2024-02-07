```json

{
  "sections": {
    "main": [
      {
        "answer": {}
      },
      {
        "record_call": {
          "format": "wav",
          "stereo": "true"
        }
      },
      {
        "ai": {
          "params": {
            "verbose_logs": "true",
            "debug_webhook_url": "https://this-is-an-optional-user:this-is-optional-password@webhook.site/a6196db2-75c2-4c36-98bf-e31245"
          },
          "post_prompt_url": "https://webhook.site/a6196db2-75c2-4c36-98bf-e31245",
          "post_prompt_auth_password": "this-is-optional-password",
          "post_prompt": {
            "top_p": 0.6,
            "temperature": 0.6,
            "text": "Summarize the converstation"
          },
          "post_prompt_auth_user": "this-is-an-optional-user",
          "pronounce": [
            {
              "ignore_case": 0,
              "with": "miles per hour",
              "replace": "mph"
            }
          ],
          "hints": [
            "weather",
            "forecast"
          ],
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
          ],
          "SWAIG": {
            "defaults": {
              "web_hook_url": "https://webhook.site/a6196db2-75c2-4c36-98bf-e31245",
              "web_hook_auth_password": "this-is-optional-password",
              "web_hook_auth_user": "this-is-an-optional-user"
            },
            "functions": [
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
              },
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
                                      "media": [
                                        "${args.media}"
                                      ],
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
              },
              {
                "function": "get_lat_lon",
                "data_map": {
                  "webhooks": [
                    {
                      "method": "GET",
                      "output": {
                        "response": "The lattitude is ${array[0].lat}, longitude is ${array[0].lon} for ${input.args.city}, ${input.args.state}",
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
                "purpose": "lattitude and logitude for any city or state",
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
              },
              {
                "argument": {
                  "properties": {
                    "lon": {
                      "type": "string",
                      "description": "Longitude to four decimal places."
                    },
                    "lat": {
                      "description": "Lattitude to four decimal places.",
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "purpose": "lattitude and logitude for any city",
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
                "function": "get_weather_point"
              },
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
                      "description": "complete forcast URL"
                    }
                  },
                  "type": "object"
                }
              }
            ]
          },
          "prompt": {
            "text": "You're a weather expert, You have three functions to help you get weather information for users.\r\n\r\nYou have to use get_lat_lon function, to get the lattitude and logitude by city and state\r\nThen you have to use get_weather_point, that takes lattitude and logitude to get the detailed weather URL\r\nFinally you use get_weather_detailed_forecast, that takes the URL from get_weather_point\r\n\r\n# Step 1\r\nGreet the user\r\n\r\n# Step 2\r\nGet the detailed forecast for the user\r\n\r\n# Step 3\r\nTell the user the detailed forcast\r\n\r\n# Step 4\r\nOffer to send the details in a message to the user",
            "temperature": 0.6,
            "top_p": 0.6
          }
        }
      }
    ]
  },
  "version": "1.0.0"
}
```
