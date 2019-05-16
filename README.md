# 3CX to InfluxDB

This script aggregates call data records (CDRs) by SIP-Trunk and destination.
The result is written to [InfluxDB](https://www.influxdata.com/products/influxdb-overview/) for further processing like drawing fancy graphs in [Grafana](https://grafana.com/).

The records are aggregated by:
* Direction (incoming/outgoing/internal)
* Gateway (the SIP-Trunk)
* Outgoing area code

This script has been tested with 3CX version 15.5

## Dependencies

Install the required Debian/Ubuntu packages:

```
apt-get install python3-postgresql python3-yaml python3-requests
```


## Configuration

Adjust the `call_logs.yml` to fit your needs.


## Running

Just start the script and pass the path to the configuration file:

```
./call_logs.py call_logs.yml
```
