# Api importations
import s3fs
import pandas as pd
import xarray as xr
import json
from json import encoder

# -- PACKAGE FOR RETRIEVING AND MANAGING CCKP RASTER DATA
# -- AUTHOR jacopo.grassi@wsp.com / jacopo.grassi@polito.it



era5_dict = {
    'collection' : ['era5-x0.25'],
    'variables' : vars,
    'dataset_with_scenario' : ['era5-x0.25-historical'],
    'aggregation_period' : ['annual', 'seasonal', 'monthly'],
    'statistic' : ['mean'],
    'percentile' : ['mean'],

    'product' : {
        'climatology' : {'time_period': ['1986-2005', '1991-2020', '1995-2014', '1986-2005', '1991-2020', '1995-2014'],
                         'product_type': ['climatology']},
        'timeseries' : {'time_period': ['1950-2022'],
                        'product_type': ['timeseries']},
        'trend' : {'time_period': ['1951-2020', '1971-2020', '1991-2020'],
                   'product_type': ['climatology']},
        'trendsignificance' : {'time_period': ['1951-2020', '1971-2020', '1991-2020'],
                               'product_type': ['climatology']},
        'trendconfidence' : {'time_period': ['1951-2020', '1971-2020', '1991-2020'],
                             'product_type': ['climatology']},
    },
}

cmip_dict = {
    'collection' : ['cmip6-x0.25'],
    'variables' : vars,
    'dataset_with_scenario' : ['ensemble-all-historical', 'ensemble-all-ssp119', 'ensemble-all-ssp126', 'ensemble-all-ssp245', 'ensemble-all-ssp370', 'ensemble-all-ssp585'],
    'aggregation_period' : ['annual', 'seasonal', 'monthly'],
    'statistic' : ['mean'],
    'percentile' : ['median', 'p10', 'p90'],

    'product' : {
        'climatology' : {'time_period': ['1995-2014'],
                         'product_type': ['climatology']},
        'timeseries' : {'time_period': ['1950-2014'],
                        'product_type': ['timeseries']},
        'trend' : {'time_period': ['1951-2020', '1971-2020', '1991-2020'],
                   'product_type': ['climatology']},
        'trendsignificance' : {'time_period': ['1951-2020', '1971-2020', '1991-2020'],
                               'product_type': ['climatology']},
        'trendconfidence' : {'time_period': ['1951-2020', '1971-2020', '1991-2020'],
                             'product_type': ['climatology']},
    },
}


class CCKP_api_ERA5():

    def __init__(self, variable, climatology = False):

        
        self.base_url = 's3://wbg-cckp/data'

        self.collection = 'era5-x0.25'
        self.variable = variable
        self.dataset_with_scenario = 'era5-x0.25-historical'
        self.aggregation_period = 'annual'
        self.statistic = 'mean'
        self.percentile = 'mean'

        self.variables_dict = self.create_dict()
        self.status_dict = {'timeseries': 'Not Retrieved', 'trend': 'Not Retrieved', 'confidence': 'Not Retrieved'}

        self.climatology = climatology
        

        if climatology:
            self.retrieve_url_timeseries = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1991-2020.nc'
        
        else:
            # Objects to store the urls
            self.retrieve_url_timeseries = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/timeseries-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_timeseries_{self.percentile}_1950-2022.nc'

        self.retrieve_url_trend_1951_2020 = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/trend-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1951-2020.nc'
        self.retrieve_url_trend_1971_2020 = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/trend-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1971-2020.nc'
        self.retrieve_url_trend_1991_2020 = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/trend-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1991-2020.nc'

        self.retrieve_url_confidence_1951_2020 = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/trendconfidence-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1951-2020.nc'
        self.retrieve_url_confidence_1971_2020 = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/trendconfidence-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1971-2020.nc'
        self.retrieve_url_confidence_1991_2020 = f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/trendconfidence-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_{self.percentile}_1991-2020.nc'

        self.timeseries_dataset = None
        self.trends_dataset = None
        self.confidence_dataset = None

        self.timeseries_point_dataframe = None
        self.trends_point_dataframe = None
        self.confidence_point_dataframe = None

        self.timeseries_point_json = None
        self.trends_point_json = None
        self.confidence_point_json = None

        self.json_to_llm = None



    def create_dict(self, vars = None):

        '''
        Function that creates a dictionary with the names of the variables and their descriptions.

        Parameters:
        vars (list): List of variables to be included in the dictionary. TO_DO

        Returns:
        variables_dict (dict): Dictionary with the names of the variables and their descriptions.
        '''

        # Import the table with the names of the variables
        names_table = pd.read_excel('packages/geonames.xlsx', sheet_name='Variables')

        # Keep only the rows of the table that correspond to the variables in the list, and convert it to a dictionary [CODE as index]
        variables_dict = names_table[names_table['Code'] == self.variable].set_index('Code').to_dict()
        variables_dict = {k: v[self.variable] for k, v in variables_dict.items()}
        variables_dict['Code'] = self.variable

        return variables_dict


    def retrieve_request(self) -> xr.Dataset:

        '''
        '''

        if self.climatology:
            product = 'climatology'
        else:
            product = 'timeseries'

        try:
            # Creating the s3 file system
            fs = s3fs.S3FileSystem()

            # Reading the data from the s3 bucket
            fs = s3fs.S3FileSystem(anon=True)
            filejob = fs.open(self.retrieve_url_timeseries)

            # Opening the dataset, rechunking it and dropping the unnecessary variables
            dataset = xr.open_dataset(filejob)
            dataset = dataset.drop_vars(['lat_bnds', 'lon_bnds', 'bnds'])
            
            self.timeseries_dataset = dataset[f'{product}-{self.variable}-{self.aggregation_period}-{self.statistic}']

            # if self.product == 'timeseries':
            #     self.dataset.values = self.dataset.values.astype(float) / self.variable_attr('normalization_factor')
            self.status_dict['timeseries'] = 'Retrieved'
            
        except:
                self.status_dict['timeseries'] = 'Error'
        

        
        try:
            trend_dts = []
            for url,years in zip([self.retrieve_url_trend_1951_2020, self.retrieve_url_trend_1971_2020, self.retrieve_url_trend_1991_2020], ['1951_2020', '1971_2020', '1991_2020']):
                
                    # Creating the s3 file system
                    fs = s3fs.S3FileSystem()

                    # Reading the data from the s3 bucket
                    fs = s3fs.S3FileSystem(anon=True)
                    filejob = fs.open(url)

                    # Opening the dataset, rechunking it and dropping the unnecessary variables
                    dataset = xr.open_dataset(filejob)
                    dataset = dataset.drop_vars(['lat_bnds', 'lon_bnds', 'bnds'])

                    trend_dts.append(dataset[f'trend-{self.variable}-{self.aggregation_period}-{self.statistic}'].rename(self.variable + '_trend_' + years).drop('time'))
            
            self.trends_dataset = xr.merge(trend_dts)
            self.status_dict['trend'] = 'Retrieved'
            
        except:
            self.status_dict['trend'] = 'Error'

        

        try:
            conf_dts = []
            for url,years in zip([self.retrieve_url_confidence_1951_2020, self.retrieve_url_confidence_1971_2020, self.retrieve_url_confidence_1991_2020], ['1951_2020', '1971_2020', '1991_2020']):
                
                    # Creating the s3 file system
                    fs = s3fs.S3FileSystem()

                    # Reading the data from the s3 bucket
                    fs = s3fs.S3FileSystem(anon=True)
                    filejob = fs.open(url)

                    # Opening the dataset, rechunking it and dropping the unnecessary variables
                    dataset = xr.open_dataset(filejob)
                    dataset = dataset.drop_vars(['lat_bnds', 'lon_bnds', 'bnds'])

                    conf_dts.append(dataset[f'trendconfidence-{self.variable}-{self.aggregation_period}-{self.statistic}'].rename(self.variable + '_trend_confidence_' + years).drop('time'))
            
            self.confidence_dataset = xr.merge(conf_dts)
            self.status_dict['confidence'] = 'Retrieved'
        except:
            self.status_dict['confidence'] = 'Error'


    def load_point(self, lat, lon):
         

        self.timeseries_point_dataframe = self.timeseries_dataset.sel(lat=lat, lon=lon, method='nearest')
        self.timeseries_point_dataframe.values = self.timeseries_point_dataframe.values.astype(float) / self.variables_dict['Normalization factor']
        self.timeseries_point_dataframe = self.timeseries_point_dataframe.to_dataframe().drop(columns=['lat', 'lon'])
        self.timeseries_point_dataframe.index = self.timeseries_point_dataframe.index.year

        self.trends_point_dataframe = self.trends_dataset.sel(lat=lat, lon=lon, method='nearest').to_dataframe().drop(columns=['lat', 'lon'])
        self.confidence_point_dataframe = self.confidence_dataset.sel(lat=lat, lon=lon, method='nearest').to_dataframe().drop(columns=['lat', 'lon'])


        # Rounding precision of dataframes to 2
        self.timeseries_point_dataframe = self.timeseries_point_dataframe.round(2)
        self.trends_point_dataframe = self.trends_point_dataframe.round(2)
        self.confidence_point_dataframe = self.confidence_point_dataframe.round(2)



        self.timeseries_point_json = self.timeseries_point_dataframe.astype(str).to_json()
        self.trends_point_json = self.trends_point_dataframe.astype(str).to_json()
        self.confidence_point_json = self.confidence_point_dataframe.astype(str).to_json()
        
        encoder.FLOAT_REPR = lambda o: format(o, '.2f')

        # Roubding precision of jsons to 2
        self.timeseries_point_json = json.loads(self.timeseries_point_json)
        self.trends_point_json = json.loads(self.trends_point_json)
        self.confidence_point_json = json.loads(self.confidence_point_json)


    def make_json_to_llm(self):
         
        self.json_to_llm = {
            
            'var_code': self.variable,
            'var_name': self.variables_dict['Variable'],
            'unit': self.variables_dict['Unit'],
            'description': self.variables_dict['Description'],
            'status': self.status_dict,

            'values': {
            'timeseries in unit': self.timeseries_point_json,
            'trends in units/decades': self.trends_point_json,
            'confidence in percentage': self.confidence_point_json
            }

        }


class CCKP_api_CMIP6():

    def __init__(self, variable, scenario, bands = ['median'], climatology = False):

        
        self.base_url = 's3://wbg-cckp/data'

        self.collection = 'cmip6-x0.25'
        self.variable = variable
        self.scenario = scenario
        self.dataset_with_scenario = f'ensemble-all-{scenario}'
        self.aggregation_period = 'annual'
        self.statistic = 'mean'
        self.climatology = climatology
        
        if scenario == 'historical':
            self.years = '1950-2014'
        
        else:
            self.years = '2015-2100'

        self.variables_dict = self.create_dict()
        self.status_dict = {'timeseries': 'Not Retrieved', 'trend': 'Not Retrieved', 'confidence': 'Not Retrieved'}

        self.bands = bands

        if climatology:
            self.retrieve_url_timeseries_median = []
            self.retrieve_url_timeseries_p10 = []
            self.retrieve_url_timeseries_p90 = []

            if scenario == 'historical':
                for years in ['1995-2014']:
                    self.retrieve_url_timeseries_median.append(f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_median_{years}.nc')
                    self.retrieve_url_timeseries_p10.append(f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_p10_{years}.nc')
                    self.retrieve_url_timeseries_p90.append(f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_p90_{years}.nc')

            if scenario != 'historical':
                for years in ['2020-2039', '2040-2059', '2060-2079', '2080-2099']:
                    self.retrieve_url_timeseries_median.append(f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_median_{years}.nc')
                    self.retrieve_url_timeseries_p10.append(f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_p10_{years}.nc')
                    self.retrieve_url_timeseries_p90.append(f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/climatology-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_climatology_p90_{years}.nc')
        
        else:
            self.retrieve_url_timeseries_median = [f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/timeseries-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_timeseries_median_{self.years}.nc']
            self.retrieve_url_timeseries_p10 = [f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/timeseries-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_timeseries_p10_{self.years}.nc']
            self.retrieve_url_timeseries_p90 = [f'{self.base_url}/{self.collection}/{self.variable}/{self.dataset_with_scenario}/timeseries-{self.variable}-{self.aggregation_period}-{self.statistic}_{self.collection}_{self.dataset_with_scenario}_timeseries_p90_{self.years}.nc']

        self.timeseries_dataset = None
        self.timeseries_point_dataframe = None
        self.timeseries_point_json = None
        self.json_to_llm = None



    def create_dict(self, vars = None):

        '''
        Function that creates a dictionary with the names of the variables and their descriptions.

        Parameters:
        vars (list): List of variables to be included in the dictionary. TO_DO

        Returns:
        variables_dict (dict): Dictionary with the names of the variables and their descriptions.
        '''

        # Import the table with the names of the variables
        names_table = pd.read_excel('packages/geonames.xlsx', sheet_name='Variables')

        # Keep only the rows of the table that correspond to the variables in the list, and convert it to a dictionary [CODE as index]
        variables_dict = names_table[names_table['Code'] == self.variable].set_index('Code').to_dict()
        variables_dict = {k: v[self.variable] for k, v in variables_dict.items()}
        variables_dict['Code'] = self.variable

        return variables_dict


    def retrieve_request(self) -> xr.Dataset:

        '''
        '''
        if self.climatology:
            product = 'climatology'
        else:
            product = 'timeseries'

        try:
            dat_dts = []


            for band in self.bands:

                if band == 'median':
                    urls = self.retrieve_url_timeseries_median
                if band == 'p10':
                    urls = self.retrieve_url_timeseries_p10
                if band == 'p90':
                    urls = self.retrieve_url_timeseries_p90

                for url in urls:

                    # Creating the s3 file system
                    fs = s3fs.S3FileSystem()

                    # Reading the data from the s3 bucket
                    fs = s3fs.S3FileSystem(anon=True)
                    filejob = fs.open(url)

                    # Opening the dataset, rechunking it and dropping the unnecessary variables
                    dataset = xr.open_dataset(filejob)
                    #dataset = dataset.drop_vars(['lat_bnds', 'lon_bnds', 'bnds'])

                    dat_dts.append(dataset[f'{product}-{self.variable}-annual-mean'].rename(f'{self.variable}_{self.scenario}_{band}'))


            self.timeseries_dataset = xr.merge(dat_dts)
            self.status_dict['timeseries'] = 'Retrieved'
            
        except:
                raise
                self.status_dict['timeseries'] = 'Error'
        

        



    def load_point(self, lat, lon):
         
        self.timeseries_point_dataframe = self.timeseries_dataset.sel(lat=lat, lon=lon, method='nearest')

        for vars in self.bands:
            self.timeseries_point_dataframe[f'{self.variable}_{self.scenario}_{vars}'].values = self.timeseries_point_dataframe[f'{self.variable}_{self.scenario}_{vars}'].values.astype(float) / self.variables_dict['Normalization factor']

        self.timeseries_point_dataframe = self.timeseries_point_dataframe.to_dataframe().drop(columns=['lat', 'lon'])
        self.timeseries_point_dataframe.index = self.timeseries_point_dataframe.index.year

        # Rounding precision of dataframes to 2
        self.timeseries_point_dataframe = self.timeseries_point_dataframe.round(2)

        self.timeseries_point_json = self.timeseries_point_dataframe.astype(str).to_json()

        
        encoder.FLOAT_REPR = lambda o: format(o, '.2f')
        # Rounding precision of jsons to 2
        self.timeseries_point_json = json.loads(self.timeseries_point_json)



    def make_json_to_llm(self):
         
        self.json_to_llm = {
            
            'var_code': self.variable,
            'var_name': self.variables_dict['Variable'],
            'unit': self.variables_dict['Unit'],
            'description': self.variables_dict['Description'],
            'status': self.status_dict,

            'values': {
            'timeseries in unit': self.timeseries_point_json
            }

        }