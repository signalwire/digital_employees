# Enhancing HVAC Customer Service with a Digital Employee

At SignalWire, we are pioneering the integration of advanced AI technology to revolutionize how people interact with customers. In this example, the digital employee, Rachael, will assist customers outside regular business hours and during peak times. Here's how Rachael can make your HVAC inquiries and service requests smoother and more efficient.

## AI Digital Employee

Rachael is designed to be more than just a digital assistant. She is the forefront of our customer service, equipped to handle calls with the efficiency and understanding you'd expect from a human operator. Rachael is operational after hours, ensuring that Thermal Thrillers HVAC supports you 24/7.

### **Capabilities**

- **Scheduling Appointments:** Whether it's after hours or within our business hours (7:30AM to 5PM M-F), Rachael can schedule appointments and arrange for urgent service if needed.
- **Collecting Essential Information:** From service addresses to specific HVAC unit details, Rachael collects all necessary information to ensure our technicians are well-prepared for the job ahead.
- **Address Verification:** Rachael ensures the accuracy of your service address, enhancing service reliability.

### **Operational Hours and Payment Methods**

- **Business Hours:** Monday to Friday, 7:30AM to 5PM.
- **After Hours:** Service available through Rachael.
- **Payment Options:** We accept cash, checks, and credit cards for your convenience.

## How The Bot Works

The digital employee Rachael's interaction with customers is streamlined into several steps, ensuring a thorough collection of information while providing a friendly and helpful service.

1. **Greeting and Assistance:** Based on the time of your call, Rachael will greet you with the appropriate message and offer assistance.
2. **Information Gathering:** Rachael will guide you through a series of steps to gather all necessary information regarding your HVAC needs.
3. **Appointment Scheduling:** Depending on the time of your call, Rachael will either schedule an appointment or arrange for after-hours service.
4. **Custom Summarize Conversation:** Define the key information you want to collect by the end of the call. This data can be utilized later for various purposes, such as importing into a database, forwarding in an SMS to a designated recipient (e.g., an on-call technician), or performing any other action you need with the collected information.

## Summarize Conversation

`summarize_conversation` is a special built custom function that you can define required array of defined fields the ai agent will summarize and populate to use for after the call is over.  

Example

```json

{
"AGE": 20,
"CUSTOMER": "true",
"OWNER": "true",
"RENTAL": "false",
"AFTERHOURS": "false",
"WARRANTY": "true",
"PHONE": "+15555551234",
"TENANT_PHONE": null,
"DATETIME": "2024-08-27 02:24 PM",
"SYSTEM": "residential",
"owner_name": "Jim Smith",
"owner_phone": "+18675309",
"tenant_name": null,
"tenant_phone": null,
"address": "123 Forbes Avenue",
"city": "Pittsburgh",
"state": "PA",
"zipcode": "15222",
"customer": "true",
"owner": "true",
"hvac_type": "residential",
"previous_repairs": "No",
"hvac_make": "Next",
"hvac_model": "TE 24,000",
"unit_age": 20,
"warranty": "true",
"additional_info": "Maintenance contract",
"summary": "You are experiencing issues with your air conditioner"
}
```

---------------------

### SignalWire

#### SignalWire’s AI Agent for Voice allows you to build and deploy your own digital employee. Powered by advanced natural language processing (NLP) capabilities, your digital employee will understand caller intent, retain context, and generally behave in a way that feels “human-like”.  In fact, you may find that it behaves exactly like your best employee, elevating the customer experience through efficient, intelligent, and personalized interactions.



