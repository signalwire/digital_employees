# Bobby’s Table Reservation System

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [SWML / SWAIG Functions](#swml--swaig-functions)
   - [Function: `create_reservation`](#function-create_reservation)
   - [Function: `get_reservation`](#function-get_reservation)
   - [Function: `update_reservation`](#function-update_reservation)
   - [Function: `cancel_reservation`](#function-cancel_reservation)
   - [Function: `move_reservation`](#function-move_reservation)
4. [Mock Data Structure](#mock-data-structure)
5. [Python Code Structure with Human-Readable Responses](#python-code-structure-with-human-readable-responses)
6. [Cursor Compose System Prompt](#cursor-compose-system-prompt)

---

## 1. Introduction

This document provides a design for the *Bobby's Table* reservation system using SignalWire AI Gateway (SWAIG). Each function is designed to manage reservations by directly interacting with SWAIG, eliminating the need for endpoint mappings. The system uses in-memory data storage to perform reservation operations, providing human-readable responses for LLM consumption.

---

## 2. System Overview

The *Bobby’s Table* reservation system allows users to perform actions such as creating, retrieving, updating, canceling, and moving reservations. Each function returns a response formatted for human readability, making it easier for LLMs to interpret the output.

---

## 3. SWML / SWAIG Functions

### Function: `create_reservation`

- **Purpose**: Creates a new reservation and generates a unique reservation ID.
- **Function Name**: `create_reservation`
- **Argument Description**:

  ```json
  {
    "function": "create_reservation",
    "description": "Create a new reservation for a user at the restaurant",
    "parameters": {
      "properties": {
        "name": {
          "description": "The name of the person making the reservation.",
          "type": "string"
        },
        "party_size": {
          "description": "The number of people in the reservation.",
          "type": "integer"
        },
        "date": {
          "description": "The date for the reservation in YYYY-MM-DD format.",
          "type": "string"
        },
        "time": {
          "description": "The time for the reservation in HH:MM format (24-hour time).",
          "type": "string"
        },
        "phone_number": {
          "description": "The phone number of the person making the reservation.",
          "type": "string"
        }
      },
      "type": "object"
    }
  }
  ```

### Function: `get_reservation`

- **Purpose**: Retrieves reservation details based on a reservation ID.
- **Function Name**: `get_reservation`
- **Argument Description**:

  ```json
  {
    "function": "get_reservation",
    "description": "Retrieve details of an existing reservation using a reservation ID",
    "parameters": {
      "properties": {
        "reservation_id": {
          "description": "The unique ID of the reservation to retrieve.",
          "type": "string"
        }
      },
      "type": "object"
    }
  }
  ```

### Function: `update_reservation`

- **Purpose**: Updates an existing reservation’s details.
- **Function Name**: `update_reservation`
- **Argument Description**:

  ```json
  {
    "function": "update_reservation",
    "description": "Update the details of an existing reservation",
    "parameters": {
      "properties": {
        "reservation_id": {
          "description": "The unique ID of the reservation to update.",
          "type": "string"
        },
        "name": {
          "description": "The updated name for the reservation, if changed.",
          "type": "string"
        },
        "party_size": {
          "description": "The updated party size for the reservation, if changed.",
          "type": "integer"
        },
        "date": {
          "description": "The updated date for the reservation in YYYY-MM-DD format, if changed.",
          "type": "string"
        },
        "time": {
          "description": "The updated time for the reservation in HH:MM format (24-hour time), if changed.",
          "type": "string"
        },
        "phone_number": {
          "description": "The updated phone number for the reservation, if changed.",
          "type": "string"
        }
      },
      "type": "object"
    }
  }
  ```

### Function: `cancel_reservation`

- **Purpose**: Cancels an existing reservation.
- **Function Name**: `cancel_reservation`
- **Argument Description**:

  ```json
  {
    "function": "cancel_reservation",
    "description": "Cancel an existing reservation",
    "parameters": {
      "properties": {
        "reservation_id": {
          "description": "The unique ID of the reservation to cancel.",
          "type": "string"
        }
      },
      "type": "object"
    }
  }
  ```

### Function: `move_reservation`

- **Purpose**: Moves an existing reservation to a new date and/or time.
- **Function Name**: `move_reservation`
- **Argument Description**:

  ```json
  {
    "function": "move_reservation",
    "description": "Change the date and/or time of an existing reservation",
    "parameters": {
      "properties": {
        "reservation_id": {
          "description": "The unique ID of the reservation to move.",
          "type": "string"
        },
        "new_date": {
          "description": "The new date for the reservation in YYYY-MM-DD format.",
          "type": "string"
        },
        "new_time": {
          "description": "The new time for the reservation in HH:MM format (24-hour time).",
          "type": "string"
        },
        "phone_number": {
          "description": "The phone number of the person making the reservation.",
          "type": "string"
        }
      },
      "type": "object"
    }
  }
  ```

---

## 4. Mock Data Structure

The reservation data will be stored in an in-memory dictionary using the `phone_number` in E.164 format as the key.

### Example Data Structure

```python
reservations = {
    "+19185551234": {
        "name": "John Doe",
        "party_size": 4,
        "date": "2024-11-01",
        "time": "19:00"
    },
    "+19185555678": {
        "name": "Jane Smith",
        "party_size": 2,
        "date": "2024-11-02",
        "time": "18:30"
    }
}
```

---

## 5. Python Code Structure with Human-Readable Responses

Here’s the Python code for each function to provide a `response` field containing a human-readable statement for LLM consumption.

```python
@swaig.endpoint(
    description="Create a new reservation for a customer",
    name=Parameter(type="string", description="The name of the person making the reservation"),
    party_size=Parameter(type="integer", description="Number of people in the party"),
    date=Parameter(type="string", description="Date of reservation in YYYY-MM-DD format"),
    time=Parameter(type="string", description="Time of reservation in HH:MM format (24-hour)"),
    phone_number=Parameter(type="string", description="Contact phone number in E.164 format (e.g., +19185551234)")
)
def create_reservation_endpoint(name, party_size, date, time, phone_number, meta_data_token=None, meta_data=None):
    return create_reservation({
        "name": name,
        "party_size": party_size,
        "date": date,
        "time": time,
        "phone_number": phone_number
    })

@swaig.endpoint(
    description="Retrieve an existing reservation",
    phone_number=Parameter(type="string", description="Phone number used for the reservation in E.164 format")
)
def get_reservation_endpoint(phone_number, meta_data_token=None, meta_data=None):
    return get_reservation({"phone_number": phone_number})

@swaig.endpoint(
    description="Update an existing reservation",
    phone_number=Parameter(type="string", description="Phone number of the existing reservation"),
    name=Parameter(type="string", description="Updated name (optional)", required=False),
    party_size=Parameter(type="integer", description="Updated party size (optional)", required=False),
    date=Parameter(type="string", description="Updated date in YYYY-MM-DD format (optional)", required=False),
    time=Parameter(type="string", description="Updated time in HH:MM format (optional)", required=False)
)
def update_reservation_endpoint(phone_number, name=None, party_size=None, date=None, time=None, meta_data_token=None, meta_data=None):
    return update_reservation({
        "phone_number": phone_number,
        "name": name,
        "party_size": party_size,
        "date": date,
        "time": time
    })

@swaig.endpoint(
    description="Cancel an existing reservation",
    phone_number=Parameter(type="string", description="Phone number of the reservation to cancel")
)
def cancel_reservation_endpoint(phone_number):
    return cancel_reservation({"phone_number": phone_number})

@swaig.endpoint(
    description="Move an existing reservation to a new date and time",
    phone_number=Parameter(type="string", description="Phone number of the existing reservation"),
    new_date=Parameter(type="string", description="New date in YYYY-MM-DD format"),
    new_time=Parameter(type="string", description="New time in HH:MM format")
)
def move_reservation_endpoint(phone_number, new_date, new_time, meta_data_token=None, meta_data=None):
    return move_reservation({
        "phone_number": phone_number,
        "new_date": new_date,
        "new_time": new_time
    })
```