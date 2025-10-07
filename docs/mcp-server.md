# MCP Server

## Resumen

El servidor MCP `capi-mcp-server` expone herramientas pensadas para que los agentes puedan navegar la documentacion del proyecto, inspeccionar archivos relevantes y ejecutar busquedas puntuales dentro del repositorio. Sigue el protocolo Model Context Protocol utilizando la libreria oficial `@modelcontextprotocol/sdk`.

## Instalacion

1. Asegurate de tener Node.js 18 o superior disponible en tu maquina.
2. Instala las dependencias localmente:
   ```bash
   npm install --prefix mcp
   ```
3. Opcional: puedes probar el servidor en modo interactivo con el inspector oficial:
   ```bash
   npx @modelcontextprotocol/inspector --command "npm" -- "--prefix" "$(pwd)/mcp" "run" "start"
   ```

## Configuracion en Codex CLI

Anade la siguiente seccion a tu `config.toml` (o define un perfil equivalente) para habilitar el servidor via STDIO:

```toml
[mcp_servers.capi]
command = "npm"
args = ["--prefix", "<ruta-del-repo>/mcp", "run", "start"]
startup_timeout_sec = 20
```

- Si clonas el repositorio en otra ruta, ajusta el segundo argumento de `--prefix`.
- Puedes reducir `startup_timeout_sec` si el servidor inicia rapidamente en tu entorno.

## Herramientas disponibles

- `list-project-files`: lista directorios y archivos dentro de `docs/`, `Backend/src` y `Frontend/src`, con soporte opcional para recorrer subdirectorios y limitar resultados.
- `read-project-file`: lee archivos de texto dentro de los mismos roots aplicando un limite de bytes configurable para evitar respuestas demasiado grandes.
- `search-project-files`: realiza busquedas de texto (sensibles o no a mayusculas) sobre archivos de texto en los roots permitidos y devuelve coincidencias con numero de linea y fragmento.

Todas las herramientas validan rutas para impedir accesos fuera de los directorios permitidos y unicamente operan sobre archivos considerados de texto.

## Recursos expuestos

Para cada root disponible se expone un esquema de URI (`docs://`, `backend://`, `frontend://`) que permite a clientes compatibles listar directorios o recuperar el contenido de archivos de texto de forma directa.

## Proximos pasos

- Automatiza la instalacion ejecutando `npm install --prefix mcp` como parte de tu bootstrap local.
- Considera agregar pruebas automatizadas para las funciones criticas del servidor si se extiende con logica adicional.
- Si habilitas nuevos roots o rutas sensibles, documenta los cambios y manten el listado de extensiones permitidas acorde a las necesidades del equipo.
