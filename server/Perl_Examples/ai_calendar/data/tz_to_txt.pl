#!/usr/bin/perl

use strict;
use warnings;
use XML::Simple;
use Data::Dumper;

# Assuming your XML file is named 'timezones.xml'
my $file_name = 'timezones.conf.xml';

# Create a new XML::Simple object
my $xml = new XML::Simple;

my $data = $xml->XMLin($file_name);


# Access the timezones and iterate over them
foreach my $zone ( keys %{$data->{timezones}->{zone}} ) {
    print $zone . "\n";
}
