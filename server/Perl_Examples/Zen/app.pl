#!/bin/env perl
# app.pl - SignalWire AI Agent / Zen AI Application
use lib '.', '/app';
use strict;
use warnings;

# SignalWire modules
use SignalWire::ML;
use SignalWire::RestAPI;
use SignalWire::CompatXML;
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
use File::Slurp;
use LWP::UserAgent;
use Time::Piece;
use JSON::PP;
use Data::Dumper;
use DateTime;
use Env::C;
use DBI;
use UUID 'uuid';
use URI::Escape qw(uri_escape);

my $ENV = Env::C::getallenv();

my ( $protocol, $dbusername, $dbpassword, $host, $port, $database ) = $ENV{DATABASE_URL} =~ m{^(?<protocol>\w+):\/\/(?<username>[^:]+):(?<password>[^@]+)@(?<host>[^:]+):(?<port>\d+)\/(?<database>\w+)$};

# Onboard SWAIG Registry
my %function = (
    check_for_input => \&check_for_input
    );


# SignalWire AI Agent function definitions
my $function = {
    update_phone_number => { function  => \&update_phone_number,
                             signature => {
                                 function => 'update_phone_number',
                                 purpose  => "To update the customer phone number",
                                 argument => {
                                     type => "object",
                                     properties => {
                                         phone_number => {
                                             type => "string",
                                             description => "users phone number in e.164 format" },
                                     },
                                     required => [ 'phone_number' ]
                                 }
                             }
    },
    speed_test => { function  => \&speed_test,
                    signature => {
                        function => 'speed_test',
                        purpose  => "To test the speed of the network",
                        argument => {
                            type => "object",
                            properties => {
                                account_number => {
                                    type => "string",
                                    description => "users account number" },
                                cpni => {
                                    type => "boolean",
                                    description => "users 4 digit pin" },
                            },

                            required => [ 'account_number', 'cpni' ]
                        }
                    }
    },
    modem_diagnostics => { function  => \&modem_diagnostics,
                           signature => {
                               function => 'modem_diagnostics',
                               purpose  => "To test the modem diagnostics",
                               argument => {
                                   type => "object",
                                   properties => {
                                       account_number => {
                                           type => "string",
                                           description => "users account number" },
                                       cpni => {
                                           type => "boolean",
                                           description => "users 4 digit pin" },
                                   },
                                   required => [ 'account_number', 'cpni' ]
                               }
                           }
    },
    verify_customer => { function  => \&verify_customer,
                         signature => {
                             function => 'verify_customer',
                             purpose  => "To verify the customer",
                             argument => {
                                 type => "object",
                                 properties => {
                                     account_number => {
                                         type => "string",
                                         description => "users account number" },
                                     cpni => {
                                         type => "boolean",
                                         description => "users 4 digit pin" },
                                 },
                                 required => [ 'account_number', 'cpni' ]
                             }
                         }
    },
    modem_swap => { function  => \&modem_swap,
                    signature => {
                        function => 'modem_swap',
                        purpose  => "To swap the modem",
                        argument => {
                            type => "object",
                            properties => {
                                mac_address => {
                                    type => "string",
                                    description => "modem mac address" },
                            },
                            required => [ 'mac_address' ]
                        }
                    }
    },
    verify_mfa => { function  => \&verify_mfa,
                    signature => {
                        function => 'verify_mfa',
                        purpose  => "To verify the MFA",
                        argument => {
                            type => "object",
                            properties => {
                                token => {
                                    type => "string",
                                    description => "MFA token" },
                            },
                            required => [ 'token' ]
                        }
                    }
    },
    send_mfa => { function  => \&send_mfa,
                  signature => {
                      function => 'send_mfa',
                      purpose  => "To send the MFA",
                      argument => {
                          type => "object",
                          properties => {
                              phone_number => {
                                  type => "string",
                                  description => "users phone number in e.164 format" },
                          },
                          required => [ 'phone_number' ]
                      }
                  }
    }
};


sub scramble_last_seven {
    my ($str) = @_;
    my $initial_part = substr($str, 0, -7);
    my $to_scramble = substr($str, -7);
    my $scrambled = join '', shuffle(split //, $to_scramble);
    return $initial_part . $scrambled;
}

sub check_for_input {
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
    my $post_data = decode_json( $req->raw_body );
    my $data      = $post_data->{argument}->{parsed}->[0];
    my $swml      = SignalWire::ML->new;
    my $json      = JSON::PP->new->ascii->pretty->allow_nonref;
    my $convo_id  = $post_data->{conversation_id};
    my @message;

    my $dbh = DBI->connect(
        "dbi:Pg:dbname=$database;host=$host;port=$port",
        $dbusername,
        $dbpassword,
        { AutoCommit => 1, RaiseError => 1 }) or die $DBI::errstr;

    my $select_sql = "SELECT * FROM ai_messages WHERE convo_id = ? AND replied = false ORDER BY id ASC";

    my $sth = $dbh->prepare( $select_sql );

    $sth->execute( $convo_id ) or die $DBI::errstr;

    while ( my $row = $sth->fetchrow_hashref ) {
        push @message, "$row->{message}";

        my $update_sql = "UPDATE ai_messages SET replied = true WHERE id = ?";

        my $usth = $dbh->prepare( $update_sql );

        $usth->execute( $row->{id} ) or die $DBI::errstr;
    }

    my $res = Plack::Response->new( 200 );

    $res->content_type( 'application/json' );

    if ( @message == 0 ) {
        $res->body( $swml->swaig_response_json( [ { response => "ok" } ] ) );
    } else {
        my $email = join(" ", @message);
        $res->body( $swml->swaig_response_json( { action => [ { user_input => "My email is $email" } ], { toggle_functions => [{ function => 'check_for_input', active => 'false' }] } }) );
    }

    $dbh->disconnect;

    return $res->finalize;
}

sub verify_customer {
        my $data      = shift;
        my $post_data = shift;
        my $env       = shift;
        my $swml      = SignalWire::ML->new;
        my $res       = Plack::Response->new( 200 );

        my $dbh = DBI->connect(
            "dbi:Pg:dbname=$database;host=$host;port=$port",
            $dbusername,
            $dbpassword,
            { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";
        my $sql = "SELECT * FROM customers WHERE account_number = ? AND cpni = ? OR phone_number = ? LIMIT 1";

        my $sth = $dbh->prepare( $sql );
        $sth->bind_param(1,$data->{account_number});
        $sth->bind_param(2,$data->{cpni});
        $sth->bind_param(3,$data->{phone_number});
        $sth->execute() or die "Couldn't execute statement: $DBI::errstr";

        my $agents = $sth->fetchrow_hashref;

        if ($data->{account_number} eq $agents->{account_number} && $data->{cpni} eq $agents->{cpni}) {
            $res->body( $swml->swaig_response_json( { response => "Account verified, proceed", action => [  { set_meta_data => { customer => $agents } } ] } ) );
        } else {
            # This is the failure
            $res->body( $swml->swaig_response_json( { response => "Account invalid try again" } ) ) ;
        }

        return $res->finalize;
}

sub verify_mfa {
        my $data      = shift;
        my $post_data = shift;
        my $env       = shift;
        my $swml      = SignalWire::ML->new;
        my $res       = Plack::Response->new( 200 );
        my $mfa       = $post_data->{meta_data}->{mfa};

        my $sw = SignalWire::RestAPI->new(
            AccountSid  => $ENV{ACCOUNT_SID},
            AuthToken   => $ENV{AUTH_TOKEN},
            Space       => $ENV{SPACE_NAME},
            API_VERSION => 'api/relay/rest'
            );

        my $verify = $sw->POST("mfa/$mfa->{id}/verify",
                               token => $data->{token});


	print STDERR Dumper($verify);
        $res->content_type('application/json');

        my $resp = decode_json($verify->{content});

	
	
        if ($resp->{success} eq 'true') { # Assuming success field in $data indicates verification success
            $res->body( $swml->swaig_response_json( { response => "Verification successful", action => [  { set_meta_data => { verified => JSON::true } } ] } ) );
        } else {
            $res->body( $swml->swaig_response_json( { response => "Verification failed, try again" } ) );
        }

        return $res->finalize;
}

sub send_mfa {
        my $data      = shift;
        my $post_data = shift;
        my $env       = shift;
        my $swml      = SignalWire::ML->new;
        my $res       = Plack::Response->new( 200 );
        my $customer  = $post_data->{meta_data}->{customer};

        my $cid = $customer->{'phone_number'};

        my $sw = SignalWire::RestAPI->new(
            AccountSid  => $ENV{ACCOUNT_SID},
            AuthToken   => $ENV{AUTH_TOKEN},
            Space       => $ENV{SPACE_NAME},
            API_VERSION => 'api/relay/rest'
            );
        # Send SMS
        my $response = $sw->POST( "mfa/sms",
                                  to => $customer->{'phone_number'},
				  from => '$ENV{ASSISTANT}',
                                  message => 'Your number to verify is: ',
                                  allow_alpha => 'true',
                                  token_length => 6,
                                  valid_for => 7200,
                                  max_attempts => 4
            );

	print STDERR Dumper $response;
        my $decoded_sms_response = decode_json($response->{content});

        if ($decoded_sms_response->{success}) {
            $res->body( $swml->swaig_response_json( { response => "6 digit number sent", action => [  { set_meta_data => { mfa => $decoded_sms_response } } ] } ) );
        } else {
            # This is the failure
            $res->body( $swml->swaig_response_json( { response => "6 digit number invalid try again" } ) ) ;
        }

        $res->content_type( 'application/json' );
        return $res->finalize;
}

sub speed_test {
    my $data      = shift;
    my $post_data = shift;
    my $env       = shift;
    my $swml      = SignalWire::ML->new;
    my $res       = Plack::Response->new( 200 );
    my $customer  = $post_data->{meta_data}->{customer};

    if ($customer->{modem_speed_upload} && $customer->{modem_speed_download}) {
        $res->body( $swml->swaig_response_json( { response => "Tell the user here are the test results. Download speed: $customer->{modem_speed_download}, Upload speed: $customer->{modem_speed_upload}" } ) );
    } else {
        $res->body( $swml->swaig_response_json( { response => "Invalid try again speed_test" } ) );

    }

    return $res->finalize;
}

sub update_phone_number {
        my $data      = shift;
        my $post_data = shift;
        my $env       = shift;
        my $swml      = SignalWire::ML->new;
        my $res       = Plack::Response->new( 200 );
        my $customer  = $post_data->{meta_data}->{customer};

        my $dbh = DBI->connect(
            "dbi:Pg:dbname=$database;host=$host;port=$port",
            $dbusername,
            $dbpassword,
            { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

        if ( is_valid_phone_number($data->{phone_number}) ) {
            # Add a SQL update statement (modify this to match your actual table and field names)
            my $update_sql = "UPDATE customers SET phone_number = ? WHERE account_number = ?";
            my $update_sth = $dbh->prepare( $update_sql );
            $update_sth->bind_param(1, $data->{phone_number});
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

            if (lc $agents->{phone_number} eq lc $data->{phone_number} ) {
                $res->body( $swml->swaig_response_json( { response => "Customers phone number updated, Anything else I can help you with today?", action => [  { set_meta_data => { customer => $agents } } ] } ) );
            } else {
                $res->body( $swml->swaig_response_json( { response => "Error updating phone number, phone number may be invalid, try again.  #1" } ) );
            }
        } else {
            $res->body( $swml->swaig_response_json( { response => "Error supdating phone number, phone number may be invalid, Please provide  a 10 digit number.  #2" } ) );
        }

        return $res->finalize;
}

sub modem_swap {
        my $data      = shift;
        my $post_data = shift;
        my $env       = shift;
        my $swml      = SignalWire::ML->new;
        my $res       = Plack::Response->new( 200 );
        my $customer  = $post_data->{meta_data}->{customer};

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
                $res->body( $swml->swaig_response_json( { response => "Customers modem mac address updated, please plug in your modem and allow 1 minute for all systems to update your new modem.", action => [  { set_meta_data => { customer => $agents } } ] } ) );

            } else {
                $res->body( $swml->swaig_response_json( { response => "Error swapping modem, mac address may be invalid, try again.  #1" } ) );
            }
        } else {
            $res->body( $swml->swaig_response_json( { response => "Error swapping modem, mac address may be invalid, Please provide 12 characters with a combination of numbers 0 through 9 and letters ranging from a-f.  #2" } ) );
        }

        return $res->finalize;
}

sub modem_diagnostics {
        my $data      = shift;
        my $post_data = shift;
        my $env       = shift;
        my $swml      = SignalWire::ML->new;
        my $res       = Plack::Response->new( 200 );
        my $customer  = $post_data->{meta_data}->{customer};


        if ($customer) {
            $res->body( $swml->swaig_response_json( { response => "Tell the user here are the test results. Downstream level: $customer->{modem_downstream_level}, Upstream level: $customer->{modem_upstream_level}, Modem SNR: $customer->{modem_snr}" } ) );
        } else {
            $res->body( $swml->swaig_response_json( { response => "Invalid try again. Use modem-diagnostics-function" } ) );
        }

        return $res->finalize;
}

sub is_valid_mac_address {
    my ($mac) = @_;

    # Regular expression for a MAC address with optional colons or dashes
    my $mac_regex = qr/^([0-9A-Fa-f]{2}(:|-)?){5}[0-9A-Fa-f]{2}$/;

    return $mac =~ $mac_regex;
}

sub is_valid_phone_number {
    my ($phone) = @_;

    my $phone_regex = qr/^\+?1?\d{10}$/;

    return $phone =~ $phone_regex;
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
sub authenticator {
    my ( $user, $pass, $env ) = @_;
    my $req    = Plack::Request->new( $env );

    if ( $ENV{USERNAME} eq $user && $ENV{PASSWORD} eq $pass ) {
        return 1;
    }

    return 0;
}

my $debug_app = sub {
    my $env       = shift;
    my $req       = Plack::Request->new( $env );
    my $swml      = SignalWire::ML->new;
    my $post_data = decode_json( $req->raw_body );
    my $res       = Plack::Response->new( 200 );

    $res->content_type( 'application/json' );

    $res->body( $swml->swaig_response_json( { response => "data received" } ) );

    print STDERR "Data received: " . Dumper( $post_data ) if $ENV{DEBUG};

    return $res->finalize;
};

my $laml_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new( $env );
    my $to      = $req->param( 'To' );
    my $from    = $req->param( 'From' );
    my $message = $req->param( 'Body' );
    my $sid     = $req->param( 'MessageSid' );
    my $resp    = SignalWire::CompatXML->new;

    $resp->name( 'Response' );

    print STDERR "$to, $from, $message, $sid\n" if $ENV{DEBUG};

    my $dbh = DBI->connect(
        "dbi:Pg:dbname=$database;host=$host;port=$port",
        $dbusername,
        $dbpassword,
        { AutoCommit => 1, RaiseError => 1 }) or die $DBI::errstr;

    my $insert_sql = "INSERT INTO ai_messages (convo_id, message, call_id) VALUES (?, ?, ?)";

    my $sth = $dbh->prepare( $insert_sql );

    my $rv  = $sth->execute( $from, $message, $sid ) or die $DBI::errstr;

    my $res = Plack::Response->new( 200 );

    $res->content_type( 'text/xml' );

    $res->body( $resp->to_string );

    return $res->finalize;
};

my $swml_app = sub {
    my $env         = shift;
    my $req         = Plack::Request->new( $env );
    my $post_data   = decode_json( $req->raw_body ? $req->raw_body : '{}' );
    my $swml        = SignalWire::ML->new;
    my $ai          = 1;
    my $prompt      = read_file( "/app/prompt.md" );
    my $post_prompt = read_file( "/app/post_prompt.md" );
    my $from        = $post_data->{call}->{from};

    my $dbh = DBI->connect(
        "dbi:Pg:dbname=$database;host=$host;port=$port",
        $dbusername,
        $dbpassword,
        { AutoCommit => 1, RaiseError => 1 } ) or die $DBI::errstr;
    #select user by phone number and get name

    my $select_sql = "SELECT * FROM customers WHERE Phone_number = ? LIMIT 1";

    my $sth = $dbh->prepare( $select_sql );

    my $rv  = $sth->execute( $from ) or die $DBI::errstr;

    my $existing = $sth->fetchrow_hashref;

    $sth->finish;

    $dbh->disconnect;

    $swml->add_application( "main", "answer" );
    $swml->add_application( "main", "record_call", { format => 'wav', stereo => 'true' });

    if ( $existing ) {
        $swml->add_application( "main", "set", { extra_prompt => "##Step 0\nThis user already had a profile, offer to transfer them to an 'agent' and skip all the other steps." } );
    }

    $swml->set_aiprompt({
        temperature => $ENV{TEMPERATURE},
        top_p       => $ENV{TOP_P},
        text        => $prompt });

    $swml->add_aiparams( { conversation_id => "$from" } );

    $swml->add_aiswaigdefaults({ web_hook_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/swaig" });

    $swml->set_aipost_prompt( {
        temperature => $ENV{TEMPERATURE},
        top_p       => $ENV{TOP_P},
        text        => $post_prompt });

    $swml->set_aipost_prompt_url( { post_prompt_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/post" } );

    $swml->add_ailanguage({
        code    => 'en-US',
        name    => 'English',
        voice   => 'Josh',
        engine  => 'elevenlabs',
        fillers => [ "one moment", "one moment please" ] });

    my $static_greeting = "Hello and thank you for calling Livewire, your local cable company! My name is Zen, an AI-driven digital employee powered by SignalWire. May I ask who I'm speaking with?";

    if ( $existing ) {
        $static_greeting = "Hello, $existing->{firstname}! I'm here to help you diagnose any cable modem problems.";
    }

    $swml->add_aiparams( { debug_webhook_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/debughook",
                           static_greeting => $static_greeting } );

    $swml->add_aiinclude( {
        functions => [ 'verify_customer', 'check_for_input', 'modem_diagnostics', 'modem_swap', 'speed_test', 'update_phone_number', 'verify_mfa', 'send_mfa' ],
        user => $ENV{USERNAME},
        pass => $ENV{PASSWORD},
        url  => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/swaig" } );

    $swml->add_aiswaigdefaults( { web_hook_url           => "https://$env->{HTTP_HOST}/swaig",
                                  web_hook_auth_user     => $ENV{USERNAME},
                                  web_hook_auth_password => $ENV{PASSWORD}
                                } );


    $swml->add_aiswaigfunction( {
        function => 'check_for_input',
        purpose  => "check for input",
        argument => "none" } );

    my $msg = SignalWire::ML->new;

    $msg->add_application( "main", "send_sms" => { to_number   => '${args.to}',
                                                   from_number => $ENV{ASSISTANT},
                                                   body        => 'Hello, This is Zen from Livewire. Reply STOP to stop.' } );

    my $output = $msg->swaig_response( {
        response => "Message sent, please wait for the user to reply.",
        action   => [ { SWML => $msg->render }, { toggle_functions => [{ function => 'send_message', active => 'false' }] } ] } );

    $swml->add_aiswaigfunction( {
        function => 'send_message',
        purpose  => "use to send text messages to a user when you need their email address",
        argument => {
            type => "object",
            properties => {
                to => {
                    type        => "string",
                    description => "The users number in e.164 format" }
            },
            required => [ "to" ]
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
                next_id             => $next_id ? "/convo?id=$next_id" : "/convo",
                prev_id             => $prev_id ? "/convo?id=$prev_id" : "/convo",
                next_text           => $next_id ? "Next >"     : "",
                prev_text           => $prev_id ? "< Previous" : "",
                call_id             => $p->{'call_id'},
                call_start_date     => $p->{'call_start_date'},
                call_log            => $p->{'call_log'},
                swaig_log           => $p->{'swaig_log'},
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

    print STDERR Dumper($post_data) if $ENV{DEBUG} > 2;

    if ( defined $post_data->{function} && exists $function{$post_data->{function}} ) {
        $function{$post_data->{function}}->( $env );
    } elsif (defined $post_data->{action} && $post_data->{action} eq 'get_signature') {
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
        $function->{$post_data->{function}}->{function}->($data, $post_data, $env);
    } else {
        my $res = Plack::Response->new( 500 );

        $res->content_type('application/json');

        $res->body($swml->swaig_response_json( { response => "I'm sorry, I don't know how to do that." } ));

        return $res->finalize;
    }
};

my $applicant_list = sub {
    my $env = shift;
    my $template = HTML::Template->new(
        filename => '/app/template/index.tmpl',
        die_on_bad_params => 0,
        );

    my $dbh = DBI->connect(
        "dbi:Pg:dbname=$database;host=$host;port=$port",
        $dbusername,
        $dbpassword,
        { AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

    my $sql = "SELECT * FROM customers WHERE created > ? ORDER BY created DESC";

    my $sth = $dbh->prepare( $sql );

    my $today = DateTime->now->truncate( to => 'day' )->subtract( days => 1 );

    $sth->execute( $today->ymd ) or die "Couldn't execute statement: $DBI::errstr\n";

    my @table_contents;

    while ( my $row = $sth->fetchrow_hashref ) {
        $row->{phone} = scramble_last_seven( $row->{phone} );
        push @table_contents, $row;
    }
    $template->param( site_url => "https://$env->{HTTP_HOST}" );
    $template->param( table_contents => \@table_contents, index => 1 );
    my $res = Plack::Response->new(200);
    $res->content_type( 'text/html' );
    $res->body($template->output);
    return $res->finalize;
};

my $applicant_edit = sub {
    my $env = shift;
    my $request = Plack::Request->new($env);

    my $params = $request->parameters;

    if ( $request->method eq 'POST' ) {
    my $sql = "UPDATE customers SET
    first_name = ?,
    last_name = ?,
    Active = ?,
    Phone_number = ?,
    mac_address = ?,
    CPNI = ?,
    Account_Number = ?,
    service_address = ?,
    billing_address = ?,
    email_address = ?,
    modem_speed_upload = ?,
    modem_speed_download = ?,
    modem_upstream_level = ?,
    modem_downstream_level = ?,
    modem_snr = ?,
    modem_downstream_uncorrectables = ?
    WHERE id = ?";

        print STDERR "SQL: $sql\n" if $ENV{DEBUG};

        my $dbh = DBI->connect(
            "dbi:Pg:dbname=$database;host=$host;port=$port",
            $dbusername,
            $dbpassword,
            { AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

        my $sth = $dbh->prepare( $sql ) or die $DBI::errstr;
        print Dumper $params;
        $sth->execute(
                $params->{first_name},
                $params->{last_name},
                $params->{Active},
                $params->{Phone_number},
                $params->{mac_address},
                $params->{CPNI},
                $params->{Account_Number},
                $params->{service_address},
                $params->{billing_address},
                $params->{email_address},
                $params->{modem_speed_upload},
                $params->{modem_speed_download},
                $params->{modem_upstream_level},
                $params->{modem_downstream_level},
                $params->{modem_snr},
                $params->{modem_downstream_uncorrectables},
                $params->{id}
            ) or die $DBI::errstr;

        print Dumper $sth->rows;
        $sth->finish;

        $dbh->disconnect;

        my $res = Plack::Response->new( 200 );

        $res->content_type( 'text/html' );

        $res->redirect('/');

        return $res->finalize;

    } else {
        my $sql = "SELECT * FROM customers WHERE application_key = ?";
        my $dbh = DBI->connect(
            "dbi:Pg:dbname=$database;host=$host;port=$port",
            $dbusername,
            $dbpassword,
            { AutoCommit => 1, RaiseError => 1 }) or die "Couldn't execute statement: $DBI::errstr\n";

        my $sth = $dbh->prepare( $sql );

        $sth->execute( $params->{key} ) or die $DBI::errstr;

        my $template = HTML::Template->new(
            filename => '/app/template/edit.tmpl',
            die_on_bad_params => 0,
            );

        my $user = $sth->fetchrow_hashref;
        print Dumper $user;
        $template->param( %$user );

        my $res = Plack::Response->new( 200 );

        $res->content_type( 'text/html' );

        $res->body( $template->output );

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

    mount '/assets'    => $assets_app;

    mount '/swaig' => builder {
        enable "Auth::Basic", authenticator => \&authenticator;
        $swaig_app;
    };

    mount '/convo' => builder {
        enable "Auth::Basic", authenticator => \&authenticator;
        $convo_app;
    };

    mount '/swml' => builder {
        enable "Auth::Basic", authenticator => \&authenticator;
        $swml_app;
    };

    mount '/laml' => builder {
        enable "Auth::Basic", authenticator => \&authenticator;
        $laml_app;
    };

    mount '/post' => builder {
        enable "Auth::Basic", authenticator => \&authenticator;
        $post_app;
    };

    mount '/edit' => $applicant_edit;

    mount '/' => $applicant_list;
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
CREATE TABLE IF NOT EXISTS customers (
    id INT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    Active BOOLEAN,
    Phone_number TEXT,
    mac_address TEXT,
    CPNI INT,
    Account_Number INT,
    service_address TEXT,
    billing_address TEXT,
    email_address TEXT,
    modem_speed_upload REAL,
    modem_speed_download REAL,
    modem_upstream_level REAL,
    modem_downstream_level REAL,
    modem_snr INT,
    modem_downstream_uncorrectables INT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    call_id TEXT,
    convo_id TEXT,
    message TEXT,
    replied BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS ai_summary (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    convo_id TEXT,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS ai_post_prompt (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB
);
SQL

$dbh->do($sql) or die "Couldn't create table: $DBI::errstr";

$dbh->disconnect;

# Running the PSGI application
my $runner = Plack::Runner->new;

$runner->run( $builder );

1;
