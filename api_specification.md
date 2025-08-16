# Evidence Checker API仕様書

## 1. /score エンドポイント

### リクエスト仕様
```http
POST /score
Content-Type: application/json
```

#### 入力パラメータ
```json
{
  "claim_text": "string (required) - チェック対象の主張文",
  "source_url": "string (optional) - 主張の出典URL",
  "text_id": "string (optional) - テキストID（source_urlの代替）",
  "topic": "string (optional) - トピック（例: 'health', 'medicine'）",
  "lang": "string (optional) - 言語コード（デフォルト: 'ja'）"
}
```

#### 出力仕様
```json
{
  "total_score": "integer (0-100) - 総合スコア",
  "label": "string - 判定ラベル（True/Mostly True/Unsupported/False/Fabricated）",
  "axis_scores": {
    "clarity": "integer (0-5) - 主張の明確性",
    "evidence_quality": "integer (0-5) - 証拠の質", 
    "consensus": "integer (0-5) - 学術合意",
    "biological_plausibility": "integer (0-5) - 生物学的妥当性",
    "transparency": "integer (0-5) - データ透明性",
    "context_distortion": "integer (0-5) - 文脈歪曲リスク（逆転評価）",
    "harm_potential": "integer (0-5) - 害の可能性（逆転評価）",
    "virality": "integer (0-5) - 拡散性",
    "correction_response": "integer (0-5) - 訂正対応"
  },
  "rationales": [
    {
      "axis": "string - 評価軸名",
      "score": "integer - その軸の得点",
      "reasoning": "string - 判定理由"
    }
  ],
  "evidence_top3": [
    {
      "source": "string - 出典（PMID/URL）",
      "title": "string - タイトル",
      "stance": "string - 支持/反証/中立",
      "relevance_score": "float (0-1) - 関連度",
      "summary": "string - 要約"
    }
  ],
  "metadata": {
    "processing_time": "float - 処理時間（秒）",
    "timestamp": "string - 評価実施時刻（ISO 8601）",
    "model_version": "string - 使用モデルバージョン",
    "confidence": "float (0-1) - 判定信頼度"
  },
  "claim_review": {
    "@context": "https://schema.org",
    "@type": "ClaimReview",
    "claimReviewed": "string - 評価対象の主張",
    "reviewRating": {
      "@type": "Rating",
      "ratingValue": "integer - 総合スコア",
      "bestRating": 100,
      "worstRating": 0,
      "alternateName": "string - ラベル"
    },
    "itemReviewed": {
      "@type": "Claim",
      "text": "string - 主張文",
      "url": "string - 出典URL（あれば）"
    },
    "url": "string - このレビューのURL",
    "datePublished": "string - 公開日（ISO 8601）",
    "author": {
      "@type": "Organization", 
      "name": "Evidence Checker"
    }
  }
}
```

### エラーレスポンス
```json
{
  "error": {
    "code": "string - エラーコード",
    "message": "string - エラーメッセージ",
    "details": "object - 詳細情報（optional）"
  }
}
```

#### エラーコード一覧
- `INVALID_INPUT`: 入力パラメータエラー
- `CLAIM_TOO_LONG`: 主張文が長すぎる（5000文字制限）
- `PROCESSING_TIMEOUT`: 処理タイムアウト（3秒制限）
- `EVIDENCE_SEARCH_FAILED`: エビデンス検索失敗
- `INTERNAL_ERROR`: 内部エラー

## 2. SLA（Service Level Agreement）

- **応答時間**: 1件あたり ≤ 3秒（キャッシュ有効時）
- **タイムアウト処理**: 制限時間超過時は "Unsupported" で返す
- **可用性**: 99.9%
- **同時処理**: 最大10リクエスト/秒

## 3. その他のエンドポイント（将来拡張）

### /health - ヘルスチェック
```http
GET /health
```

### /evidence/{pmid} - エビデンス詳細取得
```http
GET /evidence/{pmid}
```

### /batch-score - バッチ処理
```http
POST /batch-score
```

## 4. 認証・レート制限

- 現在は認証なし（MVP版）
- レート制限: 60リクエスト/分/IP
- 将来的にAPIキー認証を追加予定