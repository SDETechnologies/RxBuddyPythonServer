import requests
import time
import mysql.connector
import os

db = mysql.connector.connect(
    # host = os.environ['DB_HOST'],
    user = os.environ['DB_USER'],
    password = os.environ['DB_PASSWORD'],
    database = "rxbuddy",
    instance_connection_name = os.environ['DB_SOCKET_PATH']
    )

cur = db.cursor()


API_KEY = os.environ['PLACES_API_KEY']
MILE_TO_METER = 1609.34

# url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input=Museum%20of%20Contemporary%20Art%20Australia&inputtype=textquery&fields=formatted_address%2Cname%2Crating%2Copening_hours%2Cgeometry&key=YOUR_API_KEY"

def buildFindPlaceRequest(textInput, inputType = "textquery"):
    requestURL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
    requestURL += "input=" + textInput
    requestURL += "&inputtype=" + inputType
    requestURL += '&key=' + API_KEY
    return requestURL

def findPlace(textInput):
    requestURL = buildFindPlaceRequest(textInput)
    return requests.get(requestURL).json()

def geocodeWithZipcode(zipCode):
    if len(zipCode) != 5:
        print('invalid zip code! (does not have 5 characters)')
        return None
    requestURL = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + zipCode + '&key=' + API_KEY
    data = requests.get(requestURL).json()
    print('data: ',data)
    try:
        locationData = data["results"][0]["geometry"]["location"]
        [lat, long] = [locationData["lat"],locationData["lng"]]
        return [lat, long]
    except IndexError:
        print('No zipcode data found')
        return None

# url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=-33.8670522%2C151.1957362&radius=1500&type=restaurant&keyword=cruise&key=YOUR_API_KEY"
def getFindPlacesData(zipCode, radiusInMiles):
    allResults = []
    zipcodeData = geocodeWithZipcode(zipCode)
    if zipcodeData == None:
        return None
    [lat, lon] = geocodeWithZipcode(zipCode)
    
    # [lat, lon] = ['33.8', '-84.3']
    
    radiusInMeters = radiusInMiles * MILE_TO_METER
    requestURL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=' + str(lat) + '%2C' + str(lon) + '&radius=' + str(radiusInMeters) + '&type=pharmacy&key=' + API_KEY
    print('requestURL: ', requestURL)
    data = requests.get(requestURL).json()
    allResults += data["results"]
    nextPageToken = ''
    time.sleep(5)
    try:
        nextPageToken = data["next_page_token"] 
        print('nextPageToken: ', nextPageToken)
    except KeyError:
        print('no next page token found')
        print('data: ', data)
        nextPageToken = None
    originalURL = requestURL
    while nextPageToken != None:
        
        requestURL = originalURL + '&pagetoken=' + nextPageToken
        print('requestURL: ', requestURL)
        data = requests.get(requestURL).json()
        # print('data: ', data)
        allResults += data["results"]
        time.sleep(5)
        try:
            nextPageToken = data["next_page_token"]
            # print('\nnextPageToken: ', nextPageToken)
        except KeyError:
            print('no next page token found')
            nextPageToken = None
    # return data["results"]
    # return data
    return allResults




def getPlaceDetails(placeID):
    requestURL = 'https://maps.googleapis.com/maps/api/place/details/json?place_id=' + placeID + '&key=' + API_KEY
    test = requests.get(requestURL).json()
    # print('test: ', test)
    return requests.get(requestURL).json()["result"]

def insertPharmacy(name, address, phoneNumber, businessStatus, googlePlaceID, googleURL, locationData, cursor):
    print('inserting pharmacy with placeID: ', googlePlaceID)
    lat = locationData["lat"]
    lng = locationData["lng"]
    geog_type = "POINT(%s %s)" % (lat, lng)
    # geog_type = "ST_GeomFromText(%s,3426)" % geog_type
    # geog_type = "ST_GeomFromText('POINT(33.64380000000001 -84.01697999999999)',3426)"
    print('geog_type: ', geog_type)
    data = [name, address, phoneNumber, businessStatus, googlePlaceID, googleURL, geog_type]
    # data = [name, address, phoneNumber, businessStatus, googlePlaceID, googleURL]
    print('[name, address, phoneNumber, businessStatus, googlePlaceID, googleURL, geog_type]: ', ', '.join(data))
    sql = "INSERT INTO pharmacies (name, address, phone_number, business_status, google_place_id, google_url, location) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    sql = "INSERT INTO pharmacies (name, address, phone_number, business_status, google_place_id, google_url, location) VALUES (%s,%s,%s,%s,%s,%s,ST_GeomFromText('POINT(33.64380000000001 -84.01697999999999)',3426))"
    sql = "INSERT INTO pharmacies (name, address, phone_number, business_status, google_place_id, google_url, location) VALUES (%s,%s,%s,%s,%s,%s,ST_GeomFromText(%s,4326))"
    # test = sql % (name, address, phoneNumber, businessStatus, googlePlaceID, googleURL, geog_type)
    # test = sql % (name, address, phoneNumber, businessStatus, googlePlaceID, googleURL)
    # print('test: ', test)
    cursor.execute(sql, data)

def checkPharmacyExists(placeID):
        sql = 'SELECT * FROM pharmacies where google_place_id = %s'
        cur.execute(sql, [placeID])
        result = cur.fetchall()
        print('result: ', result)
        if len(result) == 0:
            return False
        return True
    
    
def insertPharmacies(testJSON, cursor):
    for tempJSON in testJSON:
        print('\ntempJSON: ', tempJSON, '\n')
        tempPlaceID = tempJSON["google_place_id"]
        # tempPlaceID = tempJSON["place_id"]
        print('tempPlaceID: ', tempPlaceID)
        if checkPharmacyExists(tempPlaceID) == False:
            name = tempJSON["name"]
            address = tempJSON["address"]
            phoneNumber = tempJSON["phone_number"]
            businessStatus = tempJSON["business_status"]
            placeID = tempJSON["google_place_id"]
            googleURL = tempJSON["google_url"]
            locationData = tempJSON["location"]
            insertPharmacy(name, address, phoneNumber, businessStatus, placeID, googleURL, locationData, cursor)
    cursor.close()
    db.commit()
    

def listenForCheckZipcodes():
    while True:
        print('Waiting for request')
        response = requests.get('http://localhost:3002/api/checkzipcode')
        responseData = response.json()
        print('data: ', responseData)
        waitingForRequest = responseData["waiting_for_request"]
        zipcode = responseData["zipcode"]
        print('waiting for request: ', waitingForRequest)
        if waitingForRequest and zipcode != '':
            test = getFindPlacesData(zipcode, 50)
            if test == None:
                print('No data found')
                waitingForRequest = False
                response = requests.post('http://localhost:3002/api/checkzipcode', json = {
                    "waiting_for_request": False,
                    "zipcode": zipcode,
                    "data": {},
                    "data_loaded": False
                    })
                break
            testJSON = convertToJSON(test)
            # printPlaceData(test)
            newCursor = db.cursor()
            insertPharmacies(testJSON, newCursor)
            response = requests.post('http://localhost:3002/api/checkzipcode', json = {
                "waiting_for_request": False,
                "zipcode": zipcode,
                "data": testJSON,
                "data_loaded": True
                })
        time.sleep(5)

def convertToJSON(test):
    dataList = []
    for result in test:
        name = result["name"]
        placeID = result["place_id"]
        businessStatus  = result["business_status"]
    
        placeDetails = getPlaceDetails(placeID)
        try:
            address = placeDetails["formatted_address"]
            phoneNumber = placeDetails["international_phone_number"]
            typeList = placeDetails["types"]
            googleURL = placeDetails["url"]
            locationData = placeDetails["geometry"]["location"]
            tempJSON = {
                "name": name,
                "address": address,
                "phone_number": phoneNumber,
                "business_status": businessStatus,
                "google_place_id": placeID,
                "google_url": googleURL,
                "location": locationData
                }
            dataList.append(tempJSON)
            # print("Name: ", name, ", Status: ", businessStatus, ", ", address, ", ", phoneNumber, ", ", typeList)
            # insertPharmacy(name, address, phoneNumber, businessStatus, placeID, googleURL)
        except KeyError:
            print('could not find placeDetails')   
    return dataList

def printPlaceData(test):
    for result in test:
        name = result["name"]
        placeID = result["place_id"]
        businessStatus  = result["business_status"]
    
        placeDetails = getPlaceDetails(placeID)
        try:
            address = placeDetails["formatted_address"]
            phoneNumber = placeDetails["international_phone_number"]
            typeList = placeDetails["types"]
            googleURL = placeDetails["url"]
            print("Name: ", name, ", Status: ", businessStatus, ", ", address, ", ", phoneNumber, ", ", typeList)
            # insertPharmacy(name, address, phoneNumber, businessStatus, placeID, googleURL)
        except KeyError:
            print('could not find placeDetails')       

def loadPharmacyData(zipcode):
    print('loadPharmacyData')
    test = getFindPlacesData(zipcode, 50)
    testJSON = convertToJSON(test)
    newCursor = db.cursor()
    insertPharmacies(testJSON, newCursor)
    return test
    

# searchText = 'pharmacy'
# requestURL = buildFindPlaceRequest(searchText)
# print('requestURL: ', requestURL)
# response = requests.get(requestURL).json()

# testPlaceID = 'ChIJUU4R-hqz9YgR3ulvxnIIwsk'
# placeDetailsResponse = getPlaceDetails(testPlaceID)

# # # test = geocodeWithZipcode('30094')
# test = getFindPlacesData('30094', 50)
# # newCursor = db.cursor()
# for result in test:
#     name = result["name"]
#     placeID = result["place_id"]
#     businessStatus  = result["business_status"]

#     placeDetails = getPlaceDetails(placeID)
#     # print('placeDetails: ', placeDetails)
#     try:
#         address = placeDetails["formatted_address"]
#         phoneNumber = placeDetails["international_phone_number"]
#         typeList = placeDetails["types"]
#         googleURL = placeDetails["url"]
#         locationData = placeDetails["geometry"]["location"]
#         # print('locationData: ', locationData)
#         lat = locationData["lat"]
#         lng = locationData["lng"]
#         print("Name: ", name, ", Status: ", businessStatus, ", ", address, ", ", phoneNumber, ", ", typeList, 'latitude: ', lat, ', longitude: ', lng)
#         insertPharmacy(name, address, phoneNumber, businessStatus, placeID, googleURL, locationData, newCursor)
#     except KeyError as e:
#         print('could not find placeDetails. Error: ', str(e))

# test = loadPharmacyData('30094')
# cursor = db.cursor()
# sql = "INSERT INTO pharmacies (name, address, phone_number, business_status, google_place_id, google_url, location) VALUES ('Kroger Pharmacy','1745 GA-138, Conyers, GA 30013, USA','+1 770-922-0447','OPERATIONAL','ChIJmzlACcO09YgRke0e587OG-o','https://maps.google.com/?cid=16869304217282473361',ST_GeomFromText('POINT(33.64380000000001 -84.01697999999999)',3426))"
# cursor.execute(sql)
# db.commit()

# name = 'Kroger Pharmacy'
# address = '1745 GA-138, Conyers, GA 30013, USA'
# phoneNumber = '+1 770-922-0447'
# businessStatus = 'OPERATIONAL'
# placeID = 'ChIJmzlACcO09YgRke0e587OG-o'
# googleURL = 'https://maps.google.com/?cid=16869304217282473361'
# location = "ST_GeomFromText('POINT(33.64380000000001 -84.01697999999999)',3426))"
# locationData = {"lat": 33.64380000000001, "lng": -84.01697999999999}
# insertPharmacy(name, address, phoneNumber, businessStatus, placeID, googleURL, locationData, cursor)
# db.commit()


# loadPharmacyData('30094')    
    
# # # test2 = getPlaceDetails('ChIJmzlACcO09YgRke0e587OG-o')

# listenForCheckZipcodes()
# # exists = checkPharmacyExists('ChIJjYAXQFUG9YgRXqK-XPI96yM')
# # print(exists)