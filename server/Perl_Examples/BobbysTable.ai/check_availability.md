# check_availability


`Name:` check_availability

`Purpose:` Check for availability

`Argument:` reservation_date|proposed date of reservation,reservation_time|proposed time of reservation,party_size|number of guests

## Code:

```perl
my $env             = shift;
my $req             = Plack::Request->new($env);
my $post_data       = decode_json($req->raw_body);
my $data            = $post_data->{argument}->{parsed}->[0];
my $swml            = SignalWire::ML->new;
my $json            = JSON::PP->new->ascii->pretty->allow_nonref;
my $res             = Plack::Response->new(200);

my $reservation_date = $data->{reservation_date};
my $reservation_time = $data->{reservation_time};
my $party_size       = $data->{party_size};
my $restaurant_id    = 1;

my $dbh = DBI->connect(
    "dbi:Pg:dbname=$database;host=$host;port=$port",
    $dbusername,
    $dbpassword,
    { AutoCommit => 1, RaiseError => 1 }
) or die "Couldn't execute statement: $DBI::errstr\n";

my $response = {};
# Check capacity
my $max_capacity = 50;  # Replace with the actual maximum capacity

my $total_party_size_sql = "SELECT COALESCE(SUM(party_size), 0) as total_party_size FROM reservations WHERE restaurant_id = ? AND reservation_date = ? AND reservation_time >= ? AND reservation_time <= ? + INTERVAL '1 hours'";

my $sth_party_size = $dbh->prepare($total_party_size_sql);
$sth_party_size->execute($restaurant_id, $reservation_date, $reservation_time, $reservation_time);

my $row_party_size = $sth_party_size->fetchrow_hashref;
$sth_party_size->finish;
my $total_party_size = $row_party_size->{total_party_size} || 0;

# Calculate available capacity
my $available_capacity = $max_capacity - $total_party_size;



if ($party_size > $available_capacity) {
    $response->{response} = "Requested party size exceeds available capacity.";
} else {
    # Availability check SQL (checking for overlapping reservations)
    my $check_availability_sql = "SELECT CASE WHEN EXISTS ( SELECT 1 FROM reservations WHERE restaurant_id = ? AND reservation_date = ? AND (reservation_time, reservation_time + INTERVAL '1 hours') OVERLAPS (?, ? + INTERVAL '1 hour') ) THEN 1 ELSE 0 END";

    my $sth_availability = $dbh->prepare($check_availability_sql);
    $sth_availability->execute($restaurant_id, $reservation_date, $reservation_time, $reservation_time);

    my $availability_check_passed = $sth_availability->fetchrow_array;
    $sth_availability->finish;

    if (!$availability_check_passed) {
        $response->{response} = "Requested time and date are available.";
    } else {
        $response->{response} = "Requested time and date are not available. Offer to check an hour before and after the requested time.";
    }
}

# Closing the database connection
$dbh->disconnect;

$res->content_type('application/json');

$res->body($swml->swaig_response_json({ response => $response->{response}, action => [ { back_to_back_functions => "true" } ] }));

return $res->finalize;
```
