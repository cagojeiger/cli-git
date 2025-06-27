# 아키텍처 설계

## 개요

cli-git은 함수형 프로그래밍 원칙을 핵심으로 설계되었으며, 다음을 강조합니다:
- 부작용이 없는 순수 함수
- 복잡한 클래스 계층 구조 대신 함수 합성
- 불변성과 예측 가능성
- I/O와 비즈니스 로직의 명확한 분리

## 핵심 컴포넌트

### 1. CLI 레이어 (`src/cli_git/cli.py`)

진입점은 함수형 패턴과 함께 Typer를 사용하여 선언적 CLI를 정의합니다:

```python
# 메시지 생성을 위한 순수 함수
create_version_message(version: str) -> str

# 표시를 위한 고차 함수
display_message(message_creator: Callable, version: str) -> None

# 부분 적용을 통한 함수 합성
display_version = partial(display_message, create_version_message)
```

### 2. 명령어 구조 (`src/cli_git/commands/`)

명령어는 모듈로 구성되며, 각각 순수 함수를 노출합니다:
- 입력 검증 함수
- 비즈니스 로직 함수 (순수)
- 출력 포맷팅 함수
- I/O 래퍼 함수

### 3. 버전 관리

패키지 메타데이터에서 동적 버전 로딩:
```python
from importlib.metadata import version
__version__ = version("cli-git")
```

## 설계 패턴

### 함수 합성
상속 대신 동작을 합성합니다:
```python
pipe(
    validate_input,
    transform_data,
    format_output,
    display_result
)(user_input)
```

### 부분 적용
일반 함수에서 특수한 함수를 생성합니다:
```python
version_option = partial(
    typer.Option,
    "--version",
    "-v",
    callback=version_callback,
    is_eager=True
)
```

### 관심사의 분리
- **순수 핵심**: 부작용이 없는 비즈니스 로직
- **명령형 셸**: 경계에서의 I/O 작업
- **함수형 변환**: map, filter, reduce를 사용한 데이터 파이프라인

## 테스트 전략

### 테스트 주도 개발
1. 원하는 동작을 설명하는 테스트 작성
2. 통과하기 위한 최소한의 코드 구현
3. 테스트를 유지하면서 리팩토링

### 테스트 구성
- `tests/test_*.py` - 기능별 테스트
- `tests/conftest.py` - 공유 픽스처
- 순수 함수 테스트에 집중 (쉬움)
- 필요시 I/O 작업 모킹

## 오류 처리

함수형 오류 처리 사용:
- 반환 타입 (Optional, Union)
- 실패할 수 있는 작업을 위한 Result 타입
- 순수 함수에서는 예외 없음
- I/O 경계에서만 예외

## 향후 확장성

### 명령어 추가
1. `commands/`에 새 모듈 생성
2. 로직을 위한 순수 함수 정의
3. Typer 데코레이터로 I/O 래퍼 추가
4. 메인 CLI 앱에 등록

### 플러그인 시스템 (향후)
- 동적 명령어 로딩
- 함수 레지스트리 패턴
- 합성 기반 확장

## 성능 고려사항

- 유익한 곳에서 지연 평가
- 비용이 큰 순수 함수를 위한 메모이제이션
- 동시 작업을 위한 비동기 I/O
- 대용량 데이터 스트림을 위한 제너레이터 함수
