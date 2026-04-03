
# London Pathfinder | <img src="static/line_logo/general.png" alt="London Underground" height="45" align="center"> <img src="https://img.icons8.com/?size=100&id=Wg6OhE8Wt7eI&format=png&color=000000" height="40" align="center">

![C++](https://img.shields.io/badge/C++-17-00599C.svg?style=flat&logo=c%2B%2B&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10-3776AB.svg?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.3-000000.svg?style=flat&logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker&logoColor=white)

> A high-performance pathfinding engine for the London Underground. 
  Calculates optimal travel routes by evaluating real-world geographic distances,
  switching-line penalties, and algorithmic telemetry.

<p align="center">
  <img src="assets/Map.svg" width="550" alt="System Map Visualization">
</p>

<p align="center">
  <img src="static/line_logo/Bakerloo_line_roundel.png" height="30" alt="Bakerloo">
  <img src="static/line_logo/Central_line_roundel.png" height="30" alt="Central">
  <img src="static/line_logo/Circle_line_roundel.png" height="30" alt="Circle">
  <img src="static/line_logo/District_line_roundel.png" height="30" alt="District">
  <img src="static/line_logo/H&c_line_roundel.png" height="30" alt="H&C">
  <img src="static/line_logo/Jubilee_line_roundel.png" height="30" alt="Jubilee">
  <img src="static/line_logo/Metropolitan_line_roundel.png" height="30" alt="Metropolitan">
  <img src="static/line_logo/Northern_line_roundel.png" height="30" alt="Northern">
  <img src="static/line_logo/Piccadilly_line_roundel.png" height="30" alt="Piccadilly">
  <img src="static/line_logo/Victoria_line_roundel.png" height="30" alt="Victoria">
  <img src="static/line_logo/W&c_line_roundel.png" height="30" alt="Waterloo & City">
  <img src="static/line_logo/DLR_roundel.png" height="30" alt="DLR">
  <img src="static/line_logo/Elizabeth_line_roundel.png" height="30" alt="Elizabeth">
</p>

## Live Demo & Visual Analysis

The interface is designed as a **Tactical Radar Dashboard**, providing real-time feedback on algorithmic exploration and path efficiency.

https://github.com/user-attachments/assets/a8cb9a0c-e846-45c5-a63d-dffc42af6558


### Features:
* **Real-Time Path Tracing:** Watch the engine plot the optimal route node-by-node with dynamic line-color coding.
* **Algorithmic Comparison:** Visual toggle between **Dijkstra** (exhaustive search) and **A*** (heuristic-optimized search).
* **Transfer Intelligence:** Automatic detection of line changes with dedicated "Change" badges and transit time penalties.
* **Dynamic Tooltips:** Hover over any station to see its geographical coordinates and serviced lines.



## System Architecture

London Pathfinder was built with a strict separation of concerns, isolating heavy computational loads from the transport layer:

* **Core(C++17):** Implements custom Graph data structures and graph traversal algorithms. 
C++ guarantees the memory efficiency and raw speed required to process complex network queries in milliseconds.

* **Middleware (Pybind11):** Seamlessly bridges the compiled *C++ core* to the Python runtime, entirely bypassing Python's Global Interpreter Lock (GIL) limitations during algorithmic execution.

* **Transport Layer (Flask):** A lightweight *REST API* acting solely as a router between the C++ brain and the frontend.

* **Client Interface (Vanilla JS & Leaflet):** A dynamic, glass-morphism UI that renders geographic vectors and stations directly on the browser map without reloading the page.



## Technologies

| **Core Stack** | **Implementation Details** |
| :--- | :--- |
| <img src="https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white" /> | Core routing engine (C++17), Custom Graph data structures, Pybind11 bindings |
| <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" /> | Flask REST API layer, ETL data pipeline, spherical geometry math (Haversine) |
| <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" /> | Containerized production environment, abstracting C++ compilation via Linux base image |
| <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" /> | Vanilla ES6+ async fetch handling, Leaflet.js vector mapping, DOM manipulation |
<br>


## Algorithmic Core & Telemetry

The routing engine simultaneously runs and compares two distinct algorithms to evaluate performance:

1.  **Dijkstra's Algorithm:** Computes the absolute shortest path by exhaustively evaluating edge weights (travel times + transfer penalties). Serves as the baseline for accuracy.

2.  **A* (A-Star) Search:** An optimized approach using the **Haversine formula** as its heuristic. By estimating the geographic straight-line distance to the target, A* aggressively prunes the search space.

**Real-World Constraints:**
The engine doesn't just count stops. It applies a mathematical penalty (`TRANSFER_PENALTY_MINUTES`) whenever the path requires hopping from one tube line to another, mimicking real human commuting logic.

| Metric | Dijkstra (Baseline) | A* (Optimized) |
| :--- | :--- | :--- |
| **Search Logic** | Uniform Cost Search | Geographic Heuristic (Haversine) |
| **Nodes Explored** | High (Full expansion) | Low (Target-oriented) |
| **Execution Time** | < 5ms (Native C++) | < 2ms (Native C++) |
| **Efficiency Gain** | 0% | **+60% to +85%** |



## Data Analysis (ETL)

The network is not hardcoded. The `build_dataset.py` pipeline (ETL) extracts live topographical data from open-source CSV repositories:
* Parses hundreds of coordinates (Latitude/Longitude).
* Dynamically calculates edge weights (estimated tunnel travel times) based on spherical geometry.
* Compiles a structured `london_tube.json` graph database used to initialize the C++ engine.

## API Contract
The Flask backend exposes a unified endpoint for algorithmic queries:

<p align="center">
  <img src="assets/code.png" width="550" alt="API Contract">
</p>

    

## Quick Start <img src="https://img.icons8.com/?size=100&id=GZxgGaKN8jxz&format=png&color=000000" width="30" valign="middle"> 
The application is fully containerized. No C++ toolchains, MSVC setups, or Python virtual environments are required on your host machine.

1.  **Clone the infrastructure:**

    ```bash
    git clone https://github.com/Vor7reX/London-Pathfinder.git

    cd LondonPathfinder
    ```

2.  **Forge the Engine (Build):**

    ```bash
    docker build -t metro-pathfinder .
    ```

3.  **Deploy the Server:**

    ```bash
    docker run -p 5000:5000 metro-pathfinder
    ```

    Access the interface at: `http://localhost:5000`

## VS Code Local Compilation (Bare-Metal Development) <img src="https://img.icons8.com/?size=100&id=v05jsvW3RprR&format=png&color=000000" width="30" valign="middle">

For developers aiming to tweak the C++ source code locally (requires `g++` or MSVC): 

<img src="https://img.icons8.com/?size=100&id=s0oMA2u8paUt&format=png&color=000000" width="25" valign="middle">

```bash

# 1. Setup Python Virtual Environment
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Compile the C++ extension via Pybind11 (flags: -O3 / /O2)
pip install .

# 4. Launch the API
python src/main.py
```


## Repository Structure <img src="https://img.icons8.com/?size=100&id=DNacFPxLaFAT&format=png&color=000000" width="30" valign="middle">
```text
LondonPathfinder/
├── src/
│   ├── graph.cpp            # Core C++ Graph & Routing implementation
│   └── main.py              # Flask Web Server & REST API Gateway
├── static/
│   ├── css/
│   │   └── main.css         # Tactical UI Styling (Glassmorphism)
│   ├── js/
│   │   └── app.js           # Leaflet.js mapping & AJAX logic
│   └── line_logo/           # Official TfL Underground visual assets
├── templates/
│   └── index.html           # Main application interface
├── data/
│   └── london_tube.json     # Compiled topological network graph
├── assets/
│   ├── Map.svg              # System architecture visualization
│   └── code.png             # API Contract documentation
├── build_dataset.py         # ETL Pipeline (Real-world data fetching)
├── Dockerfile               # Production container specifications
├── setup.py                 # Pybind11 C++ compilation directives
├── pyproject.toml           # Build-system requirements
├── requirements.txt         # Python dependency manifest
└── LICENSE                  # MIT License terms
```

## Roadmap & Current Limitations

* **Multi-threading**: Transitioning the C++ engine to execute Dijkstra and A* simultaneously on separate threads rather than sequentially.

* **Live TfL Data Integration**: Upgrading the ETL pipeline to ingest real-time Transport for London (TfL) delays and dynamically adjust edge weights on the fly.

* **Memory Profiling**: Implement strict memory limits and cache clearing mechanisms for prolonged server uptime.



## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/Vor7reX/London-Pathfinder/blob/main/LICENSE.md) file for details.

---

<div align="left">
  <p valign="middle">
    Created by <b>Vor7reX</b>
    <img src="https://archives.bulbagarden.net/media/upload/2/22/Spr_B2W2_Roxie.png" height="70" valign="middle" alt="Roxie">
  </p>
</div>
