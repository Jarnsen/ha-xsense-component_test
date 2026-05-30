# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Resumen
Esta integración para Home Assistant permite el uso de dispositivos Xsense dentro del sistema de hogar inteligente. Fue creada basándose en el código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) y se publicó con su permiso y en colaboración con él.

Hasta que haya una integración oficial para Home Assistant de Theo, se utilizará esta integración HACS, que se actualiza regularmente para agregar nuevas funciones y solucionar problemas existentes. Esta integración permite a los usuarios integrar sus dispositivos Xsense de manera sencilla en Home Assistant y utilizarlos para diferentes automatizaciones y supervisión.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Características
- Integración de varios dispositivos Xsense en Home Assistant.
- Soporte para automatizaciones basadas en los datos de los sensores Xsense.
- Soporte para estaciones base, detectores de humo, detectores de monóxido de carbono, alarmas de calor, detectores de agua, higrómetros, sensores de puerta, sensores de movimiento, luces, teclados, buzones, listeners, cámaras y otros dispositivos compatibles cuando estén disponibles en la cuenta X-Sense.
- Configuración fácil a través de HACS (Home Assistant Community Store).

## Requisitos
- Un servidor Home Assistant funcional (se recomienda la última versión).
- Una cuenta Xsense con dispositivos compatibles.
- HACS debe estar instalado en Home Assistant para permitir la instalación de la integración.

## Video explicativo
Para una guía detallada sobre la instalación y configuración de la integración, puedes ver el siguiente video:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparación
Antes de instalar la integración, es necesario realizar algunos preparativos:

- **Crear una segunda cuenta en la aplicación X-Sense (para uso con Home Assistant)**: Dado que no es posible iniciar sesión en la aplicación y en Home Assistant al mismo tiempo con la misma cuenta, recomendamos utilizar una cuenta separada para Home Assistant. Esto evitará que se cierre la sesión continuamente entre la aplicación y Home Assistant. La cuenta adicional permite una integración sin interrupciones y un uso continuo sin desconexiones repetidas.

- **Compartir los dispositivos compatibles desde la cuenta principal con la cuenta Home Assistant**: Utiliza la aplicación X-Sense para compartir **solo los dispositivos compatibles** con la cuenta recién creada. De esta manera, podrás usar la integración de forma sencilla en Home Assistant, mientras gestionas los dispositivos desde tu cuenta principal.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalación a través de HACS
1. **Abre HACS en Home Assistant**:
   HACS es una extensión importante para Home Assistant que te permite instalar integraciones personalizadas de manera sencilla.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Ve a los repositorios personalizados**:
   Navega en el tablero de HACS a los ajustes y añade el repositorio como una fuente personalizada.

3. **Añadir el repositorio**:
   Ingresa la URL del repositorio: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Descargar e instalar la integración**:
   Busca la integración en HACS, descárgala e instálala. Después de la instalación, la configuración se puede realizar a través de la interfaz de Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuración
Después de la instalación, se requiere una configuración básica para configurar correctamente la integración:
- **Nombre de usuario y contraseña**: Utiliza las credenciales de la cuenta X-Sense recién creada para establecer la conexión.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Visión general de los dispositivos**: Después de una configuración exitosa, los dispositivos compartidos estarán disponibles en Home Assistant y se podrán utilizar para automatizaciones.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Vista en Home Assistant
Después de una instalación y configuración exitosa, la integración será visible en Home Assistant. Los dispositivos estarán disponibles en el panel de control y se podrán utilizar para automatizaciones, notificaciones y otros casos de uso.


![Форум](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

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
- **Otros dispositivos conectados a estación**: Luz, teclado, buzón, listener, alarma de entrada, smart drop, control remoto y datos de radón se exponen cuando la API informa campos compatibles.

### Entidades y acciones disponibles
La integración crea entidades solo para campos presentes en la nube de X-Sense, MQTT shadow o APIs de cámara respaldadas por la app. Puede incluir sensores binarios, sensores de diagnóstico, interruptores, selectores, números y botones para funciones admitidas, como prueba, silencio, simulacro de incendio y despertar cámara.

Si un campo no existe o la app X-Sense marca una función como no compatible para ese dispositivo/cuenta, la entidad no se crea. La vinculación, eliminación, uso compartido, cuenta, pagos, firmware, formato de tarjeta SD y otras acciones de administración permanecen en la app X-Sense.

____________________________________________________________

## Ejemplos de automatizaciones
Con esta integración, se pueden crear varias automatizaciones. Aquí hay algunos ejemplos:

### Ejemplo 1: Alerta de temperatura
Cuando la temperatura de un termómetro Xsense es demasiado alta, se envía una notificación:

```yaml
automation:
  - alias: "Alerta de temperatura Xsense"
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

1. **Pruebas de dispositivos**: Si tienes un dispositivo Xsense que funcione con la integración, háznoslo saber para que podamos agregarlo a la lista de dispositivos compatibles.

2. **Comentarios sobre dispositivos no compatibles**: Si algún dispositivo no funciona, dános retroalimentación para que podamos proporcionar soporte o incluir el dispositivo en futuras versiones de la integración.

3. **Compartir dispositivos para pruebas**: La mejor forma de probar nuevos dispositivos es compartir el dispositivo a través de la aplicación X-Sense. Así podemos asegurarnos de que se admitan tantos dispositivos como sea posible.

4. **Apoyo a la comunidad**: Participa en las discusiones de nuestra comunidad. Ya sea que tengas sugerencias para mejorar o ayudes a otros usuarios con su configuración, toda ayuda es bienvenida.

Para discutir y obtener soporte, puedes unirte a nuestro servidor de Discord o al foro de Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Foro](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
