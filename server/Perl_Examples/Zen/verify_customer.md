verify_customer
-----------------------

* Name:`verify_customer`
* Purpose:`Verify customer account number, cpni first, last name and phone number`
* Argument:`account_number|7 digit number,cpni|4 digit number`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );

my $dbh = DBI->connect(
  "dbi:Pg:dbname=$database;host=$host;port=$port",
  $dbusername,
  $dbpassword,
  { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";
my $sql = "SELECT * FROM customers WHERE account_number = ? AND cpni = ? LIMIT 1";

my $sth = $dbh->prepare( $sql );
$sth->bind_param(1,$data->{account_number});
$sth->bind_param(2,$data->{cpni});
$sth->execute() or die "Couldn't execute statement: $DBI::errstr";

my $agents = $sth->fetchrow_hashref;


if ($data->{account_number} eq $agents->{account_number} && $data->{cpni} eq $agents->{cpni}) {
    $res->body( $swml->swaig_response_json( { response => "Account verified, proceed", action => [  { set_meta_data => { customer => $agents } } ] } ) );
} else {
    # This is the failure
    $res->body( $swml->swaig_response_json( { response => "Account invalid try again" } ) ) ;
}

return $res->finalize;
```
