from flask import Flask, jsonify
from dotenv import load_dotenv
import logging
import os
from signalwire_swaig.core import SWAIG, SWAIGArgument

from reservation_system import (
    create_reservation_response,
    get_reservation_response,
    update_reservation_response,
    cancel_reservation_response,
    move_reservation_response,
    reservations
)
import random

logging.getLogger('werkzeug').setLevel(logging.WARNING)

if os.environ.get('DEBUG'):
    print("Debug mode is enabled")
    debug_pin = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"
    os.environ['WERKZEUG_DEBUG_PIN'] = debug_pin
    logging.getLogger('werkzeug').setLevel(logging.DEBUG)
    print(f"Debugger PIN: {debug_pin}")


load_dotenv()

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.static_folder = os.path.abspath('static')
swaig = SWAIG(
    app,
    auth=(os.getenv('HTTP_USERNAME'), os.getenv('HTTP_PASSWORD'))
)

@swaig.endpoint(
    description="Create a new reservation for a customer",
    name=SWAIGArgument(type="string", description="The name of the person making the reservation", required=True),
    party_size=SWAIGArgument(type="integer", description="Number of people in the party", required=True),
    date=SWAIGArgument(type="string", description="Date of reservation in YYYY-MM-DD format", required=True),
    time=SWAIGArgument(type="string", description="Time of reservation in HH:MM format (24-hour)", required=True),
    phone_number=SWAIGArgument(type="string", description="Contact phone number in E.164 format (e.g., +19185551234)", required=True)
)
def create_reservation(name, party_size, date, time, phone_number, meta_data_token=None, meta_data=None):
    return create_reservation_response({
        "name": name,
        "party_size": party_size,
        "date": date,
        "time": time,
        "phone_number": phone_number
    })

@swaig.endpoint(
    description="Retrieve an existing reservation",
    phone_number=SWAIGArgument(type="string", description="Phone number used for the reservation in E.164 format", required=True)
)
def get_reservation(phone_number, meta_data_token=None, meta_data=None):
    return get_reservation_response({"phone_number": phone_number})

@swaig.endpoint(
    description="Update an existing reservation",
    phone_number=SWAIGArgument(type="string", description="Phone number of the existing reservation", required=True),
    name=SWAIGArgument(type="string", description="Updated name (optional)", required=True),
    party_size=SWAIGArgument(type="integer", description="Updated party size (optional)", required=True),
    date=SWAIGArgument(type="string", description="Updated date in YYYY-MM-DD format (optional)", required=True),
    time=SWAIGArgument(type="string", description="Updated time in HH:MM format (optional)", required=True)
)
def update_reservation(phone_number, name=None, party_size=None, date=None, time=None, meta_data_token=None, meta_data=None):
    return update_reservation_response({
        "phone_number": phone_number,
        "name": name,
        "party_size": party_size,
        "date": date,
        "time": time
    })

@swaig.endpoint(
    description="Cancel an existing reservation",
    phone_number=SWAIGArgument(type="string", description="Phone number of the reservation to cancel", required=True)
)
def cancel_reservation(phone_number, meta_data_token=None, meta_data=None):
    return cancel_reservation_response({"phone_number": phone_number})

@swaig.endpoint(
    description="Move an existing reservation to a new date and time",
    phone_number=SWAIGArgument(type="string", description="Phone number of the existing reservation", required=True),
    new_date=SWAIGArgument(type="string", description="New date in YYYY-MM-DD format", required=True),
    new_time=SWAIGArgument(type="string", description="New time in HH:MM format", required=True)
)
def move_reservation(phone_number, new_date, new_time, meta_data_token=None, meta_data=None):
    return move_reservation_response({
        "phone_number": phone_number,
        "new_date": new_date,
        "new_time": new_time
    })

def scramble_phone_number(phone):
    if not phone or len(phone) < 6:
        return phone
    return phone[:-6] + ''.join(random.choices('0123456789', k=6))

def get_reservations_table_html():
    if not reservations:
        return "<p>No reservations yet.</p>"
    
    table_html = """
    <table border="1">
        <tr>
            <th>Name</th>
            <th>Phone</th>
            <th>Date</th>
            <th>Time</th>
            <th>Party Size</th>
        </tr>
    """
    
    for phone, details in reservations.items():
        scrambled = scramble_phone_number(phone)
        table_html += f"""
        <tr>
            <td>{details['name']}</td>
            <td>{scrambled}</td>
            <td>{details['date']}</td>
            <td>{details['time']}</td>
            <td>{details['party_size']}</td>
        </tr>
        """
    
    table_html += "</table>"
    return table_html

#app route for the reservation page
@app.route('/swaig', methods=['GET'])
@app.route('/', methods=['GET'])
def serve_reservation_html():
    try:
        with open('static/reservation.html', 'r') as file:
            html_content = file.read()
        
        reservations_table = get_reservations_table_html()
        
        # Replace placeholders with actual data
        html_content = html_content.replace("{{reservations_table}}", reservations_table)
        
        # Insert Google Tag Manager script if the tag is available
        GOOGLE_TAG = os.getenv("GOOGLE_TAG")
        if GOOGLE_TAG:
            gtm_script = f"""
            <script async src="https://www.googletagmanager.com/gtag/js?id={GOOGLE_TAG}"></script>
            <script>
              window.dataLayer = window.dataLayer || [];
              function gtag(){{dataLayer.push(arguments);}}
              gtag('js', new Date());
              gtag('config', '{GOOGLE_TAG}');
            </script>
            """
            html_content = html_content.replace("</head>", f"{gtm_script}</head>")
        
        return html_content
    except Exception as e:
        return jsonify({"error": "Failed to serve HTML"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.getenv("PORT", 5001), debug=os.getenv("DEBUG"))
