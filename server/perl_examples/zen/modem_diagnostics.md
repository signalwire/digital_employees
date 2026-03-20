modem_diagnostics
-----------------------

* Name:`modem_diagnostics`
* Purpose:`customer modem upstream downstream and snr levels`
* Argument:`account_number|7 digit number,cpni|4 digit number`

```bash

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $customer  = $post_data->{meta_data}->{customer};

if ($customer) {
    $res->body( $swml->swaig_response_json( { response => "Tell the user here are the test results. Downstream level: $customer->{modem_downstream_level}, Upstream level: $customer->{modem_upstream_level}, Modem SNR: $customer->{modem_snr}" } ) );
} else {
    $res->body( $swml->swaig_response_json( { response => "Invalid try again. Use modem-diagnostics-function" } ) );
}

return $res->finalize;
```
