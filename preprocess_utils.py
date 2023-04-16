"""This file is to hold a bunch of useful helper functions for preprocessing so that they can be imported into any file.
"""
import helper
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, Connection

states_df = helper.load_df_from_csv(path='states.csv', low_memory = False)
# Dictionaries to convert the STATE_INITIAL to STATE_ID & STATE_NAME
d_state_initial2id = dict(zip(states_df.state, states_df.id))
d_state_initial2name = dict(zip(states_df.state, states_df.name))
d_state_id2name = dict(zip(states_df.id, states_df.name))
d_state_name2id = dict(zip(states_df.name, states_df.id))
d_state_name2initial = dict(zip(states_df.name, states_df.state))

# A bunch of standard column types
_convert_column_type_dict = {"YEAR"             : int,
                            "IS_FATAL"          : int, 
                            "SEVERITY"          : int, 
                            "IS_PED"            : int,  
                            "IS_CYC"            : int,
                            "WEATHER_COND"      : str, 
                            "LIGHT_COND"        : str, 
                            "ROAD_COND"         : str, 
                            "ROAD_NAME"         : str, 
                            "IS_INTERSECTION"   : int,
                            "LAT"               : float,
                            "LON"               : float,
                            }



def convert_columns_to_proper_types(df:pd.DataFrame) -> pd.DataFrame:
    """Convert columns to the proper types.

    Types are defined above and should not be changed.

    Args:
        df: a `pd.DataFrame`, with latitude and longitude in columns named "LAT" and "LON"

    Returns:
        A `pd.DataFrame` with columns of the proper types
    """
    # Drop all lat lon that are not numeric
    df = df[pd.to_numeric(df['LAT'], errors='coerce').notnull()]
    df = df[pd.to_numeric(df['LON'], errors='coerce').notnull()]

    # Static column type dict defined above
    df = df.astype(_convert_column_type_dict)

    return df

def remove_invalid_lat_lon(df:pd.DataFrame) -> pd.DataFrame:
    """Takes a preprocessed `pd.DataFrame` and remove points with invalid latitude and longitudes.

    Args:
        df: a `pd.DataFrame` with latitude and longitude in columns named "LAT" and "LON"

    Returns:
        A `pd.DataFrame` with invalid lat/lon removed
    """

    # If latitude is outside of -90 to 90 or longitude is outside of -180 to 180, don't keep it
    # NOTE: -180 longitude is *technically* not a valid longitude, as it is identical to 180 longitude.
    # Left the -180 in because it's still sorta valid, and would only be an issue for Russia, Fiji, or Antarctica.
    df = df.loc[(df["LAT"] >=-90) & (df["LAT"] <=90) &
                      (df["LON"] >=-180) & (df["LON"] <=180)]

    # Drop NAs
    df = df.dropna(subset=['LAT', 'LON'], how='all')

    return df

def create_point_column_from_lat_lon(df: pd.DataFrame, flip_lon_sign = False) -> gpd.GeoDataFrame:
    """Generate a Point geometry column using latitude and longitude.

    We want to use this because then we can use shapely to determine whether each of the points

    Args:
        df: a `pd.DataFrame` of data to be converted
        flip_lin_sign: a boolean defining whether to flip the sign of the longitude. Defaults to False.
    Returns
        A `gpd.GeoDataFrame` witgh the data from df
    """
    if flip_lon_sign:
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(-df['LON'], df['LAT']), crs="EPSG:4269")
    else:
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['LON'], df['LAT']), crs="EPSG:4269")

    return gdf

def connect_to_sqlalchemy(conn_string:str = 'postgresql://scope_team:greenTea123@database-1.ci75bfibgs4e.us-east-1.rds.amazonaws.com/FARS') -> Connection:
    """Connects to sqlalchemy and returns the connection.

    Args:
        conn_string: a string containing the connection string for create_engine. Defaults to our database.

    Returns:
        A `sqlalchemy.Connection` object
    """
    # Establish sqlalchemy connection
    db = create_engine(conn_string)
    return db.connect()
