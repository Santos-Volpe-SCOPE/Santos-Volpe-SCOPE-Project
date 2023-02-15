"""Combines all .csv datasets for each folder (intended for SDS data) into 1 `pd.DataFrame` per folder and writes to a single .csv file per folder.

Main function is combine_SDS_datasets. Helper functions take the folder path and get all .csv filenames, read a list of filenames into `pd.DataFrame` objects, and concatenate a list of `pd.DataFrame` objects into a single `pd.DataFrame`.

"""

import pandas as pd
import helper

#TODO: add in filtering for limited columns

def combine_SDS_datasets(path: str = '', output_path: str = 'SDS/Output/') -> dict[str,pd.DataFrame]:
    """Combines folders of SDS datasets in folder `path` into a single CSV file for each folder in `output_path`.

    Calls a series of helper functions, see their docstrings for specifics.
    
    Args: 
        path: A string specifying the folders where the CSVs will be loaded from. Defaults to 'FARS CSVs/'
        output_path: A string specifying the path to the directory where the combined CSV for each source folder will be saved. Defaults to 'SDS/Output/'

    Returns:
        A dictionary where the keys are the subdirectories of `path` and the values are the `pd.DataFrame` of all the CSV files contained within that folder.
    """

    renames = {
        'latitude' : 'lat',
        'longitude' : 'lon',
        'longitud' : 'lon',
    }

    all_dirs = helper.get_all_subdirectories(path = path)
    print("Full list of states: " + str(all_dirs))
    output = {}
    for state_dir in all_dirs:
        # print("Processing: "+state_dir)
        all_filenames = helper.get_all_filenames(path+state_dir,"*.csv")
        all_dfs_state = helper.get_all_dfs_from_csv(all_filenames, index_col=None, encoding_errors='ignore', low_memory=False)
        for df in all_dfs_state:
            df.columns =  df.columns.str.lower()
            df.rename(columns = renames,inplace = True)
            print(df)
        combined_df = helper.concat_pandas_dfs(all_dfs_state)
        helper.write_dataframe_to_file(combined_df, output_path+state_dir+".csv")
        output[state_dir] = combined_df
    return output

if __name__=="__main__":
    combine_SDS_datasets(path = 'SDS/Data/', output_path='SDS/Output/')