# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - note di rilascio collegate per ogni versione pubblicata.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Panoramica
Questa integrazione per Home Assistant consente l'utilizzo di dispositivi X-Sense all'interno di un sistema di casa intelligente. È stata creata sulla base del codice originale di [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) ed è stata pubblicata con la sua autorizzazione e in collaborazione con lui.

Questa integrazione HACS è mantenuta attivamente per chi desidera un supporto più ampio dei dispositivi X-Sense in Home Assistant. Viene aggiornata regolarmente con nuove funzionalità, maggiore copertura dei dispositivi e correzioni per i problemi segnalati.

## Compatibilità e aggiornamenti HACS
Se stai ancora usando una vecchia versione `v1.2.6.x`, aggiorna a `v1.3.14` o successiva prima di aggiornare Home Assistant Core alla 2026.7 o successiva. Le vecchie versioni `v1.2.6.x` richiedevano `aiortc`, che non è compatibile con il runtime Python 3.14 di Home Assistant. Le versioni attuali `v1.3.x` non richiedono più `aiortc`.

Questa integrazione viene installata come repository HACS personalizzato. Se Home Assistant non mostra subito l’aggiornamento, apri HACS, seleziona il repository X-Sense, usa il menu a tre punti per eseguire **Update information**, quindi aggiorna o riscarica l’integrazione e riavvia Home Assistant.


Entity changes: [X-Sense Entity Changes](../ENTITY_CHANGES.md).

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funzionalità
- Integrazione di diversi dispositivi X-Sense in Home Assistant.
- Supporto per automazioni basate sui dati dei sensori X-Sense.
- Supporto per stazioni base, rilevatori di fumo, rilevatori di monossido di carbonio, allarmi di calore, rilevatori di perdite d'acqua, igrometri, sensori porta, sensori movimento, luci, tastiere, cassette postali, dispositivo di ascolto, camere e altri dispositivi supportati quando disponibili nell'account X-Sense.
- Configurazione semplice tramite HACS (Home Assistant Community Store).

## Requisiti
- Un server Home Assistant funzionante (si consiglia l'ultima versione).
- Un account X-Sense con dispositivi supportati.
- HACS deve essere installato in Home Assistant per consentire l'installazione dell'integrazione.

## Video tutorial
Per una guida dettagliata all'installazione e alla configurazione dell'integrazione, puoi guardare il seguente video:

[![Integrazione X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparazione
Prima di installare l'integrazione, sono necessarie alcune preparazioni:

- **Crea un secondo account nell'app X-Sense (da utilizzare con Home Assistant)**: Poiché non è possibile accedere contemporaneamente all'app e a Home Assistant con lo stesso account, consigliamo di utilizzare un account separato per Home Assistant. In questo modo si evita di essere disconnessi continuamente dall'app o da Home Assistant. L'account aggiuntivo consente un'integrazione fluida e un utilizzo continuo senza interruzioni.

- **Condividi i dispositivi supportati dall'account principale con l'account Home Assistant**: Utilizza l'app X-Sense per condividere **solo i dispositivi supportati** con l'account appena creato. In questo modo sarà possibile utilizzare facilmente l'integrazione in Home Assistant continuando a gestire i dispositivi tramite l'account principale.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installazione tramite HACS
1. **Apri HACS in Home Assistant**:
  HACS è un'importante estensione per Home Assistant che consente di installare facilmente integrazioni personalizzate.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Vai ai repository personalizzati**:
  Vai alle impostazioni nella dashboard di HACS e aggiungi il repository come fonte personalizzata.

3. **Aggiungi il repository**:
  Inserisci l'URL del repository: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Scarica e installa l'integrazione**:
  Cerca l'integrazione in HACS, scaricala e installala. Dopo l'installazione, la configurazione può essere effettuata tramite l'interfaccia di Home Assistant.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configurazione
Dopo l'installazione è necessaria una configurazione di base per impostare correttamente l'integrazione:
- **Nome utente e password**: Utilizza le credenziali dell'account X-Sense appena creato per stabilire la connessione.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Panoramica dei dispositivi**: Dopo la configurazione riuscita, i dispositivi condivisi saranno disponibili in Home Assistant e potranno essere utilizzati per le automazioni.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Visualizzazione in Home Assistant
Dopo una corretta installazione e configurazione, l'integrazione sarà visibile in Home Assistant. I dispositivi saranno visibili sulla dashboard e potranno essere utilizzati per automazioni, notifiche e altre applicazioni.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Dispositivi supportati
Questa integrazione supporta diversi dispositivi X-Sense. Le entità disponibili dipendono dai campi dati riportati dal dispositivo e dall'account. Famiglie e modelli confermati includono:
- **Stazione base (SBS50)**: Hub centrale per i dispositivi X-Sense.
- **Rilevatore di calore (XH02-M)**: Rileva temperature anomale elevate.
- **Rilevatore di monossido di carbonio (XC01-M; XC04-WX)**: Rileva concentrazioni pericolose di CO.
- **Rilevatore di fumo (XS01-M; XS01-WX; XS03-WX; XS0B-MR e modelli RF/iR correlati)**: Rilevamento precoce del fumo.
- **Rilevatore combinato CO e fumo (SC07-WX; XP0A-MR e modelli XP/SC correlati)**: Rileva CO e fumo.
- **Rilevatore di perdite d'acqua (SWS51)**: Rileva acqua in punti indesiderati.
- **Igrometro-termometro (STH51, STH0A, STH0B, STH0C)**: Monitora temperatura e umidità.
- **Sensore porta (SDS0A)** e **sensore movimento (SMS0A)**: Esposti quando X-Sense fornisce lo stato.
- **Camera (SSC0A, SSC0B)**: Espone entità camera, miniature, URL live stream, diagnostica e impostazioni basate sull'app Android quando supportate da dispositivo e account.
- **Altri dispositivi collegati alla stazione**: Luce, tastiera, cassetta postale, dispositivo di ascolto, allarme vialetto, deposito intelligente, telecomando e dati radon sono esposti quando l'API riporta campi supportati.

### Entità e azioni disponibili
L'integrazione crea entità Home Assistant solo per i campi realmente presenti nel cloud X-Sense, nei payload MQTT shadow o nelle API camera allineate al comportamento dell'app Android. A seconda del dispositivo, può includere:

- Sensori binari per alarm, mute, end-of-life, AC-break, allarme acqua, allarme temperatura, ricarica, movimento, porta, stato armed, warning, reminder, light, PIR e stato keypad.
- Sensori per batteria, segnale RF, segnale Wi-Fi, firmware, temperatura, umidità, livello CO, picco CO, volume allarme, volume voce, volume del segnale, volume promemoria, soglie di avviso, timer di silenziamento, marche temporali leggibili, fuso orario e altri dati diagnostici.
- Supported camera setup and tuning controls are exposed in Home Assistant when the X-Sense app reports that the feature and account support it.
- Pulsanti test, mute, fire-drill e camera wake per i modelli in cui l'app X-Sense espone l'azione corrispondente.

Alcune entità sono diagnostiche o di configurazione e vengono raggruppate così in Home Assistant. Se un dispositivo non segnala un campo specifico, o se l'app X-Sense indica che la funzione non è supportata per quel dispositivo/account, l'entità corrispondente non viene creata. Associazione, rimozione, condivisione, account, pagamenti, aggiornamento firmware, formattazione SD e altre azioni di gestione restano nell'app X-Sense.
____________________________________________________________

## Vista live della videocamera e notifiche IA
Il modo più semplice è usare il blueprint incluso. Importalo con il pulsante qui sotto, scegli l’entità evento della videocamera `Motion` o `AI Detection` per una videocamera con abbonamento, quindi modifica l’azione di notifica se necessario.

Quando un evento Motion include dati di riproduzione X-Sense, l'integrazione può prima memorizzare il clip nella cache e poi inviare una notifica mobile che apre il clip corrispondente in X-Sense Recordings. Disattiva i link alle registrazioni nel blueprint se vuoi una semplice notifica di movimento senza attendere il video. La sincronizzazione dei media di registrazione può mantenere pronti i clip recenti in background, e i vecchi blueprint camera X-Sense importati vengono aggiornati automaticamente.

[![Importa blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion e AI Detection sono eventi singoli, non stati acceso/spento. Per automazioni manuali usa il trigger `event.received` di Home Assistant con l’entità videocamera `Motion` o `AI Detection`; `event_type` serve solo per filtrare una AI Detection con abbonamento su tipi come `person`, `pet`, `vehicle`, `package`, `other` o `ai_detection`.

Esempio di automazione:

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
## Esempi di automazioni
Con questa integrazione, è possibile creare diverse automazioni. Ecco alcuni esempi:

### Esempio 1: Avviso di temperatura
Quando la temperatura di un termometro X-Sense è troppo alta, viene inviata una notifica:

```yaml
automation:
  - alias: "Avviso di temperatura X-Sense"
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

1. **Test dei dispositivi**: Se possiedi un dispositivo X-Sense che funziona con l'integrazione, faccelo sapere in modo da poterlo aggiungere all'elenco dei dispositivi supportati.

2. **Feedback sui dispositivi non supportati**: Se un dispositivo non funziona, forniscici un feedback in modo che possiamo fornire supporto o includere il dispositivo nelle versioni future dell'integrazione.

3. **Condivisione dei dispositivi per i test**: Il modo migliore per testare nuovi dispositivi è condividerli tramite l'app X-Sense. In questo modo possiamo garantire che il maggior numero possibile di dispositivi sia supportato.

4. **Supporto della comunità**: Partecipa alle discussioni nella nostra comunità. Che si tratti di suggerimenti per miglioramenti o di aiutare altri utenti con la loro installazione, ogni aiuto è ben accetto!

Per discussioni e supporto, puoi unirti al nostro server Discord o visitare il forum Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Riferimento completo

### Account e installazione
- Usa un account X-Sense separato per Home Assistant.
- Condividi dall'account principale solo i dispositivi supportati.
- Associazione, rimozione, condivisione, firmware, account, pagamenti e gestione della scheda SD restano nell'app X-Sense.

### Aggiornamenti e uso dell'API
- Le variazioni rapide di stato arrivano tramite messaggi MQTT shadow.
- Le richieste cloud servono per accesso, rilevamento dispositivi, dati delle camere e recupero dello stato.
- Il polling periodico è solo un fallback quando manca un aggiornamento live.

### Entità, camere e risoluzione problemi
- Le entità vengono create solo per i campi che X-Sense segnala davvero.
- Le entità e i controlli delle camere vengono creati solo quando l'API allineata all'app Android segnala il supporto per quell'account e modello.
- Se manca un valore, confrontalo prima con l'app X-Sense e poi allega diagnostica e log Home Assistant pertinenti.

## Elenco dispositivi ed entità

### Famiglie principali
- Stazione SBS50, rilevatori di fumo XS, rilevatori CO XC, combinati SC/XP, rilevatori di calore XH, sensori acqua SWS, sensori temperatura/umidità STH, sensori porta SDS, sensori movimento SMS, camere SSC e altre famiglie X-Sense segnalate sono gestiti quando l'API espone i relativi campi.

### Campi di stato
- Allarme, silenziamento, batteria, segnale RF/Wi-Fi, temperatura, umidità, CO, acqua, movimento, porta, luce, promemoria, avvisi e marche temporali leggibili appaiono solo quando X-Sense li segnala.

### Controlli e segnalazioni
- Interruttori, selettori, numeri e pulsanti vengono creati solo per impostazioni e azioni scrivibili esposte da dispositivo e account.
- Una buona segnalazione include modello esatto, versione dell'integrazione, diagnostica, log e se il valore cambia correttamente nell'app X-Sense.
