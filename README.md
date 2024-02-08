# digital_employee's

Quick links to Serverless and Server examples.

## Serverless

* [Flo's_Flowers](https://github.com/signalwire/digital_employees/tree/main/serverless/Flos_Flowers)
  * Send an SMS e-card with an image url to a user's phone number. Flo will give four flower options to choose from to send. The user can include a message with the flower image.
* [Weather Bot](https://github.com/signalwire/digital_employees/tree/main/serverless/Weather_Bot)
  * Uses openstreetmap.org api to get the log and lat that is then used for the city and state for the https://api.weather.gov api giving the weather details.
* [Thermal Thrillers](https://github.com/signalwire/digital_employees/tree/main/serverless/Thermal_Thrillers)
  * An interactive after hours HVAC message taking digital employee.


## Server

* [Zen](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/Zen)
  * Zen is a digital employee for a mock cable company that does Tier 1 cable modem support. Zen can authenticate a customer via account number and cpni. Zen can also give speed test results, swap a modem and give modem levels with mock data with a database connection.
* [Bobby's Table](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/BobbysTable.ai)
  * Bobby is a reservation taking digital employee that can check for available dates, move a reservation, cancel a reservation, create a reservation based on date, time and part size. This example also uses the SignalWire multi factor application MFA API to send a 6 digit code via sms. 
* [MFA](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/MFA)
  * This digital employee is able to send a 6 digit code via sms and verify the 6 digit code with SignalWire's MFA API
* [Arduino Temperature & Humidity Sensor Bot](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/Arduino_Temperature_%26_Humidity_Sensor_Bot)
  * Ziggy is a digital employee that can interact with a ESP32 and DHT11 temperature sensor to give the temperature and humidity values from the https://api.thingspeak.com API
