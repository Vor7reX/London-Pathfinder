"""
ETL Script for London Pathfinder.
Fetches real tube network data (stations and connections) from open source repositories,
calculates geographical weights (travel times) using the Haversine formula,
and compiles the routing graph dataset.
"""
import urllib.request
import math
import json
import os

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on the Earth's surface.
    Returns the distance in kilometers.
    """
    earth_radius_km = 6371.0 
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c

def main():
    print("INFO: Connecting to open source database (London Tube)...")
    
    # 1. Fetch Stations (Nodes)
    stations_url = "https://raw.githubusercontent.com/nicola/tubemaps/master/datasets/london.stations.csv"
    req_stations = urllib.request.urlopen(stations_url)
    lines_stations = req_stations.read().decode('utf-8').strip().split('\n')[1:] # Skip header
    
    stations = []
    coords = {}
    for line in lines_stations:
        if not line: 
            continue
        parts = line.split(',')
        st_id = int(parts[0])
        lat = float(parts[1])
        lon = float(parts[2])
        name = parts[3].strip('"')
        
        stations.append({"id": st_id, "name": name, "lat": lat, "lon": lon})
        coords[st_id] = (lat, lon)
        
    print(f"INFO: Extracted {len(stations)} real stations.")

    # 2. Fetch Connections (Edges)
    connections_url = "https://raw.githubusercontent.com/nicola/tubemaps/master/datasets/london.connections.csv"
    req_connections = urllib.request.urlopen(connections_url)
    lines_connections = req_connections.read().decode('utf-8').strip().split('\n')[1:]
    
    connections = []
    seen_edges = set()
    
    for line in lines_connections:
        if not line: 
            continue
        parts = line.split(',')
        s1 = int(parts[0])
        s2 = int(parts[1])
        line_id = int(parts[2])
        
        # Differentiate edges by line ID to allow parallel tunnels between the same stations
        edge = tuple(sorted((s1, s2))) + (line_id,)
        if edge in seen_edges: 
            continue
        seen_edges.add(edge)

        if s1 in coords and s2 in coords:
            # Calculate geographical weight (Estimated travel time)
            dist_km = calculate_haversine_distance(coords[s1][0], coords[s1][1], coords[s2][0], coords[s2][1])
            
            # Average tube speed: ~33 km/h (0.55 km/min)
            time_min = max(1.0, dist_km / 0.55) 
            
            connections.append({
                "station1": s1, 
                "station2": s2, 
                "line": line_id,
                "time": round(time_min, 2)
            })

    print(f"INFO: Calculated {len(connections)} geographical connections.")

    # 3. Compile and Export Dataset
    dataset = {"stations": stations, "connections": connections}
    os.makedirs('data', exist_ok=True)
    
    output_path = 'data/london_tube.json'
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=4)
        
    print(f"INFO: Dataset successfully compiled and saved to {output_path}")

if __name__ == "__main__":
    main()