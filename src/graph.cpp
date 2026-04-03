/**
 * @file pathfinder_core.cpp
 * @brief Core C++ routing engine for the London Pathfinder application.
 * Utilizes Dijkstra and A* algorithms with line-transfer penalty handling.
 * Integrated with Python via Pybind11.
 */

#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <queue>
#include <limits>
#include <algorithm>
#include <utility>
#include <cmath>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// Custom hash function to use std::pair as keys in unordered_map
struct pair_hash {
    template <class T1, class T2>
    std::size_t operator () (const std::pair<T1, T2>& p) const {
        auto h1 = std::hash<T1>{}(p.first);
        auto h2 = std::hash<T2>{}(p.second);
        return h1 ^ (h2 << 1); 
    }
};

struct Edge {
    int target_node_id;
    double weight;
    int line_id;
};

struct Node {
    int id;
    std::string name;
    double lat;
    double lon;
    std::vector<Edge> neighbors;
};

// Advanced search state to track the current line and handle transfer penalties
struct SearchState {
    double f_score;
    double g_score;
    int node_id;
    int line_id;
    
    // Priority order for the Min-Heap
    bool operator>(const SearchState& other) const {
        return f_score > other.f_score;
    }
};

class PathFinder {
private:
    std::unordered_map<int, Node> graph;
    const double TRANSFER_PENALTY_MINUTES = 5.0;

public:
    void add_node(int id, const std::string& name, double lat, double lon) {
        graph[id] = {id, name, lat, lon, {}};
    }

    void add_edge(int source, int target, double weight, int line_id = -1) {
        graph[source].neighbors.push_back({target, weight, line_id});
        graph[target].neighbors.push_back({source, weight, line_id});
    }

    // Heuristic function for A* (Euclidean distance converted to estimated travel time)
    double heuristic(int current_id, int target_id) {
        double lat1 = graph[current_id].lat;
        double lon1 = graph[current_id].lon;
        double lat2 = graph[target_id].lat;
        double lon2 = graph[target_id].lon;
        
        // Approximate flat-earth distance calculation for speed
        double dx = (lon1 - lon2) * 71.5;
        double dy = (lat1 - lat2) * 111.3;
        double dist_km = std::sqrt(dx*dx + dy*dy);
        
        // Assume optimistic straight-line speed of 36km/h (0.6 km/min)
        return dist_km / 0.6; 
    }

    // --- DIJKSTRA ALGORITHM ---
    std::pair<std::vector<int>, std::vector<int>> run_dijkstra(int start_id, int target_id) {
        // Keys: pair<node_id, line_id> to allow visiting a node multiple times if on different lines
        std::unordered_map<std::pair<int, int>, double, pair_hash> g_score;
        std::unordered_map<std::pair<int, int>, std::pair<int, int>, pair_hash> previous;
        std::vector<int> explored_order; 
        
        std::priority_queue<SearchState, std::vector<SearchState>, std::greater<SearchState>> pq;

        g_score[{start_id, -1}] = 0.0;
        pq.push({0.0, 0.0, start_id, -1});

        std::pair<int, int> best_target_state = {-1, -1};
        double min_target_cost = std::numeric_limits<double>::infinity();

        while (!pq.empty()) {
            SearchState current = pq.top();
            pq.pop();

            if (explored_order.empty() || explored_order.back() != current.node_id) {
                explored_order.push_back(current.node_id); 
            }

            if (current.node_id == target_id) {
                if (current.g_score < min_target_cost) {
                    min_target_cost = current.g_score;
                    best_target_state = {current.node_id, current.line_id};
                }
                continue; // Do not break immediately; ensure optimal path is found
            }
            
            if (current.g_score > g_score[{current.node_id, current.line_id}]) continue;

            for (const auto& edge : graph[current.node_id].neighbors) {
                double transfer_penalty = 0.0;
                if (current.line_id != -1 && current.line_id != edge.line_id) {
                    transfer_penalty = TRANSFER_PENALTY_MINUTES; 
                }

                double tentative_g = current.g_score + edge.weight + transfer_penalty;
                std::pair<int, int> next_state = {edge.target_node_id, edge.line_id};
                
                if (g_score.find(next_state) == g_score.end() || tentative_g < g_score[next_state]) {
                    previous[next_state] = {current.node_id, current.line_id};
                    g_score[next_state] = tentative_g;
                    pq.push({tentative_g, tentative_g, edge.target_node_id, edge.line_id});
                }
            }
        }

        std::vector<int> path;
        if (best_target_state.first != -1) {
            std::pair<int, int> curr = best_target_state;
            while (curr.first != start_id) {
                path.push_back(curr.first);
                curr = previous[curr];
            }
            path.push_back(start_id);
            std::reverse(path.begin(), path.end());
            path.erase(std::unique(path.begin(), path.end()), path.end()); // Clean transfer duplicates
        }
        
        return {path, explored_order};
    }

    // --- A* ALGORITHM ---
    std::pair<std::vector<int>, std::vector<int>> run_astar(int start_id, int target_id) {
        std::unordered_map<std::pair<int, int>, double, pair_hash> g_score;
        std::unordered_map<std::pair<int, int>, double, pair_hash> f_score;
        std::unordered_map<std::pair<int, int>, std::pair<int, int>, pair_hash> previous;
        std::vector<int> explored_order; 
        
        std::priority_queue<SearchState, std::vector<SearchState>, std::greater<SearchState>> pq;

        g_score[{start_id, -1}] = 0.0;
        f_score[{start_id, -1}] = heuristic(start_id, target_id);
        pq.push({f_score[{start_id, -1}], 0.0, start_id, -1});

        std::pair<int, int> best_target_state = {-1, -1};
        double min_target_cost = std::numeric_limits<double>::infinity();

        while (!pq.empty()) {
            SearchState current = pq.top();
            pq.pop();

            if (explored_order.empty() || explored_order.back() != current.node_id) {
                explored_order.push_back(current.node_id); 
            }

            if (current.node_id == target_id) {
                if (current.g_score < min_target_cost) {
                    min_target_cost = current.g_score;
                    best_target_state = {current.node_id, current.line_id};
                }
                continue;
            }
            
            if (current.g_score > g_score[{current.node_id, current.line_id}]) continue;

            for (const auto& edge : graph[current.node_id].neighbors) {
                double transfer_penalty = 0.0;
                if (current.line_id != -1 && current.line_id != edge.line_id) {
                    transfer_penalty = TRANSFER_PENALTY_MINUTES; 
                }

                double tentative_g = current.g_score + edge.weight + transfer_penalty;
                std::pair<int, int> next_state = {edge.target_node_id, edge.line_id};
                
                if (g_score.find(next_state) == g_score.end() || tentative_g < g_score[next_state]) {
                    previous[next_state] = {current.node_id, current.line_id};
                    g_score[next_state] = tentative_g;
                    double next_f = tentative_g + heuristic(edge.target_node_id, target_id);
                    
                    f_score[next_state] = next_f;
                    pq.push({next_f, tentative_g, edge.target_node_id, edge.line_id});
                }
            }
        }

        std::vector<int> path;
        if (best_target_state.first != -1) {
            std::pair<int, int> curr = best_target_state;
            while (curr.first != start_id) {
                path.push_back(curr.first);
                curr = previous[curr];
            }
            path.push_back(start_id);
            std::reverse(path.begin(), path.end());
            path.erase(std::unique(path.begin(), path.end()), path.end());
        }
        
        return {path, explored_order};
    }
};

// PYBIND11 MODULE DEFINITION
PYBIND11_MODULE(pathfinder_core, m) {
    m.doc() = "C++ Routing Engine for London Tube Pathfinding";
    
    py::class_<PathFinder>(m, "PathFinder")
        .def(py::init<>())
        .def("add_node", &PathFinder::add_node, "Add a station to the graph")
        .def("add_edge", &PathFinder::add_edge, py::arg("source"), py::arg("target"), py::arg("weight"), py::arg("line_id") = -1, "Add a connection between stations")
        .def("run_dijkstra", &PathFinder::run_dijkstra, "Execute Dijkstra's algorithm returning path and exploration order")
        .def("run_astar", &PathFinder::run_astar, "Execute A* algorithm with geographic heuristic returning path and exploration order");
}