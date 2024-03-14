# SignalWire AI Agent Calendar Demo Application

Facilitate the creation of Google Calendar meetings seamlessly over the phone by dialing into an AI-enabled phone number supplied by SignalWire. This phone number is tailored to execute a SWML script, streamlining the process of scheduling meetings directly from your call

## Table of Contents

- [Features](#features)
- [Usage](#usage)
- [Configuration](#Configuration)

## Features

- Enables users to schedule Google Calendar meetings via phone call.
- Utilizes AI-enabled phone number provided by SignalWire.
- Configured with SWML script for efficient meeting scheduling.


## Usage

1. Clone the repository to your local machine.
2. Go to ./server/Node_Examples/AI_Calendar_Demo/
3. Set up your environment variables by creating a .env file and adding the required configurations (refer to .env.example for reference).
4. Run the application using node app.js.
5. Access the application through your preferred web browser.

## Configuration

1. Open http://localhost:3000/login  and select your google accout and click on continue to update google OAuth tokens in database
2. copy Ngrok URL from console and open your Signalwire space and click on Phone number tab
3. Click on Phone number to configure SWML script URL
4. Click on edit settings and change * ACCEPT INCOMING CALLS AS drop down to Voice calls and * HANDLE CALLS USING a SWML Script
5. Place your Ngrok ULR along with path like https://abc.ngrok-free.app/main_webhook and click on Save button
6. Now make call to your signalwire number to create goole calende event


