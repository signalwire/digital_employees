# Open Weather Map

[Open Weather Map API](https://api.openweathermap.org) offers both [free and paid](https://openweathermap.org/full-price#current) access to weather information.  In our example, we will be using the **City** and **ZIPCODE** API's to pull data from.

## How does it work?

The SignalWire digital employee in this example will make an api call to the openweathermap api and return data that can be used during the call with the user.  We will also give the option to send the details to the user via sms.

## Prompt

The prompt will give a set of instructions for the digital employee to use guiding the conversation and along with steps to follow.

```json

{
  "prompt": {
    "text": "You're a weather expert. You have three functions to help you get weather information for users.

Ask the user for the city or zipcode they want to know the weather for.
You have to use get_weather_city if the user gives a city name only.
Remove state name if city name and state name is given or get_weather_zipcode if the user gives a 5 digit zipcode.

# Step 1
Greet the user.

# Step 2
Get the detailed forecast for the user.

# Step 3
Tell the user the detailed forecast.

# Step 4
Offer to send the details in a message to the user.

# Step 5
Ask the user if there is anything else you can help them with.",
    "temperature": 0.6,
    "top_p": 0.6
  }
}


```
