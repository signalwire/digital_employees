#!/bin/env perl
# app.pl - SignalWire AI Agent / Flo's Flowers 2.0 Application
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

# SignalWire AI Agent function definitions
my $function = {
    send_flowers => { function  => \&send_flowers,
		      signature => {
			  function => 'send_flowers',
			  purpose  => "Send flowers",
			  argument => {
			      type => "object",
			      properties => {
				  to => {
				      type => "string",
				      description => "recipient's phone number in e.164 format" },
				  message => {
				      type => "string",
				      description => "message to recipient" },
				  flowertype => {
				      type => "string",
				      description => "type of flower to send" },
				  from => {
				      type => "string",
				      description => "sender's phone number in e.164 format" },
			      },
			      required => [ "to", "message", "flowertype", "from" ]
			  }
		      }
    }
};

sub scramble_last_seven {
    my ($str) = @_;

    if (!$str) {   return '+10000000000'; }
    my $initial_part = substr($str, 0, -7);
    my $to_scramble = substr($str, -7);
    my $scrambled = join '', shuffle(split //, $to_scramble);

    return $initial_part . $scrambled;
}

sub send_flowers {
	my $data      = shift;
	my $post_data = shift;
	my $env       = shift;
	my $swml      = SignalWire::ML->new();
	my $res       = Plack::Response->new(200);
	my $from      = $post_data->{call}->{from};
	my $ua        = LWP::UserAgent->new;

	my $req = HTTP::Request->new( POST => "https://api.openai.com/v1/images/generations" );

	$req->header( "Authorization" => "Bearer $ENV{OPENAI_API_KEY}" );

	$req->content_type( "application/json" );

	my $prompt = "A beautiful bouquet of $data->{flowertype}";

	$req->content( encode_json( { prompt => $prompt, model => "dall-e-3", n => 1, size => "1024x1024" } ) );

	my $image = $ua->request( $req );

	my $image_res = decode_json( $image->content );

	my $flower_url = $image_res->{data}[0]->{url};

	print STDERR Dumper($image_res);

	print STDERR Dumper($post_data);

	if ( $flower_url ) {
	    my @actions;
	    my $dbh = DBI->connect("dbi:Pg:dbname=$database;host=$host;port=$port",
				   $dbusername,
				   $dbpassword,
				   {AutoCommit => 1, RaiseError => 1, PrintError => 0});

	    my $sth = $dbh->prepare("INSERT INTO flower_deliveries (from_number, to_number, message, prompt, flower_url) VALUES (?, ?, ?, ?, ?)");

	    $sth->execute($data->{from}, $data->{to}, $data->{message}, $prompt, $flower_url);

	    $sth->finish;

	    $dbh->disconnect;

	    my $msg = SignalWire::ML->new;

	    $msg->add_application( "main", "send_sms" => { to_number   => "$data->{to}",
							   from_number => $ENV{ASSISTANT},
							   media       => [ $flower_url ],
							   body        => "You have been sent virtual flowers, from $data->{from} via Flo's Flowers, with the message: $data->{message}" } );
	    push @actions, { SWML => $msg->render };

	    $dbh->disconnect;

	    my $message = "Flowers sent to $data->{phone} with message: $data->{message}!  Enjoy your day!";

	    print STDERR "Flowers sent to $data->{phone} with message: $data->{message}!  Enjoy your day!";
	    print STDERR $swml->swaig_response_json( { post_process => 'true', response => $message, action => \@actions } );

	    $res->body($swml->swaig_response_json( { post_process => 'true', response => $message, action => \@actions } ));
	} else {
	    $res->body($swml->swaig_response_json( { post_process => 'true', response => "I'm sorry, I was unable to generate an image of the flowers.  Please try again later." } ));
	}

	return $res->finalize;
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

my $swml_app = sub {
    my $env         = shift;
    my $req         = Plack::Request->new( $env );
    my $post_data   = decode_json( $req->raw_body ? $req->raw_body : '{}' );
    my $swml        = SignalWire::ML->new;
    my $ai          = 1;
    my $prompt      = read_file( "/app/prompt.md" );
    my $post_prompt = read_file( "/app/post_prompt.md" );
    my $from        = $post_data->{call}->{from};

    $swml->add_application( "main", "answer" );
    $swml->add_application( "main", "record_call", { format => 'wav', stereo => 'true' });

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
	voice   => 'nova',
	engine  => 'openai',
	fillers => [ "hrm", "ok" ] });


    $swml->add_aiparams( { debug_webhook_url => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/debughook" } );

    $swml->add_aiinclude( {
	functions => [ 'send_flowers' ],
	user => $ENV{USERNAME},
	pass => $ENV{PASSWORD},
	url  => "https://$ENV{USERNAME}:$ENV{PASSWORD}\@$env->{HTTP_HOST}/swaig" } );

    $swml->add_aiswaigdefaults( { web_hook_url           => "https://$env->{HTTP_HOST}/swaig",
				  web_hook_auth_user     => $ENV{USERNAME},
				  web_hook_auth_password => $ENV{PASSWORD}
				} );

    $swml->add_aiapplication( "main" );

    my $res = Plack::Response->new(200);

    $res->content_type('application/json');

    $res->body($swml->render_json);

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

my $delivery_list = sub {
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
    my $sql = "SELECT * FROM  flower_deliveries ORDER BY created DESC LIMIT 25";

    my $sth = $dbh->prepare( $sql );

    $sth->execute() or die $DBI::errstr;

    my @table_contents;

    while ( my $row = $sth->fetchrow_hashref ) {
	$row->{to_number}   = scramble_last_seven( $row->{to_number} );
	$row->{from_number} = scramble_last_seven( $row->{from_number} );
	push @table_contents, $row;
    }

    $template->param( table_contents => \@table_contents, index => 1 );
    my $res = Plack::Response->new(200);
    $res->content_type( 'text/html' );
    $res->body($template->output);
    return $res->finalize;
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

    mount '/post' => builder {
	enable "Auth::Basic", authenticator => \&authenticator;
	$post_app;
    };

    mount '/' => $delivery_list;
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
CREATE TABLE IF NOT EXISTS flower_deliveries (
    id SERIAL PRIMARY KEY,
    from_number VARCHAR(20),
    to_number VARCHAR(20),
    message TEXT,
    flower_url TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    prompt TEXT,
    flower_image BYTEA
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
