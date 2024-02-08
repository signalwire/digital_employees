# Function Responses
----------------------


verify_customer
-----------------

`verify_customer` shows the contents of the record of the customer once the `account_number` and `cpni` are verified.

```json

Args:
{
  "account_number": "8005000",
  "cpni": "4455"
}
```

```json

Received:
{
   "response" : "Account verified, proceed",
   "action" : [
      {
         "set_meta_data" : {
            "customer" : {
               "email_address" : "ada.lovelace@livewirecalbe.com",
               "modem_snr" : 35,
               "active" : 1,
               "first_name" : "Ada",
               "modem_upstream_level" : 0,
               "cpni" : 4455,
               "modem_downstream_level" : 55,
               "service_address" : "123 some st pittsburgh pa 15215",
               "mac_address" : "0024688924aa",
               "modem_speed_upload" : 75,
               "modem_downstream_uncorrectables" : 534,
               "phone_number" : "5551235555",
               "last_name" : "Lovelace",
               "modem_speed_download" : 955,
               "billing_address" : "123 some st pittsburgh pa 15215",
               "account_number" : 8005000,
               "id" : 1
            }
         }
      }
   ]
}
```


speed_test
-----------------

`speed_test` uses the `meta_data` from the `verified_customer` function to populate the response with `"modem_speed_download": 955` and `"modem_speed_upload": 75`

```json

Received:
{
   "response" : "Tell the user here are the test results. Download speed: 955 megabits, Upload speed: 75 megabits"
}
```

modem_diagnostics
-------------------

`modem_diagnostics` uses the `meta_data` from the `verified_customer` function to populate the response with `"modem_downstream_level": 55` , `"modem_upstream_level": 0` and `"modem_snr": 35`

```json

Received:
{
   "response" : "Tell the user here are the test results. Downstream level: 55, Upstream level: 0, Modem SNR: 35"
}
```

swap_modem
------------

`modem_swap` shows what the `"mac_address": "0012345678ff",` was before the swap and after the database was updated with the new `"mac_address": "0012345678BB"`

```json
Args:
{
  "mac_address": "0012345678BB"
}
```

```json
Received:
{
   "response" : "Customers modem mac address updated, please plug in your modem and allow 1 minute for all systems to update your new modem"
}

```




