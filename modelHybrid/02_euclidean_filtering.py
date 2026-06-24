import osmnx as ox
import pandas as pd
import random
import math

def main():
    print("="*60)
    print(" MODUL 02: EUCLIDEAN FILTERING (RADIUS < 1 KM) ")
    print("="*60)

    print("\n1. Membaca data graf dari file ('uns_projected_graph.graphml')...")
    try:
        G_proj = ox.load_graphml("uns_projected_graph.graphml")
    except FileNotFoundError:
        print("\n[ERROR] File graf tidak ditemukan!")
        print("Pastikan file 'uns_projected_graph.graphml' berada di folder yang sama.")
        return

    nodes_proj, _ = ox.graph_to_gdfs(G_proj)
    all_nodes = list(G_proj.nodes())

    # Random user and driver
    print("2. Menempatkan posisi User dan Driver...")
    user_node = random.choice(all_nodes)
    user_x = nodes_proj.loc[user_node, 'x']
    user_y = nodes_proj.loc[user_node, 'y']
    print(f"   -> [USER] Berada di Node ID: {user_node}")

    jumlah_driver = 20
    driver_nodes = random.sample([node for node in all_nodes if node != user_node], jumlah_driver)

    # Euclidean Calculation
    print(f"\n3. Menghitung jarak garis lurus untuk {jumlah_driver} driver...")
    daftar_driver = []
    for idx, d_node in enumerate(driver_nodes):
        driver_x = nodes_proj.loc[d_node, 'x']
        driver_y = nodes_proj.loc[d_node, 'y']
        
        jarak_euclidean = math.sqrt((driver_x - user_x)**2 + (driver_y - user_y)**2)
        
        daftar_driver.append({
            'Driver_ID': f'Driver_{idx+1}',
            'Node_ID': d_node,
            'Jarak_Euclidean_Meter': round(jarak_euclidean, 2)
        })

    df_euclidean = pd.DataFrame(daftar_driver)
    df_euclidean = df_euclidean.sort_values(by='Jarak_Euclidean_Meter').reset_index(drop=True)

    # Euclidean Filtering < 1 km
    radius_batas_meter = 1000
    print(f"\n4. Menyaring driver yang berada dalam radius < {radius_batas_meter/1000} KM...")
    kandidat_driver = df_euclidean[df_euclidean['Jarak_Euclidean_Meter'] < radius_batas_meter]

    if len(kandidat_driver) == 0:
        print("\n   -> [GAGAL] Tidak ada driver di dalam radius 1 KM.")
        return
    else:
        print(f"   -> [BERHASIL] Ditemukan {len(kandidat_driver)} driver potensial:")
        print(kandidat_driver.to_string(index=False))

    # Save Output
    print("\n5. Menyimpan data kandidat dan lokasi user...")
    df_euclidean.to_csv("daftar_driver.csv", index=False)
    kandidat_driver.to_csv("kandidat_driver.csv", index=False)
    
    df_user = pd.DataFrame([{'User_ID': 'User_1', 'Node_ID': user_node}])
    df_user.to_csv("lokasi_user.csv", index=False)

    print("   -> [BERHASIL] File 'daftar_driver.csv', 'kandidat_driver.csv' dan 'lokasi_user.csv' dibuat!")
    print("="*60)

if __name__ == "__main__":
    main()