SignalWire Dental Office
----------------

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
