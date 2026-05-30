# ha-xsense-component_test

## Visão geral
Esta integração do Home Assistant permite usar dispositivos X-Sense em uma casa inteligente. Ela se baseia no trabalho original de Theo Snel e é instalada pelo HACS.

Recomendamos criar uma conta X-Sense separada para o Home Assistant e compartilhar, a partir da conta principal, apenas os dispositivos compatíveis.

## Instalação
No HACS, adicione o repositório personalizado `https://github.com/Jarnsen/ha-xsense-component_test`, baixe a integração, siga as instruções de reinicialização do HACS e configure-a com a conta X-Sense dedicada ao Home Assistant.

## Dispositivos compatíveis
São compatíveis estações base, detectores de fumaça, detectores de CO, alarmes de calor, detectores de vazamento de água, higrômetros, sensores de porta e movimento, luzes, teclados, sensores de caixa de correio, dispositivos ouvintes e câmeras compatíveis quando a conta X-Sense os reporta.

As famílias de modelos confirmadas incluem: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entidades e ações
A integração cria entidades apenas para dados que o dispositivo realmente reporta. Isso pode incluir alarmes, silenciamento, bateria, sinal, temperatura, umidade, CO, campos de horário legíveis, configurações de câmera, interruptores de LED e botões de teste, silenciamento ou simulado de incêndio.

Gerenciamento, compartilhamento, remoção de dispositivos, firmware, contas e pagamentos continuam no aplicativo X-Sense.

## Suporte
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
