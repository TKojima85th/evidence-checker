
# Evidence Scoring (Unified Rubric v3.0)

- 日付: 2025-08-17
- 内容: 入出力JSONスキーマ / スコア計算エンジン（Python） / 使い方

## 構成
- `input_schema.json` — 評価用入力スキーマ（必要フィールド・列挙型・範囲）
- `output_schema.json` — スコア結果スキーマ（内訳・合計・ラベル・確信度）
- `score_engine.py` — ルーブリックv3.0の実装（`score(payload)`）

## 使い方
```python
from score_engine import score
import json

with open("your_payload.json","r") as f:
    payload = json.load(f)

result = score(payload)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

## メモ
- ラベル閾値: True ≥90, Mostly True ≥85, Mixed/Context ≥60, Unsupported ≥30, Misleading ≥10, Harmful <10
- 重大ペナルティ時のcap: 撤回/捕食ジャーナルを主要根拠→A ≤20, B1 ≤7
- `language_assertiveness_score`: -5〜+3（断定語密度/hedging）
- `exaggeration_level`: 0（なし）〜5（極端）
