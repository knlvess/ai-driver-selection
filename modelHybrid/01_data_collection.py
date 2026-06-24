import osmnx as ox
import pandas as pd
import random
import matplotlib.pyplot as plt

# North = -7.55000; South = -7.57000
# East  = 110.86800; West = 110.84500

def main():
    print("="*60)
    print(" MODUL 01: DATA COLLECTION ")
    print("="*60)

    print("\n1. Membaca data peta jalan dari file lokal 'map.osm'...")
    try:
        G = ox.graph_from_xml("modelHybrid/map.osm")
    except FileNotFoundError:
        print("\n[ERROR] File 'map.osm' tidak ditemukan!")
        return

    print("2. Memproyeksikan graf peta ke satuan meter (UTM)...")
    G_proj = ox.project_graph(G)
    nodes_proj, edges_proj = ox.graph_to_gdfs(G_proj)


    print("3. Menghitung waktu tempuh berdasarkan status jalan (Normal/Macet)...")
    
    V_NORMAL_MS = 40 * (1000 / 3600)  # 11.11 m/s (40km/jam)
    V_MACET_MS = 20 * (1000 / 3600)   # 5.55 m/s (20km/jam)

    status_jalan_list = random.choices(['Normal', 'Macet'], weights=[0.7, 0.3], k=len(edges_proj))
    edges_proj['status_lalu_lintas'] = status_jalan_list

    waktu_tempuh_list = []
    for idx, row in edges_proj.iterrows():
        jarak = row['length']
        if row['status_lalu_lintas'] == 'Normal':
            waktu = jarak / V_NORMAL_MS
        else:
            waktu = jarak / V_MACET_MS
        waktu_tempuh_list.append(round(waktu, 2))   

    edges_proj['waktu_tempuh_detik'] = waktu_tempuh_list

    for u, v, k, data in G_proj.edges(data=True, keys=True):
        try:
            waktu_value = edges_proj.loc[(u, v, k), 'waktu_tempuh_detik']
            status_value = edges_proj.loc[(u, v, k), 'status_lalu_lintas']
            
            if isinstance(waktu_value, pd.Series):
                waktu_value = waktu_value.iloc[0]
                status_value = status_value.iloc[0]
                
            data['waktu_tempuh_detik'] = waktu_value
            data['status_lalu_lintas'] = status_value
        except KeyError:
            data['waktu_tempuh_detik'] = data.get('length', 100) / V_NORMAL_MS  
            data['status_lalu_lintas'] = 'Normal'

    print("\n4. Membuat visualisasi peta kemacetan...")
    
    warna_jalan = []
    for u, v, k, data in G_proj.edges(keys=True, data=True):
        status = data.get('status_lalu_lintas', 'Normal')
        if status == 'Normal':
            warna_jalan.append('limegreen')
        else:
            warna_jalan.append('red')    

    try:
        fig, ax = ox.plot_graph(
            G_proj, 
            node_size=0, 
            edge_color=warna_jalan, 
            edge_linewidth=2, 
            bgcolor='black', 
            show=False, 
            close=False
        )
        fig.savefig("peta_kemacetan_dummy.png", dpi=300, bbox_inches='tight')
        plt.close(fig)
        print("   -> [BERHASIL] Gambar 'peta_kemacetan_dummy.png' berhasil dibuat!")
    except Exception as e:
        print(f"   -> [GAGAL] Gagal membuat gambar: {e}")

    print("\n5. Menyimpan data graf untuk modul selanjutnya...")
    
    output_filename = "uns_projected_graph.graphml"
    ox.save_graphml(G_proj, filepath=output_filename)
    nodes_proj.to_csv("tabel_nodes_uns.csv")
    
    try:
        cols_to_save = ['name', 'length', 'status_lalu_lintas', 'waktu_tempuh_detik']
        cols_to_save = [c for c in cols_to_save if c in edges_proj.columns]
        edges_proj[cols_to_save].to_csv("tabel_edges_uns.csv")
    except Exception as e:
        print(f"Catatan: Gagal menyimpan CSV tabel jalan ({e}), namun graf tetap aman.")

    print(f"   -> [BERHASIL] File graf disimpan sebagai: '{output_filename}'")
    print(f"   -> [BERHASIL] File tabel disimpan sebagai: 'tabel_nodes_uns.csv' & 'tabel_edges_uns.csv'")
    print("="*60)

if __name__ == "__main__":
    main()