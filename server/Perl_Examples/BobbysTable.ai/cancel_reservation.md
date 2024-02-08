# cancel_reservation

`Name:` cancel_reservation

`Purpose:` Cancel a reservation

`Argument:` customer_phone|The users phone number in e.164 format

## Code:

```perl
my $env       = shift;
my $req       = Plack::Request->new( $env );
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $swml      = SignalWire::ML->new;
my $json      = JSON::PP->new->ascii->pretty->allow_nonref;
my $res       = Plack::Response->new( 200 );
my $guest     = $post_data->{meta_data}->{reservation};
  
my $reservation_id = $guest->{reservation_id};

my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

my $response = {};

# Check if the reservation exists
my $check_reservation_sql = "SELECT reservation_id FROM reservations WHERE reservation_id = ?";
my $sth_check = $dbh->prepare($check_reservation_sql);
$sth_check->execute($reservation_id);

my $existing_reservation_id = $sth_check->fetchrow_array;
$sth_check->finish;

if ($existing_reservation_id) {
    # Delete the reservation
    my $delete_reservation_sql = "DELETE FROM reservations WHERE reservation_id = ?";
    my $sth_delete = $dbh->prepare($delete_reservation_sql);
    $sth_delete->execute($reservation_id);
    $sth_delete->finish;

    $response->{response} = "Reservation with ID $reservation_id has been canceled. Ask if the user needs anything else.";
} else {
    $response->{response} = "Reservation not found.";
}

# Closing the database connection
$dbh->disconnect;

# Preparing JSON response
$res->content_type('application/json');
broadcast_by_agent_id( $agent, $response );
broadcast_by_agent_id( $agent, $data );
$res->body(  $swml->swaig_response_json( { response=> $response->{response}, action => [ { back_to_back_functions => "true"} ] } )  );

return $res->finalize;
```
