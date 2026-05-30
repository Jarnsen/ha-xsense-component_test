# ha-xsense-component_test

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

## 준비
- **Home Assistant용 두 번째 X-Sense 계정 만들기**: 같은 계정으로 앱과 Home Assistant에 동시에 안정적으로 로그인하기 어렵기 때문에 별도 계정을 권장합니다.
- **기본 계정에서 Home Assistant 계정으로 지원 장치 공유**: 관리는 기본 계정에서 계속하고, 필요한 장치만 Home Assistant 계정에 공유합니다.

## 설치 및 설정
1. Home Assistant에서 HACS를 엽니다.
2. 사용자 지정 저장소로 `https://github.com/Jarnsen/ha-xsense-component_test`를 추가합니다.
3. 통합을 다운로드하고 설치합니다.
4. Home Assistant 통합 화면에서 X-Sense 사용자 이름과 비밀번호를 입력합니다.

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
- **기타 스테이션 연결 장치**: 조명, 키패드, 우편함, listener, 진입로 알람, smart drop, 리모컨, 라돈 데이터는 API가 지원 필드를 보고할 때 표시됩니다.

## 사용 가능한 엔티티와 동작
통합은 X-Sense 클라우드, MQTT shadow 또는 앱 기반 카메라 API에 존재하는 필드에 대해서만 엔티티를 만듭니다. 이진 센서, 진단 센서, 스위치, 선택 항목, 숫자, 테스트, 음소거, 화재 훈련, 카메라 깨우기 버튼 등이 포함될 수 있습니다.

필드가 보고되지 않거나 X-Sense 앱이 해당 장치/계정에서 기능을 지원하지 않는다고 표시하면 엔티티가 생성되지 않습니다. 장치 추가/삭제/공유, 계정, 결제, 펌웨어, SD 카드 포맷 등 관리 작업은 X-Sense 앱에서 처리합니다.

____________________________________________________________

## 자동화 예시
```yaml
automation:
  - alias: "X-Sense Water Leak Alarm"
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
