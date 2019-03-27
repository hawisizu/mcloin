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






def import_mac_list_from_square(lat1,lng1,lat2,lng2):

    # reuqest sample
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
                if "townCode" in poi:
                    mc_list[mc_id]["town_code"] = poi["townCode"]

                logging.debug("imported mc id: "+ mc_id)
            else:
                logging.debug("mc id already known: "+ mc_id)


def import_them_all(min_lat, max_lat, min_lng, max_lng):
    for lat in range (min_lat,  max_lat -1):
        for lng in range (min_lng,  max_lng -1):
            import_mac_list_from_square(lat, lng, lat + 1, lng +1)


def closest_mc_donald(location):

    min_dist = 1000
    closest_mc_id = None

#    #geodesic
#    min_dist_geo = 1000
#    start_time = time.time()
#    for mc_id in mc_list:
#        mc_loc = (mc_list[mc_id]["lat"], mc_list[mc_id]["lng"])
#        distance = geodesic(mc_loc, location).kilometers
#        if (distance < min_dist_geo):
#            closest_mc_id = mc_id
#            min_dist_geo = distance
#    logging.info("[geodesic] Closest McDo from " + str(location) + " is " + mc_list[closest_mc_id]["name"] + ", at " + str(min_dist_geo) + " km.")
#    elapsed_time = time.time() - start_time
#    logging.info(f'geodesic:  {elapsed_time}')

    #haversine
    #start_time = time.time()
    for mc_id in mc_list:
        distance = haversine(mc_list[mc_id]["lng"], mc_list[mc_id]["lat"], location[1], location[0])
        if (distance < min_dist):
            closest_mc_id = mc_id
            min_dist = distance
    logging.debug("[haversine] Closest McDo from " + str(location) + " is " + mc_list[closest_mc_id]["name"] + ", at " + str(min_dist) + " km.")
    #elapsed_time = time.time() - start_time


    return (closest_mc_id, min_dist)



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


def check_all_communes():
    df = pandas.read_csv('communes.csv', sep=';', header=0)

    furthest_commune_dist = 0
    furthest_commune_insee_id = None
    furthest_commune_name = None
    furthest_commune_closest_mc_id = None




    for row_index, commune in df.iterrows():
        progress = str(row_index + 1).zfill(5) + " / " + str(df.shape[0])

        problem=None

        if not isfloat(commune['latitude']) or not isfloat(commune['longitude']) or \
            math.isnan(float(commune['latitude'])) or math.isnan(float(commune['longitude'])):
            logging.info(progress + ": No Lat / Long info for commmune: " + commune['nom_commune'])

        elif commune['EU_circo'] == 'Outre-Mer' or commune['nom_région'] == 'Corse' :
            logging.info(progress + ": skipping " + commune['nom_commune'] + " as not on continental France")

        else:
            commune_loc = float(commune['latitude']), float(commune['longitude']),
            closest_mc_id, min_dist = closest_mc_donald(commune_loc)
            logging.info(progress + ": Closest McDo from " + commune['nom_commune'] + " is " + mc_list[closest_mc_id]["name"] + ", at " + str(min_dist) + " km.")

            commune_list[commune['code_insee']] = {
                "nom_commune": commune['nom_commune'],
                "code_insee": commune['code_insee'],
                "closest_mc_id": closest_mc_id,
                "distance_to_mc_do": min_dist,
            }

            if min_dist > furthest_commune_dist:
                furthest_commune_dist = min_dist
                furthest_commune_name = commune['nom_commune']
                furthest_commune_closest_mc_id = closest_mc_id



    logging.info("Commune further away from any McDo: " + furthest_commune_name + ", which is " + str(furthest_commune_dist) + " km away from Mc Do: " + mc_list[furthest_commune_closest_mc_id]["name"])


    with open("communes.json", 'w') as outfile:
        json.dump(commune_list, outfile, indent=2)

    logging.info(str(len(commune_list)) + " communes distance to nearest McDo evaluated, and saved to local file")


if __name__ == '__main__':
    init_logger()
    logging.info("start")

    mc_list_file_name = "mclist.json"

    if os.path.isfile(mc_list_file_name):
        json_data=open(mc_list_file_name).read()
        mc_list = json.loads(json_data)
        logging.info(str(len(mc_list)) + " Mc Donalds loaded from local file")
    else:
        import_them_all(41,52,-5,9) # a square that has the entire metropolitan France
        with open(mc_list_file_name, 'w') as outfile:
            json.dump(mc_list, outfile, indent=2)
        logging.info(str(len(mc_list)) + " Mc Donalds loaded from web, and saved to local file")

    closest_mc_donald((49.571239, 4.201151))
    check_all_communes()


    logging.info("end")
