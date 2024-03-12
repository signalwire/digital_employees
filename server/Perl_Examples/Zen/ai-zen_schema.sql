CREATE TABLE customers (
    id INT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    active BOOLEAN,
    phone_number TEXT,
    mac_address TEXT,
    cpni INT,
    account_number INT,
    service_address TEXT,
    billing_address TEXT,
    email_address TEXT,
    modem_speed_upload REAL,
    modem_speed_download REAL,
    modem_upstream_level REAL,
    modem_downstream_level REAL,
    modem_snr INT,
    modem_downstream_uncorrectables INT
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
