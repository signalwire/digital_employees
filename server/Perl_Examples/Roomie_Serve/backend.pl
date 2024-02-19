#!/usr/bin/env perl
use DBI;
use strict;
use warnings;
use Env::C;

my $ENV = Env::C::getallenv();

my ( $protocol, $dbusername, $dbpassword, $host, $port, $database ) = $ENV{DATABASE_URL} =~ m{^(?<protocol>\w+):\/\/(?<username>[^:]+):(?<password>[^@]+)@(?<host>[^:]+):(?<port>\d+)\/(?<database>\w+)$};

my $dbh = DBI->connect(
    "dbi:Pg:dbname=$database;host=$host;port=$port",
    $dbusername,
    $dbpassword,
    { AutoCommit => 1, RaiseError => 1 } ) or die "Couldn't execute statement: $DBI::errstr\n";

while (1) {
    # Update orders to 'Processing' if they are at least 2 minutes old and still 'Pending'
    my $sql_processing = "UPDATE roomie_orders SET status = 'Processing' WHERE status = 'Pending' AND EXTRACT(EPOCH FROM (NOW() - created))/60 >= 2";
    $dbh->do($sql_processing);

    # Update orders to 'Sent' if they are at least 10 minutes old
    my $sql_sent = "UPDATE roomie_orders SET status = 'Sent' WHERE status = 'Processing' AND EXTRACT(EPOCH FROM (NOW() - created))/60 >= 10";
    $dbh->do($sql_sent);

    # Update orders to 'Delivered' if they are at least 15 minutes old
    my $sql_delivered = "UPDATE roomie_orders SET status = 'Delivered' WHERE status = 'Sent' AND EXTRACT(EPOCH FROM (NOW() - created))/60 >= 15";
    $dbh->do($sql_delivered);

    print "Status updates completed. Sleeping for 1 minute.\n";
    sleep(60); # Check and update statuses every 1 minute
}


