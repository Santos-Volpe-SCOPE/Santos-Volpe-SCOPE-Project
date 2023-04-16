"""Provides code to preprocess state, county, MPO, and census tract boundaries. Functions called by upload_data_to_RDS.py.
"""
import pandas as pd
import geopandas as gpd
from geoalchemy2 import WKTElement
import helper
import math
import preprocess_utils
import os

from sqlalchemy import create_engine, text

# Establish sqlalchemy connection
sqlalchemy_conn = preprocess_utils.connect_to_sqlalchemy()


def combine_geojsons_to_single_gdf(path = None):
    """Load all .geojson files at path and concatenate into one gdf

    Args:
        path: a string specifying the path to either a folder containing .geojson files or a single .geojson file

    Returns:
        A single gdf comprised of all the .geojson files
    """
    # Get list of all geojson paths
    if(os.path.isfile(path)):
        geojson_paths = [path]
    elif(os.path.isdir(path)):
        geojson_paths = helper.get_all_filenames(path = path, pattern = '*.geojson')
    else:
        print("Something got very messed up in a call to combine_geojsons_to_single_gdf")

    # Combine all geojsons in the folder
    gdf_list = []

    # Load all geojsons into gdf_list
    for geojson_path in geojson_paths:
        single_gdf = helper.load_gdf_from_geojson(geojson_path)     # load geojson into a geodataframe
        gdf_list.append(single_gdf)

    # Concatenate the gdf
    gdf = helper.concat_pandas_dfs(gdf_list)

    return gdf


def separate_gdf_into_polygon_multipolygon(gdf: gpd.GeoDataFrame):
    """Separate a single GeoDataFrame into two GeoDataFrames, with just polgons or multipolygons respectively.

    Rows with geometry type MultiPolygon need to be separated from Polygon because they require different methods to be pushed to the database.

    Args:
        gdf: a GeoDataFrame

    Returns:
        Two GeoDataFrames, the first with only Polygon geometries, and the second with only MultiPolygon geometries.

    """

    # Rows with geometry type MultiPolygon need to be separated from Polygon because they 
    # require different methods to be pushed to the database.
    polygon_gdf = gpd.GeoDataFrame(gdf[gdf['geometry'].geom_type == "Polygon"])
    multipoly_gdf = gpd.GeoDataFrame(gdf[gdf['geometry'].geom_type == "MultiPolygon"])


    # Trying to use a function
    polygon_gdf = change_gdf_geometry_to_geom(polygon_gdf)
    multipoly_gdf = change_gdf_geometry_to_geom(multipoly_gdf)

    return polygon_gdf, multipoly_gdf

def change_gdf_geometry_to_geom(gdf: gpd.GeoDataFrame):
    """Renames the geometry column of a GeoDataFrame into geom, and does conversions I don't understand

    Args:
        gdf: a GeoDataFrame

    Returns:
        A GeoDataFrame with renamed geom column
    """
    # Change geometry column to geom
    # Also convert it to a format recognized as geometry by the database
    gdf['geom'] = gdf['geometry'].apply(lambda x: WKTElement(x.wkt, srid=4269))
    gdf.drop(columns='geometry', axis=1, inplace=True)
    return gdf






def preprocess_state_boundaries_df(path = 'Shapefiles/raw_shapefiles/states_raw'):
    """Preprocesses a GeoDataFrame containing state boundaries.

    Args:
        path: a string pointing to a shapefile folder which should contain state boundaries

    Returns:
        A processed GeoDataFrame with state boundaries
    """

    gdf = gpd.read_file(path)

    gdf = gdf.rename(columns = {"STATEFP": "STATE_ID",
                                "NAME": "STATE_NAME"})
    # gdf = gdf.drop(columns=['LSAD', 'GEO_ID', 'CENSUSAREA'])
    gdf = gdf[["STATE_ID","STATE_NAME","geometry"]]
    # Change STATE_ID column type to int
    # Needs both conversions for some reason
    gdf['STATE_ID'] = gdf['STATE_ID'].astype(str).astype(int)
    # NOTE: DOESN'T HAVE STATE_INITIAL
    return gdf

def preprocess_mpo_boundaries_df(path = 'Shapefiles/raw_shapefiles/mpo_raw'):
    """Preprocesses a GeoDataFrame containing MPO boundaries.

    Args:
        path: a string pointing to a shapefile folder which should contain MPO boundaries

    Returns:
        A processed GeoDataFrame with MPO boundaries
    """
    gdf = gpd.read_file(path)

    # Process state initial into ID and name
    gdf = gdf.rename(columns={ "STATE": "STATE_INITIAL"})
    gdf['STATE_ID'] = gdf['STATE_INITIAL'].map(preprocess_utils.d_state_initial2id)
    gdf['STATE_NAME'] = gdf['STATE_INITIAL'].map(preprocess_utils.d_state_initial2name)

    # Select necessary columns
    gdf = gdf[['STATE_ID', 'STATE_NAME', 'MPO_ID', 'MPO_NAME', 'geometry']]

    # Convert column types
    convert_column_type_dict = {"STATE_ID"            : int, 
                                "STATE_NAME"          : str, 
                                "MPO_ID"              : int, 
                                "MPO_NAME"            : str
    }
    gdf = gdf.astype(convert_column_type_dict)
    print(gdf.columns)
    return gdf

def preprocess_county_boundaries_df(path = 'Shapefiles/raw_shapefiles/counties_raw'):
    """Preprocesses a GeoDataFrame containing county boundaries.

    Args:
        path: a string pointing to a shapefile folder which should contain county boundaries

    Returns:
        A processed GeoDataFrame with county boundaries
    """

    # Goal: ['STATE_ID', 'STATE_NAME', 'COUNTY_ID', 'COUNTY_NAME', 'geometry']

    gdf = gpd.read_file(path)

    # Clean up some column names
    gdf = gdf.rename(columns={  "STATEFP": "STATE_ID", 
                                "NAME": "COUNTY_NAME",
                                "COUNTYFP" : "COUNTY_ID"
                            })

    # Convert state ID to int
    # Needs both conversions for some reason
    gdf['STATE_ID'] = gdf['STATE_ID'].astype(str).astype(int)

    # Get state name from ID
    gdf['STATE_NAME'] = gdf['STATE_ID'].map(preprocess_utils.d_state_id2name)

    # Select only necessary columns
    gdf = gdf[['STATE_ID', 'STATE_NAME', 'COUNTY_ID', 'COUNTY_NAME', 'geometry']]

    # Convert types
    convert_column_type_dict = {"STATE_ID"            : int,
                                "STATE_NAME"          : str,
                                "COUNTY_ID"           : int,
                                "COUNTY_NAME"         : str
    }
    gdf = gdf.astype(convert_column_type_dict)
    print(gdf.columns)
    return gdf

def preprocess_census_tract_boundaries_df(path = 'Shapefiles/census_tracts_by_state/'):
    """Loads a geodataframe or folder of geodataframes containing census tract boundaries, and preprocesses them.

    Can do the full folder, but uploads time out doing all the tracts at once.

    Args:
        path: a path to a geodataframe or folder of geodataframes containing census tract boundaries

    Returns:
        A processed GeoDataFrame with census tract boundaries
    """

    gdf = combine_geojsons_to_single_gdf(path)

    # Rename unclear columns
    renames = {
        'SF' : 'STATE_NAME',
        'CF' : 'COUNTY_NAME',
        'GEOID10' : 'CENSUS_TRACT_ID'
    }
    gdf.rename(columns = renames,inplace = True)

    # Get state ID from name
    gdf['STATE_ID'] = gdf['STATE_NAME'].map(preprocess_utils.d_state_name2id)

    # Convert the state ids that are NAN to 0 - these are gonna be the islands
    def convert_invalid_state_ids_to_0(row):
        if row['STATE_ID'] is None or math.isnan(row['STATE_ID']):
            return 0
        else:
            return row['STATE_ID']
    gdf['STATE_ID'] = gdf.apply(lambda row: convert_invalid_state_ids_to_0(row), axis=1)

    # Select only necessary columns
    gdf = gdf[['STATE_ID', 'STATE_NAME', 'COUNTY_NAME', 'CENSUS_TRACT_ID', 'geometry']]
    # Make sure column types are correct
    column_type_dict = {"STATE_ID"                      : int, 
                        "STATE_NAME"                    : str, 
                        "CENSUS_TRACT_ID"               : int, 
                        "COUNTY_NAME"                   : str,  
    }
    gdf = gdf.astype(column_type_dict)

    # Remove the str "County" from each entry in the county column
    def remove_county_str(row):
            return row['COUNTY_NAME'].rsplit(' ', 1)[0]
    gdf['COUNTY_NAME'] = gdf.apply(lambda row: remove_county_str(row), axis=1)

    # Don't know why the data started out like this
    state_id = gdf['STATE_ID'][0]

    # Add County ID to each row
    def set_county_id(row):
        # If in a state, get the county name
        if state_id != 0:
            county_name = row['COUNTY_NAME']
            # If county name is ', change it to ''
            if "'" in county_name:
                county_name = county_name.replace("'", "''")
            sql = text(""" SELECT * FROM "boundaries_county" WHERE "STATE_ID" = {} AND "COUNTY_NAME" = '{}' LIMIT 1 """.format(state_id, county_name))
            county_boundaries = gpd.read_postgis(sql, con=sqlalchemy_conn)
            if not county_boundaries.empty:
                county_id = county_boundaries['COUNTY_ID'][0]
            else:
                county_id = None
        else:
            county_id = None   
        return county_id

    gdf['COUNTY_ID'] = gdf.apply(lambda row: set_county_id(row), axis=1)

    # Join census tract data with MPO data
    if state_id != 0: 
        # Get MPO boundaries for this state
        sql = text(""" SELECT * FROM "boundaries_mpo" WHERE "STATE_ID" = {} """.format(state_id))
        mpo_boundaries = gpd.read_postgis(sql, con=sqlalchemy_conn)

        # Perform spatial join between MPO boundaries and county boundaries
        gdf = gdf.to_crs(4269)
        gdf = gpd.sjoin(gdf,mpo_boundaries, predicate='intersects', how='left')

        columns = ['STATE_ID_left', 'STATE_NAME_left', 'COUNTY_ID', 'COUNTY_NAME', 'MPO_ID', 'MPO_NAME', 'CENSUS_TRACT_ID', 'geometry']
        gdf = gdf[columns]

        # Rename some columns
        renames = {
            'STATE_ID_left' : 'STATE_ID',
            'STATE_NAME_left' : 'STATE_NAME',
        }
        gdf.rename(columns = renames,inplace = True)
    else:
        # If state id is 0, state name is None
        def set_to_none(row):
            return None
        gdf['MPO_ID'] = gdf.apply(lambda row: set_to_none(row), axis=1)
        gdf['MPO_NAME'] = gdf.apply(lambda row: set_to_none(row), axis=1)
        columns = ['STATE_ID', 'STATE_NAME', 'COUNTY_ID', 'COUNTY_NAME', 'MPO_ID', 'MPO_NAME', 'CENSUS_TRACT_ID', 'geometry']
        gdf = gdf[columns]

    # Join census tract data with justice40 stats
    justice40 = helper.load_df_from_csv(path = "Justice40/justice_40_communities_clean.csv", low_memory = False)
    gdf = pd.merge(gdf,justice40[['CENSUS_TRACT_ID','IDENTIFIED_AS_DISADVANTAGED']],on='CENSUS_TRACT_ID', how='left')

    return gdf

def preprocess_HIN_df(gdf: gpd.GeoDataFrame):
    """Waiting on Sam and Lilo to provide this
    """

    return gdf


if __name__ == "__main__":
    # A bunch of stuff, this file should not really be run as main other than for testing

    # gdf = combine_geojsons_to_single_gdf(path = "_Shapefiles/state.geojson")
    # gdf = preprocess_state_boundaries_df(gdf)
    # polygon_gdf, multipolygon_gdf = separate_gdf_into_polygon_multipolygon(gdf)

    # gdf = combine_geojsons_to_single_gdf(path = "_Shapefiles/mpo_boundaries_by_state/")
    # gdf = preprocess_mpo_boundaries_df(gdf)
    # polygon_gdf, multipolygon_gdf = separate_gdf_into_polygon_multipolygon(gdf)

    # gdf = combine_geojsons_to_single_gdf(path = "_Shapefiles/county_by_state/")
    # gdf = preprocess_county_boundaries_df(gdf)
    # polygon_gdf, multipolygon_gdf = separate_gdf_into_polygon_multipolygon(gdf)


    # gdf = combine_geojsons_to_single_gdf(path = "_Shapefiles/census_tracts_by_state/census_tract_AK.geojson")
    gdf = preprocess_census_tract_boundaries_df('Shapefiles/census_tracts_by_state/census_tract_AK.geojson')
    # print(gdf.columns)
    polygon_gdf, multipolygon_gdf = separate_gdf_into_polygon_multipolygon(gdf)
    # print("saving modified census tracts to file")
    # gdf.to_file('Shapefiles/clean_geojsons/census_tracts.geojson', driver='GeoJSON')

    # helper.write_geodataframe_to_file(gdf, "filename")

    # gdf = combine_geojsons_to_single_gdf(path = "Shapefiles/HIN/alameda_000_threshold_hin.geojson")
    # gdf = preprocess_HIN_df(gdf)
    # polygon_gdf, multipolygongdf = separate_gdf_into_polygon_multipolygon(gdf)


