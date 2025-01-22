# Usar una imagen base de Python
FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos de la aplicación al contenedor
COPY . .

# Instalar las dependencias necesarias
RUN pip install -r requirements.txt

# Exponer el puerto que usará FastAPI (por defecto 9875)
EXPOSE 9875

# Comando para ejecutar la aplicación
CMD ["uvicorn", "indicator_api:app", "--host", "0.0.0.0", "--port", "9875"]