<div style="border:2px dashed #4CAF50; padding:1em; border-radius:8px; background:#f9fff9;">
  
## 🚀 Technical Overview of `skill.py`

The **`skill.py`** file brings the **Restaurant Reservation Skill** to life for **SignalWire AI Agents**, letting your virtual maître d' handle every step—from booking tables to processing payments and sending SMS confirmations.  

---

### 🎯 Purpose & Scope

- **Objective**: Define `RestaurantReservationSkill` to handle:
  - Table bookings 🍽️  
  - Menu pre-orders 🥗  
  - Payment flows 💳  
  - SMS notifications 📲  
- **Use Case**: Voice & text interactions for seamless restaurant bookings:
  > “I need a table for party of 2 this Saturday at 7pm? My name is Jim Smith. The other person is Chuck Norris. We would both like a surprise drink and food item from the menu.”  
- **Dependencies**:
  - **Flask** (app context) 🐍  
  - **SignalWire Agents SDK** 🤖  
  - **SQLAlchemy** models (`Reservation`, `Order`, `MenuItem`) 🗃️  

---

### 🛠️ Key Components

1. **Class Definition: `RestaurantReservationSkill`**
   - Inherits from `SkillBase` from SignalWire  
   - Metadata badges:
     - 🏷️ `SKILL_NAME`: `"restaurant_reservation"`  
     - 🔖 `SKILL_VERSION`: `"1.0.0"`  
     - 📝 `SKILL_DESCRIPTION`: “Manage restaurant reservations…”  
   - Initializes SMS sender `SIGNALWIRE_FROM_NUMBER` (defaults to `+15551234567`)

2. **Menu Management**  
   - 📦 **Caching**: Saves menu in `meta_data` to reduce DB hits  
   - 🔄 **Retry Logic**: `_load_menu_with_retry()` handles flaky DB calls  
   - 🕵️‍♂️ **Fuzzy Matching**: `_find_menu_item_fuzzy()` + Levenshtein distance for typos (“kraft lemonade” → “craft lemonade”)

3. **Reservation Management**  
   - 🆕 `create_reservation()`  
   - 🔄 `update_reservation()`  
   - ❌ `cancel_reservation()`  
   - 🔍 `get_reservation()`  
   - 🤖 Auto-extract missing details (phone, date) from conversation history

4. **Order Processing**  
   - 🍕 `_parse_individual_orders_enhanced()`: Assign items to guests  
   - 🎲 `_generate_order_number()`: Unique order IDs  
   - ✅ `_validate_and_fix_party_orders()`: Ensures each guest gets what they ordered  

5. **Payment Processing**  
   - 💳 Uses SignalWire’s `pay()` (Stripe under the hood)  
   - 🔁 Retry with `_payment_retry_handler()`  
   - 🔍 Status checks via `_check_payment_status_handler()`  
   - Auto-detects new reservations to prompt payment  

6. **SMS Notifications**  
   - 📩 `_send_reservation_sms()` and `_send_payment_confirmation_sms()`  
   - Includes calendar links 🗓️ & order breakdowns  
   - Honors user consent for SMS with `_offer_sms_confirmation_handler()`

7. **Tool Registration**  
   - Registers JSON-schema-driven tools like `create_reservation` & `pay_reservation`  
   - Each tool pairs parameters (e.g. `name`, `party_size`, `date`) with a handler  

8. **Error Handling & Robustness**  
   - 🛡️ Extensive `try/except` blocks  
   - 🔄 Fallback to hardcoded menu on DB failures  
   - 📊 Cache-freshness validation to keep data crisp  

---

### 🎨 Technical Features at a Glance

| Feature               | Detail                                                                                      |
|-----------------------|---------------------------------------------------------------------------------------------|
| **DB Integration**    | SQLAlchemy models: `Reservation`, `Order`, `OrderItem`, `MenuItem`                          |
| **Session State**     | Uses `meta_data` to store reservation/payment flags across interactions                     |
| **NLP Helpers**       | Regex & fuzzy matching to extract phone numbers, dates, “yes/no” responses                  |
| **Env Config**        | Relies on env vars (`SIGNALWIRE_PROJECT_ID`, `BASE_URL`) for secure, flexible setup         |
| **Modular Design**    | Clear separation: menu caching, order parsing, payment processing, SMS sending              |

---

### Pay Reservation Skill: `pay_reservation_skill`

1. Reservation number  
2. Cardholder name  
3. Phone number
4. Processes payment & announces success/failure  

</div>
