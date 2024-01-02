import csv
import json
import operator
import time
import traceback

import requests

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
                "hostId": result["listing"]["primaryHostPassport"]["userId"] if "primaryHostPassport" in result[
                    "listing"] and result["listing"]["primaryHostPassport"] is not None else "",
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

CSV_ROWS = ["id", "hostId", "lat", "lon", "type", "title", "active", "address"]

for k in data:
    # Mark everything from the API response as active
    data[k]["active"] = "true"
    # Give everything from the API an empty address (we'll use the one from the CSV if it's there).
    data[k]["address"] = ""
    # Remove newlines from the title.
    data[k]["title"].replace("\\n", " ")

# Load in existing CSV.
with open('data.csv', encoding='utf-8', newline='') as old_data:
    reader = csv.DictReader(old_data)
    for row in reader:
        # It's important to convert the listing ID to a string, because that's the way the API loads it.
        row["id"] = str(row["id"])
        listing_id = row["id"]
        if listing_id in data:
            # The item in this row exists in the data we just pulled from the API, so we'll consider this listing active
            row["active"] = "true"
            # Also update the title, in case that has changed.
            row["title"] = data[listing_id]["title"]
            # For all other columns, we'll keep the original values. This allows us to, for example, add addresses and
            # more accurate lat/lon data without it being overwritten on the next update.

        else:
            # The listing was in the CSV, but not in the API responses. Mark it as inactive.
            row["active"] = "false"
        # Either add or update the data from the API with the data from the CSV.
        data[listing_id] = row

# Sort by listing ID, so we get a somewhat deterministic output.
# Most listings don't have a host, but still sort by those first in case it exists.
list_data = sorted(data.values(), key=operator.itemgetter("id", "hostId"))

with open('data.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(CSV_ROWS)
    for d in list_data:
        w.writerow([d["id"], d["hostId"], d["lat"], d["lon"], d["type"], d["title"], d["active"], d["address"]])
