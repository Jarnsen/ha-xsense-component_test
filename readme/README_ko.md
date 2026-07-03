# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 개요
이 Home Assistant 통합은 X-Sense 장치를 스마트 홈 시스템에서 사용할 수 있게 해 줍니다. [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense)의 원래 코드를 기반으로 하며, 그의 허가와 협력 아래 배포됩니다.

공식 Home Assistant 통합이 제공되기 전까지 이 HACS 통합은 새 기능 추가와 문제 수정을 위해 계속 업데이트됩니다.

## 기능
- 여러 X-Sense 장치를 Home Assistant에 통합합니다.
- X-Sense 센서 데이터를 기반으로 자동화를 만들 수 있습니다.
- X-Sense 계정에서 보고되는 경우 베이스 스테이션, 연기 감지기, 일산화탄소 감지기, 열 감지기, 누수 감지기, 온습도계, 문 센서, 모션 센서, 조명, 키패드, 우편함 센서, 리스너 장치를 지원합니다.
- X-Sense MQTT shadow를 통한 실시간 업데이트와 주기적 클라우드 폴링 백업을 사용합니다.
- HACS로 쉽게 설치할 수 있습니다.

## 요구 사항
- 정상 작동하는 Home Assistant 서버.
- 지원되는 장치가 있는 X-Sense 계정.
- Home Assistant에 HACS가 설치되어 있어야 합니다.

## 사용 방법 동영상
설치와 설정 과정을 자세히 보려면 다음 동영상을 참고할 수 있습니다:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## 준비
- **Home Assistant용 두 번째 X-Sense 계정 만들기**: 같은 계정으로 앱과 Home Assistant에 동시에 안정적으로 로그인하기 어렵기 때문에 별도 계정을 권장합니다.
- **기본 계정에서 Home Assistant 계정으로 지원 장치 공유**: 관리는 기본 계정에서 계속하고, 필요한 장치만 Home Assistant 계정에 공유합니다.

## HACS를 통한 설치
1. **Home Assistant에서 HACS 열기**:
  HACS는 사용자 지정 통합을 쉽게 설치할 수 있게 해 주는 Home Assistant 확장입니다.

2. **사용자 지정 저장소로 이동**:
  HACS 대시보드의 설정에서 저장소를 사용자 지정 소스로 추가합니다.

3. **저장소 추가**:
  저장소 URL `https://github.com/Jarnsen/ha-xsense-component_test` 를 입력합니다.

4. **통합 다운로드 및 설치**:
  HACS에서 통합을 찾아 다운로드하고 설치합니다. 설치 후 Home Assistant UI에서 설정할 수 있습니다.

____________________________________________________________

## 설정
설치 후 통합을 올바르게 사용하려면 기본 설정이 필요합니다:
- **사용자 이름과 비밀번호**: 새로 만든 X-Sense 계정의 로그인 정보를 사용해 연결합니다.
- **장치 개요**: 설정이 완료되면 공유된 장치가 Home Assistant에 표시되고 자동화에 사용할 수 있습니다.

## Home Assistant에서 보기
설치와 설정이 끝나면 통합이 Home Assistant에 표시됩니다. 장치는 대시보드에서 사용할 수 있으며 자동화, 알림 및 기타 용도로 사용할 수 있습니다.


## 스크린샷으로 보는 자세한 설정

1. Home Assistant용 별도 X-Sense 계정을 만들고 기본 계정에서는 지원되는 장치만 공유하세요.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. HACS에서 `https://github.com/Jarnsen/ha-xsense-component_test`를 사용자 지정 저장소로 추가하세요.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. 통합을 다운로드하고 설치한 뒤 Home Assistant를 다시 시작하고 새 X-Sense 계정으로 설정하세요.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. 설정이 완료되면 공유된 장치가 Home Assistant 장치 페이지에 표시됩니다.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. 페어링, 제거, 펌웨어, 결제, SD 카드, 계정 관리는 X-Sense 앱에서 계속 관리합니다.

## 지원 장치
이 통합은 여러 X-Sense 장치를 지원합니다. 생성되는 엔티티는 장치와 계정이 보고하는 데이터 필드에 따라 달라집니다. 확인된 장치군과 모델은 다음과 같습니다.
- **베이스 스테이션 (SBS50)**: X-Sense 장치의 중앙 허브입니다.
- **열 감지기 (XH02-M)**: 비정상적으로 높은 온도를 감지합니다.
- **일산화탄소 감지기 (XC01-M; XC04-WX)**: 위험한 CO 농도를 감지합니다.
- **연기 감지기 (XS01-M; XS01-WX; XS03-WX; XS0B-MR 및 관련 RF/iR 모델)**: 연기를 조기에 감지합니다.
- **CO/연기 복합 감지기 (SC07-WX; XP0A-MR 및 관련 XP/SC 모델)**: CO와 연기를 감지합니다.
- **누수 감지기 (SWS51)**: 원치 않는 위치의 물을 감지합니다.
- **온습도계 (STH51, STH0A, STH0B, STH0C)**: 온도와 습도를 모니터링합니다.
- **문 센서 (SDS0A)** 및 **모션 센서 (SMS0A)**: X-Sense가 상태를 제공할 때 표시됩니다.
- **카메라 (SSC0A, SSC0B)**: 장치와 계정이 지원하는 경우 카메라 엔티티, 썸네일, 라이브 스트림 URL, 진단, Android 앱 기반 설정을 제공합니다.
- **기타 스테이션 연결 장치**: 조명, 키패드, 우편함, 청취 장치, 진입로 알람, 스마트 드롭, 리모컨, 라돈 데이터는 API가 지원 필드를 보고할 때 표시됩니다.

### 사용 가능한 엔티티와 동작
이 통합은 X-Sense 클라우드, MQTT shadow payload 또는 Android 앱과 맞춘 카메라 API에 실제로 존재하는 필드에 대해서만 Home Assistant 엔티티를 만듭니다. 장치에 따라 다음을 포함할 수 있습니다:

- 알람, 음소거, 수명 종료, AC 전원 차단, 누수 알람, 온도 알람, 충전, 움직임, 문, 경계 상태, 경고, 리마인더, 조명, PIR, 키패드 상태용 이진 센서.
- 배터리, RF 신호, Wi-Fi 신호, 펌웨어, 온도, 습도, CO 수치, CO 최고치, 알람/음성/차임/리마인더 볼륨, 경고 임계값, 음소거 타이머, 읽기 쉬운 타임스탬프, 시간대 및 기타 진단 센서.
- LED 조명, 알람 활성화, 계속 알람, 차임 톤, 리마인더, PIR, 햇빛/화이트라이트 관련 설정, 대기 상태, 키패드 소리, 카메라 움직임 감지, 녹화, 야간 시야, 오디오, 쿨다운, 조명, 도어벨 제어처럼 X-Sense가 보고하는 쓰기 가능한 설정용 스위치.
- 언어, 녹화 해상도, 코덱, 플리커 방지 주파수, 움직임 감도, 비디오 길이, 볼륨, 알람 지속 시간, 쿨다운, 야간 임계값, 도어벨 링 키 같은 지원되는 카메라 설정용 선택 항목과 숫자 엔티티.
- X-Sense 앱이 해당 모델에 동작을 제공하는 경우 테스트, 음소거, 화재 훈련, 카메라 깨우기 버튼.

일부 엔티티는 진단 또는 설정 관련 엔티티로 Home Assistant에서 해당 분류로 표시됩니다. 장치가 특정 필드를 보고하지 않거나 X-Sense 앱이 해당 장치/계정에서 기능을 지원하지 않는다고 표시하면 대응 엔티티는 생성되지 않습니다. 장치 추가, 제거, 공유, 계정, 결제, 펌웨어 업데이트, SD 카드 포맷 및 기타 관리 작업은 X-Sense 앱에 남아 있습니다.
____________________________________________________________

## 자동화 예시
이 통합을 사용하면 다양한 자동화를 만들 수 있습니다. 예시는 다음과 같습니다:

### 예시 1: 온도 경고
X-Sense 온도계의 온도가 너무 높을 때 알림을 보냅니다:

```yaml
automation:
  - alias: "X-Sense Temperature Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "온도가 30도를 초과했습니다!"
```

### 예시 2: 누수 알람
누수 감지기가 물을 감지하면 알림을 보냅니다:

```yaml
automation:
  - alias: "Water Leak Alarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "누수가 감지되었습니다!"
```

## 도움이 필요합니다
테스트되지 않은 X-Sense 장치가 있다면 GitHub, Discord 또는 Home Assistant 포럼에 피드백을 남겨 주세요.

## 전체 참고 자료

### 계정 및 설치
- Home Assistant에는 별도의 X-Sense 계정을 사용하세요.
- 기본 계정에서는 지원되는 장치만 공유하세요.
- 장치 추가, 제거, 공유, 결제, firmware, 계정 관리는 X-Sense 앱에서 계속 처리합니다.
- 앱과 Home Assistant가 서로 로그아웃된다면 같은 계정을 쓰는지 확인하세요.

### 업데이트와 API 사용
- 빠른 상태 변경은 MQTT shadow 메시지로 수신합니다.
- 클라우드 요청은 로그인, 장치 로드, 상태 갱신에만 신중하게 사용합니다.
- MQTT 메시지가 없을 때만 주기적 polling이 보조 역할을 합니다.
- 매 업데이트마다 전체 장치 검색을 반복하지 않아야 합니다.

### 엔티티, 카메라, 문제 해결
- X-Sense가 실제로 보고하는 필드에 대해서만 엔티티를 만듭니다.
- 진단 값은 Home Assistant에서 diagnostic으로 분류됩니다.
- 지원 카메라는 카메라 엔티티, thumbnail, live stream, 상태, 지원 설정을 제공할 수 있습니다.
- 문제 보고 시 모델, 통합 버전, diagnostics, logs, 앱에서 값이 바뀌는지 여부를 포함하세요.

## 장치 및 엔티티 체크리스트

### 핵심 장치군
- SBS50: 베이스 스테이션 및 스테이션 수준 상태.
- XS01-WX: 별도 하위 장치가 없는 계정을 포함한 Wi-Fi 연기 경보기.
- XS01-M, XS03-WX, XS0B-MR: 연기 경보기 장치군.
- XC01-M, XC04-WX: CO 경보기 장치군.
- SC07-WX, XP0A-MR: 연기 및 CO 복합 장치군.
- XH02-M: 열 경보기 장치군.
- SWS51: 누수 감지기 장치군.
- STH51, STH0A, STH0B, STH0C: 온도 및 습도.
- SDS0A: 문 센서.
- SMS0A: 동작 센서.
- SSC0A, SSC0B: 지원되는 카메라.

### 상태 필드
- X-Sense가 알람 필드를 보고하면 알람 상태가 표시됩니다.
- X-Sense가 음소거 필드를 보고하면 음소거 상태가 표시됩니다.
- 장치가 배터리 데이터를 보고하면 배터리 상태가 표시됩니다.
- RF 및 Wi-Fi 신호는 장치가 보고할 때 표시됩니다.
- X-Sense의 압축 시간 값은 읽기 쉬운 Home Assistant 센서로 변환됩니다.

### 제어 및 보고
- 스위치는 X-Sense가 보고한 쓰기 가능한 설정에 대해서만 생성됩니다.
- 버튼은 앱에서 지원하는 동작에 대해서만 생성됩니다.
- 카메라 제어는 API가 사용 가능하다고 표시할 때만 생성됩니다.
- 문제 보고에는 정확한 모델, 통합 버전, diagnostics, logs, X-Sense 앱에서 값이 바뀌는지 여부가 필요합니다.

____________________________________________________________

## 카메라 라이브 보기 및 AI 알림
가장 쉬운 방법은 포함된 blueprint를 사용하는 것입니다. 아래 버튼으로 가져온 뒤 카메라 `Motion` 이벤트 엔티티 또는 구독 카메라에서 사용할 수 있는 경우 `AI Detection`을 선택하고, 필요하면 알림 동작을 조정하세요.

Motion 이벤트에 X-Sense 재생 메타데이터가 포함되면 통합은 즉시 클립 캐시를 시도합니다. 캐시된 파일이 준비되면 알림은 동영상 재생에 `recording_media_url`을 사용하고, 그렇지 않으면 `recording_url`로 Home Assistant의 X-Sense Recordings 뷰어를 엽니다. Recording media sync는 최근 클립을 백그라운드에서 준비할 수 있습니다.

[![blueprint 가져오기](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion 및 AI Detection은 켜짐/꺼짐 상태가 아니라 일회성 이벤트입니다. 수동 자동화에서는 Home Assistant의 `event.received` 트리거를 카메라 `Motion` 또는 `AI Detection` 엔티티와 함께 사용하세요. 구독 AI Detection을 `person`, `pet`, `vehicle`, `package`, `other`, `ai_detection` 같은 유형으로 좁힐 때만 `event_type`을 사용하세요.

자동화 예시:

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
