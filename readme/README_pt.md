# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Visão Geral
Esta integração para Home Assistant permite o uso de dispositivos X-Sense dentro de um sistema de casa inteligente. Foi criada com base no código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) e foi publicada com a permissão dele e em colaboração com ele.

Esta integração HACS é mantida ativamente para utilizadores que desejam suporte mais amplo a dispositivos X-Sense no Home Assistant. Ela é atualizada regularmente com novas funcionalidades, maior cobertura de dispositivos e correções para problemas relatados.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funcionalidades
- Integração de vários dispositivos X-Sense no Home Assistant.
- Suporte para automações com base nos dados dos sensores X-Sense.
- Suporte para os seguintes tipos de dispositivos: estações-base, detectores de fumaça, detectores de monóxido de carbono, alarmes de calor, detectores de vazamento de água e higrômetros.
- Configuração simples através do HACS (Home Assistant Community Store).

## Requisitos
- Um servidor Home Assistant funcional (recomenda-se a versão mais recente).
- Uma conta X-Sense com dispositivos suportados.
- O HACS deve ser instalado no Home Assistant para permitir a instalação da integração.

## Vídeo Tutorial
Para obter um guia detalhado sobre a instalação e configuração da integração, você pode assistir ao seguinte vídeo:

[![Integração X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparação
Antes de instalar a integração, algumas preparações são necessárias:

- **Crie uma segunda conta no aplicativo X-Sense (para uso com o Home Assistant)**: Como não é possível estar conectado ao aplicativo e ao Home Assistant com a mesma conta ao mesmo tempo, recomendamos o uso de uma conta separada para o Home Assistant. Dessa forma, evita-se ser constantemente desconectado do aplicativo ou do Home Assistant. A conta adicional permite uma integração e uso contínuos e sem interrupções causadas por logins repetidos.

- **Compartilhe os dispositivos suportados da conta principal com a conta do Home Assistant**: Use o aplicativo X-Sense para compartilhar **apenas os dispositivos suportados** com a conta recém-criada. Dessa forma, será possível usar a integração de maneira simples no Home Assistant, enquanto a administração continua sendo feita pela conta principal.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalação através do HACS
1. **Abra o HACS no Home Assistant**:
  O HACS é uma extensão importante para o Home Assistant, que permite instalar integrações personalizadas de forma fácil.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Vá até os repositórios personalizados**:
  Navegue até as configurações no painel do HACS e adicione o repositório como uma fonte personalizada.

3. **Adicione o repositório**:
  Insira a URL do repositório: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Baixe e instale a integração**:
  Procure a integração no HACS, faça o download e instale-a. Após a instalação, a configuração pode ser feita através da interface do Home Assistant.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuração
Após a instalação, é necessária uma configuração básica para definir corretamente a integração:
- **Nome de usuário e senha**: Use as credenciais da conta X-Sense recém-criada para estabelecer a conexão.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Visão geral dos dispositivos**: Depois da configuração bem-sucedida, os dispositivos compartilhados estarão disponíveis no Home Assistant e poderão ser utilizados para automações.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Visualização no Home Assistant
Após uma instalação e configuração bem-sucedidas, a integração será visível no Home Assistant. Os dispositivos estarão disponíveis no painel e poderão ser usados para automações, notificações e outras aplicações.


![Fórum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Dispositivos Suportados
Esta integração suporta vários dispositivos X-Sense. As entidades disponíveis dependem dos campos relatados por cada dispositivo e conta. Famílias e modelos confirmados incluem:
- **Estação base (SBS50)**: Hub central para dispositivos X-Sense.
- **Alarme de calor (XH02-M)**: Detecta temperaturas anormalmente altas.
- **Detector de monóxido de carbono (XC01-M; XC04-WX)**: Detecta concentrações perigosas de CO.
- **Detector de fumaça (XS01-M; XS01-WX; XS03-WX; XS0B-MR e modelos RF/iR relacionados)**: Detecção precoce de fumaça.
- **Detector combinado de CO e fumaça (SC07-WX; XP0A-MR e modelos XP/SC relacionados)**: Detecta CO e fumaça.
- **Detector de vazamento de água (SWS51)**: Detecta água em locais indesejados.
- **Higrômetro-termômetro (STH51, STH0A, STH0B, STH0C)**: Monitora temperatura e umidade.
- **Sensor de porta (SDS0A)** e **sensor de movimento (SMS0A)**: Expostos quando a X-Sense fornece o estado.
- **Câmera (SSC0A, SSC0B)**: Expõe entidades de câmera, miniaturas, URLs de transmissão ao vivo, diagnósticos e configurações baseadas no app Android quando suportadas pelo dispositivo e pela conta.
- **Outros dispositivos conectados à estação**: Luz, teclado, caixa de correio, dispositivo de escuta, alarme de entrada, caixa de entrega inteligente, controle remoto e dados de radônio são expostos quando a API relata campos suportados.

### Entidades e ações disponíveis
A integração cria entidades do Home Assistant apenas para campos presentes na nuvem X-Sense, nos mensagens MQTT shadow ou nas APIs de câmera alinhadas ao app Android. Dependendo do dispositivo, isso pode incluir:

- Sensores binários de alarme, silenciar, fim de vida, falha de CA, alarme de água, alarme de temperatura, carregamento, movimento, porta, armado, aviso, lembrete, luz, PIR e estado do teclado.
- Sensores de bateria, sinal RF, sinal Wi-Fi, firmware, temperatura, umidade, nível de CO, pico de CO, volume de alarme, volume de voz, volume de chirp, volume de lembrete, limites de aviso, temporizadores de silêncio, horários legíveis, fuso horário e outros dados de diagnóstico.
- Switches para configurações graváveis suportadas, como luz LED, habilitação de alarme, alarme contínuo, tom chirp, lembretes, PIR, sunshine/white light, espera, som do teclado, detecção de movimento da câmera, gravação, visão noturna, áudio, cooldown, luz e controles de campainha.
- Seletores e números para configurações de câmera suportadas, como idioma, resolução de gravação, codec, anti-flicker, sensibilidade de movimento, duração de vídeo, volume, duração do alarme, cooldown, limite noturno e tecla da campainha.
- Botões de teste, silenciar, simulado de incêndio e despertar câmera para modelos em que o app X-Sense expõe a ação correspondente.

Algumas entidades são de diagnóstico ou configuração e aparecem agrupadas assim no Home Assistant. Se um dispositivo não relatar um campo específico, ou se o app X-Sense marcar a função como não suportada para esse dispositivo/conta, a entidade correspondente não será criada. Vincular, remover, compartilhar, conta, pagamentos, atualização de firmware, formatação de cartão SD e outras ações administrativas permanecem no app X-Sense.
____________________________________________________________

## Camera AI Notifications
Supported cameras create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

The easiest UI path is the included blueprint: `blueprints/automation/xsense/camera_ai_notification.yaml`. Import it, select the camera `AI Detection` event entity, leave Detection types selected to notify for every AI event, then keep or replace the default notification action.

AI detections are one-time events, not on/off states. Trigger on them with Home Assistant's `event.received` trigger and filter by `event_type`. Supported event types include `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

Example automation:

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

Use the `Last AI Detection` sensor and related last-detection timestamp sensors only for last-known history, dashboards, or conditions. These sensors can be unknown until the first notification arrives and are not the main notification trigger.
____________________________________________________________
## Exemplos de Automação
Com esta integração, é possível criar várias automações. Aqui estão alguns exemplos:

### Exemplo 1: Alerta de Temperatura
Quando a temperatura de um termômetro X-Sense está muito alta, uma notificação é enviada:

```yaml
automation:
  - alias: "Alerta de Temperatura X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "A temperatura ultrapassou 30 graus!"
```

### Exemplo 2: Alarme de Vazamento de Água
Quando o detector de vazamento de água detecta a presença de água, um alerta é acionado:

```yaml
automation:
  - alias: "Alarme de Vazamento de Água"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Vazamento de água detectado!"
```

____________________________________________________________

## Precisamos da Sua Ajuda
Estamos sempre em busca de suporte para continuar desenvolvendo e melhorando esta integração. Aqui estão algumas maneiras pelas quais você pode ajudar:

1. **Testar dispositivos**: Se você possui um dispositivo X-Sense que funciona com a integração, nos avise para que possamos adicioná-lo à lista de dispositivos suportados.

2. **Feedback sobre dispositivos não suportados**: Caso algum dispositivo não funcione, nos forneça feedback para que possamos oferecer suporte ou incluir o dispositivo em futuras versões da integração.

3. **Compartilhar dispositivos para teste**: A melhor maneira de testar novos dispositivos é compartilhá-los através do aplicativo X-Sense. Assim, podemos garantir que o maior número possível de dispositivos seja suportado.

4. **Suporte da comunidade**: Participe das discussões em nossa comunidade. Se você tiver sugestões de melhorias ou ajudar outros usuários com sua instalação, toda ajuda será bem-vinda!

Para discussões e suporte, você pode se juntar ao nosso servidor Discord ou visitar o fórum Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Fórum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Referência completa

### Conta e instalação
- Use uma conta X-Sense separada para o Home Assistant.
- Partilhe apenas dispositivos suportados a partir da conta principal X-Sense.
- Emparelhamento, remoção, partilha, firmware, conta, pagamentos e gestão do cartão SD permanecem na aplicação X-Sense.

### Atualizações e utilização da API
- Alterações rápidas de estado chegam por mensagens MQTT shadow.
- Pedidos à cloud são usados para início de sessão, descoberta de dispositivos, dados de câmaras e recuperação de estado.
- A consulta periódica é apenas uma alternativa quando falta uma atualização em tempo real.

### Entidades, câmaras e resolução de problemas
- As entidades são criadas apenas para campos que o X-Sense realmente comunica.
- Entidades e controlos de câmara são criados apenas quando a API alinhada com a app Android indica suporte para essa conta e modelo.
- Se faltar um valor, compare primeiro com a app X-Sense e depois anexe diagnósticos e registos relevantes do Home Assistant.

## Lista de dispositivos e entidades

### Famílias principais
- Estação SBS50, alarmes de fumo XS, alarmes CO XC, alarmes combinados SC/XP, alarmes de calor XH, sensores de água SWS, sensores temperatura/humidade STH, sensores de porta SDS, sensores de movimento SMS, câmaras SSC e outras famílias X-Sense comunicadas são tratadas quando a API expõe os seus campos.

### Campos de estado
- Alarme, silêncio, bateria, sinal RF/Wi-Fi, temperatura, humidade, CO, água, movimento, porta, luz, lembretes, avisos e carimbos temporais legíveis aparecem apenas quando o X-Sense os comunica.

### Controlos e relatórios
- Interruptores, seletores, números e botões são criados apenas para definições e ações graváveis expostas pelo dispositivo/conta.
- Um bom relatório de erro inclui modelo exato, versão da integração, diagnósticos, registos e se o valor muda corretamente na app X-Sense.
