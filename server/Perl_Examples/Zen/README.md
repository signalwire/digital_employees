### AI Zen is a demo Tier 1 Support Digital Employee powered by SignalWire at the cable company Livewire. 

![image](https://github.com/signalwire/digital_employees/assets/13131198/beba8304-be29-4c6e-b16b-1591fc605c2b)




#### Server OS/applications needed:

* Debian 12
* Perl
* NGINX
* NGROK
* [SignalWire AI Agent](https://signalwire.com/products/ai-agent?utm_source=AI-Zen)

### Docker Container
#### To use Zen with a docker container please see [WireStarter](https://github.com/signalwire/WireStarter)

## Prompt Used

```xml

# Your name is Zen. You speak English.

# Personality and Introduction

You are a witty assistant who likes to make light of every situation but is very dedicated to helping people. You are Zen and work for the local cable company Livewire. Greet the user with that information.

# Your Skills, Knowledge, and Behavior

## Reboot Modem

This will reboot the modem.

## Check Modem

Check if the modem is online or offline.

## Modem Speed Test

This will perform a speed test from the modem to a speed test site with speed_test function.

## Modem Speed Subscription

The customer subscribes to 1 gigabit download and 75 megabits upload.

## Modem Signal

The upstream can be between 40db and 50db. The downstream can be between -10db and +10db.

## SNR

SNR is signal-to-noise ratio. A good SNR is 30db to 40db.

## Swap Modem

Be sure to ask for new mac address. Read back to the provided mac address to verify it's accuracy. If the user verifies it is correct then use swap_modem function.

## Transfer Calls

You are able to transfer calls to the following destinations: Sales, Supervisor, Freeswitch, External.

## Customer Verification

You are able to verify customer first name, last name, cpni, account number and phone number with verify_customer function.

# Conversation Flow

These are the steps you need to follow during this conversation. Ensure you are strictly following the steps below in order.

## Step 1

Ask the user for their account number and CPNI, Then use verify_customer function to verify the customer . If the account number and CPNI are incorrect after 4 attempts, continue.

## Step 2

Perform a speed test and give the results from speed_test function then give the results.

## Step 3

Check modem levels with modem_diagnostics function and give the results.

## Step 4

Check modem SNR with modem_diagnostics function and give the results.

## Step 5

Ask the customer if there is anything else you can help them with.

## Step 6

End all calls with saying "Thank you for choosing Livewire."
```

## Functions

Functions in this example will connect to a database and pull data with json output. In this example, once the function `verify_customer` is executed by the user verifing the `account_number` and `cpni` then the record for that customer can be used later. The prompt for this example won't allow any further steps to happen unless verify_customer is validated.


verify_customer
-----------------------

* Name:`verify_customer`
* Purpose:`Verify customer account number, cpni first, last name and phone number`
* Argument:`account_number|7 digit number,cpni|4 digit number`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );

my $dbh = DBI->connect(
  "dbi:Pg:dbname=$database;host=$host;port=$port",
  $dbusername,
  $dbpassword,
  { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";
my $sql = "SELECT * FROM customers WHERE account_number = ? AND cpni = ? LIMIT 1";

my $sth = $dbh->prepare( $sql );
$sth->bind_param(1,$data->{account_number});
$sth->bind_param(2,$data->{cpni});
$sth->execute() or die "Couldn't execute statement: $DBI::errstr";

my $agents = $sth->fetchrow_hashref;


if ($data->{account_number} eq $agents->{account_number} && $data->{cpni} eq $agents->{cpni}) {
    $res->body( $swml->swaig_response_json( { response => "Account verified, proceed", action => [  { set_meta_data => { customer => $agents } } ] } ) );
} else {
    # This is the failure
    $res->body( $swml->swaig_response_json( { response => "Account invalid try again" } ) ) ;
}

return $res->finalize;
```

## Meta_Data Functions

Meta_Data Functions access the output of an already executed function. In this example once the function `verify_customer` is executed by the user by verifing `account_number` and cpni then the record for that customer is accessable via json for any meta_data functions.

modem_swap
-----------------------

* Name:`modem_swap`
* Purpose:`Swap the users modem`
* Argument:`mac_address|new modem MAC Address in lowercase hex 12 characters`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $customer  = $post_data->{meta_data}->{customer};

sub is_valid_mac_address {
    my ($mac) = @_;

    # Regular expression for a MAC address with optional colons or dashes
    my $mac_regex = qr/^([0-9A-Fa-f]{2}(:|-)?){5}[0-9A-Fa-f]{2}$/;

    return $mac =~ $mac_regex;
}

my $dbh = DBI->connect(
  "dbi:Pg:dbname=$database;host=$host;port=$port",
  $dbusername,
  $dbpassword,
  { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

if ( is_valid_mac_address($data->{mac_address}) ) {
# Add a SQL update statement (modify this to match your actual table and field names)
    my $update_sql = "UPDATE customers SET mac_address = ? WHERE account_number = ?";
    my $update_sth = $dbh->prepare( $update_sql );
    $update_sth->bind_param(1, $data->{mac_address});
    $update_sth->bind_param(2, $customer->{account_number});
    $update_sth->execute() or die "Couldn't execute statement: $DBI::errstr";

    $update_sth->finish;

# Your existing SELECT query
    my $select_sql = "SELECT * FROM customers WHERE account_number = ? LIMIT 1";
    my $select_sth = $dbh->prepare( $select_sql );
    $select_sth->bind_param(1, $customer->{account_number} );
    $select_sth->execute() or die "Couldn't execute statement: $DBI::errstr";

    my $agents = $select_sth->fetchrow_hashref;

    $select_sth->finish;

    if (lc $agents->{mac_address} eq lc $data->{mac_address} ) {
        $res->body( $swml->swaig_response_json( { response => "Customers modem mac address updated, please allow 5 minutes for all systems to update and plug in your new modem.", action => [  { set_meta_data => { customer => $agents } } ] } ) );
        broadcast_by_agent_id( $agent, $agents );
        
    } else {
        $res->body( $swml->swaig_response_json( { response => "Error swapping modem, mac address may be invalid, try again.  #1" } ) );
    }
} else {
    $res->body( $swml->swaig_response_json( { response => "Error swapping modem, mac address may be invalid, try again later.  #2" } ) );  
}

return $res->finalize;

```

speed_test
-----------------------

* Name:`speed_test`
* Purpose:`Test upload and download speed from the modem`
* Argument:`account_number|7 digit number,cpni|4 digit number`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $customer  = $post_data->{meta_data}->{customer};

if ($customer->{modem_speed_upload} && $customer->{modem_speed_download}) {
    $res->body( $swml->swaig_response_json( { response => "Tell the user here are the test results. Download speed: $customer->{modem_speed_download}, Upload speed: $customer->{modem_speed_upload}" } ) );
} else {
    $res->body( $swml->swaig_response_json( { response => "Invalid try again speed_test" } ) );
}

return $res->finalize;
```

modem_diagnostics
-----------------------

* Name:`modem_diagnostics`
* Purpose:`customer modem upstream downstream and snr levels`
* Argument:`account_number|7 digit number,cpni|4 digit number`

```bash

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $customer  = $post_data->{meta_data}->{customer};

if ($customer) {
    $res->body( $swml->swaig_response_json( { response => "Tell the user here are the test results. Downstream level: $customer->{modem_downstream_level}, Upstream level: $customer->{modem_upstream_level}, Modem SNR: $customer->{modem_snr}" } ) );
} else {
    $res->body( $swml->swaig_response_json( { response => "Invalid try again. Use modem-diagnostics-function" } ) );
}

return $res->finalize;
```

---------------------

### SignalWire

#### SignalWire’s AI Agent for Voice allows you to build and deploy your own digital employee. Powered by advanced natural language processing (NLP) capabilities, your digital employee will understand caller intent, retain context, and generally behave in a way that feels “human-like”.  In fact, you may find that it behaves exactly like your best employee, elevating the customer experience through efficient, intelligent, and personalized interactions.
