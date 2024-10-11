# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Panoramica
Questa integrazione per Home Assistant consente l'utilizzo di dispositivi Xsense all'interno di un sistema di casa intelligente. È stata creata sulla base del codice originale di [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) ed è stata pubblicata con la sua autorizzazione e in collaborazione con lui.

Fino a quando non sarà disponibile un'integrazione ufficiale per Home Assistant da parte di Theo, verrà utilizzata questa integrazione HACS, che verrà regolarmente aggiornata per aggiungere nuove funzionalità e risolvere eventuali problemi. Questa integrazione consente agli utenti di integrare facilmente i loro dispositivi Xsense in Home Assistant e di utilizzarli per varie automazioni e monitoraggi.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funzionalità
- Integrazione di diversi dispositivi Xsense in Home Assistant.
- Supporto per automazioni basate sui dati dei sensori Xsense.
- Supporto per i seguenti tipi di dispositivi: stazioni base, rilevatori di fumo, rilevatori di monossido di carbonio, rilevatori di calore, rilevatori di perdite d'acqua e igrometri.
- Configurazione semplice tramite HACS (Home Assistant Community Store).

## Requisiti
- Un server Home Assistant funzionante (si consiglia l'ultima versione).
- Un account Xsense con dispositivi supportati.
- HACS deve essere installato in Home Assistant per consentire l'installazione dell'integrazione.

## Video tutorial
Per una guida dettagliata all'installazione e alla configurazione dell'integrazione, puoi guardare il seguente video:

[![Integrazione X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparazione
Prima di installare l'integrazione, sono necessarie alcune preparazioni:

- **Crea un secondo account nell'app X-Sense (da utilizzare con Home Assistant)**: Poiché non è possibile accedere contemporaneamente all'app e a Home Assistant con lo stesso account, consigliamo di utilizzare un account separato per Home Assistant. In questo modo si evita di essere disconnessi continuamente dall'app o da Home Assistant. L'account aggiuntivo consente un'integrazione fluida e un utilizzo continuo senza interruzioni.

- **Condividi i dispositivi supportati dall'account principale con l'account Home Assistant**: Utilizza l'app X-Sense per condividere **solo i dispositivi supportati** con l'account appena creato. In questo modo sarà possibile utilizzare facilmente l'integrazione in Home Assistant continuando a gestire i dispositivi tramite l'account principale.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installazione tramite HACS
1. **Apri HACS in Home Assistant**:
   HACS è un'importante estensione per Home Assistant che consente di installare facilmente integrazioni personalizzate.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Vai ai repository personalizzati**:
   Vai alle impostazioni nella dashboard di HACS e aggiungi il repository come fonte personalizzata.

3. **Aggiungi il repository**:
   Inserisci l'URL del repository: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Scarica e installa l'integrazione**:
   Cerca l'integrazione in HACS, scaricala e installala. Dopo l'installazione, la configurazione può essere effettuata tramite l'interfaccia di Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configurazione
Dopo l'installazione è necessaria una configurazione di base per impostare correttamente l'integrazione:
- **Nome utente e password**: Utilizza le credenziali dell'account X-Sense appena creato per stabilire la connessione.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Panoramica dei dispositivi**: Dopo la configurazione riuscita, i dispositivi condivisi saranno disponibili in Home Assistant e potranno essere utilizzati per le automazioni.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Visualizzazione in Home Assistant
Dopo una corretta installazione e configurazione, l'integrazione sarà visibile in Home Assistant. I dispositivi saranno visibili sulla dashboard e potranno essere utilizzati per automazioni, notifiche e altre applicazioni.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Dispositivi supportati
Questa integrazione supporta diversi dispositivi Xsense. Ecco un elenco dei dispositivi attualmente confermati e testati:
- **Stazione base (SBS50)**: Hub centrale per i dispositivi Xsense.
- **Rilevatore di calore (XH02-M)**: Rilevamento di temperature insolitamente elevate.
- **Rilevatore di monossido di carbonio (XC01-M; XC04-WX)**: Rileva concentrazioni pericolose di monossido di carbonio.
- **Rilevatore di fumo (XS01-M, WX; XS03-WX; XS0B-MR)**: Rilevamento precoce del fumo.
- **Rilevatore combinato di monossido di carbonio e fumo (SC07-WX; XP0A-MR (parzialmente supportato))**: Dispositivi combinati per rilevare sia il monossido di carbonio che il fumo.
- **Rilevatore di perdite d'acqua (SWS51)**: Rileva la presenza di acqua in luoghi indesiderati.
- **Igrometro-termometro (STH51)**: Monitoraggio della temperatura e dell'umidità.

Questi dispositivi possono essere utilizzati per creare automazioni e avvisi una volta integrati in Home Assistant.

____________________________________________________________

## Esempi di automazioni
Con questa integrazione, è possibile creare diverse automazioni. Ecco alcuni esempi:

### Esempio 1: Avviso di temperatura
Quando la temperatura di un termometro Xsense è troppo alta, viene inviata una notifica:

```yaml
automation:
  - alias: "Avviso di temperatura Xsense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "La temperatura supera i 30 gradi!"
```

### Esempio 2: Allarme del rilevatore di perdite d'acqua
Quando il rilevatore di perdite d'acqua rileva una presenza d'acqua, viene attivato un avviso:

```yaml
automation:
  - alias: "Allarme del rilevatore di perdite d'acqua"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Rilevata perdita d'acqua!"
```

____________________________________________________________

## Abbiamo bisogno del tuo aiuto
Siamo sempre alla ricerca di supporto per sviluppare e migliorare ulteriormente questa integrazione. Ecco alcuni modi in cui puoi aiutare:

1. **Test dei dispositivi**: Se possiedi un dispositivo Xsense che funziona con l'integrazione, faccelo sapere in modo da poterlo aggiungere all'elenco dei dispositivi supportati.

2. **Feedback sui dispositivi non supportati**: Se un dispositivo non funziona, forniscici un feedback in modo che possiamo fornire supporto o includere il dispositivo nelle versioni future dell'integrazione.

3. **Condivisione dei dispositivi per i test**: Il modo migliore per testare nuovi dispositivi è condividerli tramite l'app X-Sense. In questo modo possiamo garantire che il maggior numero possibile di dispositivi sia supportato.

4. **Supporto della comunità**: Partecipa alle discussioni nella nostra comunità. Che si tratti di suggerimenti per miglioramenti o di aiutare altri utenti con la loro installazione, ogni aiuto è ben accetto!

Per discussioni e supporto, puoi unirti al nostro server Discord o visitare il forum Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)



