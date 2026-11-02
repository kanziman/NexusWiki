## ADDED Requirements

### Requirement: 분쟁 근거 표시
시스템은 분쟁 중인 위키 페이지를 근거로 쓸 때 모델 컨텍스트에 분쟁 중임을 SHALL 표시하고, `citations`에 해당 별칭을 담아 답변 화면이 경고를 표시하게 한다.

#### Scenario: 분쟁 페이지가 근거에 있다
- **WHEN** Ask 근거에 `disputed` 위키 페이지가 있다
- **THEN** 프롬프트의 그 블록에 분쟁 표시가 있고, `citations.disputed_aliases`에 별칭이 있으며, 화면에 경고가 표시된다

#### Scenario: 분쟁 페이지가 없다
- **WHEN** 근거에 분쟁 페이지가 없다
- **THEN** 프롬프트에 분쟁 표시가 없고 경고도 없다
