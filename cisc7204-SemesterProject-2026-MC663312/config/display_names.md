# Display names

Airport display names combine the project's OurAirports reference with the BTS origin-city field. Codes remain the analytical keys; unknown or historical entries are labelled rather than guessed. PBI uses Palm Beach International Airport. These small lookup tables support name/city/code search without loading the full flight panel in the UI.

Carrier names use BTS and FAA code lists. US Airways and Virgin America are historical carriers in the study period; labels are descriptive names, not claims about present operations.

Sources: https://www.bts.gov/topics/airlines-and-airports/airline-codes and https://aspmhelp.faa.gov/index/ASQP__Carrier_Codes_and_Names.html . Airport reference provenance is recorded in data/README.md.
