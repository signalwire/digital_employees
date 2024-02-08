```
my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $json      = JSON->new->allow_nonref;
my $mfa       = $post_data->{meta_data}->{mfa};

# uncomment so the end user can see what all we do post to SWAIG functions
broadcast_by_agent_id( $agent, $data );

# Initialize SignalWire REST API
my $sw = SignalWire::RestAPI->new(
    AccountSid  => 'replace-me',
    AuthToken   => 'PTreplace-me',
    Space       => 'replace-me',
    API_VERSION => 'api/relay/rest'
);

# Get token from the user input (or wherever it's stored)
# Make the verification request
my $verify = $sw->POST("mfa/$mfa->{id}/verify",
                            token => $data->{token});                        

# Decode the verification response and print it using Dumper

$res->content_type('application/json');
broadcast_by_agent_id( $agent, $verify);

my $resp = decode_json($verify->{content});

if ($resp->{success} eq 'true') { # Assuming success field in $data indicates verification success
    $res->body( $swml->swaig_response_json( { response => "Verification successful", action => [  { set_meta_data => { verified => JSON::true } } ] } ) );
    broadcast_by_agent_id( $agent, $swml->swaig_response_json( { response => "Verification successful", action => [  { set_meta_data => { verified => JSON::true } } ] } ) );
} else {
    $res->body( $swml->swaig_response_json( { response => "Verification failed, try again" } ) );
    broadcast_by_agent_id( $agent, $swml->swaig_response_json( { response => "Verification failed, try again" } ) );
}


return $res->finalize;
```
