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
생성되는 엔티티는 X-Sense 클라우드 또는 MQTT shadow가 보고하는 필드에 따라 달라집니다. SBS50 베이스 스테이션, XS/SC/XP/XC 계열 연기 및 일산화탄소 장치, XH 열 감지기, SWS 누수 감지기, STH 온습도계, SDS 문 센서, SMS 모션 센서, 조명, 키패드, 우편함, 진입로 알람 및 기타 지원 필드를 보고하는 장치를 포함합니다.

## 사용 가능한 엔티티와 동작
- 알람, 음소거, 수명 종료, AC 오류, 누수, 온도 알람, 충전, 모션, 문, 경계, 알림, 조명 및 진단 이진 센서.
- 배터리, RF 신호, Wi-Fi 신호, 펌웨어, 온도, 습도, CO 값, 볼륨, 읽기 쉬운 타임스탬프, 일련번호, MAC 주소 및 기타 진단 센서.
- 장치가 지원하는 경우 LED 조명, 알람, 알림, PIR, 햇빛, 대기 및 키패드 소리 설정 스위치.
- 지원 모델의 테스트, 음소거 및 화재 훈련 버튼.

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
