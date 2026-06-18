# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Aperçu
Cette intégration pour Home Assistant permet l'utilisation des appareils X-Sense au sein d'un système de maison intelligente. Elle est basée sur le code original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) et a été publiée avec son autorisation et en collaboration avec lui.

Cette intégration HACS est activement maintenue pour les utilisateurs qui souhaitent une prise en charge plus large des appareils X-Sense dans Home Assistant. Elle est régulièrement mise à jour avec de nouvelles fonctions, une meilleure couverture des appareils et des corrections issues des signalements.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Fonctionnalités
- Intégration de divers appareils X-Sense dans Home Assistant.
- Prise en charge des automatisations basées sur les données des capteurs X-Sense.
- Prise en charge des stations de base, détecteurs de fumée, détecteurs de monoxyde de carbone, détecteurs de chaleur, détecteurs de fuite d'eau, hygromètres, capteurs de porte, capteurs de mouvement, lumières, claviers, boîtes aux lettres, dispositifs d’écoute, caméras et autres appareils compatibles lorsqu'ils sont disponibles dans le compte X-Sense.
- Installation simple via HACS (Home Assistant Community Store).

## Conditions préalables
- Un serveur Home Assistant fonctionnel (la dernière version est recommandée).
- Un compte X-Sense avec des appareils pris en charge.
- HACS doit être installé dans Home Assistant pour permettre l'installation de l'intégration.

## Tutoriel vidéo
Pour un guide détaillé sur l'installation et la configuration de l'intégration, vous pouvez regarder la vidéo suivante :

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Préparation
Avant d'installer l'intégration, certaines préparations sont nécessaires :

- **Créez un deuxième compte dans l'application X-Sense (pour l'utilisation avec Home Assistant)** : Comme il est impossible d'être connecté simultanément à l'application et à Home Assistant avec le même compte, nous vous recommandons d'utiliser un compte distinct pour Home Assistant. Cela évitera que vous soyez constamment déconnecté de l'application ou de Home Assistant. Le deuxième compte permet une utilisation fluide et continue sans interruptions dues à des connexions et déconnexions répétées.

- **Partagez les appareils pris en charge du compte principal avec le compte Home Assistant** : Utilisez l'application X-Sense pour partager **uniquement les appareils pris en charge** avec le compte nouvellement créé. Ainsi, vous pourrez facilement utiliser l'intégration dans Home Assistant tout en continuant à gérer les appareils via votre compte principal.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installation via HACS
1. **Ouvrir HACS dans Home Assistant** :
  HACS est une extension importante pour Home Assistant qui vous permet d'installer facilement des intégrations personnalisées.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Accéder aux dépôts personnalisés** :
  Accédez au tableau de bord HACS, allez dans les paramètres et ajoutez le dépôt en tant que source personnalisée.

3. **Ajouter le dépôt** :
  Entrez l'URL du dépôt : `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Télécharger et installer l'intégration** :
  Recherchez l'intégration dans HACS, téléchargez-la et installez-la. Après l'installation, la configuration peut être effectuée via l'interface de Home Assistant.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuration
Après l'installation, une configuration de base est nécessaire pour configurer correctement l'intégration :
- **Nom d'utilisateur et mot de passe** : Utilisez les identifiants du compte X-Sense nouvellement créé pour établir la connexion.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Aperçu des appareils** : Une fois configurés avec succès, les appareils partagés seront disponibles dans Home Assistant et pourront être utilisés pour les automatisations.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Affichage dans Home Assistant
Après une installation et une configuration réussies, l'intégration sera visible dans Home Assistant. Les appareils seront disponibles sur le tableau de bord et pourront être utilisés pour les automatisations, les notifications et d'autres applications.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Appareils pris en charge
Cette intégration prend en charge plusieurs appareils X-Sense. Les entités disponibles dépendent des champs de données signalés par chaque appareil et compte. Familles et modèles confirmés :
- **Station de base (SBS50)** : Hub central pour les appareils X-Sense.
- **Détecteur de chaleur (XH02-M)** : Détecte les températures anormalement élevées.
- **Détecteur de monoxyde de carbone (XC01-M; XC04-WX)** : Détecte les concentrations dangereuses de monoxyde de carbone.
- **Détecteur de fumée (XS01-M; XS01-WX; XS03-WX; XS0B-MR et modèles RF/iR associés)** : Détection précoce de fumée.
- **Détecteur combiné monoxyde de carbone et fumée (SC07-WX; XP0A-MR et modèles XP/SC associés)** : Détecte le monoxyde de carbone et la fumée.
- **Détecteur de fuite d'eau (SWS51)** : Détecte l'eau dans les endroits indésirables.
- **Hygromètre-thermomètre (STH51, STH0A, STH0B, STH0C)** : Surveille température et humidité.
- **Capteur de porte (SDS0A)** : Expose l'état de porte lorsque X-Sense le fournit.
- **Détecteur de mouvement (SMS0A)** : Expose l'état d'alarme de mouvement lorsque X-Sense le fournit.
- **Caméra (SSC0A, SSC0B)** : Expose les entités caméra, miniatures, URLs de flux en direct, diagnostics et réglages basés sur l'app Android lorsque l'appareil et le compte les prennent en charge.
- **Autres appareils reliés à une station** : Lumière, clavier, boîte aux lettres, dispositif d’écoute, alarme d'allée, boîte de dépôt intelligente, télécommande et données radon sont exposés lorsque l'API signale les champs compatibles.

### Entités et actions disponibles
L'intégration crée des entités Home Assistant uniquement pour les champs présents dans le cloud X-Sense, les messages MQTT shadow ou les API caméra alignées sur l'application Android. Selon l'appareil, cela peut inclure :

- Des capteurs binaires pour l'alarme, le silence, la fin de vie, la coupure secteur, l'alarme eau, l'alarme température, la charge, le mouvement, la porte, l'armement, les avertissements, les rappels, la lumière, le PIR et l'état du clavier.
- Des capteurs de batterie, signal RF, signal Wi-Fi, firmware, température, humidité, niveau CO, pic CO, volume d'alarme, volume vocal, volume chirp, volume de rappel, seuils d'avertissement, minuteries de silence, horodatages lisibles, fuseau horaire et autres données de diagnostic.
- Des interrupteurs pour les réglages modifiables pris en charge, comme la LED, l'activation d'alarme, l'alarme continue, le ton chirp, les rappels, le PIR, sunshine/white light, l'attente, le son du clavier, la détection de mouvement caméra, l'enregistrement, la vision nocturne, l'audio, le cooldown, la lumière et les contrôles de sonnette.
- Des sélecteurs et nombres pour les réglages caméra pris en charge, comme la langue, la résolution d'enregistrement, le codec, l'anti-scintillement, la sensibilité de mouvement, la durée vidéo, le volume, la durée d'alarme, le cooldown, le seuil de nuit et la touche de sonnette.
- Des boutons test, silence, exercice incendie et réveil caméra pour les modèles où l'application X-Sense expose l'action correspondante.

Certaines entités sont de diagnostic ou de configuration et sont regroupées ainsi dans Home Assistant. Si un appareil ne signale pas un champ précis, ou si l'application X-Sense marque la fonction comme non prise en charge pour cet appareil/compte, l'entité correspondante n'est pas créée. La liaison, suppression, partage, compte, paiement, mise à jour firmware, formatage de carte SD et autres actions d'administration restent dans l'application X-Sense.
____________________________________________________________

## Camera Live View and AI Notifications
Supported cameras use native Home Assistant WebRTC for live video and audio. They also create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

The easiest UI path is the included blueprint. Use the button below to import it, select the camera `AI Detection` event entity, leave Detection types selected to notify for every AI event, then keep or replace the default notification action.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

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
## Exemples d'automatisations
Avec cette intégration, vous pouvez créer différentes automatisations. Voici quelques exemples :

### Exemple 1 : Alerte de température
Lorsque la température d'un thermomètre X-Sense est trop élevée, une notification est envoyée :

```yaml
automation:
  - alias: "Alerte de température X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "La température dépasse 30 degrés !"
```

### Exemple 2 : Alarme de détecteur de fuite d'eau
Lorsque le détecteur de fuite d'eau détecte la présence d'eau, une alerte est déclenchée :

```yaml
automation:
  - alias: "Alarme de détecteur de fuite d'eau"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Une fuite d'eau a été détectée !"
```

____________________________________________________________

## Nous avons besoin de votre aide
Nous sommes toujours à la recherche de soutien pour continuer à développer et améliorer cette intégration. Voici quelques façons dont vous pouvez aider :

1. **Tester des appareils** : Si vous possédez un appareil X-Sense qui fonctionne avec l'intégration, faites-le nous savoir afin que nous puissions l'ajouter à la liste des appareils pris en charge.

2. **Retour sur les appareils non pris en charge** : Si un appareil ne fonctionne pas, faites-le nous savoir afin que nous puissions fournir un support ou intégrer l'appareil dans les futures versions de l'intégration.

3. **Partage de dispositifs pour les tests** : Le meilleur moyen de tester de nouveaux appareils est de partager l'appareil via l'application X-Sense. Cela nous aidera à assurer la compatibilité d'un maximum d'appareils.

4. **Support communautaire** : Participez aux discussions dans notre communauté. Que vous ayez des suggestions d'amélioration ou que vous aidiez d'autres utilisateurs à installer l'intégration, chaque aide est la bienvenue !

Pour des discussions et du support, vous pouvez nous rejoindre sur notre serveur Discord ou sur le forum Home Assistant :

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

![Discord](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

## Référence complète

### Compte et installation
- Utilisez un compte X-Sense séparé pour Home Assistant.
- Partagez uniquement les appareils pris en charge depuis le compte X-Sense principal.
- L'appairage, la suppression, le partage, le micrologiciel, le compte, les paiements et la gestion de la carte SD restent dans l'application X-Sense.

### Mises à jour et utilisation de l'API
- Les changements d'état rapides arrivent par les messages MQTT shadow.
- Les requêtes cloud servent à la connexion, à la découverte des appareils, aux données caméra et à la récupération d'état.
- L'interrogation périodique n'est qu'un secours lorsqu'une mise à jour en direct manque.

### Entités, caméras et dépannage
- Les entités sont créées uniquement pour les champs réellement signalés par X-Sense.
- Les entités et commandes de caméra sont créées uniquement lorsque l'API alignée sur l'application Android indique leur prise en charge pour ce compte et ce modèle.
- Si une valeur manque, comparez d'abord avec l'application X-Sense, puis joignez les diagnostics et les journaux Home Assistant pertinents.

## Liste de contrôle des appareils et entités

### Familles principales
- Station SBS50, détecteurs de fumée XS, détecteurs CO XC, détecteurs combinés SC/XP, détecteurs de chaleur XH, détecteurs d'eau SWS, capteurs température/humidité STH, capteurs de porte SDS, détecteurs de mouvement SMS, caméras SSC et autres familles X-Sense signalées sont gérés lorsque l'API expose leurs champs.

### Champs d'état
- Alarme, sourdine, batterie, signal RF/Wi-Fi, température, humidité, CO, eau, mouvement, porte, lumière, rappels, avertissements et horodatages lisibles apparaissent uniquement lorsqu'ils sont signalés par X-Sense.

### Commandes et signalements
- Les interrupteurs, sélecteurs, nombres et boutons sont créés uniquement pour les réglages et actions modifiables exposés par l'appareil et le compte.
- Un bon rapport de bug inclut le modèle exact, la version de l'intégration, les diagnostics, les journaux et si la valeur change correctement dans l'application X-Sense.
