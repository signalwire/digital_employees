speed_test
-----------------------

* Name:`speed_test`
* Purpose:`Test upload and download speed from the modem`
* Argument:`account_number|7 digit number,cpni|4 digit number`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $customer  = $post_data->{meta_data}->{customer};

if ($customer->{modem_speed_upload} && $customer->{modem_speed_download}) {
    $res->body( $swml->swaig_response_json( { response => "Tell the user here are the test results. Download speed: $customer->{modem_speed_download}, Upload speed: $customer->{modem_speed_upload}" } ) );
} else {
    $res->body( $swml->swaig_response_json( { response => "Invalid try again speed_test" } ) );
}

return $res->finalize;
```
