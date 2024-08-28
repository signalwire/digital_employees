# ESP8266 Temperature and Humidity Sensor Bot

ESP8266, thingspeak.com, DHT11 sensor data interacting with SignalWire's AI technology. Giving a nice experience with software and hardware (IOT).

![image](https://github.com/user-attachments/assets/c8b7671b-e238-48a2-8899-e1d01b2b7eec)


## Stuff you need
- Create or Log on to your [SignalWire Space](https://signalwire.com/signin)
- [Kit from Amazon](https://www.amazon.com/gp/product/B07GPBBY7F)
- [Arduio IDE](https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing)
- [Arduino IDE Sketch](https://github.com/signalwire/digital_employees/tree/main/serverless/ESP8266_Temperature_and_Humidity_Sensor_Bot/arduino_sketch)
- Frosty beverage (optional)

## How it works

In this example we have the [ESP8266 kit from Amazon](https://www.amazon.com/gp/product/B07GPBBY7F). The kit will provide the local weather from [Openweathermap](https://openweathermap.org/) that displays on the LCD. The part that will interact with the SignalWire serverless [SWML bin](https://github.com/signalwire/digital_employees/blob/main/serverless/ESP8266_Temperature_and_Humidity_Sensor_Bot/full_example_SWML.json) is the DHT11 temperature and humidity sensor. There is also a light sensor we can get data from. The ESP8266 will send the data from the DHT11 and light sensor to the [Thingspeak api.](api.thingspeak.com). This will create the api responses we need to use with our [SWML bin example](https://github.com/signalwire/digital_employees/blob/main/serverless/ESP8266_Temperature_and_Humidity_Sensor_Bot/full_example_SWML.json) The digital employee can now query the api and tell the caller what the temperature and humidity is. The digital employee will also give you the option to send an sms message with the same temperature and humidity info.


## Json variables to use

- **"Temperature":** `${feeds[0].field1}`: This would map to "80" from the first entry in the feeds array (field1).
- **"Humidity":** `${feeds[0].field2}`: This would map to "51" from the first entry in the feeds array (field2).
- **"Light":** `${feeds[0].field3}`: This would map to "0" from the first entry in the feeds array (field3).
- **"Atmosphere":** `${feeds[0].field4}`: This would map to "96355" from the first entry in the feeds array (field4).

#### Webhook reply:
```json
{
    "webhook_reply": {
        "channel": {
            "id": 1464062,
            "name": "ClueCon2021",
            "description": "ESP8266 and DHT11",
            "latitude": "0.0",
            "longitude": "0.0",
            "field1": "Temperature",
            "field2": "Humidity",
            "field3": "Light",
            "field4": "Atmosphere",
            "created_at": "2021-08-04T03:17:29Z",
            "updated_at": "2021-08-04T03:46:20Z",
            "last_entry_id": 619290
        },
        "feeds": [
            {
                "created_at": "2024-08-26T23:37:05Z",
                "entry_id": 619289,
                "field1": "79",
                "field2": "53",
                "field3": "0",
                "field4": "96368"
            }
        ]
    }
}
```

## Functions used

#### **Function:** `get_temperature_humidity`

```json
              {
                "function": "get_temperature_humidity",
                "data_map": {
                  "webhooks": [
                    {
                      "url": "https://api.thingspeak.com/channels/1464062/feeds.json?results=2",
                      "method": "GET",
                      "output": {
                        "response": "The current weather is ${feeds[0].field1} and humidity is ${feeds[0].field2}",
                        "action": []
                      }
                    }
                  ]
                },
                "purpose": "get the temperature and humidity.",
                "argument": {
                  "properties": {
                    "zip": {
                      "type": "string",
                      "description": "Temperature and humidity."
                    }
                  },
                  "type": "object"
                }
              }
            ]
          },
```

#### **Function:** `send_message`

```json
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
                                      "body": " ${args.message} Reply STOP to stop.",
                                      "from_number": "+15555555555"
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
```
