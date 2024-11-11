import streamlit as st
import os

import json
import numpy as np
import pandas as pd
import requests
from streamlit_folium import folium_static
import folium
import warnings
warnings.filterwarnings("ignore")


# -- GENERAL SETTINGS

# Initialize the AzureOpenAI capabilities
from openai import AzureOpenAI
client = AzureOpenAI(
  azure_endpoint = st.secrets['AZURE_ENDPOINT'], 
  api_key = st.secrets['OPENAI_API_KEY'],  
  api_version="2024-02-01"
)


# Set the page configuration
st.set_page_config(page_title='Function Calling ERA5', page_icon='🌍', layout='wide')

st.title('Function Calling - ERA5')
# Initialize chat history as streamlit session states
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "Retrieve the past weather data for the given location from the ERA5 dataset, and comment."},
                                {"role": "system", "content": "Don't make assumptions about what values to use with functions. Ask for clarification if a user request is ambiguous."}]

if "data" not in st.session_state:
    st.session_state.data = []


# -- FUNCTIONS

# Defining the function that can be called by GPT
def get_past_weather(latitude, longitude, variable, start, end, resample='Y'):

    # Create the link to the API 
    link = f'https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start}&end_date={end}&hourly={variable}&models=era5'

    # Get the data
    f = requests.get(link, verify=False)
    data = f.json()

    # Convert the data in a pandas dataframe
    dat = pd.DataFrame(data['hourly'])

    # convert dat.time in datetime
    dat['time'] = pd.to_datetime(dat['time'])
    dat = dat.set_index('time')

    if resample != 'H' and variable != 'precipitation':
        dat = dat.resample(resample).agg({variable: [np.mean, np.min, np.max]})
    
    if resample != 'H' and variable == 'precipitation':
        dat = dat.resample(resample).agg({variable: np.sum})

    if resample == 'Y':
        dat.index = dat.index.strftime('%Y')
    if resample == 'M':
        dat.index = dat.index.strftime('%Y-%m')
    if resample == 'W':
        dat.index = dat.index.strftime('%Y-%W')
    if resample == 'D':
        dat.index = dat.index.strftime('%Y-%m-%d')
    if resample == 'H':
        dat.index = dat.index.strftime('%Y-%m-%d %H')

    st.session_state.data.append({'latitude': latitude, 'longitude': longitude, 'variable': variable, 'start': start, 'end': end, 'resample': resample, 'data': dat})

    return dat.to_json()

# Define the dictionary with the structure of the function
get_past_weather_dict ={

        "type": "function",
        "function": {
            "name": "get_past_weather",
            "description": "Get the past weather data of a given location from ERA5 dataset",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "string",
                        "description": "The latitude of the location",
                    },
                    "longitude": {
                        "type": "string",
                        "description": "The longitude of the location",
                    },
                    "variable": {
                        "type": "string",
                        "description": "The weather variable to retrieve. Use 'temperature_2m' for temperature data; 'precipitation' for precipitation data; 'wind_speed_10m' for wind speed , 'relative_humidity_2m' for humidity, and 'wind_gusts_10m' for wind gusts data.",
                    },
                    "start": {
                        "type": "string",
                        "description": "The start date of the period",
                    },
                    "end": {
                        "type": "string",
                        "description": "The end date of the period",
                    },
                    "resample": {
                        "type": "string",
                        "description": "The resampling frequency. Use 'Y' for yearly data, 'M' for monthly data, 'W' for weekly data, 'D' for daily data, 'H' for hourly data. Use preferaily YEARLY data.",}
                },
                "required": ["latitude", "longitude", "variable", "start", "end", "resample"],
            },
        }

        
    }

# Register the functions
tools = [
    get_past_weather_dict
    ]

available_functions = {
    "get_past_weather": get_past_weather
    } 


# A function for making a step in the conversation
def conversation_step(messages, tools=None, tool_choice=None):

    response = client.chat.completions.create(
        model = "llm-gpt35",
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )

    return response

# A function for generating the response with the function calling option
def generate_response(tools=None, tool_choice=None):

    generating = True

    while generating:
        
        # Make the model say something
        response = conversation_step(st.session_state.messages, tools=tools, tool_choice="auto")
        
        for choice in response.choices:
                st.session_state.messages.append(choice.message)
                
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        
                        # Get the data from the tool call
                        function_name = tool_call.function.name
                        function_to_call = available_functions[function_name]
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Call the function
                        data = function_to_call(**function_args)
                        
                        st.session_state.messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": data,
                            }
                        )
                
                else:
                    generating = False
                    break


# -- DASHBOARD 
if __name__ == "__main__":

    # A restart bottom to clean the conversation history
    if st.button('Restart'):
        st.session_state.messages = [{"role": "system", "content": "Retrieve the past weather data for the given location from the ERA5 dataset, and comment."},
                                    {"role": "system", "content": "Don't make assumptions about what values to use with functions. Ask for clarification if a user request is ambiguous."}]
        st.session_state.data = []
        st.rerun()

    col1, col2 = st.columns([1, 1])



    with col1:
        if prompt := st.chat_input("Ask me something!"):

            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.spinner("Generating response..."):
                generate_response(tools=tools, tool_choice="auto")

            response = f"{st.session_state.messages[-1].content}"
            # Display assistant response in chat message container
            
            with st.chat_message("assistant"):
                st.markdown(response)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

    if len(st.session_state.data)!=0:

        for i in range(len(st.session_state.data)):

            latitude = st.session_state.data[i]['latitude']
            longitude = st.session_state.data[i]['longitude']
            variable = st.session_state.data[i]['variable']
            start = st.session_state.data[i]['start']
            end = st.session_state.data[i]['end']
            resample = st.session_state.data[i]['resample']
            dat = st.session_state.data[i]['data']

            with col2:

                with st.expander("Show data"):

                    st.subheader('The assistant has retrieved data for')
                    st.write('Latitude:', latitude, 'Longitude:', longitude)
                    st.write('Variable:', variable)
                    st.write('Start date:', start, 'End date:', end)


                    st.line_chart(dat[variable])
                    m = folium.Map(location=[latitude, longitude], zoom_start=7)
                    folium.CircleMarker(
                        location=[latitude, longitude],
                        radius=8,
                        color='k',
                        fill=True,
                        fill_color='k',
                        fill_opacity=0.7
                    ).add_to(m)
                    folium_static(m)

    st.divider()

    # Look at messages and put all dictionary in a dataframe. Some items in messages are not dictionaries, so we need to filter them out
    df = pd.DataFrame([i for i in st.session_state.messages if isinstance(i, dict)])
    st.write(df)
