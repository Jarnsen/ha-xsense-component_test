# ha-xsense-component_test

## Résumé
Cette intégration pour Home Assistant permet l'utilisation des appareils Xsense au sein du système de maison intelligente. L'intégration est basée sur le code original de [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) et a été publiée avec son autorisation et en collaboration avec lui.

Jusqu'à ce qu'une intégration officielle pour Home Assistant soit disponible de la part de Theo, cette intégration HACS sera utilisée et mise à jour régulièrement pour ajouter de nouvelles fonctionnalités et résoudre les problèmes existants. Cette intégration permet aux utilisateurs d'intégrer facilement leurs appareils Xsense dans Home Assistant et de les utiliser pour diverses automatisations et surveillances.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Fonctionnalités
- Intégration de plusieurs appareils Xsense dans Home Assistant.
- Prise en charge des automatisations basées sur les données des capteurs Xsense.
- Prise en charge des types d'appareils suivants : stations de base, détecteurs de fumée, détecteurs de monoxyde de carbone, capteurs de chaleur, capteurs d'eau et hygromètres.
- Installation simple via HACS (Home Assistant Community Store).

## Exigences
- Un serveur Home Assistant fonctionnel (la dernière version est recommandée).
- Un compte Xsense avec des appareils compatibles.
- HACS doit être installé dans Home Assistant pour permettre l'installation de l'intégration.

## Tutoriel vidéo
Pour un guide détaillé sur l'installation et la configuration de l'intégration, vous pouvez regarder la vidéo suivante :

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Préparation
Avant d'installer l'intégration, il est nécessaire d'effectuer certaines préparations :

- **Créer un deuxième compte dans l'application X-Sense (pour une utilisation avec Home Assistant)** : Étant donné qu'il n'est pas possible de se connecter simultanément à l'application et à Home Assistant avec le même compte, nous recommandons d'utiliser un compte séparé pour Home Assistant. Cela évitera que vous soyez constamment déconnecté entre l'application et Home Assistant. Le compte supplémentaire permettra une intégration et une utilisation fluides sans interruptions dues à des connexions et déconnexions répétées.

- **Partager les appareils compatibles du compte principal avec le compte Home Assistant** : Utilisez l'application X-Sense pour partager **uniquement les appareils compatibles** avec le compte nouvellement créé. De cette manière, vous pourrez utiliser l'intégration dans Home Assistant de manière simple, tout en gérant les appareils via votre compte principal.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installation via HACS
1. **Ouvrir HACS dans Home Assistant** :
   HACS est une extension importante pour Home Assistant qui vous permet d'installer facilement des intégrations personnalisées.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Accéder aux dépôts personnalisés** :
   Naviguez vers le tableau de bord HACS, allez dans les paramètres et ajoutez le dépôt comme source personnalisée.

3. **Ajouter le dépôt** :
   Entrez l'URL du dépôt : `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Télécharger et installer l'intégration** :
   Recherchez l'intégration dans HACS, téléchargez-la et installez-la. Après l'installation, la configuration peut être effectuée via l'interface Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuration
Après l'installation, une configuration de base est nécessaire pour configurer correctement l'intégration :
- **Nom d'utilisateur et mot de passe** : Utilisez les identifiants du compte X-Sense nouvellement créé pour établir la connexion.
- **Vue d'ensemble des appareils** : Une fois configurés avec succès, les appareils partagés seront disponibles dans Home Assistant et pourront être utilisés pour des automatisations.

## Affichage dans Home Assistant
Après une installation et une configuration réussies, l'intégration sera visible dans Home Assistant. Les appareils seront disponibles sur le tableau de bord et pourront être utilisés pour des automatisations, des notifications et d'autres applications.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/50bbafde-c94b-445e-9aa3-9c33d5f151d6)

____________________________________________________________

## Appareils compatibles
Cette intégration est compatible avec plusieurs appareils Xsense. Voici une liste des appareils confirmés et testés :
- **Station de base (SBS50)** : Hub central pour les appareils Xsense.
- **Capteur de chaleur (XH02-M)** : Détection de températures inhabituellement élevées.
- **Détecteur de monoxyde de carbone (XC01-M; XC04-WX)** : Détecte les concentrations dangereuses de monoxyde de carbone.
- **Détecteur de fumée (XS01-M, WX; XS03-WX; XS0B-MR)** : Détection précoce de fumée.
- **Détecteur combiné de monoxyde de carbone et de fumée (SC07-WX; XP0A-MR (partiellement compatible))** : Détecte à la fois le monoxyde de carbone et la fumée.
- **Capteur d'eau (SWS51)** : Détecte la présence d'eau dans des endroits indésirables.
- **Hygromètre-thermomètre (STH51)** : Surveillance de la température et de l'humidité.

Ces appareils, une fois intégrés dans Home Assistant, peuvent être utilisés pour des automatisations et des alertes.

____________________________________________________________

## Exemples d'automatisations
Avec cette intégration, vous pouvez créer différentes automatisations. Voici quelques exemples :

### Exemple 1 : Alerte de température
Lorsque la température d'un thermomètre Xsense est trop élevée, une notification est envoyée :
```yaml
automation:
  - alias: "Alerte de température Xsense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "La température dépasse 30 degrés !"
```

### Exemple 2 : Alarme de capteur d'eau
Lorsque le capteur d'eau détecte de l'eau, une alerte est déclenchée :
```yaml
automation:
  - alias: "Alarme de capteur d'eau"
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

1. **Tester des appareils** : Si vous possédez un appareil Xsense qui fonctionne avec l'intégration, faites-le nous savoir afin que nous puissions l'ajouter à la liste des appareils compatibles.

2. **Support pour les appareils non compatibles** : Si un appareil ne fonctionne pas, faites-le nous savoir afin que nous puissions fournir un support ou l'intégrer dans les versions futures.

3. **Partager des appareils** : La meilleure façon de tester de nouveaux appareils est de partager l'appareil via l'application X-Sense.

Pour des discussions et du support, vous pouvez nous rejoindre sur notre serveur Discord ou sur le forum Home Assistant :

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

![Discord](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)
