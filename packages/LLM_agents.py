from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
import streamlit as st
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import json

# Setting off warnings
import warnings
warnings.filterwarnings("ignore")

all = {
    "Average temperatures": [
        "Average Mean Surface Air Temperature",
        "Growing Season Length",
        "Growing Season Length End",
        "Growing Season Length Start",
        "Number of Summer Days (Tmax > 25°C)",
        "Average Maximum Surface Air Temperature",
        "Average Minimum Surface Air Temperature",
        "Minimum of Daily Min-Temperature",
        "Maximum of Daily Max-Temperature",
        "Warm Spell Duration Index"
    ],
    "Average precipitation": [
        "Precipitation",
        "Precipitation Percent Change"
    ],
    "Heat": [
        "Cooling Degree Days (ref-65°F)",
        "Number of Hot Days (Tmax > 30°C)",
        "Heat Index",
        "Number of Days with Heat Index > 39°C",
        "Number of Days with Heat Index > 37°C",
        "Number of Days with Heat Index > 41°C",
        "Relative Humidity",
        "Number of Tropical Nights (T-min > 20°C)",
        "Number of Tropical Nights (T-min > 23°C)",
        "Number of Tropical Nights (T-min > 26°C)",
        "Number of Tropical Nights (T-min > 29°C)",
        "Number of Days with Heat Index > 35°C",
        "Number of Hot Days (Tmax > 50°C)",
        "Number of Hot Days (Tmax > 45°C)",
        "Number of Hot Days (Tmax > 42°C)",
        "Number of Hot Days (Tmax > 40°C)",
        "Number of Hot Days (Tmax > 35°C)"
    ],
    "Cold": [
        "Cold Spell Duration Index",
        "Number of Frost Days (Tmin < 0°C)",
        "Heating degree days (ref-65°F)",
        "Number of Ice Days (Tmax < 0°C)",
        "Number of Frost Days (Tmin<0C)"
    ],
    "Drought": [
        "Maximum number of consecutive dry days"
    ],
    "Extreme precipitation": [
        "Number of Days with Precipitation >50mm",
        "Precipitation amount during wettest days",
        "Number of Days with Precipitation >20mm",
        "Average Largest 1-Day Precipitation",
        "Average Largest 5-Day Cumulative Precipitation"
    ]
    }



class main_agent(object):

    def __init__(self, llm, tools=None):

        self.conversation = []
        self.llm = llm

        # Initilize the conversation
        self.conversation.append(SystemMessage("You are ALM-APP, an Augmented Language Model based application designed to help in climate change analysis.\
                                                You can fill the form for selecting the climate data. The form is on the right side of the page. \
                                                You can select the sources, the variables, the scenarios, the bands and latitude and longitude of the location. \
                                                Do not make a selection if you are not sure about the choice.  \
                                                Here you have the description of the sources:\
                                                - ERA5: provides indices based on observed data, assimilated throught a physical model. It covers the periods from 1950 to 2022. \
                                                - CMIP6: provides indices based on Global Climate Models. It covers the period from 1950 to 2014 (historical scenario) and from 2015 to 2100 (future projection on SSPs scenarios). \
                                               If you include CMIP6, you must select at least one scenario. Here a description of the scenarios: \
                                                - historical: the historical scenario, from 1950 to 2014. You can use it for a comparison with ERA5 in order to test the reliability of CMUP6 models. \
                                                - ssp126: the Shared Socioeconomic Pathway 1-2.6, a scenario with low emissions. \
                                                - ssp245: the Shared Socioeconomic Pathway 2-4.5, a scenario with medium-low emissions. \
                                                - ssp585: the Shared Socioeconomic Pathway 5-8.5, a scenario with high emissions. \
                                               If you include CMIP6 you must also include the ensemble bands. Here a description of the bands: \
                                                - median: the median of the ensemble. Use it for the most probable outcome. \
                                                - p10: the 10th percentile of the ensemble. Use it to assess the uncertainity of median value. \
                                                - p90: the 90th percentile of the ensemble. Use it to assess the uncertainity of median value.  \
                                               If you include band and scenarios, remember to also include CMIP6 from the sources.\
                                                Here you have the description of the variables:\
                                               "))
        
        self.conversation.append(SystemMessage(str(all)))

        if tools:
            self.tools = tools
            self.augmented_llm = llm.bind_tools(self.tools, tool_choice="fill_form")


    def conversation_step(self, tools = False):

        if tools:
            ai_msg = self.augmented_llm.invoke(self.conversation)
        
        else:
            ai_msg = self.llm.invoke(self.conversation)
        
        self.conversation.append(ai_msg)


    def check_tool(self):

        # st.write(self.conversation)

        ai_msg = self.conversation[-1]
    
        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                try:
                    selected_tool = {"fill_form": fill_form}[tool_call["name"].lower()]
                    tool_output = selected_tool.invoke(tool_call["args"])
                    self.conversation.append(ToolMessage(tool_output[0], tool_call_id=tool_call["id"]))
                    self.conversation.append(SystemMessage('Explain which data you want to retrieve and you intend to use them. Write a detailed proposal for the analysis.\
                                                           Be spcific about the reasons why you selected that variables instead of others.\
                                                           Be specific about the time periods you want to analyze.\
                                                           Be specific about the variables, the sources, the scenarios and the bands.\
                                                           Be specific about the criteria you will use in the analysis.'))
                    self.conversation_step(False)
                    st.session_state.proposed_analysis = self.conversation[-1].content

                    return tool_output[1]

                except KeyError:
                    raise







categories = ['Average temperatures', 'Average precipitation', 'Heat', 'Cold', 'Drought', 'Extreme precipitation']

@tool
def fill_form(sources, variables, scenarios, bands, latitude, longitude):

    '''
    Function that creates the form for selecting the climate data for a certain location
    Args:
    sources (list): the sources of data. The elements are boolean values that indicate if the source is selected. First element is ERA5, second element is CMIP6
    variables (dict): the variables to be selected. The parameter must be a subsection of the dict all provided in before. All the categories must be included, at least left empty. For each category, the variables must be put in a list.
    scenarios (list): the scenarios to be selected. The choices are 'historical', 'ssp126', 'ssp245', 'ssp585'. They are the scenarios of the CMIP6 data source. If you include CMIP6, you must select at least one scenario.
    bands (list): the bands to be selected. The choices are 'median', 'p10', 'p90'
    latitude (float): the latitude of the location
    longitude (float): the longitude of the location
    '''

    # Standardize the request variables - look all the variables for each cathegory, compare with all dict and remove from variables dict the ones that are not in all dict
    # for cat in categories:
    #     try:
    #         for var in variables[cat]:
    #             if var not in all[cat]:
    #                 variables[cat].remove(var)
    #     except:
    #         variables[cat] = []
    
    st.session_state.sources = sources
    st.session_state.variables = variables
    st.session_state.scenarios = scenarios
    st.session_state.bands = bands
    st.session_state.latitude = latitude
    st.session_state.longitude = longitude


    return f"This is the choiche: the sources are {sources}, the variables are {variables}, the scenarios are {scenarios} and the bands are {bands}. The location is {latitude}, {longitude}", json.dumps({"sources": sources, "variables": variables, "scenarios": scenarios, "bands": bands, "latitude": latitude, "longitude": longitude})



