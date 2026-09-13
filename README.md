# level-graph-embedding
This repo consists of a implementation and a demo of embedding proper level planar graphs done in $O(n^4)$ time.
# Level graph
Level graph is a graph $G = (V,E)$ and a additional level assignment $V(G) \to \mathbb{N}$. For a proper level graph, the edges can only connect vertices on adjacent levels. 
# The planarity problem
Given a proper level graph, draw it so that for each vertex its level matches the level assignment, all edges are $y$-monotone and no edges cross.
# It's not that easy
Some easy (and fast) algorithms were proposed, but [recent work by Fink et. al.](https://arxiv.org/pdf/2409.01727) showed that these algorithm were not correct. 
# The outline of the algorithm
Solution implemented here is quite simple (unfortunately not that fast). Checking whether a graph is level planar can be done in $O(n^2)$ time by 2-SAT formulation proposed by Randerath et al.(2001), and proofed by Brückner et al.(2022). First step to the embedding is using that algorithm to check the planarity of a given graph. Next, we can try adding some new edges and see whether the graph is still planar. If so, we add the edge to the graph. At the end, we will have a maximal (on the set of edges) level planar graph, which is a lot easier to embed.
# Setup 
```
python3 -m venv venv
source venv/bin/activate
pip install .
python gui.py
```
<img width="2192" height="962" alt="image" src="https://github.com/user-attachments/assets/ded87f49-198c-4efd-9021-92e384a121d5" />
