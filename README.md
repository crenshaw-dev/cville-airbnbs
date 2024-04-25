# Charlottesville Airbnb Data

## What?

Information about Airbnbs in Charlottesville, with a nice [map](https://crenshaw-dev.github.io/cville-airbnbs/).

Map pin color key:
* Green: address known, registered with the city for 2023
* Red: address known, not registered with the city for 2023
* Grey: address unknown

## Why?

Data is good.

## How?

I run [main.py](main.py) occasionally. That updates [data.csv](data.csv). The script pulls listings from Airbnb's API by
filtering on the rough rectangle around Charlottesville and then filtering by city name.

The coordinates from Airbnb are obfuscated. Where possible, I manually inspect the Airbnb listing and try to find an
address. Where I find an address, I also update the coordinates.

Many of the addresses were copied from [Erin's CSV](https://github.com/erinleeryan/cville_airbnb/blob/fe5500c2c9236623e7ba0f8094731cdcd5f51811/data/cville_airbnb_locations.csv).

The script is designed to preserve the manually updated coordinates and address.

Listings come and go from the API results. Where the `active` column contains `true`, the most recent API scrape
contained the listing. Where the `active` column is `false`, the listing was once present in the API response but is no
longer. Some listings appear/disappear frequently. Use the "blame" feature in GitHub to view the history of a certain 
listing.

The "2023 approved" column contains "true" if the address is known to have been approved in 2023. The list of approved
addresses is in [2023_approved.csv](2023_approved.csv). It's joined to data.csv whenever main.py is run.

## Roadmap

* Make it easy to swap in a different city. This would mean making the 2023_approved.csv file optional and more general.
  Maybe the approval status should be added by a separate script.
* Make the script handle missing CSVs more gracefully. Right now the script fails if CSV isn't present.
* Get date of most recent review, so we have a sense of whether the listing is active.
* Note in data whether the listing falls in a zoning area that requires registration. (This may be difficult if we don't have GIS data for the new zoning areas yet.)
* Generate a human-readable report from the data.
* Add arbitrary "notes" column.
* Generate a report describing single addresses with multiple listings.
