import streamlit as st
from stqdm import stqdm
from packages.CCKP_new_api import CCKP_api_ERA5, CCKP_api_CMIP6
import pandas as pd


categories = ['Average temperatures', 'Average precipitation', 'Heat', 'Cold', 'Drought', 'Extreme precipitation']

# Function for importing the variables
@st.cache_data 
def load_variables_table():
    names_table = pd.read_excel('packages/geonames.xlsx', sheet_name='Variables').set_index('Code').to_dict()
    return names_table

@st.cache_data 
def select_category(category):

    '''
    Function that selects the variables of a certain category

    Parameters:
    -> category (str): the category of the variables

    Returns:
    -> var_names (dict): the names of the variables in the category
    -> var_description (list): the description of the variables in the category
    -> var_codes (set): the codes of the variables in the category
    '''

    names_table = load_variables_table()
    # Select the item in obj.variables_dict['Category'] that corresponds to the category
    var_codes = {k for k, v in names_table['Category'].items() if v == category}

    # Select the names of the variables that are in var_codes
    var_nm = {k: v for k, v in names_table['Variable'].items() if k in var_codes}
    var_names = {v: k for k, v in var_nm.items()}

    # Select the description of the variables
    var_desc = {k: v for k, v in names_table['Description'].items() if k in var_codes}
    var_description = [x for x in var_desc.values()]

    return var_names, var_description, var_codes

# Function for the climate form
def climate_form(sources, variables, scenarios, bands, latitude, longitude) -> None:

    with st.form(key='my_form'):

        # Check box for selectiong the sources
        ERA5_on = st.checkbox('Include ERA5', value=sources[0])
        CMIP6_on = st.checkbox('Include CMIP6', value=sources[1])

        # Select the variables
        selected_vars = {}
        for cat in categories:

            selected_vars.update({cat: []})


            try:
                var_names, _, _ = select_category(cat)
                var = st.multiselect(cat, var_names, variables[cat])
                
                # update the selected variables
                selected_vars[cat] = var

            except:
                var = st.multiselect(cat, var_names)

        
        # Select the scenarios
        scenarios = st.multiselect('Select the scenarios', ['historical', 'ssp119', 'ssp126', 'ssp370', 'ssp245', 'ssp585'], scenarios)

        # Select the bands
        bands = st.multiselect('Select the bands', ['p10','median','p90'], bands)

        latitude = st.number_input('Latitude', value=latitude)
        longitude = st.number_input('Longitude', value=longitude)

        # Submit the form
        load_button = st.form_submit_button('Confirm selection')
    
    if load_button:

        if not ERA5_on and not CMIP6_on:
            st.error('At least one source must be selected')
        else:
            st.session_state.sources = [ERA5_on, CMIP6_on]
        

        # Create the dict with the selected variables associated with the categories
        st.session_state.variables = selected_vars
        
        if CMIP6_on and len(scenarios) == 0:
            st.error('At least one scenario must be selected if you include CMIP6')

        else:
            st.session_state.scenarios = scenarios
        
        if CMIP6_on and len(bands) == 0:
            st.error('At least one band must be selected if you include CMIP6')


        else:
            st.session_state.bands = bands

        
        st.session_state.latitude = latitude
        st.session_state.longitude = longitude


        return True


def retrieve_climate_data(variables, sources, scenarios, bands, latitude, longitude, climatology) -> None:


    '''
    Function that retrieves the climate data from the API and fills the session state climate_data

    Parameters:
    -> variables (dict): the variables selected by the user
    -> sources (list): the sources selected by the user
    -> scenarios (list): the scenarios selected by the user
    -> bands (list): the bands selected by the user
    -> latitude (float): the latitude of the location
    -> longitude (float): the longitude of the location

    Returns:
    -> None
    '''

    # Add the coordinates to the session state climate_data
    if not st.session_state.climate_data.get('attrs'):    
        st.session_state.climate_data['attrs'] = {'latitude': latitude, 'longitude': longitude}

    # If the coordinates are different, update them and reset the climate_data
    if latitude != st.session_state.climate_data['attrs']['latitude'] or longitude != st.session_state.climate_data['attrs']['longitude']:
        st.session_state.climate_data = {}
        st.session_state.climate_data['attrs'] = {'latitude': latitude, 'longitude': longitude}

    selected_var_names = {v for k, v in variables.items() for v in v}
    selected_var_codes = [k[0] for k in load_variables_table()['Variable'].items() if k[1] in selected_var_names]

    for v in selected_var_codes:
        if not st.session_state.climate_data.get(v):
            st.session_state.climate_data[v] = {}
    
    # Look if there are variables loaded that are not in the selected ones and remove them
    cl_bkp = st.session_state.climate_data.copy()
    for v in st.session_state.climate_data.keys():
        if v not in selected_var_codes and v != 'attrs':
            cl_bkp.pop(v)
    st.session_state.climate_data = cl_bkp

    if sources[0]:
        with st.status('Loading ERA5 data... [could take a while]'):
            for v in stqdm(selected_var_codes):

                if not st.session_state.climate_data[v].get('ERA5'):
                    st.session_state.climate_data[v].update({'ERA5': {}})
                    st.write(f'Loading {v}')
                    obj = CCKP_api_ERA5(v)
                    obj.retrieve_request()
                    obj.load_point(latitude, longitude)
                    obj.make_json_to_llm()
                    st.session_state.climate_data[v].update({'ERA5': {'historical': obj}})
                
                else:
                    st.write(f'{v} has already been loaded')
    


    if sources[1]:
        with st.status('Loading CMIP6 data... [could take a while]'):
            for v in stqdm(selected_var_codes):

                if not st.session_state.climate_data[v].get('CMIP6'):
                    st.session_state.climate_data[v].update({'CMIP6': {}})

                for scenario in scenarios:

                    if not st.session_state.climate_data[v]['CMIP6'].get(scenario):
                        st.write(f'Loading {v} - {scenario} - {bands}')
                        obj = CCKP_api_CMIP6(v, scenario, bands, climatology)
                        obj.retrieve_request()
                        obj.load_point(latitude, longitude)
                        obj.make_json_to_llm()
                        st.session_state.climate_data[v]['CMIP6'].update({scenario: obj})
                    
                    else:
                        st.write(f'{v} - {scenario} has already been loaded')
