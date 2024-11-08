import streamlit as st

from packages.CCKP_new_api import CCKP_api_ERA5, CCKP_api_CMIP6
from packages.interaction_funcs import *
from packages.LLM_agents import main_agent, fill_form
from openai import AzureOpenAI

import pandas as pd
from stqdm import stqdm
from dotenv import load_dotenv
from openai import AzureOpenAI
import json, os
import plotly.express as px

# Insert here the path for the credentials.env file
load_dotenv("../credentials.env")


# Set the page configuration
st.set_page_config(page_title='CCKP API', page_icon='🌍', layout='wide')

st.title('Climate Change ALM-APP')

st.markdown('**Climate Change ALM-APP** is an Augmented Language Model based app designed to help you in the analysis of climate data.')


# Some template requests

req_templates =  {'Airport Climate Change Risk Assessment':'I want to make a Risk Assessment for Fiumicino Airport, Rome, Italy. I want to analyze heat, extreme precipitation, and drought. Please, for each category select one hazard, retrieve the data and analyze them. Choose the climate variables in an appropriate way, making sure that they are relevant for the hazard, the location and the fact that we are interested in an airport. For example, do not choose variables with high thresholds which are never reached in the location.\n \
                    I want to see the historical data and the future projections for the SSP126, and SSP585 scenarios. For the historical period, use both ERA5 and Historical scenario from CMIP6.\n \
                    The RISK is defined as a combination of EXPOSURE, VULNERABILITY, and HAZARD. You must compute the risk for each category considered (heat, extreme precipitation and drought).\n \
                    The HAZARD must be computed from the data you retrieved. Once you have the data, define what is normal for the historical period and then compare it to what is expected in 2030, 2050 and 2100. For each of these time horizons use the data in plus/minus 5 years (for example, for 2050 use data from 2045 to 2055).\n \
                    For the EXPOSURE, consider the type of infrastructure to determine if the hazard considered can affect it.\n \
                    For the VULNERABILITY, try to guess how that hazard can affect that infrastructure\n \
                    One you have hazard, vulnerability and exposure, combine them to obtain the risk.\n \
                    For each of these time horizons I want a risk level (LOWEST, LOW, MEDIUM, HIGH or HIGHEST)  for each category, and an explanation of why you choose that level.\n \
                    Provide also a detailed explanation of the analysis, specifying how you choose the data, how you determined hazard, vulnerability and exposure, and how you combined them into the risk.\n \
                   ',

                    'Climate Baseline chapter for ESIA':'I want to write the Climate Baseline chapter for the ESIA of the new highway in the region of Lazio, Italy. I want a general overview of the climate in the region in the last 30 years.'}

with st.container(border=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        req = st.radio('Select a template request', list(req_templates.keys()))

    with col2:
        st.subheader('Request template')
        st.markdown(req_templates[req])


st.divider()
st.subheader('Select the variables')


#Setting AI parameters
openai_deployment_name = os.getenv("GPT_DEPLOYMENT_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_api_version = os.getenv("OPENAI_API_VERSION")
azure_endpoint = os.getenv("AZURE_ENDPOINT")

llm = AzureChatOpenAI(deployment_name=openai_deployment_name, openai_api_version=openai_api_version,
                            openai_api_key=openai_api_key, azure_endpoint=azure_endpoint, temperature=0)



# Initialize the AzureOpenAI client
client = AzureOpenAI(
  azure_endpoint = os.environ['AZURE_ENDPOINT'], 
  api_key = os.environ['OPENAI_API_KEY'],  
  api_version=os.environ['OPENAI_API_VERSION']
)


categories = ['Average temperatures', 'Average precipitation', 'Heat', 'Cold', 'Drought', 'Extreme precipitation']
colors = {
    'historical': 'blue',
    'ssp119': 'lightgreen',
    'ssp126': 'green',
    'ssp245': 'orange',
    'ssp370': 'purple',
    'ssp585': 'red'
}


col1, col2 = st.columns([2, 1])



if 'sources' not in st.session_state:
    st.session_state.sources = [False, False]

if 'variables' not in st.session_state:
    st.session_state.variables = {
        'Average temperatures': [],
        'Average precipitation': [],
        'Heat': [],
        'Cold': [],
        'Drought': [],
        'Extreme precipitation': []
    }

if 'climate_data' not in st.session_state:
    st.session_state.climate_data = {}

if 'scenarios' not in st.session_state:
    st.session_state.scenarios = []

if 'bands' not in st.session_state:
    st.session_state.bands = []

if 'single_gpt' not in st.session_state:
    st.session_state.single_gpt = {}

if 'latitude' not in st.session_state:
    st.session_state.latitude = 0

if 'longitude' not in st.session_state:
    st.session_state.longitude = 0

if 'main_agent' not in st.session_state:
    st.session_state.main_agent = main_agent(llm, [fill_form])

if 'proposed_analysis' not in st.session_state:
    st.session_state.proposed_analysis = None

if 'show_data' not in st.session_state:
    st.session_state.show_data = False

if 'climatology' not in st.session_state:
    st.session_state.climatology = False

if 'screening' not in st.session_state:
    st.session_state.screening = False

if 'screening_data' not in st.session_state:
    st.session_state.screening_data = None

def describe_graphs(json, request):

    messages = [
        {
            "role": "system",
            "content": request
        }
    ]


    messages.append(
        {
            "role": "system",
            "content": str(json)
        }
    )
    response = client.chat.completions.create(
        model = os.environ['GPT_DEPLOYMENT_NAME'],
        messages=messages,
    )

    return response.choices[0].message.content


with col1:
    col11, col12 = st.columns([1, 1])

    with col11:
        if st.button('Reset'):
            st.session_state.main_agent = main_agent(llm, [fill_form])
            st.session_state.proposed_analysis = None
            st.session_state.show_data = False
    
    with col12:
        st.session_state.screening = st.checkbox('Screening', st.session_state.screening)

    prompt = st.chat_input('Ask me something')

    if prompt:

        st.session_state.main_agent.conversation.append(HumanMessage(prompt))
        st.session_state.main_agent.conversation_step(True)
        st.session_state.main_agent.check_tool()

        if st.session_state.screening and st.session_state.screening_data is None and st.session_state.proposed_analysis is not None:

            st.session_state.screening_data = [CCKP_api_ERA5('tas', True), CCKP_api_ERA5('pr', True),
                                                CCKP_api_ERA5('tasmin', True), CCKP_api_ERA5('tasmax', True), CCKP_api_ERA5('sd', True),
                                                CCKP_api_ERA5('wsdi', True), CCKP_api_ERA5('hd30', True), CCKP_api_ERA5('hd35', True),
                                                CCKP_api_ERA5('hd40', True), CCKP_api_ERA5('hd42', True), CCKP_api_ERA5('tr23', True),
                                                CCKP_api_ERA5('tr26', True), CCKP_api_ERA5('tr29', True), CCKP_api_ERA5('rx1day', True),
                                                CCKP_api_ERA5('rx5day', True), CCKP_api_ERA5('r20mm', True), CCKP_api_ERA5('r50mm', True)]

            st.write('Importing data for the screening...')
            for obj in stqdm(st.session_state.screening_data):
                obj.retrieve_request()
                obj.load_point(st.session_state.latitude, st.session_state.latitude)
                obj.make_json_to_llm()
        
        if st.session_state.screening and st.session_state.screening_data is not None:

            st.session_state.main_agent.conversation.append(SystemMessage(f'Here some local data for a pre screening. Remember that the timelines of these data are climatological, that is to say they are average for the period 1991-2020.The data are: {[x.json_to_llm for x in st.session_state.screening_data]}. \
                                                                        Empty the form and rewrite the proposal for the analysis basing on the parameters that i provided you. \
                                                                        Use them to make a more consistent proposal. In the new proposal, you do not have to include all these variables. Just use them to choose the most appropriate variables and to justify the choices.\
                                                                        In the new proposal, specify how you used the screening data in the choiches. Make specific references to the numerical values you have found in the screening data.'))
            st.session_state.main_agent.conversation_step(True)
            st.session_state.main_agent.check_tool()



    

    


with col2:
    with st.expander('Form for selecting the climate data'):
        st.session_state.climatology = st.checkbox('Use climatology for CMIP6 [faster]', st.session_state.climatology)
        trigger = climate_form(st.session_state.sources, st.session_state.variables, st.session_state.scenarios, st.session_state.bands, st.session_state.latitude, st.session_state.longitude)

        if trigger:
            st.session_state.main_agent.conversation.append(HumanMessage(f'I have modified the form with the following parameters: \
                                                                            Variables: {st.session_state.variables} \
                                                                            Sources: {st.session_state.sources} \
                                                                            Scenarios: {st.session_state.scenarios} \
                                                                            Bands: {st.session_state.bands} \
                                                                            Latitude: {st.session_state.latitude} \
                                                                            Longitude: {st.session_state.longitude} \
                                                                            Please, rewrite the proposal for the analysis basing on the parameters that i provided you.'))
            st.session_state.main_agent.conversation_step(False)
            st.session_state.proposed_analysis = st.session_state.main_agent.conversation[-1].content

            #st.write(st.session_state.main_agent.conversation)

with col1:
    if st.session_state.proposed_analysis:
        with st.container(border=True):
            st.subheader('Proposed analysis:')
            st.write(st.session_state.proposed_analysis)

if st.button('Loada data'):
    retrieve_climate_data(st.session_state.variables, st.session_state.sources, st.session_state.scenarios, st.session_state.bands, st.session_state.latitude, st.session_state.longitude, st.session_state.climatology)



#st.write(st.session_state.climate_data)
st.divider()


st.show_data = st.checkbox('Show data', st.session_state.show_data)

if st.show_data:
    for var in st.session_state.climate_data:

        if var != 'attrs':

            with st.container(border=True):
                st.write(f'**{var}**')

                if st.session_state.sources[0] and st.session_state.climate_data[var]['ERA5']:
                    st.write(f"**{st.session_state.climate_data[var]['ERA5']['historical'].variables_dict['Variable']}**")
                    with st.expander('ERA5 - Plot'):
                        if st.session_state.climate_data[var]['ERA5']:

                            obj = st.session_state.climate_data[var]['ERA5']['historical']
                            fig = px.line(obj.timeseries_point_dataframe)
                            st.plotly_chart(fig, use_container_width=True)
                    
                if st.session_state.sources[1] and st.session_state.climate_data[var]['CMIP6']:


                    with st.expander('CMIP6 - Plot'):

                        fig = px.line()
                        for scenario in st.session_state.climate_data[var]['CMIP6']:
                            obj = st.session_state.climate_data[var]['CMIP6'][scenario]
                            #st.write(px.line(obj.timeseries_point_dataframe).data[0])
                            for j, sty in zip(st.session_state.bands, ['solid', 'dot', 'dash']):
                                #st.write(obj.timeseries_point_dataframe)
                                fig.add_scatter(x=obj.timeseries_point_dataframe.index, y=obj.timeseries_point_dataframe[f'{var}_{scenario}_{j}'], line=dict(dash=sty, color=colors[scenario], width=2), name=f'{scenario} - {j}')
                            
                    
                        st.plotly_chart(fig, use_container_width=True)
                
                with st.expander('Description'):
                    
                    # check if the description is already present IN st.session_state.climate_data[var]
                    if not 'Description' in st.session_state.climate_data[var]:

                        tot_json = {}
                        if st.session_state.sources[0] and st.session_state.climate_data[var]['ERA5']:
                            era_json = st.session_state.climate_data[var]['ERA5']['historical'].json_to_llm
                            tot_json = {**tot_json, **era_json}

                        if st.session_state.sources[1] and st.session_state.climate_data[var]['CMIP6']:
                            cmip_json = {scenario: st.session_state.climate_data[var]['CMIP6'][scenario].json_to_llm for scenario in st.session_state.scenarios}
                            tot_json = {**tot_json, **cmip_json}
                        
                        answ = describe_graphs(tot_json, f'{st.session_state.proposed_analysis} \n Based on that request, analyze only the variable you are provided with data. Please, be exauhstive in your analysis and make a long output. Follow the proposal you made at the beginning of the conversation. Consider explicity the time horizons that you wrote in the proposal.')
                        st.session_state.climate_data[var]['Description'] = answ


                    st.write(st.session_state.climate_data[var]['Description'])
                        


    with st.expander('Summary'):

        if st.button('Reset summary'):
            del st.session_state.summarizer
            st.session_state.summarizer = main_agent(llm)
            st.session_state.summarizer.conversation.append(HumanMessage('Summarize the analysis of the data that you have just done.'))
            if st.session_state.climatology:
                st.session_state.summarizer.conversation.append(SystemMessage('I have used the climatology for the CMIP6 data. This means that the data are representative for the 20 years after the date. E.g 2020 means 2020-2040.'))
            st.session_state.summarizer.conversation.append(SystemMessage(st.session_state.proposed_analysis))
            st.session_state.summarizer.conversation.append(SystemMessage(str(st.session_state.climate_data)))
            st.session_state.summarizer.conversation_step(False)


        if 'summarizer' not in st.session_state:
            st.session_state.summarizer = main_agent(llm)
            st.session_state.summarizer.conversation.append(HumanMessage('Summarize the analysis of the data that you have just done.'))
            if st.session_state.climatology:
                st.session_state.summarizer.conversation.append(SystemMessage('I have used the climatology for the CMIP6 data. This means that the data are representative for the 20 years after the date. E.g 2020 means 2020-2040.'))
            st.session_state.summarizer.conversation.append(SystemMessage(st.session_state.proposed_analysis))
            st.session_state.summarizer.conversation.append(SystemMessage(str(st.session_state.climate_data)))
            st.session_state.summarizer.conversation_step(False)
        

        inpt = st.text_input('Addition request')
        if inpt:
            st.session_state.summarizer.conversation.append(HumanMessage(inpt))
            st.session_state.summarizer.conversation_step(False)

        st.write(st.session_state.summarizer.conversation[-1].content)












