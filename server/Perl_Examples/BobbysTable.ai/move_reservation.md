# move_reservation


`Name:` move_reservation

`Purpose:` move a current reservation

`Argument:` minutes_to_move|The number of minutes to move the reservation forward

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

my $reservation_id  = $guest->{reservation_id};
my $minutes_to_move = $data->{minutes_to_move};

my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 0, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

my $response = {};

# Fetch the current reservation details, including date and time
my $fetch_reservation_sql = "SELECT reservation_date, reservation_time, party_size FROM reservations WHERE reservation_id = ?";
my $sth_fetch = $dbh->prepare($fetch_reservation_sql);
$sth_fetch->execute($reservation_id);

my $row_reservation = $sth_fetch->fetchrow_hashref;
my $reservation_date = $row_reservation->{reservation_date};
my $current_reservation_time = $row_reservation->{reservation_time};
my $party_size = $row_reservation->{party_size};

# Calculate the new reservation time
my ($current_hours, $current_minutes) = split(/:/, $current_reservation_time);
my $current_time_in_seconds = ($current_hours * 3600) + ($current_minutes * 60);
my $new_time_in_seconds = $current_time_in_seconds + ($minutes_to_move * 60);

my $max_capacity = 50;  # Replace with the actual maximum capacity

if ($new_time_in_seconds >= 0) {
    # Calculate new time hours and minutes, taking into account rollover to the next day
    my $new_hours = int($new_time_in_seconds / 3600);
    my $new_minutes = int(($new_time_in_seconds % 3600) / 60);
    # Check if the new time rolls over to the next day
    if ($new_hours >= 24) {
        my $days_to_add = int($new_hours / 24);
        $new_hours = $new_hours % 24;
            # Move the date forward by the number of days
        my $current_date = DateTime->new(
            year   => substr($reservation_date, 0, 4),
            month  => substr($reservation_date, 5, 2),
            day    => substr($reservation_date, 8, 2),
        );
        $current_date->add(days => $days_to_add);
        $reservation_date = $current_date->ymd('-');
    }

    my $new_reservation_time = sprintf("%02d:%02d", $new_hours, $new_minutes);

    # Check if the new time is within restaurant open hours (2 PM to 11 PM (minus 1 hour) for final reservation)
    if ($new_hours >= 14 && $new_hours < 22) {
        # Check if the new time exceeds capacity
        my $total_party_size_sql = "SELECT COALESCE(SUM(party_size), 0) as total_party_size FROM reservations WHERE reservation_date = ? AND reservation_time = ?";
        my $sth_party_size = $dbh->prepare($total_party_size_sql);
        $sth_party_size->execute($reservation_date, $new_reservation_time);

        my $row_party_size = $sth_party_size->fetchrow_hashref;
        my $total_party_size = $row_party_size->{total_party_size} || 0;
        $sth_party_size->finish;

        if ($total_party_size + $party_size > $max_capacity) {
            $response->{response} = "Time cannot be moved forward. It would exceed the restaurant's capacity.";
        } else {
            # Update the reservation time
            my $update_time_sql = "UPDATE reservations SET reservation_date = ?, reservation_time = ? WHERE reservation_id = ?";
            my $sth_update_time = $dbh->prepare($update_time_sql);
            $sth_update_time->execute($reservation_date, $new_reservation_time, $reservation_id);
            $dbh->commit;  # Commit the transaction
            $sth_update_time->finish;
            $response->{response} = "Reservation moved forward to $reservation_date $new_reservation_time.";
        }
    } else {
        # Move to the next day's opening time (2 PM)
        my $next_day = DateTime->new(
            year   => substr($reservation_date, 0, 4),
            month  => substr($reservation_date, 5, 2),
            day    => substr($reservation_date, 8, 2),
        );
        $next_day->add(days => 1);
        my $next_day_date = $next_day->ymd('-');
        my $next_day_time = "14:00";  # Opening time on the next day
            # Check if the new time on the next day exceeds capacity
        my $total_party_size_sql = "SELECT COALESCE(SUM(party_size), 0) as total_party_size FROM reservations WHERE reservation_date = ? AND reservation_time = ?";
        my $sth_party_size = $dbh->prepare($total_party_size_sql);
        $sth_party_size->execute($next_day_date, $next_day_time);

        my $row_party_size = $sth_party_size->fetchrow_hashref;
        my $total_party_size = $row_party_size->{total_party_size} || 0;
        $sth_party_size->finish;

        if ($total_party_size + $party_size > $max_capacity) {
            $response->{response} = "Time cannot be moved forward. It would exceed the restaurant's capacity.";
        } else {
            # Update the reservation date and time
            my $update_time_sql = "UPDATE reservations SET reservation_date = ?, reservation_time = ? WHERE reservation_id = ?";

            my $sth_update_time = $dbh->prepare($update_time_sql);
            $sth_update_time->execute($next_day_date, $next_day_time, $reservation_id);

            $dbh->commit;  # Commit the transaction
            $sth_update_time->finish;
            $response->{response} = "Reservation moved forward to $next_day_date $next_day_time.";
        }
    }
} else {
    # Move backward
    $response->{response} = "Moving the reservation time backward is not supported.";
}

# Closing the database connection
$sth_fetch->finish;
$dbh->disconnect;

$res->content_type('application/json');
broadcast_by_agent_id( $agent, $response );
broadcast_by_agent_id( $agent, $data );
$res->body($swml->swaig_response_json({ response => $response->{response} }));
return $res->finalize;
```

