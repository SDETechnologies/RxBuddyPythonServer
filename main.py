import requests
import os
from flask import Flask
from flask_restful import Resource, Api, reqparse
from google_place_util import *
from flask import request

app = Flask(__name__)
api = Api(app)

data = {
        'waiting_for_request': True,
        'zipcode': None,
        'data_loaded': False,
        'data': None
        }


def getCheckZipcodeData():
    return requests.get('https://api.rxbuddy.net/api/checkzipcode').json()

def getZipcodeData(zipcode):
    data = getFindPlacesData(zipcode, 50)
    jsonData = convertToJSON(data)
    return jsonData

class CheckZipcode(Resource):
    def get(self):
        return data, 200
    def post(self):
        postData = request.form
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
        # return data,200

api.add_resource(CheckZipcode, '/checkzipcode')

# print(getCheckZipcodeData())

# testData = getFindPlacesData('30094', 50)
# testJSON = getZipcodeData('30094')
# data['data'] = testJSON


# print('testData: ', testData)


if __name__ == '__main__':
    app.run()  # run our Flask app