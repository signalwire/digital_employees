* **Name:** `send_mfa`
* **Purpose:** `To send a 6 digit token to the user via text message`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $json      = JSON->new->allow_nonref;

# Access caller_id_number from the data


my $cid = $post_data->{'caller_id_num'};
#broadcast_by_agent_id( $agent, $cid);

# uncomment so the end user can see what all we do post to SWAIG functions
#broadcast_by_agent_id( $agent, $post_data );
# Initialize SignalWire REST API
my $sw = SignalWire::RestAPI->new(
    AccountSid  => 'replace-me',
    AuthToken   => 'PTreplace-me',
    Space       => 'replaceme',
    API_VERSION => 'api/relay/rest'
);
# Send SMS
my $response = $sw->POST( "mfa/sms",
    to => $cid,
    from => '+15552221234',
    message => 'Your number to verify is: ',
    allow_alpha => 'true',
    token_length => 6,
    valid_for => 7200,
    max_attempts => 4
);

broadcast_by_agent_id( $agent, $response);
# Decode the response
my $decoded_sms_response = $json->decode($response->{content});

if ($decoded_sms_response->{success}) {
    $res->body( $swml->swaig_response_json( { response => "6 digit number sent", action => [  { set_meta_data => { mfa => $decoded_sms_response } } ] } ) );
    broadcast_by_agent_id( $agent,  $swml->swaig_response_json( { response => "verification number has been sent to your device", action => [  { set_meta_data => { mfa => $decoded_sms_response  } } ] } ) );
} else {
    # This is the failure
    $res->body( $swml->swaig_response_json( { response => "6 digit number invalid try again" } ) ) ;
    broadcast_by_agent_id( $agent, $swml->swaig_response_json( { response => "6 digit code invalid, try again" } ) );
}

$res->content_type( 'application/json' );
return $res->finalize;
```
