

# Digital Employee List

* [Flos_Flowers](https://github.com/signalwire/digital_employees/tree/main/serverless/Flos_Flowers)
* [Weather_Bot](https://github.com/signalwire/digital_employees/tree/main/serverless/Weather_Bot)

------------------------

Copy, Paste, Edit.  Copy the SWML example, paste into a new SWML bin and edit.

# Calling with PSTN




# Calling With SIP

Using a sip address to dial to your Digital Employee via a Domain App. 

## Create a SWML Bin

* Create a SWML Bin from one of the examples.

![image](https://github.com/signalwire/digital_employees/assets/13131198/85a36e64-8ec0-426c-a412-c6d1a4b412dd)


## Create a Domain App

* Create the Domain App if one doesn't exist or if you want a new one.
* In the `HANDLE USING` section, select `a SWML Script`
* In the `WHEN A CALL COMES IN` section select the SWML Bin to use.

![image](https://github.com/signalwire/digital_employees/assets/13131198/1c8761fd-d265-469a-b155-a6646bd25589)

![image](https://github.com/signalwire/digital_employees/assets/13131198/9140e2c9-48ff-4338-a31f-55400f3489d4)


## Assign to a Domain App

* Assign the SWML Bin to an existing Domain App.
* In the `HANDLE USING` section, select `a SWML Script`
* In the `WHEN A CALL COMES IN` section select the SWML Bin to use.

![image](https://github.com/signalwire/digital_employees/assets/13131198/a27a32ac-ebf1-4803-91e2-699718aab08f)



![image](https://github.com/signalwire/digital_employees/assets/13131198/9140e2c9-48ff-4338-a31f-55400f3489d4)


## Make Call


Now you can make a call with `sip:Call-This@len-Call.dapp.signalwire.com`
