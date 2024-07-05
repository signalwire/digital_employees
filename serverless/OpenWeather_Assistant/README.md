# Open Weather

![img](https://openweathermap.org/themes/openweathermap/assets/img/logo_white_cropped.png)

[Open Weather Map API](https://api.openweathermap.org) offers both [free and paid](https://openweathermap.org/full-price#current) access to weather information.  In our example, we will be using the **City** and **ZIPCODE** API's to pull data from.

## How does it work?

The SignalWire digital employee in this example will make an api call to the openweathermap api and return data that can be used during the call with the user.  We will also give the option to send the details to the user via sms.

Full working example can be found [here]( https://github.com/signalwire/digital_employees/blob/main/serverless/OpenWeather_Assistant/full_example.json).

## Breaking down the example

These next sections will show each part of the JSON that comprises the entire JSON example.

## main

## [answer:](https://developer.signalwire.com/sdks/reference/swml/methods/answer/) Answer the call (optional)

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

```json

"params": {
            "verbose_logs": "true",
            "debug_webhook_url": "https://webhook.site/b97f64b4-a7a0-44c6-b9e5-2ed0112930d6"
          },

```

[post_prompt_url](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_post_prompt_url)
```json
          "post_prompt_url": "https://webhook.site/b97f64b4-a7a0-44c6-b9e5-2ed0112930d6",
          "post_prompt": {
            "top_p": 0.6,
            "temperature": 0.6,
            "text": "Summarize the conversation"
          },

```

### [pronounce](https://developer.signalwire.com/sdks/reference/swml/methods/ai/ai_pronounce)
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
    "temperature": 0.6,
    "top_p": 0.6
  }
}


```
