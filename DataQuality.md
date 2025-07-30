# FMS 데이터 품질 요구사항 정의서

## 3. 데이터 품질 요건 정의

### 3.1 FMS 센서 데이터 구조
FMS(Factory Management System)에서 수집되는 센서 데이터는 JSON 형식이며, 다음 항목을 포함합니다:

| 필드명        | 설명                 | 예시                      |
|---------------|----------------------|---------------------------|
| `time`        | 수집 시각            | "2025-07-10T09:30:00Z"    |
| `DeviceId`    | 장비 식별자 (1~100)   | 42                        |
| `sensor1~3`   | 센서값 (온도/습도/압력) | 24.5, 60.1, 95.0          |
| `motor1~3`    | 모터 RPM             | 1200, 1000, 1500          |
| `isFail`      | 장애 여부 플래그      | false                     |
| `collected_at`| 수집된 시각(원본 기준) | "2025-07-10T09:30:05Z"    |

---

### 3.2 데이터 타입 정의 및 유효성 규칙

| 필드명     | 데이터 타입 | 필수 여부 | 유효 범위           | 처리 방식 요약             |
|------------|-------------|-----------|---------------------|----------------------------|
| `time`     | String(ISO8601) | 필수      | 파싱 가능한 형식      | `timestamp` 변환 실패 시 `CHECK` |
| `DeviceId` | Integer     | 필수      | 1~100               | 범위 벗어나면 `CHECK`        |
| `sensor1`  | Float       | 필수      | 0~100               | 범위 벗어나면 `ALERT`        |
| `sensor2`  | Float       | 필수      | 0~100               | 범위 벗어나면 `ALERT`        |
| `sensor3`  | Float       | 필수      | 0~150               | 범위 벗어나면 `ALERT`        |
| `motor1`   | Float       | NULL 허용 | 0~2000              | NULL → 0, 범위 초과 시 `ALERT` |
| `motor2`   | Float       | NULL 허용 | 0~1500              | NULL → 0, 범위 초과 시 `ALERT` |
| `motor3`   | Float       | NULL 허용 | 0~1800              | NULL → 0, 범위 초과 시 `ALERT` |
| `isFail`   | Boolean     | NULL 허용 | true/false          | NULL → false, 유효값 아니면 `CHECK` |

---

### 3.3 데이터 품질 이슈 유형

#### ✅ 완전성 문제
- `time`, `DeviceId`, `isFail` 결측 → `CHECK`
- `motor` 필드 NULL → 0으로 대체
- `isFail` 필드 NULL → false 대체

#### ✅ 정확성 문제
- `sensor`, `motor` 값 유효 범위 초과 → `ALERT`
- `time` 변환 실패 → `CHECK`

#### ✅ 일관성 문제
- 중복 데이터, 시간 역전 등은 현재 로직에서는 처리하지 않음 (추후 개선 예정)

---

### 3.4 NULL 값 처리 전략

| 대상 필드         | 처리 전략   | 설명                            |
|--------------------|-------------|---------------------------------|
| `time`, `DeviceId`, `isFail` | REJECT/FLAG | 결측 시 상태를 `CHECK`로 분류       |
| `motor1~3`          | DEFAULT     | 결측 시 0으로 설정                  |
| `isFail`           | DEFAULT     | 결측 시 false로 설정                |

---

### 3.5 이상치 탐지
- 유효 범위 초과 시 `ALERT` 처리
- 센서값(`sensor1~3`) 또는 모터값(`motor1~3`) 중 하나라도 기준을 초과하면 `ALERT`
- 추가적인 통계 기반 탐지는 적용되어 있지 않음

---

### 3.6 데이터 타입 검증 및 변환
- `time` 필드는 `timestamp`로 변환
- 변환 실패 시 `CHECK`
- 다른 필드들은 자동 형변환 시도, 실패 시 Spark에서 자동 제외될 수 있음

---

### 3.7 상태 분류 및 저장 정책

| 상태     | 조건                                                                 | 저장 위치 (HDFS)                        |
|----------|----------------------------------------------------------------------|-----------------------------------------|
| `NORMAL` | 모든 필드 유효 + `isFail == false`                                   | `/fms/processed/normal/`               |
| `ALERT`  | 센서 또는 모터값 범위 초과 OR `isFail == true`                       | `/fms/processed/alert/`                |
| `CHECK`  | 핵심 필드(`DeviceId`, `time`, `isFail`) 누락 또는 타입 오류           | `/fms/processed/check/`                |

※ 보관 기간 정책은 현재 적용되지 않음 (향후 별도 정의 예정)

---

### 3.8 실시간 품질 점검
- `/fms/processed/{status}/year=YYYY/month=MM/day=DD/hour=HH` 기준으로 분기 저장
- `fms_processing_result.py` 스크립트를 통해 상태별 파일 존재 및 로드 확인 가능

```bash
python3 /df/spark-processor/fms_prosessing_result.py <YYYYMMDDHH>
```
