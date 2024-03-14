const express = require('express');
const ngrok = require('ngrok');
const sqlite3 = require('sqlite3').verbose();
const bodyParser = require('body-parser');
const SignalWireML = require('./SignalwireML');
const axios = require('axios');
const app = express();
const basicAuth = require('basic-auth');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const { OAuth2Client } = require('google-auth-library');


const moment = require('moment-timezone');
const { json, urlencoded } = require('body-parser');
const fs = require('fs').promises;
const PORT = 3000; // Change the port as needed
let ngrokSubdomain;
// SQLite database setup
const db = new sqlite3.Database('./calender_database.db'); // Change this to a file path if you want to persist data

// Middleware to parse JSON requests
app.use(bodyParser.json());


const redirectUri = process.env.REDIRECT_URL+'/oauth2callback';
const scopes = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/userinfo.email'];
const oAuth2Client = new OAuth2Client(process.env.CLIENT_ID, process.env.CLIENT_SECRET, redirectUri);

// Function to create tables in the SQLite database
function create_tables() {
  db.serialize(() => {
    db.run(`
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          google_id TEXT UNIQUE, -- Unique constraint on google_id
          username TEXT,
          password TEXT,
          hd TEXT,
          verified_email BOOLEAN,
          email TEXT,
          picture TEXT
        )`);

    db.run(`
        CREATE TABLE IF NOT EXISTS google_calendar_credentials (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            scope TEXT,
            refresh_token TEXT,
            access_token TEXT,
            expires_in INTEGER,
            token_type TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id)
        )`);

  });
}

// Initialize tables when the app starts

create_tables();

// Simulated PlackResponse class
class PlackResponse {
  constructor(status) {
    this.status = status;
    this.headers = {};
    this.responseBody = ''; // Changed property name to responseBody
  }

  contentType(type) {
    this.headers['Content-Type'] = type;
  }

  setBody(content) { // Renamed the method to setBody
    this.responseBody = content;
  }

  finalize() {
    return {
      statusCode: this.status,
      headers: this.headers,
      body: this.responseBody,
    };
  }
}


async function refresh_access_token(refreshToken) {
  try {
    const { tokens } = await oAuth2Client.refreshToken(refreshToken);
    const { access_token, expires_in } = tokens;

    // Log the expiration information
    console.log(`Refreshed access token: ${access_token}`);
    console.log(`Expires in: ${expires_in} seconds`);

    return { access_token, expires_in };
  } catch (error) {
    console.error(`Error refreshing token: ${error.message}`);
    return null;
  }
}


async function does_user_exist_with_google_id(googleId) {
  console.log("googleId googleId googleId");
  console.log(googleId);
  const sql = 'SELECT COUNT(*) AS count FROM users WHERE google_id = ?';

  return new Promise((resolve, reject) => {
    db.get(sql, [googleId], (err, row) => {
      if (err) {
        console.error(`Error checking if user exists: ${err.message}`);
        reject(err);
      } else {
        const userCount = row ? row.count : 0;
        resolve(userCount > 0);
      }
    });
  });
}


async function upsert_user(userData) {

  userData.username = "HKrUk0ZDK336G84l";
  userData.password = "Fh2E0JFY5ub9Mi5t"

  const userExists = await does_user_exist_with_google_id(userData.id);
  if (userExists) {
    console.log("Update exixsting  User ");
    const insertUpdateSql = `
    INSERT INTO users
      (google_id, username, password, hd, verified_email, email, picture)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (google_id)
    DO UPDATE SET
      username = EXCLUDED.username,
      password = EXCLUDED.password,
      hd = EXCLUDED.hd,
      verified_email = EXCLUDED.verified_email,
      email = EXCLUDED.email,
      picture = EXCLUDED.picture;
  `;
    return new Promise((resolve, reject) => {
      db.run(insertUpdateSql, [
        userData.id,
        userData.username,
        userData.password,
        userData.hd,
        userData.verified_email,
        userData.email,
        userData.picture
      ], function (err) {
        if (err) {
          console.error(`Error upserting user: ${err.message}`);
          reject(err);
        } else {
          // Resolve with the user ID (last inserted/updated ID)
          const userId = this.lastID;
          console.log(`User upserted successfully with ID: ${userId}`);
          resolve(userId);
        }
      });
    });
  } else {
    console.log("Inserting new User:", userData);
    const insertSql = `
      INSERT INTO users
        (google_id, username, password, hd, verified_email, email, picture)
      VALUES (?, ?, ?, ?, ?, ?, ?);
    `;
    return new Promise((resolve, reject) => {
      db.run(insertSql, [
        userData.id,
        userData.username,
        userData.password,
        userData.hd,
        userData.verified_email,
        userData.email,
        userData.picture
      ], function (err) {
        if (err) {
          console.error(`Error inserting user: ${err.message}`);
          reject(err);
        } else {
          // Resolve with the user ID (last inserted ID)
          const userId = this.lastID;
          console.log(`User inserted successfully with ID: ${userId}`);
          resolve(userId);
        }
      });
    });
  }
}

// Function to get user information using the access token
async function get_userinfo(accessToken) {
  const response = await axios.get('https://www.googleapis.com/oauth2/v1/userinfo', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return response.data;
}
async function upsert_token_data(tokenData) {
  const sql = `
      INSERT INTO google_calendar_credentials
        (user_id, scope, refresh_token, access_token, expires_in, token_type)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT (user_id)
      DO UPDATE SET
        scope = EXCLUDED.scope,
        refresh_token = EXCLUDED.refresh_token,
        access_token = EXCLUDED.access_token,
        expires_in = EXCLUDED.expires_in,
        token_type = EXCLUDED.token_type
    `;

  return new Promise((resolve, reject) => {
    db.run(sql, [
      tokenData.user_id,
      tokenData.scope,
      tokenData.refresh_token,
      tokenData.access_token,
      tokenData.expires_in,
      tokenData.token_type
    ], function (err) {
      if (err) {
        console.error(`Error upserting token data: ${err.message}`);
        reject(err);
      } else {
        console.log(`Token data upserted successfully for user_id: ${tokenData.user_id}`);
        resolve();
      }
    });
  });
}

async function get_email_address(username) {
  return new Promise((resolve, reject) => {
    const selectEmailStmt = 'SELECT email FROM users WHERE username = ?';

    db.get(selectEmailStmt, [username], (err, row) => {
      if (err) {
        console.error(`Error retrieving email for username ${username}: ${err.message}`);
        reject(err);
        return;
      }

      if (!row) {
        console.error(`Email not found for username: ${username}`);
        resolve(null);
        return;
      }

      resolve(row.email);
    });
  });
}

// Function to get access token
async function get_access_token(username) {
  return new Promise((resolve, reject) => {
    const selectRefreshTokenStmt = 'SELECT refresh_token FROM google_calendar_credentials WHERE user_id=(SELECT id FROM users WHERE username=?)';

    db.get(selectRefreshTokenStmt, [username], async (err, row) => {
      if (err) {
        reject(err);
        return;
      }

      const refresh_token = row ? row.refresh_token : null;

      if (!refresh_token) {
        console.error(`Refresh token not found for username: ${username}`);
        resolve(null);
        return;
      }
      refresh_access_token(refresh_token)
        .then((token_info) => {
          if (token_info) {
            console.log(`Refreshed access token: ${token_info.access_token}`);
            console.log(`Expires in: ${token_info.expires_in} seconds`);

            const expires_at = Date.now() + token_info.expires_in * 1000;

            const updateStmt = 'UPDATE google_calendar_credentials SET access_token=?, expires_in=? WHERE user_id=(SELECT id FROM users WHERE username=?)';

            db.run(updateStmt, [token_info.access_token, expires_at, username], (err) => {
              if (err) {
                reject(err);
              } else {
                console.log('Refreshed token successfully');
                resolve(token_info);
              }
            });
          } else {
            console.error('Error refreshing token. Access token not available.');
            resolve(null);
          }
        })
        .catch((error) => {
          console.error(`Error refreshing token: ${error.message}`);
          resolve(null);
        });

    });
  });
}

async function create_event(access_token, calendar_id, start_time, length, timezone, email, summary, description, cal_email, location) {
  console.log("Scheduling meeting");
  console.log("Start time:", start_time);
  console.log("Length:", length);
  console.log("Timezone:", timezone);
  console.log("Email:", email);
  console.log("Summary:", summary);
  console.log("Description:", description);
  console.log("Calendar email:", cal_email);
  console.log("Location:", location);
  console.log("calendar_id:", calendar_id);

  const startMoment = moment.tz(start_time, timezone);
  const endMoment = startMoment.clone().add(length, 'minutes');
  const end_time = endMoment.format('YYYY-MM-DDTHH:mm:ssZZ');

  const url = `https://www.googleapis.com/calendar/v3/calendars/${calendar_id}/events`;

  const requestData = {
    summary,
    description,
    location,
    start: {
      dateTime: startMoment.format(),
      timeZone: timezone,
    },
    end: {
      dateTime: end_time,
      timeZone: timezone,
    },
    attendees: [
      {
        email,
        self: false,
      },
      {
        email: cal_email,
        responseStatus: 'accepted',
        optional: false,
        self: true,
      },
    ],
  };
  try {
    console.log('Request Data:', requestData);
    const response = await axios.post(url, requestData, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${access_token}`,
      },
    });

    console.log('Event created successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error creating event :', error.message);
    console.error(`API Error - Status Code: ${error.response ? error.response.status : 'Unknown'}`);
    console.error('Response Data:', error.response ? error.response.data : 'No response data available');
    throw error;
  }
}

const events = async (data, post_data, env) => {
  const swml = new SignalWireML({ version: '1.0.1' });
  console.log(post_data);

  try {
    const response = new PlackResponse(200);
    const tokens = await get_access_token(process.env.REMOTE_USER);
    const calendarEmail = await get_email_address(process.env.REMOTE_USER);
    const eventResult = await create_event(
      tokens.access_token,
      'primary',
      data.start_time,
      data.length,
      data.timezone,
      data.email,
      data.summary,
      data.description,
      calendarEmail,
      data.location
    );

    if (eventResult) {
      response.setBody(swml.swaig_response_json({ response: "Your meeting has been scheduled." }));
    } else {
      response.setBody(swml.swaig_response_json({ response: "There was an error scheduling your meeting." }));
    }

    return response.finalize();
  } catch (error) {
    console.error('Error in events:', error.message);
    const response = new PlackResponse(500);
    response.body(swml.swaig_response_json({ response: "Internal Server Error" }));
    return response.finalize();
  }
};

async function is_time_available(access_token, calendar_id, start_time, length, timezone) {
  console.log("Checking if time is available with access token:", access_token);
  console.log("Start time:", start_time);
  console.log("Length:", length);
  console.log("Timezone:", timezone);

  const startTime = new Date(start_time);
  const endTime = new Date(startTime.getTime() + length * 60000); // Convert length to milliseconds

  const url = 'https://www.googleapis.com/calendar/v3/freeBusy';

  const requestData = {
    timeMin: startTime.toISOString(),
    timeMax: endTime.toISOString(),
    timeZone: timezone,
    items: [{ id: calendar_id }],
  };
  console.log(requestData);
  try {
    const response = await axios.post(url, requestData, {
      headers: {
        Authorization: `Bearer ${access_token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 200) {
      const result = response.data;
      const busy = result.calendars[calendar_id].busy;
      console.log("Busy:", busy.length);

      if (busy.length > 0) {
        console.log("Time is NOT available");
        return 0;
      } else {
        console.log("Time is available");
        return 1;
      }
    } else {
      console.error("530 Error checking if time is available response.statusText:", response.statusText);
      return -1;
    }
  } catch (error) {
    console.error("Error checking if time is available error.message:", error.message);
    return -1;
  }
}

async function check_for_input(data,postData){
  const swml = new SignalWireML({ version: '1.0.1' });
  console.log("check_for_input function")
  console.log(require('util').inspect(postData));
  console.log(require('util').inspect(data));
  const res = new PlackResponse(200);
  res.setBody(swml.swaig_response_json({ response: 'Email addess is shashikumarece@gmail.com' }));
  return res.finalize();
}
async function freebusy(data, postData) {
  const swml = new SignalWireML({ version: '1.0.1' });

  try {
    if (process.env.DEBUG) {
      console.error(require('util').inspect(postData));
    }

    const tokenInfo = await get_access_token(process.env.REMOTE_USER);

    console.log(`In Free busy function Refreshed access token: ${tokenInfo.access_token}`);
    console.log(`In Free busy function Expires in: ${tokenInfo.expires_in} seconds`);

    const available = await is_time_available(
      tokenInfo.access_token,
      'primary',
      data.start_time,
      data.length,
      data.timezone
    );

    const res = new PlackResponse(available === 1 ? 200 : 500);

    if (available === 1) {
      res.setBody(swml.swaig_response_json({ response: 'That time is available.' }));
    } else if (available === 0) {
      res.setBody(swml.swaig_response_json({ response: 'That time is NOT available.' }));
    } else if (available === -1) {
      res.setBody(swml.swaig_response_json({ response: 'There was an error checking the calendar.' }));
    }
    return res.finalize();
  } catch (error) {
    console.error(`Error in freebusy function: ${error.message}`);
    const res = new PlackResponse(500);
    res.setBody(swml.swaig_response_json({ response: 'Internal server error.' }));
    return res.finalize();
  }
}
const functions = {
  freebusy: {
    function: freebusy,
    signature: {
      function: 'freebusy',
      purpose: 'Check if a time is available on a calendar',
      argument: {
        type: 'object',
        properties: {
          start_time: {
            type: 'string',
            description: 'start time in ISO8601 format with timezone',
          },
          length: {
            type: 'integer',
            description: 'length of time in minutes',
          },
          timezone: {
            type: 'string',
            description: 'the timezone',
          },
        },
      },
    },
  },
  events: {
    function: events,
    signature: {
      function: 'events',
      purpose: 'Schedule an event on a calendar',
      argument: {
        type: 'object',
        properties: {
          start_time: {
            type: 'string',
            description: 'start time in ISO8601 format with timezone',
          },
          length: {
            type: 'integer',
            description: 'length of time in minutes',
          },
          timezone: {
            type: 'string',
            description: 'the timezone',
          },
          email: {
            type: 'string',
            description: 'the email address of the user to schedule the event with',
          },
          summary: {
            type: 'string',
            description: 'the summary of the event',
          },
          description: {
            type: 'string',
            description: 'the description of the event',
          },
          location: {
            type: 'string',
            description: 'the location or URL of the event',
          },
        },
      },
    },
  },
};


// Get user credentials function
async function get_user_credentials(username) {
  return new Promise((resolve, reject) => {
    db.get('SELECT username, password FROM users WHERE username = ?', [username], (err, row) => {
      if (err) {
        console.error('Error getting user credentials:', err.message);
        reject(err);
      } else {
        resolve(row);
      }
    });
  });
}

// Serve static assets
app.use('/assets', express.static('/app/assets'));

app.post('/debug_webhook_url', async (req, res) => {
  const body = req.body;
  console.log("****************** debug_webhook_url webhook **************");
  console.log(JSON.stringify(body));
  res.status(200).send("ok");
  res.end();
});

app.post('/post_prompt_url', async (req, res) => {
  const body = req.body;
  console.log("****************** post_prompt_url **************");
  console.log(JSON.stringify(body));
  res.status(200).send("ok");
  res.end();
});

// Parse JSON and form-urlencoded data
app.use(json());
app.use(urlencoded({ extended: true }));

app.post('status_callback', async (req, res) => {
  const body = req.body;
  console.log("****************** status_callback webhook **************");
  console.log(JSON.stringify(body));
  res.status(200).send("ok");
  res.end();
})
// Express route for '/swaig'
app.post('/swaig', async (req, res) => {
  console.log("****************** swaig webhook **************");
  const body = req.body;
  var data;
  const swml = new SignalWireML({ version: '1.0.1' });
  console.log(JSON.stringify(body));
  console.log(body);
  const user_info = await get_user_credentials(process.env.REMOTE_USER);
  if (body.argument) {
    data = body.argument.parsed[0];
  }
  console.error(body);
  if (body.action && body.action === 'get_signature') {
    const _functions = [];
    const uuidValue = uuidv4();
    const response = {};
    for (const func of body.functions) {
      if (functions[func]) {
        functions[func].signature.web_hook_auth_user = user_info.username;
        functions[func].signature.web_hook_auth_password = user_info.password;
        functions[func].signature.web_hook_url = `https://${req.headers.host}/swaig`;
        functions[func].signature.meta_data_token = uuidValue;
        _functions.push(functions[func].signature);
      }
    }
    console.error(user_info);
    response.body = _functions;
    res.status(200).json(response.body);
  } else if (body.function && functions[body.function]?.function) {
    try {
      const response = await functions[body.function].function(data, body);
      console.log("final response from /swaig ");
      console.log(response);
      console.log("final response from /swaig ");
      res.status(response.statusCode).json(JSON.parse(response.body));
    } catch (error) {
      console.error(`Error in Express route: ${error.message}`);
      res.status(500).json(JSON.parse({ error: 'Internal server error.' }));
    }
  }else if (body.function && body.function =="check_for_input"){
    const response = await check_for_input(data, body); 
    console.log(response);
    console.log("final response from /swaig ");
    res.status(response.statusCode).json(JSON.parse(response.body));
  } else {
    const response = {};
    response.body = swml.swaig_response_json({ response: "I'm sorry, I don't know how to do that." });
    res.status(200).json(JSON.parse(response.body));
  }
});


// Generate the URL for user consent
app.get('/login', (req, res) => {
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline', // 'offline' will give you a refresh token
    prompt: 'consent',
    scope: scopes,
  });
  console.log("********************** console.log(authUrl) **********************")
  res.redirect(authUrl);
});


// Callback route to handle the code from Google after user grants permission
app.get('/oauth2callback', async (req, res) => {
  const { code } = req.query;

  // Use the code to obtain an access token and refresh token
  const { tokens } = await oAuth2Client.getToken(code);
  console.log('Access Token:', tokens.access_token);
  console.log('Refresh Token:', tokens.refresh_token);
  console.log('Tokens:', tokens);

  if (tokens) {
    const user_info = await get_userinfo(tokens.access_token);
    console.log('User Info:', user_info);
    tokens.user_id = await upsert_user(user_info);

    //const user_data = await get_username(tokens.user_id);
    console.log('User tokens.user_id :', tokens.user_id);
    await upsert_token_data(tokens);

    //res.redirect(`/success?username=${user_data.username}`);
  }
  res.send('Tokens received! Check the console for details.');
});



app.get('/main_webhook', async (req, res) => {
  try {
    // Read JSON data from the file
    const jsonData = await fs.readFile('SWML_JSON.json', 'utf-8');
    updatedJsonData = jsonData.replaceAll("NGROK_URI", ngrokSubdomain);
    const parsedData = JSON.parse(updatedJsonData);
    res.contentType('application/json');
    res.send(parsedData);
    res.end();
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

app.post('/main_webhook', async (req, res) => {
  res.contentType('application/json');
  try {
    // Read JSON data from the file
    const jsonData = await fs.readFile('SWML_JSON.json', 'utf-8');
    updatedJsonData = jsonData.replaceAll("NGROK_URI", ngrokSubdomain);
    const parsedData = JSON.parse(updatedJsonData);

    res.json(parsedData);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Start ngrok and create a tunnel for your Express app
(async () => {
  const ngrokUrl = await ngrok.connect({
    addr: PORT,
  });
  // Extract the domain from the ngrokUrl
  ngrokSubdomain = new URL(ngrokUrl).hostname;

  console.log(`ngrok tunnel is live at: ${ngrokUrl}`);
  console.log(`Extracted domain: ${ngrokSubdomain}`);

})();

app.listen(PORT, () => {
  console.log(`Express app is running on port ${PORT}`);
});