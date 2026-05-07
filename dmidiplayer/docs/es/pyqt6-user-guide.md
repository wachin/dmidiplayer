# Guía de usuario de dmidiplayer PyQt6

Esta guía explica la interfaz actual de PyQt6 en lenguaje claro. Sirve para
entender para qué funciona cada control visible en la versión Python tal como
existe hoy.

## Ventana principal

La ventana principal está dividida en dos áreas:

- `List`: la lista de reproducción. Muestra los archivos MIDI en cola.
- Área de reproducción: información de la canción, deslizador de posición,
  controles de reproducción, panel de ritmo, fila de destino MIDI, teclado
  visual y texto de estado.

Si todavía no hay un archivo cargado, la ventana inicia vacía y espera a que
abras un archivo MIDI o una lista `.lst`.

## Menú File

- `Open`: abre uno o más archivos MIDI o una lista de reproducción `.lst`.
- `Open Playlist`: abre directamente un archivo de lista de reproducción.
- `Open Recent`: vuelve a abrir un archivo MIDI usado recientemente.
- `Save Playlist`: guarda la lista actual en el archivo `.lst` actual.
- `Save Playlist As`: guarda la lista actual en un nuevo archivo `.lst`.
- `Move Up`: mueve la fila seleccionada una posición hacia arriba.
- `Move Down`: mueve la fila seleccionada una posición hacia abajo.
- `Sort Playlist`: ordena la lista alfabéticamente por nombre de archivo.
- `Remove Selected`: elimina la fila seleccionada.
- `Clear Playlist`: elimina todas las filas y descarga la canción actual.
- `Exit`: cierra la aplicación.

## Menú Playback

- `Previous`: carga la entrada anterior de la lista.
- `Play`: inicia la reproducción desde la posición actual.
- `Pause`: pausa la reproducción y conserva la posición.
- `Stop`: detiene la reproducción y vuelve al inicio.
- `Next`: carga la siguiente entrada de la lista.
- `Bar -`: salta al comienzo del compás anterior.
- `Bar +`: salta al comienzo del compás siguiente.
- `Go`: salta al compás indicado en el control `Jump bar`.
- `Repeat Playlist`: al llegar a la última canción, continúa desde la primera.
- `Shuffle Playlist`: elige la siguiente canción al azar en vez de seguir el
  orden normal.
- `Auto-Play On Load`: inicia la reproducción automáticamente al cargar un
  archivo.
- `Playlist Auto-Advance`: continúa automáticamente con la siguiente entrada
  cuando termina una canción.

## Menú View

- `Channels`: abre la ventana de actividad de canales.
- `Lyrics`: abre la ventana de texto y letras de la canción actual.
- `Toolbar`: muestra u oculta la barra de herramientas.
- `Status bar`: muestra u oculta la barra de estado.
- `Keyboard`: muestra u oculta la vista del teclado.
- `Rhythm`: muestra u oculta el panel de ritmo.

## Menú Tools

- `Preferences`: abre el cuadro de preferencias actual.
- `Refresh MIDI Destinations`: vuelve a buscar las salidas MIDI disponibles.
- `Connect MIDI Destination`: conecta el destino MIDI seleccionado.
- `Disconnect MIDI Destinations`: desconecta todos los destinos MIDI activos.

## Menú Help

- `Help Contents`: abre el índice general de ayuda local.
- `User Guide`: abre esta guía.
- `About`: muestra créditos del proyecto, enlaces clicables para los autores,
  información de licencia y las tecnologías principales usadas en el port a
  Python/PyQt6.

## Barra de herramientas

La barra de herramientas expone las acciones principales de uso diario:

- `Open`
- `Previous`
- `Play`
- `Pause`
- `Stop`
- `Next`

Es la forma más rápida de navegar y controlar la reproducción una vez que ya
hay archivos cargados.

## Área de lista

La `List` de la izquierda es la lista de reproducción actual.

- Un clic selecciona una fila.
- Doble clic carga esa canción.
- Abrir varios archivos MIDI crea una lista temporal automáticamente.
- Abrir una lista `.lst` carga esa lista guardada.
- Por omisión no se duplican filas. Si abres un archivo que ya estaba en la
  lista, se reutiliza la fila existente.

Si el título de la ventana muestra un `*` antes del nombre de la lista, eso
indica que hay cambios sin guardar.

## Información de la canción

La línea de texto encima del deslizador de posición muestra un resumen del
archivo cargado:

- título del archivo
- formato MIDI
- número de pistas
- longitud total en ticks
- duración aproximada en segundos

## Deslizador de posición y línea de tiempo

El deslizador horizontal muestra la posición actual de reproducción.

- Puedes arrastrarlo para buscar otro punto dentro de la canción.
- La línea debajo muestra:
  - tiempo actual
  - tiempo total
  - BPM efectivo
  - compás actual y total de compases

## Controles de reproducción en el panel principal

La primera fila contiene:

- `Pitch`: transpone la canción entre `-12` y `+12` semitonos.
- `0`: restablece el tono normal.
- `Drums`: elige qué canal MIDI se tratará como percusión y no se transpondrá.
- `Tempo`: escala la velocidad entre `50%` y `200%`.
- `100%` junto a `Tempo`: restablece la velocidad normal.
- `Volume`: escala el volumen MIDI CC7 entre `0%` y `200%`.
- `100%` junto a `Volume`: restablece el volumen normal.
- `Bar -`: salta al compás anterior.
- `Bar +`: salta al compás siguiente.

## Controles de salto y bucle

La segunda fila contiene:

- `Jump bar`: elige el compás de destino.
- `Go`: salta directamente al compás elegido.
- `Loop`: activa o desactiva el bucle.
- `Start bar`: primer compás del bucle.
- `End bar`: último compás del bucle.

Cuando `Loop` está activado, la reproducción repite el rango entre `Start bar`
y `End bar`.

## Panel de ritmo

El panel de ritmo muestra información musical en tiempo real:

- compás activo, por ejemplo `4/4`
- número de compás actual
- número de pulso actual
- BPM actual
- una tira de pulsos donde el pulso activo queda resaltado

Este panel se actualiza durante la reproducción y también cuando haces una
búsqueda manual.

## Ventana de canales

La ventana `Channels` se abre desde el menú `View`. Muestra una fila por cada
canal MIDI usado por la canción cargada.

Cada fila incluye actualmente:

- `Channel`: el número de canal MIDI
- `Label`: una etiqueta de texto editable para ese canal
- `Mute`: silencia ese canal durante la reproducción
- `Solo`: mantiene ese canal a nivel completo mientras reduce los otros según
  la preferencia actual de reducción de solo
- `Program`: envía un cambio de programa para ese canal y reemplaza los cambios
  de programa posteriores que vengan desde el archivo. El selector ahora muestra
  nombres de instrumentos General MIDI en lugar de solo números
- `Lock`: ignora los cambios de programa posteriores que vengan desde el archivo
- `Volume`: ajusta el nivel de reproducción de ese canal entre `0%` y `200%`
- `Level`: un medidor de actividad en vivo que sigue la velocidad de las notas
  mientras la reproducción está en marcha

Este sigue siendo un tramo temprano del port de la vista de canales, así que
todavía faltan comportamientos de canal más avanzados.

## Ventana de letras

La ventana `Lyrics` se abre desde el menú `View`. Muestra eventos de texto MIDI
relacionados con la canción cargada.

El filtro superior permite cambiar entre:

- `All tracks`
- `Track 1`, `Track 2` y así sucesivamente para las pistas que contienen texto
- `All`
- `Lyrics`
- `Text`
- `Marker`
- `Cue Point`
- `Other`

Cuando un archivo tiene texto en varias pistas, la ventana empieza
automaticamente en la pista que contiene eventos de letra cuando existe una. Si
el archivo tiene texto pero no una pista de letras dedicada, entonces usa como
respaldo la pista con mas eventos de texto. Si vuelves a `All tracks`, veras el
numero de pista delante de cada linea para distinguir el origen.

El selector `Encoding` controla como se decodifica en la ventana el texto MIDI
incrustado. `Auto` usa la deteccion integrada, mientras que `UTF-8`,
`Latin-1` y `CP1252` te permiten forzar manualmente la visualizacion.

Usa `Save` para guardar en un archivo el texto filtrado actual. Cuando esta
seleccionado `Auto`, el archivo se guarda como `UTF-8`; en los demas casos se
usa la codificacion elegida.

Usa `Print` para enviar el texto filtrado actual a una impresora mediante el
cuadro de impresion estandar de Qt.

Usa `Copy` para llevar al portapapeles el texto filtrado actual. Usa `Font`
para elegir una fuente mas comoda para el panel de letras. Usa `Fullscreen`
para ampliar la ventana de letras durante el ensayo o el canto, y pulsa `Esc`
para volver a la ventana normal.

Durante la reproduccion, las lineas visibles se resaltan por estado: las lineas
anteriores se atenúan, la linea actual se enfatiza y las siguientes quedan
faciles de distinguir.

## Fila de destino MIDI

Esta fila controla a dónde se envían los eventos MIDI:

- `MIDI destination`: elige un puerto de salida detectado.
- `Refresh MIDI Destinations`: vuelve a buscar puertos.
- `Connect MIDI Destination`: conecta el puerto elegido.
- `Disconnect MIDI Destinations`: desconecta todos los puertos conectados.

Recuerda que un reproductor MIDI envía eventos MIDI, no audio. Todavía hace
falta un sintetizador software o hardware conectado para escuchar sonido.

## Vista de teclado

La vista de teclado resalta las notas mientras se reproducen. Es una referencia
visual compacta de la actividad de notas.

## Barra de estado

La barra de estado informa lo que hace la aplicación, por ejemplo:

- `Loading ...`
- `Ready: ...`
- `Playing`
- `Paused`
- `Stopped`
- `End of sequence`
- errores MIDI o de carga de archivos

## Diálogo de preferencias

La pestaña `General` actual incluye:

- `Percussion channel`: el canal tratado como batería.
- `Solo volume reduction`: ajuste reservado para el próximo comportamiento de
  solo por canal.
- `Auto-play after loading a file`
- `Auto-advance to the next playlist item`
- `Send GM reset before playback`
- `Restore Defaults`: devuelve las opciones visibles a sus valores por defecto.

## Atajos útiles

- `Ctrl+O`: abrir
- `Space`: reproducir
- `P`: pausar
- `Esc`: detener
- `Ctrl+Left`: canción anterior
- `Ctrl+Right`: canción siguiente
- `Alt+Left`: compás anterior
- `Alt+Right`: compás siguiente
- `Alt+Up`: mover la fila seleccionada hacia arriba
- `Alt+Down`: mover la fila seleccionada hacia abajo
- `Ctrl+J`: saltar al compás elegido

## Límites actuales

Este port a PyQt6 ya es útil, pero todavía faltan partes de la aplicación
original. En especial, la edición de canales, letras, vistas avanzadas de
pianola y ajustes por canción todavía no están completos.
