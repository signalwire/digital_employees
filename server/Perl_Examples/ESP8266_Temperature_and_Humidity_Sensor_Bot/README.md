# Sensor-ai
ESP8266, thingspeak.com, DHT11 sensor data interacting with SignalWire's AI technology

## [sensor_data Function](https://github.com/Len-PGH/Sensor-ai/blob/main/perl-function.pl)

Perl modules:
- `LWP::Simple` for fetching data from the web,
- `JSON` for parsing JSON data,
- `Plack` for creating a simple web application, and
- `SignalWire::ML` for constructing responses (assuming this is part of your application's architecture).

## Step-by-Step Guide

### 1. Setting Up Your Perl Script

First, ensure you have Perl installed on your system along with the necessary modules. You can install missing modules using CPAN:

```shell
cpan install LWP::Simple JSON Plack
```

Start by importing the required modules at the beginning of your script:

```perl
use strict;
use warnings;
use Plack::Request;
use Plack::Response;
use SignalWire::ML;
use JSON qw(decode_json);
use LWP::Simple qw(get);
```

### 2. Fetching JSON Data

Define the URL of the JSON data you intend to fetch. In this example, we're using ThingSpeak's API to get the latest two entries of environmental data from a specific channel:

```perl
my $json_url = "https://api.thingspeak.com/channels/1464062/feeds.json?results=2";
```

Use `LWP::Simple`'s `get` function to fetch the data:

```perl
my $json_text = get($json_url);
die "Could not fetch JSON data" unless defined $json_text;
```

### 3. Processing the JSON Data

Decode the fetched JSON text into a Perl data structure using the `JSON` module:

```perl
my $decoded_json = decode_json($json_text);
```

Extract the necessary data from the decoded JSON. For instance, to get the temperature and humidity from the latest feed entry:

```perl
my $latest_feed = $decoded_json->{feeds}[-1];
my $temperature = $latest_feed->{field1};
my $humidity    = $latest_feed->{field2};
```

### 4. Constructing the HTTP Response

Create a new response object with `Plack::Response` and set the content type to `application/json`:

```perl
my $res = Plack::Response->new(200);
$res->content_type('application/json');
```

Construct the response body to include the temperature and humidity information:

```perl
my $response_text = "The latest temperature is $temperature degrees, and the humidity is $humidity%.";
$res->body($swml->swaig_response_json({ response => $response_text }));
```

### 5. Finalizing the Response

Return the finalized response from your application:

```perl
return $res->finalize;
```
