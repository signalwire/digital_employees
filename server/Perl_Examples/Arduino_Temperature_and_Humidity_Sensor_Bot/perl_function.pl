use strict;
use warnings;
use Plack::Request;
use Plack::Response;
use SignalWire::ML;
use JSON qw(decode_json);
use LWP::Simple qw(get); # Make sure you've imported 'get'

my $env       = shift;
my $req       = Plack::Request->new($env);
my $swml      = SignalWire::ML->new;

# URL of the JSON data from ThingSpeak
my $json_url  = "https://api.thingspeak.com/channels/1464062/feeds.json?results=2";

# Fetch the JSON data from the URL
my $json_text = get($json_url);
die "Could not fetch JSON data" unless defined $json_text;

# Decode the fetched JSON data
my $decoded_json = decode_json($json_text);

# Assuming you want to use the latest feed's temperature and humidity
my $latest_feed = $decoded_json->{feeds}[-1]; # Get the last element of the feeds array
my $temperature = $latest_feed->{field1};
my $humidity    = $latest_feed->{field2};

my $res = Plack::Response->new(200);
$res->content_type('application/json');

# Construct the response to include temperature and humidity
my $response_text = "The latest temperature is $temperature degrees, and the humidity is $humidity%.";

$res->body($swml->swaig_response_json({ response => $response_text }));

return $res->finalize;
