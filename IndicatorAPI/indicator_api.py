from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import json
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path


class Indicator:
    def __init__(self):
        self.data = None
        self.layers = []
        self.numeric = []
        self.dict_of_layers = {}
        self.dict_of_numeric = {}
        self.actual_layer = None
        self.value_column = None
        self.min_value = None
        self.max_value = None
        self.colormap = plt.cm.jet

    def create_layer(self, layer_id: str):
        self.dict_of_layers[layer_id] = None

    def set_layer_to_edit(self, layer_id: str):
        if layer_id not in self.dict_of_layers:
            raise ValueError(f"Layer '{layer_id}' not found. Load the layer data first.")
        self.actual_layer = layer_id
        self.data = None

    def read_data_to_layer(self, filepath: str):
        self.read_layer_data(filepath, self.actual_layer)

    def read_layer_data(self, filepath: str, layer_id: str):
        data = gpd.read_file(filepath)
        data = data.to_crs(epsg=4326)
        if 'geometry' not in data.columns:
            raise ValueError("GeoDataFrame must contain a 'geometry' column.")
        self.dict_of_layers[layer_id] = data
        self.data = data

    def set_value_column(self, column_name: str):
        if column_name not in self.data.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the data.")
        self.value_column = column_name

    def set_min_max(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value

    def set_colormap(self, colormap: Any):
        self.colormap = colormap

    def add_fill_column(self):
        if self.value_column is None:
            raise ValueError("Value column must be set before calculating colors.")
        norm = plt.Normalize(vmin=self.min_value, vmax=self.max_value)
        self.data['color'] = self.data[self.value_column].apply(lambda x: self.colormap(norm(x))[:3])
        self.data['color'] = self.data['color'].apply(lambda rgb: tuple(int(c * 255) for c in rgb))
        self.data['fill'] = self.data['color'].apply(lambda x: '#%02x%02x%02x' % (x[0], x[1], x[2]))

    def update_layer(self):
        self.dict_of_layers[self.actual_layer] = self.data

    def add_indicator_layer(self, layer_id: str, layer_type: str = "geojson"):
        data = self.dict_of_layers[layer_id]
        if data is None:
            raise ValueError("Data not loaded. Use read_data first.")
        features = json.loads(data.to_json())
        self.layers.append({"id": layer_id, "type": layer_type, "data": features, "properties": {"filled": True}})

    def add_indicator_numeric(self, layer_id: str):
        self.numeric.append({"id": layer_id, "values": self.data[self.value_column].tolist()})

    def clear_layers_and_numeric(self):
        self.layers = []
        self.numeric = []

    def get_layers_and_numeric(self) -> Dict[str, List[Any]]:
        return {"layers": self.layers, "numeric": self.numeric}


app = FastAPI()
indicator = Indicator()

# Static folder setup
os.makedirs("/app/data", exist_ok=True)
app.mount("/static", StaticFiles(directory="/app/data"), name="static")


class FileRequest(BaseModel):
    filename: str


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


class LayerRequest(BaseModel):
    layer_id: str

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


@app.post("/set_layer_to_edit/")
async def set_layer_to_edit(request: LayerRequest):
    try:
        layer_id = request.layer_id
        indicator.set_layer_to_edit(layer_id)
        return {"message": f"Layer '{layer_id}' set as current for editing."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class FilePathRequest(BaseModel):
    filepath: str

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

class IndicatorLayerRequest(BaseModel):
    layer_id: str
    layer_type: str = "geojson"

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

class ColumnRequest(BaseModel):
    column_name: str

@app.post("/set_value_column/")
async def set_value_column(request: ColumnRequest):
    try:
        column_name = request.column_name
        indicator.set_value_column(column_name)
        return {"message": f"Column '{column_name}' set as value column."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@app.post("/clear_layers_and_numeric/")
async def clear_layers_and_numeric():
    try:
        indicator.clear_layers_and_numeric()
        return {"message": "Layers and numeric cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/get_layers_and_numeric/")
async def get_layers_and_numeric():
    try:
        return indicator.get_layers_and_numeric()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
