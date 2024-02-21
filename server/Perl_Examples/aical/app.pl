#!/bin/env perl
# app.pl - SignalWire AI Agent Calendar Demo Application
use lib '.', '/app';
use strict;
use warnings;

# SignalWire modules
use SignalWire::ML;
use SignalWire::RestAPI;

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
use DateTime::Format::ISO8601;
use Env::C;
use DBI;
use UUID 'uuid';
use URI::Escape qw(uri_escape);

my $ENV = Env::C::getallenv();

my ( $protocol, $dbusername, $dbpassword, $host, $port, $database ) = $ENV{DATABASE_URL} =~ m{^(?<protocol>\w+):\/\/(?<username>[^:]+):(?<password>[^@]+)@(?<host>[^:]+):(?<port>\d+)\/(?<database>\w+)$};

# SignalWire AI Agent function definitions
my $function = {
    freebusy => { function  => \&freebusy,
		  signature => {
		      function => 'freebusy',
		      purpose  => "Check if a time is available on a calendar",
		      argument => {
			  type => "object",
			  properties => {
			      start_time => {
				  type => "string",
				  description => "start time in ISO8601 format with timezone" },
			      length   => {
				  type => "integer",
				  description => "length of time in minutes" },
			      timezone => {
				  type => "string",
				  description => "the timezone" }
			  }
		      }
		  }
    },
    events => { function  => \&events,
		signature => {
		    function => 'events',
		    purpose  => "Schedule an event on a calendar",
		    argument => {
			type => "object",
			properties => {
			    start_time => {
				type => "string",
				description => "start time in ISO8601 format with timezone" },
			    length   => {
				type => "integer",
				description => "length of time in minutes" },
			    email => {
				type => "string",
				description => "the email address of the user to schedule the event with" },
			    summary => {
				type => "string",
				description => "the summary of the event" },
			    description => {
				type => "string",
				description => "the description of the event" },
			}
		    }
		}
    }
};

sub create_event {
    my ($access_token, $calendar_id, $start_time, $length, $timezone, $email, $summary, $description, $cal_email, $location, $notes) = @_;

    print STDERR "Scheduling meeting\n";
    print STDERR "Start time: $start_time\n";
    print STDERR "Length: $length\n";
    print STDERR "Timezone: $timezone\n";
    print STDERR "Email: $email\n";
    print STDERR "Summary: $summary\n";
    print STDERR "Description: $description\n";
    print STDERR "Calendar email: $cal_email\n";
    print STDERR "Location: $location\n";

    my $dt = DateTime::Format::ISO8601->parse_datetime($start_time);

    $dt->add(minutes => $length );

    my $end_time = $dt->strftime('%Y-%m-%dT%H:%M:%S%z');

    my $url = "https://www.googleapis.com/calendar/v3/calendars/$calendar_id/events?sendUpdates=all";

    my $json_data = {
	"summary" => $summary,
	"description" => $description . "\n\n" . $notes,
	    location => $location,
	"start" => {
	    "dateTime" => $start_time,
	    "timeZone" => $timezone
	},
	"end" => {
	    "dateTime" => $end_time,
	    "timeZone" => $timezone
	},
	"attendees" => [
	    {
		"email" => $email,
		"self" => "false"

	    },
	    {
		"email" => $cal_email,
		"responseStatus" => "accepted",
		"optional" => "false",
		"self" => "true"
	    }
	]
    };

    my $ua = LWP::UserAgent->new;

    my $request = HTTP::Request->new('POST', $url);

    $request->header('Authorization' => "Bearer $access_token");

    $request->header('Content-Type' => 'application/json');

    $request->content(encode_json($json_data));

    my $response = $ua->request($request);

    if ($response->is_success) {
	my $result = decode_json($response->content);

	return 1;
    } else {
	print STDERR "Error scheduling meeting: " . $response->status_line . "\n";

	return 0;
    }
}

sub is_time_available {
    my ($access_token, $calendar_id, $start_time, $length, $timezone) = @_;

    print STDERR "Checking if time is available\n";
    print STDERR "Start time: $start_time\n";
    print STDERR "Length: $length\n";
    print STDERR "Timezone: $timezone\n";

    my $dt = DateTime::Format::ISO8601->parse_datetime($start_time);

    $dt->add(minutes => $length );

    my $end_time = $dt->strftime('%Y-%m-%dT%H:%M:%S%z');

    my $url = "https://www.googleapis.com/calendar/v3/freeBusy";

    my $json_data = {
	"timeMin"  => $start_time,
	"timeMax"  => $end_time,
	"timeZone" => $timezone,
	"items"    => [ { "id" => $calendar_id } ]
    };

    my $ua = LWP::UserAgent->new;

    my $request = HTTP::Request->new('POST', $url);

    $request->header('Authorization' => "Bearer $access_token");

    $request->header('Content-Type' => 'application/json');

    $request->content(encode_json($json_data));

    my $response = $ua->request($request);

    if ($response->is_success) {
	my $result = decode_json($response->content);

	my $busy = $result->{calendars}->{$calendar_id}->{busy};
	print STDERR "Busy: " . scalar(@$busy) . "\n";

	if (scalar(@$busy) > 0) {
	    print STDERR "Time is NOT available\n";

	    return 0;
	} else {
	    print STDERR "Time is available\n";

	    return 1;
	}
    } else {
	print STDERR "Error checking if time is available: " . $response->status_line . "\n";

	return -1;
    }
}

sub events {
    my $data      = shift;
    my $post_data = shift;
    my $env       = shift;
    my $swml      = SignalWire::ML->new();

    print STDERR Dumper($post_data) if $ENV{DEBUG};

    my $tokens = get_access_token( $env->{REMOTE_USER} );

    my $res = Plack::Response->new(200);

    my $user = get_user_credentials($env->{REMOTE_USER});

    my $calendar  = get_calendar_details($env->{REMOTE_USER});
    
    $res->content_type( 'application/json' );

    my $events = create_event( $tokens->{access_token}, $calendar->{calendar_id}, $data->{start_time}, $data->{length}, $calendar->{timezone}, $data->{email}, $data->{summary}, $data->{description}, $user->{email}, $calendar->{default_location}, $calendar->{notes} );

    if ($events == 1) {
	$res->body($swml->swaig_response_json( { response => "Your meeting has been scheduled." } ) );
    } else {
	$res->body($swml->swaig_response_json( { response => "There was an error scheduling your meeting." } ) );
    }

    return $res->finalize;
}

sub freebusy {
    my $data      = shift;
    my $post_data = shift;
    my $env       = shift;
    my $swml      = SignalWire::ML->new();

    print STDERR Dumper($post_data) if $ENV{DEBUG};

    my $tokens = get_access_token($env->{REMOTE_USER});

    my $available = is_time_available($tokens->{access_token}, 'primary', $data->{start_time}, $data->{length}, $data->{timezone});

    my $res = Plack::Response->new(200);

    $res->content_type( 'application/json' );

    if ($available == 1) {
	$res->body($swml->swaig_response_json( { response => "That time is available." } ) );
    } elsif ($available == 0) {
	$res->body($swml->swaig_response_json( { response => "That time is NOT available." } ) );
    } elsif ($available == -1) {
	$res->body($swml->swaig_response_json( { response => "There was an error checking the calendar." } ) );
    }

    return $res->finalize;
}

# OAUTH2 connection parameters
my $client_id     = $ENV{CLIENT_ID};
my $client_secret = $ENV{CLIENT_SECRET};

# Google OAuth 2.0 endpoints
my $redirect_uri = 'https://aical.signalwire.me/auth/callback';
my $auth_url = 'https://accounts.google.com/o/oauth2/v2/auth';
my $token_url = 'https://www.googleapis.com/oauth2/v4/token';
my $scope = uri_escape('https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email');

sub get_authorization_url {
    return "$auth_url?response_type=code&client_id=$client_id&redirect_uri=$redirect_uri&scope=$scope&access_type=offline&prompt=consent";
}

sub get_tokens_from_code {
    my ($code) = @_;

    my $ua = LWP::UserAgent->new;

    my $response = $ua->post($token_url, [
				 code          => $code,
				 client_id     => $client_id,
				 client_secret => $client_secret,
				 redirect_uri  => $redirect_uri,
				 grant_type    => 'authorization_code'
			     ]);

    if (!$response->is_success) {
	print STDERR "Error getting tokens: " . $response->status_line . "\n";
	print STDERR "Response content: " . $response->decoded_content . "\n";

	return undef;
    } else {
	print STDERR "Got tokens successfully\n";

	return decode_json($response->decoded_content);
    }
}

sub get_access_token {
    my $username = shift;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

    my $select_refresh_token_stmt = "SELECT refresh_token FROM google_calendar_credentials WHERE user_id=(SELECT id FROM users WHERE username=?)";

    my $sth_select = $dbh->prepare($select_refresh_token_stmt);

    $sth_select->execute($username) or die "Couldn't execute statement: $DBI::errstr\n";

    my $refresh_token = $sth_select->fetchrow_array;

    $sth_select->finish;

    if (!$refresh_token) {
	print STDERR "Refresh token not found for username: $username\n";

	return undef;
    }

    my $ua = LWP::UserAgent->new;

    my $response = $ua->post($token_url, [
				 refresh_token => $refresh_token,
				 client_id     => $client_id,
				 client_secret => $client_secret,
				 grant_type    => 'refresh_token'
			     ]);

    if (!$response->is_success) {
	print STDERR "Error refreshing token: " . $response->status_line . "\n";
	print STDERR "Response content: " . $response->decoded_content . "\n";

	$dbh->disconnect;

	return undef;
    } else {
	my $token_data = decode_json($response->decoded_content);

	my $expires_at = time() + $token_data->{expires_in};

	my $update_stmt = "UPDATE google_calendar_credentials SET access_token=?, expires_in=? WHERE user_id=(SELECT id FROM users WHERE username=?)";

	my $sth_update = $dbh->prepare($update_stmt);

	$sth_update->execute($token_data->{access_token}, $expires_at, $username);

	$sth_update->finish;
	$dbh->disconnect;

	print STDERR "Refreshed token successfully\n";
	return $token_data;
    }
}

sub get_calendar_details {
    my $username = shift;
    
    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";
    
    my $select_stmt = "SELECT calendar_id, default_location, timezone, notes FROM google_calendar_credentials WHERE user_id=(SELECT id FROM users WHERE username=?)";
    
    my $sth_select = $dbh->prepare($select_stmt);
    
    $sth_select->execute($username) or die "Couldn't execute statement: $DBI::errstr\n";
    
    my $calendar_details = $sth_select->fetchrow_hashref;
    
    $sth_select->finish;

    $dbh->disconnect;
    
    if (!$calendar_details) {
	print STDERR "Calendar details not found for username: $username\n";

	return undef;
    }

    return $calendar_details;
}
    
sub refresh_access_token {
    my ($refresh_token) = @_;

    my $ua = LWP::UserAgent->new;

    my $response = $ua->post($token_url, [
				 refresh_token => $refresh_token,
				 client_id     => $client_id,
				 client_secret => $client_secret,
				 grant_type    => 'refresh_token'
			     ]);

    die "Error refreshing token: " . $response->status_line unless $response->is_success;

    print STDERR "Refreshed token successfully\n";

    return decode_json($response->decoded_content);
}

sub upsert_token_data {
    my ($token_data) = @_;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

    my $sql = 'INSERT INTO google_calendar_credentials (user_id, scope, refresh_token, access_token, expires_in, token_type, calendar_id) VALUES (?, ?, ?, ?, ?, ?,?) ON CONFLICT (user_id) DO UPDATE SET scope = EXCLUDED.scope, refresh_token = EXCLUDED.refresh_token, access_token = EXCLUDED.access_token, expires_in = EXCLUDED.expires_in, token_type = EXCLUDED.token_type';

    my $sth = $dbh->prepare($sql);

    $sth->execute($token_data->{user_id}, $token_data->{scope}, $token_data->{refresh_token}, $token_data->{access_token}, $token_data->{expires_in}, $token_data->{token_type}, 'primary');

    $sth->finish;
    $dbh->disconnect;

    print STDERR "Token data upserted successfully for user_id: $token_data->{user_id}\n";
}

sub upsert_user {
    my ($user) = @_;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

    $user->{username} = generate_random_string(16);
    $user->{password} = generate_random_string(16);

    my $sql = 'INSERT INTO users (google_id, username, password, hd, verified_email, email, picture) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (google_id) DO UPDATE SET username = EXCLUDED.username, password = EXCLUDED.password, hd = EXCLUDED.hd, verified_email = EXCLUDED.verified_email, email = EXCLUDED.email, picture = EXCLUDED.picture RETURNING id';

    my $sth = $dbh->prepare($sql);

    $sth->execute($user->{id}, $user->{username}, $user->{password},  $user->{hd}, $user->{verified_email}, $user->{email}, $user->{picture});

    my ($user_id) = $sth->fetchrow_array();

    $sth->finish;
    $dbh->disconnect;

    print STDERR "User upserted successfully\n";

    return $user_id;
}

sub get_user_credentials {
    my ($username) = @_;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

    my $sql = 'SELECT * FROM users WHERE username = ?';

    my $sth = $dbh->prepare($sql);

    $sth->execute($username) or die "Couldn't execute statement: $DBI::errstr\n";

    my $row = $sth->fetchrow_hashref();

    $sth->finish;

    $dbh->disconnect;

    return $row;
}

sub get_username {
    my ($user_id) = @_;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

    my $sql = 'SELECT username FROM users WHERE id = ?';

    my $sth = $dbh->prepare($sql);

    $sth->execute($user_id) or die "Couldn't execute statement: $DBI::errstr\n";

    my $row = $sth->fetchrow_hashref();

    $sth->finish;

    $dbh->disconnect;

    return $row;
}

sub generate_random_string {
    my $length = shift || 16;

    my @chars = ('0'..'9', 'A'..'Z', 'a'..'z');

    my $random_string;

    foreach (1..$length) {
	$random_string .= $chars[rand @chars];
    }

    return $random_string;
}

sub authenticator {
    my ( $ausername, $apassword, $env ) = @_;

    my $req    = Plack::Request->new( $env );

    my $method = $req->method;

    my $user = get_user_credentials($ausername);

    return $ausername eq $user->{username} && $apassword eq $user->{password};
}

my $settings_app = sub {
    my $env    = shift;
    my $req    = Plack::Request->new($env);
    my $res    = Plack::Response->new(200);
    my $params = $req->parameters;

    my $dbh = DBI->connect(
	"dbi:Pg:dbname=$database;host=$host;port=$port",
	$dbusername,
	$dbpassword,
	{ AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

    $res->content_type('text/html');

    my $user = get_user_credentials($env->{REMOTE_USER});
    
    my $template = HTML::Template->new(filename => '/app/template/settings.tmpl', die_on_bad_params => 0);

    if ($req->method eq 'POST') {
	my $sql = 'UPDATE google_calendar_credentials SET calendar_id = ?, default_location = ?, timezone = ?, notes = ? WHERE user_id = ?';

	my $sth = $dbh->prepare($sql);

	$sth->execute($params->{calendar_id}, $params->{default_location}, $params->{timezone}, $params->{notes}, $user->{id}) or die $DBI::errstr;

	$sth->finish;
	$dbh->disconnect;

	$res->redirect('/settings');

	return $res->finalize;
    }
    my $sql = 'SELECT calendar_id, default_location, timezone, notes FROM google_calendar_credentials WHERE user_id = ?';

    my $sth = $dbh->prepare($sql);

    $sth->execute($user->{id}) or die $DBI::errstr;

    my $row = $sth->fetchrow_hashref();

    $sth->finish;

    $dbh->disconnect;

    my $tokens = get_access_token( $env->{REMOTE_USER} );

    my @calendars;
    
    if ( $tokens ) {
	my $ua = LWP::UserAgent->new;

	my $response = $ua->get('https://www.googleapis.com/calendar/v3/users/me/calendarList?minAccessRole=owner', Authorization => "Bearer $tokens->{access_token}");

	if ($response->is_success) {
	    my $json = JSON->new->decode($response->decoded_content);

	    foreach my $calendar (@{$json->{items}}) {
		my $cal;

		$cal->{calendar_id} = $calendar->{id};
		$cal->{timezone}    = $calendar->{timeZone};

		if ( $row->{calendar_id} eq $calendar->{id} || $user->{email} eq $calendar->{id} ) {
		    $cal->{selected} = 'selected';
		}

		push @calendars, $cal;
	    }
	}

    }
	
    my $fh = FileHandle->new("/app/data/timezones.txt", "r");

    my @src_timezones = <$fh>;

    $fh->close;

    my @timezones;
    
    foreach my $timezone (@src_timezones) {
	my $tz;

	chomp($timezone);

	if ($row->{timezone} eq $timezone) {
	    $tz->{selected} = 'selected';
	}

	$tz->{name} = $timezone;

	push @timezones, $tz;
    }

    $template->param( calendars => \@calendars );

    $template->param( timezones => \@timezones );

    $template->param( url => "https://$user->{username}:$user->{password}\@$env->{HTTP_HOST}/swaig" );
    
    $template->param( calendar_id => $row->{calendar_id}, default_location => $row->{default_location}, timezone => $row->{timezone}, notes => $row->{notes}, picture => $user->{picture}, username => $user->{username} );

    $res->body($template->output());

    return $res->finalize;
};

my $swaig_app = sub {
    my $env       = shift;
    my $req       = Plack::Request->new($env);
    my $post_data = decode_json( $req->raw_body );
    my $swml      = SignalWire::ML->new();
    my $data      = $post_data->{argument}->{parsed}->[0];

    print STDERR Dumper($data) if $ENV{DEBUG};

    if (defined $post_data->{action} && $post_data->{action} eq 'get_signature') {
	my @functions;
	my @funcs;
	my $res = Plack::Response->new(200);

	$res->content_type('application/json');

	print STDERR Dumper($post_data) if $ENV{DEBUG};

	if ( scalar (@{ $post_data->{functions}}) ) {
	    @funcs =  @{ $post_data->{functions}};
	} else {
	    @funcs = keys %{$function};
	}

	print STDERR Dumper(\@funcs) if $ENV{DEBUG};

	my $user = get_user_credentials($env->{REMOTE_USER});

	foreach my $func ( @funcs ) {
	    $function->{$func}->{signature}->{web_hook_url} = "https://$user->{username}:$user->{password}\@$env->{HTTP_HOST}$env->{REQUEST_URI}";

	    push @functions, $function->{$func}->{signature};
	}

	print STDERR Dumper(\@funcs) if $ENV{DEBUG};

	$res->body( encode_json( \@functions ) );

	return $res->finalize;
    } elsif (defined $post_data->{function} && exists $function->{$post_data->{function}}->{function}) {
	$function->{$post_data->{function}}->{function}->($data, $post_data, $env);
    } else {
	my $res = Plack::Response->new( 500 );

	$res->content_type('application/json');

	$res->body($swml->swaig_response_json( { response => "I'm sorry, I don't know how to do that." } ));

	return $res->finalize;
    }
};

my $assets_app = Plack::App::Directory->new( root => "/app/assets" )->to_app;

my $app = builder {

    enable sub {
	my $app = shift;

	return sub {
	    my $env = shift;
	    my $res = $app->( $env );

	    Plack::Util::header_set( $res->[1], 'Expires', 0 );

	    return $res;
	};
    };

    mount "/assets"    => $assets_app;

    mount "/swaig" => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$swaig_app;
    };

    mount "/settings" => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$settings_app;
    };
    
    mount "/auth" => sub {
	my $res = Plack::Response->new(302);
	$res->redirect(get_authorization_url());
	$res->finalize;
    };

    mount '/auth/callback' => sub {
	my $env = shift;
	my $req = Plack::Request->new( $env );

	my $tokens = get_tokens_from_code( $req->param( 'code' ) );

	if ( $tokens ) {
	    my $ua = LWP::UserAgent->new;
	    # Test to see if we can get the user's calendar list
	    my $response = $ua->get('https://www.googleapis.com/calendar/v3/users/me/calendarList?minAccessRole=owner', Authorization => "Bearer $tokens->{access_token}");

	    if ($response->is_success) {
		# Get the user's info
		my $userresp = $ua->get('https://www.googleapis.com/oauth2/v2/userinfo',
					'Authorization' => "Bearer $tokens->{access_token}");
		if ($userresp->is_success) {

		    my $user = decode_json($userresp->decoded_content);

		    $tokens->{user_id} = upsert_user($user);

		    my $user_data = get_username($tokens->{user_id});

		    upsert_token_data($tokens);

		    my $res = Plack::Response->new(302);
		    $res->redirect("/success?username=$user_data->{username}");
		    return $res->finalize;
		} else {
		    print STDERR $userresp->status_line;
		    my $res = Plack::Response->new(302);
		    $res->redirect('/error?error=1');
		    return $res->finalize;
		}
	    } else {
		print STDERR $response->status_line;
		my $res = Plack::Response->new(302);
		$res->redirect('/error?error=2');
		return $res->finalize;
	    }
	} else {
	    my $res = Plack::Response->new(404);
	    $res->redirect('/error?error=3');
	    return $res->finalize;
	}
    };

    mount '/success' => sub {
	my $env      = shift;
	my $req      = Plack::Request->new( $env );
	my $username = $req->param( 'username' );

	my $template = HTML::Template->new(
	    filename => '/app/template/success.tmpl',
	    die_on_bad_params => 0,
	    );

	my $user = get_user_credentials($username);

	$template->param( url => "https://$user->{username}:$user->{password}\@$env->{HTTP_HOST}/swaig" );
	$template->param( settings_url => "https://$user->{username}:$user->{password}\@$env->{HTTP_HOST}/settings" );

	my $res = Plack::Response->new(200);
	$res->content_type( 'text/html' );
	$res->body($template->output);
	return $res->finalize;
    };

    mount '/tos' => sub {
	my $env = shift;
	my $template = HTML::Template->new(
	    filename => '/app/template/tos.tmpl',
	    die_on_bad_params => 0,
	    );

	my $res = Plack::Response->new(200);
	$res->content_type( 'text/html' );
	$res->body($template->output);
	return $res->finalize;
    };

    mount '/error' => sub {
	my $env = shift;
	my $template = HTML::Template->new(
	    filename => '/app/template/error.tmpl',
	    die_on_bad_params => 0,
	    );

	my $res = Plack::Response->new(200);
	$res->content_type( 'text/html' );
	$res->body($template->output);
	return $res->finalize;
    };

    mount '/privacy' => sub {
	my $env = shift;
	my $template = HTML::Template->new(
	    filename => '/app/template/privacy.tmpl',
	    die_on_bad_params => 0,
	    );


	my $res = Plack::Response->new(200);
	$res->content_type( 'text/html' );
	$res->body($template->output);
	return $res->finalize;
    };

    mount '/' => sub {
	my $env = shift;
	my $template = HTML::Template->new(
	    filename => '/app/template/index.tmpl',
	    die_on_bad_params => 0,
	    );

	my $res = Plack::Response->new(200);
	$res->content_type( 'text/html' );
	$res->body($template->output);
	return $res->finalize;
    };

};

# Create a Plack builder and wrap the app
my $builder = builder {
    $app;
};

my $dbh = DBI->connect(
    "dbi:Pg:dbname=$database;host=$host;port=$port",
    $dbusername,
    $dbpassword,
    { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

my $sql = <<'SQL';
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    google_id TEXT UNIQUE,
    username TEXT,
    password TEXT,
    hd TEXT,
    verified_email BOOLEAN,
    email TEXT,
    picture TEXT
);
CREATE TABLE IF NOT EXISTS google_calendar_credentials (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) UNIQUE,
    scope TEXT,
    refresh_token TEXT,
    access_token TEXT,
    expires_in INT,
    token_type TEXT,
    default_location TEXT,
    calendar_id TEXT,
    notes TEXT,
    timezone TEXT
);
SQL

$dbh->do($sql) or die "Couldn't create table: $DBI::errstr";

$dbh->disconnect;

# Running the PSGI application
my $runner = Plack::Runner->new;

$runner->run( $builder );

1;
