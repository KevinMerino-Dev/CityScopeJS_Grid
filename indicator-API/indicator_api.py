from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Callable
import os
import json
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path


#La clase indicador se encarga de contener los atributos y métodos necesarios para la creación de un indicador.
class Indicator:
    def __init__(self):
       #Contiene los datos de la capa actual
        self.data = None 
        #Contiene las capas de indicadores
        self.layers = []
        #Contiene los indicadores numéricos
        self.numeric = []
        #Contiene un diccionario con las capas de indicadores
        self.dict_of_layers = {}
        #Contiene un diccionario con los indicadores numéricos
        self.dict_of_numeric = {}
        #Contiene la capa actual
        self.actual_layer = None
        #Contiene la columna de valores para el indicador
        self.value_column = None
        #Contiene los valores mínimo y máximo para normalizar el colormap
        self.min_value = None
        self.max_value = None
        #Contiene el colormap para el indicador
        self.colormap = plt.cm.jet

    def create_layer(self, layer_id: str): #Crea una capa vacía con el ID especificado
        self.dict_of_layers[layer_id] = None

    def set_layer_to_edit(self, layer_id: str): #Establece la capa actual para editarla
        if layer_id not in self.dict_of_layers:
            raise ValueError(f"Layer '{layer_id}' not found. Load the layer data first.")
        self.actual_layer = layer_id
        self.data = None

    def read_data_to_layer(self, filepath: str): #Lee los datos de un archivo y los guarda en el diccionario de capas
        self.read_layer_data(filepath, self.actual_layer)

    def read_layer_data(self, filepath: str, layer_id: str): #Lee los datos de un archivo y los guarda en un diccionario
        data = gpd.read_file(filepath)
        data = data.to_crs(epsg=4326) #Se convierten los datos a EPSG 4326
        if 'geometry' not in data.columns:
            raise ValueError("GeoDataFrame must contain a 'geometry' column.")
        self.dict_of_layers[layer_id] = data
        self.data = data


    def set_value_column(self, column_name: str): #Establece la columna de valores para el indicador
        if column_name not in self.data.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the data.")
        self.value_column = column_name


    def set_min_max(self, min_value: float, max_value: float):#Establece los valores mínimo y máximo para normalizar el colormap
        self.min_value = min_value
        self.max_value = max_value

    def set_colormap(self, colormap: Any): #Establece el colormap para el indicador
        self.colormap = colormap

    def add_fill_column(self): #Agrega una columna de relleno a los datos, con esta nueva columna se  agregan los valores y colores a los polígonos.
        if self.value_column is None:
            raise ValueError("Value column must be set before calculating colors.")
        norm = plt.Normalize(vmin=self.min_value, vmax=self.max_value)
        self.data['color'] = self.data[self.value_column].apply(lambda x: self.colormap(norm(x))[:3])
        self.data['color'] = self.data['color'].apply(lambda rgb: tuple(int(c * 255) for c in rgb))
        self.data['fill'] = self.data['color'].apply(lambda x: '#%02x%02x%02x' % (x[0], x[1], x[2]))

    def delete_column(self, column_name: str): #Elimina una columna de los datos
        if self.value_column is None:
            raise ValueError("Value column must be set before calculating colors.")
        self.data.drop(columns=[column_name], inplace=True)

    def set_elevation_column(self, column_name: str): #Establece la columna que contiene los valores de elevación para el indicador
        if column_name not in self.data.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the data.")
        self.data['elevation'] = self.data[column_name]

    def update_layer(self): #Actualiza la capa actual con los datos actuales
        self.dict_of_layers[self.actual_layer] = self.data

    def add_indicator_layer(self, layer_id: str, layer_type: str ): #Agregar una capa de indicador a la lista de capas.
        data = self.dict_of_layers[layer_id]
        if data is None:
            raise ValueError("Data not loaded. Use read_data first.")
        features = json.loads(data.to_json())
        self.layers.append({"id": layer_id, "type": layer_type, "data": features, "properties": {"filled": True}})

    def add_indicator_numeric(self, layer_id: str): #Agrega un indicador numérico a la lista de indicadores numéricos
        self.numeric.append({"id": layer_id, "values": self.data[self.value_column].tolist()})

    def clear_layers_and_numeric(self): #Limpia las listas de capas y de indicadores numéricos
        self.layers = []
        self.numeric = []

    def get_layers_and_numeric(self) -> Dict[str, List[Any]]: #Devuelve un diccionario con las listas de capas e indicadores numéricos
        return {"layers": self.layers, "numeric": self.numeric}
    
    def delete_columns(self, columns_to_delete: list):
        if self.data is None:
            raise ValueError("No data loaded in the current layer.")
        print("Columns before deleting:", self.data.columns.tolist())
        self.data = self.data.drop(columns=columns_to_delete, errors='ignore')
        if self.actual_layer:
            self.dict_of_layers[self.actual_layer] = self.data
        print("Columns after deleting:", self.data.columns.tolist())

    def set_color_column(self, color_column: str): 
        if self.data is None:
            raise ValueError("No data loaded in the current layer.")
        norm = plt.Normalize(vmin=self.min_value, vmax=self.max_value)
        self.data[color_column] = self.data[self.value_column].apply(lambda x: self.colormap(norm(x))[:3])
        self.data[color_column] = self.data[color_column].apply(lambda rgb: tuple(int(c * 255) for c in rgb))
        #self.data['fill'] = self.data['color'].apply(lambda x: '#%02x%02x%02x' % (x[0], x[1], x[2]))

    def set_key_column(self, key_column: str): 
        if self.data is None:
            raise ValueError("No data loaded in the current layer.")
        if self.value_column is None:
            raise ValueError("Value column must be set before calculating colors.")
        self.data[key_column] = self.data[self.value_column]
        #self.data[key_column] = self.data[self.value_column].apply(lambda x: x)
        print(f"Key column '{key_column}' added successfully. Sample values:")
        print(self.data[key_column].head())


#A partir de ahora se comenzará a desarrollar la API REST con FastAPI.
app = FastAPI()
indicator = Indicator()

# Static folder setup
os.makedirs("/app/data", exist_ok=True)
app.mount("/static", StaticFiles(directory="/app/data"), name="static")

#FileRequest especifica el nombre del archivo a cargar.
class FileRequest(BaseModel): 
    filename: str

#Cargamos el archivo y lo almacenamos en una capa
@app.post("/read_data")
async def read_data(file_request: FileRequest): 
    try:
        filename = f"/app/data/{file_request.filename}"
        indicator.read_layer_data(filename, "default_layer")
        return {"message": f"File '{file_request.filename}' loaded successfully."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

#LayerRequest especifica el ID o identificador de la capa a crear.
class LayerRequest(BaseModel):
    layer_id: str

#Creamos una capa vacía con el ID especificado.
@app.post("/create_layer/")
async def create_layer(request: LayerRequest):
    """
    Crea un nuevo layer vacío con el ID especificado.
    """
    try:
        indicator.create_layer(request.layer_id)
        return {"message": f"Layer '{request.layer_id}' created successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

#Para configurar las columnas de valores.
class ValueColumnRequest(BaseModel):
    column_name: str

@app.post("/set_value_column/")
async def set_value_column(request: ValueColumnRequest):
    try:
        indicator.set_value_column(request.column_name)
        return {"message": f"Value column '{request.column_name}' set successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

#Establecemos la capa actual para editarla.
@app.post("/set_layer_to_edit/")
async def set_layer_to_edit(request: LayerRequest):
    try:
        layer_id = request.layer_id
        indicator.set_layer_to_edit(layer_id)
        return {"message": f"Layer '{layer_id}' set as current for editing."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

#FilePathRequest especifica la ruta del archivo a cargar, basicamente maneja los indentificadores de las capas.
class FilePathRequest(BaseModel):
    filepath: str

#Leemos los datos de un archivo y los almacenamos en la capa actual.
@app.post("/read_data_to_layer/")
async def read_data_to_layer(request: FilePathRequest):
    try:
        filename = Path(request.filepath)
        filename = f'/app/data/{filename}'
        indicator.read_data_to_layer(filename)
        return {"message": f"Data from '{request.filepath}' loaded into the current layer."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")


@app.post("/update_layer/")
async def update_layer():
    try:
        indicator.update_layer()
        return {"message": "Current layer updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

#IndicatorLayerRequest especifica el ID de la capa a agregar como indicador.
class IndicatorLayerRequest(BaseModel):
    layer_id: str
    layer_type: str


@app.post("/add_indicator_layer/")
async def add_indicator_layer(request: IndicatorLayerRequest):
    try:
        indicator.add_indicator_layer(request.layer_id, request.layer_type)
        return {"message": f"Indicator '{request.layer_id}' added successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/add_indicator_numeric/")
async def add_indicator_numeric(layer_id: str):
    try:
        indicator.add_indicator_numeric(layer_id)
        return {"message": f"Numeric indicator for layer '{layer_id}' added successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

#ElevationRequest especifica el nombre de la columna de elevación.
class ElevationRequest(BaseModel):
    column_name: str

@app.post("/set_elevation/")
async def set_elevation(request: ElevationRequest):
    try:
        indicator.set_elevation_column(request.column_name)
        return {"message": f"Elevation column set to '{request.column_name}' successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

#MinMaxRequest especifica los valores mínimo y máximo para normalizar el colormap.
class MinMaxRequest(BaseModel):
    min_value: float
    max_value: float

@app.post("/set_min_max/")
async def set_min_max(request: MinMaxRequest):
    """
    Define los valores mínimo y máximo para normalizar el colormap.
    """
    try:
        indicator.set_min_max(request.min_value, request.max_value)
        return {"message": "Min and max values set successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

#ColormapRequest especifica el nombre del colormap a utilizar y configura el mapa de color para el indicador.
class ColormapRequest(BaseModel):
    colormap_name: str

@app.post("/set_colormap/")
async def set_colormap(request: ColormapRequest):
    try:
        colormap = getattr(plt.cm, request.colormap_name, None)
        if colormap is None:
            return {"error": f"Colormap '{request.colormap_name}' not found."}
        indicator.set_colormap(colormap)
        return {"message": f"Colormap '{request.colormap_name}' set successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/add_fill_column/")
async def add_fill_column():
    try:
        indicator.add_fill_column()
        return {"message": "Fill column added successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

#Reiniciamos las capas e indicadores
@app.post("/clear_layers_and_numeric/")
async def clear_layers_and_numeric():
    try:
        indicator.clear_layers_and_numeric()
        return {"message": "Layers and numeric cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Modelo para recibir la lista de columnas a eliminar
class DeleteColumnsRequest(BaseModel):
    columns: list

@app.post("/delete_columns/")
async def delete_columns_endpoint(request: DeleteColumnsRequest):
    try:
        # Se asume que la capa a editar ya ha sido establecida
        indicator.delete_columns(request.columns)
        return {"message": "Columnas eliminadas correctamente.", "remaining_columns": indicator.data.columns.tolist()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
class columnRequest(BaseModel):
    column: str

@app.post("/add_color_column/")
async def set_color_column(request: columnRequest):
    try:
        # Se asume que la capa a editar ya ha sido establecida
        indicator.set_color_column(request.column)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/add_key_column/")
async def set_key_column(request: columnRequest):
    try:
        # Se asume que la capa a editar ya ha sido establecida
        indicator.set_key_column(request.column)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

#Home
@app.get("/")
async def root():
    return {"message": "Home - API de Indicadores"}

#Recupera información sobre las capas e indicadores
@app.get("/get_layers_and_numeric/")
async def get_layers_and_numeric():
    try:
        return indicator.get_layers_and_numeric()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


#Recupera información sobre las capas e indicadores
@app.get("/get_columns/")
async def get_columns():
    try:
        return indicator.data.columns
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))