# GitHub에서 실행하는 방법

이 문서는 GitHub에서 Battery Air Cooling Simulator를 실행하는 다양한 방법을 설명합니다.

---

## 🚀 방법 1: GitHub Codespaces (추천)

가장 쉽고 빠른 방법입니다. 브라우저에서 바로 실행할 수 있습니다.

### 단계:

1. **GitHub 저장소 접속**
   ```
   https://github.com/tutu9599-afk/-1
   ```

2. **Codespaces 시작**
   - 초록색 `Code` 버튼 클릭
   - `Codespaces` 탭 선택
   - `Create codespace on main` 클릭
   - 몇 분 기다리면 브라우저에서 VS Code가 자동으로 열립니다

3. **의존성 설치** (처음 한 번만)
   
   터미널에서 실행:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **시뮬레이션 실행**
   
   ```bash
   # 설정 검증
   battery-aircooling validate --config examples/study_rib_sweep.yaml
   
   # 단일 시뮬레이션 실행
   battery-aircooling run --config examples/study_rib_sweep.yaml
   
   # 파라미터 스윕 실행
   battery-aircooling sweep --config examples/study_rib_sweep.yaml
   ```

5. **결과 확인**
   ```bash
   # 요약 보기
   cat results/summary.txt
   
   # CSV 결과 보기
   cat results/sweep_ribs_height.csv
   
   # 그래프는 results/figs/ 폴더에서 확인
   ls results/figs/
   ```

---

## 🤖 방법 2: GitHub Actions (자동 실행)

코드를 push하면 자동으로 시뮬레이션이 실행됩니다.

### 자동 실행되는 경우:
- `main` 브랜치에 push할 때
- Pull Request를 만들 때
- 수동으로 Actions 탭에서 실행할 때

### 수동 실행 방법:

1. **GitHub 저장소의 `Actions` 탭으로 이동**

2. **왼쪽에서 워크플로우 선택:**
   - `Battery Cooling Simulation` - 단일 시뮬레이션
   - `Parameter Sweep Study` - 파라미터 스윕

3. **`Run workflow` 버튼 클릭**

4. **설정 선택 (Parameter Sweep의 경우)**
   - Configuration file 선택
   - `Run workflow` 클릭

5. **결과 다운로드**
   - 워크플로우 실행이 완료되면 (초록색 체크 표시)
   - 실행 페이지로 이동
   - 하단 `Artifacts` 섹션에서 결과 다운로드:
     - `simulation-results` - 시뮬레이션 결과 파일
     - `sweep-results` - 파라미터 스윕 결과
     - `sweep-summary` - 요약 마크다운 파일

### 결과 보존 기간:
- 단일 시뮬레이션: 30일
- 파라미터 스윕: 90일

---

## 💻 방법 3: 로컬에서 Clone해서 실행

자신의 컴퓨터에서 실행하는 방법입니다.

### 요구사항:
- Python 3.9 이상
- Git

### 단계:

1. **저장소 Clone**
   ```bash
   git clone https://github.com/tutu9599-afk/-1.git
   cd -1
   ```

2. **가상환경 생성 (추천)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **실행**
   ```bash
   # 예제 실행
   battery-aircooling run --config examples/study_rib_sweep.yaml
   
   # 파라미터 스윕
   battery-aircooling sweep --config examples/study_rib_sweep.yaml
   ```

---

## 📓 방법 4: Jupyter Notebook으로 실행

인터랙티브하게 탐색하고 싶다면 노트북을 사용하세요.

### Codespaces에서:

1. Codespaces 실행 (위 방법 1 참조)

2. 의존성 설치
   ```bash
   pip install -r requirements.txt
   pip install -e .
   pip install jupyter
   ```

3. Jupyter 시작
   ```bash
   jupyter notebook examples/notebook_demo.ipynb
   ```

4. 브라우저에서 자동으로 노트북이 열립니다

5. 셀을 하나씩 실행하면서 결과 확인

### Google Colab에서:

1. **노트북 파일 업로드**
   - Google Colab (https://colab.research.google.com/) 접속
   - `examples/notebook_demo.ipynb` 업로드

2. **첫 번째 셀에 설치 코드 추가**
   ```python
   !pip install git+https://github.com/tutu9599-afk/-1.git
   ```

3. **셀 실행**

---

## 🔧 설정 파일 수정하기

자신만의 시뮬레이션을 실행하려면:

### 1. 설정 파일 복사
```bash
cp examples/study_rib_sweep.yaml my_config.yaml
```

### 2. YAML 파일 편집
```yaml
# 주요 파라미터 수정
air:
  mdot: 0.05  # 유량 변경

cells:
  q_gen: 15.0  # 발열량 변경

ribs:
  height: 0.003  # 리브 높이 변경
  pitch: 0.020   # 리브 피치 변경
  type: "rect"   # 리브 형상: rect, tri, semi, dimple

# 스윕 파라미터
sweep:
  - path: "ribs.height"
    values: [0.001, 0.002, 0.003, 0.004, 0.005]
```

### 3. 수정한 설정으로 실행
```bash
battery-aircooling run --config my_config.yaml
```

---

## 📊 결과 분석

### 생성되는 파일:

```
results/
├── summary.txt                    # 텍스트 요약
├── metrics.json                   # 성능 지표 JSON
├── best_config.json               # 최적 설정
├── sweep_ribs_height.csv          # 스윕 결과 CSV
└── figs/                          # 그래프
    ├── temperature_distribution.png
    ├── channel_flow_distribution.png
    └── sweep_ribs_height.png
```

### CSV 데이터 분석:

```bash
# 최고 온도가 가장 낮은 설정 찾기
cat results/sweep_ribs_height.csv | sort -t',' -k2 -n | head -1

# Python으로 분석
python
>>> import pandas as pd
>>> df = pd.read_csv('results/sweep_ribs_height.csv')
>>> print(df.describe())
>>> best_idx = df['objective_score'].idxmin()
>>> print(df.loc[best_idx])
```

---

## ❓ 문제 해결

### "command not found: battery-aircooling"
```bash
# 패키지가 설치되지 않았습니다
pip install -e .
```

### "ModuleNotFoundError"
```bash
# 의존성이 설치되지 않았습니다
pip install -r requirements.txt
```

### "ValidationError"
```bash
# YAML 설정 파일에 오류가 있습니다
battery-aircooling validate --config your_config.yaml
```

### CadQuery 관련 오류
```bash
# CadQuery는 선택 사항입니다. ROM 모드는 CadQuery 없이도 작동합니다
# CFD 모드만 CadQuery가 필요합니다
```

---

## 🎯 빠른 시작 체크리스트

1. ✅ GitHub Codespaces 시작
2. ✅ `pip install -r requirements.txt && pip install -e .`
3. ✅ `battery-aircooling validate --config examples/study_rib_sweep.yaml`
4. ✅ `battery-aircooling run --config examples/study_rib_sweep.yaml`
5. ✅ `cat results/summary.txt`

---

## 📚 추가 자료

- **README.md**: 상세한 기술 문서
- **examples/notebook_demo.ipynb**: 인터랙티브 튜토리얼
- **tests/**: 테스트 코드 예제

---

## 💡 팁

- **빠른 테스트**: 예제 YAML의 `max_iter: 50`으로 줄이면 빠르게 테스트 가능
- **플롯 보기**: Codespaces에서 이미지 파일을 클릭하면 미리보기 가능
- **병렬 실행**: 여러 Codespaces를 동시에 열어서 다른 설정 테스트 가능
- **결과 백업**: 중요한 결과는 GitHub에 커밋하거나 Artifacts로 다운로드

---

**즐거운 시뮬레이션 되세요! 🚀**
