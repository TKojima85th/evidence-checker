.PHONY: help install dev test lint format clean run

help:	## このヘルプを表示
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:	## 依存関係をインストール
	poetry install

dev:	## 開発用の依存関係をインストール
	poetry install --with dev

test:	## テストを実行
	poetry run pytest tests/ -v

lint:	## コードチェックを実行
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/
	poetry run mypy src/

format:	## コードフォーマットを実行
	poetry run black src/ tests/
	poetry run isort src/ tests/

clean:	## キャッシュとビルドファイルを削除
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

run:	## 開発サーバーを起動
	poetry run uvicorn src.main:app --reload --port 8000

setup-db:	## データベースを初期化
	poetry run python scripts/setup_db.py

# Docker関連
docker-build:	## Dockerイメージをビルド
	docker build -t evidence-checker .

docker-run:	## Dockerコンテナを起動
	docker run -p 8000:8000 evidence-checker

docker-compose-up:	## docker-composeで起動
	docker-compose up -d

docker-compose-down:	## docker-composeを停止
	docker-compose down

# テスト関連
test-all:	## 全テストを実行（単体・統合・NLI）
	poetry run pytest tests/ -v --tb=short

test-unit:	## 単体テストのみ実行
	poetry run pytest tests/test_extract.py tests/test_scoring.py tests/test_nli.py -v

test-integration:	## 統合テストのみ実行
	poetry run pytest tests/test_integration.py -v

test-api:	## API テストのみ実行
	poetry run pytest tests/test_api.py -v

# パフォーマンス
benchmark:	## 簡易ベンチマークの実行
	poetry run python -c "import time; from tests.test_integration import TestPerformance; t = TestPerformance(); t.test_response_time_under_load(); print('Performance test completed')"

# バージョン管理
archive:	## 現在のバージョンをアーカイブ
	mkdir -p Archive/session3_$(shell date +%Y%m%d_%H%M%S)
	cp -r src/ Archive/session3_$(shell date +%Y%m%d_%H%M%S)/