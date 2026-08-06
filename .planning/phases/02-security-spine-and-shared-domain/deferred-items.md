## 02-02에서 발견 (범위 밖)

- **`README.md:16`의 `uv sync --frozen`이 워크스페이스 멤버를 설치하지 않는다.** 루트가 `package = false`이고 의존성이 없어 `api`·`worker`·`nexuswiki-core`가 venv에서 제거된다. `Dockerfile:18`은 이미 `--all-packages`를 쓴다. ROADMAP 성공기준 3("저장소를 새로 클론한 상태에서 `uv sync` 한 번으로 세 패키지가 빌드된다")과 어긋난다. 발견: 02-02 Task 1.
