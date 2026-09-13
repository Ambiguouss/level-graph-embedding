#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "GraphCore.h"
 
namespace py = pybind11;
 
PYBIND11_MODULE(graphcore, m) {
    m.doc() = "Level-planarity core: SAT-style feasibility check, tightening, and planar layout.";
    m.def(
        "planarize",
        [](int num_nodes,
           const std::vector<std::vector<int>>& levels,
           const std::vector<std::pair<int,int>>& edges) -> py::object {
        int num_levles = levels.size();
        vector<Node>nodes;
        for(int i=0;i<num_nodes;i++){
            nodes.push_back(Node(i,-1));
        }
        vector<vector<int>> new_levels(num_levles);
        for(int i=0;i<num_levles;i++){
            int nodes_in_level = levels[i].size();
            for(int j=0;j<nodes_in_level;j++){
                int x = levels[i][j];
                nodes[x].level=i;
                new_levels[i].push_back(x);
            }
        }
        vector<std::vector<int>>adj(num_nodes);
        for(auto [x,y]:edges){
            adj[x].push_back(y);
            adj[y].push_back(x);
        }
        LevelGraph graph(nodes, adj, new_levels);
        auto [ok, result_levels] = planarize_pipeline(graph);
        if(!ok){
            return py::none();
        }
        return py::cast(result_levels);
        },
        py::arg("num_nodes"),
        py::arg("levels"),
        py::arg("edges"),
        R"doc(
        Attempt to compute a level-planar layout.
 
        Parameters
        ----------
        num_nodes : int
            Total number of nodes, ids assumed to be 0..num_nodes-1.
        levels : list[list[int]]
            Node ids grouped by level, top to bottom.
        edges : list[tuple[int, int]]
            Undirected edges as (node_id, node_id) pairs, each connecting
            adjacent levels.
 
        Returns
        -------
        list[list[int]] or None
            Node ids grouped by level in left-to-right planar order, or
            None if the graph is not level planar.
        )doc"
    );
}
