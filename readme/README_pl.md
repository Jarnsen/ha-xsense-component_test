# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Przegląd
Ta integracja z Home Assistant umożliwia korzystanie z urządzeń X-Sense w systemie inteligentnego domu. Została stworzona na podstawie oryginalnego kodu [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) i opublikowana za jego zgodą oraz we współpracy z nim.

Ta integracja HACS jest aktywnie utrzymywana dla użytkowników, którzy chcą szerszej obsługi urządzeń X-Sense w Home Assistant. Jest regularnie aktualizowana o nowe funkcje, obsługę kolejnych urządzeń i poprawki zgłaszanych problemów.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funkcje
- Integracja różnych urządzeń X-Sense z Home Assistant.
- Obsługa automatyzacji na podstawie danych z czujników X-Sense.
- Obsługa stacji bazowych, czujników dymu, czujników tlenku węgla, alarmów ciepła, czujników zalania, higrometrów, czujników drzwi, czujników ruchu, świateł, klawiatur, skrzynek pocztowych, urządzeń nasłuchowych, kamer i innych obsługiwanych urządzeń, gdy są dostępne na koncie X-Sense.
- Prosta konfiguracja przez HACS (Home Assistant Community Store).

## Wymagania
- Działający serwer Home Assistant (zalecana najnowsza wersja).
- Konto X-Sense z obsługiwanymi urządzeniami.
- HACS musi być zainstalowany w Home Assistant, aby umożliwić instalację tej integracji.

## Wideo instruktażowe
Aby uzyskać szczegółowy przewodnik dotyczący instalacji i konfiguracji integracji, możesz obejrzeć poniższe wideo:

[![Integracja X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Przygotowanie
Przed zainstalowaniem integracji należy wykonać kilka przygotowań:

- **Utwórz drugie konto w aplikacji X-Sense (do użytku z Home Assistant)**: Ponieważ nie jest możliwe jednoczesne zalogowanie się do aplikacji i do Home Assistant za pomocą tego samego konta, zalecamy użycie osobnego konta do Home Assistant. Dzięki temu unikasz ciągłego wylogowywania się z aplikacji lub Home Assistant. Dodatkowe konto umożliwia płynną integrację i użytkowanie bez przerw wynikających z częstego logowania i wylogowywania.

- **Udostępnij obsługiwane urządzenia z głównego konta do konta Home Assistant**: Użyj aplikacji X-Sense, aby udostępnić **tylko obsługiwane urządzenia** nowo utworzonemu kontu. W ten sposób możesz bezproblemowo korzystać z integracji w Home Assistant, kontynuując zarządzanie urządzeniami z poziomu głównego konta.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalacja przez HACS
1. **Otwórz HACS w Home Assistant**:
  HACS to ważne rozszerzenie dla Home Assistant, które umożliwia łatwą instalację niestandardowych integracji.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Przejdź do niestandardowych repozytoriów**:
  Przejdź do ustawień w panelu HACS i dodaj to repozytorium jako źródło niestandardowe.

3. **Dodaj repozytorium**:
  Wprowadź URL repozytorium: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Pobierz i zainstaluj integrację**:
  Wyszukaj integrację w HACS, pobierz ją i zainstaluj. Po zakończeniu instalacji konfigurację można przeprowadzić za pomocą interfejsu Home Assistant.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Konfiguracja
Po zainstalowaniu wymagane jest podstawowe skonfigurowanie, aby prawidłowo ustawić integrację:
- **Nazwa użytkownika i hasło**: Użyj danych logowania do nowo utworzonego konta X-Sense, aby nawiązać połączenie.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Przegląd urządzeń**: Po pomyślnym skonfigurowaniu, udostępnione urządzenia będą dostępne w Home Assistant i mogą być używane do automatyzacji.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Widok w Home Assistant
Po pomyślnej instalacji i konfiguracji integracja będzie widoczna w Home Assistant. Urządzenia będą widoczne na pulpicie nawigacyjnym i mogą być używane do automatyzacji, powiadomień i innych zastosowań.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)


____________________________________________________________

## Obsługiwane urządzenia
Integracja obsługuje różne urządzenia X-Sense. Dostępne encje zależą od pól zgłaszanych przez urządzenie i konto. Potwierdzone rodziny i modele obejmują:
- **Stacja bazowa (SBS50)**: Centralny hub dla urządzeń X-Sense.
- **Czujnik ciepła (XH02-M)**: Wykrywa nietypowo wysoką temperaturę.
- **Czujnik tlenku węgla (XC01-M; XC04-WX)**: Wykrywa niebezpieczne stężenia CO.
- **Czujnik dymu (XS01-M; XS01-WX; XS03-WX; XS0B-MR i powiązane modele RF/iR)**: Wczesne wykrywanie dymu.
- **Czujnik łączony CO i dymu (SC07-WX; XP0A-MR i powiązane modele XP/SC)**: Wykrywa CO i dym.
- **Czujnik zalania (SWS51)**: Wykrywa wodę w niepożądanych miejscach.
- **Higrometr-termometr (STH51, STH0A, STH0B, STH0C)**: Monitoruje temperaturę i wilgotność.
- **Czujnik drzwi (SDS0A)** i **czujnik ruchu (SMS0A)**: Widoczne, gdy X-Sense zgłasza stan.
- **Kamera (SSC0A, SSC0B)**: Udostępnia encje kamery, miniatury, URL transmisji na żywo, diagnostykę i ustawienia zgodne z aplikacją Android, gdy urządzenie i konto je obsługują.
- **Inne urządzenia stacji**: Światło, klawiatura, skrzynka pocztowa, urządzenie nasłuchowe, alarm podjazdu, inteligentny odbiornik przesyłek, pilot i dane radonu są pokazywane, gdy API zgłasza obsługiwane pola.

### Dostępne encje i akcje
Integracja tworzy encje Home Assistant tylko dla pól faktycznie obecnych w chmurze X-Sense, payloadach MQTT shadow albo API kamer zgodnych z zachowaniem aplikacji Android. W zależności od urządzenia może to obejmować:

- Czujniki binarne dla alarm, mute, end-of-life, AC-break, alarmu wody, alarmu temperatury, ładowania, ruchu, drzwi, stanu armed, warning, reminder, light, PIR i stanu keypad.
- Czujniki baterii, sygnału RF, sygnału Wi-Fi, firmware, temperatury, wilgotności, poziomu CO, szczytu CO, głośności alarmu, głośności głosu, głośności sygnału, głośności przypomnień, progów ostrzeżeń, timerów wyciszenia, czytelnych znaczników czasu, strefy czasowej i innych danych diagnostycznych.
- Przełączniki dla zapisywalnych ustawień zgłaszanych przez X-Sense, takich jak LED light, alarm enablement, continued alarm, chirp tone, reminders, PIR, sunshine/white light, await, keypad sound, camera motion detection, recording, night vision, audio, cooldown, light i doorbell controls.
- Select i number dla obsługiwanych ustawień kamery, takich jak language, recording resolution, codec, anti-flicker rate, motion sensitivity, video length, volume, alarm duration, cooldown, night threshold i doorbell ring key.
- Przyciski test, mute, fire-drill i camera wake dla modeli, w których aplikacja X-Sense udostępnia odpowiednią akcję.

Część encji jest diagnostyczna lub konfiguracyjna i tak jest grupowana w Home Assistant. Jeśli urządzenie nie zgłasza konkretnego pola albo aplikacja X-Sense oznacza funkcję jako nieobsługiwaną dla danego urządzenia/konta, odpowiednia encja nie jest tworzona. Parowanie, usuwanie, udostępnianie urządzeń, konto, płatności, aktualizacja firmware, formatowanie karty SD i inne akcje administracyjne pozostają w aplikacji X-Sense.
____________________________________________________________

## Przykłady automatyzacji
Dzięki tej integracji można tworzyć różne automatyzacje. Oto kilka przykładów:

### Przykład 1: Ostrzeżenie o temperaturze
Gdy temperatura z termometru X-Sense jest zbyt wysoka, zostaje wysłane powiadomienie:

```yaml
automation:
  - alias: "X-Sense Ostrzeżenie o temperaturze"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatura przekroczyła 30 stopni!"
```

### Przykład 2: Alarm wycieku wody
Gdy czujnik wycieku wody wykryje wodę, zostaje uruchomiony alarm:

```yaml
automation:
  - alias: "Alarm wycieku wody"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Wykryto wyciek wody!"
```

____________________________________________________________

## Potrzebujemy Twojej pomocy
Zawsze szukamy wsparcia, aby dalej rozwijać i ulepszać tę integrację. Oto kilka sposobów, w jakie możesz pomóc:

1. **Testowanie urządzeń**: Jeśli posiadasz urządzenie X-Sense, które działa z tą integracją, daj nam znać, abyśmy mogli dodać je do listy obsługiwanych urządzeń.

2. **Informacje zwrotne o nieobsługiwanych urządzeniach**: Jeśli urządzenie nie działa prawidłowo, przekaż nam informacje zwrotne, abyśmy mogli zapewnić wsparcie lub uwzględnić urządzenie w przyszłych wersjach integracji.

3. **Udostępnienie urządzeń do testów**: Najlepszym sposobem na przetestowanie nowych urządzeń jest udostępnienie ich za pomocą aplikacji X-Sense. W ten sposób możemy zapewnić obsługę jak największej liczby urządzeń.

4. **Wsparcie społeczności**: Dołącz do dyskusji w naszej społeczności. Czy to sugestie dotyczące ulepszeń, czy pomoc innym użytkownikom w konfiguracji — każde wsparcie jest mile widziane!

W celu uzyskania wsparcia i uczestniczenia w dyskusji możesz dołączyć do naszego serwera Discord lub odwiedzić forum Home Assistant:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Pełna dokumentacja referencyjna

### Konto i instalacja
- Używaj osobnego konta X-Sense dla Home Assistant.
- Z głównego konta udostępniaj tylko obsługiwane urządzenia.
- Parowanie, usuwanie, udostępnianie, firmware, konto, płatności i zarządzanie kartą SD pozostają w aplikacji X-Sense.

### Aktualizacje i użycie API
- Szybkie zmiany stanu przychodzą przez komunikaty MQTT shadow.
- Zapytania do chmury służą do logowania, wykrywania urządzeń, danych kamer i odzyskiwania stanu.
- Okresowe odpytywanie jest tylko rezerwą, gdy brakuje aktualizacji na żywo.

### Encje, kamery i diagnostyka
- Encje są tworzone tylko dla pól faktycznie raportowanych przez X-Sense.
- Encje i sterowanie kamerą są tworzone tylko wtedy, gdy API zgodne z aplikacją Android zgłasza obsługę dla danego konta i modelu.
- Jeśli brakuje wartości, najpierw porównaj ją z aplikacją X-Sense, a potem dołącz diagnostykę i odpowiednie logi Home Assistant.

## Lista kontrolna urządzeń i encji

### Główne rodziny urządzeń
- Stacja SBS50, czujniki dymu XS, czujniki CO XC, czujniki łączone SC/XP, alarmy ciepła XH, czujniki wody SWS, czujniki temperatury/wilgotności STH, czujniki drzwi SDS, czujniki ruchu SMS, kamery SSC oraz inne raportowane rodziny X-Sense są obsługiwane, gdy API udostępnia ich pola.

### Pola stanu
- Alarm, wyciszenie, bateria, sygnał RF/Wi-Fi, temperatura, wilgotność, CO, woda, ruch, drzwi, światło, przypomnienia, ostrzeżenia i czytelne znaczniki czasu pojawiają się tylko wtedy, gdy X-Sense je raportuje.

### Sterowanie i zgłoszenia
- Przełączniki, listy wyboru, liczby i przyciski są tworzone tylko dla zapisywalnych ustawień i akcji udostępnianych przez urządzenie/konto.
- Dobre zgłoszenie błędu zawiera dokładny model, wersję integracji, diagnostykę, logi i informację, czy wartość zmienia się poprawnie w aplikacji X-Sense.
