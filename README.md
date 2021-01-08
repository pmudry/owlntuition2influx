# OWL Intuition to InfluxDB parser and forwarder script
A Python script that sends OWL Intuition LC measurements to InfluxDB, using the multicast messages from OWL. Nothing fancy here, the only thing done is some XML -> JSON transformations with data conversions for Influx.

# Requirements
- Some Python version, with `xmltodict` and `progress` installed (using `pip` for example).
- An InfluxDB server with a database named `OWL` created. Credentials and database name can be changed in the code according to your needs.

Cheers

