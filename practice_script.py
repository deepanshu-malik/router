import folium
import requests

from pydantic import BaseModel

service = 'route'
version = 'v1'
profile = 'cyling'
host = 'http://localhost:5000'

url = f'{host}/{service}/{version}/{profile}'
map_path = '/mnt/c/Users/Deepanshu/projects/router/map.html'

class Point(BaseModel):
    latitude: float
    longitude: float

    def __str__(self):
        return f'{self.latitude},{self.longitude}'

# 29.00729086187103, 77.00476960714381
mine = Point(latitude=29.00729086187103, longitude=77.00476960714381)
# 29.00221440153974, 77.005200097138
vinit = Point(latitude=29.00221440153974, longitude=77.005200097138)
# 29.00433353382278, 77.00552983293501
dahiya = Point(latitude=29.00433353382278, longitude=77.00552983293501)
# 28.642560304398643, 77.17436809125691
kogta = Point(latitude=28.642560304398643, longitude=77.17436809125691)
# 28.49530595054764, 77.08923236185112
cyber_hub = Point(latitude=28.49530595054764, longitude=77.08923236185112)
# 29.004417462354244, 77.00433396396643
center_point = Point(latitude=29.004417462354244, longitude=77.00433396396643)

# 34.68274756641921, 75.45878247604018
random_1 = Point(latitude=34.68274756641921, longitude=75.45878247604018)
# 33.5139385272305, 75.20363865249003
random_2 = Point(latitude=33.5139385272305, longitude=75.20363865249003)
# 34.51337424423889, 75.37647791484817
random_center = Point(latitude=34.51337424423889, longitude=75.37647791484817)


points = [mine, vinit, dahiya, kogta, cyber_hub]
random_points = [random_1, random_2, random_center]

# points = random_points
# center_point = random_center

def get_folium_map(center_point: Point, points: list[Point], zoom_level: int = 14) -> folium.Map:
    folium_map = folium.Map(
        location=[center_point.latitude, center_point.longitude], zoom_start=zoom_level)

    for point in points:
        folium.Marker(location=[point.latitude, point.longitude],
                      popup='Point').add_to(folium_map)

    return folium_map

# folium_map = get_folium_map(center_point, points)
# folium_map.save(map_path)

coordinates = ';'.join([str(point) for point in points])

response = requests.get(f'{url}/{coordinates}', params={
    'overview': 'full',
    'steps': 'true',
    'geometries': 'geojson',
    'alternatives': 'true',
    })

if response.status_code == 200:
    data = response.json()
    # print(data)
    # Extract the route geometry from the response
    route_geometry = data['routes'][0]['geometry']
    print(route_geometry)

    # Create a folium map centered at the first point
    folium_map = get_folium_map(center_point, points)

    popup_text = f"Distance: {data['routes'][0]['distance']} meters<br>Duration: {data['routes'][0]['duration']} seconds"
    popup = folium.Popup(popup_text, max_width=300)

    route_coordinates = [[point[1], point[0]] for point in data['routes'][0]['geometry']['coordinates']]
    folium.PolyLine(
        locations=route_coordinates, color='blue', weight=5, popup=popup).add_to(folium_map)
    print(route_coordinates)
    print(points)
    # Save the map to an HTML file
    folium_map.save(map_path)
else:
    print(f"Error: {response.status_code} - {response.text}")
