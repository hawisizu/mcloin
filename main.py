import logging
import urllib.request, json
import os
import pandas
import math
import time
from math import radians, cos, sin, asin, sqrt
import re
from geopy.distance import geodesic

#dict with all info of all restaurants
mc_list = {}

commune_list = {}

def init_logger():
    logging.basicConfig(level=logging.INFO,handlers=[
        logging.FileHandler(filename='example.log', mode='w'),
        logging.StreamHandler()
    ])
    logging.getLogger('imdb.parser.http.piculet').setLevel(logging.WARNING)


def import_mc_list_from_square(lat1,lng1,lat2,lng2):

    # request example:
    # https://uws2.mappy.net/data/poi/5.3/applications/mcdonalds?bbox=45.058001435398296,-21.884765625,47.60616304386874,22.939453125&max=100
    base_url = "http://uws2.mappy.net/data/poi/5.3/applications/mcdonalds"
    url = base_url + "?bbox=" + str(lat1) + "," + str(lng1) + "," + str(lat2) + "," + str(lng2) + "&max=500"
    global mc_list

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        pois = data["pois"]

        logging.info("loaded "+ str(len(pois)) + " Mc Donalds")

        for poi in pois:
            mc_id = poi["id"]
            if mc_id not in mc_list:
                mc_list[mc_id] = {
                    "mappy_id":mc_id,
                    "name":poi["name"],
                    "lat":poi["lat"],
                    "lng":poi["lng"],
                }
                logging.debug("imported mc id: "+ mc_id)
            else:
                logging.debug("mc id already known: "+ mc_id)


def import_them_all(min_lat, max_lat, min_lng, max_lng):
    for lat in range (min_lat,  max_lat -1):
        for lng in range (min_lng,  max_lng -1):
            import_mc_list_from_square(lat, lng, lat + 1, lng +1)


def find_centroid(loc1, loc2, loc3):
    return (loc1[0] + loc2[0] + loc3[0]) / 3, (loc1[1] + loc2[1] + loc3[1]) / 3


def closest_mc_donald(location):
    min_dist = 1000
    closest_mc_id = None

    for mc_id in mc_list:
        distance = haversine(mc_list[mc_id]["lng"], mc_list[mc_id]["lat"], location[1], location[0])
        if (distance < min_dist):
            closest_mc_id = mc_id
            min_dist = distance
    logging.debug("[haversine] Closest McDo from " + str(location) + " is " + mc_list[closest_mc_id]["name"] + ", at " + str(min_dist) + " km.")
    return (closest_mc_id, min_dist)


def find_5_closest_mc_donalds(location):
    closest_list=[]
    for mc_id in mc_list:
        distance = haversine(mc_list[mc_id]["lng"], mc_list[mc_id]["lat"], location[1], location[0])
        # distance_geodesic =  geodesic((mc_list[mc_id]["lat"], mc_list[mc_id]["lng"]), location).kilometers

        if len(closest_list) < 5 or distance < closest_list[4]['distance']:
            closest_list.append({
                "distance": distance,
                "mc_id": mc_id,
                "name": mc_list[mc_id]["name"]
            })
            closest_list = sorted(closest_list, key=lambda mc_do: mc_do["distance"])

        if len(closest_list) == 6:
            closest_list.pop()

    return closest_list


def haversine(lon1, lat1, lon2, lat2):
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371* c
    return km


def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False


def import_go2poi_mc_list():
    df = pandas.read_csv('go2poi_mc_list.csv', sep=',', header=0, encoding = "ISO-8859-1")
    found = 0

    for row_index, mcdo in df.iterrows():
        if not isfloat(mcdo['lng']) or not isfloat(mcdo['lat']) or math.isnan(float(mcdo['lng'])) or math.isnan(float(mcdo['lat'])):
            logging.info("No Lat / Long info for commmune: " + mcdo['name'])
        else:
            closest_mc_id, min_dist = closest_mc_donald((mcdo['lat'],mcdo['lng']))
            if min_dist < 1:
                logging.debug("line " + str(row_index) + " of go2poi list (" + mcdo['town'] + ") correspond to " + mc_list[closest_mc_id]["name"])
                found += 1
            else:
                logging.info("line " + str(row_index) + " of go2poi list (" + mcdo['town'] + ") has no equivalent in Mappy: " + str(mcdo['lat']) + ", " + str(mcdo['lng']))

    logging.info("found "+ str(found) + " of the " + str(df.shape[0]) + " McDonalds of the go2poi list")



def check_all_communes():
    df = pandas.read_csv('communes.csv', sep=',', header=0, dtype={'departement': str, 'code_insee': str})

    furthest_commune_dist = 0
    furthest_commune_name = None
    furthest_commune_closest_mc_id = None

    for row_index, commune in df.iterrows():
        progress = str(row_index + 1).zfill(5) + " / " + str(df.shape[0])

        if not isfloat(commune['lat']) or not isfloat(commune['lng']) or \
            math.isnan(float(commune['lat'])) or math.isnan(float(commune['lng'])):
            logging.info(progress + ": No Lat / Long info for commmune: " + commune['nom_reel'])

        elif commune['departement'] == "2A" or commune['departement'] == "2B" or commune['departement'] > "95" :
            logging.info(progress + ": skipping " + commune['nom_reel'] + " as not on continental France")

        else:
            commune_loc = float(commune['lat']), float(commune['lng']),
            closest_mc_id, min_dist = closest_mc_donald(commune_loc)
            logging.info(progress + ": Closest McDo from " + commune['nom_reel'] + " is " + mc_list[closest_mc_id]["name"] + ", at " + str(min_dist) + " km.")

            commune_list[commune['code_insee']] = {
                "nom_commune": commune['nom_reel'],
                "code_insee": commune['code_insee'],
                "lat":commune['lat'],
                "lng":commune['lng'],
                "closest_mc_id": closest_mc_id,
                "distance_to_mc_do": min_dist,
                "5_closest_mc_dos": find_5_closest_mc_donalds(commune_loc)
            }

            if min_dist > furthest_commune_dist:
                furthest_commune_dist = min_dist
                furthest_commune_name = commune['nom_reel']
                furthest_commune_closest_mc_id = closest_mc_id

    logging.info("Commune further away from any McDo: " + furthest_commune_name + ", which is " + str(furthest_commune_dist) + " km away from Mc Do: " + mc_list[furthest_commune_closest_mc_id]["name"])

    with open("communes.json", 'w') as outfile:
        json.dump(commune_list, outfile, indent=2)

    logging.info(str(len(commune_list)) + " communes distance to nearest McDo evaluated, and saved to local file")


if __name__ == '__main__':
    init_logger()

    mc_list_file_name = "mclist.json"
    communes_file_name = "communes.json"

    if os.path.isfile(mc_list_file_name):
        json_data=open(mc_list_file_name).read()
        mc_list = json.loads(json_data)
        logging.info(str(len(mc_list)) + " Mc Donalds loaded from local file")
    else:
        import_them_all(41,52,-5,9) # a square that has the entire metropolitan France
        with open(mc_list_file_name, 'w') as outfile:
            json.dump(mc_list, outfile, indent=2)
        logging.info(str(len(mc_list)) + " Mc Donalds loaded from web, and saved to local file")



    check_all_communes()

    # import_go2poi_mc_list()

