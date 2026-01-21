# Serverless Examples

SWML (SignalWire Markup Language) examples that run directly in your SignalWire Space without requiring a backend server.

## Examples

| Example | Description |
|---------|-------------|
| [sigmond](sigmond/) | AI assistant robot with C-3PO-inspired personality |
| [santa](santa/) | Holiday marketing campaign with gift selection |
| [dr_bob_confirm](dr_bob_confirm/) | Call transfer with confirmation |
| [flos_flowers](flos_flowers/) | SMS e-card flower delivery |
| [weather_bot](weather_bot/) | Weather info using OpenStreetMap and Weather.gov APIs |
| [openweather_assistant](openweather_assistant/) | Weather assistant using OpenWeather API |
| [thermal_thrillers](thermal_thrillers/) | HVAC after-hours message taking |
| [bartender](bartender/) | AI bartender with vectorized drink recipes |
| [esp8266_sensor_bot](esp8266_sensor_bot/) | IoT temperature/humidity sensor integration |
| [multilingual_support_agent](multilingual_support_agent/) | Multi-language support agent |

## Getting Started

Copy, Paste, Edit, Save. Copy the SWML example, paste into a new SWML bin, edit and save.

1. Navigate to your SignalWire Space dashboard
2. Go to **Relay/SWML** > **SWML Scripts** tab
3. Create a new SWML Script
4. Copy the contents from any example's `SWML.json` or `SWML.yaml`
5. Edit as needed and save

## Calling with PSTN

Using a PSTN phone number to dial to your Digital Employee.

### Assigning a SWML Bin to a phone number

* Edit an existing phone number
* In the `HANDLE USING` section, select `a SWML Script`
* In the `WHEN A CALL COMES IN` section select the SWML Bin to use.

![image](https://github.com/signalwire/digital_employees/assets/13131198/2feb0525-1e87-4ff7-928d-341b5f940190)

![image](https://github.com/signalwire/digital_employees/assets/13131198/f39b5e40-719d-47d4-aa10-ffcefd3b6b78)

## Calling With SIP

Using a SIP address to dial to your Digital Employee via a Domain App.

### Create a SWML Bin

* Create a SWML Bin from one of the examples.

![image](https://github.com/signalwire/digital_employees/assets/13131198/85a36e64-8ec0-426c-a412-c6d1a4b412dd)

### Create a Domain App

* Create the Domain App if one doesn't exist or if you want a new one.
* In the `HANDLE USING` section, select `a SWML Script`
* In the `WHEN A CALL COMES IN` section select the SWML Bin to use.

![image](https://github.com/signalwire/digital_employees/assets/13131198/1c8761fd-d265-469a-b155-a6646bd25589)

![image](https://github.com/signalwire/digital_employees/assets/13131198/9140e2c9-48ff-4338-a31f-55400f3489d4)

### Assign to a Domain App

* Assign the SWML Bin to an existing Domain App.
* In the `HANDLE USING` section, select `a SWML Script`
* In the `WHEN A CALL COMES IN` section select the SWML Bin to use.

![image](https://github.com/signalwire/digital_employees/assets/13131198/a27a32ac-ebf1-4803-91e2-699718aab08f)

![image](https://github.com/signalwire/digital_employees/assets/13131198/9140e2c9-48ff-4338-a31f-55400f3489d4)

### Make Call

Now you can make a call to your digital employee with a SIP address like `sip:yourapp@yourspace.dapp.signalwire.com`
