# ha-xsense-component_test

## Resumen
Esta integración para Home Assistant permite el uso de dispositivos Xsense dentro del sistema de hogar inteligente. La integración está basada en el código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) y se publicó con su permiso y en colaboración con él.

Hasta que haya una integración oficial de Home Assistant por parte de Theo, se utilizará esta integración de HACS, la cual se actualizará regularmente para agregar nuevas funciones y resolver problemas existentes. Esta integración permite a los usuarios integrar fácilmente sus dispositivos Xsense en Home Assistant y utilizarlos para diferentes automatizaciones y monitoreo.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Funciones
- Integración de varios dispositivos Xsense en Home Assistant.
- Soporte para automatizaciones basadas en datos de sensores de Xsense.
- Soporte para los siguientes tipos de dispositivos: estaciones base, detectores de humo, detectores de monóxido de carbono, detectores de calor, sensores de agua e higrómetros.
- Instalación sencilla a través de HACS (Home Assistant Community Store).

## Requisitos
- Un servidor Home Assistant en funcionamiento (se recomienda la versión más reciente).
- Una cuenta de Xsense con dispositivos compatibles.
- HACS debe estar instalado en Home Assistant para permitir la instalación de la integración.

## Video tutorial
Para una guía detallada sobre la instalación y configuración de la integración, puedes ver el siguiente video:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparación
Antes de instalar la integración, es necesario realizar algunas preparaciones:

- **Crea una segunda cuenta en la aplicación X-Sense (para uso con Home Assistant)**: Dado que no es posible estar conectado simultáneamente en la aplicación y en Home Assistant con la misma cuenta, recomendamos utilizar una cuenta separada para Home Assistant. Esto evitará que te desconectes constantemente entre la aplicación y Home Assistant. La cuenta adicional permitirá una integración y uso sin interrupciones debido a inicios y cierres de sesión repetidos.

- **Comparte los dispositivos compatibles desde la cuenta principal con la cuenta de Home Assistant**: Utiliza la aplicación X-Sense para compartir **solo los dispositivos compatibles** con la cuenta recién creada. De esta manera, puedes usar la integración en Home Assistant de manera sencilla, mientras gestionas los dispositivos a través de tu cuenta principal.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalación a través de HACS
1. **Abre HACS en Home Assistant**:
   HACS es una extensión importante para Home Assistant que te permite instalar integraciones personalizadas de manera sencilla.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Ve a los repositorios personalizados**:
   Navega al panel de HACS, dirígete a la configuración y añade el repositorio como una fuente personalizada.

3. **Añade el repositorio**:
   Introduce la URL del repositorio: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Descarga e instala la integración**:
   Busca la integración en HACS, descárgala e instálala. Tras la instalación, la configuración se puede realizar a través de la interfaz de Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuración
Después de la instalación, es necesario realizar una configuración básica para establecer correctamente la integración:
- **Nombre de usuario y contraseña**: Utiliza las credenciales de la cuenta de X-Sense recién creada para establecer la conexión.
- **Visión general de los dispositivos**: Una vez configurados con éxito, los dispositivos compartidos estarán disponibles en Home Assistant y podrán ser utilizados para automatizaciones.

## Visualización en Home Assistant
Después de una instalación y configuración exitosa, la integración será visible en Home Assistant. Los dispositivos estarán disponibles en el panel de control y podrán ser utilizados para automatizaciones, notificaciones y otras aplicaciones.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/50bbafde-c94b-445e-9aa3-9c33d5f151d6)

____________________________________________________________

## Dispositivos compatibles
Esta integración es compatible con varios dispositivos Xsense. A continuación se muestra una lista de los dispositivos confirmados y probados:
- **Estación base (SBS50)**: Centro para los dispositivos Xsense.
- **Sensor de calor (XH02-M)**: Detección de temperaturas inusualmente altas.
- **Detector de monóxido de carbono (XC01-M; XC04-WX)**: Detecta concentraciones peligrosas de monóxido de carbono.
- **Detector de humo (XS01-M, WX; XS03-WX; XS0B-MR)**: Detección temprana de humo.
- **Detector combinado de monóxido de carbono y humo (SC07-WX; XP0A-MR (parcialmente compatible))**: Detecta tanto monóxido de carbono como humo.
- **Sensor de agua (SWS51)**: Detecta la presencia de agua en lugares no deseados.
- **Higrómetro-termómetro (STH51)**: Monitoreo de temperatura y humedad.

Estos dispositivos, una vez integrados en Home Assistant, pueden ser utilizados para automatizaciones y alertas.

____________________________________________________________

## Ejemplos de automatizaciones
Con esta integración se pueden crear diferentes automatizaciones. A continuación se muestran algunos ejemplos:

### Ejemplo 1: Alerta de temperatura
Cuando la temperatura de un termómetro Xsense sea demasiado alta, se enviará una notificación:
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
        message: "¡La temperatura ha superado los 30 grados!"
```

### Ejemplo 2: Alarma del sensor de agua
Cuando el sensor de agua detecte agua, se activará una alerta:
```yaml
automation:
  - alias: "Alarma de sensor de agua"
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
Siempre estamos buscando apoyo para seguir desarrollando y mejorando esta integración. Aquí hay algunas formas en las que puedes ayudar:

1. **Prueba de dispositivos**: Si tienes un dispositivo Xsense que funcione con la integración, háznoslo saber para que podamos añadirlo a la lista de dispositivos compatibles.

2. **Soporte para dispositivos no compatibles**: Si un dispositivo no funciona, infórmanos para que podamos proporcionar soporte o integrarlo en futuras versiones.

3. **Compartir dispositivos**: La mejor manera de probar nuevos dispositivos es compartiendo el dispositivo a través de la aplicación X-Sense.

Para discusiones y soporte, puedes unirte a nuestro servidor de Discord o al foro de Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Foro](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

