# ESP8266 Temperature and Humidity Sensor Bot

ESP8266, thingspeak.com, DHT11 sensor data interacting with SignalWire's AI technology


# Other Variables

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
