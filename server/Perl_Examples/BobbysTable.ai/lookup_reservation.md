lookup_reservation
-------------------



`Name:` lookup_reservation

`Purpose:` Lookup a reservation

`Argument:` customer_phone|The users 11 digit phone number in e.164 format

## Code:

```perl
my $env       = shift;
my $req       = Plack::Request->new( $env );
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $swml      = SignalWire::ML->new;
my $json      = JSON::PP->new->ascii->pretty->allow_nonref;
my $res       = Plack::Response->new( 200 );

my $customer_phone = $data->{customer_phone};
broadcast_by_agent_id( $agent, "Customer Phone: $customer_phone" );
# Remove all space
$customer_phone =~ s/\s+//g;
$customer_phone =~ s/^1//;
# Prepend '+1' if not already present
if ($customer_phone !~ /^\+1/) {
    $customer_phone = '+1' . $customer_phone;
}

# Ensure the phone number is exactly 12 including the +
$customer_phone = substr($customer_phone, 0, 12);

my $dbh = DBI->connect(
    "dbi:Pg:dbname=$database;host=$host;port=$port",
    $dbusername,
    $dbpassword,
    { AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

my $response = {};
broadcast_by_agent_id( $agent, "Customer Phone: $customer_phone" );
# Fetch the upcoming reservation by phone number
my $lookup_sql = "SELECT reservation_id, reservation_date, reservation_time, party_size, customer_name FROM reservations WHERE customer_phone = ? AND reservation_date >= CURRENT_DATE ORDER BY reservation_date, reservation_time LIMIT 1";
my $sth_lookup = $dbh->prepare($lookup_sql);

$sth_lookup->execute($customer_phone);

my $row_reservation = $sth_lookup->fetchrow_hashref;
broadcast_by_agent_id( $agent, $row_reservation );
if ($row_reservation) {
    $response->{response}         = "Upcoming reservation found for $row_reservation->{customer_name} party of $row_reservation->{party_size} on $row_reservation->{reservation_date} at $row_reservation->{reservation_time}.";
    $response->{reservation_id}   = $row_reservation->{reservation_id};
    $response->{reservation_date} = $row_reservation->{reservation_date};
    $response->{reservation_time} = $row_reservation->{reservation_time};
    $response->{party_size}       = $row_reservation->{party_size};
    $response->{customer_name}    = $row_reservation->{customer_name};
} else {
    $response->{response}         = "No upcoming reservations found.";
}

# Closing the database connection
$sth_lookup->finish;
$dbh->disconnect;

# Preparing JSON response
$res->content_type('application/json');
broadcast_by_agent_id( $agent, $response );
broadcast_by_agent_id( $agent, $data );

if ( $response->{reservation_id} ) {
    $res->body(  $swml->swaig_response_json( { response => $response->{response}, action => [  { set_meta_data => { reservation => $response } } ] } ) );
} else {
    $res->body(  $swml->swaig_response_json( { response => $response->{response} } ) );
}    

return $res->finalize;
```
