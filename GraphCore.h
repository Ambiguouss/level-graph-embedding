#include <bits/stdc++.h>
using namespace std;
struct Node {
    int id;
    int level;
    Node(int _id,int _level): id(_id),level(_level){}
};

class LevelGraph {
    public:
    std::vector<Node> nodes;
    std::vector<std::vector<int>> adjacency;
    std::vector<std::vector<int>> levels;
    LevelGraph(vector<Node> _nodes,vector<vector<int>> _adj,vector<vector<int>> _levels) : 
        nodes(_nodes),adjacency(_adj),levels(_levels){}
};

class GraphTransformer{
    public:
    LevelGraph transform(const LevelGraph& graph){
        int n=graph.nodes.size();
        int number_of_levels = graph.levels.size();
        vector<Node> nodes;
        vector<vector<int>> adjacency(2*n);
        vector<vector<int>> levels(2*number_of_levels);

        for(int i=0;i<2*n;i++){
            nodes.push_back(Node(i,0));
        }
        for(int i=0;i<n;i++){
            adjacency[i].push_back(i+n);
            adjacency[i+n].push_back(i);
        }
        
        for(int i=0;i<number_of_levels;i++){
            for(auto x:graph.levels[i]){
                levels[2*i].push_back(x);
                levels[2*i+1].push_back(x+n);
                nodes[x].level=2*i;
                nodes[x+n].level=2*i+1;
            }
        }
        for(auto& l : graph.levels){
            for(auto x : l){
                for(auto y:graph.adjacency[x]){
                    if(nodes[x].level<nodes[y].level){
                        adjacency[n+x].push_back(y);
                        adjacency[y].push_back(n+x);
                    }
                }
            }
        }
        return LevelGraph(nodes,adjacency,levels);
    }
};

class SatGraph{
    public:
    int n;
    vector<vector<int>> edges;
    vector<int> antinode;

    SatGraph(int _n,vector<vector<int>>_e,vector<int> _ant):
        n(_n),edges(_e),antinode(_ant){}

    bool feasible(){
        vector<int> visited(n,0);

        auto bfs = [&](int x,int e_class){
            queue<int> q;
            visited[x]=e_class;
            q.push(x);
            while(!q.empty()){
                int v=q.front();
                q.pop();
                for(auto y:edges[v]){
                    if(!visited[y]){
                        visited[y]=e_class;
                        q.push(y);
                    }
                }
                
            }
        };

        int equi_class=1;
        for(int i=0;i<n;i++){
            if(!visited[i]){
                bfs(i,equi_class);
                equi_class++;
            }
        }

        for(int i=0;i<n;i++){
            if(visited[i]==visited[antinode[i]])return false;
        }
        return true;
    }
};

class SatCreater{
    public:
    SatGraph create(const LevelGraph& graph){
        int n=0;
        vector<int> antinode;
        vector<vector<int>>pairs_to_nodes(graph.nodes.size(),vector<int>(graph.nodes.size()));
        for(int l_ind=0;l_ind<graph.levels.size();l_ind++){
            auto l=graph.levels[l_ind];
            for(int i=0;i<l.size();i++){
                for(int j=i+1;j<l.size();j++){
                    int x =l[i];
                    int y = l[j];
                    pairs_to_nodes[x][y]=n;
                    pairs_to_nodes[y][x]=n+1;
                    antinode.push_back(n+1);
                    antinode.push_back(n);
                    n+=2;
                }
            }
        }
        vector<vector<int>> edges(n);
        for(int l_ind=0;l_ind<graph.levels.size()-1;l_ind++){
            auto l=graph.levels[l_ind];
            for(int i=0;i<l.size();i++){
                for(int j=i+1;j<l.size();j++){
                    int x=l[i];
                    int y=l[j];
                    for(auto a:graph.adjacency[x]){
                        for(auto b:graph.adjacency[y]){
                            if(a!=b){
                                edges[pairs_to_nodes[x][y]].push_back(pairs_to_nodes[a][b]);
                                edges[pairs_to_nodes[y][x]].push_back(pairs_to_nodes[b][a]);
                            }
                        }
                    }
                }
            }
        }
        return SatGraph(n,edges,antinode);
    }
};

class GraphTightener{
    public:
    //assume graph is level planar, also already split
    LevelGraph tighten(const LevelGraph& graph,SatCreater creater){
        LevelGraph result = graph;
        int l=graph.levels.size();
        for(int i=0;i<l;i+=2){
            for(int x=0;x<graph.levels[i].size();x++){
                for(int y=x+1;y<graph.levels[i+1].size();y++){
                    result.adjacency[graph.levels[i][x]].push_back(graph.levels[i+1][y]);
                    result.adjacency[graph.levels[i+1][y]].push_back(graph.levels[i][x]);
                    SatGraph sat = creater.create(result);
                    if(!sat.feasible()){
                        result.adjacency[graph.levels[i][x]].pop_back();
                        result.adjacency[graph.levels[i+1][y]].pop_back();
                    }
                }
            }
        }
        return result;
    }
};

class GraphPlanarer{
    public:
    LevelGraph planar(const LevelGraph& graph, const LevelGraph& tight){
        int n=graph.nodes.size();
        int l=graph.levels.size();
        vector<vector<int>> planar_levels;
        vector<Node> planar_nodes = graph.nodes;
        vector<vector<int>> adjacency = graph.adjacency;
        int first_with_down_n = -1;
        int down_n=0;
        for(int i=0;i<l;i++){
            vector<int> planar_level;
            int current;
            int previous=-1;
            for(int j=0;j<tight.levels[2*i].size();j++){
                int deg=0;
                int v = tight.levels[2*i][j];
                for(auto x:tight.adjacency[v]){
                    if(tight.nodes[x].level>2*i && x!=v + n)deg++;
                }
                for(auto x:tight.adjacency[v+n]){
                    if(tight.nodes[x].level<2*i+1 && x!=v)deg++;
                }
                if(deg<=1){
                    planar_level.push_back(v);
                    current=v;
                    break;
                }
            }
            while(planar_level.size()!=graph.levels[i].size()){
                for(auto x:tight.adjacency[current]){
                    if(tight.nodes[x].level>2*i && x-n!=current && x-n!=previous){
                        previous=current;
                        current=x-n;
                        planar_level.push_back(current);
                        break;
                    }
                }
                for(auto x:tight.adjacency[current+n]){
                    if(tight.nodes[x].level<2*i+1 && x!=current && x!=previous){
                        previous=current;
                        current=x;
                        planar_level.push_back(current);
                        break;
                    }
                }
            }
            if(first_with_down_n!=-1){
                bool present=false;
                bool swap=true;
                int up_adj=0;
                for(auto x:planar_level){
                    for(auto y:graph.adjacency[x]){
                        if(y==first_with_down_n){
                            swap=false;
                            //break;
                        }
                        if(graph.nodes[y].level<i){
                            up_adj++;
                            present=true;
                        }
                    }
                    if(swap==false && (up_adj==1 || down_n==1))break;
                    if(present==true){
                        reverse(planar_level.begin(),planar_level.end());
                        break;
                    }
                }
            }
            first_with_down_n=-1;
            down_n=0;
            for(auto x:planar_level){
                for(auto y:graph.adjacency[x]){
                    if(graph.nodes[y].level>i){
                        first_with_down_n=x;
                        down_n++;
                    }
                }
                if(first_with_down_n==x)break;
            }
            planar_levels.push_back(planar_level);
        }
        return LevelGraph(planar_nodes,adjacency,planar_levels);
    }
};

inline std::pair<bool, std::vector<std::vector<int>>> planarize_pipeline(const LevelGraph& graph){
    GraphTransformer transformer;
    GraphTightener tightener;
    SatCreater creater;
    GraphPlanarer planarer;
    
    LevelGraph transformed = transformer.transform(graph);
    SatGraph sat = creater.create(transformed);

    if(!sat.feasible()){
        return {false, {}};
    }

    LevelGraph tight = tightener.tighten(transformed,creater);
    LevelGraph planar = planarer.planar(graph,tight);
    return {true, planar.levels};

}
