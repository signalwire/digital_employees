modem_swap
-----------------------

* Name:`modem_swap`
* Purpose:`Swap the users modem`
* Argument:`mac_address|new modem MAC Address in lowercase hex 12 characters`

```perl

my $env       = shift;
my $req       = Plack::Request->new( $env );
my $swml      = SignalWire::ML->new;
my $post_data = decode_json( $req->raw_body );
my $data      = $post_data->{argument}->{parsed}->[0];
my $res       = Plack::Response->new( 200 );
my $agent     = $req->param( 'agent_id' );
my $customer  = $post_data->{meta_data}->{customer};

sub is_valid_mac_address {
    my ($mac) = @_;

    # Regular expression for a MAC address with optional colons or dashes
    my $mac_regex = qr/^([0-9A-Fa-f]{2}(:|-)?){5}[0-9A-Fa-f]{2}$/;

    return $mac =~ $mac_regex;
}

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
        $res->body( $swml->swaig_response_json( { response => "Customers modem mac address updated, please allow 5 minutes for all systems to update and plug in your new modem.", action => [  { set_meta_data => { customer => $agents } } ] } ) );
        broadcast_by_agent_id( $agent, $agents );
        
    } else {
        $res->body( $swml->swaig_response_json( { response => "Error swapping modem, mac address may be invalid, try again.  #1" } ) );
    }
} else {
    $res->body( $swml->swaig_response_json( { response => "Error swapping modem, mac address may be invalid, try again later.  #2" } ) );  
}

return $res->finalize;

```
