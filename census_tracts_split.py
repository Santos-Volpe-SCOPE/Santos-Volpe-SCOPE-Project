"""Splits the single census tracts geojson into a geojson for each state.
"""
import json
import helper

def load_states(path='states.csv'):
    """Loads state info and returns a dictionary mapping state names to state initial.

    Args:
        path: A string defining where the states csv file is. Default is 'states.csv'.

    Returns:
        A dictionary containing the state names as keys and the state initials as values
    """
    states_df = helper.load_df_from_csv(path=path, low_memory = False)
    d_state_name2initial = dict(zip(states_df.name, states_df.state))

    return d_state_name2initial

def load_all_tracts_geojson(path='Shapefiles/census_tracts.geojson'):
    """Loads a geojson which should contain all census tracts nationwide.

    Args:
        path: A string defining where the geojson file containing all tracts is located. Default is 'Shapefiles/census_tracts.geojson'.

    Returns:
        A dictionary containing the geojson information.
    """
    # Opening JSON file
    f = open(path)

    # returns JSON object as dictionary
    tracts = json.load(f)
    print("Successfully loaded in geojson")
    # Closing file
    f.close()
    return tracts


def categorize_tracts_by_state(tracts):
    """Categorizes all census tracts into the state they're located within.

    Args:
        tracts: A dictionary containing the geojson info loaded by `load_all_tracts_geojson`.

    Returns:
        A dictionary with a key for each state and with a value containing a dictionary of census tracts for that state.
    """
    state_dict = {}

    # Iterating through the json list
    for i, tract in enumerate(tracts['features']):
        state_name = str(tract["properties"]["SF"])
        if(state_name not in state_dict):
            state_dict[state_name] = []
        state_dict[state_name].append(tracts['features'][i])

    print("Finished categorizing census tracts into different states")

    return state_dict

def write_files(state_dict, d_state_name2initial):
    """Writes a geojson file for each state.

    Args:
        state_dict: a dictionary returned by `categorize_tracts_by_state`
        d_state_name2initial: a dictionary returned by `load_states`

    Returns:
        none
    """
    for state_name in state_dict.keys():
        string = '{"type":"FeatureCollection","name":"census_tracts_split","features":" + json.dumps(state_dict[state_name]) + "}'

        label = state_name
        if state_name in d_state_name2initial:
            label = d_state_name2initial[state_name]
        with open(f"Shapefiles/census_tracts_by_state/census_tract_{label}.geojson", "w") as outfile:
            print("writing to file for ", state_name)
            outfile.write(string)


def split_census_tracts():
    """Main function combining each of the above helper functions.

    Args:
        none

    Returns:
        none
    """
    d_state_name2initial = load_states()

    tracts = load_all_tracts_geojson()

    state_dict = categorize_tracts_by_state(d_state_name2initial,tracts)

    write_files(state_dict,d_state_name2initial)

if __name__ == "__main__":
    split_census_tracts()