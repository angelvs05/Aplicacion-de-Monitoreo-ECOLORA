Aplicación de Monitoreo ECOLORA con Meshtastic
Esta aplicación de escritorio sirve como interfaz para conectar, visualizar y analizar datos de los nodos de sensores ECOLORA en tiempo real a través de una red LoRa Meshtastic.

Arquitectura del Proyecto
El código está organizado en módulos para facilitar su mantenimiento y escalabilidad.

main.py: Punto de entrada de la aplicación.

gui_manager.py: Construye y gestiona la interfaz gráfica.

serial_manager.py: Gestiona la conexión con el nodo Meshtastic.

database_manager.py: Se encarga de las operaciones con la base de datos.

data_processor.py: Analiza los datos y genera interpretaciones.

config.py: Almacena configuraciones globales.

requirements.txt: Lista de las dependencias de Python.

NOTA IMPORTANTE SOBRE NOMBRES DE ARCHIVO: En Python, los nombres de los archivos .py no deben contener espacios. Se utiliza snake_case (palabras separadas por guiones bajos) para asegurar que los import funcionen correctamente. Por favor, mantén los nombres de archivo como se proporcionan aquí.

Cómo Empezar
Crear un Entorno Virtual (Recomendado):

python -m venv .venv

Y actívalo:

Windows: .venv\Scripts\activate

macOS/Linux: source .venv/bin/activate

Instalar Dependencias: Abre una terminal en la carpeta del proyecto y ejecuta:

pip install -r requirements.txt

Conectar el Nodo Meshtastic: Conecta tu nodo gateway a tu PC a través de USB.

Ejecutar la Aplicación:

python main.py

La aplicación detectará el puerto COM. Selecciónalo y haz clic en "Conectar". A medida que tus otros nodos envíen datos, aparecerán en la pestaña "Gestión de Nodos".