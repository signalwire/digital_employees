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
* Schedule, move, delete appointments that interacts with SQLITE
* Mock patient and dentist data

---

## Table of Contents

1. [Create Custom AI Agent](#Create-Custom-AI-Agent)
2. [Creating a Click 2 Call Resource](#Creating-a-Click-To-Call-Resource)
3. [Populate Variables in .env](#Populate-Variables-in-env)
4. [Install Script Specifics](#Install-Script-Specifics)


---

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



## Creating a Click To Call Resource

From the SignalWire dashboard:

1. Click Tools at the bottom left menu, then Click To Call

<img src="https://github.com/user-attachments/assets/1662fc43-d20c-4479-b221-c26038f83daf" alt="image" style="width:10%;">


2. Click + Add

<img src="https://github.com/user-attachments/assets/26876fbf-e8ed-4c06-9177-9ad27d5c7b53" alt="image" style="width:10%;">

3. Choose and select the Resource

<img src="https://github.com/user-attachments/assets/5e1a9a6e-d7e9-445a-b413-06d79b3e83d2" alt="image" style="width:50%;">


4. Click the work Add

<img src="https://github.com/user-attachments/assets/02adb341-dc2d-448c-aa09-34b03a19e508" alt="image" style="width:50%;">

5. You now have a click to call widget

<img src="https://github.com/user-attachments/assets/0dfcaccb-e13c-4c7c-bd3f-c8b34444fed9" alt="image" style="width:50%;">


## Populate Variables in env

The setup script will output a .env file that your will populate with credentials and API Key's


```
HTTP_USERNAME=admin
HTTP_PASSWORD=password
SIGNALWIRE_PROJECT_ID=
SIGNALWIRE_TOKEN=
SIGNALWIRE_SPACE=
FROM_NUMBER=
C2C_ADDRESS=
C2C_API_KEY=
NGROK_DOMAIN=
NGROK_PATH=/usr/local/bin/ngrok
NGROK_AUTH_TOKEN=
```


* `HTTP_USERNAME` HTTP username that is used in the dashboard endpoint SWML URL.
* `HTTP_PASSWORD` HTTP password that is used in the dashboard endpoint SWML URL.
* `SIGNALWIRE_PROJECT_ID` Your SignalWire Project ID. This is found in the dashboard.
* `SIGNALWIRE_TOKEN` Your SignalWire Token (API Key). This is generated in the dashboard under API.
* `SignalWire Space` This is your subdomain name. For example: hxxps://subdomain.signalwire.com.
* `FROM_NUMBER` This is a phone number from your SignalWire dashboard and is project specific.
* `C2C_ADDRESS` This is the address that is created when you create a Click To Call resource widget.
  *  This is found under Tools > Click To Call > Then click on the widget.
  *  Use the Address. In this example you would use `dental-office-kihyn`

<img src="https://github.com/user-attachments/assets/ae05c14d-dd58-410c-a513-9ef141c9b6db" alt="image" style="width:50%;">

* `C2C_API_KEY` Use the Copy Token (Key)
* `NGROK_DOMAIN` Use if you have a custom NGROK domain
* `NGROK_PATH` Edit this if your ngrok path is different.
* `NGROK_AUTH_TOKEN` Use the token from the NGROK dashboard.



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
