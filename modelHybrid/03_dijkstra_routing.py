import osmnx as ox
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt

def main():
    print("=" * 60)
    print(" MODUL 03: DIJKSTRA ROUTING (FASTEST ROUTE) ")
    print("=" * 60)

    print("\n1. Memuat seluruh data...")
    try:
        G_proj = ox.load_graphml("uns_projected_graph.graphml")

        for u, v, k, data in G_proj.edges(data=True, keys=True):
            if 'waktu_tempuh_detik' in data:
                data['waktu_tempuh_detik'] = float(data['waktu_tempuh_detik'])

            if 'length' in data:
                data['length'] = float(data['length'])

        df_kandidat = pd.read_csv("kandidat_driver.csv")
        df_user = pd.read_csv("lokasi_user.csv")
        df_daftar = pd.read_csv("daftar_driver.csv")

    except FileNotFoundError as e:
        print(f"\n[ERROR] File tidak ditemukan: {e.filename}")
        return

    tipe_node = type(list(G_proj.nodes())[0])

    user_node = tipe_node(df_user['Node_ID'].iloc[0])

    print(f"   -> [SUKSES] Memuat Peta UNS dan {len(df_kandidat)} Kandidat Driver.")
    print(f"   -> Posisi User di Node ID: {user_node}")

    # =====================================================
    # VISUALISASI SEMUA DRIVER
    # =====================================================

    print("\n2. Membuat visualisasi seluruh kandidat driver...")

    try:
        fig, ax = ox.plot_graph(
            G_proj,
            node_size=0,
            edge_linewidth=0.8,
            bgcolor='black',
            show=False,
            close=False
        )

        all_driver_x = []
        all_driver_y = []

        for _, row in df_kandidat.iterrows():
            node_id = tipe_node(row['Node_ID'])

            all_driver_x.append(G_proj.nodes[node_id]['x'])
            all_driver_y.append(G_proj.nodes[node_id]['y'])

        daftar_driver_x = []
        daftar_driver_y = []

        for _, row in df_daftar.iterrows():
            node_id = tipe_node(row['Node_ID'])

            daftar_driver_x.append(G_proj.nodes[node_id]['x'])
            daftar_driver_y.append(G_proj.nodes[node_id]['y'])

        user_x = G_proj.nodes[user_node]['x']
        user_y = G_proj.nodes[user_node]['y']

        # Semua driver awal (sebelum difilter)
        ax.scatter(
            daftar_driver_x,
            daftar_driver_y,
            c='purple',
            s=60,
            alpha=0.6,
            edgecolors='white',
            label='Seluruh Driver'
        )

        # Semua kandidat driver
        ax.scatter(
            all_driver_x,
            all_driver_y,
            c='yellow',
            s=60,
            alpha=0.8,
            edgecolors='black',
            label='Kandidat Driver'
        )

        # User
        ax.scatter(
            user_x,
            user_y,
            c='red',
            s=180,
            edgecolors='white',
            linewidths=2,
            label='User'
        )

        ax.legend(
            loc='upper right',
            facecolor='black',
            labelcolor='white'
        )

        fig.savefig(
            "driver_candidates.png",
            dpi=300,
            bbox_inches='tight'
        )

        plt.close(fig)

        print("   -> [BERHASIL] driver_candidates.png dibuat!")

    except Exception as e:
        print(f"   -> [GAGAL] Visualisasi kandidat driver: {e}")

    # =====================================================
    # DIJKSTRA
    # =====================================================

    print("\n3. Mengeksekusi Algoritma Dijkstra...")
    hasil_rute_dijkstra = []

    # Modified Weight
    PENALTI_PER_NODE = 5
    def waktu_dengan_penalti(u, v, data):
        waktu_edge = min(e.get('waktu_tempuh_detik', float('inf')) for e in data.values())
        return waktu_edge + PENALTI_PER_NODE

    for _, row in df_kandidat.iterrows():
        driver_id = row['Driver_ID']
        driver_node = tipe_node(row['Node_ID'])
        jarak_euclidean = row['Jarak_Euclidean_Meter']

        try:
            waktu_tempuh_total_raw, jalur_rute = nx.single_source_dijkstra(
                G=G_proj,
                source=driver_node,
                target=user_node,
                weight=waktu_dengan_penalti
            )

            # Tahap Lanjutan
            jarak_aktual_rute = 0
            waktu_tempuh_dasar = 0
            for i in range(len(jalur_rute) - 1):
                u = jalur_rute[i]
                v = jalur_rute[i + 1]

                jarak_aktual_rute += G_proj[u][v][0]['length']
                waktu_tempuh_dasar += G_proj[u][v][0]['waktu_tempuh_detik']

            jumlah_simpang = max(0, len(jalur_rute) - 2)
            penalti_waktu = jumlah_simpang * PENALTI_PER_NODE
            waktu_tempuh_total = waktu_tempuh_total_raw - PENALTI_PER_NODE

            hasil_rute_dijkstra.append({
                'Driver_ID': driver_id,
                'Node_ID': driver_node,
                'Jarak_Euclidean_m': jarak_euclidean,
                'Jarak_Rute_Aktual_m': round(jarak_aktual_rute, 2),
                'Waktu_Tempuh_Dasar': round(waktu_tempuh_dasar, 2),
                'Jumlah_Simpang': jumlah_simpang,
                'Penalti_Detik': penalti_waktu,
                'Waktu_Tempuh_Total': round(waktu_tempuh_total, 2),
                'Rute_Jalur': jalur_rute
            })

            print(
                f"   -> [PROSES] {driver_id}"
                f" | Jarak: {round(jarak_aktual_rute,2)}m"
                f" | Simpang: {jumlah_simpang}"
                f" | Penalti detik: {penalti_waktu}"
                f" | Waktu tempuh dasar: {round(waktu_tempuh_dasar, 2)} detik"
                f" | ETA: {round(waktu_tempuh_total,2)} detik"
            )

        except nx.NetworkXNoPath:
            print(
                f"   -> [GAGAL] {driver_id}"
                f" tidak memiliki rute."
            )

    df_hasil = pd.DataFrame(hasil_rute_dijkstra)

    if df_hasil.empty:
        print("\n[GAGAL TOTAL] Tidak ada rute valid.")
        return

    df_hasil = (
        df_hasil
        .sort_values(by='Waktu_Tempuh_Total')
        .reset_index(drop=True)
    )

    driver_terpilih = df_hasil.iloc[0]

    menit = int(driver_terpilih['Waktu_Tempuh_Total'] // 60)
    detik = int(driver_terpilih['Waktu_Tempuh_Total'] % 60)

    print("\n" + "=" * 60)
    print(" DRIVER TERPILIH ".center(60))
    print("=" * 60)

    print(f"🏆 Driver      : {driver_terpilih['Driver_ID']}")
    print(f"📏 Euclidean   : {driver_terpilih['Jarak_Euclidean_m']} meter")
    print(f"🛣️ Jarak Rute  : {driver_terpilih['Jarak_Rute_Aktual_m']} meter")
    print(f"🚦 Simpang     : {driver_terpilih['Jumlah_Simpang']}")
    print(f"⏱️ ETA         : {driver_terpilih['Waktu_Tempuh_Total']} detik")
    print(f"⏱️ ETA         : {menit} menit {detik} detik")

    print("=" * 60)

    # =====================================================
    # VISUALISASI RUTE PEMENANG
    # =====================================================

    print("\n4. Membuat visualisasi rute pemenang...")

    try:

        rute_jalur = driver_terpilih['Rute_Jalur']

        fig, ax = ox.plot_graph_route(
            G_proj,
            rute_jalur,
            route_color='lime',
            route_linewidth=4,
            node_size=0,
            bgcolor='black',
            show=False,
            close=False
        )

        # Semua driver
        ax.scatter(
            all_driver_x,
            all_driver_y,
            c='yellow',
            s=60,
            alpha=0.5,
            label='Driver Lain'
        )

        driver_node_final = rute_jalur[0]

        driver_x = G_proj.nodes[driver_node_final]['x']
        driver_y = G_proj.nodes[driver_node_final]['y']

        # Driver terpilih
        ax.scatter(
            driver_x,
            driver_y,
            c='cyan',
            s=60,
            edgecolors='white',
            linewidths=2,
            zorder=10,
            label='Driver Terpilih'
        )

        # User
        ax.scatter(
            user_x,
            user_y,
            c='red',
            s=60,
            edgecolors='white',
            linewidths=2,
            zorder=10,
            label='User'
        )

        ax.legend(
            loc='upper right',
            facecolor='black',
            labelcolor='white'
        )

        fig.savefig(
            "rute_pemenang.png",
            dpi=300,
            bbox_inches='tight'
        )

        plt.close(fig)

        print("   -> [BERHASIL] rute_pemenang.png dibuat!")

    except Exception as e:
        print(f"   -> [GAGAL] {e}")

if __name__ == "__main__":
    main()