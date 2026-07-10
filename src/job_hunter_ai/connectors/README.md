# Connectors

Each connector should do one thing well: fetch source data and emit raw records.

Connector code should avoid business decisions like ranking or ghost detection.
Those decisions belong downstream and must remain evaluable.

