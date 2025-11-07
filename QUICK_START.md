# ⚡ 빠른 시작 가이드

## 🌐 GitHub에서 바로 실행하기 (가장 쉬움!)

### 1️⃣ GitHub Codespaces 사용 (추천)

1. **저장소로 이동**: https://github.com/tutu9599-afk/-1

2. **초록색 `Code` 버튼 클릭**

3. **`Codespaces` 탭 선택**

4. **`Create codespace on main` 클릭**

5. **브라우저에서 VS Code가 자동으로 열립니다** (1-2분 소요)

6. **터미널에서 실행** (화면 하단에 터미널이 보임):

   ```bash
   # 의존성 설치 (처음 한 번만)
   pip install -r requirements.txt
   pip install -e .
   
   # 시뮬레이션 실행
   battery-aircooling run --config examples/study_rib_sweep.yaml
   
   # 결과 확인
   cat results/summary.txt
   ```

**끝! 이게 전부입니다! 🎉**

---

## 🚀 다른 실행 방법들

### 파라미터 스윕 (여러 조건 비교)

```bash
battery-aircooling sweep --config examples/study_rib_sweep.yaml
```

결과 파일:
- `results/sweep_ribs_height.csv` - 모든 결과 데이터
- `results/best_config.json` - 최적 설정
- `results/figs/` - 그래프들

### 리브 타입 비교

```bash
battery-aircooling sweep --config examples/compare_rib_types.yaml
```

4가지 리브 형상(rect, tri, semi, dimple) 성능 비교!

### Jupyter 노트북 (인터랙티브)

```bash
pip install jupyter
jupyter notebook examples/notebook_demo.ipynb
```

---

## 📊 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `battery-aircooling validate --config FILE` | 설정 파일 검증 |
| `battery-aircooling run --config FILE` | 단일 시뮬레이션 |
| `battery-aircooling sweep --config FILE` | 파라미터 스윕 |
| `battery-aircooling report RESULTS_DIR` | 결과 리포트 생성 |

---

## 🎯 내 설정으로 실행하기

### 1. 설정 파일 복사
```bash
cp examples/study_rib_sweep.yaml my_simulation.yaml
```

### 2. 파일 편집 (주요 파라미터만)

```yaml
air:
  mdot: 0.05          # 유량 [kg/s]

cells:
  n_rows: 4           # 셀 행 개수
  n_cols: 8           # 셀 열 개수
  q_gen: 15.0         # 셀 발열량 [W]

ribs:
  type: "rect"        # rect, tri, semi, dimple
  height: 0.003       # 리브 높이 [m]
  pitch: 0.020        # 리브 간격 [m]

# 파라미터 스윕
sweep:
  - path: "ribs.height"
    values: [0.001, 0.002, 0.003, 0.004, 0.005]
```

### 3. 실행
```bash
battery-aircooling sweep --config my_simulation.yaml
```

---

## 📈 결과 보는 법

### 터미널에서
```bash
# 요약 보기
cat results/summary.txt

# 최적 설정 보기
cat results/best_config.json

# CSV 데이터 확인
head results/sweep_ribs_height.csv
```

### 그래프 보기 (Codespaces)
1. 왼쪽 Explorer에서 `results/figs/` 폴더 열기
2. PNG 파일 클릭하면 미리보기

### Python으로 분석
```python
import pandas as pd
df = pd.read_csv('results/sweep_ribs_height.csv')
print(df.describe())
```

---

## ❓ 문제 해결

### "command not found"
```bash
pip install -e .
```

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### 설정 오류
```bash
battery-aircooling validate --config your_file.yaml
```

---

## 💡 유용한 팁

- **빠른 테스트**: YAML에서 `max_iter: 50`으로 줄이기
- **여러 시나리오**: 여러 Codespaces 동시 실행 가능
- **결과 저장**: 중요한 결과는 Git에 커밋하거나 다운로드

---

## 📚 더 자세한 정보

- **GITHUB_USAGE.md**: GitHub 실행 방법 상세 가이드
- **README.md**: 기술 문서 및 API 설명
- **examples/notebook_demo.ipynb**: 인터랙티브 튜토리얼

---

**5분 안에 시작할 수 있습니다! 🚀**

질문이 있으면 이슈를 올려주세요!
