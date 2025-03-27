import websocket
import rel
from time import sleep
import json
from threading import Thread

class MicroBrix():

    remote_host = 'cityio.media.mit.edu/cityio' #Se conecta al servidor CityIO.
    geogrid_data = {}  #Es un diccionario para almacenar los datos del grid geográfico.
    geogrid = {}  #Este diccionario almacena el grid estructural.

    #Este es el constructor!
    def __init__(self, 
            table_name=None,         #Nombre de la tabla a suscribirse
            quietly=False,           
            host_mode ='remote',     #Especifica la forma de conectarse. local o remote.
            host_name = None,        
            core = False,            #Indica si el módulo es "core" en CityIO
            core_name = None,        
            core_description = None, 
            core_category = None,     
            keep_updating = False,   #Permiten realizar actualizaciones automáticas
            update_interval = 5.0,   #Intervalo en el que se realiza la actualización
            module_function = None,  #Función que devuelve las capas (layers) y los datos (numeric)
            save = False             #Este apartado icore_descriptionndica si los datos se guardarán en la tabla.
    ):

        if host_name is None:
            self.host = self.remote_host
        else:
            self.host = host_name.strip('/')
        self.host = '127.0.0.1:8080' if host_mode=='local' else self.host

        #Variables iniciales
        self.quietly = quietly
        self.save = save
        self.keep_updating = keep_updating
        self.update_interval = update_interval
        self.table_name = table_name
        self.core = core
        self.core_name = core_name
        self.core_description = core_description
        self.core_category = core_category
        self.secure_protocol = '' if host_mode == 'local' else 's'
        #Variables para definir URL para interactuar con la API de CityIO
        self.front_end_url   = f'http{self.secure_protocol}://cityio-beta.media.mit.edu/?cityscope={self.table_name}'
        self.cityIO_post_url = f'http{self.secure_protocol}://{self.host}/api/table/{table_name}/'
        self.cityIO_list = f'http{self.secure_protocol}://{self.host}/api/table/list/'
        self.cityIO_wss = f'ws{self.secure_protocol}://{self.host}/module'
        if core:
            self.cityIO_wss = self.cityIO_wss + '/core'

        if(module_function == None):
            raise ValueError("module_function should contain a function that returns DeckGL layers")

        self.module_function = module_function

        if(not self.quietly):
            websocket.enableTrace(True)
        #Configuramos el WebSocket
        self.ws = websocket.WebSocketApp(
            self.cityIO_wss,
            on_open=self.on_open,   
            on_message=self.on_message, #Manejo de mensajes recibidos
            on_error=self.on_error,     #Captura los errores de la conexión
            on_close=self.on_close     
            )
        
    #Manejo de Mensajes
    def on_message(self, ws, message):
        dict_rec = json.loads(message)  #Toma el mensaje que trae un JSON
        message_type = dict_rec['type'] #Cambia el formato de json a diccionario de Python
        if(message_type == 'TABLE_SNAPSHOT'):      #Table_snapshot
            table_name = dict_rec['content']['tableName']
            self.geogrid_data[table_name] = dict_rec['content']['snapshot']['GEOGRIDDATA']
            self.geogrid[table_name] = dict_rec['content']['snapshot']['GEOGRID']
            self.perform_update(table_name)
            thread = Thread(target = self.threaded_function, args = (table_name, ), daemon=True)
            thread.start()
        elif(message_type == 'GEOGRIDDATA_UPDATE'):                 #Geogriddata
            print(dict_rec)
            table_name = dict_rec['content']['tableName']
            self.geogrid_data[table_name] = dict_rec['content']['geogriddata']
            self.perform_update(table_name)
        elif(self.core and message_type == 'SUBSCRIPTION_REQUEST'):  #Subscription
            requester = dict_rec['content']['table']
            self.send_message(json.dumps({"type":"SUBSCRIBE","content":{"gridId":requester}}))
        elif(self.core and message_type == 'SUBSCRIPTION_REMOVAL_REQUEST'):   #Removal
            requester = dict_rec['content']['table']  
            # self._clear_values(requester)
            self.send_message(json.dumps({"type":"UNSUBSCRIBE","content":{"gridId":requester}}))

    def on_error(self, ws, error):   #Definimos errores
        print(error)

    def on_close(self, ws, close_status_code, close_msg):   
        print("## Connection closed")
   

    def on_open(self, ws):     
        print("## Opened connection")
        if self.core:
            self.send_message(json.dumps({"type":"CORE_MODULE_REGISTRATION","content":{"name":self.core_name, "description": self.core_description, "moduleType":self.core_category}}))
        else:
            self.send_message(json.dumps({"type":"SUBSCRIBE","content":{"gridId":self.table_name}}))

    #Entrega el mensaje guardado en "message"
    def send_message(self, message):
        self.ws.send(message)

    #Linea para actualizaciones
    def threaded_function(self,table_name):
        if(self.keep_updating):
            while True:
                try:
                    sleep(self.update_interval)
                    self.perform_update(table_name)
                except:
                    continue
    
    #Construye el mensaje con los datos
    #Entrega Layers y Numeric de acuerdo a lo que se recibio
    def _send_indicators(self, layers, numeric, table):
        if(layers is not None and numeric is not None):
            message = {"type": "MODULE", "content":{"gridId": table, "save": self.save, "moduleData":{"layers":layers,"numeric":numeric}}}
        elif(layers is not None):
            message = {"type": "MODULE", "content":{"gridId": table, "save": self.save, "moduleData":{"layers":layers}}}
        elif(numeric is not None):
            message = {"type": "MODULE", "content":{"gridId": table, "save": self.save, "moduleData":{"numeric":numeric}}}

        self.send_message(json.dumps(message))
    
    #Llama al modulo para generar capas y los datos numericos. Esta información se envía mediante send_indicators.
    def perform_update(self,table):
        layers, numeric = self.module_function(self.geogrid[table],self.geogrid_data[table])
        self._send_indicators(layers, numeric ,table)

    #Esta linea de codigo abre la comunicación. Abre el WebSocket
    def listen(self):
        self.ws.run_forever(dispatcher=rel, reconnect=5)
        rel.signal(2, rel.abort)  # Keyboard Interrupt
        rel.dispatch()
    
    def stop(self):
        self.ws.close()
