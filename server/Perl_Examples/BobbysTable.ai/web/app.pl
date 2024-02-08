#!/usr/bin/env perl
# app.pl - SignalWire AI Agent Bobby's Table Demo Application
use lib '.', '/app';
use strict;
use warnings;

# SignalWire modules
use SignalWire::RestAPI;

# PSGI/Plack
use Plack::Builder;
use Plack::Runner;
use Plack::Request;
use Plack::Response;
use Plack::App::Directory;
use Twiggy::Server;

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
    reminders => {
	create => qq( CREATE TABLE IF NOT EXISTS reminders (reminder_id SERIAL PRIMARY KEY, reservation_id INT REFERENCES reservations(reservation_id), reminder_status VARCHAR(20) NOT NULL, reminder_datetime TIMESTAMP NOT NULL) ),
    }
};

# Load environment variables
my $ENV = Env::C::getallenv();

my ( $protocol, $dbusername, $dbpassword, $host, $port, $database ) = $ENV{DATABASE_URL} =~ m{^(?<protocol>\w+):\/\/(?<username>[^:]+):(?<password>[^@]+)@(?<host>[^:]+):(?<port>\d+)\/(?<database>\w+)$};

# Dispatch table for PSGI
my %dispatch = (
    'GET' => {
	'/view'        => \&view,
	'/'          => \&reservations,
	'/update'    => \&update,
    },
    'POST' => {
	'/'          => \&reservations,
	'/update'    => \&update,
    }
    );

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

# PSGI application code
sub view {
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
}

sub update {
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
}

sub reservations {
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
}

# This is the Asset entry point for the application
my $assets_app = Plack::App::Directory->new( root => "/app/assets" )->to_app;

# This is the HTTP entry point for the application
my $web_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new( $env );
    my $agent   = $req->param( 'agent_id' );
    my $path    = $req->path_info;
    my $method  = $req->method;

    if ( exists $dispatch{$method} && exists $dispatch{$method}{$path} ) {
	return $dispatch{$method}{$path}->( $env );
    } else {
	my $response = Plack::Response->new( 404 );
	$response->content_type( 'text/html' );
	$response->body( "Not Found" );
    }
};

my $server = builder {
    mount "/assets"    => $assets_app;

    mount '/' => $web_app;
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

$runner->parse_options( '-s', 'Twiggy' );

$runner->run( $server );

1;
