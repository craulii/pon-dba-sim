# Guion — Presentación de Avances Nº 2
## TEL-341 Simulación de Redes — OmneTeam
**Duración estimada total: ~10–12 minutos**

---

## Slide 1 — Portada (30 seg)

> *Empieza cuando aparezca la portada en pantalla.*

"Buenos días / Buenas tardes. Somos OmneTeam: David, José y Matías. Hoy les presentamos el avance número dos de nuestro proyecto de simulación de redes. El proyecto se llama **Evaluación de Algoritmos DBA en Redes PON bajo Tráfico 5G Multi-Servicio**. En la presentación anterior les explicamos qué es OMNeT++ como herramienta; hoy les mostramos lo que hemos construido con ella."

---

## Slide 2 — Objetivo y Motivación (90 seg)

> *Señalar la columna izquierda y luego la tabla.*

"El proyecto responde a una pregunta concreta: **¿puede un algoritmo de scheduling inteligente proteger el tráfico de ultra-baja latencia de 5G cuando comparte el canal con tráfico de alto volumen?**"

"El contexto es una red PON —fibra óptica pasiva— que en 5G sirve como backhaul. Estas redes tienen un canal ascendente compartido: todas las ONUs deben *pedir permiso* para transmitir. El mecanismo que decide quién puede transmitir y cuándo se llama DBA, o Asignación Dinámica de Ancho de Banda."

"El problema es que el estándar existente, llamado IPACT, no distingue entre tipos de tráfico. En 5G tenemos tres clases radicalmente distintas:" *(señalar la tabla)* "eMBB genera mucho volumen, URLLC necesita llegar en menos de 10 milisegundos, y mMTC son millones de sensores con poco tráfico."

"La hipótesis que vamos a verificar es: bajo carga real, IPACT falla en proteger URLLC, y un algoritmo QoS-aware sí puede."

---

## Slide 3 — Arquitectura (90 seg)

> *Señalar el diagrama de izquierda a derecha.*

"La red que simulamos es esta: una OLT en la central, un splitter pasivo, y 16 ONUs en los extremos. Los retardos de propagación son los reales: 100 microsegundos para la fibra alimentadora y 10 para la distribución."

"Lo importante arquitectónicamente es que el canal upstream es **TDM**: solo transmite una ONU a la vez, y el DBA es quien asigna los slots. Todo esto está implementado desde cero en OMNeT++, sin usar el framework INET —lo que significa que modelamos cada mensaje, cada grant, cada reporte manualmente."

"Los parámetros clave los ven abajo: 16 ONUs compartiendo 1 Gbps, ciclo de polling de 2 ms, y un deadline de 10 ms para los paquetes URLLC —que es el presupuesto de latencia asignado a la red de acceso en arquitecturas 5G."

---

## Slide 4 — Módulos Implementados (60 seg)

> *Hacer un barrido rápido de las cajas.*

"Estos son los módulos que implementamos. Cada uno tiene su archivo `.h` y `.cc` en C++17. Los dos más importantes son la OLT —que contiene el motor DBA— y la ONU —que tiene las tres colas y mide la latencia de cada paquete al momento de transmitirlo."

"Los algoritmos DBA están en clases separadas: `IPACT.cc` y `QoSDBA.cc`, y son intercambiables por parámetro de configuración sin recompilar."

"El módulo `PONMessages.msg` define los tres tipos de mensajes que viajan en la red: DataPacket, ReportMessage y GrantMessage. OMNeT++ los compila automáticamente a clases C++."

---

## Slide 5 — Algoritmos DBA (90 seg)

> *Señalar izquierda para IPACT, derecha para QoS-DBA.*

"IPACT, a la izquierda: el algoritmo estándar. Funciona así: la OLT pregunta cuántos bytes tiene cada ONU en total, y le asigna un grant proporcional a ese total, con un máximo. El problema es que no distingue entre eMBB y URLLC. Cuando el tráfico eMBB genera una ráfaga —que es frecuente con la distribución Pareto que usamos— ocupa casi todo el grant, y URLLC queda con muy poco. Los paquetes URLLC se acumulan, superan su deadline, y se descartan."

"QoS-DBA, a la derecha: nuestro algoritmo con conciencia de QoS. Funciona en dos pasos: primero, se asigna **todo** lo que necesita URLLC, sin restricciones. Con lo que queda, se aplica Weighted Fair Queuing entre eMBB (70%) y mMTC (30%). El resultado es que URLLC siempre recibe su asignación, sin importar el volumen de eMBB."

---

## Slide 6 — Estado de Implementación (60 seg)

> *Señalar columna verde (hecho) y columna naranja (pendiente).*

"En verde, lo que ya está funcionando: los módulos compilan, las simulaciones se ejecutan correctamente, tenemos 24 corridas completadas y los scripts de análisis generan los gráficos automáticamente."

"En naranja, lo que queda pendiente: el más crítico es aumentar las repeticiones de 3 a 10 para tener intervalos de confianza del 95% estadísticamente válidos. También falta ejecutar los escenarios con 32 ONUs y preparar el análisis estadístico formal."

---

## Slide 7 — Configuración de Experimentos (45 seg)

> *Señalar la tabla.*

"La tabla muestra los cuatro escenarios planificados. Por ahora ejecutamos los dos de 16 ONUs —con IPACT y QoS-DBA— variando la carga eMBB entre 50 y 200 Mbps, con 3 repeticiones cada uno. Los de 32 ONUs están pendientes."

"El diseño usa semillas distintas por repetición para garantizar reproducibilidad, y un período de calentamiento de 1 segundo que se excluye del análisis."

---

## Slide 8 — Resultados (tabla) (90 seg)

> *Señalar los valores de la tabla, comparar filas.*

"Aquí están los resultados preliminares. La columna más importante es **lossRate URLLC**."

"Con IPACT, la tasa de pérdida de paquetes URLLC es **75 a 87%**, dependiendo de la carga. Esto significa que en el mejor caso, 3 de cada 4 paquetes de tráfico crítico se pierden. Incluso a 50 Mbps de carga eMBB, que es relativamente baja, el 75% de URLLC se descarta."

"Con QoS-DBA, la tasa de pérdida URLLC es **0% en todos los niveles de carga**. El algoritmo cumple su objetivo."

"El costo es que eMBB tiene ligeramente más pérdida con QoS-DBA que con IPACT —diferencia de unos 5 puntos porcentuales—, que es el intercambio esperado: cedemos un poco de eMBB para proteger completamente URLLC."

---

## Slide 9 — Dashboard (60 seg)

> *Señalar cada subplot.*

"Este es el dashboard con los cuatro gráficos principales. Arriba a la izquierda, la latencia promedio por clase: QoS-DBA reduce la latencia de URLLC drásticamente. Arriba a la derecha, el P99 URLLC versus carga —nótese que IPACT supera el deadline en casi todos los escenarios. Abajo a la izquierda, el throughput agregado. Abajo a la derecha, la tasa de pérdida por clase, que resume el resultado central del proyecto."

"Este es el gráfico que irá en la lámina de resultados del informe final."

---

## Slide 10 — Próximos Pasos (60 seg)

> *Señalar cada bloque numerado.*

"Para cerrar el proyecto tenemos cuatro tareas principales:"

"Primero: aumentar a 10 repeticiones —es relativamente rápido, estimamos unos 15 minutos de cómputo adicional."

"Segundo: ejecutar los escenarios de 32 ONUs, para ver cómo escala el comportamiento con más usuarios compartiendo el canal."

"Tercero: el análisis estadístico completo —intervalos de confianza, tests de hipótesis— para que las conclusiones sean formalmente sólidas."

"Cuarto: la demo GUI en Qtenv —que muestra la animación de la red con mensajes de colores moviéndose— y el informe final en formato IEEE."

"Hasta aquí el avance. ¿Preguntas?"

---

## Notas generales

- **Tiempo total estimado**: ~10 min de exposición + 2–3 min de preguntas
- **Demo opcional**: si la profesora lo pide, mostrar brevemente la GUI de OMNeT++ con Qtenv
- **Si preguntan por los bugs corregidos**: "Durante el desarrollo encontramos inconsistencias en los parámetros del modelo —el deadline URLLC y el parámetro del generador Pareto— que corregimos y que explicamos en detalle en el informe"
- **Si preguntan por la diferencia eMBB**: "QoS-DBA penaliza levemente a eMBB porque le cede prioridad absoluta a URLLC; es el trade-off esperado y documentado en la literatura"
