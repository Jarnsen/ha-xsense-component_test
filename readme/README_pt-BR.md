# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Visão geral
Esta integração para Home Assistant permite usar dispositivos X-Sense em um sistema de casa inteligente. Ela foi criada com base no código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) e é publicada com a permissão e colaboração dele.

Até que uma integração oficial do Home Assistant de Theo esteja disponível, esta integração HACS será usada e atualizada regularmente para adicionar novas funções e corrigir problemas existentes. Ela permite integrar dispositivos X-Sense ao Home Assistant e usá-los em automações e monitoramento.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Recursos
- Integração de vários dispositivos X-Sense ao Home Assistant.
- Suporte a automações com base nos dados dos sensores X-Sense.
- Suporte aos seguintes tipos de dispositivo: estações base, detectores de fumaça, detectores de monóxido de carbono, alarmes de calor, detectores de vazamento de água, higrômetros, sensores de porta, sensores de movimento, luzes, teclados, sensores de caixa de correio, dispositivos ouvintes e câmeras compatíveis quando disponíveis na conta X-Sense.
- Atualizações em tempo real por shadows MQTT da X-Sense, com consulta periódica à nuvem como fallback.
- Instalação simples pelo HACS (Home Assistant Community Store).

## Requisitos
- Um servidor Home Assistant funcionando (versão mais recente recomendada).
- Uma conta X-Sense com dispositivos compatíveis.
- O HACS deve estar instalado no Home Assistant para permitir a instalação da integração.

## Vídeo tutorial
Para um guia detalhado de instalação e configuração da integração, assista ao vídeo abaixo:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparação
Antes de instalar a integração, alguns preparativos são necessários:

- **Crie uma segunda conta no app X-Sense (para usar com o Home Assistant)**: Como não é possível ficar conectado ao app e ao Home Assistant com a mesma conta ao mesmo tempo, recomendamos usar uma conta separada para o Home Assistant. Isso evita desconexões constantes no app ou no Home Assistant.

- **Compartilhe os dispositivos compatíveis da conta principal com a conta do Home Assistant**: Use o app X-Sense para compartilhar **somente os dispositivos compatíveis** com a conta recém-criada. Assim, a integração pode ser usada no Home Assistant enquanto a administração continua na conta principal.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalação via HACS
1. **Abra o HACS no Home Assistant**:
   O HACS é uma extensão importante do Home Assistant que permite instalar integrações personalizadas com facilidade.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Acesse os repositórios personalizados**:
   Navegue até as configurações no painel do HACS e adicione o repositório como uma fonte personalizada.

3. **Adicione o repositório**:
   Informe a URL do repositório: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Baixe e instale a integração**:
   Encontre a integração no HACS, baixe e instale. Depois da instalação, a configuração pode ser feita pela interface do Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuração
- **Usuário e senha**: Use as credenciais da conta X-Sense recém-criada para estabelecer a conexão.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Visão geral dos dispositivos**: Depois da configuração bem-sucedida, os dispositivos compartilhados ficarão disponíveis no Home Assistant e poderão ser usados em automações.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Visualização no Home Assistant
Depois da instalação e configuração bem-sucedidas, a integração ficará visível no Home Assistant. Os dispositivos estarão disponíveis no painel e poderão ser usados em automações, notificações e outros usos.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Dispositivos compatíveis
Esta integração oferece suporte a vários dispositivos X-Sense. As entidades compatíveis dependem dos campos de dados informados por cada dispositivo e conta. Estes são os grupos de dispositivos e modelos confirmados atualmente:
- **Estação base (SBS50)**: Hub central para dispositivos X-Sense.
- **Alarme de calor (XH02-M)**: Detecta temperaturas anormalmente altas.
- **Detector de monóxido de carbono (XC01-M; XC04-WX)**: Detecta concentrações perigosas de monóxido de carbono.
- **Detector de fumaça (XS01-M; XS01-WX; XS03-WX; XS0B-MR e modelos RF/iR relacionados)**: Detecção antecipada de fumaça.
- **Detector combinado de monóxido de carbono e fumaça (SC07-WX; XP0A-MR e modelos XP/SC relacionados)**: Dispositivos combinados para detectar monóxido de carbono e fumaça.
- **Detector de vazamento de água (SWS51)**: Detecta água em áreas indesejadas.
- **Higrômetro-termômetro (STH51, STH0A, STH0B, STH0C)**: Monitora temperatura e umidade.
- **Sensor de porta (SDS0A)**: Expõe o estado da porta quando fornecido pela conta X-Sense.
- **Detector de movimento (SMS0A)**: Expõe o estado de alarme de movimento quando fornecido pela conta X-Sense.
- **Câmera (SSC0A, SSC0B)**: Expõe entidades de câmera, miniaturas, URLs de transmissão ao vivo, diagnósticos de status e configurações alinhadas ao app Android quando suportadas pelo dispositivo e pela conta.
- **Outros dispositivos conectados à estação**: Dados de luzes, teclados, caixas de correio, ouvintes, alarmes de garagem, smart drop, controles remotos e dispositivos de radônio são expostos quando a API X-Sense informa campos compatíveis.

Esses dispositivos podem ser usados para criar automações e alertas depois de integrados ao Home Assistant.

### Entidades e ações disponíveis
A integração cria entidades do Home Assistant somente para campos presentes na nuvem X-Sense, nos payloads de shadow MQTT ou nas APIs de câmera alinhadas ao app Android. Dependendo do dispositivo, isso pode incluir:

- Sensores binários de alarme, silenciamento, fim de vida, falha de energia AC, alarme de água, alarme de temperatura, carregamento, movimento, porta, armado, aviso, lembrete, luz, PIR e status de teclado.
- Sensores de bateria, sinal RF, sinal Wi-Fi, firmware, temperatura, umidade, nível de CO, pico de CO, volume de alarme, volume de voz, volume de chirp, volume de lembrete, limites de aviso, temporizadores de silenciamento, horários legíveis, fuso horário, número de série, endereço MAC e outros diagnósticos.
- Switches para configurações graváveis suportadas pela X-Sense, como luz LED, ativação de alarme, alarme contínuo, tom de chirp, lembretes, PIR, sunshine, await, som do teclado, detecção de movimento da câmera, gravação, visão noturna, áudio, cooldown, luz e controles de campainha.
- Seleções e números para configurações de câmera suportadas, como idioma, resolução de gravação, codec, taxa anti-flicker, sensibilidade de movimento, duração do vídeo, volume, duração do alarme, cooldown, limite noturno e tecla da campainha.
- Botões de teste, silenciamento, simulação de incêndio e despertar câmera para modelos em que o app X-Sense expõe a ação correspondente.

Algumas entidades são de diagnóstico ou configuração e são agrupadas dessa forma no Home Assistant. Se um dispositivo não informar um campo específico, ou se o app X-Sense marcar o recurso como não suportado para aquele dispositivo ou conta, a entidade correspondente não será criada. Vinculação, remoção, compartilhamento, conta, pagamento, atualização de firmware, formatação de cartão SD e outras ações de gerenciamento permanecem no app X-Sense.

____________________________________________________________

## Exemplos de automação
Com esta integração, é possível criar várias automações. Veja alguns exemplos:

### Exemplo 1: Alerta de temperatura
Quando a temperatura de um termômetro X-Sense estiver alta demais, uma notificação será enviada:

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
        message: "A temperatura passou de 30 graus!"
```

### Exemplo 2: Alarme de vazamento de água
Quando o detector de vazamento de água detectar água, um alerta será acionado:

```yaml
automation:
  - alias: "Alarme de vazamento de água"
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

## Precisamos da sua ajuda
Estamos sempre buscando apoio para continuar desenvolvendo e melhorando esta integração. Veja como você pode ajudar:

1. **Testar dispositivos**: Se você tem um dispositivo X-Sense que funciona com a integração, avise-nos para que possamos adicioná-lo à lista de dispositivos compatíveis.

2. **Feedback sobre dispositivos não compatíveis**: Se um dispositivo não funcionar, envie feedback para que possamos oferecer suporte ou incluí-lo em futuras versões da integração.

3. **Compartilhar dispositivos para testes**: A melhor forma de testar novos dispositivos é compartilhá-los pelo app X-Sense. Assim, podemos garantir suporte para o maior número possível de dispositivos.

4. **Suporte da comunidade**: Participe das discussões da comunidade. Sugestões de melhoria e ajuda a outros usuários são sempre bem-vindas.

Para discussões e suporte, entre no nosso servidor Discord ou visite o fórum do Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
