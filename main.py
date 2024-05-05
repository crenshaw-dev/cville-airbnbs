import base64
import csv
import json
import operator
import re
import time
import traceback

import folium
import pandas as pd
import geopandas as gpd
import requests
from matplotlib import pyplot as plt

url = "https://www.airbnb.com/api/v3/StaysSearch?operationName=StaysSearch&locale=en&currency=USD"

headers = {
    "Origin": "https://www.airbnb.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "X-Airbnb-API-Key": "d306zoyjsyarp7ifhu67rjxn52tv0t20",
}


class Rectangle:
    neLat: float
    neLng: float
    swLat: float
    swLng: float

    def __init__(self, ne_lat, ne_lng, sw_lat, sw_lng):
        self.neLat = ne_lat
        self.neLng = ne_lng
        self.swLat = sw_lat
        self.swLng = sw_lng

    @property
    def width(self):
        return abs(self.neLat - self.swLat)

    @property
    def height(self):
        return abs(self.neLng - self.swLng)

    def __str__(self):
        return f'Rectangle({self.neLat}, {self.neLng}, {self.swLat}, {self.swLng})'


# cleverly derived by just trying to get kinda close.
rectangle_around_cville = Rectangle(
    38.077262603677,
    -78.44334735313731,
    38.007180818958936,
    -78.52890101049371,
)


def get_rectangle_subdivisions(rect: Rectangle, subdivisions: int):
    lat_dist_per_subdivision = rect.width / subdivisions
    lng_dist_per_subdivision = rect.height / subdivisions
    # This outer loop iterates over the columns of subdivisions, i.e. left-to-right on the map.
    for lat_i in range(subdivisions):
        # Subtract because the latitude decreases as we go to the right.
        current_ne_lat = rect.neLat - (lat_dist_per_subdivision * lat_i)
        # This inner loop iterates over the rows of subdivisions, i.e. bottom-to-top on the map.
        for lng_i in range(subdivisions):
            # Again, subtract because the longitude decreases as we go down.
            current_ne_lng = rect.neLng - (lng_dist_per_subdivision * lng_i)

            # Calculate SW corner entirely based on NE corner and subdivision size.
            current_sw_lat = current_ne_lat - lat_dist_per_subdivision
            current_sw_lng = current_ne_lng - lng_dist_per_subdivision

            yield Rectangle(current_ne_lat, current_ne_lng, current_sw_lat, current_sw_lng)


def get_request_body(rect: Rectangle):
    return {'operationName': 'StaysSearch', 'variables': {
        'staysSearchRequest': {'requestedPageType': 'STAYS_SEARCH', 'metadataOnly': False, 'searchType': 'AUTOSUGGEST',
                               'treatmentFlags': ['feed_map_decouple_m11_treatment',
                                                  'stays_search_rehydration_treatment_desktop',
                                                  'stays_search_rehydration_treatment_moweb',
                                                  'upfront_pricing_enabled'],
                               'rawParams': [{'filterName': 'adults', 'filterValues': ['0']},
                                             {'filterName': 'cdnCacheSafe', 'filterValues': ['false']},
                                             {'filterName': 'children', 'filterValues': ['0']},
                                             {'filterName': 'datePickerType', 'filterValues': ['flexible_dates']},
                                             {'filterName': 'flexibleTripDates',
                                              'filterValues': ['january', 'february', 'march', 'april', 'may', 'june',
                                                               'july', 'august', 'september', 'october', 'november',
                                                               'december']},
                                             {'filterName': 'flexibleTripLengths', 'filterValues': ['one_week']},
                                             {'filterName': 'infants', 'filterValues': ['0']},
                                             {'filterName': 'itemsPerGrid', 'filterValues': ['18']},
                                             {'filterName': 'pets', 'filterValues': ['0']},
                                             {'filterName': 'query', 'filterValues': ['Charlottesville, VA']},
                                             {'filterName': 'refinementPaths', 'filterValues': ['/homes']},
                                             {'filterName': 'screenSize', 'filterValues': ['large']},
                                             {'filterName': 'tabId', 'filterValues': ['home_tab']},
                                             {'filterName': 'version', 'filterValues': ['1.8.3']},
                                             {'filterName': 'neLat', 'filterValues': [str(rect.neLat)]},
                                             {'filterName': 'neLng', 'filterValues': [str(rect.neLng)]},
                                             {'filterName': 'swLat', 'filterValues': [str(rect.swLat)]},
                                             {'filterName': 'swLng', 'filterValues': [str(rect.swLng)]},
                                             ], 'maxMapItems': 9999},
        'includeMapResults': True, 'isLeanTreatment': False}, 'extensions': {
        'persistedQuery': {'version': 1,
                           'sha256Hash': '81c26682ee29edbbf0cd22db48b9b01b5686c4cb43f2c98758395a0cdac50700'}}}


def get_listing_request_url(listing_id: str):
    id = ("StayListing:" + listing_id).encode('ascii')
    id = base64.b64encode(id).decode('ascii')
    return 'https://www.airbnb.com/api/v3/StaysPdpSections/036017be486462ae7b1e9d9916e4dea14951cf33a75c242b92d267b468d97bfd?operationName=StaysPdpSections&locale=en&currency=USD&variables={"id":"' + id + '","pdpSectionsRequest":{"adults":"1","amenityFilters":null,"bypassTargetings":false,"categoryTag":null,"causeId":null,"children":null,"disasterId":null,"discountedGuestFeeVersion":null,"displayExtensions":null,"federatedSearchId":null,"forceBoostPriorityMessageType":null,"infants":null,"interactionType":null,"layouts":["SIDEBAR","SINGLE_COLUMN"],"pets":0,"pdpTypeOverride":null,"photoId":null,"preview":false,"previousStateCheckIn":null,"previousStateCheckOut":null,"priceDropSource":null,"privateBooking":false,"promotionUuid":null,"relaxedAmenityIds":null,"searchId":null,"selectedCancellationPolicyId":null,"selectedRatePlanId":null,"splitStays":null,"staysBookingMigrationEnabled":false,"translateUgc":null,"useNewSectionWrapperApi":false,"sectionIds":null,"checkIn":null,"checkOut":null,"p3ImpressionId":"p3_1714337066_efTKaazDV6pyCgEf"}}&extensions={"persistedQuery":{"version":1,"sha256Hash":"036017be486462ae7b1e9d9916e4dea14951cf33a75c242b92d267b468d97bfd"}}'


def rating_from_string(rating: str) -> str:
    if rating is None:
        return ""

    match = re.search(r'\((\d+)\)$', rating)
    if match is None or len(match.groups()) < 1:
        return ""

    return match.group(1)


def data_from_response(r: requests.Response) -> dict[str, dict[str, str]]:
    r_json = r.json()
    try:
        results = r_json["data"]["presentation"]["staysSearch"]["results"]
        data = {
            result["listing"]["id"]: {
                "city": result["listing"]["city"],
                "lat": result["listing"]["coordinate"]["latitude"],
                "lon": result["listing"]["coordinate"]["longitude"],
                "type": result["listing"]["roomTypeCategory"],
                "title": result["listing"]["name"],
                "id": result["listing"]["id"],
                "ratings": rating_from_string(result["listing"]["avgRatingLocalized"] if "avgRatingLocalized" in result["listing"] else None),
            }
            for result in results["searchResults"]
            if "listing" in result and result["listing"]["city"] == "Charlottesville"
        }

        if "paginationInfo" in results and "nextPageCursor" in results["paginationInfo"]:
            next_page_cursor = results["paginationInfo"]["nextPageCursor"]
        else:
            next_page_cursor = None
    except KeyError:
        print("Unexpected JSON format:")
        print(traceback.format_exc())
        print(json.dumps(r_json))
        exit(1)

    return data, next_page_cursor


# Break the map into subdivisions, so we avoid the per-search limit. 2 subdivisions means 2 columns and 2 rows, so
# actually 4 rectangles. I need a better name for this variable.
subdivisions = 2

data: dict[str, dict[str, str]] = {}

n = 1
for rect in get_rectangle_subdivisions(rectangle_around_cville, subdivisions):
    print(f"on rect {n} of {subdivisions ** 2}")
    n += 1
    r = requests.post(url, json=get_request_body(rect), headers=headers)
    first_data, next_page_cursor = data_from_response(r)
    # Merge the dictionaries. We're not concerned with which one wins.
    data = data | first_data

    while next_page_cursor is not None:
        body = get_request_body(rect)
        body["variables"]["staysSearchRequest"]["cursor"] = next_page_cursor

        r = requests.post(url, json=body, headers=headers)
        new_data, next_page_cursor = data_from_response(r)
        data = data | new_data
        print("sleeping a sec")
        time.sleep(0.5)


CSV_ROWS = ["id", "lat", "lon", "type", "title", "street number", "street name", "2023 approved", "last seen", "ratings", "host id", "host name", "owner name", 'count by host id', 'count by owner name', "comments"]

last_seen_date = time.strftime("%Y-%m-%d")

for k in data:
    # Give everything from the API an empty address (we'll use the one from the CSV if it's there).
    data[k]["street number"] = ""
    data[k]["street name"] = ""
    # Remove newlines from the title.
    data[k]["title"].replace("\\n", " ")
    # Add today's date/time as a string to the data.
    data[k]["last seen"] = last_seen_date

# Load in existing CSV. This could probably be done with pandas instead.
with open('data.csv', encoding='utf-8', newline='') as old_data:
    reader = csv.DictReader(old_data)
    for row in reader:
        # It's important to convert the listing ID to a string, because that's the way the API loads it.
        row["id"] = str(row["id"])
        listing_id = row["id"]
        if listing_id in data:
            # The item in this row exists in the data we just pulled from the API, so we'll consider this listing active
            row["last seen"] = last_seen_date
            # Also update the title and ratings, in case those have changed.
            row["title"] = data[listing_id]["title"]
            row["ratings"] = data[listing_id]["ratings"]
            # For all other columns, we'll keep the original values. This allows us to, for example, add addresses and
            # more accurate lat/lon data without it being overwritten on the next update.
        # Either add or update the data from the API with the data from the CSV.
        data[listing_id] = row

        # If the listing doesn't have a host ID or name, we'll add it to the data.
        if "host id" not in data[listing_id] or data[listing_id]["host id"] == "" or "host name" not in data[listing_id] or data[listing_id]["host name"] == "":
            listing_url = get_listing_request_url(listing_id)
            r = requests.get(listing_url, headers=headers)
            listing_data = r.json()

            detail_page = listing_data["data"]["presentation"]["stayProductDetailPage"]
            if "sections" in detail_page and detail_page["sections"] is not None:
                # Only update if it hasn't been set yet.
                if "host id" not in data[listing_id] or data[listing_id]["host id"] == "":
                    sections = listing_data["data"]["presentation"]["stayProductDetailPage"]["sections"]["sbuiData"]["sectionConfiguration"]["root"]["sections"]
                    for section in sections:
                        if section["sectionId"] == "HOST_OVERVIEW_DEFAULT":
                            host_id = section["loggingData"]["eventData"]["pdpContext"]["hostId"]
                            break
                    data[listing_id]["host id"] = host_id

                if "host name" not in data[listing_id] or data[listing_id]["host name"] == "":
                    sections = listing_data["data"]["presentation"]["stayProductDetailPage"]["sections"]["sections"]
                    for section in sections:
                        if section["sectionId"] == "MEET_YOUR_HOST":
                            host_name = section["section"]["cardData"]["name"]
                            break
                    data[listing_id]["host name"] = host_name
            # Sleep for a bit to avoid rate limiting.
            print("got host ID, sleeping a sec")
            time.sleep(0.1)

# Sort by listing ID, so we get a somewhat deterministic output.
list_data = sorted(data.values(), key=operator.itemgetter("id"))

# Convert list_data to a pandas dataframe. All fields should be treated as strings.
df = pd.DataFrame(list_data, columns=CSV_ROWS)

# Load in the 2023_approved.csv file.
approved_df = pd.read_csv('2023_approved.csv')
# Set "2023 approved" to true for all rows in the approved_df.
approved_df['2023 approved'] = True
# First, coerce the street number to a string in both dataframes.
df['street number'] = df['street number'].astype(str)
approved_df['street number'] = approved_df['street number'].astype(str)

# Join the two dataframes together on the street number and street name, and fill in the 2023 approved column with
# False for any rows that don't exist in the approved_df.
df = df.merge(approved_df, how='left', on=['street number', 'street name'], suffixes=('_delete', ''))
# Drop the _delete column.
df.drop(columns=['2023 approved_delete'], inplace=True)

df['2023 approved'].fillna(False, inplace=True)

# Convert the 2023 approved column to a lowercase string.
df['2023 approved'] = df['2023 approved'].astype(str).str.lower()

# Download CSV of parcels and owners
parcels = pd.read_csv('https://opendata.arcgis.com/api/v3/datasets/0e9946c2a77d4fc6ad16d9968509c588_72/downloads/data?format=csv&spatialRefId=4326&where=1%3D1')

# Remove columns where the Unit field is not null, we don't match to that granularity.
parcels = parcels[parcels['Unit'].isnull()]

# Add column of uppercase street names to listings
df['street name upper'] = df['street name'].str.upper()

# Join parcels and listings on street name upper and street number, keeping all listings.
df = pd.merge(df, parcels, how='left', left_on=['street number', 'street name upper'], right_on=['StreetNumber', 'StreetName'])

# If there's an & in the OwnerName, remove everything except the part before the " &"
df['OwnerName'] = df['OwnerName'].str.replace(r'(.+) & .+', r'\1', regex=True)

# If there's a "Last, First <initial>" followed by a space and then the exact same pattern, remove the second pattern.
# We'll assume that's two names.
df['OwnerName'] = df['OwnerName'].str.replace(r'(\w+), (\w+ \w{2,}) (\w+), (\w+ \w{2,})', r'\1, \2', regex=True)

# If OwnerName follows the pattern "LAST, FIRST <initial>", then convert it to "First Last", capitalizing only the first letter of the first name and last name
df['owner name'] = df['OwnerName'].str.replace(r'^(\w+), (\w+( \w{2,})?)( [A-Z])?(, JR)?$', r'\2 \1', regex=True).str.title()

# If the OwnerName ends with " Llc", replace it with " LLC"
df['owner name'] = df['owner name'].str.replace(r' Llc$', ' LLC', regex=True)

# Set the "owner" column to the "OwnerName" column, but only if the "owner" column is null. We don't want to overwrite any existing owner names.
df['owner name'] = df['owner name'].fillna(df['OwnerName'])

# Count the number of listings by host ID and owner name.
df['count by host id'] = df[df['host id'].notna() & (df['host id'] != '')].groupby('host id')['host id'].transform('count')
df['count by owner name'] = df[df['owner name'].notna() & (df['owner name'] != '')].groupby('owner name')['owner name'].transform('count')

# Drop all but these columns.
df = df[CSV_ROWS]

# Write the dataframe to a CSV.
df.to_csv('data.csv', index=False)

# Mapping code adapted (basically straight-up copied) from
# https://github.com/erinleeryan/cville_airbnb/blob/fe5500c2c9236623e7ba0f8094731cdcd5f51811/mapping_code/map_cville_airbnbs.ipynb
cville_streets = gpd.read_file('https://opendata.arcgis.com/datasets/e5a3e226dd9d4399aa014858f489852a_60.geojson')

# To avoid conflicting with the GeoDataFrame's type column, rename the type column in the CSV to rental_type.
df.rename(columns={"type": "rental_type"}, inplace=True)

airbnb_to_map = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat, crs="WGS84"))

fig, ax = plt.subplots(figsize=(30, 30))
cville_streets.plot(ax=ax, color='0.8')
airbnb_to_map.plot(ax=ax, column='rental_type', legend=True, legend_kwds={'fontsize': 'x-large'})
plt.axis('off')

m = folium.Map(location=[38.03185, -78.477], zoom_start=14, tiles='cartodb positron')

geo_df_list = [[point.xy[1][0], point.xy[0][0]] for point in airbnb_to_map.geometry]

i = 0
for coordinates in geo_df_list:
    if airbnb_to_map["street number"].iloc[i] == "":
        location = f"""<a href="https://www.google.com/maps/search/{airbnb_to_map.lat.iloc[i]},{airbnb_to_map.lon.iloc[i]}">{airbnb_to_map.lat.iloc[i]},{airbnb_to_map.lon.iloc[i]} (approximate)</a>"""
        icon_type = "home"
        type_color = "gray"
        icon_prefix = "fa"
    else:
        address = f"{airbnb_to_map['street number'].iloc[i]} {airbnb_to_map['street name'].iloc[i]}"
        location = f"""<a href="https://www.google.com/maps/place/{address}+Charlottesville+VA/">{address}</a>"""
        if airbnb_to_map["2023 approved"].iloc[i] == "true":
            type_color = "green"
        else:
            type_color = "red"
        icon_type = "home"
        icon_prefix = "fa"

    displ_tooltip = f"""<ul><li>{location}</li>
                     <li><a href="https://airbnb.com/rooms/{airbnb_to_map.id[i]}">Listing ({airbnb_to_map.rental_type[i]})</a></li>
                    </ul>"""

    m.add_child(folium.Marker(location=coordinates,
                              icon=folium.Icon(color=type_color, icon=icon_type, prefix=icon_prefix),
                              popup=displ_tooltip))
    i = i + 1

m.save("docs/index.html")
