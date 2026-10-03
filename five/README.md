# Five — la regla de los 5 segundos

Five es una pequeña app para Windows. Cuando te descubres procrastinando, presionas
**Ctrl + Alt + 5** y la pantalla completa se pone negra y cuenta **5, 4, 3, 2, 1… GO**.
Después te muestra **una** acción al azar de tu lista. La haces y presionas **Done**.

Todo se queda en tu computador. La app no usa internet, no necesita cuentas y no envía datos
a ningún lado. Solo la instalación descarga 3 librerías gratuitas de Python.

## Instalación (una sola vez)

1. **Descarga la carpeta `five`** a tu computador (por ejemplo a `Documentos\five`).
   Si la bajaste como ZIP, haz clic derecho sobre el ZIP → **Extraer todo**.
2. **Si no tienes Python:** entra a <https://www.python.org/downloads/>, descarga e instala Python.
   En la primera pantalla del instalador **marca la casilla "Add python.exe to PATH"**.
   (Si te lo saltas, `setup.bat` intenta instalarlo solo, pero así es más seguro).
3. Abre la carpeta `five` y haz **doble clic en `run.bat`**.
   - La primera vez se abre una ventana negra que instala todo (tarda 1 o 2 minutos).
   - Si Windows muestra "Windows protegió su PC", haz clic en **Más información → Ejecutar de todas formas**.
4. Cuando veas *"Five está corriendo"*, listo. Aparece un ícono **5** junto al reloj
   (puede estar escondido detrás de la flechita **^**).

A partir de ahí, **Five se abre solo cada vez que prendes Windows**.

## Cómo se usa

| Qué haces | Qué pasa |
|---|---|
| **Ctrl + Alt + 5** (en cualquier programa) | Te pregunta *"What do you need to do?"*. Puedes: **escribir** tu tarea y presionar **Enter**, hacer clic en **⚄ Random** (una acción al azar de tu lista), o hacer clic en **una acción de tu lista**. Luego empieza la cuenta regresiva |
| **+ Save to my list** | Guarda lo que escribiste en tu lista |
| **✕** junto a una acción | La borra de tu lista |
| **Esc** en la pregunta | Cancela sin anotar nada |
| Clic en **Done** o **Enter** | Se cierra y queda anotado como `done` en `log.csv` |
| **Esc** | Se cierra y queda anotado como `skipped` en `log.csv` |
| Clic derecho en el ícono **5** → **Open stats** | Te muestra tus estadísticas |
| Clic derecho → **Edit actions** | Abre tu lista de acciones en el Bloc de notas |
| Clic derecho → **Update Five** | Instala la versión nueva de Five (ver abajo) |
| Clic derecho → **Quit** | Cierra Five (hasta que lo vuelvas a abrir con `run.bat`) |

## Archivos que puedes editar (con el Bloc de notas)

- **`actions.txt`**: tus acciones, una por línea. Guarda el archivo y listo; no hay que reiniciar.
- **`config.txt`**: la configuración.
  - `hotkey=ctrl+alt+5`: el atajo de teclado. Ejemplos: `ctrl+shift+f`, `ctrl+alt+f9`.
  - `countdown_seconds=5`: cuántos segundos dura la cuenta regresiva.
  - `close_browser=false`: cámbialo a `true` para que al llegar a GO se cierren todas las
    ventanas de Chrome y Edge.
  - `autostart=true`: cámbialo a `false` si no quieres que Five arranque con Windows.
  - `ask_task=true`: Five te pregunta tu tarea antes de la cuenta regresiva. Con `false` siempre elige
    una acción al azar de `actions.txt`.

  Los cambios de `hotkey` y `autostart` necesitan reiniciar Five (clic derecho en el
  ícono → **Quit** y después doble clic en `run.bat`). Los demás funcionan desde la siguiente cuenta regresiva.

## Cómo actualizar Five

1. Descarga el nuevo `Five.zip` (déjalo en **Descargas**, no hace falta extraerlo).
2. Clic derecho en el ícono **5** → **Update Five**.

Five busca el zip más nuevo en Descargas, cambia solo sus archivos de programa (`five.py`, `run.bat`,
`setup.bat`, `README.md`) y se reinicia solo. **Tu `actions.txt`, tu `config.txt` y tu `log.csv` no se tocan.**
Guarda una copia de la versión anterior como `five.py.bak`, por si acaso.

## Archivos que crea Five

- **`log.csv`**: tu historial (fecha, hora, resultado y acción). Se abre con Excel.
- **`five_error.log`**: solo aparece si algo falla. Sirve para pedir ayuda.

## Estadísticas desde la terminal (opcional)

Abre la carpeta `five`, escribe `cmd` en la barra de direcciones y presiona Enter. Luego escribe:

```
py five.py --stats
```

Te muestra cuántas veces usaste Five esta semana (desde el lunes), cuántas veces elegiste `done` y
cuántas `skipped`, y tu **racha**: cuántos días seguidos tienes con al menos un `done`.

## Si algo no funciona

- **El atajo no hace nada:** revisa que el ícono **5** esté junto al reloj. Si no está, abre `run.bat`.
  Si un programa abierto como administrador tiene el foco, Windows no deja que otros programas
  vean el teclado. Haz clic en otra ventana y vuelve a intentarlo.
- **"Five is already running":** ya está abierto. Busca el ícono **5**.
- **Quiero desinstalarlo:** cierra Five (clic derecho → **Quit**), pon `autostart=false` en `config.txt`,
  abre `run.bat` una vez, ciérralo de nuevo con **Quit** y borra la carpeta.
