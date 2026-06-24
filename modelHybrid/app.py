from flask import Flask, request, jsonify
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import random
import math
from pyproj import Transformer, CRS

app = Flask(__name__)
CORS(app)

print("="*60)
print("1. Memuat Infrastruktur Peta (Mohon tunggu beberapa detik)...")
try:
    G_proj = ox.load_graphml("uns_projected_graph.graphml")
    print("   -> [SUKSES] Graf berhasil dimuat.")
except FileNotFoundError:
    print("   -> [ERROR] File 'uns_projected_graph.graphml' tidak ditemukan!")
    exit(1)

# Persiapan Data (Seperti Modul 01)
V_NORMAL_MS = 40 * (1000 / 3600)  # 11.11 m/s (40km/jam)
V_MACET_MS = 20 * (1000 / 3600)   # 5.55 m/s (20km/jam)

print("2. Menghitung waktu tempuh dan status jalan...")
for u, v, k, data in G_proj.edges(data=True, keys=True):
    # Bersihkan length
    jarak = float(data.get('length', 100))
    data['length'] = jarak
    
    # Assign status jalan acak
    status = random.choices(['Normal', 'Macet'], weights=[0.7, 0.3], k=1)[0]
    data['status_lalu_lintas'] = status
    
    # Hitung waktu tempuh
    waktu = jarak / V_NORMAL_MS if status == 'Normal' else jarak / V_MACET_MS
    data['waktu_tempuh_detik'] = waktu
    
print("   -> [SUKSES] Data jalan siap.")

# Alat penerjemah koordinat
crs_proj = CRS(G_proj.graph['crs'])
transformer_to_utm = Transformer.from_crs("EPSG:4326", crs_proj, always_xy=True)
transformer_to_wgs = Transformer.from_crs(crs_proj, "EPSG:4326", always_xy=True)

all_nodes = list(G_proj.nodes())

def get_dijkstra_with_penalty(G, source_node, target_node):
    waktu_dasar, jalur = nx.single_source_dijkstra(
        G, source=source_node, target=target_node, weight='waktu_tempuh_detik'
    )
    jumlah_simpang = max(0, len(jalur) - 2)
    penalti = jumlah_simpang * 5
    waktu_total = waktu_dasar + penalti
    
    jarak_aktual = 0
    for i in range(len(jalur) - 1):
        u = jalur[i]
        v = jalur[i + 1]
        jarak_aktual += G[u][v][0]['length']
        
    return waktu_total, jarak_aktual, jumlah_simpang, jalur

def convert_nodes_to_latlng(rute_nodes):
    koordinat_leaflet = []
    for node in rute_nodes:
        x_utm = G_proj.nodes[node]['x']
        y_utm = G_proj.nodes[node]['y']
        lng, lat = transformer_to_wgs.transform(x_utm, y_utm)
        koordinat_leaflet.append([lat, lng])
    return koordinat_leaflet

@app.route('/find-driver', methods=['POST'])
def find_driver():
    data = request.json
    user_lat, user_lng = data['lat'], data['lng']

    # 1. Convert User WGS84 -> UTM
    user_x_utm, user_y_utm = transformer_to_utm.transform(user_lng, user_lat)
    user_node = ox.distance.nearest_nodes(G_proj, X=user_x_utm, Y=user_y_utm)
    user_x_actual = G_proj.nodes[user_node]['x']
    user_y_actual = G_proj.nodes[user_node]['y']
    user_lng_act, user_lat_act = transformer_to_wgs.transform(user_x_actual, user_y_actual)

    # 2. Modul 02: Generate 20 Driver & Hitung Euclidean
    jumlah_driver = 20
    driver_nodes = random.sample([n for n in all_nodes if n != user_node], jumlah_driver)
    
    daftar_driver = []
    for idx, d_node in enumerate(driver_nodes):
        driver_x = G_proj.nodes[d_node]['x']
        driver_y = G_proj.nodes[d_node]['y']
        jarak_euclidean = math.sqrt((driver_x - user_x_utm)**2 + (driver_y - user_y_utm)**2)
        
        d_lng, d_lat = transformer_to_wgs.transform(driver_x, driver_y)
        
        daftar_driver.append({
            'driver_id': f'Driver_{idx+1}',
            'node_id': d_node,
            'jarak_euclidean_m': round(jarak_euclidean, 2),
            'latlng': [d_lat, d_lng]
        })
        
    daftar_driver.sort(key=lambda x: x['jarak_euclidean_m'])
    
    # 3. Modul 02: Euclidean Filtering < 1 KM
    radius_batas_meter = 1000
    kandidat_driver_raw = [d for d in daftar_driver if d['jarak_euclidean_m'] < radius_batas_meter]
    
    if not kandidat_driver_raw:
        return jsonify({
            "status": "gagal", 
            "pesan": "Tidak ada driver dalam radius 1 KM!",
            "user_latlng": [user_lat_act, user_lng_act],
            "daftar_driver": daftar_driver
        })

    # 4. Modul 03: Dijkstra + Penalti
    kandidat_driver = []
    for driver in kandidat_driver_raw:
        d_node = driver['node_id']
        try:
            waktu_total, jarak_aktual, jumlah_simpang, rute_jalur = get_dijkstra_with_penalty(
                G_proj, d_node, user_node
            )
            
            menit = int(waktu_total // 60)
            detik = int(waktu_total % 60)
            eta_teks = f"{menit} Menit {detik} Detik" if menit > 0 else f"{detik} Detik"
            
            rute_koordinat = convert_nodes_to_latlng(rute_jalur)
            
            driver_copy = driver.copy()
            driver_copy.update({
                'jarak_rute_m': round(jarak_aktual, 2),
                'eta_detik': round(waktu_total, 2),
                'eta_teks': eta_teks,
                'jumlah_simpang': jumlah_simpang,
                'rute_koordinat': rute_koordinat
            })
            kandidat_driver.append(driver_copy)
            
        except nx.NetworkXNoPath:
            continue

    if not kandidat_driver:
         return jsonify({
            "status": "gagal", 
            "pesan": "Semua kandidat driver tidak memiliki rute ke lokasi Anda (jalan buntu).",
            "user_latlng": [user_lat_act, user_lng_act],
            "daftar_driver": daftar_driver
        })

    # 5. Tentukan Pemenang (Waktu Tercepat)
    kandidat_driver.sort(key=lambda x: x['eta_detik'])
    driver_terpilih = kandidat_driver[0]

    return jsonify({
        "status": "sukses",
        "user_node": user_node,
        "user_latlng": [user_lat_act, user_lng_act],
        "daftar_driver": daftar_driver,
        "kandidat_driver": kandidat_driver,
        "driver_terpilih": driver_terpilih
    })

if __name__ == '__main__':
    print("\n[SERVER READY] Buka file 'index.html' di browser Anda!")
    app.run(port=5000, debug=True)