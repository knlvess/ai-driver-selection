import osmnx as ox
import networkx as nx
import pandas as pd
import math
import time
import random

PENALTI_PER_NODE = 5

def _weight_fn(u, v, data):
    return min(e.get('waktu_tempuh_detik', float('inf')) for e in data.values()) + PENALTI_PER_NODE

def get_dijkstra_with_penalty(G, source_node, target_node):
    waktu_raw, jalur = nx.single_source_dijkstra(
        G, source=source_node, target=target_node, weight=_weight_fn
    )
    waktu_koreksi = waktu_raw - (2 * PENALTI_PER_NODE)
    
    waktu_dasar = sum(G[u][v][0].get('waktu_tempuh_detik', 0) for u, v in zip(jalur[:-1], jalur[1:]))
    waktu_final = max(waktu_dasar, waktu_koreksi)
    
    return waktu_final, jalur

def main():
    print("="*70)
    print(" MODUL 04: EVALUASI PERFORMA ")
    print("="*70)

    # ==============================================================================
    # STEP 1: PERSIAPAN DATA
    # ==============================================================================
    print("\n1. Memuat infrastruktur peta UNS...")
    try:
        G_proj = ox.load_graphml("uns_projected_graph.graphml")
        for u, v, k, data in G_proj.edges(data=True, keys=True):
            if 'waktu_tempuh_detik' in data:
                data['waktu_tempuh_detik'] = float(data['waktu_tempuh_detik'])
    except FileNotFoundError:
        print("\n[ERROR] File 'uns_projected_graph.graphml' tidak ditemukan!")
        return

    nodes_proj, _ = ox.graph_to_gdfs(G_proj)
    all_nodes = list(G_proj.nodes())
    tipe_node = type(all_nodes[0])

    print("\n2. Men-generate Beban Uji (1 User & 100 Driver secara acak)...")
    user_node = random.choice(all_nodes)
    user_x = nodes_proj.loc[user_node, 'x']
    user_y = nodes_proj.loc[user_node, 'y']
    
    JUMLAH_DRIVER = 100
    driver_nodes = random.sample([n for n in all_nodes if n != user_node], JUMLAH_DRIVER)

    hasil_waktu = {}
    pemenang = {}

    # ==============================================================================
    # SKENARIO 1: DIJKSTRA MURNI
    # ==============================================================================
    print(f"\n[SKENARIO 1] Dijkstra Murni ke {JUMLAH_DRIVER} Driver...")
    waktu_mulai = time.time()
    waktu_tercepat_1 = float('inf')
    for d_node in driver_nodes:
        try:
            waktu_total, _ = get_dijkstra_with_penalty(G_proj, tipe_node(d_node), tipe_node(user_node))
            if waktu_total < waktu_tercepat_1:
                waktu_tercepat_1, pemenang['Dijkstra'] = waktu_total, d_node
        except nx.NetworkXNoPath: continue
    hasil_waktu['Dijkstra'] = time.time() - waktu_mulai

    # ==============================================================================
    # SKENARIO 2: MODEL HYBRID (EUCLIDEAN + DIJKSTRA)
    # ==============================================================================
    print(f"[SKENARIO 2] Model Hybrid (Euclidean Radius < 1KM + Dijkstra)...")
    waktu_mulai_filter = time.time()
    
    # Fase Euclidean
    kandidat_lolos = [
        d for d in driver_nodes 
        if math.sqrt((nodes_proj.loc[d, 'x'] - user_x)**2 + (nodes_proj.loc[d, 'y'] - user_y)**2) < 1000
    ]
    waktu_filter = time.time() - waktu_mulai_filter
    print(f"   -> {len(kandidat_lolos)} driver lolos filter Geofencing.")

    # Fase Routing Dijkstra
    waktu_mulai_routing = time.time()
    waktu_tercepat_3 = float('inf')
    for d_node in kandidat_lolos:
        try:
            waktu_total, _ = get_dijkstra_with_penalty(G_proj, tipe_node(d_node), tipe_node(user_node))
            if waktu_total < waktu_tercepat_3:
                waktu_tercepat_3, pemenang['Hybrid'] = waktu_total, d_node
        except nx.NetworkXNoPath: continue
    waktu_routing = time.time() - waktu_mulai_routing
    hasil_waktu['Hybrid'] = waktu_filter + waktu_routing

    # ==============================================================================
    # KESIMPULAN & METRIK
    # ==============================================================================
    print("\n" + "="*70)
    print(" KESIMPULAN BENCHMARK 2 ALGORITMA ".center(70))
    print("="*70)
    
    semua_pemenang = list(pemenang.values())
    if len(set(semua_pemenang)) == 1:
        print(" ✅ AKURASI: 100% (Ketiga metode mengarah ke driver yang sama)")
    else:
        print(" ⚠️ PERHATIAN: Ditemukan pembedaan pemenang antar algoritma.")
        
    print("-" * 70)
    print(f" ⏳ Waktu Komputasi Skenario 1 (Dijkstra) : {hasil_waktu['Dijkstra']:.4f} detik")
    print(f" 🚀 Waktu Komputasi Skenario 2 (Hybrid)   : {hasil_waktu['Hybrid']:.4f} detik")
    
    print("-" * 70)
    baseline = hasil_waktu['Dijkstra']
    if baseline > 0:
        print(" TINGKAT EFISIENSI TERHADAP DIJKSTRA MURNI:")
        print(f"  - Hybrid     : {((baseline - hasil_waktu['Hybrid'])/baseline)*100:.2f}% lebih cepat")
    print("="*70)

if __name__ == "__main__":
    main()