# Charlottesville Airbnb Data

## What?

Information about Airbnbs in Charlottesville.

## Why?

Data is good.

## How?

I run [main.py](main.py) occasionally. That updates [data.csv](data.csv). The script pulls listings from Airbnb's API by
filtering on the rough rectangle around Charlottesville and then filtering by city name.

The coordinates from Airbnb are obfuscated. Where possible, I manually inspect the Airbnb listing and try to find an
address. Where I find an address, I also update the coordinates.

The script is designed to preserve the manually updated coordinates and address.

Listings come and go from the API results. Where the `active` column contains `true`, the most recent API scrape
contained the listing. Where the `active` column is `false`, the listing was once present in the API response but is no
longer. Some listings appear/disappear frequently. Use the "blame" feature in GitHub to view the history of a certain 
listing.
