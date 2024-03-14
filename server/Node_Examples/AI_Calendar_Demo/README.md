# SignalWire AI Agent Calendar Demo Application

Facilitate the creation of Google Calendar meetings seamlessly over the phone by dialing into an AI-enabled phone number supplied by SignalWire. This phone number is tailored to execute a SWML script, streamlining the process of scheduling meetings directly from your call

## Table of Contents

- [Features](#features)
- [Usage](#usage)
- [Configuration](#Configuration)

## Features

- Enables users to schedule Google Calendar meetings via phone call.
- Utilizes AI-enabled phone numbers provided by SignalWire.
- Configured with SWML script for efficient meeting scheduling.


## Usage

1. Clone the repository to your local machine.
2. Go to ./server/Node_Examples/AI_Calendar_Demo/
3. Set up your environment variables by creating a .env file and adding the required configurations (refer to the .env.example for reference).
4. Run the application using node app.js.
5. Access the application through your preferred web browser.

## Configuration

1. Open http://localhost:3000/login  select your Google account and click on continue to update Google OAuth tokens in the database
2. copy the Ngrok URL from the console open your Signalwire space and click on the Phone number tab
3. Click on the Phone number to configure the SWML script URL
4. Click on edit settings and change the `* ACCEPT INCOMING CALLS AS` drop down to Voice calls and `* HANDLE CALLS USING` a SWML Script
5. Place your Ngrok ULR along with a path like https://abc.ngrok-free.app/main_webhook in `* WHEN A CALL COMES IN:` in the textbox and click on the Save button
6. Now make the call to your signalwire number to create a Google Calendar event


