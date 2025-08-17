# Evidence Checker - 段階的AI評価システム

医学・健康情報のエビデンスを段階的AI評価により100点満点で自動評価するツール

## 📋 プロジェクト概要

SNSのコメントや書籍の内容がエビデンスに則ったものかを**段階的AI評価**により自動チェックし、信頼性を点数化するシステムです。PubMed、WHO、CDC、NIH、Cochrane Database等の信頼できるソースと照合して評価を行います。

## 🚀 最新アップデート（2025-08-17）

### ✅ 段階的AI評価システム v1.0 実装完了

2つの重要な問題を解決し、提供された`prompt_byChatgpt.md`、`scoring_byClaude.md`、`scoring_byChatGPT0817`フォルダの仕様に基づく段階的評価システムを実装しました。

#### 解決した問題
1. **ログ保存機能の修正** ✅ - 新しい検索のログが正常に保存されるようになりました
2. **論文内容解釈機能の実装** ✅ - 論文の詳細解釈と根拠の可視化を実装

#### 新機能
- **段階的AI評価システム**: 4段階の詳細評価プロセス
- **100点満点ルーブリック**: 5カテゴリ別の精密スコアリング
- **論文内容解釈**: 個別論文の詳細分析とGRADE評価
- **改良されたログ機能**: Excel形式での詳細ログ記録

## 🎯 段階的評価システム（4段階）

### Stage 1: 主張正規化
- PICO分析（Population/Intervention/Comparator/Outcome）
- 医学用語の標準化
- 検索語の最適化

### Stage 2: 高精度文献検索
- PubMed API連携
- 一次スクリーニング
- 研究デザイン別優先度付け

### Stage 3: 論文内容解釈・総合分析（NEW）
- 個別論文の詳細解釈
- エビデンス総合とGRADE評価
- 研究品質評価（RoB 2.0準拠）
- 研究間異質性分析

### Stage 4: 段階的スコアリング（NEW）
- 100点満点の詳細評価
- 5カテゴリ別スコアリング
- 減点・加点システム
- 信頼度評価

## 📊 100点満点ルーブリック v3.0

| カテゴリ | 配点 | 説明 |
|----------|------|------|
| **Evidence Alignment** | 0-60点 | エビデンス整合性×GRADE確信度 |
| **Citation Quality** | 0-22点 | 検証可能性・ソース階層・透明性 |
| **Scope & Nuance** | 0-12点 | PICO適合性・外的妥当性・限界明示 |
| **Quantitative Accuracy** | 0-6点 | 数値の正確性・不確実性の提示 |
| **Safety Risk Handling** | 0-6点 | 有害事象・安全配慮の記載 |

### 判定ラベル
- **85-100点**: True / Mostly True（信頼度: High）
- **60-84点**: Mixed / Context Needed（信頼度: Medium）
- **30-59点**: Unsupported / Misleading（信頼度: Medium）
- **0-29点**: False / Harmful（信頼度: High）

## 🏗️ 開発進捗

### ✅ Stage 0-3 完了（2025-08-15）
- [x] 9軸ルーブリック詳細化
- [x] FastAPI + Poetry環境構築
- [x] 日本語NLP環境（GiNZA、spaCy）
- [x] PubMed検索・NLI統合
- [x] Docker環境構築

### ✅ Stage 4 完了（2025-08-17）
- [x] **問題1**: ログ保存機能の修正
- [x] **問題2**: 論文内容解釈機能の実装  
- [x] **Stage 3**: 段階的AI評価システム設計
- [x] **新スコアリング**: 100点満点ルーブリック実装
- [x] **API統合**: 段階的評価とフォールバック機能
- [x] **システムテスト**: Docker環境での動作確認

## 📁 ファイル構成

```
Evidence_Checker/
├── README.md                           # このファイル（更新済み）
├── Purpose.txt                         # プロジェクト目的
├── prompt_byChatgpt.md                 # 7段階評価プロンプト集
├── scoring_byClaude.md                 # 100点満点ルーブリック v3.0
├── scoring_byChatGPT0817/              # スコアリングシステム原案
│   ├── README.md                       # 構成説明
│   ├── input_schema.json               # 入力スキーマ
│   ├── output_schema.json              # 出力スキーマ
│   └── score_engine.py                 # スコア計算エンジン
├── src/                                # メインアプリケーション
│   ├── core/
│   │   ├── medical_normalizer_v2.py    # Stage 1: 正規化
│   │   ├── literature_searcher.py      # Stage 2: 文献検索
│   │   └── staged_evaluator.py         # Stage 3-4: 段階的評価（NEW）
│   └── utils/
│       └── evaluation_logger.py        # 改良されたログ機能
├── test_main_with_normalizer.py        # 統合APIサーバー
├── evidence_checker_web.html           # Webインターフェース（手動テスト用）
├── requirements-minimal.txt            # 最小構成の依存関係
├── Dockerfile.minimal                  # 軽量Docker環境
├── docker-compose.yml                  # Docker Compose設定
└── logs/                               # Excel形式のログファイル
    └── evaluation_log.xlsx             # 評価ログ
```

## 🛠️ 技術スタック

### 新規追加
- **段階的評価**: `StagedEvaluator`クラス
- **論文解釈**: AI支援による詳細分析
- **GRADE評価**: エビデンス確信度評価
- **Excel ログ**: pandas + openpyxl

### 既存技術
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **NLP**: GiNZA, spaCy（最小構成では無効）
- **ML/AI**: OpenAI, Gemini, DeepSeek API連携
- **Infrastructure**: Docker, Poetry
- **External APIs**: PubMed E-utilities

## 🚀 使い方

### 1. Docker実行（推奨）

```bash
# リポジトリクローン
git clone <repository-url>
cd Evidence_Checker

# 環境設定
cp .env.example .env
# .envにAPI keys等を設定

# Docker起動
docker-compose up -d

# 動作確認
curl http://localhost:8000/health/
```

### 2. API使用方法

#### 基本評価API
```bash
curl -X POST "http://localhost:8000/api/v1/score" \
     -H "Content-Type: application/json" \
     -d '{"claim_text": "ビタミンDは免疫機能をサポートする", "language": "ja"}'
```

#### 段階的評価API（完全版環境）
```bash
curl -X POST "http://localhost:8000/api/v1/staged-evaluation" \
     -H "Content-Type: application/json" \
     -d '{"claim_text": "体操がめまいを改善させる", "language": "ja"}'
```

#### ログダウンロード
```bash
curl -f http://localhost:8000/api/v1/logs/download -o evaluation_log.xlsx
```

### 3. Webインターフェース

```bash
# ローカルでWebインターフェースを開く
open evidence_checker_web.html
```

- 美しいUIで手動テスト可能
- リアルタイムでのスコア確認
- Excelログの直接ダウンロード

## 🧪 テスト方法

### 手動テスト
1. **Webインターフェース**:
   - `evidence_checker_web.html`をブラウザで開く
   - 様々な医学的主張を入力してテスト

2. **推奨テストケース**:
   ```
   ビタミンDは免疫機能をサポートする効果があります
   体操がめまいを改善させる
   オメガ3脂肪酸は心臓病を予防する
   大麻は副鼻腔炎を軽減する
   Vitamin C prevents common cold
   ```

### 自動テスト
```bash
# 全機能テスト
make test-all

# API統合テスト
pytest tests/
```

## 📊 システム構成

### 現在の稼働状況
- ✅ **基本評価API**: 正常稼働（75点/基本モード）
- ✅ **ログ機能**: Excel形式で正常記録
- ✅ **Webインターフェース**: 手動テスト可能
- ⚠️ **段階的評価**: 依存関係により制限モード

### フォールバック機能
- 依存関係不足時は基本評価モードで稼働
- 適切なエラーメッセージとフォールバック
- ログ機能は常に正常動作

## 🔍 ログ機能

### Excel ログの内容
- 評価日時、原文、総合スコア
- 医学用語、検索クエリ、医学分野
- 論文詳細（PMID、タイトル、研究タイプ）
- 正規化・文献検索・段階的評価の使用状況

### ログダウンロード
- Web UI: 「📥 ログをダウンロード」ボタン
- API: `GET /api/v1/logs/download`
- ファイル形式: Excel (.xlsx)

## 🔧 完全版セットアップ

段階的AI評価システムをフル機能で使用するには：

1. **完全版依存関係のインストール**
   ```bash
   pip install -r requirements.txt  # spaCy, Ginza等を含む
   ```

2. **API Keys設定**
   ```bash
   # .envファイルに以下を設定
   OPENAI_API_KEY=your_openai_key
   GEMINI_API_KEY=your_gemini_key
   DEEPSEEK_API_KEY=your_deepseek_key
   NCBI_EMAIL=your_email@example.com
   ```

3. **言語モデルのダウンロード**
   ```bash
   python -m spacy download en_core_web_sm
   python -c "import ginza; ginza.download_model('ja')"
   ```

## 🌟 主な特徴

### 段階的AI評価
- **Stage 1**: 医学用語正規化とPICO分析
- **Stage 2**: PubMed高精度検索
- **Stage 3**: 論文内容詳細解釈
- **Stage 4**: 100点満点精密スコアリング

### 高精度スコアリング
- GRADE確信度ベースの評価
- RoB 2.0研究品質評価
- 減点・加点システム
- 透明性の高い根拠提示

### 実用性
- Webインターフェース搭載
- Excel形式ログ出力
- Docker環境対応
- API統合とフォールバック

## 📈 今後の展開

### Phase 1: 基盤強化
- 完全版Docker環境構築
- 多言語対応拡張
- パフォーマンス最適化

### Phase 2: 高度機能
- 外部サービス連携（Retraction Watch、PROSPERO）
- リアルタイム評価
- ユーザー管理機能

### Phase 3: 実用化
- Web アプリケーション化
- モバイル対応
- 商用展開

## 📝 作業履歴

| 日付 | セッション | 作業内容 | 成果物 |
|------|------------|----------|--------|
| 2025-08-15 | 0-3 | 基盤システム構築 | 9軸評価、NLP、Docker |
| 2025-08-17 | 4 | 段階的AI評価実装 | 100点ルーブリック、論文解釈 |

## 🤝 貢献

プロジェクトへの貢献を歓迎します：
- Issue報告
- 機能提案
- プルリクエスト
- テストケース追加

---

**Current Status**: 🎉 段階的AI評価システム v1.0 完成！

**最終更新**: 2025-08-17  
**バージョン**: v1.0.0  
**ステータス**: Production Ready (基本機能) / Beta (完全版)