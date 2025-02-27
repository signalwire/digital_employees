#!/bin/bash

# Create project directory structure
mkdir -p dental_app/templates dental_app/static/css dental_app/static/js

# Create schema.sql with non-auto-increment patient IDs
cat > dental_app/schema.sql << 'EOF'
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth TEXT,
    gender TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    insurance TEXT
);

CREATE TABLE IF NOT EXISTS dentists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    specialty TEXT,
    phone TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    dentist_id INTEGER,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (dentist_id) REFERENCES dentists(id)
);

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    visit_datetime TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
EOF

# Create index.html with Dark Theme and Appointment Modal
cat > dental_app/templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Dental Appointment Calendar</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; background-color: #212529; color: #f8f9fa; }
        #calendar { max-width: 1100px; margin: 0 auto; }
        .fc { color: #f8f9fa; }
        .fc-button { background-color: #495057; border-color: #495057; }
        .fc-button:hover { background-color: #6c757d; border-color: #6c757d; }
        .modal-content { background-color: #343a40; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = `https://${SIGNALWIRE_SPACE}.signalwire.com/api/fabric/embeds/tokens`;
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">Dental Appointment Calendar</h1>
        <div class="mb-3">
            <a href="/add" class="btn btn-primary">Add Appointment</a>
            <a href="/admin/patients" class="btn btn-secondary">Manage Patients</a>
            <a href="/admin/dentists" class="btn btn-secondary">Manage Dentists</a>
            <div id="click2call" class="d-inline-block"></div>
            <div id="call"></div>
        </div>
        <div id="calendar"></div>
    </div>

    <!-- Modal for Appointment Details -->
    <div class="modal fade" id="appointmentModal" tabindex="-1" aria-labelledby="appointmentModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="appointmentModalLabel">Appointment Details</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p><strong>ID:</strong> <span id="modalId"></span></p>
                    <p><strong>Title:</strong> <span id="modalTitle"></span></p>
                    <p><strong>Patient:</strong> <span id="modalPatient"></span></p>
                    <p><strong>Dentist:</strong> <span id="modalDentist"></span></p>
                    <p><strong>Start Time:</strong> <span id="modalStart"></span></p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            var calendarEl = document.getElementById('calendar');
            var calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: 'timeGridWeek',
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                },
                events: '/api/appointments',
                editable: true,
                eventDrop: function(info) {
                    $.ajax({
                        url: '/api/appointments/' + info.event.id,
                        method: 'PUT',
                        data: JSON.stringify({
                            start_time: info.event.start.toISOString()
                        }),
                        contentType: 'application/json',
                        success: function() {
                            alert('Appointment moved successfully');
                        }
                    });
                },
                eventClick: function(info) {
                    $('#modalId').text(info.event.id);
                    $('#modalTitle').text(info.event.title);
                    $('#modalPatient').text(info.event.extendedProps.patient_name);
                    $('#modalDentist').text(info.event.extendedProps.dentist_name);
                    $('#modalStart').text(info.event.start.toLocaleString());
                    $('#appointmentModal').modal('show');
                },
                slotDuration: '01:00:00', // 1-hour slots
                slotMinTime: '08:00:00', // Example: start at 8 AM
                slotMaxTime: '17:00:00' // Example: end at 5 PM
            });
            calendar.render();
        });
    </script>
</body>
</html>
EOF

# Create add_appointment.html with Dark Theme
cat > dental_app/templates/add_appointment.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Add Appointment</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .select2-container--default .select2-selection--single { background-color: #343a40; border-color: #495057; color: #f8f9fa; }
        .select2-container--default .select2-selection--single .select2-selection__rendered { color: #f8f9fa; }
        .select2-dropdown { background-color: #343a40; border-color: #495057; color: #f8f9fa; }
        .select2-results__option { color: #f8f9fa; }
        .select2-results__option--highlighted { background-color: #495057; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Add New Appointment</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Patient</label>
                <select name="patient_id" class="form-select patient-select" required>
                    <option value="">Select a patient</option>
                    {% for patient in patients %}
                        <option value="{{ patient.id }}">{{ patient.first_name }} {{ patient.last_name }} - {{ patient.phone }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Dentist</label>
                <select name="dentist_id" class="form-select" required>
                    {% for dentist in dentists %}
                        <option value="{{ dentist.id }}">{{ dentist.first_name }} {{ dentist.last_name }} - {{ dentist.specialty }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Title</label>
                <input type="text" name="title" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Date</label>
                <input type="date" name="appointment_date" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Start Time</label>
                <input type="time" name="start_time" class="form-control" step="3600" min="08:00" max="16:00" required>
            </div>
            <button type="submit" class="btn btn-primary">Add Appointment</button>
            <a href="/" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
    <script>
        $(document).ready(function() {
            $('.patient-select').select2({
                placeholder: "Search for a patient",
                allowClear: true
            });
        });
    </script>
</body>
</html>
EOF

# Create move_appointment.html with Dark Theme
cat > dental_app/templates/move_appointment.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Move Appointment</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Move Appointment</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Title</label>
                <input type="text" name="title" class="form-control" value="{{ appointment.title }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Dentist</label>
                <select name="dentist_id" class="form-select" required>
                    {% for dentist in dentists %}
                        <option value="{{ dentist.id }}" {% if dentist.id == appointment.dentist_id %}selected{% endif %}>
                            {{ dentist.first_name }} {{ dentist.last_name }} - {{ dentist.specialty }}
                        </option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Date</label>
                <input type="date" name="appointment_date" class="form-control" value="{{ appointment.start_time[:10] }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Start Time</label>
                <input type="time" name="start_time" class="form-control" value="{{ appointment.start_time[11:16] }}" step="3600" min="08:00" max="16:00" required>
            </div>
            <button type="submit" class="btn btn-primary">Update Appointment</button>
            <a href="/" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create admin_dentists.html with Dark Theme
cat > dental_app/templates/admin_dentists.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Manage Dentists</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote-bs5.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .table { color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Manage Dentists</h1>
        <div class="mb-3">
            <a href="/admin/dentists/add" class="btn btn-primary">Add New Dentist</a>
            <div id="click2call" class="d-inline-block"></div>
            <div id="call"></div>
        </div>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Specialty</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for dentist in dentists %}
                <tr>
                    <td>{{ dentist.id }}</td>
                    <td>{{ dentist.first_name }}</td>
                    <td>{{ dentist.last_name }}</td>
                    <td>{{ dentist.specialty }}</td>
                    <td>{{ dentist.phone }}</td>
                    <td>{{ dentist.email }}</td>
                    <td>
                        <a href="/admin/dentists/edit/{{ dentist.id }}" class="btn btn-sm btn-primary">Edit</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <a href="/" class="btn btn-secondary">Back to Calendar</a>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote-bs5.min.js"></script>
</body>
</html>
EOF

# Create admin_add_dentist.html with Dark Theme
cat > dental_app/templates/admin_add_dentist.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Add Dentist</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote-bs5.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .summernote { background-color: #343a40; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Add New Dentist</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">First Name</label>
                <input type="text" name="first_name" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Last Name</label>
                <input type="text" name="last_name" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Specialty</label>
                <input type="text" name="specialty" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">Phone</label>
                <input type="tel" name="phone" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control">
            </div>
            <button type="submit" class="btn btn-primary">Add Dentist</button>
            <a href="/admin/dentists" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote-bs5.min.js"></script>
</body>
</html>
EOF

# Create admin_edit_dentist.html with Dark Theme
cat > dental_app/templates/admin_edit_dentist.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Edit Dentist</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote-bs5.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .summernote { background-color: #343a40; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Edit Dentist</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">First Name</label>
                <input type="text" name="first_name" class="form-control" value="{{ dentist.first_name }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Last Name</label>
                <input type="text" name="last_name" class="form-control" value="{{ dentist.last_name }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Specialty</label>
                <input type="text" name="specialty" class="form-control" value="{{ dentist.specialty }}">
            </div>
            <div class="mb-3">
                <label class="form-label">Phone</label>
                <input type="tel" name="phone" class="form-control" value="{{ dentist.phone }}">
            </div>
            <div class="mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" value="{{ dentist.email }}">
            </div>
            <button type="submit" class="btn btn-primary">Update Dentist</button>
            <a href="/admin/dentists" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote-bs5.min.js"></script>
</body>
</html>
EOF

# Create admin_patients.html with Dark Theme
cat > dental_app/templates/admin_patients.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Manage Patients</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .table { color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Manage Patients</h1>
        <div class="mb-3">
            <a href="/admin/patients/add" class="btn btn-primary">Add New Patient</a>
            <a href="/admin/appointments/add" class="btn btn-primary">Add Appointment</a>
            <div id="click2call" class="d-inline-block"></div>
            <div id="call"></div>
        </div>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for patient in patients %}
                <tr>
                    <td>{{ patient.id }}</td>
                    <td>{{ patient.first_name }}</td>
                    <td>{{ patient.last_name }}</td>
                    <td>{{ patient.phone }}</td>
                    <td>{{ patient.email }}</td>
                    <td>
                        <a href="/admin/patients/edit/{{ patient.id }}" class="btn btn-sm btn-primary">Edit</a>
                        <a href="/admin/patients/{{ patient.id }}/visits" class="btn btn-sm btn-primary">View Visits</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <a href="/" class="btn btn-secondary">Back to Calendar</a>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create admin_add_patient.html with Dark Theme
cat > dental_app/templates/admin_add_patient.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Add Patient</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Add New Patient</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">First Name</label>
                <input type="text" name="first_name" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Last Name</label>
                <input type="text" name="last_name" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Date of Birth</label>
                <input type="date" name="date_of_birth" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">Gender</label>
                <select name="gender" class="form-select">
                    <option value="">Select Gender</option>
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Address</label>
                <textarea name="address" class="form-control"></textarea>
            </div>
            <div class="mb-3">
                <label class="form-label">Phone</label>
                <input type="tel" name="phone" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">Insurance</label>
                <input type="text" name="insurance" class="form-control">
            </div>
            <button type="submit" class="btn btn-primary">Add Patient</button>
            <a href="/admin/patients" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create admin_edit_patient.html with Dark Theme
cat > dental_app/templates/admin_edit_patient.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Edit Patient</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Edit Patient</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">First Name</label>
                <input type="text" name="first_name" class="form-control" value="{{ patient.first_name }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Last Name</label>
                <input type="text" name="last_name" class="form-control" value="{{ patient.last_name }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Date of Birth</label>
                <input type="date" name="date_of_birth" class="form-control" value="{{ patient.date_of_birth }}">
            </div>
            <div class="mb-3">
                <label class="form-label">Gender</label>
                <select name="gender" class="form-select">
                    <option value="">Select Gender</option>
                    <option value="M" {% if patient.gender == 'M' %}selected{% endif %}>Male</option>
                    <option value="F" {% if patient.gender == 'F' %}selected{% endif %}>Female</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Address</label>
                <textarea name="address" class="form-control">{{ patient.address }}</textarea>
            </div>
            <div class="mb-3">
                <label class="form-label">Phone</label>
                <input type="tel" name="phone" class="form-control" value="{{ patient.phone }}">
            </div>
            <div class="mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" value="{{ patient.email }}">
            </div>
            <div class="mb-3">
                <label class="form-label">Insurance</label>
                <input type="text" name="insurance" class="form-control" value="{{ patient.insurance }}">
            </div>
            <button type="submit" class="btn btn-primary">Update Patient</button>
            <a href="/admin/patients" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create admin_add_appointment.html with Dark Theme
cat > dental_app/templates/admin_add_appointment.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Add Appointment (Admin)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .select2-container--default .select2-selection--single { background-color: #343a40; border-color: #495057; color: #f8f9fa; }
        .select2-container--default .select2-selection--single .select2-selection__rendered { color: #f8f9fa; }
        .select2-dropdown { background-color: #343a40; border-color: #495057; color: #f8f9fa; }
        .select2-results__option { color: #f8f9fa; }
        .select2-results__option--highlighted { background-color: #495057; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Add New Appointment (Admin)</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Patient</label>
                <select name="patient_id" class="form-select patient-select" required>
                    <option value="">Select a patient</option>
                    {% for patient in patients %}
                        <option value="{{ patient.id }}">{{ patient.first_name }} {{ patient.last_name }} - {{ patient.phone }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Dentist</label>
                <select name="dentist_id" class="form-select" required>
                    {% for dentist in dentists %}
                        <option value="{{ dentist.id }}">{{ dentist.first_name }} {{ dentist.last_name }} - {{ dentist.specialty }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Title</label>
                <input type="text" name="title" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Date</label>
                <input type="date" name="appointment_date" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Start Time</label>
                <input type="time" name="start_time" class="form-control" step="3600" min="08:00" max="16:00" required>
            </div>
            <button type="submit" class="btn btn-primary">Add Appointment</button>
            <a href="/admin/patients" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
    <script>
        $(document).ready(function() {
            $('.patient-select').select2({
                placeholder: "Search for a patient",
                allowClear: true
            });
        });
    </script>
</body>
</html>
EOF

# Create admin_patient_visits.html with Dark Theme
cat > dental_app/templates/admin_patient_visits.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Patient Visits</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .table { color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Visits and Appointments for {{ patient.first_name }} {{ patient.last_name }}</h1>
        <div class="mb-3">
            <a href="/admin/patients/{{ patient.id }}/visits/add" class="btn btn-primary">Add New Visit</a>
            <a href="/admin/appointments/add" class="btn btn-primary">Add New Appointment</a>
            <div id="click2call" class="d-inline-block"></div>
            <div id="call"></div>
        </div>

        <h2>Visits</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Date/Time</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
                {% for visit in visits %}
                <tr>
                    <td>{{ visit.id }}</td>
                    <td>{{ visit.visit_datetime }}</td>
                    <td>{{ visit.notes }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>Appointments</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Dentist</th>
                    <th>Start Time</th>
                </tr>
            </thead>
            <tbody>
                {% for appointment in appointments %}
                <tr>
                    <td>{{ appointment.id }}</td>
                    <td>{{ appointment.title }}</td>
                    <td>{{ appointment.dentist_first_name }} {{ appointment.dentist_last_name }}</td>
                    <td>{{ appointment.start_time }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <a href="/admin/patients" class="btn btn-secondary">Back to Patients</a>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create admin_add_patient_visit.html with Dark Theme
cat > dental_app/templates/admin_add_patient_visit.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Add Patient Visit</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Add Visit for {{ patient.first_name }} {{ patient.last_name }}</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Visit Date</label>
                <input type="date" name="visit_date" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Visit Time</label>
                <input type="time" name="visit_time" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Notes</label>
                <textarea name="notes" class="form-control"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Add Visit</button>
            <a href="/admin/patients/{{ patient.id }}/visits" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create debug_db.html with Dark Theme
cat > dental_app/templates/debug_db.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Database Debug</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
        .table { color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Database Debug</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>

        <h2>Patients</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Phone</th>
                    <th>Email</th>
                </tr>
            </thead>
            <tbody>
                {% for patient in patients %}
                <tr>
                    <td>{{ patient.id }}</td>
                    <td>{{ patient.first_name }}</td>
                    <td>{{ patient.last_name }}</td>
                    <td>{{ patient.phone }}</td>
                    <td>{{ patient.email }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>Dentists</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Specialty</th>
                    <th>Phone</th>
                    <th>Email</th>
                </tr>
            </thead>
            <tbody>
                {% for dentist in dentists %}
                <tr>
                    <td>{{ dentist.id }}</td>
                    <td>{{ dentist.first_name }}</td>
                    <td>{{ dentist.last_name }}</td>
                    <td>{{ dentist.specialty }}</td>
                    <td>{{ dentist.phone }}</td>
                    <td>{{ dentist.email }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>Appointments</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Patient ID</th>
                    <th>Dentist ID</th>
                    <th>Title</th>
                    <th>Start Time</th>
                </tr>
            </thead>
            <tbody>
                {% for appointment in appointments %}
                <tr>
                    <td>{{ appointment.id }}</td>
                    <td>{{ appointment.patient_id }}</td>
                    <td>{{ appointment.dentist_id }}</td>
                    <td>{{ appointment.title }}</td>
                    <td>{{ appointment.start_time }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>Visits</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Patient ID</th>
                    <th>Date/Time</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
                {% for visit in visits %}
                <tr>
                    <td>{{ visit.id }}</td>
                    <td>{{ visit.patient_id }}</td>
                    <td>{{ visit.visit_datetime }}</td>
                    <td>{{ visit.notes }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <a href="/" class="btn btn-secondary">Back to Calendar</a>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create generate_token.html with Dark Theme
cat > dental_app/templates/generate_token.html << 'EOF'
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Generate Token</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #212529; color: #f8f9fa; }
    </style>
    <script>
        (a => {
            var i, s, k, n = "Signalwire C2C API", o = "sw", c = "spawn", x = "Loaded", h = "authenticate", y = "{{ c2c_api_key }}",
                r = document, k = window;
            k = k[o] || (k[o] = {});
            var w = k.c2c || (k.c2c = {}), l = (p) => new Promise(async (u, v) => {
                await (s = r.createElement("script"));
                s.src = `${k.codeRepository}/${p}.js`;
                w[`${p}${x}`] = () => {
                    delete w[`${p}${a}`];
                    !w[h] ? w[c](h, y).then(u) : u();
                };
                s.onerror = () => i = v(Error(n + " could not load."));
                s.nonce = r.querySelector("script[nonce]")?.nonce || "";
                r.head.append(s);
            });
            k.relayHost = "https://puc.signalwire.com";
            k.codeRepository = "https://app.signalwire.com";
            k.authEndpoint = "https://dev.swire.io/api/fabric/embeds/tokens";
            w[c] ? k[h](y) : w[c] = (f, ...n) => new Promise((g,) => {w[f] ? g(w[f](...n)) : l(f).then(() => g(w[f](...n)))})
        })({ apiKey: "{{ c2c_api_key }}", v: "0.0.1" });

        sw.c2c.spawn('C2CButton', {
            destination: '/private/${C2C_ADDRESS}',
            buttonParentSelector: '#click2call',
            innerHTML: null,
            callParentSelector: '#call',
            beforeCallStartFn: () => { console.log('attempting to start new call...'); return true },
            afterCallStartFn: () => { console.log('call started.') },
            beforeCallLeaveFn: () => { console.log('attempting to hangup call...'); return true },
            afterCallLeaveFn: () => { console.log('call ended.') },
            onCallError: (error) => { console.error(error) }
        });
    </script>
</head>
<body>
    <div class="container mt-4">
        <h1>Generate API Token</h1>
        <div id="click2call" class="mb-3"></div>
        <div id="call"></div>
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Current Token</label>
                <input type="text" class="form-control" value="{{ token }}" readonly>
            </div>
            <button type="submit" class="btn btn-primary">Generate New Token</button>
            <a href="/" class="btn btn-secondary">Back to Calendar</a>
        </form>
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
EOF

# Create fake data script with E.164 formatted 10-digit phone numbers and random 5-digit patient IDs
cat > dental_app/create_fake_data.py << 'EOF'
import sqlite3
import random
import faker

fake = faker.Faker()

def generate_e164_phone():
    # Generate a 10-digit US phone number and prefix with +1
    area_code = random.randint(200, 999)  # Avoid invalid US area codes like 0xx or 1xx
    exchange = random.randint(200, 999)  # Avoid invalid exchanges
    subscriber = random.randint(0, 9999)  # Last 4 digits
    return f"+1{area_code}{exchange}{subscriber:04d}"

def generate_random_5_digit_id(existing_ids):
    # Generate a unique random 5-digit ID (10000-99999)
    while True:
        new_id = random.randint(10000, 99999)
        if new_id not in existing_ids:
            return new_id

def create_fake_data():
    conn = sqlite3.connect('dental_app/calendar.db')
    c = conn.cursor()

    # Track used IDs to ensure uniqueness
    used_patient_ids = set()

    # Fake patients with random 5-digit IDs
    for _ in range(20):
        patient_id = generate_random_5_digit_id(used_patient_ids)
        used_patient_ids.add(patient_id)
        c.execute('''INSERT INTO patients (id, first_name, last_name, date_of_birth, gender, address, phone, email, insurance)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (patient_id, fake.first_name(), fake.last_name(), fake.date_of_birth(minimum_age=18, maximum_age=80),
                   random.choice(['M', 'F']), fake.address(), generate_e164_phone(),
                   fake.email(), fake.company()))

    # Fake dentists (still using auto-increment IDs)
    specialties = ['General', 'Orthodontics', 'Periodontics', 'Endodontics']
    for _ in range(5):
        c.execute('''INSERT INTO dentists (first_name, last_name, specialty, phone, email)
                     VALUES (?, ?, ?, ?, ?)''',
                  (fake.first_name(), fake.last_name(), random.choice(specialties),
                   generate_e164_phone(), fake.email()))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_fake_data()
EOF

import sqlite3
import random
import faker

fake = faker.Faker()

def create_fake_data():
    conn = sqlite3.connect('dental_app/calendar.db')
    c = conn.cursor()

    # Fake patients
    for _ in range(20):
        c.execute('''INSERT INTO patients (first_name, last_name, date_of_birth, gender, address, phone, email, insurance)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (fake.first_name(), fake.last_name(), fake.date_of_birth(minimum_age=18, maximum_age=80),
                   random.choice(['M', 'F']), fake.address(), fake.phone_number(),
                   fake.email(), fake.company()))

    # Fake dentists
    specialties = ['General', 'Orthodontics', 'Periodontics', 'Endodontics']
    for _ in range(5):
        c.execute('''INSERT INTO dentists (first_name, last_name, specialty, phone, email)
                     VALUES (?, ?, ?, ?, ?)''',
                  (fake.first_name(), fake.last_name(), random.choice(specialties),
                   fake.phone_number(), fake.email()))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_fake_data()
EOF

# Create database initialization script
cat > dental_app/init_db.py << 'EOF'
import sqlite3

def init_db():
    conn = sqlite3.connect('dental_app/calendar.db')
    with open('dental_app/schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
EOF

# Create app.py with MFA-verified patient data used in appointment actions
cat > dental_app/app.py << 'EOF'
import os
import logging
import subprocess
import requests
import re
import json
import sqlite3
import time
from datetime import datetime
from functools import wraps
import psutil
import secrets
from dotenv import load_dotenv, set_key
from flask import Flask, request, jsonify, g, render_template, redirect, url_for, session
from signalwire.rest import Client as SignalWireClient
from signalwire_swaig.core import SWAIG, SWAIGArgument

# =======================
# Configuration and Setup
# =======================

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('signalwire').setLevel(logging.DEBUG)

load_dotenv()

app = Flask(__name__)
app.config['DATABASE'] = os.path.abspath(os.path.join(app.root_path, 'calendar.db'))
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
print(f"Using database: {app.config['DATABASE']}")

SIGNALWIRE_TOKEN = os.getenv("SIGNALWIRE_TOKEN")
C2C_API_KEY = os.getenv("C2C_API_KEY")
DENTIST_API = os.getenv("DENTIST_API")
PROJECT_ID = os.getenv("SIGNALWIRE_PROJECT_ID")
SPACE = os.getenv("SIGNALWIRE_SPACE")
FROM_NUMBER = os.getenv("FROM_NUMBER")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")
NGROK_PATH = os.getenv("NGROK_PATH")
HTTP_USERNAME = os.getenv("HTTP_USERNAME")
HTTP_PASSWORD = os.getenv("HTTP_PASSWORD")
DEBUG_WEBOOK_URL = os.getenv("DEBUG_WEBOOK_URL")

required_vars = [
    "SIGNALWIRE_PROJECT_ID", "SIGNALWIRE_TOKEN", "SIGNALWIRE_SPACE", "FROM_NUMBER",
    "NGROK_AUTH_TOKEN", "NGROK_DOMAIN", "NGROK_PATH", "HTTP_USERNAME", "HTTP_PASSWORD"
]

def validate_phone(phone):
    return bool(re.match(r'^\+[1-9]\d{1,14}$', phone))

for var in required_vars:
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {var}")
    if var == "FROM_NUMBER" and not validate_phone(value):
        raise ValueError(f"Invalid phone number format for {var}: {value}")

NGROK_URL = f"https://{NGROK_DOMAIN}"

logging.debug(f"SIGNALWIRE_SPACE: {SPACE}")
logging.debug(f"SIGNALWIRE_FROM_NUMBER: {FROM_NUMBER}")
logging.debug(f"NGROK_DOMAIN: {NGROK_DOMAIN}")
logging.debug(f"DEBUG_WEBOOK_URL: {DEBUG_WEBOOK_URL}")

# SWAIG Setup
swaig = SWAIG(app, auth=(HTTP_USERNAME, HTTP_PASSWORD))

# =======================
# Database Helper Functions
# =======================

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    with app.app_context():
        db = get_db()
        try:
            with app.open_resource('schema.sql', mode='r') as f:
                db.executescript(f.read())
            db.commit()
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            required_tables = {'patients', 'dentists', 'appointments', 'visits'}
            if not required_tables.issubset(tables):
                raise ValueError(f"Missing required tables: {required_tables - tables}")
            logging.info("Database initialized with required tables")
        except (FileNotFoundError, sqlite3.Error, ValueError) as e:
            logging.error(f"Database initialization failed: {e}")
            raise

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# =======================
# Helper Functions
# =======================

def is_dentist_overbooked(dentist_id, start_time, exclude_id=None):
    try:
        appointment_date = datetime.strptime(start_time, '%Y-%m-%d %H:%M').strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid time format. Use 'YYYY-MM-DD HH:MM'")

    db = get_db()
    query = """
        SELECT COUNT(*) as count 
        FROM appointments 
        WHERE dentist_id = ? 
        AND DATE(start_time) = ?
    """
    params = (dentist_id, appointment_date)
    if exclude_id:
        query += " AND id != ?"
        params += (exclude_id,)
    
    result = db.execute(query, params).fetchone()
    return result['count'] >= 4

def is_time_slot_taken(dentist_id, start_time, exclude_id=None):
    db = get_db()
    query = """
        SELECT id 
        FROM appointments 
        WHERE dentist_id = ? 
        AND start_time = ?
    """
    params = (dentist_id, start_time)
    if exclude_id:
        query += " AND id != ?"
        params += (exclude_id,)
    
    return db.execute(query, params).fetchone() is not None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        auth_header = request.headers.get('Authorization')
        meta_data_token = kwargs.get('meta_data_token')
        if auth_header and auth_header.lower().startswith('bearer '):
            token = auth_header.split(' ', 1)[1]
        effective_token = meta_data_token or token
        if not effective_token or effective_token != DENTIST_API:
            logging.warning(f"Unauthorized access attempt - Expected: {DENTIST_API}, Got: {effective_token}, Meta: {meta_data_token}, Header: {auth_header}, Query: {token}")
            return jsonify({"success": False, "message": "Token is missing or invalid!"}), 401
        return f(*args, **kwargs)
    return decorated

# =======================
# SignalWire MFA
# =======================

class SignalWireMFA:
    def __init__(self, project_id: str, token: str, space: str, from_number: str):
        try:
            self.client = SignalWireClient(project_id, token, signalwire_space_url=f"{space}.signalwire.com")
            self.project_id = project_id
            self.token = token
            self.space = space
            self.from_number = from_number
            self.base_url = f"https://{space}.signalwire.com/api/relay/rest"
            logging.debug(f"Initialized SignalWireMFA with from_number: {self.from_number}")
        except Exception as e:
            logging.error(f"Failed to initialize SignalWire Client: {e}")
            raise

    def send_mfa(self, to_number: str) -> dict:
        try:
            url = f"{self.base_url}/mfa/sms"
            payload = {
                "to": to_number,
                "from": self.from_number,
                "message": "Here is your code: ",
                "token_length": 6,
                "max_attempts": 3,
                "allow_alphas": False,
                "valid_for": 3600
            }
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Sending MFA from {self.from_number} to {to_number}")
            response = requests.post(url, json=payload, auth=(self.project_id, self.token), headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error sending MFA: {e}")
            raise

    def verify_mfa(self, mfa_id: str, token: str) -> dict:
        try:
            verify_url = f"{self.base_url}/mfa/{mfa_id}/verify"
            payload = {"token": token}
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Verifying MFA with ID {mfa_id} using token {token}")
            response = requests.post(verify_url, json=payload, auth=(self.project_id, self.token), headers=headers)
            response.raise_for_status()
            return response.json()  # Expected format: {"success": true/false, ...}
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                return {"success": False, "message": "Unauthorized: Invalid credentials or MFA ID"}
            elif status_code == 400:
                return {"success": False, "message": "Bad Request: Invalid MFA code or parameters"}
            else:
                return {"success": False, "message": f"HTTP error {status_code}: {str(e)}"}
        except Exception as e:
            logging.error(f"Unexpected error verifying MFA: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

mfa_util = SignalWireMFA(PROJECT_ID, SIGNALWIRE_TOKEN, SPACE, FROM_NUMBER)

def is_valid_uuid(uuid_to_test, version=4):
    regex = {
        4: r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
    }
    pattern = regex.get(version)
    return bool(pattern and re.match(pattern, uuid_to_test))

# Global variable for MFA ID
LAST_MFA_ID = None

# Store verified patient data globally (simplified session-like storage)
VERIFIED_PATIENT_DATA = {}

# =======================
# SWAIG Endpoints
# =======================

@swaig.endpoint(
    "Send an MFA code to a specified phone number or patient's registered number",
    to_number=SWAIGArgument("string", "Phone number in E.164 format (optional if patient_id provided)", required=False),
    patient_id=SWAIGArgument("integer", "Patient ID to lookup phone number (optional)", required=False)
)
def send_mfa_code(to_number: str = None, patient_id: int = None, meta_data: dict = None, **kwargs):
    global LAST_MFA_ID
    db = get_db()
    
    # Determine the phone number to use
    if patient_id:
        patient = db.execute("SELECT phone FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if patient and patient['phone']:
            to_number = patient['phone']
            logging.debug(f"Using patient's phone number from record: {to_number}")
        elif not to_number:
            return {"success": False, "message": "Patient ID provided but no phone number found, and no fallback number given"}, 400

    if not to_number:
        # Fallback to caller_id from meta_data if available
        caller_id = meta_data.get('caller_id') if meta_data else None
        if caller_id and validate_phone(caller_id):
            to_number = caller_id
            logging.debug(f"Fallback to caller ID from meta_data: {to_number}")
        else:
            return {"success": False, "message": "No valid phone number provided or found"}, 400

    if not validate_phone(to_number):
        return {"success": False, "message": "Invalid phone number format. Use E.164 (e.g., +1234567890)"}, 400

    logging.debug(f"Attempting to send MFA code to {to_number}")
    try:
        response = mfa_util.send_mfa(to_number)
        mfa_id = response.get("id")
        if not mfa_id:
            return {"success": False, "message": "MFA ID not found in response"}, 400
        LAST_MFA_ID = mfa_id
        logging.debug(f"Full send_mfa response: {response}")
        return {"success": True, "message": "6 digit number sent successfully", "data": {"mfa_id": mfa_id}}, 200
    except Exception as e:
        logging.error(f"Error sending MFA code: {e}")
        return {"success": False, "message": f"Failed to send MFA code: {str(e)}"}, 500

@swaig.endpoint(
    "Verify an MFA code",
    token=SWAIGArgument("string", "The 6-digit code from SMS", required=True)
)
def verify_mfa_code(token: str, meta_data: dict = None, **kwargs):
    global LAST_MFA_ID, VERIFIED_PATIENT_DATA
    logging.debug(f"Received token: {token}")
    if not LAST_MFA_ID or not is_valid_uuid(LAST_MFA_ID):
        logging.error("No valid MFA session")
        return json.dumps({"success": False, "message": "No valid MFA session"}), {"status": 401}
    
    try:
        verification_response = mfa_util.verify_mfa(LAST_MFA_ID, token)
        logging.debug(f"Verification response: {verification_response}")
        
        if "mfa_id" not in verification_response:
            verification_response["mfa_id"] = LAST_MFA_ID
        
        if verification_response.get("success"):
            # After successful MFA, use meta_data from search_patient if available
            if meta_data and 'search_patient_result' in meta_data:
                patient_data = meta_data['search_patient_result']
                VERIFIED_PATIENT_DATA[LAST_MFA_ID] = patient_data
                logging.debug(f"Stored verified patient data: {patient_data}")
            return json.dumps({"success": True, "message": "MFA verified successfully", "data": {"mfa_id": LAST_MFA_ID}})
        else:
            error_message = verification_response.get("message", "Invalid MFA code. Please try again.")
            raise ValueError(error_message)
    except Exception as e:
        logging.error(f"Verification failed: {e}")
        return json.dumps({"success": False, "message": str(e), "data": {"mfa_id": LAST_MFA_ID if LAST_MFA_ID else None}}), {"status": 401}

@swaig.endpoint(
    "Search Patient",
    query=SWAIGArgument("string", "Search query for patient first or last name or ID", required=True)
)
def swaig_search_patient(query: str, meta_data: dict = None, **kwargs):
    db = get_db()
    try:
        patient_id = int(query)
        cursor = db.execute(
            "SELECT id, first_name, last_name, phone FROM patients WHERE id = ?",
            (patient_id,)
        )
        result = cursor.fetchone()
        if result:
            results = [dict(result)]
            response = json.dumps({"success": True, "message": "Patient found by ID", "data": {"results": results}})
            logging.debug(f"Search by ID '{query}' response: {response}")
            # Include patient data in meta_data for subsequent calls
            return response, {"search_patient_result": results[0]}
    except ValueError:
        pass

    cursor = db.execute(
        "SELECT id, first_name, last_name, phone FROM patients WHERE UPPER(first_name || ' ' || last_name) LIKE UPPER(?) LIMIT 10",
        ('%' + query + '%',)
    )
    results = [dict(row) for row in cursor.fetchall()]
    response = json.dumps({"success": True, "message": "Patient search completed", "data": {"results": results}})
    logging.debug(f"Search by name '{query}' response: {response}")
    # Include first result in meta_data if available
    return response, {"search_patient_result": results[0] if results else None}

@swaig.endpoint(
    "Get Appointments for a Patient",
    patient_id=SWAIGArgument("integer", "Patient ID to retrieve appointments for", required=True)
)
def swaig_get_patient_appointments(patient_id: int, meta_data: dict = None, **kwargs):
    db = get_db()
    patient = db.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        response = json.dumps({"success": False, "message": "Patient not found"})
        logging.debug(f"Get appointments for patient {patient_id} response: {response}")
        return response, {}
    
    cursor = db.execute("""
        SELECT a.id, a.patient_id, a.dentist_id, a.title, a.start_time,
               p.first_name, p.last_name, p.phone AS patient_phone, p.email AS patient_email,
               d.first_name AS dentist_first_name, d.last_name AS dentist_last_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dentists d ON a.dentist_id = d.id
        WHERE a.patient_id = ?
        ORDER BY a.start_time
    """, (patient_id,))
    appointments = [dict(row) for row in cursor.fetchall()]
    response = json.dumps({"success": True, "message": f"Appointments retrieved for patient {patient_id}", "data": {"appointments": appointments}})
    logging.debug(f"Get appointments for patient {patient_id} response: {response}")
    return response, {}

@swaig.endpoint(
    "Add New Appointment",
    patient_id=SWAIGArgument("integer", "Patient ID (optional if in meta_data)", required=False),
    dentist_id=SWAIGArgument("integer", "Dentist ID", required=True),
    title=SWAIGArgument("string", "Title/Procedure", required=True),
    start_time=SWAIGArgument("string", "Start time (YYYY-MM-DDTHH:MM)", required=True)
)
def swaig_add_appointment(patient_id: int = None, dentist_id: int = None, title: str = None, start_time: str = None, meta_data: dict = None, **kwargs):
    global VERIFIED_PATIENT_DATA, LAST_MFA_ID
    try:
        start_time_db = datetime.strptime(start_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return json.dumps({"success": False, "message": "Invalid time format. Use YYYY-MM-DDTHH:MM"}), {}

    db = get_db()
    
    # Use patient_id from meta_data if not provided and MFA was verified
    if not patient_id and meta_data and LAST_MFA_ID in VERIFIED_PATIENT_DATA:
        patient_data = VERIFIED_PATIENT_DATA.get(LAST_MFA_ID)
        if patient_data and 'id' in patient_data:
            patient_id = patient_data['id']
            logging.debug(f"Using patient_id {patient_id} from verified MFA meta_data")

    if not patient_id:
        return json.dumps({"success": False, "message": "Patient ID required and not found in meta_data"}), {}
    
    patient = db.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        return json.dumps({"success": False, "message": "Patient not found"}), {}
    dentist = db.execute("SELECT id FROM dentists WHERE id = ?", (dentist_id,)).fetchone()
    if not dentist:
        return json.dumps({"success": False, "message": "Dentist not found"}), {}
    if is_dentist_overbooked(dentist_id, start_time_db):
        return json.dumps({"success": False, "message": "Dentist has reached the maximum of 4 appointments for this day"}), {}
    if is_time_slot_taken(dentist_id, start_time_db):
        return json.dumps({"success": False, "message": "Time slot already taken for this dentist"}), {}
    
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO appointments (patient_id, dentist_id, title, start_time) VALUES (?, ?, ?, ?)",
        (patient_id, dentist_id, title, start_time_db)
    )
    db.commit()
    appointment_id = cursor.lastrowid
    return json.dumps({"success": True, "message": "Appointment added", "data": {"appointment_id": appointment_id}}), {}

@swaig.endpoint(
    "Update Appointment",
    appointment_id=SWAIGArgument("integer", "Appointment ID", required=True),
    patient_id=SWAIGArgument("integer", "Patient ID (optional if in meta_data)", required=False),
    dentist_id=SWAIGArgument("integer", "Dentist ID", required=False),
    title=SWAIGArgument("string", "Title/Procedure", required=False),
    start_time=SWAIGArgument("string", "Start time (YYYY-MM-DDTHH:MM)", required=False)
)
def swaig_update_appointment(appointment_id: int = None, patient_id: int = None, dentist_id: int = None, title: str = None, start_time: str = None, meta_data: dict = None, **kwargs):
    global VERIFIED_PATIENT_DATA, LAST_MFA_ID
    db = get_db()
    appointment = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    if not appointment:
        return json.dumps({"success": False, "message": "Appointment not found"}), {}
    
    # Use patient_id from meta_data if not provided and MFA was verified
    if not patient_id and meta_data and LAST_MFA_ID in VERIFIED_PATIENT_DATA:
        patient_data = VERIFIED_PATIENT_DATA.get(LAST_MFA_ID)
        if patient_data and 'id' in patient_data:
            patient_id = patient_data['id']
            logging.debug(f"Using patient_id {patient_id} from verified MFA meta_data")

    new_patient_id = patient_id if patient_id is not None else appointment['patient_id']
    new_dentist_id = dentist_id if dentist_id is not None else appointment['dentist_id']
    new_start = datetime.strptime(start_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M") if start_time else appointment['start_time']
    new_title = title if title is not None else appointment['title']
    
    if patient_id and not db.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone():
        return json.dumps({"success": False, "message": "Patient not found"}), {}
    if dentist_id and not db.execute("SELECT id FROM dentists WHERE id = ?", (dentist_id,)).fetchone():
        return json.dumps({"success": False, "message": "Dentist not found"}), {}
    if start_time:
        if is_dentist_overbooked(new_dentist_id, new_start, exclude_id=appointment_id):
            return json.dumps({"success": False, "message": "Dentist has reached the maximum of 4 appointments for this day"}), {}
        if is_time_slot_taken(new_dentist_id, new_start, exclude_id=appointment_id):
            return json.dumps({"success": False, "message": "Time slot already taken for this dentist"}), {}
    
    db.execute("UPDATE appointments SET patient_id = ?, dentist_id = ?, title = ?, start_time = ? WHERE id = ?",
               (new_patient_id, new_dentist_id, new_title, new_start, appointment_id))
    db.commit()
    return json.dumps({"success": True, "message": "Appointment updated"}), {}

@swaig.endpoint(
    "Delete Appointment",
    appointment_id=SWAIGArgument("integer", "Appointment ID", required=True),
    patient_id=SWAIGArgument("integer", "Patient ID (optional if in meta_data)", required=False)
)
def swaig_delete_appointment(appointment_id: int = None, patient_id: int = None, meta_data: dict = None, **kwargs):
    global VERIFIED_PATIENT_DATA, LAST_MFA_ID
    db = get_db()
    
    # Use patient_id from meta_data if not provided and MFA was verified
    if not patient_id and meta_data and LAST_MFA_ID in VERIFIED_PATIENT_DATA:
        patient_data = VERIFIED_PATIENT_DATA.get(LAST_MFA_ID)
        if patient_data and 'id' in patient_data:
            patient_id = patient_data['id']
            logging.debug(f"Using patient_id {patient_id} from verified MFA meta_data")

    appointment = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    if not appointment:
        return json.dumps({"success": False, "message": "Appointment not found"}), {}
    
    # Verify the patient_id matches the appointment’s patient_id if provided
    if patient_id and appointment['patient_id'] != patient_id:
        return json.dumps({"success": False, "message": "Unauthorized: Patient ID does not match appointment"}), {}
    
    db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    db.commit()
    return json.dumps({"success": True, "message": "Appointment deleted"}), {}

# =======================
# Web Interface Routes
# =======================

@app.route('/admin/generate_token', methods=['GET', 'POST'])
@token_required
def generate_token():
    if request.method == 'POST':
        new_token = secrets.token_hex(16)
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        set_key(env_path, "DENTIST_API", new_token)
        global DENTIST_API
        DENTIST_API = new_token
        logging.info(f"Generated new DENTIST_API token: {new_token}")
        return render_template('generate_token.html', token=new_token, c2c_api_key=C2C_API_KEY)
    return render_template('generate_token.html', token=DENTIST_API, c2c_api_key=C2C_API_KEY)

@app.route('/')
def index():
    return render_template('index.html', signalwire_token=SIGNALWIRE_TOKEN, c2c_api_key=C2C_API_KEY)

@app.route('/add', methods=['GET', 'POST'])
def add_appointment():
    db = get_db()
    dentists = db.execute("SELECT * FROM dentists").fetchall()
    patients = db.execute("SELECT * FROM patients").fetchall()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        dentist_id = request.form.get('dentist_id')
        title = request.form.get('title')
        appointment_date = request.form.get('appointment_date')
        start_time_val = request.form.get('start_time')
        if not all([patient_id, dentist_id, title, appointment_date, start_time_val]):
            return "All fields are required", 400
        try:
            start_datetime = datetime.strptime(f"{appointment_date} {start_time_val}", "%Y-%m-%d %H:%M")
            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return "Invalid date or time format", 400
        
        patient = db.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient:
            return "Error: Patient not found", 400
        dentist = db.execute("SELECT id FROM dentists WHERE id = ?", (dentist_id,)).fetchone()
        if not dentist:
            return "Error: Dentist not found", 400
        if is_dentist_overbooked(dentist_id, start_datetime_str):
            return "Error: Dentist has reached the maximum of 4 appointments for this day", 409
        if is_time_slot_taken(dentist_id, start_datetime_str):
            return "Error: Time slot already taken for this dentist", 409
        
        db.execute(
            "INSERT INTO appointments (patient_id, dentist_id, title, start_time) VALUES (?, ?, ?, ?)",
            (patient_id, dentist_id, title, start_datetime_str)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('add_appointment.html', dentists=dentists, patients=patients, c2c_api_key=C2C_API_KEY)

@app.route('/move/<int:appointment_id>', methods=['GET', 'POST'])
def move_appointment(appointment_id):
    db = get_db()
    cursor = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()
    if not appointment:
        return "Appointment not found", 400
    dentists = db.execute("SELECT * FROM dentists").fetchall()
    if request.method == 'POST':
        title = request.form.get('title', appointment['title'])
        dentist_id = request.form.get('dentist_id')
        appointment_date = request.form.get('appointment_date')
        start_time_val = request.form.get('start_time')
        if not all([dentist_id, appointment_date, start_time_val]):
            return "All fields are required", 400
        try:
            start_datetime = datetime.strptime(f"{appointment_date} {start_time_val}", "%Y-%m-%d %H:%M")
            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return "Invalid date or time format", 400
        
        dentist = db.execute("SELECT id FROM dentists WHERE id = ?", (dentist_id,)).fetchone()
        if not dentist:
            return "Error: Dentist not found", 400
        if is_dentist_overbooked(dentist_id, start_datetime_str, exclude_id=appointment_id):
            return "Error: Dentist has reached the maximum of 4 appointments for this day", 409
        if is_time_slot_taken(dentist_id, start_datetime_str, exclude_id=appointment_id):
            return "Error: Time slot already taken for this dentist", 409
        
        db.execute(
            "UPDATE appointments SET title = ?, dentist_id = ?, start_time = ? WHERE id = ?",
            (title, dentist_id, start_datetime_str, appointment_id)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('move_appointment.html', appointment=appointment, dentists=dentists, c2c_api_key=C2C_API_KEY)

@app.route('/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    db = get_db()
    cursor = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    if not cursor.fetchone():
        return "Appointment not found", 400
    db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    db.commit()
    return redirect(url_for('index'))

@app.route('/admin/patients', methods=['GET'])
def admin_patients():
    db = get_db()
    cursor = db.execute("SELECT * FROM patients")
    patients = cursor.fetchall()
    return render_template('admin_patients.html', patients=patients, c2c_api_key=C2C_API_KEY)

@app.route('/admin/patients/add', methods=['GET', 'POST'])
def admin_add_patient():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        if not all([first_name, last_name]):
            return "First and last name are required", 400
        date_of_birth = request.form.get('date_of_birth', '')
        gender = request.form.get('gender', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        insurance = request.form.get('insurance', '')
        db = get_db()
        db.execute(
            "INSERT INTO patients (first_name, last_name, date_of_birth, gender, address, phone, email, insurance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (first_name, last_name, date_of_birth, gender, address, phone, email, insurance)
        )
        db.commit()
        return redirect(url_for('admin_patients'))
    return render_template('admin_add_patient.html', c2c_api_key=C2C_API_KEY)

@app.route('/admin/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
def admin_edit_patient(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        return "Patient not found", 400
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        if not all([first_name, last_name]):
            return "First and last name are required", 400
        date_of_birth = request.form.get('date_of_birth', '')
        gender = request.form.get('gender', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        insurance = request.form.get('insurance', '')
        db.execute('''UPDATE patients SET first_name = ?, last_name = ?, date_of_birth = ?, gender = ?, address = ?, phone = ?, email = ?, insurance = ?
                     WHERE id = ?''',
                  (first_name, last_name, date_of_birth, gender, address, phone, email, insurance, patient_id))
        db.commit()
        return redirect(url_for('admin_patients'))
    return render_template('admin_edit_patient.html', patient=patient, c2c_api_key=C2C_API_KEY)

@app.route('/admin/appointments/add', methods=['GET', 'POST'])
def admin_add_appointment():
    db = get_db()
    dentists = db.execute("SELECT * FROM dentists").fetchall()
    patients = db.execute("SELECT * FROM patients").fetchall()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        dentist_id = request.form.get('dentist_id')
        title = request.form.get('title')
        appointment_date = request.form.get('appointment_date')
        start_time_val = request.form.get('start_time')
        if not all([patient_id, dentist_id, title, appointment_date, start_time_val]):
            return "All fields are required", 400
        try:
            start_datetime = datetime.strptime(f"{appointment_date} {start_time_val}", "%Y-%m-%d %H:%M")
            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return "Invalid date or time format", 400
        
        patient = db.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient:
            return "Error: Patient not found", 400
        dentist = db.execute("SELECT id FROM dentists WHERE id = ?", (dentist_id,)).fetchone()
        if not dentist:
            return "Error: Dentist not found", 400
        if is_dentist_overbooked(dentist_id, start_datetime_str):
            return "Error: Dentist has reached the maximum of 4 appointments for this day", 409
        if is_time_slot_taken(dentist_id, start_datetime_str):
            return "Error: Time slot already taken for this dentist", 409
        
        db.execute(
            "INSERT INTO appointments (patient_id, dentist_id, title, start_time) VALUES (?, ?, ?, ?)",
            (patient_id, dentist_id, title, start_datetime_str)
        )
        db.commit()
        return redirect(url_for('admin_patients'))
    return render_template('admin_add_appointment.html', dentists=dentists, patients=patients, c2c_api_key=C2C_API_KEY)

@app.route('/admin/patients/<int:patient_id>/visits', methods=['GET'])
def admin_patient_visits(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        return "Patient not found", 400
    visits = db.execute("SELECT * FROM visits WHERE patient_id = ? ORDER BY visit_datetime DESC", (patient_id,)).fetchall()
    appointments = db.execute("""
        SELECT a.id, a.title, a.start_time, d.first_name AS dentist_first_name, d.last_name AS dentist_last_name
        FROM appointments a
        JOIN dentists d ON a.dentist_id = d.id
        WHERE a.patient_id = ? ORDER BY a.start_time DESC
    """, (patient_id,)).fetchall()
    return render_template('admin_patient_visits.html', patient=patient, visits=visits, appointments=appointments, c2c_api_key=C2C_API_KEY)

@app.route('/admin/patients/<int:patient_id>/visits/add', methods=['GET', 'POST'])
def admin_add_patient_visit(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        return "Patient not found", 400
    if request.method == 'POST':
        visit_date = request.form.get('visit_date')
        visit_time = request.form.get('visit_time')
        if not all([visit_date, visit_time]):
            return "Visit date and time are required", 400
        try:
            visit_datetime = datetime.strptime(f"{visit_date} {visit_time}", "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return "Invalid date or time format", 400
        notes = request.form.get('notes', '')
        db.execute("INSERT INTO visits (patient_id, visit_datetime, notes) VALUES (?, ?, ?)",
                   (patient_id, visit_datetime, notes))
        db.commit()
        return redirect(url_for('admin_patient_visits', patient_id=patient_id))
    return render_template('admin_add_patient_visit.html', patient=patient, c2c_api_key=C2C_API_KEY)

@app.route('/debug/db')
def debug_db():
    db = get_db()
    patients = db.execute("SELECT * FROM patients").fetchall()
    dentists = db.execute("SELECT * FROM dentists").fetchall()
    appointments = db.execute("SELECT * FROM appointments").fetchall()
    visits = db.execute("SELECT * FROM visits").fetchall()
    return render_template('debug_db.html', patients=patients, dentists=dentists, appointments=appointments, visits=visits, c2c_api_key=C2C_API_KEY)

@app.route('/api/appointments')
def get_appointments():
    db = get_db()
    start = request.args.get('start')
    end = request.args.get('end')

    query = '''
        SELECT a.id, a.title, a.start_time as start,
               p.first_name || ' ' || p.last_name as patient_name,
               d.first_name || ' ' || d.last_name as dentist_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN dentists d ON a.dentist_id = d.id
    '''
    params = []

    if start and end:
        try:
            start_db = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M")
            end_db = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M")
            query += " WHERE a.start_time >= ? AND a.start_time <= ?"
            params = [start_db, end_db]
        except ValueError:
            return jsonify({"success": False, "message": "Invalid start or end date format. Use ISO 8601 (e.g., 2025-01-26T00:00:00-05:00)"}), 400

    appointments = db.execute(query, params).fetchall()
    return jsonify([dict(apt) for apt in appointments])

@app.route('/api/patients')
@token_required
def get_patients():
    db = get_db()
    patients = db.execute("SELECT id, first_name, last_name, phone FROM patients").fetchall()
    return jsonify([dict(patient) for patient in patients])

@app.route('/admin/dentists', methods=['GET'])
def admin_dentists():
    db = get_db()
    dentists = db.execute("SELECT * FROM dentists").fetchall()
    return render_template('admin_dentists.html', dentists=dentists, c2c_api_key=C2C_API_KEY)

@app.route('/admin/dentists/add', methods=['GET', 'POST'])
def admin_add_dentist():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        specialty = request.form.get('specialty')
        phone = request.form.get('phone')
        email = request.form.get('email')
        db = get_db()
        db.execute('''INSERT INTO dentists (first_name, last_name, specialty, phone, email)
                     VALUES (?, ?, ?, ?, ?)''',
                  (first_name, last_name, specialty, phone, email))
        db.commit()
        return redirect(url_for('admin_dentists'))
    return render_template('admin_add_dentist.html', c2c_api_key=C2C_API_KEY)

@app.route('/admin/dentists/edit/<int:dentist_id>', methods=['GET', 'POST'])
def admin_edit_dentist(dentist_id):
    db = get_db()
    dentist = db.execute("SELECT * FROM dentists WHERE id = ?", (dentist_id,)).fetchone()
    if not dentist:
        return "Dentist not found", 400
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        specialty = request.form.get('specialty')
        phone = request.form.get('phone')
        email = request.form.get('email')
        db.execute('''UPDATE dentists SET first_name = ?, last_name = ?, specialty = ?, phone = ?, email = ?
                     WHERE id = ?''',
                  (first_name, last_name, specialty, phone, email, dentist_id))
        db.commit()
        return redirect(url_for('admin_dentists'))
    return render_template('admin_edit_dentist.html', dentist=dentist, c2c_api_key=C2C_API_KEY)

# =======================
# Ngrok Process Management
# =======================

def is_ngrok_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ngrok' in proc.info['name'].lower() or (proc.info['cmdline'] and 'ngrok' in ' '.join(proc.info['cmdline']).lower()):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None

def start_ngrok():
    ngrok_pid = is_ngrok_running()
    if ngrok_pid:
        logging.info(f"Ngrok already running with PID {ngrok_pid}")
        return None
    try:
        subprocess.run([NGROK_PATH, "config", "add-authtoken", NGROK_AUTH_TOKEN], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ngrok_cmd = [NGROK_PATH, "http", "--domain=" + NGROK_DOMAIN, "8888"]
        ngrok_process = subprocess.Popen(ngrok_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        if ngrok_process.poll() is not None:
            error = ngrok_process.stderr.read().decode().strip()
            raise RuntimeError(f"Ngrok failed to start: {error}")
        logging.info(f"Started ngrok with PID {ngrok_process.pid}")
        return ngrok_process
    except Exception as e:
        logging.error(f"Error starting ngrok: {e}")
        raise

# =======================
# Application Runner
# =======================

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        logging.info("Creating new database")
        init_db()
    else:
        with app.app_context():
            db = get_db()
            cursor = db.execute("PRAGMA table_info(patients)")
            if not cursor.fetchall():
                logging.warning("Database exists but is incomplete; reinitializing")
                init_db()
    ngrok_process = None
    try:
        ngrok_process = start_ngrok()
        app.run(host="0.0.0.0", port=8888, debug=False)
    except Exception as e:
        logging.error(f"Startup error: {e}")
        if ngrok_process and ngrok_process.poll() is None:
            ngrok_process.terminate()
            logging.info("Ngrok process terminated.")
        raise
    finally:
        if ngrok_process and ngrok_process.poll() is None:
            ngrok_process.terminate()
            logging.info("Ngrok process terminated.")
EOF

# Install required Python packages
cat > dental_app/requirements.txt << 'EOF'
flask
python-dotenv
signalwire
signalwire-swaig
requests
psutil
faker
EOF

# Make script executable and run setup
chmod +x $0
echo "Setting up environment..."
python3 -m venv dental_app/venv
source dental_app/venv/bin/activate
pip install --upgrade pip
pip install -r dental_app/requirements.txt
echo "Initializing database..."
python dental_app/init_db.py
echo "Creating fake data..."
python dental_app/create_fake_data.py
echo "Setup complete! Run your Flask app with: python dental_app/app.py"

echo " ----Edit dental_app/rename.env to .env and complete the VARIABLES---- "
# Create .env file with required environment variables
cat > dental_app/rename.env << 'EOF'
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
EOF
