# create_reservation



`Name:` create_reservation

`Purpose:` Create a reservation

`Argument:` reservation_date|create a reservation for a date,reservation_time|create reservation in military time,party_size|number of guests,customer_name|name of guest,customer_phone|phone number of guest in e.164 format

## Code:

```perl
my $env       = shift;
my $req       = Plack::Request->new( $env );
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $swml      = SignalWire::ML->new;
my $json      = JSON::PP->new->ascii->pretty->allow_nonref;
my $res       = Plack::Response->new( 200 );

my $reservation_date = $data->{reservation_date};
my $reservation_time = $data->{reservation_time};
my $party_size       = $data->{party_size};
my $customer_name    = $data->{customer_name};
my $customer_phone   = $data->{customer_phone};

#  my $restaurant_id    = $data->{restaurant_id};
my $restaurant_id    = 1;

sub generate_random_string {
    my $length = 8;
    my @chars = ('0'..'9', 'A'..'Z', 'a'..'z');
    my $random_string;
    foreach (1..$length) {
        $random_string .= $chars[rand @chars];
    }
    return $random_string;
}

# Remove all space
$customer_phone =~ s/\s+//g;
$customer_phone =~ s/^1//;
# Prepend '+1' if not already present
if ($customer_phone !~ /^\+1/) {
    $customer_phone = '+1' . $customer_phone;
}

# Ensure the phone number is exactly 12 digits
$customer_phone = substr($customer_phone, 0, 12);

my $dbh = DBI->connect(
    "dbi:Pg:dbname=$database;host=$host;port=$port",
    $dbusername,
    $dbpassword,
    { AutoCommit => 0, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

my $response = {};

my ($requested_hours, $requested_minutes) = split(/:/, $reservation_time);
my $requested_time_in_seconds = ($requested_hours * 3600) + ($requested_minutes * 60);
my $end_time_in_seconds = $requested_time_in_seconds + 3600;
my $end_hours = int($end_time_in_seconds / 3600);
my $end_minutes = int(($end_time_in_seconds % 3600) / 60);  # Subtract 1 minute to avoid overlapping reservations
my $reservation_end_time = sprintf("%02d:%02d", $end_hours, $end_minutes);

my $max_capacity = 50;  # Replace with the actual maximum capacity

my $total_party_size_sql = "SELECT COALESCE(SUM(party_size), 0) as total_party_size FROM reservations WHERE restaurant_id = ? AND reservation_date = ? AND reservation_time >= ? AND reservation_time <= ? + INTERVAL '1 hours'";

my $sth_party_size = $dbh->prepare($total_party_size_sql);
$sth_party_size->execute($restaurant_id, $reservation_date, $reservation_time, $reservation_time);

my $row_party_size = $sth_party_size->fetchrow_hashref;
my $total_party_size = $row_party_size->{total_party_size} || 0;

# Calculate available capacity
my $available_capacity = $max_capacity - $total_party_size;


# Check if the available capacity is sufficient for the party size
if ($party_size <= $available_capacity) {
    # Availability check SQL (checking for overlapping reservations)
    my $check_availability_sql = "SELECT CASE WHEN EXISTS ( SELECT 1 FROM reservations WHERE restaurant_id = ? AND reservation_date = ? AND (reservation_time, reservation_time + INTERVAL '1 hours') OVERLAPS (?, ? + INTERVAL '1 hour') ) THEN 1 ELSE 0 END";

    my $sth_availability = $dbh->prepare($check_availability_sql);
    $sth_availability->execute($restaurant_id, $reservation_date, $reservation_time, $reservation_time);

    my $availability_check_passed = $sth_availability->fetchrow_array;
    $sth_availability->finish;
	
    if (!$availability_check_passed) {
        my $reservation_key = generate_random_string();
        my $insert_reservation_sql = "INSERT INTO reservations (restaurant_id, reservation_date, reservation_time, reservation_key, party_size, customer_name, customer_phone) VALUES (?, ?, ?, ?, ?, ?, ?)";	
        my $sth_insert = $dbh->prepare($insert_reservation_sql);
        $sth_insert->execute($restaurant_id, $reservation_date, $reservation_time, $reservation_key, $party_size, $customer_name, $customer_phone);
        $dbh->commit;  # Commit the transaction
        $sth_insert->finish;
        $response->{response} = "Reservation successfully created. Here is the URL to update or cancel it, include it with the text message https://bobbystable.ai/view?rk=$reservation_key";
    } else {
        $dbh->rollback;  # Rollback the transaction
        $response->{response} = "Reservation failed. Time not available. Offer to check an hour before and after the requested time.";
    }

    # Closing the database connection # https://xkcd.com/327/
    $sth_availability->finish;
    $dbh->disconnect;
} else {
	$dbh->rollback;  # Rollback the transaction
	$response->{response} = "Reservation failed. Time not available. Offer to check an hour before and after the requested time.";
}

# Preparing JSON response
$res->content_type('application/json');
broadcast_by_agent_id( $agent, $response );
broadcast_by_agent_id( $agent, $data );
$res->body(  $swml->swaig_response_json( { response=> $response->{response} } ) );
    
return $res->finalize;
```
