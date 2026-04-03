"""
London Pathfinder - Main Web Application Server
Serves the Flask frontend and handles API requests for routing calculations.
Interfaces with the C++ pathfinder_core module for performance.
"""
from flask import Flask, render_template, request, jsonify
import json
import pathfinder_core
import os
import time

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Initialize the C++ Routing Engine
routing_engine = pathfinder_core.PathFinder()

# Load Network Graph
with open("data/london_tube.json", "r") as f:
    dataset = json.load(f)

# TFL Official Palette and Metadata
LINE_COLORS = {
    1: "#B36305", 2: "#E32017", 3: "#FFD300", 4: "#00782A",
    5: "#EE7C0E", 6: "#F3A9BB", 7: "#A0A5A9", 8: "#9B0056",
    9: "#000000", 10: "#003688", 11: "#0098D4", 12: "#95CDBA",
    13: "#00A4A7", 14: "#6950a1", -1: "#888888"
}

LINE_NAMES = {
    1: "Bakerloo Line", 2: "Central Line", 3: "Circle Line", 4: "District Line",
    5: "East London Line", 6: "Hammersmith & City", 7: "Jubilee Line", 8: "Metropolitan Line",
    9: "Northern Line", 10: "Piccadilly Line", 11: "Victoria Line", 12: "Waterloo & City",
    13: "DLR", 14: "Elizabeth Line", -1: "Interchange"
}

LINE_LOGOS = {
    1: "Bakerloo_line_roundel.png", 2: "Central_line_roundel.png", 3: "Circle_line_roundel.png", 
    4: "District_line_roundel.png", 5: "East_London_line_roundel.png", 6: "H&c_line_roundel.png", 
    7: "Jubilee_line_roundel.png", 8: "Metropolitan_line_roundel.png", 9: "Northern_line_roundel.png", 
    10: "Piccadilly_line_roundel.png", 11: "Victoria_line_roundel.png", 12: "Waterloo_&_City_line_roundel.png",
    13: "DLR_roundel.png", 14: "Elizabeth_line_roundel.png", -1: ""
}

TRANSFER_PENALTY_MINUTES = 5 

# Graph Data Structures
coords = {}
id_to_name = {}
edge_lines = {}
edge_times = {} 
station_lines_map = {} 

def format_time(minutes):
    """Formats estimated travel time into a readable string."""
    m = round(minutes)
    if m < 60:
        return f"{m} min"
    
    hours = m // 60
    remaining_mins = m % 60
    hour_str = "hour" if hours == 1 else "hours"
    
    if remaining_mins == 0:
        return f"{hours} {hour_str}"
    return f"{hours} {hour_str} and {remaining_mins} min"

# Build Graph Structures
for st in dataset["stations"]:
    routing_engine.add_node(st["id"], st["name"], st["lat"], st["lon"])
    coords[st["id"]] = (st["lat"], st["lon"])
    id_to_name[st["id"]] = st["name"]
    station_lines_map[st["id"]] = {}

for conn in dataset["connections"]:
    u, v, line_id = conn["station1"], conn["station2"], conn.get("line", -1)
    travel_time = conn.get("time", 2) 
    
    routing_engine.add_edge(u, v, travel_time, line_id)
    
    if (u, v) not in edge_lines:
        edge_lines[(u, v)] = []
        edge_lines[(v, u)] = []
        
    edge_lines[(u, v)].append(line_id)
    edge_lines[(v, u)].append(line_id)
    
    edge_times[(u, v)] = travel_time
    edge_times[(v, u)] = travel_time
    
    line_name = LINE_NAMES.get(line_id, "Interchange")
    line_color = LINE_COLORS.get(line_id, "#888888")
    line_logo = LINE_LOGOS.get(line_id, "")
    
    if u in station_lines_map: station_lines_map[u][line_name] = {"color": line_color, "logo": line_logo}
    if v in station_lines_map: station_lines_map[v][line_name] = {"color": line_color, "logo": line_logo}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stations')
def get_stations():
    stations = [{"id": k, "name": v} for k, v in id_to_name.items()]
    return jsonify(sorted(stations, key=lambda x: x['name']))

@app.route('/api/network')
def get_network():
    edges = []
    for conn in dataset["connections"]:
        u, v, line_id = conn["station1"], conn["station2"], conn.get("line", -1)
        if u in coords and v in coords:
            edges.append({"coords": [coords[u], coords[v]], "color": LINE_COLORS.get(line_id, "#888888")})
            
    nodes = [{"coord": coords[st_id], "name": id_to_name[st_id], "lines": [{"name": k, "color": v["color"], "logo": v["logo"]} for k, v in station_lines_map[st_id].items()]} for st_id in coords]
    return jsonify({"edges": edges, "nodes": nodes})

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    start_id = data['start']
    target_id = data['target']

    start_time_cpu = time.time()
    path_dijkstra, explored_dijkstra = routing_engine.run_dijkstra(start_id, target_id)
    path_astar, explored_astar = routing_engine.run_astar(start_id, target_id)
    calc_time = time.time() - start_time_cpu

    itinerary_html = f"<div style='margin-bottom: 12px;'>📍 <b>START:</b> {id_to_name[path_astar[0]]}</div>"
    current_line = None
    stops = 0
    partial_time = 0
    total_travel_time = 0
    transfer_nodes = [] 

    for i in range(len(path_astar) - 1):
        u, v = path_astar[i], path_astar[i+1]
        available_lines = edge_lines.get((u, v), [-1])
        chosen_line = current_line if current_line in available_lines else available_lines[0]
        
        leg_time = edge_times.get((u, v), 2)
        total_travel_time += leg_time
        
        if chosen_line != current_line:
            if current_line is not None:
                total_travel_time += TRANSFER_PENALTY_MINUTES
                itinerary_html += f"&nbsp;&nbsp;↳ {stops} stops ({format_time(partial_time)}).<br><div style='margin-top: 4px;'>&nbsp;&nbsp;🛑 Alight at <b>{id_to_name[u]}</b> <i style='color: #d93025;'>(+{TRANSFER_PENALTY_MINUTES} min transit)</i>.</div>"
                
                from_name = LINE_NAMES.get(current_line, 'Interchange')
                from_color = LINE_COLORS.get(current_line, '#888888')
                from_logo = LINE_LOGOS.get(current_line, '')
                
                to_name = LINE_NAMES.get(chosen_line, 'Interchange')
                to_color = LINE_COLORS.get(chosen_line, '#888888')
                to_logo = LINE_LOGOS.get(chosen_line, '')
                
                img_from = f"<img src='/static/line_logo/{from_logo}' style='height: 14px; width: 14px; object-fit: contain; margin-right: 5px; vertical-align: middle;'>" if from_logo else ""
                badge_from = f"<span style='background-color: {from_color}; color: #fff; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; border: 1px solid rgba(0,0,0,0.2); text-shadow: 0 1px 1px rgba(0,0,0,0.3); display: inline-flex; align-items: center; white-space: nowrap;'>{img_from}{from_name}</span>"

                img_to = f"<img src='/static/line_logo/{to_logo}' style='height: 14px; width: 14px; object-fit: contain; margin-right: 5px; vertical-align: middle;'>" if to_logo else ""
                badge_to = f"<span style='background-color: {to_color}; color: #fff; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; border: 1px solid rgba(0,0,0,0.2); text-shadow: 0 1px 1px rgba(0,0,0,0.3); display: inline-flex; align-items: center; white-space: nowrap;'>{img_to}{to_name}</span>"
                
                itinerary_html += f"<div style='margin: 12px 0; padding: 10px; border: 1px solid rgba(0,0,0,0.35); border-radius: 5px; font-size: 12px; background: rgba(240,240,240,0.9); display: flex; align-items: center; gap: 8px; overflow-x: auto; scrollbar-width: none;'><span style='white-space: nowrap; color: #333;'>🔄 <b>CHANGE:</b></span> {badge_from} <span style='font-size: 10px; color: #666;'>➔</span> {badge_to}</div>"
                
                transfer_nodes.append({
                    "coord": coords[u], "from_line": from_name, "from_color": from_color, "from_logo": from_logo,
                    "to_line": to_name, "to_color": to_color, "to_logo": to_logo
                })
            
            line_name = LINE_NAMES.get(chosen_line, 'Interchange')
            line_color = LINE_COLORS.get(chosen_line, '#888888')
            line_logo = LINE_LOGOS.get(chosen_line, '')
            img_tag = f"<img src='/static/line_logo/{line_logo}' style='height: 14px; width: 14px; object-fit: contain; margin-right: 5px; vertical-align: middle;'>" if line_logo else ""
            badge = f"<span style='background-color: {line_color}; color: #fff; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; border: 1px solid rgba(0,0,0,0.2); text-shadow: 0 1px 1px rgba(0,0,0,0.3); display: inline-flex; align-items: center; white-space: nowrap;'>{img_tag}{line_name}</span>"
            
            itinerary_html += f"<div style='margin-bottom: 6px;'><b>TAKE:</b> {badge}</div>"
            current_line = chosen_line
            stops = 1
            partial_time = leg_time
        else:
            stops += 1
            partial_time += leg_time
            
    itinerary_html += f"&nbsp;&nbsp;↳ {stops} stops ({format_time(partial_time)}).<br><br><div style='margin-top: 12px;'>🏁 <b>ARRIVE AT:</b> {id_to_name[path_astar[-1]]}<br>⏱️ <b>ESTIMATED TOTAL TIME:</b> <span style='color:#1a73e8; font-weight:bold;'>{format_time(total_travel_time)}</span></div>"
    
    efficiency = round((1 - len(explored_astar)/len(explored_dijkstra))*100) if len(explored_dijkstra) > 0 else 0
    performance_stats = f"CPU TIME: {calc_time*1000:.2f} ms\nDIJKSTRA: {len(explored_dijkstra)} nodes\nA*: {len(explored_astar)} nodes\nEFFICIENCY: +{efficiency}%"

    return jsonify({
        'itinerary': itinerary_html, 'stats': performance_stats, 
        'dijkstra': [coords[n] for n in explored_dijkstra], 'astar': [coords[n] for n in explored_astar],
        'path': [coords[n] for n in path_astar], 'transfers': transfer_nodes, 
        'start_name': id_to_name[start_id], 'target_name': id_to_name[target_id]
    })

if __name__ == "__main__":
    print("INFO: Initializing Flask Application.")
    print("INFO: For Docker deployment: Container binds to 0.0.0.0:5000")
    #app.run(host='127.0.0.1', port=5000, debug=False) for local testing on VScode python src/main.py
    # 0.0.0.0 is required for Docker to expose the port to the host
    app.run(host='0.0.0.0', port=5000)
