# Evidence Checker

医学・健康情報のエビデンスを9軸100点ルーブリックで自動評価するツール

## 📋 プロジェクト概要

SNSのコメントや書籍の内容がエビデンスに則ったものかを自動チェックし、信頼性を点数化するシステムです。PubMed、WHO、CDC、NIH、Cochrane Database等の信頼できるソースと照合して評価を行います。

## 🎯 評価基準（9軸ルーブリック）

| 軸 | 重み | 説明 |
|---|---|---|
| 主張の明確性 | 10% | 誰が・いつ・何を・どれだけ主張しているか |
| 証拠の質 | 20% | 研究デザインと出典の信頼性 |
| 学術合意 | 15% | 主要学会・機関のコンセンサスとの整合 |
| 生物学的妥当性 | 10% | 既知の生理・薬理・疫学との整合性 |
| データ透明性 | 10% | 一次資料、方法、COI開示の有無 |
| 文脈歪曲リスク | 10% | 相関と因果の混同、過剰一般化等 |
| 害の可能性 | 15% | 医療忌避・経済損失・差別誘発リスク |
| 拡散性 | 5% | 拡散速度と到達規模 |
| 訂正対応 | 5% | 誤り指摘後の修正・謝罪対応 |

## 📊 判定ラベル

- **90-100点**: 正確（True）
- **75-89点**: 概ね正確（Mostly True）
- **55-74点**: 根拠薄い/ミスリーディング（Unsupported/Misleading）
- **35-54点**: 不正確（False）
- **0-34点**: 虚偽/でっち上げ（Fabricated）

## 🏗️ 開発進捗

### ✅ セッション0 完了（2025-08-15）
- [x] 9軸ルーブリック詳細化（`rubric_detailed.md`）
- [x] API入出力仕様固定（`api_specification.md`）
- [x] プロジェクト構造・DBスキーマ設計（`project_structure.md`）
- [x] README.md初期版作成

### ✅ セッション1 完了（2025-08-15）
- [x] FastAPI + Poetry環境構築
- [x] DBスキーマ実装（SQLite開発環境）
- [x] `/score`エンドポイントのスタブ実装
- [x] 基本的なテスト環境セットアップ
- [x] Makefile作成（タスク自動化）

### ✅ セッション2 完了（2025-08-15）
- [x] 日本語NLP環境構築（GiNZA、spaCy）
- [x] extract実装（主張抽出機能）
- [x] evidence実装（PubMed検索機能）
- [x] 包括的スコアリングロジック統合
- [x] 単体テスト・結合テスト作成

### ✅ セッション3 完了（2025-08-15）
- [x] NLI実装（自然言語推論）
- [x] エビデンスと主張の支持/反証判定機能
- [x] スコア精度向上とNLI統合
- [x] Docker環境構築
- [x] 統合テスト・パフォーマンステスト

### 🎯 プロジェクト完成
**Evidence Checker v0.3.0** - 本格的なエビデンス評価システムが完成しました！

## 📁 ファイル構成

```
Evidence_Checker/
├── README.md                 # このファイル
├── Purpose.txt              # プロジェクト目的  
├── Proposal.txt             # ChatGPT提案内容
├── rubric_detailed.md       # 9軸ルーブリック詳細
├── api_specification.md     # API仕様書
├── project_structure.md     # プロジェクト構造設計
├── pyproject.toml           # Poetry設定
├── Makefile                 # タスク自動化
├── .env.example             # 環境変数テンプレート
├── src/                     # メインアプリケーション
│   ├── main.py             # FastAPIエントリーポイント
│   ├── config.py           # 設定管理
│   ├── database.py         # SQLAlchemyモデル
│   ├── api/                # APIエンドポイント
│   │   ├── health.py       # ヘルスチェック
│   │   └── score.py        # スコア評価（NLI統合済み）
│   ├── core/               # コアロジック
│   │   ├── extract.py      # 主張抽出（GiNZA）
│   │   ├── nli.py          # 自然言語推論（NEW）
│   │   └── scoring.py      # 統合スコアリング
│   ├── models/             # Pydanticモデル
│   │   └── claim.py        # リクエスト/レスポンスモデル
│   └── utils/              # ユーティリティ
│       └── pubmed.py       # PubMed検索
├── tests/                  # 完全なテストスイート
│   ├── test_api.py         # API統合テスト
│   ├── test_extract.py     # 主張抽出テスト
│   ├── test_scoring.py     # スコアリングテスト
│   ├── test_nli.py         # NLIテスト（NEW）
│   └── test_integration.py # エンドツーエンドテスト（NEW）
├── Dockerfile              # Docker環境
├── docker-compose.yml      # Docker Compose設定
└── Archive/                # バージョン管理用
```

## 🛠️ 技術スタック

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Database**: PostgreSQL (本番) / SQLite (開発)
- **NLP**: GiNZA, spaCy, sentence-transformers, transformers
- **ML/AI**: 多言語NLI、semantic similarity、ルールベース推論
- **Infrastructure**: Docker, Redis (cache), Poetry
- **External APIs**: PubMed E-utilities
- **Testing**: pytest, 統合テスト、パフォーマンステスト

## 📋 必要な事前準備

セッション1開始前に以下を用意：

- [ ] シードデータ（50-100件の健康関連主張）
- [ ] 各主張の金標準スコア
- [ ] 根拠URL（PubMed/学会）1-3本/主張
- [ ] `.env`設定（NCBI_EMAIL等）
- [ ] Docker環境

## 🔄 作業履歴

| 日付 | セッション | 作業内容 | 成果物 |
|---|---|---|---|
| 2025-08-15 | 0 | 仕様策定・設計 | ルーブリック、API仕様、DB設計 |
| 2025-08-15 | 1 | 基盤実装 | FastAPI環境、DBスキーマ、スタブAPI |
| 2025-08-15 | 2 | コア機能実装 | 主張抽出、PubMed検索、スコアリング統合 |
| 2025-08-15 | 3 | NLI統合・完成 | 自然言語推論、Docker化、完全テスト |

## 📝 作業時の約束

- 作業更新時にREADME.mdを更新
- バージョン変更時は前バージョンをArchive/に保存
- Purpose.txtは上書きしない

---

**Current Status**: 🎉 プロジェクト完成！Evidence Checker v0.3.0

## 🚀 使い方

### ローカル実行
```bash
# 依存関係のインストール
make install

# 開発サーバー起動
make run

# API エンドポイント
curl -X POST "http://localhost:8000/api/v1/score" \
     -H "Content-Type: application/json" \
     -d '{"claim_text": "ビタミンDは免疫機能をサポートする"}'
```

### Docker実行
```bash
# Docker環境で起動
make docker-compose-up

# ヘルスチェック
curl http://localhost:8000/health/
```

### テスト実行
```bash
# 全テスト実行
make test-all

# 統合テストのみ
make test-integration
```