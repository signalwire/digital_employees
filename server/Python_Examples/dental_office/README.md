SignalWire Dental Office
----------------

<img src="https://github.com/user-attachments/assets/b71a75e4-5aa4-422b-bcd7-4502036fe429" alt="image" style="width:75%;">


SignalWire Dental Office is a demo of how a Dental Office could use SignalWire's AI capabilites.

The example highlights:

* Click to Call
* Web Calendar
* MFA Multifactor Authentication
* PSTN connectivity
* AI Agent (Digital Employee) interaction
* Typical schedule, move, delete appointments that interacts with SQLITE
* Mock patient and dentist data

## Create Custom AI Agent

1. Go to `Resources` left side tab.

<img src="https://github.com/user-attachments/assets/b5dd5804-207a-42b0-a22c-f4575bd3a225" alt="image" style="width:15%;">


2. Click the button `Add New`

<img src="https://github.com/user-attachments/assets/07eea87d-b2fc-4a92-8c7a-dfb97c462eaa" alt="image" style="width:15%;">


3. Choose `AI Agent`

<img src="https://github.com/user-attachments/assets/a0dc60a6-a871-402c-8ec7-07da15e8113e" alt="image" style="width:50%;">


4. Choose `Custom AI Agent`

<img src="https://github.com/user-attachments/assets/a5ee97ff-3d06-4c10-86a7-ba6c6422d99b" alt="image" style="width:50%;">


5. Click the `functions` tab

<img src="https://github.com/user-attachments/assets/041c2e7c-3187-4c6d-adf4-4e87c1f1f3af" alt="image" style="width:50%;">



6. Enter the URL in the search box. In this example we are using NGROK. https://admin:password@test.ngrok-free.app/swaig

<img src="https://github.com/user-attachments/assets/e83fb060-4444-46b3-a5a2-3cf4e643a701" alt="image" style="width:50%;">


7. Click the checkbox to enable the functions. Then click the `create` button.


<img src="https://github.com/user-attachments/assets/f4073afa-4b54-4cda-a807-71ddc697acb3" alt="image" style="width:50%;">


8. Then click the `save` button.

<img src="https://github.com/user-attachments/assets/528c5188-19db-4460-b8de-ee4d11bda4fe" alt="image" style="width:50%;">



## Install Script Specifics

### Section 1: Script Header and Directory Structure
- **File**: None (just creates directories)
- **Content**: `mkdir -p dental_app/templates dental_app/static/css dental_app/static/js`

### Section 2: Create schema.sql
- **File**: `dental_app/schema.sql`
- **Content**: Defines tables (`patients`, `dentists`, `appointments`, `visits`).

### Section 3: Create index.html
- **File**: `dental_app/templates/index.html`
- **Content**: Calendar UI with links to add/manage appointments.

### Section 4: Create add_appointment.html
- **File**: `dental_app/templates/add_appointment.html`
- **Content**: Form for adding appointments via web UI.
- This is for the web interface, not SWAIG endpoints.

### Section 5: Create move_appointment.html
- **File**: `dental_app/templates/move_appointment.html`
- **Content**: Form for moving appointments via web UI.
- Web UI only.

### Section 6: Create admin_dentists.html
- **File**: `dental_app/templates/admin_dentists.html`
- **Content**: Manage dentists UI.
- Dentist management UI, not SWAIG-related.

### Section 7: Create admin_add_dentist.html
- **File**: `dental_app/templates/admin_add_dentist.html`
- **Content**: Add dentist form.
- Web UI only.

### Section 8: Create admin_edit_dentist.html
- **File**: `dental_app/templates/admin_edit_dentist.html`
- **Content**: Edit dentist form.
- Web UI only.

### Section 9: Create admin_patients.html
- **File**: `dental_app/templates/admin_patients.html`
- **Content**: Manage patients UI.
- Web UI only.

### Section 10: Create admin_add_patient.html
- **File**: `dental_app/templates/admin_add_patient.html`
- **Content**: Add patient form.
- Web UI only.

### Section 11: Create admin_edit_patient.html
- **File**: `dental_app/templates/admin_edit_patient.html`
- **Content**: Edit patient form.
- Web UI only.

### Section 12: Create admin_add_appointment.html
- **File**: `dental_app/templates/admin_add_appointment.html`
- **Content**: Add appointment form for admin UI.
- Web UI only.

### Section 13: Create admin_patient_visits.html
- **File**: `dental_app/templates/admin_patient_visits.html`
- **Content**: View patient visits and appointments UI.
- Web UI only.

### Section 14: Create admin_add_patient_visit.html
- **File**: `dental_app/templates/admin_add_patient_visit.html`
- **Content**: Add patient visit form.
- Web UI only.

### Section 15: Create debug_db.html
- **File**: `dental_app/templates/debug_db.html`
- **Content**: Debug database view UI.
- Web UI only.

### Section 16: Create generate_token.html
- **File**: `dental_app/templates/generate_token.html`
- **Content**: Token generation UI.
- Web UI only.

### Section 17: Create create_fake_data.py
- **File**: `dental_app/create_fake_data.py`
- **Content**: Generates fake data with E.164 phone numbers.

### Section 18: Create init_db.py
- **File**: `dental_app/init_db.py`
- **Content**: Initializes the database with `schema.sql`.

### Section 19: Create app.py
- **File**: `dental_app/app.py`
- **Content**: Main Flask app with SWAIG endpoints.

### Section 20: Create requirements.txt
- **File**: `dental_app/requirements.txt`
- **Content**: Lists Python dependencies (`flask`, `signalwire-swaig`, etc.).

### Section 21: Setup Commands
- **File**: None (just commands)
- **Content**: Sets up venv, installs requirements, runs `init_db.py` and `create_fake_data.py`.
