from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import pandas as pd
import heapq
from pyproj import Transformer, CRS

app = Flask(__name__)
CORS(app)

print("="*60)
print("1. Memuat Infrastruktur Peta untuk Visualisasi...")
try:
    G_proj = ox.load_graphml("uns_projected_graph.graphml")
    print("   -> [SUKSES] Graf berhasil dimuat.")
except FileNotFoundError:
    print("   -> [ERROR] File 'uns_projected_graph.graphml' tidak ditemukan!")
    exit(1)

try:
    df_kandidat = pd.read_csv("kandidat_driver.csv")
    df_user = pd.read_csv("lokasi_user.csv")
    print("   -> [SUKSES] Data kandidat dan user dimuat.")
except FileNotFoundError:
    print("   -> [ERROR] File CSV kandidat/user tidak ditemukan. Jalankan 02_euclidean_filtering.py dulu.")
    exit(1)

# Ensure 'waktu_tempuh_detik' exists (we use a simple speed assumption if not present from module 1)
# But it should be present. Just in case, let's normalize it.
for u, v, k, data in G_proj.edges(data=True, keys=True):
    if 'waktu_tempuh_detik' in data:
        data['waktu_tempuh_detik'] = float(data['waktu_tempuh_detik'])
    else:
        # Fallback if somehow missing
        jarak = float(data.get('length', 100))
        V_NORMAL_MS = 40 * (1000 / 3600)
        data['waktu_tempuh_detik'] = jarak / V_NORMAL_MS

tipe_node = type(list(G_proj.nodes())[0])
user_node = tipe_node(df_user['Node_ID'].iloc[0])

# Alat penerjemah koordinat
crs_proj = CRS(G_proj.graph['crs'])
transformer_to_wgs = Transformer.from_crs(crs_proj, "EPSG:4326", always_xy=True)

def node_to_latlng(node_id):
    x_utm = G_proj.nodes[node_id]['x']
    y_utm = G_proj.nodes[node_id]['y']
    lng, lat = transformer_to_wgs.transform(x_utm, y_utm)
    return [lat, lng]

def dijkstra_visual(G, source, target):
    """
    Custom Dijkstra implementation that tracks visited nodes in order.
    """
    PENALTI_PER_NODE = 5
    
    dist = {source: 0}
    prev = {}
    visited = set()
    visited_order = []
    
    # Priority Queue: (cost, current_node, path_length_so_far)
    pq = [(0, source, 1)] 
    
    while pq:
        cost, u, path_len = heapq.heappop(pq)
        
        if u in visited:
            continue
            
        visited.add(u)
        
        # Record visit
        visited_order.append({
            "latlng": node_to_latlng(u),
            "cost": round(cost, 2),
            "step": len(visited_order) + 1
        })
        
        if u == target:
            break
            
        # Explore neighbors
        for v in G.neighbors(u):
            # Find the minimum weight among parallel edges
            waktu_edge = float('inf')
            for key in G[u][v]:
                waktu_edge = min(waktu_edge, G[u][v][key]['waktu_tempuh_detik'])
            
            edge_weight = waktu_edge + PENALTI_PER_NODE
            new_cost = cost + edge_weight
            
            if new_cost < dist.get(v, float('inf')):
                dist[v] = new_cost
                prev[v] = u
                heapq.heappush(pq, (new_cost, v, path_len + 1))
                
    # Reconstruct path
    path = []
    if target in prev or source == target:
        curr = target
        while curr in prev:
            path.append(node_to_latlng(curr))
            curr = prev[curr]
        path.append(node_to_latlng(source))
        path.reverse()
        
    # Subtract the 1 excess penalty from final cost (same mathematical logic as Modul 03)
    final_cost = dist.get(target, 0)
    if len(path) > 1:
        final_cost -= PENALTI_PER_NODE
        
    return visited_order, path, max(0, final_cost)

@app.route('/dijkstra-visual', methods=['POST'])
def run_dijkstra_visual():
    data = request.json
    driver_idx = data.get('driver_idx', 0)
    
    if driver_idx >= len(df_kandidat):
        return jsonify({"status": "gagal", "pesan": "Driver index out of range."})
        
    row = df_kandidat.iloc[driver_idx]
    driver_id = row['Driver_ID']
    driver_node = tipe_node(row['Node_ID'])
    
    visited_nodes, final_path, total_cost = dijkstra_visual(G_proj, driver_node, user_node)
    
    if not final_path:
        return jsonify({
            "status": "gagal", 
            "pesan": f"Tidak ada jalan dari {driver_id} ke User."
        })
        
    return jsonify({
        "status": "sukses",
        "driver_id": driver_id,
        "driver_latlng": node_to_latlng(driver_node),
        "user_latlng": node_to_latlng(user_node),
        "visited_nodes": visited_nodes,
        "final_path": final_path,
        "total_visited": len(visited_nodes),
        "total_cost": round(total_cost, 2)
    })

@app.route('/kandidat-list', methods=['GET'])
def get_kandidat():
    # Return list of drivers for the UI dropdown
    kandidat_list = []
    for idx, row in df_kandidat.iterrows():
        kandidat_list.append({
            "idx": idx,
            "driver_id": row['Driver_ID'],
            "jarak_euclidean": row['Jarak_Euclidean_Meter']
        })
    return jsonify({
        "status": "sukses",
        "kandidat": kandidat_list
    })

if __name__ == '__main__':
    print("\n[VISUAL SERVER READY] Buka file 'visual.html' di browser Anda!")
    print("API berjalan di http://localhost:5001")
    app.run(port=5001, debug=True)
