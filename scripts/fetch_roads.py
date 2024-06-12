import osmnx as ox
import geopandas as gpd

def descargar_calles(ciudad):
    # Descargar los datos de la ciudad desde OpenStreetMap
    graph = ox.graph_from_place(ciudad, network_type='all')
    
    # Convertir los datos en un GeoDataFrame de calles
    gdf = ox.graph_to_gdfs(graph, nodes=False, edges=True)
    
    return gdf

if __name__ == "__main__":
    ciudad = "Concepción, Chile"  # Puedes cambiar la ciudad aquí
    print(f'Descargando las calles de {ciudad}')
    gdf_calles = descargar_calles(ciudad)
    
    # Mostrar información básica del GeoDataFrame
    print("Número de calles descargadas:", len(gdf_calles))
    print("Esquema del GeoDataFrame:")
    print(gdf_calles.head())
    gdf_calles.reset_index(inplace=True)
    gdf_calles.to_parquet("/app/data/roads.parquet")
