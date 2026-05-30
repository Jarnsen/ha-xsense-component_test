# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Przegląd
Ta integracja z Home Assistant umożliwia korzystanie z urządzeń Xsense w systemie inteligentnego domu. Została stworzona na podstawie oryginalnego kodu [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) i opublikowana za jego zgodą oraz we współpracy z nim.

Do czasu, gdy dostępna będzie oficjalna integracja Home Assistant od Theo, będzie używana ta integracja HACS, która jest regularnie aktualizowana, aby dodawać nowe funkcje i rozwiązywać istniejące problemy. Ta integracja umożliwia użytkownikom łatwą integrację urządzeń Xsense z Home Assistant oraz ich używanie do różnych automatyzacji i monitorowania.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funkcje
- Integracja różnych urządzeń Xsense z Home Assistant.
- Obsługa automatyzacji na podstawie danych z czujników Xsense.
- Obsługa stacji bazowych, czujników dymu, czujników tlenku węgla, alarmów ciepła, czujników zalania, higrometrów, czujników drzwi, czujników ruchu, świateł, klawiatur, skrzynek pocztowych, listenerów, kamer i innych obsługiwanych urządzeń, gdy są dostępne na koncie X-Sense.
- Prosta konfiguracja przez HACS (Home Assistant Community Store).

## Wymagania
- Działający serwer Home Assistant (zalecana najnowsza wersja).
- Konto Xsense z obsługiwanymi urządzeniami.
- HACS musi być zainstalowany w Home Assistant, aby umożliwić instalację tej integracji.

## Wideo instruktażowe
Aby uzyskać szczegółowy przewodnik dotyczący instalacji i konfiguracji integracji, możesz obejrzeć poniższe wideo:

[![Integracja X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Przygotowanie
Przed zainstalowaniem integracji należy wykonać kilka przygotowań:

- **Utwórz drugie konto w aplikacji X-Sense (do użytku z Home Assistant)**: Ponieważ nie jest możliwe jednoczesne zalogowanie się do aplikacji i do Home Assistant za pomocą tego samego konta, zalecamy użycie osobnego konta do Home Assistant. Dzięki temu unikasz ciągłego wylogowywania się z aplikacji lub Home Assistant. Dodatkowe konto umożliwia płynną integrację i użytkowanie bez przerw wynikających z częstego logowania i wylogowywania.

- **Udostępnij obsługiwane urządzenia z głównego konta do konta Home Assistant**: Użyj aplikacji X-Sense, aby udostępnić **tylko obsługiwane urządzenia** nowo utworzonemu kontu. W ten sposób możesz bezproblemowo korzystać z integracji w Home Assistant, kontynuując zarządzanie urządzeniami z poziomu głównego konta.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Instalacja przez HACS
1. **Otwórz HACS w Home Assistant**:
   HACS to ważne rozszerzenie dla Home Assistant, które umożliwia łatwą instalację niestandardowych integracji.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Przejdź do niestandardowych repozytoriów**:
   Przejdź do ustawień w panelu HACS i dodaj to repozytorium jako źródło niestandardowe.

3. **Dodaj repozytorium**:
   Wprowadź URL repozytorium: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Pobierz i zainstaluj integrację**:
   Wyszukaj integrację w HACS, pobierz ją i zainstaluj. Po zakończeniu instalacji konfigurację można przeprowadzić za pomocą interfejsu Home Assistant.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Konfiguracja
Po zainstalowaniu wymagane jest podstawowe skonfigurowanie, aby prawidłowo ustawić integrację:
- **Nazwa użytkownika i hasło**: Użyj danych logowania do nowo utworzonego konta X-Sense, aby nawiązać połączenie。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Przegląd urządzeń**: Po pomyślnym skonfigurowaniu, udostępnione urządzenia będą dostępne w Home Assistant i mogą być używane do automatyzacji。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Widok w Home Assistant
Po pomyślnej instalacji i konfiguracji integracja będzie widoczna w Home Assistant. Urządzenia będą widoczne na pulpicie nawigacyjnym i mogą być używane do automatyzacji, powiadomień i innych zastosowań。


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
- **Inne urządzenia stacji**: Światło, klawiatura, skrzynka pocztowa, listener, alarm podjazdu, smart drop, pilot i dane radonu są pokazywane, gdy API zgłasza obsługiwane pola.

### Dostępne encje i akcje
Integracja tworzy encje tylko dla pól obecnych w chmurze X-Sense, payloadach MQTT shadow lub API kamery wspieranym przez aplikację. Może to obejmować czujniki binarne, diagnostyczne, przełączniki, listy wyboru, liczby i przyciski dla obsługiwanych funkcji, takich jak test, wyciszenie, próba pożarowa i wybudzenie kamery.

Jeśli pole nie jest zgłaszane albo aplikacja X-Sense oznacza funkcję jako nieobsługiwaną dla danego urządzenia/konta, encja nie zostanie utworzona. Parowanie, usuwanie, udostępnianie, konto, płatności, firmware, formatowanie karty SD i inne działania administracyjne pozostają w aplikacji X-Sense.

____________________________________________________________

## Przykłady automatyzacji
Dzięki tej integracji można tworzyć różne automatyzacje。Oto kilka przykładów：

### Przykład 1：Ostrzeżenie o temperaturze
Gdy temperatura z termometru Xsense jest zbyt wysoka, zostaje wysłane powiadomienie：

```yaml
automation：
  - alias："Xsense Ostrzeżenie o temperaturze"
    trigger：
      platform：numeric_state
      entity_id：sensor.xsense_temperature
      above：30
    action：
      service：notify.notify
      data：
        message："Temperatura przekroczyła 30 stopni！"
```

### Przykład 2：Alarm wycieku wody
Gdy czujnik wycieku wody wykryje wodę, zostaje uruchomiony alarm：

```yaml
automation：
  - alias："Alarm wycieku wody"
    trigger：
      platform：state
      entity_id：binary_sensor.xsense_waterleak
      to："on"
    action：
      service：notify.notify
      data：
        message："Wykryto wyciek wody！"
```

____________________________________________________________

## Potrzebujemy Twojej pomocy
Zawsze szukamy wsparcia, aby dalej rozwijać i ulepszać tę integrację。Oto kilka sposobów, w jakie możesz pomóc：

1. **Testowanie urządzeń**：Jeśli posiadasz urządzenie Xsense, które działa z tą integracją, daj nam znać, abyśmy mogli dodać je do listy obsługiwanych urządzeń。

2. **Informacje zwrotne o nieobsługiwanych urządzeniach**：Jeśli urządzenie nie działa prawidłowo, przekaż nam informacje zwrotne, abyśmy mogli zapewnić wsparcie lub uwzględnić urządzenie w przyszłych wersjach integracji。

3. **Udostępnienie urządzeń do testów**：Najlepszym sposobem na przetestowanie nowych urządzeń jest udostępnienie ich za pomocą aplikacji Xsense。W ten sposób możemy zapewnić obsługę jak największej liczby urządzeń。

4. **Wsparcie społeczności**：Dołącz do dyskusji w naszej społeczności。Czy to sugestie dotyczące ulepszeń, czy pomoc innym użytkownikom w konfiguracji — każde wsparcie jest mile widziane！

W celu uzyskania wsparcia i uczestniczenia w dyskusji możesz dołączyć do naszego serwera Discord lub odwiedzić forum Home Assistant：

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
