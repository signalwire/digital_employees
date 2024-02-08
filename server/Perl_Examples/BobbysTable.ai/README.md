# Bobbystable.ai
https://Bobbystable.ai AI Reservation bot powered by [Signalwire](https://signalwire.com/?utm_source=bobbystable.ai)

Live demo: Call `+1-754-432-6229`

Welcome to Bobbystable.ai. Bobbystable.ai is a functional demo of a restaurant reservation system using Signalwire's APIs.

In this repository, you will find the full prompt used, along with all the functions. The functions are written in Perl.

In addition to what is included in this repository, you will also need a web server (NGINX), a database (PostgreSQL), Signalwire's APIs, and a registered/apporoved campaign for SMS.


-------------------

The website is used to display the reservation details. This could be protected with a username and password, but it was left open to demonstrate the functionality.

- `Date:` Reservation date.
- `Time:` Reservation time.
- `Party Size:` Number of guests.
- `Guest Name:` Name of the guest.
- `Guest Number:` Phone number of the guest.

![image](https://github.com/Len-PGH/Bobbystable.ai/assets/13131198/5a03a103-83df-495b-bc98-8de136fa5cdc)


---------------------------

This is a backend interface gated by a login user name and password.

- `user:` The caller's interaction.
- `Assistant:` The AI bot's interaction.
- `function:` This shows that the function was executed either correctly or incorrectly.
- `system:` This is like the assistant but on a higher level.

![1705971341262](https://github.com/Len-PGH/Bobbystable.ai/assets/13131198/772e91b4-0338-41b3-aa33-29e5f295cc2d)


----------------------------

This is the text message sent that includes:

- Reservation name.
- Reservation date and time.
- Instructions on how to update the reservation online with a unique link.
- The option to STOP to help comply with sms regulation.

![1705971339655](https://github.com/Len-PGH/Bobbystable.ai/assets/13131198/1319f8e2-4cf2-4d8e-a1b1-e22ca9717649)


---------------------

### SignalWire

#### SignalWire’s AI Agent for Voice allows you to build and deploy your own digital employee. Powered by advanced natural language processing (NLP) capabilities, your digital employee will understand caller intent, retain context, and generally behave in a way that feels “human-like”.  In fact, you may find that it behaves exactly like your best employee, elevating the customer experience through efficient, intelligent, and personalized interactions.






