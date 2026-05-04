# Roadmap de conversion a Qt/Python con PyQt6

Ultima actualizacion: 2026-05-02.

Este archivo debe servir como relevo para continuar la migracion en otra sesion.
Antes de tocar codigo, leer especialmente las secciones:

- `Estado actual al cierre`
- `Como verificar rapidamente`
- `Siguiente sesion: tareas concretas`
- `Limitaciones conocidas`

Este repositorio contiene dos proyectos C++/Qt que deben convivir durante la
conversion:

- `drumstick`: biblioteca MIDI para Qt. En Python queda como paquete
  `drumstick_py` dentro de la misma carpeta.
- `dmidiplayer`: reproductor que depende de Drumstick. En Python queda como
  paquete `dmidiplayer_py` dentro de la misma carpeta.

La conversion debe hacerse por capas. Primero se porta `drumstick_py`, luego se
conecta `dmidiplayer_py` contra esa API Python. El C++ original se conserva
como referencia hasta que cada modulo tenga paridad funcional y pruebas.

## Ecosistema Drumstick completo

![Drumstick ecosystem](drumstick-ecosystem.webp)

La imagen `drumstick-ecosystem.webp` resume la relacion entre las bibliotecas y
programas de la familia Drumstick. Los bloques verdes son bibliotecas o
utilidades Drumstick; los bloques rosados son aplicaciones externas o
dependencias externas. Para este port, el punto importante es que
`dmidiplayer_py` no debe verse como un programa aislado: depende de un
ecosistema Python equivalente a las bibliotecas C++ originales.

Bibliotecas C++ de referencia y equivalentes Python esperados:

- `Drumstick::ALSA`: capa Linux sobre ALSA Sequencer. En Python se esta
  reemplazando dentro de `drumstick_py.rt` usando `ctypes` sobre
  `libasound.so.2`.
- `Drumstick::File`: lectura/escritura de `.mid`, `.kar`, `.rmi` y `.wrk`. En
  Python se reemplaza con `drumstick_py.file`.
- `Drumstick::RT`: E/S MIDI realtime con backends ALSA, FluidSynth y otros. En
  Python debe quedar como API de salida/entrada reusable por `dmidiplayer_py`,
  `vpiano_py` y futuras utilidades.
- `Drumstick::Widgets`: widgets MIDI Qt, especialmente teclado/piano virtual.
  En Python se reemplaza con `drumstick_py.widgets`.

Ademas de `dmidiplayer_py`, el objetivo final incluye portar completamente a
PyQt6 las tres utilidades graficas de Drumstick mencionadas en
`drumstick/readme.md`:

- `drumgrid`: "Drumstick Drum Grid", editor/reproductor grafico de patrones de
  percusion. Depende principalmente de la capa ALSA.
- `guiplayer`: "Drumstick ALSA MIDI Player", reproductor grafico de archivos
  MIDI/WRK basado en Drumstick::ALSA y Drumstick::File. Es una referencia
  directa para el reproductor y para pruebas comparativas del port.
- `vpiano`: "Drumstick Virtual Piano", piano virtual grafico basado en
  Drumstick::RT y Drumstick::Widgets. Debe servir para validar entrada/salida
  realtime y widgets reutilizables.

Estas tres aplicaciones deben tener scripts ejecutables Python propios, UI
PyQt6 completa, pruebas basicas y documentacion de uso. La meta es que el
repositorio termine ofreciendo una familia coherente:

- `dmidiplayer-py`
- `drumstick-drumgrid-py`
- `drumstick-guiplayer-py`
- `drumstick-vpiano-py`

## Objetivo final de paridad funcional

La meta de este port es que `dmidiplayer_py`, usando `drumstick_py`, llegue a
ser un reproductor MIDI completo y agradable para uso real: abrir canciones,
sonar bien con hardware MIDI o sintetizadores software, mostrar informacion
musical util, ayudar a cantantes/instrumentistas a ensayar, y mantener una UI
practica para repertorios y karaoke.

Esta seccion resume las caracteristicas finales esperadas a partir de la
documentacion de dmidiplayer/Drumstick y sirve como lista de destino para toda
la migracion.

### Formatos y lectura de archivos

- Abrir `.mid`, `.midi` y `.kar` como Standard MIDI Files.
- Abrir `.wrk` de Cakewalk.
- Portar RIFF MIDI.
- Conservar eventos MIDI de canal, eventos meta, letras, textos, marcadores,
  cue points, cambios de tempo, compas, armadura y SysEx.
- Detectar o permitir elegir la codificacion de textos/letras.
- Reportar errores de archivo sin cerrar la aplicacion.
- Mantener metadatos suficientes para vistas de letras, canales, pianola,
  duracion, compases y busqueda de posicion.

### Salida MIDI y sintetizadores

- Enviar MIDI a puertos hardware.
- Enviar MIDI a sintetizadores software mediante backends Drumstick:
  - ALSA sequencer en Linux;
  - FluidSynth;
  - otros backends disponibles o razonables en la version Python.
- Listar destinos MIDI y conectar/desconectar desde la UI.
- Soportar salida dummy para pruebas automatizadas.
- Enviar reset SysEx GM/GS/XG antes de reproducir cuando este configurado.
- Ejecutar `all_notes_off` al detener, pausar, cambiar archivo, cerrar, buscar
  posicion o cambiar loop.
- Evitar que fallos de salida MIDI aborten el proceso; deben mostrarse al
  usuario como errores recuperables.

### Controles de reproduccion

- Reproducir, pausar/continuar y detener.
- Avanzar rapido y retroceder por compas.
- Saltar a un numero de compas concreto.
- Mover la posicion con un slider.
- Reproducir automaticamente al cargar archivo, si la preferencia esta activa.
- Mostrar estado actual en la barra de estado: reproduciendo, detenido, pausa,
  cargando, error, etc.
- Avanzar automaticamente al siguiente elemento de playlist al terminar, si la
  preferencia esta activa.

### Tempo, transpose y volumen

- Transponer la tonalidad de la cancion entre -12 y +12 semitonos.
- No transponer el canal de percusion configurado, por defecto canal GM 10.
- Controlar volumen global de 0% a 200%, enviando MIDI CC7 y respetando el
  limite 0-127 del protocolo.
- Restablecer volumen global.
- Escalar tempo entre 50% y 200%.
- Restablecer tempo.
- Mostrar tempo efectivo en BPM, empezando en 120 BPM si el archivo no define
  tempo.
- Actualizar el BPM visible mientras se reproduce un archivo con cambios de
  tempo.
- Aplicar pitch/tempo/volumen al scheduler y a los eventos enviados, no solo a
  la UI.

### Jump, loop y posicionamiento musical

- Calcular compases a partir del mapa de tempo y compas.
- Saltar a compas por numero, desde 1 hasta el ultimo compas de la cancion.
- Definir loop entre dos compases.
- Activar/desactivar loop durante la reproduccion.
- Mantener el slider de posicion sincronizado con ticks, tiempo real y compas.
- Permitir seek arbitrario sin dejar notas colgadas.

### Song settings por cancion

- Guardar y cargar ajustes por cancion en `$HOME/.dmidiplayer`.
- Usar el mismo nombre de la cancion y sufijo `.cfg`.
- Permitir carga/guardado automatico segun preferencia.
- Permitir carga/guardado manual desde menu.
- Guardar:
  - codificacion de texto/letras;
  - ruta del archivo MIDI;
  - transpose;
  - variacion de tempo;
  - variacion de volumen global.
- Guardar por canal:
  - variacion de volumen;
  - etiqueta editable;
  - patch/programa MIDI;
  - estado de solo;
  - estado de mute;
  - estado de lock.

### Vista de canales

- Mostrar hasta 16 filas, una por canal MIDI usado.
- Mostrar numero de canal y etiqueta editable.
- Mute por canal.
- Solo por canal, reduciendo volumen de los demas segun preferencia.
- Indicador de actividad/nivel por canal.
- Slider de volumen por canal.
- Lock de patch para impedir cambios de programa enviados por el archivo.
- Selector de patch/programa usando nombres General MIDI.
- Sincronizar cambios de canal con la reproduccion en tiempo real.

### Pianola / Piano Player

- Mostrar hasta 16 filas, una por canal usado.
- Cada fila debe tener numero/etiqueta de canal y teclado.
- Resaltar teclas segun notas MIDI reproducidas.
- Permitir colores personalizables por canal/estado.
- Permitir tinte por velocidad de nota.
- Mostrar nombres de notas segun preferencia:
  - nunca;
  - minimo;
  - al activar;
  - siempre.
- Soportar designacion de octava configurable.
- Permitir tocar notas manualmente con teclado de computadora y mouse cuando
  corresponda.
- Menu de ventana:
  - pantalla completa;
  - mostrar todos los canales;
  - ocultar todos los canales;
  - ajustar rango de teclas a las octavas realmente usadas;
  - mostrar/ocultar canales individuales.

### Letras y karaoke

- Mostrar textos meta del MIDI/KAR.
- Filtrar por pista:
  - todas las pistas;
  - pista individual.
- Seleccionar automaticamente la pista con mas datos de texto.
- Filtrar por tipo de texto:
  - lyrics;
  - text;
  - marker;
  - cue point;
  - otros tipos relevantes;
  - todos.
- Detectar codificacion automaticamente y permitir override manual.
- Resaltar letras pasadas/futuras con colores configurables.
- Copiar letras al portapapeles.
- Guardar letras a archivo con la codificacion seleccionada.
- Imprimir letras.
- Cambiar fuente de letras.
- Pantalla completa para vista de letras.

### Vista de ritmo

- Portar la vista Rhythm embebida en la ventana principal.
- Permitir ocultar/mostrar la vista desde el menu View.
- Sincronizarla con la reproduccion, tempo y compas.

### Playlists y repertorio

- Gestionar playlists desde `File -> Play List...`.
- Crear, modificar, ordenar, abrir y guardar playlists.
- Mostrar el nombre del archivo de playlist en el titulo de la ventana.
- Navegar manualmente con Next y Prev.
- Crear playlist temporal al abrir varios archivos por linea de comandos.
- Crear playlist temporal al arrastrar/soltar archivos en la ventana.
- Recordar la ultima playlist abierta o guardada.
- No guardar automaticamente playlists salvo accion explicita.
- Usar archivos de playlist de texto plano, un archivo por linea.
- Soportar rutas absolutas y rutas relativas al archivo `.lst`.
- Incluir una playlist inicial con ejemplos o permitir empezar con lista vacia.

### Apertura de archivos y recientes

- Abrir archivos desde menu/toolbar.
- Abrir archivos recientes, recordando hasta diez entradas.
- Abrir archivos pasados por linea de comandos.
- Integrarse con gestores de archivos usando "Open With...".
- Soportar drag and drop de archivos en la ventana principal.

### Preferencias

- Dialogo de preferencias con boton Restore Defaults.
- Pestaña General:
  - canal de percusion, por defecto 10;
  - porcentaje de reduccion de volumen para solo, por defecto 50%;
  - reproducir automaticamente al cargar;
  - avanzar automaticamente en playlist;
  - cargar/guardar song settings automaticamente;
  - sticky window borders, si se conserva para Windows;
  - forzar modo oscuro cuando aplique;
  - usar tema interno de iconos;
  - estilo Qt Widgets;
  - reset SysEx MIDI antes de reproducir.
- Pestaña Lyrics:
  - fuente;
  - color de texto futuro;
  - color de texto pasado.
- Pestaña Player Piano:
  - paletas de resaltado;
  - color unico de resaltado;
  - tinte por velocidad;
  - fuente de nombres de notas;
  - modo de mostrar nombres;
  - designacion de octava.
- Persistir preferencias con `QSettings` o formato compatible definido para el
  port.

### Personalizacion de toolbar

- Permitir mover toolbar.
- Permitir mostrar toolbar arriba, abajo o flotante segun soporte Qt.
- Dialogo de personalizacion con:
  - acciones disponibles;
  - acciones seleccionadas;
  - agregar/quitar;
  - mover arriba/abajo.
- Estilos de botones:
  - solo icono;
  - solo texto;
  - texto junto al icono;
  - texto bajo el icono;
  - seguir estilo Qt.

### UI principal y vistas

- Portar menu File, View, herramientas, status bar y dialogos principales.
- Vistas independientes:
  - Channels;
  - Lyrics;
  - Piano Player.
- Vistas embebidas mostrables/ocultables:
  - toolbar;
  - status bar;
  - Rhythm.
- Mantener iconos existentes y tema interno cuando sea necesario.
- Portar ayuda y ventana About.
- Portar traducciones, especialmente espanol e ingles.

### Documentacion, ayuda y distribucion

- Documentar instalacion y uso en README.
- Mantener instrucciones de prueba con MX Linux 23, kernel RT, QjackCtl,
  QSynth y `FluidR3.sf2`.
- Portar ayuda local desde markdown/html existentes.
- Preparar empaquetado local cuando el port sea estable:
  - scripts de entrada;
  - `.desktop`;
  - recursos;
  - iconos;
  - traducciones;
  - posible `pyproject.toml`.

### Criterio de exito del port

- dmidiplayer Python reproduce archivos reales con estabilidad y sonido MIDI
  real.
- La experiencia principal iguala o mejora la version C++ para abrir,
  reproducir, pausar, detener, navegar, modificar tempo/tono/volumen y usar
  playlists.
- Las vistas de canales, letras, pianola y ritmo estan sincronizadas con la
  reproduccion.
- Las preferencias y song settings sobreviven entre sesiones.
- Las pruebas automatizadas cubren parser, scheduler, salida dummy, conversion
  ALSA basica y flujos criticos de UI.
- La aplicacion nunca deja notas sonando al detener, buscar, cerrar o fallar la
  salida MIDI.
- `drumgrid`, `guiplayer` y `vpiano` existen tambien como aplicaciones PyQt6
  completas y reutilizan `drumstick_py` en vez de duplicar logica MIDI.

## Estado actual al cierre

Ya se creo una base Python ejecutable y se mantiene dentro de las carpetas de
cada proyecto, sin borrar ni sustituir el C++ original.

- `drumstick/drumstick_py/`
  - `file.py`: lector SMF inicial, sin dependencias externas, con mapa de
    tempo, duracion real y metadatos basicos.
  - `rt.py`: `BackendManager`, salida dummy, diagnostico con
    `python3-alsaaudio`, salida ALSA sequencer inicial mediante `libasound`,
    listado de destinos ALSA y conexion por puerto.
  - `widgets.py`: `PianoKeyboard` PyQt6 inicial.
- `dmidiplayer/dmidiplayer_py/`
  - `app.py`: ventana PyQt6 inicial con lista, controles, posicion, teclado y
    selector de destino MIDI ALSA; toolbar reducida a acciones principales y
    controles musicales movidos al panel principal; indicador de tiempo, BPM y
    compas actual.
  - `i18n.py`: carga de traducciones Qt `.qm` con ingles como idioma fuente.
  - `settings.py`: configuracion persistente mediante
    `QStandardPaths.AppConfigLocation` y `QSettings`.
  - `sequence.py`: modelo que carga SMF desde `drumstick_py`.
  - `player.py`: reproductor temporizado con `QTimer` y reloj real basado en
    mapa de tempo.
  - `__main__.py`: entrada `python3 -m dmidiplayer_py`.
- `dmidiplayer/dmidiplayer-py`: script lanzador local que configura
  `PYTHONPATH`.
- `tests/test_smf_parser.py`: prueba `unittest` minima que genera un SMF y
  valida note on/off, tempo y final de pista.
- `tests/test_alsa_event.py`: prueba minima para validar el armado de eventos
  SysEx ALSA con longitud variable.
- `tests/test_sequence_player.py`: prueba minima para validar seek por ticks en
  `SequencePlayer`.
- `tests/test_i18n.py`: prueba minima para validar fallback de idioma.
- `tests/test_settings.py`: prueba minima para validar persistencia de la
  ultima carpeta visitada.
- `tests/test_app_playlist.py`: pruebas minimas de navegacion de playlist e
  indicador de tiempo/BPM en la UI.

Estado funcional:

- `./dmidiplayer/dmidiplayer-py --help` funciona.
- La ventana PyQt6 arranca.
- Se pueden cargar archivos `.mid`, `.midi` y `.kar` siempre que sean SMF
  legibles por el parser inicial.
- El parser calcula mapa de tempo, compas, armadura, textos y duracion real.
- El reproductor temporizado emite eventos a la salida configurada usando los
  tiempos reales derivados del mapa de tempo.
- El slider de posicion permite seek basico por tick; al moverlo se detienen
  notas activas y se continua desde la nueva posicion si la reproduccion estaba
  activa.
- La UI muestra tiempo actual/total, BPM efectivo y compas actual/total; el BPM
  respeta cambios de tempo del archivo y el porcentaje de tempo seleccionado.
- La lista funciona como playlist temporal:
  - se pueden cargar varios archivos por linea de comandos o dialogo;
  - `Previous` y `Next` navegan la lista;
  - al terminar una cancion, avanza automaticamente al siguiente elemento.
- Hay controles iniciales de tono y tempo en el panel principal:
  - transpose entre -12 y +12 semitonos;
  - el canal de percusion GM 10 no se transpone;
  - tempo entre 50% y 200%, aplicado al reloj musical del scheduler.
- Hay control inicial de volumen global:
  - escala eventos MIDI CC7 entre 0% y 200%;
  - envia CC7 a los 16 canales cuando se cambia el control;
  - limita valores al rango MIDI 0-127.
- Hay loop basico por ticks MIDI:
  - controles `Loop`, `Start` y `End` en el panel principal;
  - al llegar al final del rango, vuelve al inicio y envia `all_notes_off`;
  - aun falta loop por compases musicales.
- La UI usa cadenas fuente en ingles y puede cargar traducciones Qt Linguist
  compiladas desde `dmidiplayer/dmidiplayer_py/translations`.
- La aplicacion guarda configuracion en `.config` en Linux y AppData/equivalente
  en Windows mediante Qt; recuerda la ultima carpeta visitada por el dialogo
  `Open MIDI`.
- La app intenta abrir ALSA sequencer primero.
- Si ALSA sequencer falla, la app cae a salida dummy y sigue abriendo la UI.
- `python3-alsaaudio` se usa solo como diagnostico de tarjetas/PCM. No sirve
  para ALSA sequencer MIDI porque el paquete no expone esa API.
- El envio MIDI ALSA real se implemento con `ctypes` sobre `libasound.so.2`.
- Los eventos SysEx ALSA se marcan como longitud variable; esto evita
  `Argumento invalido` al reproducir archivos como `examples/test.mid`.
- La UI lista destinos ALSA y puede conectar la salida directamente a QSynth,
  FluidSynth u otro puerto MIDI compatible. Si detecta QSynth/FluidSynth al
  arrancar, intenta autoconectarse.
- Se creo `README.md` en la raiz con notas de prueba en MX Linux 23, kernel RT,
  QjackCtl, QSynth y `FluidR3.sf2`.
- Se agrego `drumstick-ecosystem.webp` a la raiz y se documento en este Roadmap
  para dejar claro que el port tambien incluye las utilidades graficas
  `drumgrid`, `guiplayer` y `vpiano`.

Ejecucion actual:

```bash
./dmidiplayer/dmidiplayer-py archivo.mid
```

La salida MIDI real ALSA ya tiene una primera implementacion. Si ALSA sequencer
no esta disponible, la aplicacion cae automaticamente a salida dummy para validar
parser, UI y temporizacion.

Para que ALSA sequencer funcione debe existir `/dev/snd/seq`. En Debian suele
activarse con el modulo del kernel `snd-seq`; se puede comprobar con:

```bash
aconnect -lo
```

Si `aconnect -lo` falla con `open /dev/snd/seq failed`, cargar el modulo:

```bash
sudo modprobe snd-seq
```

Despues de lanzar `dmidiplayer-py`, se puede conectar el puerto ALSA desde la
propia UI con el selector `Destino MIDI`. `aconnect` sigue siendo util para
diagnostico manual.

## Como verificar rapidamente

Desde la raiz del repo:

```bash
./dmidiplayer/dmidiplayer-py --help
PYTHONPATH=drumstick:dmidiplayer python3 -m compileall drumstick/drumstick_py dmidiplayer/dmidiplayer_py
PYTHONPATH=drumstick:dmidiplayer python3 -m unittest tests.test_smf_parser tests.test_alsa_event tests.test_sequence_player tests.test_i18n tests.test_settings tests.test_app_playlist
QT_QPA_PLATFORM=offscreen timeout 2s ./dmidiplayer/dmidiplayer-py
```

Notas sobre estas pruebas:

- El comando offscreen debe terminar por `timeout` porque la app queda abierta;
  eso es normal.
- Si en el entorno no existe `/dev/snd/seq`, aparecera un mensaje de ALSA y la
  app usara dummy. Eso no es fallo de importacion.
- Despues de `compileall`, se pueden borrar los `__pycache__` generados.

Prueba manual con ALSA real:

```bash
aconnect -lo
./dmidiplayer/dmidiplayer-py archivo.mid
aconnect -lo
```

En otra terminal, conectar el puerto de `dmidiplayer PyQt6` a FluidSynth,
hardware MIDI, QSynth u otro sintetizador ALSA.

## Limitaciones conocidas

- El parser SMF inicial ya calcula tempo, duracion real y compases para SMF
  PPQ, pero aun necesita mas pruebas de borde y comparacion contra Drumstick
  C++.
- El scheduler de `dmidiplayer_py.player` ya usa tiempos reales, seek basico y
  loop por ticks; tambien aplica escala de tempo. Sigue dependiendo de `QTimer`
  y aun no implementa loop por compases ni compensacion avanzada de latencia.
- El transpose inicial ya afecta eventos de nota, pero aun falta integrarlo con
  song settings, canales bloqueados y UI final.
- Aun falta volumen por canal y restaurar volumen original por cancion/canal
  con song settings.
- La salida ALSA ya lista/conecta destinos desde la UI; falta mostrar
  conexiones activas y desconectar/reconectar destinos.
- La UI PyQt6 actual es una ventana minima, no una conversion completa de
  `guiplayer.ui`.
- No se han portado todavia canales, playlist completa, loop, letras, pianola
  completa, preferencias ni ayuda.
- La playlist temporal ya navega y auto-avanza, pero aun falta dialogo completo
  de playlist, guardar/abrir `.lst`, repeticion y aleatorio.
- RIFF MIDI y Cakewalk WRK aun no estan portados.
- `uchardet` aun no esta conectado al parser Python.
- Hay una prueba automatizada minima para SMF; falta ampliar cobertura.
- La traduccion espanola inicial existe como `.ts`, pero todavia no esta
  traducida ni compilada a `.qm`.

## Siguiente sesion: tareas concretas

Prioridad recomendada para continuar:

1. Ampliar pruebas de `drumstick_py.file`:
   - formato 1 multipista;
   - running status;
   - sysex;
   - cambios de tempo multiples;
   - compas, armadura, lyrics y markers.
2. Mejorar `drumstick_py.rt`:
   - mostrar conexiones activas y desconectar/reconectar destinos;
   - conectar por busqueda de nombre mas flexible desde preferencias;
   - exponer errores ALSA sin escribir demasiado en stderr;
   - verificar tamano/layout de `snd_seq_event_t` con una prueba pequena.
3. Empezar la conversion de UI real:
   - decidir si se usara `pyuic6` o `PyQt6.uic.loadUi`;
   - cargar `guiplayer.ui`;
   - conectar acciones basicas contra el `SequencePlayer` Python.
4. Traducir `dmidiplayer_py_es.ts` en Qt Linguist y compilar `.qm`.
5. Convertir los controles `Loop`, `Start` y `End` para trabajar por compases
   usando `tick_for_bar()`.
6. Agregar acciones de avanzar/retroceder por compas y salto a compas.

No repetir:

- No buscar bindings de `python3-alsaaudio` para MIDI sequencer: ya se reviso y
  solo expone PCM/mixer.
- No borrar C++ original; sigue siendo referencia.
- No mover los paquetes Python fuera de sus carpetas actuales.
- No introducir dependencias de `pip` sin necesidad fuerte.

## Dependencias Debian 12

Ya instaladas por el usuario:

- `python3-pyqt6`
- `uchardet`
- `pandoc`
- `python3-alsaaudio`

Paquetes recomendados para pruebas reales de sonido:

- `alsa-utils`: trae `aconnect`. En el entorno revisado ya existe
  `/usr/bin/aconnect`.
- `fluidsynth`: sintetizador software para escuchar salida MIDI.
- `fluid-soundfont-gm`: soundfont General MIDI comun en Debian.

Paquetes que el usuario indico que estan disponibles para instalar si hicieran
falta:

- `python3-audioread`
- `python3-pydub`
- `python-soundfile-doc`
- `python3-pyao`
- `python3-pymad`
- `python-mutagen-doc`
- `python3-soundfile`
- `python3-mediafile`
- `python3-ecasound`
- `python3-jack-client`
- `python3-aubio`

Evaluacion de esos paquetes para este proyecto:

- `python3-jack-client` podria ser util mas adelante si se porta soporte JACK.
- `python3-soundfile`, `python3-pydub` y `python3-audioread` solo serian utiles
  si se agrega renderizado/exportacion de audio, no para MIDI realtime.
- `python3-aubio` sirve para analisis de audio, no es prioridad.
- `python3-pymad`, `python3-mediafile`, `python-mutagen-doc`, `python3-pyao` y
  `python3-ecasound` no son necesarios para la ruta actual de dmidiplayer.

Dependencias recomendadas para fases posteriores:

- `python3-pyqt6.qtmultimedia`, si se decide usar Qt Multimedia para audio.
- `python3-alsaaudio`, ya instalado, queda como diagnostico PCM/mixer.
- `fluidsynth` y, si esta disponible en repositorios, bindings Python para
  FluidSynth; si no, usar `ctypes` sobre `libfluidsynth`.
- `python3-pytest` para pruebas unitarias.
- `python3-pytestqt`, si se desea automatizar widgets PyQt6.
- `pyqt6-dev-tools`, para `pylupdate6`.
- `qt6-tools-dev-tools`, `qttools5-dev-tools` y `qtchooser`, para Qt Linguist,
  `lupdate` y `lrelease` segun el entorno.
- `linguist-qt6`, disponible en MX Linux para editar traducciones `.ts`.

No introducir paquetes de `pip` salvo que sea inevitable. La prioridad es usar
paquetes de Debian 12.

## Fase 1: base Python y compatibilidad de estructura

Estado: iniciada y usable como esqueleto.

- Mantener el C++ original sin borrar archivos.
- Usar paquetes Python paralelos:
  - `drumstick/drumstick_py`
  - `dmidiplayer/dmidiplayer_py`
- Mantener nombres de clases cercanos a los originales cuando ayude:
  - `BackendManager`
  - `Sequence`
  - `SequencePlayer`
  - `PianoKeyboard`
- Crear scripts de ejecucion locales, sin instalacion global al principio.
- Confirmar que `python3 -m compileall` pasa en ambos paquetes.
- Confirmar que `./dmidiplayer/dmidiplayer-py --help` funciona.

## Fase 2: Drumstick File

Estado: iniciada. Hay lector SMF basico en `drumstick_py/file.py`.

Objetivo: reemplazar `library/file` en Python.

Tareas:

- Completar lector SMF:
  - tempo `0x51`
  - compas `0x58`
  - armadura `0x59`
  - textos, lyrics, markers y cue points
  - sysex completo
  - running status ya iniciado, ampliar pruebas de borde
  - duracion real en microsegundos considerando cambios de tempo
- Agregar escritor SMF si alguna utilidad lo requiere.
- Portar RIFF MIDI desde `rmid.cpp`.
- Portar Cakewalk WRK desde `qwrk.cpp`.
- Integrar deteccion de codificacion:
  - usar `uchardet` mediante comando externo o binding `ctypes`
  - mapear codificaciones a codecs Python
  - conservar comportamiento de letras karaoke
- Definir excepciones Python equivalentes a errores de carga C++.
- Crear fixtures MIDI pequenos para pruebas:
  - formato 0
  - formato 1 multipista
  - karaoke `.kar`
  - archivo con sysex
  - archivo con cambios de tempo

Criterios de salida:

- `drumstick_py.file.read_smf()` devuelve eventos ordenables por tick.
- La duracion y metadatos coinciden con dmidiplayer C++ en archivos de prueba.
- Los errores de archivo se reportan sin cerrar la aplicacion.

## Fase 3: Drumstick RT

Estado: iniciada. Hay salida dummy y primera salida ALSA sequencer en
`drumstick_py/rt.py`.

Objetivo: reemplazar `library/rt` y backends necesarios para Debian 12.

Prioridad Linux/Debian:

- ALSA sequencer output.
- ALSA sequencer input, si se necesita para utilidades como vpiano.
- FluidSynth output.
- Dummy output para pruebas.

Tareas:

- Disenar interfaz Python estable:
  - `MIDIOutput.open()`
  - `MIDIOutput.close()`
  - `MIDIOutput.send_event()`
  - `MIDIOutput.all_notes_off()`
  - `BackendManager.output_drivers()`
  - `BackendManager.connections()`
- Investigar si Debian 12 ofrece bindings ALSA suficientes.
- `python3-alsaaudio` cubre PCM/mixer, pero no ALSA sequencer MIDI. Usarlo para
  diagnostico y mantener la capa MIDI con `ctypes` sobre `libasound.so`.
- Portar conversion de eventos MIDI a mensajes raw.
- Implementar listado de puertos y conexion por nombre.
- Implementar reset GM/GS/XG si dmidiplayer lo requiere.
- Mantener backend dummy para pruebas automatizadas.

Criterios de salida:

- dmidiplayer Python puede enviar notas a un puerto ALSA visible.
- dmidiplayer Python puede usar FluidSynth si esta disponible.
- `all_notes_off` funciona al detener, pausar, cerrar y cambiar de archivo.

## Fase 4: Drumstick Widgets

Estado: iniciada solo con `PianoKeyboard` minimo.

Objetivo: reemplazar `library/widgets`.

Tareas:

- Completar `PianoKeyboard`:
  - teclas negras
  - rango configurable
  - colores por canal/estado
  - eventos de mouse/teclado si vpiano lo necesita
- Portar dialogos de configuracion:
  - FluidSynth
  - Network
  - Sonivox solo si se mantiene soporte
  - MacSynth no es prioridad en Debian
- Portar `SettingsFactory`.
- Reusar `.ui` existentes con `pyuic6` o cargar con `PyQt6.uic`, segun sea mas
  mantenible.

Criterios de salida:

- Los widgets se pueden importar sin depender de dmidiplayer.
- Los dialogos guardan/restauran configuracion con `QSettings`.

## Fase 5: dmidiplayer Core

Estado: iniciada con `Sequence` y `SequencePlayer` minimos.

Objetivo: portar la logica C++ de dmidiplayer.

Tareas por archivo C++ original:

- `events.*`
  - crear jerarquia/dataclasses Python para eventos MIDI, tempo, beat y texto.
- `sequence.*`
  - usar `drumstick_py.file`
  - calcular tiempos reales con mapa de tempo
  - conservar textos, lyrics, marcadores, compases y armadura
  - portar busqueda de codec y metadatos
- `seqplayer.*`
  - reemplazar temporizador simple por scheduler preciso
  - respetar tempo, pitch shift, volumen, mute, lock y programas
  - implementar loop por compases/ticks
  - emitir senales PyQt equivalentes a las C++
- `settings.*`
  - portar constantes de aplicacion
  - usar `QSettings`
  - modo portable `--portable` y `--file`
- `instrumentset.*`
  - cargar nombres de instrumentos y bancos
- `recentfileshelper.*`
  - guardar y poblar menu recientes

Criterios de salida:

- Abrir, reproducir, pausar, detener y cambiar posicion funcionan con MIDI real.
- Los canales respetan mute, volumen, programa y bloqueo.
- El comportamiento de loop coincide con C++.

## Fase 6: dmidiplayer UI PyQt6

Estado: iniciada con ventana minima escrita a mano. La UI completa original aun
no esta portada.

Objetivo: portar todas las ventanas y dialogos.

Archivos `.ui` a convertir o cargar:

- `guiplayer.ui`
- `connections.ui`
- `loopdialog.ui`
- `playerabout.ui`
- `playlist.ui`
- `prefsdialog.ui`
- `toolbareditdialog.ui`

Widgets/vistas C++ a portar:

- `channels.*`
- `connections.*`
- `framelesswindow.*`
- `helpwindow.*`
- `lyrics.*`
- `pianola.*`
- `playlist.*`
- `prefsdialog.*`
- `rhythmview.*`
- `toolbareditdialog.*`
- `vumeter.*`

Tareas:

- Convertir `.qrc` a recursos Python o resolver iconos desde rutas locales.
- Reusar iconos existentes en `dmidiplayer/icons`.
- Portar menus, toolbars y acciones.
- Implementar drag and drop de archivos.
- Implementar dialogo de conexiones usando `BackendManager`.
- Implementar preferencias completas.
- Implementar playlist con repeticion y aleatorio.
- Implementar lyrics y karaoke sincronizado.
- Implementar pianola y vista ritmica.
- Implementar ayuda usando los markdown convertidos con `pandoc` cuando aplique.

Criterios de salida:

- La UI Python permite los mismos flujos principales que la C++.
- No quedan botones principales conectados a placeholders.
- La aplicacion cierra sin dejar notas sonando.

## Fase 7: traducciones y documentacion

Tareas:

- Revisar `.ts` existentes.
- Decidir si se conservan traducciones Qt Linguist (`.qm`) con PyQt6.
- Portar carga de idioma dinamica.
- Regenerar ayuda/manpages con `pandoc`.
- Documentar ejecucion Python en `README.md`.
- Mantener notas de diferencias respecto al C++ mientras dure la migracion.

Criterios de salida:

- Espanol e ingles funcionan en la UI Python.
- La ayuda abre desde la aplicacion.

## Fase 8: utilidades de Drumstick

Objetivo: portar a Python/PyQt6 las utilidades incluidas en `drumstick/utils`,
manteniendo las CLI como herramientas de diagnostico y convirtiendo por
completo las utilidades graficas.

Prioridad grafica obligatoria:

- `utils/drumgrid`: debe convertirse en `drumstick-drumgrid-py`.
  - UI PyQt6 completa para crear y reproducir patrones de bateria.
  - Reusar `drumstick_py.rt` para salida ALSA/realtime.
  - Mantener comportamiento equivalente al ejecutable C++ "Drumstick Drum
    Grid".
- `utils/guiplayer`: debe convertirse en `drumstick-guiplayer-py`.
  - UI PyQt6 completa para reproducir SMF/WRK con salida ALSA.
  - Reusar `drumstick_py.file` y `drumstick_py.rt`.
  - Usarlo como aplicacion de referencia comparativa frente a dmidiplayer.
- `utils/vpiano`: debe convertirse en `drumstick-vpiano-py`.
  - UI PyQt6 completa de piano virtual.
  - Reusar `drumstick_py.widgets.PianoKeyboard` y ampliar el widget hasta tener
    interaccion por mouse/teclado.
  - Reusar `drumstick_py.rt` para entrada/salida MIDI realtime.

Estas tres utilidades no son opcionales: forman parte del objetivo final del
port del ecosistema Drumstick a Python.

Prioridad CLI y diagnostico:

- `utils/playsmf`
- `utils/dumpsmf`
- `utils/dumpmid`
- `utils/dumprmi`
- `utils/dumpwrk`
- `utils/sysinfo`
- `utils/metronome`

Cada utilidad debe tener su propio paquete o modulo dentro de
`drumstick_py/utils`.

Criterios de salida:

- Cada utilidad grafica abre desde arbol fuente con su script local.
- Cada utilidad grafica puede usar salida dummy para pruebas y ALSA real para
  pruebas manuales.
- `drumgrid`, `guiplayer` y `vpiano` tienen pruebas de importacion/arranque
  offscreen.
- El README explica como ejecutar cada utilidad Python.

## Fase 9: pruebas

Estado: pendiente. Solo se han hecho verificaciones manuales de importacion,
compilacion y arranque offscreen.

Pruebas minimas:

- Parser SMF:
  - cabecera invalida
  - evento meta
  - running status
  - sysex
  - tempo
  - formato 0 y 1
- Scheduler:
  - orden de eventos
  - tempo variable
  - loop
  - stop/all notes off
- UI:
  - abre ventana principal
  - carga archivo
  - cambia estado play/pause/stop
  - dialogo conexiones lista backends

Comandos esperados:

```bash
PYTHONPATH=drumstick:dmidiplayer python3 -m compileall drumstick/drumstick_py dmidiplayer/dmidiplayer_py
PYTHONPATH=drumstick:dmidiplayer python3 -m dmidiplayer_py --help
PYTHONPATH=drumstick:dmidiplayer python3 -m unittest tests.test_smf_parser tests.test_alsa_event tests.test_sequence_player tests.test_i18n tests.test_settings tests.test_app_playlist
```

## Fase 10: empaquetado local

Tareas:

- Crear `pyproject.toml` si se decide instalar como paquete.
- Crear scripts:
  - `dmidiplayer-py`
  - utilidades `drumstick-*`
- Evaluar instalacion en `/usr/local` solo al final.
- Crear archivo `.desktop` para version Python.
- Asegurar que recursos, iconos y traducciones se encuentren desde instalacion
  y desde arbol fuente.

## Orden recomendado de trabajo

1. Ampliar pruebas automatizadas para parser y scheduler.
2. Completar `drumstick_py.rt` con listado/conexion de puertos ALSA.
3. Portar `settings`, `sequence` y `events` con paridad C++.
4. Convertir/cargar `.ui` y conectar acciones reales.
5. Portar canales, lyrics, playlist, loop, pianola y ritmo.
6. Portar preferencias, conexiones, ayuda y traducciones.
7. Portar las utilidades graficas de Drumstick:
   - `drumstick-guiplayer-py`
   - `drumstick-vpiano-py`
   - `drumstick-drumgrid-py`
8. Portar utilidades CLI Drumstick restantes.
9. Preparar empaquetado e instalacion.

## Archivos Python creados hasta ahora

- `drumstick/drumstick_py/__init__.py`
- `drumstick/drumstick_py/file.py`
- `drumstick/drumstick_py/rt.py`
- `drumstick/drumstick_py/widgets.py`
- `dmidiplayer/dmidiplayer_py/__init__.py`
- `dmidiplayer/dmidiplayer_py/__main__.py`
- `dmidiplayer/dmidiplayer_py/app.py`
- `dmidiplayer/dmidiplayer_py/i18n.py`
- `dmidiplayer/dmidiplayer_py/player.py`
- `dmidiplayer/dmidiplayer_py/sequence.py`
- `dmidiplayer/dmidiplayer_py/settings.py`
- `dmidiplayer/dmidiplayer_py/translations/dmidiplayer_py_es.ts`
- `dmidiplayer/dmidiplayer-py`
- `tests/test_smf_parser.py`
- `tests/test_alsa_event.py`
- `tests/test_sequence_player.py`
- `tests/test_i18n.py`
- `tests/test_settings.py`
- `tests/test_app_playlist.py`

## Detalle tecnico del estado actual

`drumstick_py.file`:

- Lee cabecera `MThd`.
- Lee tracks `MTrk`.
- Soporta variable-length quantities.
- Soporta running status basico.
- Clasifica eventos de canal:
  - `note_off`
  - `note_on`
  - `key_pressure`
  - `control_change`
  - `program_change`
  - `channel_pressure`
  - `pitch_bend`
- Guarda meta eventos como `kind="meta"` con `meta_type`.
- Guarda sysex como `kind="sysex"`.
- Expone mapa de tempo con `TempoChange`.
- Expone metadatos basicos con `TimeSignature`, `KeySignature` y `TextEvent`.
- Calcula `length_microseconds`, `tick_to_microseconds()` y
  `microseconds_to_tick()`.
- Cachea eventos ordenados, duracion, tempo y metadatos calculados para evitar
  reordenar/recalcular repetidamente al abrir archivos MIDI mas grandes.
- Aun falta ampliar pruebas de borde y comparar duraciones/metadatos contra C++.

`drumstick_py.rt`:

- `DummyMidiOutput` guarda eventos en memoria.
- `AlsaSequencerOutput` abre `snd_seq_open("default", SND_SEQ_OPEN_OUTPUT)`.
- Crea un puerto `MIDI out` con capacidades de lectura/subscripcion para que
  otros clientes ALSA puedan suscribirse.
- Envia eventos directos con `snd_seq_event_output_direct`.
- Usa destino `SND_SEQ_ADDRESS_SUBSCRIBERS`.
- Marca SysEx con `SND_SEQ_EVENT_LENGTH_VARIABLE`.
- Lista puertos ALSA con `snd_seq_query_next_client` y
  `snd_seq_query_next_port`, filtrando destinos con `WRITE|SUBS_WRITE`.
- Conecta el puerto propio a destinos con `snd_seq_connect_to`.
- `all_notes_off()` envia controladores 123 y 120 en los 16 canales.
- Si falla ALSA, levanta `MidiOutputError`.

`dmidiplayer_py.player`:

- Carga `Sequence`.
- Avanza con `QTimer` preciso cada 2 ms y `QElapsedTimer`.
- Programa eventos segun los microsegundos calculados desde el mapa de tempo.
- Implementa `seek(tick)` y reposiciona el indice del siguiente evento.
- Implementa `set_tempo_percent()` entre 50% y 200%.
- Implementa `set_pitch_shift()` entre -12 y +12 semitonos.
- Implementa `set_volume_percent()` entre 0% y 200%.
- Implementa `set_loop_range()` y `set_loop_enabled()` para loop por ticks.
- Transpone eventos de nota excepto el canal de percusion cero-basado 9
  (canal GM 10).
- Escala eventos `control_change` CC7 y envia CC7 global a los 16 canales al
  cambiar volumen.
- Emite `positionChanged`, `eventPlayed`, `started`, `stopped`, `finished`.
- Aun falta loop y compensacion avanzada de latencia.

`dmidiplayer_py.app`:

- Crea `BackendManager`.
- Intenta `create_output("alsa")`.
- Si falla, muestra mensaje en status bar y usa dummy.
- Usa ingles como idioma fuente de la UI.
- Puede cargar traducciones con `--language CODIGO` o `--language system`.
- Crea `AppSettings` para recordar la ultima carpeta abierta.
- Tiene toolbar minima: abrir, reproducir, pausa, detener, anterior y siguiente.
- Tiene controles iniciales de tono, tempo y volumen con reset.
- Tiene controles iniciales de loop por ticks.
- Tiene selector de destinos MIDI ALSA con refrescar/conectar.
- Los controles de tono/tempo/volumen/loop/destino MIDI viven en filas
  compactas dentro del panel principal para no saturar la toolbar.
- Tiene lista de archivos, etiqueta de informacion, slider de posicion,
  teclado y etiqueta del ultimo evento.
- El slider de posicion llama a `SequencePlayer.seek()` al soltarlo.
- La lista lateral funciona como playlist temporal y se sincroniza con el
  archivo cargado.
- Al terminar una cancion, intenta cargar y reproducir el siguiente elemento.

`dmidiplayer_py.settings`:

- Usa `QStandardPaths.AppConfigLocation` para ubicar configuracion de forma
  portable: `.config` en Linux y AppData/equivalente en Windows.
- Guarda `settings.ini` con `QSettings`.
- Si la carpeta de configuracion no se puede crear/escribir, cae a un
  directorio temporal para no impedir que la aplicacion arranque en entornos
  restringidos.
- Persiste `files/last_folder`.
- Si la ruta guardada ya no existe, vuelve a una carpeta fallback.

## Notas tecnicas

- Evitar dependencias externas no disponibles en Debian 12.
- Preferir PyQt6 nativo sobre wrappers propios cuando Qt ya resuelve algo.
- Mantener el backend dummy siempre disponible para pruebas.
- No mezclar codigo C++ y Python en el mismo modulo; usar el C++ solo como
  referencia mientras se porta.
- Cualquier funcionalidad que todavia sea placeholder debe quedar marcada en
  este roadmap o con una excepcion clara en la UI.
