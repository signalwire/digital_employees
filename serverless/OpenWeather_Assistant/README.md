# Open Weather

![img](https://openweathermap.org/themes/openweathermap/assets/img/logo_white_cropped.png)

[Open Weather Map API](https://api.openweathermap.org) offers both [free and paid](https://openweathermap.org/full-price#current) access to weather information.  In our example, we will be using the **City/State/Country** and **ZIPCODE** API's to pull data from.

## How does it work?

The SignalWire digital employee in this example will make an api call to the openweathermap api and return data that can be used during the call with the user.  We will also give the option to send the weather details to the user via sms.

Full working example can be found [here]( https://github.com/signalwire/digital_employees/blob/main/serverless/OpenWeather_Assistant/full_example.json).

## Breaking down the example

These next sections will show each part of the JSON that comprises the entire JSON example.

## main

### [answer](https://developer.signalwire.com/sdks/reference/swml/methods/answer/)

```
Answer the call.
```

### [record_call](https://developer.signalwire.com/sdks/reference/swml/methods/record_call/)

This will record the call in stereo and in a wav format. You can also use mp3 for the format
```json
{
        "record_call": {
          "format": "wav",
          "stereo": "true"
        }
```

## [ai](https://developer.signalwire.com/sdks/reference/swml/methods/ai/)

### [params](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_params/)

debug_webhook_url will provide more verbose return of data from the webhook defined. Very useful for troubleshooting.
```json

"params": {
            "verbose_logs": "true",
            "debug_webhook_url": "https://webhook.site/b97f64b4-a7a0-44c6-b9e5-2ed0112930d6"
          },

```

[post_prompt_url](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_post_prompt_url)

The url defined to send the post prompt data to.
```json
          "post_prompt_url": "https://webhook.site/b97f64b4-a7a0-44c6-b9e5-2ed0112930d6",
          "post_prompt": {
            "top_p": 0.6,
            "temperature": 0.6,
            "text": "Summarize the conversation"
          },

```

### [pronounce](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_pronounce)
Replace an abbreviation with the full words.
```json
          "pronounce": [
            {
              "ignore_case": 0,
              "with": "miles per hour",
              "replace": "mph"
            }
          ],

```

```json
          "hints": [
            "weather",
            "forecast"
          ],

```

### [languages](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_languages/#supported-voices-and-languages)
The different languagues used, fillers words to use when executing a function and voice engine used.
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
          ],

```

## [prompt](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_prompt)

The prompt will give a set of instructions for the digital employee to use guiding the conversation and along with steps to follow.

```json

{
  "prompt": {
    "text": "You're a weather expert. You have two functions to help you get weather information for users and one function to send messages.

Ask the user for the city or zipcode they want to know the weather for.
You have to use get_weather_city if the user gives a city and state name is given or get_weather_zipcode if the user gives a 5 digit zipcode.

# Step 1
Greet the user.

# Step 2
Get the detailed forecast for the user.

# Step 3
Tell the user the detailed forecast.

# Step 4
Offer to send the details in a message to the user.

# Step 5
Ask the user if there is anything else you can help them with. Keep assisting the user until the user is ready to end the call.",
```

[Temperature](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_prompt) and [top_p](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_prompt) used.

```json
    "temperature": 0.6,
    "top_p": 0.6
  }
}

```

[SWAIG](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_swaig/)

SWAIG consists of:
* [defaults](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_swaig/defaults)
* [native_functions](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_swaig/native_functions/)
* [includes](functions)
* [functions](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_swaig/functions/)

```json

"SWAIG": {
            "defaults": {},
            "functions": [
              {
                "purpose": "use to send text messages to a user",
                "argument": {
                  "type": "object",
                  "properties": {
                    "to": {
                      "type": "string",
                      "description": "The user's number in e.164 format"
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
                                      "from_number": "+15554441234"
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
                "purpose": "use to send multimedia messages to a user",
                "argument": {
                  "properties": {
                    "to": {
                      "description": "The user's number in e.164 format",
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

```
```json

                "function": "send_mms",
                "data_map": {
                  "expressions": [
                    {
                      "pattern": ".*",
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
                                      "media": [
                                        "${args.media}"
                                      ],
                                      "body": "${args.message}, Reply STOP to stop.",
                                      "region": "us",
                                      "from_number": "+15554441234"
                                    }
                                  }
                                ]
                              }
                            }
                          }
                        ]
                      },
                      "string": "${args.message}"
                    }
                  ]
                }
              },
              {

```

### get_weather_city

This is a function that uses openweathermap.org api that queries by US city and state.

```json

               "function": "get_weather_city",
                "data_map": {
                  "webhooks": [
                    {
                      "url": "https://api.openweathermap.org/data/2.5/weather?q=${args.city},${args.state},US&units=imperial&appid=cdd2941CHANGE_ME46218144",
                      "method": "GET",
                      "output": {
                        "response": "The current weather is ${weather[0].description} with a temperature of '{Math.floor(${main.temp})}' and Longitude ${coord.lon} Latitude ${coord.lat} Weather ID ${weather[0].id} Main Weather ${weather[0].main} Weather Description ${weather[0].description} Weather Icon ${weather[0].icon} Base ${base} Temperature ${main.temp} Feels Like Temperature ${main.feels_like} Minimum Temperature ${main.temp_min} Maximum Temperature ${main.temp_max} Pressure ${main.pressure} Humidity ${main.humidity} Visibility ${visibility} Wind Speed ${wind.speed} Wind Direction ${wind.deg} Wind Gust ${wind.gust} Cloudiness ${clouds.all} Datetime ${dt} System Type ${sys.type} System ID ${sys.id} Country ${sys.country} Sunrise ${sys.sunrise} Sunset ${sys.sunset} Timezone ${timezone} Location ID ${id} Location Name ${name} Status Code ${cod}. ",
                        "action": []
                      }
                    }
                  ]
                },
                "purpose": "get weather information using city name and 2 letter state name abbreviation",
                "argument": {
                  "properties": {
                    "city": {
                      "type": "string",
                      "description": "City name."
                    },
                    "state": {
                      "type": "string",
                      "description": "2 letter state name abbreviation."
                    }
                  },
                  "type": "object"
                }
              },

```

### get_weather_zipcode

This is a function that uses openweathermap.org api that queries by US zipcode and returns json for that specific zipcode.

```json

              {
                "function": "get_weather_zipcode",
                "data_map": {
                  "webhooks": [
                    {
                      "url": "https://api.openweathermap.org/data/2.5/weather?zip=${args.zip}&units=imperial&appid=cdd2941CHANGE_ME46218144",
                      "method": "GET",
                      "output": {
                        "response": "The current weather is ${weather[0].description} with a temperature of '{Math.floor(${main.temp})}' and Longitude ${coord.lon} Latitude ${coord.lat} Weather ID ${weather[0].id} Main Weather ${weather[0].main} Weather Description ${weather[0].description} Weather Icon ${weather[0].icon} Base ${base} Temperature ${main.temp} Feels Like Temperature ${main.feels_like} Minimum Temperature ${main.temp_min} Maximum Temperature ${main.temp_max} Pressure ${main.pressure} Humidity ${main.humidity} Visibility ${visibility} Wind Speed ${wind.speed} Wind Direction ${wind.deg} Wind Gust ${wind.gust} Cloudiness ${clouds.all} Datetime ${dt} System Type ${sys.type} System ID ${sys.id} Country ${sys.country} Sunrise ${sys.sunrise} Sunset ${sys.sunset} Timezone ${timezone} Location ID ${id} Location Name ${name} Status Code ${cod}. ",
                        "action": []
                      }
                    }
                  ]
                },
                "purpose": "get detailed forecast for a location using zipcode",
                "argument": {
                  "properties": {
                    "zip": {
                      "type": "string",
                      "description": "Zipcode used to get the weather."
                    }
                  },
                  "type": "object"
                }
              }
            ]
          },

```
