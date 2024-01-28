import pandas as pd
import geopandas as gpd

# This script is heavily inspired by https://github.com/erinleeryan/cville_airbnb/blob/fe5500c2c9236623e7ba0f8094731cdcd5f51811/mapping_code/map_cville_airbnbs.ipynb

sales_csv_url = 'https://opendata.arcgis.com/api/v3/datasets/489adf140c174534a544136dc3e4cb90_3/downloads/data?format=csv&spatialRefId=4326&where=1%3D1'
airbnb_list = pd.read_csv('../../data.csv')
airbnb_list.dropna(subset=['lat', 'lon', 'street number', 'street name'], inplace=True)
airbnb_list['street name'] = airbnb_list['street name'].str.upper()

# Group by street name and street number.
airbnb_list.drop_duplicates(subset=['street name', 'street number'], inplace=True)

# Load the Fifeville geojson.
fifeville_geojson = gpd.read_file('fifeville.geojson')

# Get all airbnbs in Fifeville.
airbnb_list_fifeville = gpd.GeoDataFrame(airbnb_list, geometry=gpd.points_from_xy(airbnb_list.lon, airbnb_list.lat, crs="WGS84"))
airbnb_list_fifeville = gpd.sjoin(airbnb_list_fifeville, fifeville_geojson, how='inner')

# Print the number of airbnbs in Fifeville.
print(f"Number of Airbnbs (by address) in Fifeville: {len(airbnb_list_fifeville)}")

sales_list = pd.read_csv(sales_csv_url)
sales_list['SaleDate'] = pd.to_datetime(sales_list['SaleDate'])

# Filter down to only the most recent sale for each property. Sort sale amount descending. If there were multiple sales
# on the same day, use the sale with the highest sale amount (some have duplicates with a zero sale amount).
sales_list = sales_list.sort_values(by=['ParcelNumber', 'SaleDate', 'SaleAmount'], ascending=[True, False, False])
sales_list = sales_list.drop_duplicates(subset=['ParcelNumber'])

# Filter down to only sales starting with 2000.
sales_list = sales_list[sales_list['SaleDate'] >= '2000-01-01']

# Merge the Airbnb list and the sales list on the street number and street name.
sales_and_airbnb = pd.merge(airbnb_list, sales_list, how='inner', left_on=['street number', 'street name'],
                            right_on=['StreetNumber', 'StreetName'])

# Convert the standard dataframe to a geodataframe.
sales_and_airbnb = gpd.GeoDataFrame(sales_and_airbnb, geometry=gpd.points_from_xy(sales_and_airbnb.lon,
                                                                                  sales_and_airbnb.lat, crs="WGS84"))

# Filter the list of sales to only those in Fifeville.
fifeville_sales = gpd.sjoin(sales_and_airbnb, fifeville_geojson, how='inner')

# Use only the columns we care about. Address, sale date, and sale price.
fifeville_sales = fifeville_sales[['street name', 'street number', 'SaleDate', 'SaleAmount']]

# Sort by street name, then street number.
fifeville_sales = fifeville_sales.sort_values(by=['street name', 'street number'])

# Write a CSV of the sales in Fifeville.
fifeville_sales.to_csv('fifeville-sales.csv', index=False)
