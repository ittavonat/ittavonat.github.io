import requests
import json
import time
from datetime import datetime
import shutil
import os

GRAPHQL_ENDPOINT = "https://emma.mav.hu/otp2-backend/otp/routers/default/index/graphql"
OUTPUT_FILE = "/tmp/train_data.json"
STATIC_FILE = "train_data.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def get_service_day():
    now = datetime.now()
    return now.strftime("%Y-%m-%d")

def fetch_vehicle_positions(session):
    query = '''
    {
        vehiclePositions(
          swLat: 45.5,
          swLon: 16.1,
          neLat: 48.7,
          neLon: 22.8,
          modes: [RAIL, RAIL_REPLACEMENT_BUS]
        ) {
          trip {
            gtfsId
            tripShortName
            tripHeadsign
          }
          vehicleId
          lat
          lon
          label
          speed
          heading
        }
    }'''

    response = session.post(GRAPHQL_ENDPOINT, headers=HEADERS, json={"query": query})
    response.raise_for_status()
    return response.json()["data"]["vehiclePositions"]

def fetch_trip_details(session, gtfs_id, service_day):
    query = f'''
    {{
        trip(id: "{gtfs_id}", serviceDay: "{service_day}") {{
          gtfsId
          tripHeadsign
          trainCategoryName
          trainName
          route {{
            longName(language: "hu")
            shortName
          }}
          stoptimes {{
            stop {{
              name
              lat
              lon
              platformCode
            }}
            realtimeArrival
            realtimeDeparture
            arrivalDelay
            departureDelay
            scheduledArrival
            scheduledDeparture
          }}
        }}
    }}'''

    response = session.post(GRAPHQL_ENDPOINT, headers=HEADERS, json={"query": query})
    response.raise_for_status()
    return response.json().get("data", {}).get("trip", {})

def main():
    service_day = get_service_day()
    print("Fetching vehicle positions...")

    with requests.Session() as session:
        vehicles = fetch_vehicle_positions(session)

        all_data = {
            "lastUpdated": int(time.time()),
            "vehicles": []
        }

        for vehicle in vehicles:
            trip = vehicle.get("trip")
            gtfs_id = trip.get("gtfsId") if trip else None
            print("Fetching data for", gtfs_id)
            trip_details = fetch_trip_details(session, gtfs_id, service_day) if gtfs_id else {}

            trip_short_name = trip.get("tripShortName")
            trip_headsign = trip.get("tripHeadsign")
            vehicle_id = vehicle.get("vehicleId")
            lat = vehicle.get("lat")
            lon = vehicle.get("lon")
            label = vehicle.get("label")
            speed = vehicle.get("speed")
            heading = vehicle.get("heading")
            # trip_headsign = trip_details.get("tripHeadsign") duplicate info
            train_cat = trip_details.get("trainCategoryName")
            train_name = trip_details.get("trainName")
            route_long_name = trip_details.get("route").get("longName")
            route_short_name = trip_details.get("route").get("shortName") # Useless garbage
            stop_times = trip_details.get("stoptimes")

            stops_compressed = []
            for stop in stop_times:
                st = stop.get("stop")
                s_lat = st.get("lat")
                s_lon = st.get("lon")
                s_name = st.get("name")
                vagany = st.get("platformCode")
                realtime_arr = stop.get("realtimeArrival")
                realtime_dep = stop.get("realtimeDeparture")
                sched_arr = stop.get("scheduledArrival")
                sched_dep = stop.get("scheduledDeparture")
                arr_delay = stop.get("arrivalDelay")
                dep_delay = stop.get("departureDelay")
                stops_compressed.append({
                    "name": s_name,
                    "ra": realtime_arr,
                    "rd": realtime_dep,
                    "sa": sched_arr,
                    "sd": sched_dep,
                    "a": arr_delay,
                    "d": dep_delay,
                    "v": vagany
                })


            name = trip_short_name
            # The field can contain weirdly long strings, but I found no other way to get the short labels like S60 from the API
            if route_long_name != None and len(route_long_name) < 6:
                name = "[" + route_long_name + "] " + trip_short_name


            all_data["vehicles"].append({
                "id": gtfs_id,
                "name": name,
                "headsgn" : trip_headsign,
                "lat" : lat,
                "lon" : lon,
                "sp" : speed,
                "hd" : heading,
                "stops" : stops_compressed
            })

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, separators=(",", ":"), ensure_ascii=False)
        try:
            if os.path.exists(STATIC_FILE): shutil.copy(STATIC_FILE, STATIC_FILE + ".bak")
            shutil.copy(OUTPUT_FILE, STATIC_FILE)
        except Exception as e:
            print(f"Error putting train_data.json to the webserver location. ERROR: {e}")
        print(f"Saved data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
