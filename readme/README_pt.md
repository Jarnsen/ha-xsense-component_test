# ha-xsense-component_test

## Visão Geral
Esta integração para Home Assistant permite o uso de dispositivos Xsense dentro de um sistema de casa inteligente. Foi criada com base no código original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) e foi publicada com a permissão dele e em colaboração com ele.

Até que uma integração oficial para Home Assistant esteja disponível por Theo, será utilizada esta integração HACS, que será regularmente atualizada para adicionar novas funcionalidades e resolver problemas existentes. Esta integração permite aos usuários integrar facilmente seus dispositivos Xsense ao Home Assistant e utilizá-los para diversas automações e monitoramento.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Funcionalidades
- Integração de vários dispositivos Xsense no Home Assistant.
- Suporte para automações com base nos dados dos sensores Xsense.
- Suporte para os seguintes tipos de dispositivos: estações-base, detectores de fumaça, detectores de monóxido de carbono, alarmes de calor, detectores de vazamento de água e higrômetros.
- Configuração simples através do HACS (Home Assistant Community Store).

## Requisitos
- Um servidor Home Assistant funcional (recomenda-se a versão mais recente).
- Uma conta Xsense com dispositivos suportados.
- O HACS deve ser instalado no Home Assistant para permitir a instalação da integração.

## Vídeo Tutorial
Para obter um guia detalhado sobre a instalação e configuração da integração, você pode assistir ao seguinte vídeo:

[![Integração X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparação
Antes de instalar a integração, algumas preparações são necessárias:

- **Crie uma segunda conta no aplicativo X-Sense (para uso com o Home Assistant)**: Como não é possível estar conectado ao aplicativo e ao Home Assistant com a mesma conta ao mesmo tempo, recomendamos o uso de uma conta separada para o Home Assistant. Dessa forma, evita-se ser constantemente desconectado do aplicativo ou do Home Assistant. A conta adicional permite uma integração e uso contínuos e sem interrupções causadas por logins repetidos.

- **Compartilhe os dispositivos suportados da conta principal com a conta do Home Assistant**: Use o aplicativo X-Sense para compartilhar **apenas os dispositivos suportados** com a conta recém-criada. Dessa forma, será possível usar a integração de maneira simples no Home Assistant, enquanto a administração continua sendo feita pela conta principal.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalação através do HACS
1. **Abra o HACS no Home Assistant**:
   O HACS é uma extensão importante para o Home Assistant, que permite instalar integrações personalizadas de forma fácil.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Vá até os repositórios personalizados**:
   Navegue até as configurações no painel do HACS e adicione o repositório como uma fonte personalizada.

3. **Adicione o repositório**:
   Insira a URL do repositório: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Baixe e instale a integração**:
   Procure a integração no HACS, faça o download e instale-a. Após a instalação, a configuração pode ser feita através da interface do Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuração
Após a instalação, é necessária uma configuração básica para definir corretamente a integração:
- **Nome de usuário e senha**: Use as credenciais da conta X-Sense recém-criada para estabelecer a conexão.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Visão geral dos dispositivos**: Depois da configuração bem-sucedida, os dispositivos compartilhados estarão disponíveis no Home Assistant e poderão ser utilizados para automações.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Visualização no Home Assistant
Após uma instalação e configuração bem-sucedidas, a integração será visível no Home Assistant. Os dispositivos estarão disponíveis no painel e poderão ser usados para automações, notificações e outras aplicações.


![Fórum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Dispositivos Suportados
Esta integração suporta vários dispositivos Xsense. Aqui está uma lista dos dispositivos atualmente confirmados e testados:
- **Estação-base (SBS50)**: Hub central para dispositivos Xsense.
- **Alarme de calor (XH02-M)**: Detecta temperaturas anormalmente altas.
- **Detector de monóxido de carbono (XC01-M; XC04-WX)**: Detecta concentrações perigosas de monóxido de carbono.
- **Detector de fumaça (XS01-M, WX; XS03-WX; XS0B-MR)**: Detecta fumaça em estágios iniciais.
- **Detector combinado de monóxido de carbono e fumaça (SC07-WX; XP0A-MR (parcialmente suportado))**: Dispositivos combinados para detectar monóxido de carbono e fumaça.
- **Detector de vazamento de água (SWS51)**: Detecta a presença de água em locais indesejados.
- **Higrômetro-termômetro (STH51)**: Monitoramento de temperatura e umidade.

Esses dispositivos podem ser usados para criar automações e alertas após serem integrados ao Home Assistant.

____________________________________________________________

## Exemplos de Automação
Com esta integração, é possível criar várias automações. Aqui estão alguns exemplos:

### Exemplo 1: Alerta de Temperatura
Quando a temperatura de um termômetro Xsense está muito alta, uma notificação é enviada:

```yaml
automation:
  - alias: "Alerta de Temperatura Xsense"
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

1. **Testar dispositivos**: Se você possui um dispositivo Xsense que funciona com a integração, nos avise para que possamos adicioná-lo à lista de dispositivos suportados.

2. **Feedback sobre dispositivos não suportados**: Caso algum dispositivo não funcione, nos forneça feedback para que possamos oferecer suporte ou incluir o dispositivo em futuras versões da integração.

3. **Compartilhar dispositivos para teste**: A melhor maneira de testar novos dispositivos é compartilhá-los através do aplicativo X-Sense. Assim, podemos garantir que o maior número possível de dispositivos seja suportado.

4. **Suporte da comunidade**: Participe das discussões em nossa comunidade. Se você tiver sugestões de melhorias ou ajudar outros usuários com sua instalação, toda ajuda será bem-vinda!

Para discussões e suporte, você pode se juntar ao nosso servidor Discord ou visitar o fórum Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Fórum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
