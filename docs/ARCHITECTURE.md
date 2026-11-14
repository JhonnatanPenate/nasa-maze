# Planetary Explorer
### Propuesta de proyecto y arquitectura de software

## 1. Descripción del proyecto

Planetary Explorer es una herramienta de navegación geoespacial inteligente que permite calcular rutas entre dos ubicaciones sobre la superficie de cuerpos celestes, inicialmente Marte o la Luna.

Inspirado en herramientas como Waze, el sistema permitirá buscar ubicaciones mediante nombres de referencia, seleccionar un origen y un destino, y obtener rutas optimizadas considerando las características físicas, geológicas y ambientales del terreno.

A diferencia de un navegador convencional, Planetary Explorer no se limita a encontrar el camino más corto, sino que evalúa las condiciones de transitabilidad y los posibles riesgos asociados al desplazamiento.

## 2. Funcionamiento general

El usuario introduce una ubicación de origen y otra de destino. El sistema convierte ambas referencias en coordenadas planetarias y consulta los conjuntos de datos geoespaciales disponibles localmente.

Posteriormente, analiza diferentes variables:

- **Geográficas:** elevación, pendientes, cráteres, formaciones rocosas y características del terreno.
- **Ambientales:** temperatura, radiación y otras condiciones que puedan afectar el desplazamiento.

Con esta información, el motor de navegación calcula rutas alternativas y presenta distancia, tiempo estimado, advertencias y riesgos relevantes.

El resultado será un mapa interactivo que permita identificar la ubicación, visualizar los trayectos y consultar información específica de cada ruta.

## 3. Arquitectura basada en microservicios

El proyecto se desarrollará utilizando una arquitectura de microservicios dentro de un único repositorio (Monorepo). Cada integrante será responsable de desarrollar un servicio independiente, con una responsabilidad específica y una API propia.

La arquitectura estará compuesta por seis microservicios y un componente central denominado **Core**, encargado de coordinar su comunicación.

| Componente | Responsabilidad |
|---|---|
| **1. Location Service** | Buscar ubicaciones planetarias y convertir nombres en coordenadas. |
| **2. Data Management Service** | Consultar fuentes científicas oficiales, descargar datasets y administrar sus actualizaciones. |
| **3. Raster Service** | Administrar el acceso a archivos geoespaciales y proporcionar consultas sobre sus valores. |
| **4. Terrain Analysis Service** | Analizar elevación, pendientes y características físicas del terreno. |
| **5. Risk Assessment Service** | Evaluar riesgos ambientales y geográficos que puedan afectar el desplazamiento. |
| **6. Routing Engine** | Calcular y optimizar rutas considerando distancia, tiempo y condiciones de transitabilidad. |
| **Core** | Recibir solicitudes, coordinar los microservicios e integrar sus resultados para entregarlos al usuario. |

Cada microservicio tendrá independencia lógica y podrá desarrollarse, ejecutarse y probarse individualmente. La comunicación entre ellos se realizará principalmente mediante APIs REST.

## 4. Gestión y disponibilidad de los datos

El sistema aprovechará fuentes científicas oficiales, como NASA, USGS y otros repositorios de información planetaria, para obtener conjuntos de datos geoespaciales.

Se utilizarán formatos como GeoTIFF y GeoPackage para almacenar información cartográfica y ambiental.

Los datos se organizarán en un almacenamiento local compartido. El Raster Service funcionará como punto de acceso común a la información geoespacial, evitando que cada microservicio tenga que descargar o duplicar los mismos archivos.

Los servicios de análisis podrán generar nuevas capas derivadas, como mapas de pendientes o riesgos, que también quedarán disponibles localmente.

La descarga y actualización de información requerirá conexión a Internet, pero la consulta de ubicaciones, el análisis y el cálculo de rutas deberán funcionar sin conexión una vez preparados los datasets necesarios.

## 5. Tecnologías y organización

Se propone utilizar Python y FastAPI para desarrollar los microservicios, Rasterio/GDAL para el procesamiento geoespacial, SQLite para el catálogo de datasets y Docker Compose para ejecutar e integrar los componentes.

El repositorio único contendrá los seis microservicios, el Core, los paquetes compartidos, la configuración de infraestructura y la documentación técnica.

## 6. Alcance inicial

El MVP se enfocará en un único cuerpo celeste y una región geográfica delimitada. Deberá demostrar la búsqueda de ubicaciones, consulta de datos offline, análisis topográfico, evaluación básica de riesgos y generación de rutas alternativas.

El objetivo principal es construir una plataforma modular y extensible que demuestre la viabilidad de la navegación inteligente sobre superficies planetarias, dejando abierta la incorporación de nuevas variables, fuentes científicas y cuerpos celestes en futuras versiones.

---

**Principio del proyecto:** transformar datos científicos geoespaciales en información útil para tomar decisiones de navegación sobre superficies extraterrestres.

For more information: [Chat GPT Conversation GPT-4](https://chatgpt.com/share/6af895f4-de94-83e8-9d60-52998ca71e0e)