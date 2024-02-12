# SignalWire Digital Employees

Quick links to Serverless and Server examples.

## Serverless

Try out the following serverless examples in the dashboard of your SignalWire Space. Navigate to the **Relay/SWML** sidebar item and the **SWML Scripts** tab.

* [Flo's_Flowers](https://github.com/signalwire/digital_employees/tree/main/serverless/Flos_Flowers)
  * Send an SMS e-card with an image url to a user's phone number. Flo will give four flower options to choose from to send. The user can include a message with the flower image.

* [Weather Bot](https://github.com/signalwire/digital_employees/tree/main/serverless/Weather_Bot)
  * Uses the [OpenStreetMap](https://openstreetmap.org) API to fetch longitude and latitude values based on the provided city and state. The bot then uses these coordinates and the [Weather.gov](https://api.weather.gov) API to retrieve the requested weather details.

* [Thermal Thrillers](https://github.com/signalwire/digital_employees/tree/main/serverless/Thermal_Thrillers)
  * An interactive digital employee capable of taking messages and performing related tasks after hours at an HVAC firm.


## Server

* [Zen](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/Zen)
  * Zen is a digital employee for a mock cable company who performs Tier 1 support for cable modems. Zen can authenticate a customer using their account number and CPNI (Customer Proprietary Network Information). Zen can also give speed test results, swap a modem, and give modem levels with mock data from a database connection.
   
* [Bobby's Table](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/BobbysTable.ai)
  * Bobby is a digital employee who performs comprehensive reservation management tasks for a busy virtual restaurant. Bobby can check for available dates and create a reservation based on date, time and party size.  Bobby is also capable of moving, cancelling, and altering reservations. This example also uses the SignalWire MFA API to send a 6 digit code via SMS.
    
* [MFA](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/MFA)
  * This digital employee is able to send a 6 digit code via SMS, and verify the 6 digit code with SignalWire's MFA API.
    
* [Arduino Temperature & Humidity Sensor Bot](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/Arduino_Temperature_%26_Humidity_Sensor_Bot)
  * Ziggy is a digital employee that can interact with a ESP32 and DHT11 temperature sensor to give the temperature and humidity values from the [ThingSpeak API](https://www.mathworks.com/help/thingspeak/channels-and-charts-api.html).
