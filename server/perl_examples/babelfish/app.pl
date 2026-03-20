#!/usr/bin/env perl
# app.pl - Bablefish Application
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
use Plack::App::WebSocket;

# Other modules
use HTTP::Request::Common;
use HTML::Template::Expr;
use LWP::UserAgent;
use JSON::PP;
use URI::Encode qw(uri_encode);
use Data::Dumper;
use Encode qw(encode_utf8 decode_utf8);

# Main Application
my $web_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new($env);
    my $params  = $req->parameters;
    
    my $template = HTML::Template::Expr->new(
        filename => "/app/template/index.tmpl",
        die_on_bad_params => 0
    );

    $template->param(%ENV);
    
    my $res = Plack::Response->new(200);
    $res->content_type('text/html');
    $res->body($template->output);
    
    return $res->finalize;
};

# Hangup endpoint
my $hangup_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new($env);
    my $method  = $req->method;
    my $res     = Plack::Response->new(200);
    my $data    = decode_json($req->raw_body || '{}');
    my $json    = JSON::PP->new->ascii->pretty->allow_nonref;

    $res->content_type('application/json');

    if ($method eq 'POST') {
        my $sw = SignalWire::RestAPI->new(
            AccountSid  => $ENV{ACCOUNT_SID},
            AuthToken   => $ENV{AUTH_TOKEN},
            Space       => $ENV{SPACE_NAME},
            Domain      => $ENV{DOMAIN_NAME},
            API_VERSION => "api/calling"
        );
        
        my $response = $sw->POST(
            "calls",
            id      => $data->{uuid},
            command => "calling.end",
            params  => { reason => "hangup" }
        );
        print STDERR Dumper($sw);
        print STDERR Dumper($response);
        
        if ($response->{code} == 200) {
            $res->body($json->encode({ success => JSON::true, message => "Call hung up" }));
        } else {
            $res->body($json->encode({ success => JSON::false, message => "Call hangup failed" }));
        }
    } else {
        $res->body($json->encode({ success => JSON::false, message => "Invalid Method" }));
    }
    
    return $res->finalize;
};

# Call endpoint
my $call_app = sub {
    my $env     = shift;
    my $req     = Plack::Request->new($env);
    my $method  = $req->method;
    my $res     = Plack::Response->new(200);
    my $data    = decode_json($req->raw_body || '{}');
    my $json    = JSON::PP->new->ascii->pretty->allow_nonref;
    my $swml    = SignalWire::ML->new;
    
    $res->content_type('application/json');

    if ($method eq 'POST') {
        my $sw = SignalWire::RestAPI->new(
            AccountSid  => $ENV{ACCOUNT_SID},
            AuthToken   => $ENV{AUTH_TOKEN},
            Space       => $ENV{SPACE_NAME},
            Domain      => $ENV{DOMAIN_NAME},
            API_VERSION => "api/calling"
        );

        print Dumper \%ENV;
        
        $swml->add_application("main", "answer");

        if ($data->{recordCall}) {
            $swml->add_application("main", "record_call", { format => 'wav', stereo => 'true' });
        }
        
        $swml->add_application("main", "live_translate", { action => {
            start => {
                webhook     => $data->{webhook},
                from_lang   => $data->{fromLang},
                to_lang     => $data->{toLang},
                from_voice  => $data->{fromVoice},
                to_voice    => $data->{toVoice},
                live_events => $data->{liveEvents},
                ai_summary  => $data->{aiSummary},
                direction   => [ "local-caller", "remote-caller" ]
            } } } );
        
        $swml->add_application("main", "connect", { to => $data->{caller}, from => $ENV{FROM_NUMBER} });
        print STDERR $swml->render_json;

        my $response = $sw->POST(
            "calls",
            command => "dial",
            params  => { swml => $swml->render, to => $data->{callee}, from => $ENV{FROM_NUMBER} }
        );

        print STDERR Dumper($response);

        if ($response->{code} == 200) {
            my $resdata = decode_json($response->{content});

            $res->body($json->encode({ success => JSON::true, message => "Call initiated", uuid => $resdata->{id} }));
        } else {
            $res->body($json->encode({ success => JSON::false, message => "Call failed" }));
        }

        return $res->finalize;
        
    } else {
        $res->body($json->encode({ success => JSON::false, message => "Invalid Method" }));
        
        return $res->finalize;
    }
};

my $webhook_app = sub {
    my $env  = shift;
    my $req  = Plack::Request->new($env);
    my $data = eval { decode_json($req->content) };
    my $res  = Plack::Response->new(200);

    unless ($data) {
        $res->status(400);
        $res->content_type('application/json');
        $res->body(encode_json({ error => 'Invalid JSON' }));
        return $res->finalize;
    }

    my $uuid = $data->{channel_data}->{call_id};

    queue_event($uuid, $data);

    $res->content_type('application/json');
    $res->body(encode_json({ success => 1 }));

    return $res->finalize;
};

# Events endpoint
my $events_app = sub {
    my $env = shift;
    my $req = Plack::Request->new($env);
    my $res = Plack::Response->new(200);

    $res->content_type('text/html');

    my $template = HTML::Template::Expr->new(
        filename => "/app/template/events.tmpl",
        die_on_bad_params => 0
    );

    $res->body($template->output);

    return $res->finalize;
};

# WebSocket entry point
my %clients;

sub queue_event {
    my ($uuid, $event) = @_;
    my $message = encode_json($event);

    if (exists $clients{$uuid}) {
        for my $client (@{ $clients{$uuid} }) {
            $client->send($message);
        }
    } else {
        warn "No clients connected for UUID: $uuid";
    }
}

my $websocket_app = sub {
    my $env  = shift;
    my $req  = Plack::Request->new($env);

    my $ws = Plack::App::WebSocket->new(
        on_establish => sub {
            my $conn = shift;

            $conn->on(
                message => sub {
                    my ($conn, $msg) = @_;
                    my $data = decode_json($msg);
                    print STDERR Dumper($data);
                    if ($data->{action} && $data->{action} eq 'subscribe' && $data->{uuid}) {
                        my $uuid = $data->{uuid};
                        push @{ $clients{$uuid} }, $conn;
                        print STDERR "Client subscribed to UUID: $uuid\n";
                    }
                    
                    if ($data->{message} && $data->{uuid}) {
                        my $uuid = $data->{uuid};
                        my $message = $data->{message};

                        my $sw = SignalWire::RestAPI->new(
                            AccountSid  => $ENV{ACCOUNT_SID},
                            AuthToken   => $ENV{AUTH_TOKEN},
                            Space       => $ENV{SPACE_NAME},
                            API_VERSION => "api/calling"
                        );
                        my $response = $sw->POST(
                            "calls",
                            id      => $uuid,
                            command => "calling.live_translate",
                            params  => { action => { inject => { message => "$message", direction => "remote-caller"} } }
                        );
                        print STDERR Dumper($sw);
                        print STDERR Dumper($response);

                        queue_event($uuid, $response);

                        print STDERR "Received message: $message\n";
                    }
                }
            );

            $conn->on(
                finish => sub {
                    foreach my $uuid (keys %clients) {
                        @{ $clients{$uuid} } = grep { $_ != $conn } @{ $clients{$uuid} };
                        print STDERR "Client disconnected from UUID: $uuid\n";
                    }
                }
            );
        }
    )->to_app;

    return $ws->($env);
};

my $assets_app = Plack::App::Directory->new( root => "/app/assets" )->to_app;
my $css_app    = Plack::App::Directory->new( root => "/app/css" )->to_app;
my $js_app     = Plack::App::Directory->new( root => "/app/js" )->to_app;

my $server = builder {
    mount "/events"    => $events_app;
    mount "/websocket" => $websocket_app;
    mount "/webhook"   => $webhook_app;
    mount "/assets"    => $assets_app;
    mount "/css"       => $css_app;
    mount "/js"        => $js_app;
    mount '/call'      => $call_app;
    mount '/hangup'    => $hangup_app;
    mount '/'          => $web_app;
};

# Running the PSGI application
my $runner = Plack::Runner->new;

$runner->run($server);

1;
