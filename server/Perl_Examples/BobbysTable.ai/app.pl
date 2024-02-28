#!/usr/bin/env perl
# app.pl - SignalWire AI Agent Bobby's Table Demo Application
use lib '.', '/app';
use strict;
use warnings;

# SignalWire modules
use SignalWire::RestAPI;
use SignalWire::ML;

# PSGI/Plack
use Plack::Builder;
use Plack::Runner;
use Plack::Request;
use Plack::Response;
use Plack::App::Directory;

# Other modules
use List::Util qw(shuffle);
use HTTP::Request::Common;
use HTML::Template::Expr;
use LWP::UserAgent;
use Time::Piece;
use JSON::PP;
use Data::Dumper;
use DateTime;
use Env::C;
use DBI;
use File::Slurp qw(read_file);

# Array of slogans
my @slogans = (
    "Where Your Appetite Meets Our 'SELECT' Recipes!",
    "Join the 'JOIN' at Bobby's Table Flavorful Queries Served Daily!",
    "'INSERT' Flavor, 'DELETE' Hunger!",
    "Dine In, 'UPDATE' Your Tastes!",
    "'DROP' In for a Byte of Delight!",
    "'ALTER' Your Dining, Elevate Your Experience!",
    "Savor the 'UNION' of Taste and Tech!",
    "'COMMIT' to a Meal at Bobby's Table Exceptionally Executed Eats!",
    "Where Every 'TABLE' Tells a Tasty Tale!",
    "Experience GROUP BY' Gastronomy 'WHERE' Every Dish Connects!",
    "Feast on 'SELECT' Specials Every Day!",
    "Where 'JOIN' Meets Joy Culinary Queries Answered!",
    "INSERT Flavor, DELETE Boredom!",
    "UPDATE Your Dining Experience with Us!",
    "DROP In for a Byte of Unexpected Delights!",
    "ALTER Your Appetite, Elevate Your Meal!",
    "Savor the UNION of Innovative Cuisine and Technology!",
    "COMMIT to a Culinary Adventure Like No Other!",
    "Every TABLE Tells a Story of Flavor and Fun!",
    "GROUP BY Gourmet Connecting Dishes and Diners!"
);
my $function = {
    lookup_reservation =>  { function => \&lookup_reservation,
			     signature => {
				 function => "lookup_reservation",
				 argument => {
				     properties => {
					 customer_phone => {
					     type => "string",
					     description => "The users phone number in e.164 format",
					 },
				     },
				     required => ["customer_phone"],
				     type => "object",
				 },
				 purpose => "Lookup a reservation",
				 active => "true",
			     },
    },
    cancel_reservation => { function => \&cancel_reservation,
			     signature => {
				 active => "true",
				 purpose => "Cancel a reservation",
				 argument => {
				     required => ["customer_phone"],
				     properties => {
					 customer_phone => {
					     description => "The users phone number in e.164 format",
					     type => "string",
					 },
				     },
				     type => "object",
				 },
				 function => "cancel_reservation",
			     },
    },
    move_reservation => { function => \&move_reservation,
			  signature => {
			      active => "true",
			      argument => {
				  properties => {
				      minutes_to_move => {
					  type => "string",
					  description => "The number of minutes to move the reservation forward",
				      },
				  },
				  required => ["minutes_to_move"],
				  type => "object",
			      },
			      purpose => "Move a current reservation",
			      function => "move_reservation",
			  },
    },
    check_availability => { function =>\&check_availability,
			    signature => {
				purpose => "Check for availability",
				argument => {
				    required => ["party_size", "reservation_time", "reservation_date"],
				    properties => {
					reservation_time => {
					    description => "proposed time of reservation",
					    type => "string",
					},
					reservation_date => {
					    type => "string",
					    description => "proposed date of reservation",
					},
					party_size => {
					    type => "string",
					    description => "number of guests",
					},
				    },
				    type => "object",
				},
				function => "check_availability",
				active => "true",
			    },
    },
    create_reservation => { function => \&create_reservation,
				signature => {
				    purpose => "Create a reservation",
				    argument => {
					required => ["customer_phone", "customer_name", "party_size", "reservation_time", "reservation_date"],
					properties => {
					    party_size => {
						description => "number of guests",
						type => "string",
					    },
					    customer_phone => {
						type => "string",
						description => "phone number of guest in e.164 format",
					    },
					    reservation_time => {
						type => "string",
						description => "create reservation in military time",
					    },
					    reservation_date => {
						description => "create a reservation for a date",
						type => "string",
					    },
					    customer_name => {
						type => "string",
						description => "name of guest",
					    },
					},
					type => "object",
				    },
				    function => "create_reservation",
				    active => "true",
			    },
    },
};


# Function to randomly select a slogan
sub random_slogan {
    return $slogans[rand @slogans];
}

my $data_sql = {
    restaurants => {
	create => qq( CREATE TABLE IF NOT EXISTS restaurants (restaurant_id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, location VARCHAR(255), phone_number VARCHAR(20), email_address VARCHAR(255), open_time TIME NOT NULL,close_time TIME NOT NULL,days_open VARCHAR(255)[],capacity INT NOT NULL,blackout_dates DATE[]) ),
    },
    reservations => {
	create => qq( CREATE TABLE IF NOT EXISTS reservations (reservation_id SERIAL PRIMARY KEY, restaurant_id INT REFERENCES restaurants(restaurant_id), reservation_date DATE NOT NULL, reservation_time TIME NOT NULL, reservation_key VARCHAR(8), party_size INT NOT NULL, customer_name VARCHAR(255) NOT NULL, customer_phone VARCHAR(20) NOT NULL, customer_email VARCHAR(255) ) ),
    },
    summary => {
	create => qq( CREATE TABLE IF NOT EXISTS ai_summary (id SERIAL PRIMARY KEY, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, convo_id TEXT, summary TEXT) )
    },
    post_prompt => {
	create => qq( CREATE TABLE IF NOT EXISTS ai_post_prompt (id SERIAL PRIMARY KEY, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, data JSONB ) )
    }
};

# Load environment variables
my $ENV = Env::C::getallenv();

my ( $protocol, $dbusername, $dbpassword, $host, $port, $database ) = $ENV{DATABASE_URL} =~ m{^(?<protocol>\w+):\/\/(?<username>[^:]+):(?<password>[^@]+)@(?<host>[^:]+):(?<port>\d+)\/(?<database>\w+)$};

sub scramble_last_seven {
    my ($str) = @_;
    my $initial_part = substr($str, 0, -7);
    my $to_scramble = substr($str, -7);
    my $scrambled = join '', shuffle(split //, $to_scramble);
    return $initial_part . $scrambled;
}

sub format_e164 {
    my ($phone_number) = @_;

    # Remove any non-digit characters
    $phone_number =~ s/\D//g;

    # Check if the number starts with the country code, if not prepend it
    # Assuming country code '1' for US as an example
    if ($phone_number !~ /^1/) {
	$phone_number = "1" . $phone_number;
    }

    # Format to E.164
    return "+$phone_number";
}
sub generate_random_string {
    my $length = 8;
    my @chars = ('0'..'9', 'A'..'Z', 'a'..'z');
    my $random_string;
    foreach (1..$length) {
	$random_string .= $chars[rand @chars];
    }
    return $random_string;
}

# PSGI application code
sub lookup_reservation {
    my $data      = shift;
    my $post_data = shift;
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
    my $swml      = SignalWire::ML->new;
    my $json      = JSON::PP->new->ascii->pretty->allow_nonref;
    my $res       = Plack::Response->new( 200 );

    my $customer_phone = $data->{customer_phone};

    # Remove all space
    $customer_phone =~ s/\s+//g;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

    my $response = {};

    # Fetch the upcoming reservation by phone number
    my $lookup_sql = "SELECT reservation_id, reservation_date, reservation_time, party_size, customer_name FROM reservations WHERE customer_phone = ? AND reservation_date >= CURRENT_DATE ORDER BY reservation_date, reservation_time LIMIT 1";
    my $sth_lookup = $dbh->prepare($lookup_sql);

    $sth_lookup->execute($customer_phone);

    my $row_reservation = $sth_lookup->fetchrow_hashref;

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

    if ( $response->{reservation_id} ) {
	$res->body(  $swml->swaig_response_json( { response => $response->{response}, action => [  { set_meta_data => { reservation => $response } } ] } ) );
    } else {
	$res->body(  $swml->swaig_response_json( { response => $response->{response} } ) );
    }

    return $res->finalize;
}

sub cancel_reservation {
    my $data 	  = shift;
    my $post_data = shift;
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
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

    $res->body(  $swml->swaig_response_json( { response=> $response->{response}, action => [ { back_to_back_functions => "true"} ] } )  );

    return $res->finalize;
}

sub move_reservation {
    my $data      = shift;
    my $post_data = shift;
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
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

    $res->body($swml->swaig_response_json({ response => $response->{response} }));
    return $res->finalize;
}

sub check_availability {
    my $data 		= shift;
    my $post_data       = shift;
    my $env             = shift;
    my $req             = Plack::Request->new($env);
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
}

sub create_reservation {
    my $data      = shift;
    my $post_data = shift;
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
    my $swml      = SignalWire::ML->new;
    my $json      = JSON::PP->new->ascii->pretty->allow_nonref;
    my $res       = Plack::Response->new( 200 );

    my $reservation_date = $data->{reservation_date};
    my $reservation_time = $data->{reservation_time};
    my $party_size       = $data->{party_size};
    my $customer_name    = $data->{customer_name};
    my $customer_phone   = $data->{customer_phone};

    my $restaurant_id    = 1;

    # Remove any non-digit characters from the phone number
    $customer_phone =~ s/\s+//g;


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
	    $response->{response} = "Reservation successfully created. Here is the URL to update or cancel it, include it with the text message https://$ENV{NGROK_URL}/view?rk=$reservation_key";
	} else {
	    $dbh->rollback;  # Rollback the transaction
	    $response->{response} = "Reservation failed. Time not available. Offer to check an hour before and after the requested time.";
	}

	# Closing the database connection # https://xkcd.com/327/
	$dbh->disconnect;
    } else {
	$dbh->rollback;  # Rollback the transaction
	$response->{response} = "Reservation failed. Time not available. Offer to check an hour before and after the requested time.";
    }

    # Preparing JSON response
    $res->content_type('application/json');

    $res->body(  $swml->swaig_response_json( { response=> $response->{response} } ) );

    return $res->finalize;
}

my $view_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new( $env );
    my $params  = $req->parameters;
    my $json    = JSON::PP->new->ascii->pretty->allow_nonref;
    my $method  = $req->method;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

    my $res = Plack::Response->new(200);
    $res->content_type('text/html');

    my $template = HTML::Template::Expr->new( filename => "/app/template/update.tmpl", die_on_bad_params => 0 );

    if ($params->{rk}) {
	my $sql = "SELECT * FROM reservations WHERE reservation_key = ?";

	my $sth = $dbh->prepare( $sql );

	$sth->execute( $params->{rk} ) or die "Couldn't execute statement: $DBI::errstr\n";

	my $row = $sth->fetchrow_hashref;

	if ( $row ) {
	    $template->param(
		update_step_3    => 1,
		reservation_id   => $row->{reservation_id},
		reservation_key  => $row->{reservation_key},
		customer_name    => $row->{customer_name},
		customer_phone   => $row->{customer_phone},
		customer_email   => $row->{customer_email},
		party_size       => $row->{party_size},
		slogan           => random_slogan(),
		reservation_date => $row->{reservation_date},
		reservation_time => $row->{reservation_time},
		"s$row->{party_size}"   => 'selected'
		);
	} else {
	    $template->param(
		error	      => "No reservation found.",
		update_step_1 => 1,
		slogan        => random_slogan()
		);
	}
    }

    $res->body( $template->output );
    return $res->finalize;
};

my $update_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new( $env );
    my $params  = $req->parameters;
    my $json    = JSON::PP->new->ascii->pretty->allow_nonref;
    my $method  = $req->method;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

    my $res = Plack::Response->new(200);
    $res->content_type('text/html');

    my $template = HTML::Template::Expr->new( filename => "/app/template/update.tmpl", die_on_bad_params => 0 );

    my $sw = SignalWire::RestAPI->new(
	AccountSid  => $ENV{ACCOUNT_SID},
	AuthToken   => $ENV{AUTH_TOKEN},
	Space       => $ENV{SPACE_NAME},
	API_VERSION => $ENV{API_VERSION}
	);

    if ( $method eq 'POST' ) {

	if ($params->{action} eq 'update_step_2') {
	    if ( !$params->{terms} ) {
		$template->param(
		    error          => 'You must agree to the terms and conditions to continue.',
		    slogan         => random_slogan(),
		    update_step_1  => 1,
		    customer_phone => $params->{customer_phone}
		    );
	    } else {
		my $sql = "SELECT customer_phone FROM reservations WHERE customer_phone = ?";

		my $sth = $dbh->prepare( $sql );

		my $customer_phone = format_e164( $params->{customer_phone} );

		$sth->execute( $customer_phone ) or die "Couldn't execute statement: $DBI::errstr\n";

		my $row = $sth->fetchrow_hashref;

		if ( $row ) {
		    my $response = $sw->POST( "mfa/sms",
					      to => $row->{customer_phone},
					      from => $ENV{ASSISTANT},
					      message => 'Your code is: ',
					      allow_alpha => 'true',
					      token_length => 6,
					      valid_for => 1200,
					      max_attempts => 6
			);

		    my $mfa_response = $json->decode( $response->{content} );

		    $template->param(
			update_step_2  => 1,
			mfa_id         => $mfa_response->{id},
			customer_phone => $customer_phone,
			slogan         => random_slogan()
			);
		} else {
		    $template->param(
			error	  => "No reservation found for that phone number",
			update_step_1 => 1,
			slogan        => random_slogan()
			);
		}
	    }
	} elsif ( $params->{action} eq 'update_step_3' ) {
	    my $verify = $sw->POST("mfa/$params->{mfa_id}/verify", token => $params->{mfa_token});

	    if ( $verify->{content} !~ /{\"success\":true}/ ){
		$verify->{content} ='{"success":false}';
	    }

	    my $resp = $json->decode( $verify->{content} );

	    if ( $resp->{success} ) {
		my $sql = "SELECT reservation_id, reservation_date, reservation_time, party_size, customer_name FROM reservations WHERE customer_phone = ? AND reservation_date >= CURRENT_DATE ORDER BY reservation_date, reservation_time LIMIT 1";

		my $sth = $dbh->prepare( $sql );

		my $customer_phone = $params->{customer_phone};

		$sth->execute( $customer_phone ) or die "Couldn't execute statement: $DBI::errstr\n";

		my $row = $sth->fetchrow_hashref;

		if ( $row ) {
		    $template->param(
			update_step_3    => 1,
			mfa_id           => $params->{mfa_id},
			mfa_token        => $params->{token},
			reservation_id   => $row->{reservation_id},
			reservation_key  => $row->{reservation_key},
			customer_name    => $row->{customer_name},
			customer_phone   => $customer_phone,
			party_size       => $row->{party_size},
			slogan           => random_slogan(),
			reservation_date => $row->{reservation_date},
			reservation_time => $row->{reservation_time},
			"s$row->{party_size}"   => 'selected'
			);
		} else {
		    $template->param(
			error	      => "No reservation found for that phone number",
			update_step_1 => 1,
			slogan        => random_slogan()
			);
		}
	    } else {
		$template->param(
		    error	   => "Invalid code, Try again",
		    update_step_2  => 1,
		    customer_phone => $params->{customer_phone},
		    mfa_id         => $params->{mfa_id},
		    slogan         => random_slogan()
		    );
	    }
	} elsif ( $params->{action} eq 'cancel' ) {
	    my $sql = "DELETE FROM reservations WHERE reservation_id = ? AND reservation_key = ?";

	    my $sth = $dbh->prepare( $sql );

	    my $reservation_id  = $params->{reservation_id};
	    my $reservation_key = $params->{reservation_key};

	    $sth->execute( $reservation_id, $reservation_key ) or die "Couldn't execute statement: $DBI::errstr\n";

	    $template->param(
		message       => "Your reservation has been cancelled.",
		thank_you     => "Thank you for considering Bobby's Table!",
		slogan        => random_slogan(),
		);
	} elsif ( $params->{action} eq 'update' ) {
	    my $sql = "UPDATE reservations SET customer_name = ?, customer_phone = ?, customer_email = ?, party_size = ?, reservation_date = ?, reservation_time = ? WHERE reservation_id = ?";

	    my $sth = $dbh->prepare( $sql );

	    my $customer_name    = $params->{customer_name};
	    my $customer_phone   = $params->{customer_phone};
	    my $customer_email   = $params->{customer_email};
	    my $party_size       = $params->{party_size};
	    my $reservation_date = $params->{reservation_date};
	    my $reservation_time = $params->{reservation_time};
	    my $reservation_id   = $params->{reservation_id};

	    $sth->execute( $customer_name, $customer_phone, $customer_email, $party_size, $reservation_date, $reservation_time, $reservation_id ) or die "Couldn't execute statement: $DBI::errstr\n";

	    $template->param(
		message       => "Reservation updated!",
		thank_you     => "Thank you!",
		slogan        => random_slogan()
		);

	} else {
	    $template->param(
		error	      => "Invalid action, Try again",
		update_step_1 => 1,
		slogan        => random_slogan()
		);
	}
    } else {
	$template->param(
	    update_step_1 => 1,
	    slogan        => random_slogan()
	    );
    }
    $res->body( $template->output );
    return $res->finalize;
};

my $reservation_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new( $env );
    my $params  = $req->parameters;
    my $json    = JSON::PP->new->ascii->pretty->allow_nonref;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

    my $sql = "SELECT * FROM reservations WHERE reservation_date >= ? ORDER BY reservation_date, reservation_time";

    my $sth = $dbh->prepare( $sql );

    my $today = DateTime->now->truncate( to => 'day' )->subtract( days => 1 );

    $sth->execute( $today->ymd ) or die "Couldn't execute statement: $DBI::errstr\n";

    my @table_contents;

    while ( my $row = $sth->fetchrow_hashref ) {
	my ($hours, $minutes, $seconds) = split(':', $row->{reservation_time});
	my $seconds_since_midnight = $hours * 3600 + $minutes * 60 + $seconds;
	$row->{reservation_time} = POSIX::strftime("%I:%M %p", 0, $minutes, $hours, 1, 0, 0);

	my $t = Time::Piece->strptime( $row->{reservation_date}, "%Y-%m-%d" );

	# Get the day of the month
	my $day = $t->mday;

	# Determine the suffix
	my $suffix = do {
	    ($day =~ /1\d$/) ? 'th' :
		($day % 10 == 1) ? 'st' :
		($day % 10 == 2) ? 'nd' :
		($day % 10 == 3) ? 'rd' : 'th';
	};

	# Format the date with the correct suffix
	$row->{reservation_date} = $t->strftime("%A, %B ") . $day . $suffix;

	$row->{customer_phone} = scramble_last_seven( $row->{customer_phone} );
	push @table_contents, $row;
    }

    $sth->finish;

    $dbh->disconnect;

    my $template = HTML::Template::Expr->new( filename => "/app/template/reservations.tmpl", die_on_bad_params => 0 );

    $template->param(
	date            => $today->ymd,
	table_contents  => \@table_contents,
	slogan          => random_slogan()

	);

    my $res = Plack::Response->new( 200 );

    $res->content_type( 'text/html' );

    $res->body( $template->output );

    return $res->finalize;
};

my $debug_app = sub {
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
    my $swml      = SignalWire::ML->new;
    my $post_data = decode_json( $req->raw_body );
    my $agent     = $req->param( 'agent_id' );
    my $res       = Plack::Response->new( 200 );

    $res->content_type( 'application/json' );

    $res->body( $swml->swaig_response_json( { response => "data received" } ) );

    print STDERR "Data received: " . Dumper( $post_data ) if $ENV{DEBUG};

    return $res->finalize;
};

my $assets_app = Plack::App::Directory->new( root => "/app/assets" )->to_app;

my $swml_app = sub {
    my $env         = shift;
    my $req         = Plack::Request->new( $env );
    my $post_data   = decode_json( $req->raw_body ? $req->raw_body : '{}' );
    my $swml        = SignalWire::ML->new;
    my $ai          = 1;
    my $prompt      = read_file( "/app/prompt.md" );
    my $post_prompt = read_file( "/app/post_prompt.md" );
    my $roomieserve = $ENV{BOBBYSTABLE};

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die $DBI::errstr;

    $swml->add_application( "main", "answer" );
    $swml->add_application( "main", "record_call", { format => 'wav', stereo => 'true' });

    $swml->set_aiprompt({
	temperature => $ENV{TEMPERATURE},
	top_p       => $ENV{TOP_P},
	text        => $prompt });

    $swml->add_aiswaigdefaults({ web_hook_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/swaig" });

    $swml->set_aipost_prompt( {
	temperature => $ENV{TEMPERATURE},
	top_p       => $ENV{TOP_P},
	text        => $post_prompt });

    $swml->set_aipost_prompt_url( { post_prompt_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/post" } );

    $swml->add_ailanguage({
	code    => 'en-US',
	name    => 'English',
	voice   => 'rachel',
	engine  => 'elevenlabs',
	fillers => [ "one moment" ] });

    $swml->add_aiparams( { debug_webhook_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/debughook" } );

    $swml->add_aiinclude( {
	functions => [ 'move_reservation', 'check_availability', 'create_reservation', 'cancel_reservation', 'lookup_reservation' ],
	user => $ENV{USERNAME},
	pass => $ENV{PASSWORD},
	url  => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/swaig" } );

    my $msg = SignalWire::ML->new;

    $msg->add_application( "main", "send_sms" => { to_number   => '${args.to}',
						   from_number => $ENV{ASSISTANT},
						   body        => '${args.message}, Reply STOP to stop.' } );

    my $output = $msg->swaig_response( {
	response => "Message sent.",
	action   => [ { SWML => $msg->render } ] } );

    $swml->add_aiswaigfunction( {
	function => 'send_message',
	purpose  => "use to send text messages to a user",
	argument => {
	    type => "object",
	    properties => {
		message => {
		    type        => "string",
		    description => "the message to send to the user" },
		to => {
		    type        => "string",
		    description => "The users number in e.164 format" }
	    },
	    required => [ "message", "to" ]
	},
	data_map => {
	    expressions => [{
		string  => '${args.message}',
		pattern => '.*',
		output  => $output
			    }]}} );

    $swml->add_aiapplication( "main" );

    my $res = Plack::Response->new(200);

    $res->content_type('application/json');

    $res->body($swml->render_json);

    $dbh->disconnect;

    return $res->finalize;
};

my $convo_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new( $env );
    my $params  = $req->parameters;
    my $id      = $params->{id};
    my $json    = JSON::PP->new->ascii->pretty->allow_nonref;
    my $session = $env->{'psgix.session'};

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 }) or die $DBI::errstr;

    if ( $id ) {
	my $sql = "SELECT * FROM ai_post_prompt WHERE id = ?";

	my $sth = $dbh->prepare( $sql );

	$sth->execute( $id ) or die $DBI::errstr;

	my $row = $sth->fetchrow_hashref;

	my $sql_next = "SELECT id FROM ai_post_prompt WHERE id > ? ORDER BY id ASC LIMIT 1";

	my $sql_prev = "SELECT id FROM ai_post_prompt WHERE id < ? ORDER BY id DESC LIMIT 1";

	my $sth_next = $dbh->prepare( $sql_next );

	$sth_next->execute( $id );

	my ( $next_id ) = $sth_next->fetchrow_array;

	$sth_next->finish;

	my $sth_prev = $dbh->prepare( $sql_prev );

	$sth_prev->execute( $id );

	my ( $prev_id ) = $sth_prev->fetchrow_array;

	$sth_prev->finish;

	if ( $row ) {
	    my $p = $json->decode( $row->{data} );

	    $sth->finish;

	    $dbh->disconnect;

	    foreach my $log ( @{ $p->{'call_log'} } ) {
		$log->{content} =~ s/\r\n/<br>/g;
		$log->{content} =~ s/\n/<br>/g;
	    }

	    my $template = HTML::Template::Expr->new( filename => "/app/template/conversation.tmpl", die_on_bad_params => 0 );
	    my $start =  ($p->{'ai_end_date'}   / 1000) - 5000;
	    my $end   =  ($p->{'ai_start_date'} / 1000) + 5000;

	    $template->param(
		nonce               => $env->{'plack.nonce'},
		next_id		    => $next_id ? "/convo?id=$next_id" : "/convo",
		prev_id		    => $prev_id ? "/convo?id=$prev_id" : "/convo",
		next_text	    => $next_id ? "Next >"     : "",
		prev_text	    => $prev_id ? "< Previous" : "",
		call_id             => $p->{'call_id'},
		call_start_date     => $p->{'call_start_date'},
		call_log            => $p->{'call_log'},
		swaig_log	    => $p->{'swaig_log'},
		caller_id_name      => $p->{'caller_id_name'},
		caller_id_number    => $p->{'caller_id_number'},
		total_output_tokens => $p->{'total_output_tokens'},
		total_input_tokens  => $p->{'total_input_tokens'},
		raw_json            => $json->encode( $p ),
		record_call_url     => $p->{SWMLVars}->{record_call_url} );

	    my $res = Plack::Response->new( 200 );

	    $res->content_type( 'text/html' );

	    $res->body( $template->output );

	    return $res->finalize;
	} else {
	    my $res = Plack::Response->new( 200 );

	    $res->redirect( "/convo" );
	    return $res->finalize;
	}
    } else {
	my $page_size    = 20;
	my $current_page = $params->{page} || 1;
	my $offset       = ( $current_page - 1 ) * $page_size;

	my $sql = "SELECT * FROM ai_post_prompt ORDER BY created DESC LIMIT ? OFFSET ?";

	my $sth = $dbh->prepare( $sql );

	$sth->execute( $page_size, $offset ) or die $DBI::errstr;

	my @table_contents;

	while ( my $row = $sth->fetchrow_hashref ) {
	    my $p = $json->decode( $row->{data} );

	    $row->{caller_id_name}       = $p->{caller_id_name};
	    $row->{caller_id_number}     = $p->{caller_id_number};
	    $row->{call_id}              = $p->{call_id};
	    $row->{summary}              = $p->{post_prompt_data}->{substituted};
	    push @table_contents, $row;
	}

	$sth->finish;

	my $total_rows_sql = "SELECT COUNT(*) FROM ai_post_prompt";

	$sth = $dbh->prepare( $total_rows_sql );

	$sth->execute();

	my ( $total_rows ) = $sth->fetchrow_array();

	my $total_pages = int( ( $total_rows + $page_size - 1 ) / $page_size );

	$current_page = 1 if $current_page < 1;
	$current_page = $total_pages if $current_page > $total_pages;

	my $next_url = "";
	my $prev_url = "";

	if ( $current_page > 1 ) {
	    my $prev_page = $current_page - 1;
	    $prev_url = "/convo?&page=$prev_page";
	}

	if ( $current_page < $total_pages ) {
	    my $next_page = $current_page + 1;
	    $next_url = "/convo?page=$next_page";
	}

	$sth->finish;

	$dbh->disconnect;

	my $template = HTML::Template::Expr->new( filename => "/app/template/conversations.tmpl", die_on_bad_params => 0 );

	$template->param(
	    nonce                => $env->{'plack.nonce'},
	    table_contents       => \@table_contents,
	    next_url             => $next_url,
	    prev_url             => $prev_url
	    );

	my $res = Plack::Response->new( 200 );

	$res->content_type( 'text/html' );

	$res->body( $template->output );

	return $res->finalize;
    }
};

my $post_app = sub {
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
    my $post_data = decode_json( $req->raw_body ? $req->raw_body : '{}' );
    my $swml      = SignalWire::ML->new;
    my $raw       = $post_data->{post_prompt_data}->{raw};
    my $data      = $post_data->{post_prompt_data}->{parsed}->[0];
    my $recording = $post_data->{SWMLVars}->{record_call_url};
    my $from      = $post_data->{SWMLVars}->{from};
    my $json      = JSON::PP->new->ascii->allow_nonref;
    my $action    = $post_data->{action};
    my $convo_id  = $post_data->{conversation_id};
    my $convo_sum = $post_data->{conversation_summary};

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die $DBI::errstr;

    if ( $action eq "fetch_conversation" && defined $convo_id ) {
	my @summary;

	my $fetch_sql = "SELECT created,summary FROM ai_summary WHERE convo_id = ? AND created >= CURRENT_TIMESTAMP - INTERVAL '4 hours'";

	my $fsth = $dbh->prepare( $fetch_sql );

	$fsth->execute( $convo_id ) or die $DBI::errstr;

	while ( my $row = $fsth->fetchrow_hashref ) {
	    push @summary, "$row->{created} - $row->{summary}";
	}

	my $res = Plack::Response->new( 200 );

	$res->content_type( 'application/json' );

	if ( @summary == 0 ) {
	    $res->body( $swml->swaig_response_json( { response => "co conversation found" } ) );
	} else {
	    $res->body( $swml->swaig_response_json( { response => "conversation found" , conversation_summary => join("\n", @summary) } ) );
	}

	$dbh->disconnect;

	return $res->finalize;
    } else {
	if ( !$ENV{SAVE_BLANK_CONVERSATIONS} && $post_data->{post_prompt_data}->{raw} =~ m/no\sconversation\stook\splace/g ) {
	    my $res = Plack::Response->new( 200 );

	    $res->content_type( 'application/json' );

	    $res->body( $swml->swaig_response_json( { response => "data ignored" } ) );

	    $dbh->disconnect;

	    return $res->finalize;
	}

	if ( defined $convo_id && defined $convo_sum ) {
	    my $convo_sql = "INSERT INTO ai_summary (created, convo_id, summary) VALUES (CURRENT_TIMESTAMP, ?, ?)";

	    my $csth = $dbh->prepare( $convo_sql );

	    $csth->execute( $convo_id, $convo_sum ) or die $DBI::errstr;

	}

	my $insert_sql = "INSERT INTO ai_post_prompt (created, data ) VALUES (CURRENT_TIMESTAMP, ?)";

	my $json_data = $req->raw_body;

	my $sth = $dbh->prepare( $insert_sql );

	$sth->execute( $json_data ) or die $DBI::errstr;

	my $last_insert_id = $dbh->last_insert_id( undef, undef, 'ai_post_prompt', 'id' );

	$dbh->disconnect;

	my $res = Plack::Response->new( 200 );

	$res->content_type( 'application/json' );

	$res->body( $swml->swaig_response_json( { response => 'data received' } ) );

	return $res->finalize;
    }
};

my $swaig_app = sub {
    my $env       = shift;
    my $req       = Plack::Request->new($env);
    my $body      = $req->raw_body;

    my $post_data = decode_json( $body eq '' ? '{}' : $body );
    my $swml      = SignalWire::ML->new();
    my $data      = $post_data->{argument}->{parsed}->[0];
    print STDERR Dumper($post_data);
    
    if (defined $post_data->{action} && $post_data->{action} eq 'get_signature') {
	my @functions;
	my @funcs;
	my $res = Plack::Response->new(200);

	$res->content_type('application/json');

	if ( scalar (@{ $post_data->{functions}}) ) {
	    @funcs =  @{ $post_data->{functions}};
	} else {
	    @funcs = keys %{$function};
	}

	print STDERR Dumper(\@funcs) if $ENV{DEBUG};

	foreach my $func ( @funcs ) {
	    $function->{$func}->{signature}->{web_hook_auth_user}     = $ENV{USERNAME};
	    $function->{$func}->{signature}->{web_hook_auth_password} = $ENV{PASSWORD};
	    $function->{$func}->{signature}->{web_hook_url} = "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}$env->{REQUEST_URI}";
	    push @functions, $function->{$func}->{signature};
	}

	$res->body( encode_json( \@functions ) );

	return $res->finalize;
    } elsif (defined $post_data->{function} && exists $function->{$post_data->{function}}->{function}) {
	print STDERR "Calling function $post_data->{function}\n" if $ENV{DEBUG};
	print STDERR "Data: " . Dumper($data) if $ENV{DEBUG};
	print STDERR "Post Data: " . Dumper($post_data) if $ENV{DEBUG};
	$function->{$post_data->{function}}->{function}->($data, $post_data, $env);
    } else {
	my $res = Plack::Response->new( 500 );

	$res->content_type('application/json');

	$res->body($swml->swaig_response_json( { response => "I'm sorry, I don't know how to do that." } ));

	return $res->finalize;
    }
};

sub authenticator {
    my ( $user, $pass, $env ) = @_;
    my $req    = Plack::Request->new( $env );

    if ( $ENV{USERNAME} eq $user && $ENV{PASSWORD} eq $pass ) {
	return 1;
    }

    return 0;
}

my $server = builder {

    mount "/post" => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$post_app;
    };

    mount "/convo" => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$convo_app;
    };

    mount "/swaig" => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$swaig_app;
    };

    mount "/swml" => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$swml_app;
    };

    mount '/'       => $reservation_app;
    mount '/update' => $update_app;
    mount '/view'   => $view_app;
    mount "/assets"    => $assets_app;
};

my $dbh = DBI->connect(
    "dbi:Pg:dbname=$database;host=$host;port=$port",
    $dbusername,
    $dbpassword,
    { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

foreach my $table ( keys %{$data_sql} ) {
    print STDERR "Checking for table $table\n" if $ENV{DEBUG};
    my $sql = $data_sql->{$table}->{create};
    print STDERR "Creating table $sql\n" if $ENV{DEBUG};
    $dbh->do( $sql ) or die "Couldn't execute statement: $DBI::errstr\n";
}

$dbh->disconnect;

# Running the PSGI application
my $runner = Plack::Runner->new;

$runner->run( $server );

1;
