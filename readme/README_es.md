# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Resumen
Esta integración para Home Assistant permite el uso de dispositivos X-Sense dentro del sistema de hogar inteligente. Fue creada basándose en el código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) y se publicó con su permiso y en colaboración con él.

Esta integración HACS se mantiene activamente para quienes quieren una compatibilidad más amplia con dispositivos X-Sense en Home Assistant. Se actualiza regularmente con nuevas funciones, más cobertura de dispositivos y correcciones para problemas reportados.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Características
- Integración de varios dispositivos X-Sense en Home Assistant.
- Soporte para automatizaciones basadas en los datos de los sensores X-Sense.
- Soporte para estaciones base, detectores de humo, detectores de monóxido de carbono, alarmas de calor, detectores de agua, higrómetros, sensores de puerta, sensores de movimiento, luces, teclados, buzones, dispositivos de escucha, cámaras y otros dispositivos compatibles cuando estén disponibles en la cuenta X-Sense.
- Configuración fácil a través de HACS (Home Assistant Community Store).

## Requisitos
- Un servidor Home Assistant funcional (se recomienda la última versión).
- Una cuenta X-Sense con dispositivos compatibles.
- HACS debe estar instalado en Home Assistant para permitir la instalación de la integración.

## Video explicativo
Para una guía detallada sobre la instalación y configuración de la integración, puedes ver el siguiente video:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparación
Antes de instalar la integración, es necesario realizar algunos preparativos:

- **Crear una segunda cuenta en la aplicación X-Sense (para uso con Home Assistant)**: Dado que no es posible iniciar sesión en la aplicación y en Home Assistant al mismo tiempo con la misma cuenta, recomendamos utilizar una cuenta separada para Home Assistant. Esto evitará que se cierre la sesión continuamente entre la aplicación y Home Assistant. La cuenta adicional permite una integración sin interrupciones y un uso continuo sin desconexiones repetidas.

- **Compartir los dispositivos compatibles desde la cuenta principal con la cuenta Home Assistant**: Utiliza la aplicación X-Sense para compartir **solo los dispositivos compatibles** con la cuenta recién creada. De esta manera, podrás usar la integración de forma sencilla en Home Assistant, mientras gestionas los dispositivos desde tu cuenta principal.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalación a través de HACS
1. **Abre HACS en Home Assistant**:
  HACS es una extensión importante para Home Assistant que te permite instalar integraciones personalizadas de manera sencilla.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Ve a los repositorios personalizados**:
  Navega en el tablero de HACS a los ajustes y añade el repositorio como una fuente personalizada.

3. **Añadir el repositorio**:
  Ingresa la URL del repositorio: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Descargar e instalar la integración**:
  Busca la integración en HACS, descárgala e instálala. Después de la instalación, la configuración se puede realizar a través de la interfaz de Home Assistant.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuración
Después de la instalación, se requiere una configuración básica para configurar correctamente la integración:
- **Nombre de usuario y contraseña**: Utiliza las credenciales de la cuenta X-Sense recién creada para establecer la conexión.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Visión general de los dispositivos**: Después de una configuración exitosa, los dispositivos compartidos estarán disponibles en Home Assistant y se podrán utilizar para automatizaciones.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Vista en Home Assistant
Después de una instalación y configuración exitosa, la integración será visible en Home Assistant. Los dispositivos estarán disponibles en el panel de control y se podrán utilizar para automatizaciones, notificaciones y otros casos de uso.


![Foro](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Dispositivos compatibles
Esta integración admite varios dispositivos X-Sense. Las entidades disponibles dependen de los campos de datos que informe cada dispositivo y cuenta. Familias y modelos confirmados:
- **Estación base (SBS50)**: Concentrador central para dispositivos X-Sense.
- **Alarma de calor (XH02-M)**: Detecta temperaturas inusualmente altas.
- **Detector de monóxido de carbono (XC01-M; XC04-WX)**: Detecta concentraciones peligrosas de monóxido de carbono.
- **Detector de humo (XS01-M; XS01-WX; XS03-WX; XS0B-MR y modelos RF/iR relacionados)**: Detección temprana de humo.
- **Detector combinado de monóxido de carbono y humo (SC07-WX; XP0A-MR y modelos XP/SC relacionados)**: Detecta monóxido de carbono y humo.
- **Detector de fuga de agua (SWS51)**: Detecta agua en lugares no deseados.
- **Higrómetro-termómetro (STH51, STH0A, STH0B, STH0C)**: Supervisa temperatura y humedad.
- **Sensor de puerta (SDS0A)**: Expone el estado de la puerta cuando X-Sense lo proporciona.
- **Detector de movimiento (SMS0A)**: Expone el estado de alarma de movimiento cuando X-Sense lo proporciona.
- **Cámara (SSC0A, SSC0B)**: Expone entidades de cámara, miniaturas, URLs de transmisión en vivo, diagnósticos y ajustes respaldados por la app de Android cuando el dispositivo y la cuenta lo admiten.
- **Otros dispositivos conectados a estación**: Luz, teclado, buzón, dispositivo de escucha, alarma de entrada, entrega inteligente, control remoto y datos de radón se exponen cuando la API informa campos compatibles.

### Entidades y acciones disponibles
La integración crea entidades de Home Assistant solo para campos que existen en la nube de X-Sense, en los mensajes MQTT shadow o en las APIs de cámara alineadas con la app Android. Según el dispositivo, esto puede incluir:

- Sensores binarios de alarma, silencio, fin de vida, corte de CA, alarma de agua, alarma de temperatura, carga, movimiento, puerta, armado, advertencia, recordatorio, luz, PIR y estado del teclado.
- Sensores de batería, señal RF, señal Wi-Fi, firmware, temperatura, humedad, nivel de CO, pico de CO, volumen de alarma, volumen de voz, volumen de chirp, volumen de recordatorio, umbrales de advertencia, temporizadores de silencio, marcas de tiempo legibles, zona horaria y otros datos de diagnóstico.
- Interruptores para ajustes escribibles compatibles, como luz LED, habilitación de alarma, alarma continua, tono chirp, recordatorios, PIR, sunshine/white light, espera, sonido del teclado, detección de movimiento de cámara, grabación, visión nocturna, audio, cooldown, luz y controles de timbre.
- Selectores y números para ajustes de cámara compatibles, como idioma, resolución de grabación, códec, frecuencia anti-parpadeo, sensibilidad de movimiento, duración de vídeo, volumen, duración de alarma, cooldown, umbral nocturno y tecla de timbre.
- Botones de prueba, silencio, simulacro de incendio y despertar cámara para los modelos donde la app X-Sense expone esa acción.

Algunas entidades son de diagnóstico o configuración y se agrupan así en Home Assistant. Si un dispositivo no informa un campo concreto, o si la app X-Sense marca la función como no compatible para ese dispositivo/cuenta, no se crea la entidad correspondiente. La vinculación, eliminación, uso compartido, cuenta, pagos, actualización de firmware, formateo de tarjeta SD y otras acciones de administración permanecen en la app X-Sense.
____________________________________________________________

## Vista en vivo de cámara y notificaciones de IA
La forma más sencilla es usar el blueprint incluido. Impórtalo con el botón de abajo, elige la entidad de evento de cámara `Motion` o `AI Detection` para una cámara con suscripción, y ajusta la acción de notificación si hace falta.

[![Importar blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion y AI Detection son eventos puntuales, no estados de encendido/apagado. Para automatizaciones manuales usa el disparador `event.received` de Home Assistant con la entidad de cámara `Motion` o `AI Detection`; `event_type` solo es necesario para limitar una entidad AI Detection con suscripción a tipos como `person`, `pet`, `vehicle`, `package`, `other` o `ai_detection`.

Ejemplo de automatización:

```yaml
alias: "Notify when X-Sense detects a person"
triggers:
  - trigger: event.received
    target:
      entity_id: event.front_camera_ai_detection
    options:
      event_type:
        - person
actions:
  - action: notify.mobile_app_phone
    data:
      message: "X-Sense camera detected a person."
```

____________________________________________________________
## Ejemplos de automatizaciones
Con esta integración, se pueden crear varias automatizaciones. Aquí hay algunos ejemplos:

### Ejemplo 1: Alerta de temperatura
Cuando la temperatura de un termómetro X-Sense es demasiado alta, se envía una notificación:

```yaml
automation:
  - alias: "Alerta de temperatura X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "¡La temperatura supera los 30 grados!"
```

### Ejemplo 2: Alarma de detector de agua
Cuando el detector de agua detecta agua, se activa una alerta:

```yaml
automation:
  - alias: "Alarma de detector de agua"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "¡Se ha detectado una fuga de agua!"
```

____________________________________________________________

## Necesitamos tu ayuda
Siempre estamos buscando apoyo para desarrollar y mejorar esta integración. Aquí hay algunas formas en las que puedes ayudar:

1. **Pruebas de dispositivos**: Si tienes un dispositivo X-Sense que funcione con la integración, háznoslo saber para que podamos agregarlo a la lista de dispositivos compatibles.

2. **Comentarios sobre dispositivos no compatibles**: Si algún dispositivo no funciona, dános retroalimentación para que podamos proporcionar soporte o incluir el dispositivo en futuras versiones de la integración.

3. **Compartir dispositivos para pruebas**: La mejor forma de probar nuevos dispositivos es compartir el dispositivo a través de la aplicación X-Sense. Así podemos asegurarnos de que se admitan tantos dispositivos como sea posible.

4. **Apoyo a la comunidad**: Participa en las discusiones de nuestra comunidad. Ya sea que tengas sugerencias para mejorar o ayudes a otros usuarios con su configuración, toda ayuda es bienvenida.

Para discutir y obtener soporte, puedes unirte a nuestro servidor de Discord o al foro de Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Foro](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Referencia completa

### Cuenta e instalación
- Usa una cuenta X-Sense separada para Home Assistant.
- Comparte solo los dispositivos compatibles desde la cuenta principal de X-Sense.
- El emparejamiento, la eliminación, el uso compartido, el firmware, la cuenta, los pagos y la gestión de tarjetas SD permanecen en la app X-Sense.

### Actualizaciones y uso de la API
- Los cambios rápidos de estado llegan mediante mensajes MQTT shadow.
- Las solicitudes a la nube se usan para iniciar sesión, descubrir dispositivos, obtener datos de cámaras y recuperar estado.
- El sondeo periódico es solo un respaldo cuando falta una actualización en vivo.

### Entidades, cámaras y solución de problemas
- Las entidades se crean solo para campos que X-Sense realmente informa.
- Las entidades y controles de cámara se crean solo cuando la API alineada con la app Android indica soporte para esa cuenta y modelo.
- Si falta un valor, compáralo primero con la app X-Sense y luego adjunta diagnósticos y registros relevantes de Home Assistant.

## Lista de dispositivos y entidades

### Familias principales
- Estación SBS50, alarmas de humo XS, alarmas de CO XC, alarmas combinadas SC/XP, alarmas de calor XH, sensores de agua SWS, sensores STH de temperatura/humedad, sensores de puerta SDS, sensores de movimiento SMS, cámaras SSC y otras familias X-Sense informadas se gestionan cuando la API expone sus campos.

### Campos de estado
- Alarma, silencio, batería, señal RF/Wi-Fi, temperatura, humedad, CO, agua, movimiento, puerta, luz, recordatorios, advertencias y marcas de tiempo legibles aparecen solo cuando X-Sense los informa.

### Controles e informes
- Interruptores, selectores, números y botones se crean solo para ajustes y acciones escribibles que expone el dispositivo/cuenta.
- Un buen informe de error incluye el modelo exacto, la versión de la integración, diagnósticos, registros y si el valor cambia correctamente en la app X-Sense.
