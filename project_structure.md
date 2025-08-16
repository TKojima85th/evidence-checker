# プロジェクト構造設計

## ディレクトリ構造
```
Evidence_Checker/
├── README.md
├── Purpose.txt
├── Proposal.txt
├── rubric_detailed.md
├── api_specification.md
├── project_structure.md
├── Archive/                    # バージョン管理用
├── docs/                      # ドキュメント
│   ├── setup.md
│   └── deployment.md
├── src/                       # メインアプリケーション
│   ├── main.py               # FastAPI エントリーポイント
│   ├── config.py             # 設定管理
│   ├── database.py           # DB接続・モデル
│   ├── api/                  # API エンドポイント
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── score.py
│   ├── core/                 # コアロジック
│   │   ├── __init__.py
│   │   ├── extract.py        # 主張抽出
│   │   ├── evidence.py       # エビデンス検索
│   │   ├── nli.py           # 自然言語推論
│   │   └── scoring.py        # スコア計算
│   ├── models/               # データモデル
│   │   ├── __init__.py
│   │   ├── claim.py
│   │   ├── evidence.py
│   │   └── score.py
│   └── utils/                # ユーティリティ
│       ├── __init__.py
│       ├── pubmed.py         # PubMed検索
│       ├── cache.py          # キャッシュ管理
│       └── validators.py     # 入力検証
├── tests/                    # テスト
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_extract.py
│   ├── test_evidence.py
│   ├── test_nli.py
│   └── test_scoring.py
├── data/                     # データファイル
│   ├── seed_claims.jsonl     # シードデータ
│   ├── evidence_cache/       # エビデンスキャッシュ
│   └── models/              # 学習済みモデル
├── scripts/                  # スクリプト
│   ├── setup_db.py          # DB初期化
│   ├── import_seed.py       # シードデータ投入
│   └── export_results.py    # 結果エクスポート
├── docker/                   # Docker関連
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
├── .env.example              # 環境変数テンプレート
├── .gitignore
├── pyproject.toml           # Poetry設定
├── poetry.lock
└── Makefile                 # タスク自動化
```

## データベーススキーマ設計

### 1. claims テーブル
```sql
CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    text_content TEXT NOT NULL,
    source_url VARCHAR(500),
    text_id VARCHAR(100),
    topic VARCHAR(50),
    language VARCHAR(5) DEFAULT 'ja',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- インデックス
    CONSTRAINT unique_text_source UNIQUE (text_content, source_url)
);

CREATE INDEX idx_claims_topic ON claims(topic);
CREATE INDEX idx_claims_created_at ON claims(created_at);
```

### 2. evidence テーブル
```sql
CREATE TABLE evidence (
    id SERIAL PRIMARY KEY,
    pmid VARCHAR(20),                    -- PubMed ID
    doi VARCHAR(100),                    -- DOI
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT,
    journal VARCHAR(200),
    publication_date DATE,
    study_type VARCHAR(50),              -- RCT, Meta-analysis, etc.
    url VARCHAR(500),
    source_type VARCHAR(20) DEFAULT 'pubmed', -- pubmed, who, cdc, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_pmid UNIQUE (pmid),
    CONSTRAINT unique_doi UNIQUE (doi)
);

CREATE INDEX idx_evidence_pmid ON evidence(pmid);
CREATE INDEX idx_evidence_study_type ON evidence(study_type);
CREATE INDEX idx_evidence_publication_date ON evidence(publication_date);
```

### 3. scores テーブル
```sql
CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id) ON DELETE CASCADE,
    total_score INTEGER CHECK (total_score >= 0 AND total_score <= 100),
    label VARCHAR(20) NOT NULL,
    
    -- 9軸スコア
    clarity_score INTEGER CHECK (clarity_score >= 0 AND clarity_score <= 5),
    evidence_quality_score INTEGER CHECK (evidence_quality_score >= 0 AND evidence_quality_score <= 5),
    consensus_score INTEGER CHECK (consensus_score >= 0 AND consensus_score <= 5),
    biological_plausibility_score INTEGER CHECK (biological_plausibility_score >= 0 AND biological_plausibility_score <= 5),
    transparency_score INTEGER CHECK (transparency_score >= 0 AND transparency_score <= 5),
    context_distortion_score INTEGER CHECK (context_distortion_score >= 0 AND context_distortion_score <= 5),
    harm_potential_score INTEGER CHECK (harm_potential_score >= 0 AND harm_potential_score <= 5),
    virality_score INTEGER CHECK (virality_score >= 0 AND virality_score <= 5),
    correction_response_score INTEGER CHECK (correction_response_score >= 0 AND correction_response_score <= 5),
    
    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
    processing_time REAL,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_claim_score UNIQUE (claim_id)
);

CREATE INDEX idx_scores_label ON scores(label);
CREATE INDEX idx_scores_total_score ON scores(total_score);
```

### 4. rationales テーブル
```sql
CREATE TABLE rationales (
    id SERIAL PRIMARY KEY,
    score_id INTEGER REFERENCES scores(id) ON DELETE CASCADE,
    axis VARCHAR(50) NOT NULL,
    axis_score INTEGER CHECK (axis_score >= 0 AND axis_score <= 5),
    reasoning TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rationales_score_id ON rationales(score_id);
CREATE INDEX idx_rationales_axis ON rationales(axis);
```

### 5. claim_evidence テーブル（多対多関係）
```sql
CREATE TABLE claim_evidence (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id) ON DELETE CASCADE,
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE,
    stance VARCHAR(20),                  -- support, contradict, neutral
    relevance_score REAL CHECK (relevance_score >= 0 AND relevance_score <= 1),
    summary TEXT,
    rank_position INTEGER,              -- Top-3での順位
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_claim_evidence UNIQUE (claim_id, evidence_id)
);

CREATE INDEX idx_claim_evidence_claim_id ON claim_evidence(claim_id);
CREATE INDEX idx_claim_evidence_stance ON claim_evidence(stance);
CREATE INDEX idx_claim_evidence_relevance ON claim_evidence(relevance_score);
```

### 6. cache テーブル（オプション）
```sql
CREATE TABLE cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(256) UNIQUE NOT NULL,
    cache_value JSONB NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cache_key ON cache(cache_key);
CREATE INDEX idx_cache_expires_at ON cache(expires_at);
```

## 技術スタック確認

### バックエンド
- **Python**: 3.11+
- **Web Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL (本番) / SQLite (開発)
- **Migration**: Alembic

### NLP・ML
- **日本語処理**: GiNZA
- **文章ベクトル**: sentence-transformers
- **NLI**: 多言語NLIモデル

### インフラ
- **Container**: Docker + docker-compose
- **Cache**: Redis (オプション)
- **Vector Search**: pgvector

### 開発ツール
- **依存管理**: Poetry
- **テスト**: pytest
- **型チェック**: mypy
- **フォーマット**: black, isort
- **リント**: flake8

このスキーマでよろしいでしょうか？次にREADME.mdを作成してセッション0を完了します。