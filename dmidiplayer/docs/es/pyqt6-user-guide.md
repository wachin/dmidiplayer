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
- `Play List...`: abre la ventana dedicada para administrar la lista.
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

## Menú Window

- `Main Window`: trae al frente la ventana principal del reproductor.
- `Play List`: muestra u oculta la ventana del administrador de listas.
- `Channels`: muestra u oculta la ventana de canales.
- `Piano Player`: muestra u oculta la ventana de Piano Player.
- `Lyrics`: muestra u oculta la ventana de letras.

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

`File -> Play List...` abre una ventana separada que refleja las mismas
canciones y la misma selección de la ventana principal. Desde allí puedes
añadir archivos, mover entradas hacia arriba o abajo, aleatorizar el orden,
eliminar entradas, vaciar la lista y abrir o guardar archivos `.lst`.

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
- `Label`: una etiqueta de texto editable en línea para ese canal
- `Mute`: silencia ese canal durante la reproducción
- `Solo`: mantiene ese canal a nivel completo mientras reduce los otros según
  la preferencia actual de reducción de solo
- `Level`: una zona compacta que combina actividad en vivo y deslizador de volumen
- `Program`: envía un cambio de programa para ese canal y reemplaza los cambios
  de programa posteriores que vengan desde el archivo. El selector ahora muestra
  nombres de instrumentos General MIDI en lugar de solo números
- `Lock`: ignora los cambios de programa posteriores que vengan desde el archivo
  mientras la reproducción está en marcha

Este sigue siendo un tramo temprano del port de la vista de canales, así que
todavía faltan comportamientos de canal más avanzados.

## Ventana Piano Player

La ventana `Piano Player` se abre desde el menú `View`.

Este primer tramo muestra solo las pistas que realmente contienen MIDI dentro
del archivo cargado. Las pistas se reparten en pestañas con un maximo de 8
pistas por pestaña:

- la primera pestaña se abre por defecto
- las pistas 1-8 aparecen en la primera pestaña
- las pistas 9-16 aparecen en la segunda pestaña cuando hace falta
- las pistas posteriores continúan en una tercera pestaña cuando hace falta

Cada fila visible muestra una etiqueta de pista, un resumen de canales y un
teclado. Durante la reproduccion, la actividad de notas se refleja en los
teclados de las pistas cuyos canales MIDI estan activos.

Cada fila tambien tiene una casilla `Show` para ocultar o mostrar el teclado
de esa pista sin perder el encabezado. La ventana incluye botones `Show All`
y `Hide All` para cambiar rapidamente la visibilidad de todas las pistas
mostradas.

La ventana tambien incluye un boton `Fullscreen`. Puedes usar `Esc` para salir
rapidamente del modo de pantalla completa.

En el tramo actual, cada teclado de pista se ajusta al rango de notas que esa
pista realmente usa, de modo que las partes graves y agudas no comparten todas
el mismo rango sobredimensionado.

Usa el selector `Range` para cambiar entre el rango exacto de notas de cada
pista y `Used octaves`, que amplia la vista a octavas completas para una
lectura mas comoda.

Usa el selector `Labels` para elegir como aparecen los nombres de las notas en
las teclas: `Never`, `Minimal`, `When active` o `Always`.

Usa el selector `Octaves` para elegir la convencion de numeracion de octavas
para esas etiquetas. Las opciones actuales son `Scientific` y `Yamaha`.

Usa el selector `Colors` para mantener la paleta azul actual o cambiar a
`By channel`, que da a cada teclado de pista una familia de color basada en su
canal.

El widget de teclado ahora incluye teclas negras dentro de ese rango reducido,
de modo que la vista de pista se parece mas a un teclado de piano real.

Las notas activas tambien se tiñen segun la velocidad, para que durante la
reproduccion sea un poco mas facil distinguir golpes suaves y fuertes.

Tambien puedes tocar notas directamente desde los teclados:
- haz clic sobre las teclas con el raton
- usa la fila inferior del teclado QWERTY (`Z`, `S`, `X`, `D`, etc.) cuando el teclado tenga el foco

## Ventana de letras

La ventana `Lyrics and Texts` se abre desde el menú `View`. Muestra eventos de texto MIDI
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

La fila superior también incluye:

- `Encoding`: controla como se decodifica en la ventana el texto MIDI
  incrustado. `Auto` usa la deteccion integrada, mientras que `UTF-8`,
  `Latin-1` y `CP1252` te permiten forzar manualmente la visualizacion.
- boton de menu: abre acciones para `Copy to Clipboard`, `Save to File...`,
  `Print...`, `Fullscreen` y `Font...`

`Save` guarda en un archivo el texto filtrado actual. Cuando esta seleccionado
`Auto`, el archivo se guarda como `UTF-8`; en los demas casos se usa la
codificacion elegida.

`Print` envia el texto filtrado actual a una impresora mediante el cuadro de
impresion estandar de Qt.

`Copy` lleva al portapapeles el texto filtrado actual. `Font` elige una fuente
mas comoda para el panel de letras. `Fullscreen` amplia la ventana de letras
durante el ensayo o el canto, y `Esc` vuelve a la ventana normal.

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
- `Automatically load and save song settings`
- `Force dark mode`
- `Use internal icon theme`
- `Qt Widgets style`
- `Send GM reset before playback`

Desde el menú `File`, el port actual también incluye `Song Settings -> Load`
y `Song Settings -> Save`. Esto guarda un archivo `.cfg` en
`$HOME/.dmidiplayer` usando el nombre del archivo MIDI cargado más `.cfg`.

La pestaña `Lyrics` actual incluye:

- `Font`
- `Font size`
- `Future text color`
- `Past text color`

La pestaña `Player Piano` actual incluye:

- `Highlight colors`: `Single color` o `By channel`
- `Single highlight color`
- `Use note velocity for highlight strength`
- `Note names`: `Never`, `Minimal`, `When active` o `Always`
- `Note-name font`
- `Note-name size`
- `Octave designation`: `Scientific` o `Yamaha`

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

## Barra de herramientas

El port actual permite:

- mostrar u ocultar la barra desde `View`
- mover la barra usando el comportamiento estándar de Qt
- abrir `Customize Toolbar` desde `View` para decidir qué acciones aparecen
- elegir estilos de botones desde `View -> Toolbar Buttons`:
  - `Icon Only`
  - `Text Only`
  - `Text Beside Icon`
  - `Text Under Icon`
  - `Follow Qt Style`

El diálogo `Customize Toolbar` actual ofrece:

- `Available Actions`
- `Selected Actions`
- `Add`
- `Remove`
- `Move Up`
- `Move Down`

## Límites actuales

Este port a PyQt6 ya es útil, pero todavía faltan partes de la aplicación
original. En especial, la edición de canales, letras, vistas avanzadas de
pianola y ajustes por canción todavía no están completos.
