# mcloin

This is the french equivalent of the McFurthest point, the point furthest away from a McDonald. 
Loin means far in French, so McFurthest = McLoin. 


## Intro and result
Everything starts from this french twit 
https://twitter.com/JulesGrandin/status/1108404221790093325

complaining about no one having calculated the McFurthest point of France. 
And also from the fact that I want to make some tiny side projects to work on geo data. So this seemed a good excercise.  

I see 3 steps

1. Find the list of McDonalds in France (the McList)
1. Make a function that gives the close McDo from a given location
1. Find the McLoin point. 

### Result: 
The city in France furthest away from any McDonald restaurant is: **Châteauneuf-d'Entraunes**, which is 50.235 km away from: McDonald's GATTIERES



## Get the McList 
Mappy has got a Map that seems easy to scrap
https://fr.mappy.com/app/mcdonalds#/15/M2/Tmcdonalds/N151.12061,6.11309,0.53541,46.35344/Z5/

With the chrome dev tools, we can easily see that a request is done to: 

https://uws2.mappy.net/data/poi/5.3/applications/mcdonalds?bbox=45.058001435398296,-21.884765625,47.60616304386874,22.939453125&max=100

Params are easy to understand: 2 points defined by lat & long, defining a square, and a result cap. 

On peut donc rapidement faire une fonction qui donne tous les mcdos d’un carré données par deux points. 

```python
def import_mc_list_from_square(lat1,lng1,lat2,lng2):
  # request example: 
  # https://uws2.mappy.net/data/poi/5.3/applications/mcdonalds?bbox=45.058001435398296,-21.884765625,47.60616304386874,22.939453125&max=100
  base_url = "http://uws2.mappy.net/data/poi/5.3/applications/mcdonalds"
  url = base_url + "?bbox=" + str(lat1) + "," + str(lng1) + "," + str(lat2) + "," + str(lng2) + "&max=500"

  with urllib.request.urlopen(url) as response:
      data = json.loads(response.read().decode())
      pois = data["pois"]
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
```

Mappy's API also gives us their own ID, which I use to make sure each shop is imported only once. 
I store the results in a global variable `mc_list`. 

Sadly, even when passing 10000 as max, we never get more than 500 results. So we cannot import all french restaurant in one request. 
We need a function parsing France, tiny square by tiny square, and we should check that the number of imported restaurant is always below 500.

So I simply made a method taking a big square, then querying restaurants for all the tiny squares of 1 x 1 within the bounds. Lots of these tiny squares are in the sea, but this is not a problem, Mappy simply returns 0 for those. 

![France](https://www.evernote.com/shard/s517/sh/97d97f2a-0333-4664-818a-91299efcac4d/899bf07a9af0a269/res/6d039011-6f77-4cf3-ae8a-6ba8ecd89fd0/skitch.png)

```python
def import_them_all(min_lat, max_lat, min_lng, max_lng):
    for lat in range (min_lat,  max_lat -1):
        for lng in range (min_lng,  max_lng -1):
            import_mc_list_from_square(lat, lng, lat + 1, lng +1)


#...
import_them_all(41,52,-5,9)
```

I see in the logs that we are always below 500. In total 1480 restuarants are imported, which seems coherent with what I see on google. 

## Calculating distances
Not so hard really: a lot of online examples are really helpful. 
I started by using geopy: 

```python
from geopy.distance import geodesic

#location is a tuple (lat,lng)
def closest_mc_donald(location):
    min_dist = 1000
    closest_mc_id = None
    min_dist = 1000
    for mc_id in mc_list:
        mc_loc = (mc_list[mc_id]["lat"], mc_list[mc_id]["lng"])
        distance = geodesic(mc_loc, location).kilometers
        if (distance < min_dist_geo):
            closest_mc_id = mc_id
            min_dist = distance
    logging.info("[geodesic] Closest McDo from " + str(location) + " is " + mc_list[closest_mc_id]["name"] + ", at " + str(min_dist_geo) + " km.")
```

Which works fine, but is slow. It was taking half a second to compare a location to 1480 McDonalds. 

Looking a big further, I fond on StackOverflow a very nice and very fast approximation which makes the same in about 2 or 3 ms. 

```python
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
```

In the above function, only the line of the distance calculation changes. 

## Find the McFurthest point
I am a bit unsure what is the best strategy here, so I though that I could first start by taking each city of France (commune), whose lat / lng should be easy to find, then find which of these was the farthest away from a McDonald restaurant. 

I found a csv file here: 
https://www.data.gouv.fr/fr/datasets/listes-des-communes-geolocalisees-par-regions-departements-circonscriptions-nd/

This is the csv file "communes.csv"

Parsing this file was quite easy with Pandas. Mappy api gave us McDonalds only for Continental France, so no Corsica and no outer sea territories! 
Also, a lot of lines were missing the lat / lng, and some had weird formats with comas instead of dots. 

```python
def check_all_communes():
    df = pandas.read_csv('communes.csv', sep=';', header=0)

    furthest_commune_dist = 0
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
```

## Next Steps
* trying to find really the furthest point, instead of calculating the furthest from the all teh center of cities. But this is a bit more challenging, I have to find strategies here, as taking a point each 100 m seems unscalable. 
* make a beautiful map with colours. I know, this has been done already, but as said, this is more an exercice for me than anything else. 
