# Dr. Bob Confirm

Dr. Bob Confirm is an example that uses the SignalWire confirm option. In this process, a person calls a SignalWire number, C2C, or SIP endpoint, and SignalWire's AI digital employee answers the call. The user then requests to speak to a representative, and Confirm has predefined endpoints that dial in parallel, causing each endpoint to ring at the same time. When an endpoint answers, a second SWML script is executed, prompting the endpoint to either press 1 to accept the call or decline. If the endpoint accepts, the call transfer is complete.

- A person calls a SignalWire number, C2C, or SIP endpoint.
- SignalWire's AI digital employee answers the call.
- The user requests to speak to a representative.
- Confirm has predefined endpoints to dial in parallel.
- Each endpoint rings at the same time.
- When an endpoint answers, the second SWML script is executed and the endpoint either presses 1 to accept the call or declines.
- If the endpoint accepts, the call transfer is complete.

## SWML Setup


1. In this example, two files are provided: `SWML1.json` and `SWML2.json`. To implement this, create two SWML bins in your SignalWire space, then copy and paste the content from each respective file into its corresponding bin.
2. Take the SWML bin url `hxxps://replace-this-url-with-your-part2-swml-bin-url.signalwire.com/relay-bins/qlqle239-27b8-4e8a-8e5e-c868ef8269cf` from SWML2 example and put it as the `confirm` option under `connect`

