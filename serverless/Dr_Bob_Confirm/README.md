# Dr. Bob Confirm

<img src="https://github.com/user-attachments/assets/066ab999-2fe1-42e8-89fd-a28f4234dcf8" alt="image" width="20%" />



# Dr. Bob Confirm: How SignalWire's Confirm Option Works

## Table of Contents
1. [Introduction](#introduction)
2. [Step-by-Step Workflow](#step-by-step-workflow)
3. [SWML Setup](#swml-setup)
4. [Conclusion](#conclusion)

## Introduction
Dr. Bob Confirm is an example that leverages SignalWire's confirm option to streamline call transfers. In this process, when a call is received, SignalWire’s AI digital employee handles the initial interaction before routing the call to a live representative. Let's take a look at the process and detailed setup instructions using SWML (SignalWire Markup Language).

## Step-by-Step Workflow
1. **Call Initiation:**  
   A person calls a SignalWire number, C2C, or SIP endpoint.

2. **AI Digital Employee Interaction:**  
   SignalWire's AI digital employee answers the call.

3. **User Request:**  
   The user requests to speak to a representative.

4. **Parallel Dialing:**  
   The Confirm feature has predefined endpoints that dial in parallel, meaning each endpoint rings simultaneously.

5. **Endpoint Answering:**  
   When an endpoint answers, a secondary SWML script is executed. This script prompts the endpoint to either press 1 to accept the call or decline.

6. **Call Transfer Completion:**  
   If the endpoint accepts by pressing 1, the call transfer is successfully completed.

## SWML Setup
To implement this process, follow these steps:

1. **Prepare SWML Files:**  
   Two files are provided in this example: `SWML1.json` and `SWML2.json`.  
   - Create two SWML bins in your SignalWire space.
   - Copy and paste the content from each respective file into its corresponding bin.

2. **Configure the Confirm Option:**  
   - Retrieve the SWML bin URL from the SWML2 example, for instance:  
     `hxxps://replace-this-url-with-your-part2-swml-bin-url.signalwire.com/relay-bins/qlqle239-27b8-4e8a-8e5e-c868ef8269cf`
   - Use this URL as the `confirm` option under `connect` in your configuration.

## Conclusion
The Dr. Bob Confirm example illustrates an efficient method to handle call transfers using SignalWire's AI digital employee and the confirm feature. By following the outlined process and setting up your SWML bins as described, you can streamline communications and ensure that calls are routed effectively. This approach not only enhances the caller experience but also optimizes the overall call management process.

