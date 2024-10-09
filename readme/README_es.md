# ha-xsense-component_test

## Resumen
Esta integración para Home Assistant permite el uso de dispositivos Xsense dentro del sistema de hogar inteligente. Fue creada basándose en el código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) y se publicó con su permiso y en colaboración con él.

Hasta que haya una integración oficial para Home Assistant de Theo, se utilizará esta integración HACS, que se actualiza regularmente para agregar nuevas funciones y solucionar problemas existentes. Esta integración permite a los usuarios integrar sus dispositivos Xsense de manera sencilla en Home Assistant y utilizarlos para diferentes automatizaciones y supervisión.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Características
- Integración de varios dispositivos Xsense en Home Assistant.
- Soporte para automatizaciones basadas en los datos de los sensores Xsense.
- Soporte para los siguientes tipos de dispositivos: estaciones base, detectores de humo, detectores de monóxido de carbono, sensores de calor, detectores de agua e higrómetros.
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

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/50bbafde-c94b-445e-9aa3-9c33d5f151d6)

____________________________________________________________

## Dispositivos compatibles
Esta integración admite una variedad de dispositivos Xsense. A continuación se muestra una lista de los dispositivos confirmados y probados:
- **Estación base (SBS50)**: Concentrador central para los dispositivos Xsense.
- **Sensor de calor (XH02-M)**: Detección de temperaturas inusualmente altas.
- **Detector de monóxido de carbono (XC01-M; XC04-WX)**: Detecta concentraciones peligrosas de monóxido de carbono.
- **Detector de humo (XS01-M, WX; XS03-WX; XS0B-MR)**: Detección temprana de desarrollo de humo.
- **Detector combinado de monóxido de carbono y humo (SC07-WX; XP0A-MR (parcialmente compatible))**: Dispositivos combinados para la detección de monóxido de carbono y humo.
- **Detector de agua (SWS51)**: Detecta la presencia de agua en lugares no deseados.
- **Higrómetro-termómetro (STH51)**: Supervisión de la temperatura y la humedad.

Estos dispositivos se pueden usar para crear automatizaciones y alertas después de la integración en Home Assistant.

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
