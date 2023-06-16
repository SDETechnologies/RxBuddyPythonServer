import requests
import os
import json
import pandas as pd
import urllib.request
from flask import Flask
from flask_restful import Resource, Api, reqparse
from google_place_util import *
from flask import request
from flask_cors import CORS, cross_origin

ENV_TYPE = os.environ.get('ENV_TYPE')
PROD_ORIGIN = "https://rxbuddy.net"
DEV_ORIGIN = "http://localhost:3005"

DATA_FILE_NAME = 'data'
DATA_FILE_TYPE = 'csv'
# DATA_FILE_TYPE = 'xlsx'
DATA_FILE_NAME_WHOLE = DATA_FILE_NAME + '.' + DATA_FILE_TYPE

print('environment type: ', ENV_TYPE)

if ENV_TYPE == 'dev':
    origin = DEV_ORIGIN
else:
    origin = PROD_ORIGIN

app = Flask(__name__)
api = Api(app)
# cors = CORS(app, resources={r"/*": {"origins": "https://rxbuddy.net"}})
cors = CORS(app, resources={r"/*": {"origins": origin}})

data = {
        'waiting_for_request': True,
        'zipcode': None,
        'data_loaded': False,
        'data': None
        }

def getFetchURL(suffix):
    if ENV_TYPE == 'dev':
        base = 'http://localhost:5000'
    else:
        base = 'https://api.rxbuddy.net'
    return os.path.join(base, suffix)

def getCheckZipcodeData():
    return requests.get('https://api.rxbuddy.net/api/checkzipcode').json()

def getZipcodeData(zipcode):
    data = getFindPlacesData(zipcode, 50)
    jsonData = convertToJSON(data)
    return jsonData

def getStatus(df, row):
    return df.loc[row][11]

def getCurrentRows(df):
    return df.loc[df[' Status'] == 'Current']
    

def getCurrentGenericShortages(df):
    currentRows = getCurrentRows(df)
    return currentRows['Generic Name'].unique().tolist()

def getDF():
    df = pd.read_csv(DATA_FILE_NAME_WHOLE)
    return df

def getData():
    # response = requests.get('https://www.accessdata.fda.gov/scripts/drugshortages/Drugshortages.cfm')
    # print(response.json)
    urllib.request.urlretrieve('https://www.accessdata.fda.gov/scripts/drugshortages/Drugshortages.cfm',DATA_FILE_NAME_WHOLE)

class CheckZipcode(Resource):
    def get(self):
        return data, 200
    def post(self):
        # print('request.form: ', request.form)
        # print('request.data: ', request.data)
        # postData = request.form
        postData = json.loads(request.data)
        print('postData: ', postData)
        zipcode = postData['zipcode']
        print('zipcode: ', zipcode)
        data['zipcode'] = zipcode
        data['waiting_for_request'] = False
        data['data_loaded'] = False
        jsonData = getZipcodeData(zipcode)
        newCursor = db.cursor()
        insertPharmacies(jsonData, newCursor)
        data['data'] = jsonData
        data['waiting_for_request'] = True
        data['data_loaded'] = True
        print('done getting data')
        return data,200




class ShortageData(Resource):
    def get(self):
        getData()
        df = getDF()

class CurrentGeneric(Resource):
        def get(self):
            getData()
            df = getDF()
            currentGenericDrugs = getCurrentGenericShortages(df)
            currentRows = getCurrentRows(df)
            # return json.dumps(currentRows.values.tolist())
            return currentGenericDrugs

api.add_resource(CheckZipcode, '/checkzipcode')
api.add_resource(CurrentGeneric, '/currentgeneric')

# print(getCheckZipcodeData())

# testData = getFindPlacesData('30094', 50)
# testJSON = getZipcodeData('30094')
# data['data'] = testJSON


# print('testData: ', testData)

print('---------------------------------------')

if __name__ == '__main__':
    app.run()  # run our Flask app