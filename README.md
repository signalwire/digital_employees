# SignalWire Digital Employees

[SignalWire.ai](https://signalwire.ai) - Part of the SignalWire Call Fabric platform, enables developers of all skill levels to quickly prototype and deploy digital employees that can perform interactive tasks to create integrations with remote systems and can harness all the functionality of the rest of the SignalWire platform features.

Below are Quick links to Serverless and Server examples.

## Serverless

Try out the following serverless examples in the dashboard of your SignalWire Space. Navigate to the **Relay/SWML** sidebar item and the **SWML Scripts** tab.

#### 🤖  [Sigmond](https://github.com/signalwire/digital_employees/tree/main/serverless/Sigmond)
  * Sigmond - SignalWire AI Agent Sigmond is a live demo robot with a friendly, C-3PO-inspired personality that assists users with SignalWire, FreeSWITCH, and Programmable Unified Communications by showcasing innovative features such as real-time API-driven workflows, global scalability, low latency, and interactive support through SWML scripting.

#### 🎅 [Interactive Santa](https://github.com/signalwire/digital_employees/tree/main/serverless/Santa)
  * Santa - This JSON config defines a Santa Claus-themed SignalWire holiday marketing campaign where an AI Santa, using child-friendly language, guides the user through selecting a single Christmas gift from a dynamically generated list via SWML functions, while enforcing rules for polite behavior and concluding with a festive farewell.

#### 👨‍⚕️  [Dr. Bob Confirm](https://github.com/signalwire/digital_employees/tree/main/serverless/Dr_Bob_Confirm)
  * Dr. Bob - A person calls a SignalWire number or endpoint, the AI digital employee answers, and when the user requests a representative, multiple endpoints are dialed in parallel, with the call transferring once one endpoint accepts by pressing 1.

#### 💐  [Flo's Flowers](https://github.com/signalwire/digital_employees/tree/main/serverless/Flos_Flowers)
  * Flo - Send an SMS e-card with an image url to a user's phone number. Flo will give four flower options to choose from to send. The user can include a message with the flower image.

#### ☔️  [Weather Bot](https://github.com/signalwire/digital_employees/tree/main/serverless/Weather_Bot)
  * Uses the [OpenStreetMap](https://openstreetmap.org) API to fetch longitude and latitude values based on the provided city and state. The bot then uses these coordinates and the [Weather.gov](https://api.weather.gov) API to retrieve the requested weather details.

#### ☎️  [Thermal Thrillers](https://github.com/signalwire/digital_employees/tree/main/serverless/Thermal_Thrillers)
  * An interactive digital employee capable of taking messages and performing related tasks after hours at an HVAC firm.

#### 🌡️  [ESP8266 Temperature & Humidity Sensor Bot](https://github.com/signalwire/digital_employees/tree/main/serverless/ESP8266_Temperature_and_Humidity_Sensor_Bot)
  * Ziggy - A digital employee that can interact with a ESP8266 and DHT11 temperature sensor to give the temperature and humidity values from the [ThingSpeak API](https://www.mathworks.com/help/thingspeak/channels-and-charts-api.html).

#### 🍹  [AI Bartender](https://github.com/signalwire/digital_employees/blob/main/serverless/Bartender)
  * Kevin - The AI Bartender is a digital employee designed to serve as your personal bartender. Kevin uses a vectorized PDF of drink recipes instead of imagining them.


## Server

#### 📽️ [Movie Bot](https://github.com/signalwire/digital_employees/tree/main/server/Python_Examples/moviebot)
  * Movie Expert AI Agent with SignalWire AI Gateway.

#### 🦷 [Dental Office](https://github.com/signalwire/digital_employees/tree/main/server/Python_Examples/dental_office)
  * Jen - A click-to-call example paired with an interactive web calendar featuring multi-factor authentication (MFA), PSTN connectivity, AI agent (digital employee) interaction, and the ability to schedule, move, and delete appointments that interact with SQLite and mock patient and dentist data.

#### 💐 [Flo's Flowers 2](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/FlosFlowers2)
  * Flo - Flo's Flowers 2.0 can send an SMS e-card with an image of any type of flower now. Just tell Flo what kind of flowers to send.

#### &#x1F935; [RoomieServe](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/Roomie_Serve)
  * Roomie Serve is a digital assistant designed for use in hotels and hospitals, aimed at enhancing the efficiency and accuracy of room service orders. Roomie Serve interfaces with a menu inventory database to facilitate the creation of room service orders.

#### &#x1F4C5; [Aical](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/aical)
  * Aical is a digital employee that integrates with [Google Calendar API](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid). Aical defines functions to check calendar availability (`freebusy`) and schedule events (`events`), leveraging Google Calendar's API to manage calendar entries based on user input, and utilizes OAuth2 for authentication with Google services. The application is structured around the PSGI specification, employing `Plack::Builder` to route HTTP requests to the appropriate handlers, enabling basic authentication, and managing user sessions and database connections for storing OAuth tokens and user information.


#### 🌐  [Zen](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/Zen)
  * Zen - A digital employee for a mock cable company who performs Tier 1 support for cable modems. Zen can authenticate a customer using their account number and CPNI (Customer Proprietary Network Information). Zen can also give speed test results, swap a modem, and give modem levels with mock data from a database connection.
   
#### 🍽️  [Bobby's Table](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/BobbysTable.ai)
  * Bobby - A digital employee who performs comprehensive reservation management tasks for a busy virtual restaurant. Bobby can check for available dates and create a reservation based on date, time and party size.  Bobby is also capable of moving, cancelling, and altering reservations. This example also uses the SignalWire MFA API to send a 6 digit code via SMS.
    
#### 🔐  [MFA](https://github.com/signalwire/digital_employees/tree/main/server/Perl_Examples/MFA)
  * This digital employee is able to send a 6 digit code via SMS, and verify the 6 digit code with SignalWire's MFA API.
    

## Tools

#### 🎧 [TAP](https://github.com/signalwire/digital_employees/tree/main/server/tools/tap)
  * Listen to Real-time Transport Protocol (RTP) audio streams. Supports multiple streams.

--------------
Explore the possibilities of Remote Communication, Workflow Integration, and Real-time Collaboration with SignalWire's Scalable Solutions, enhanced with Natural Language Processing (NLP) capabilities.
