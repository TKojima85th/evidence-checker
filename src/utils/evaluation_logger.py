import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path


class EvaluationLogger:
    """評価結果をログとして記録するクラス"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.excel_file = self.log_dir / "evaluation_log.xlsx"
        
        # 既存のログファイルを読み込み、なければ新規作成
        if self.excel_file.exists():
            try:
                self.df = pd.read_excel(self.excel_file, index_col=0)
            except Exception as e:
                print(f"既存ログファイル読み込みエラー: {e}")
                self.df = self._create_empty_dataframe()
        else:
            self.df = self._create_empty_dataframe()
    
    def _create_empty_dataframe(self) -> pd.DataFrame:
        """空のデータフレームを作成"""
        columns = [
            # 基本情報
            "評価日時",
            "原文",
            "出典URL",
            "トピック",
            "言語",
            
            # 抽出された主張情報
            "抽出された主張",
            "主張タイプ",
            "主張の信頼度",
            
            # 検索されたエビデンス
            "エビデンス1_PMID",
            "エビデンス1_タイトル",
            "エビデンス1_要約",
            "エビデンス1_立場",
            "エビデンス1_信頼度",
            
            "エビデンス2_PMID",
            "エビデンス2_タイトル",
            "エビデンス2_要約",
            "エビデンス2_立場",
            "エビデンス2_信頼度",
            
            "エビデンス3_PMID",
            "エビデンス3_タイトル",
            "エビデンス3_要約",
            "エビデンス3_立場",
            "エビデンス3_信頼度",
            
            # 9軸スコア
            "明確性_スコア",
            "明確性_理由",
            "証拠の質_スコア",
            "証拠の質_理由",
            "学術合意_スコア",
            "学術合意_理由",
            "生物学的妥当性_スコア",
            "生物学的妥当性_理由",
            "データ透明性_スコア",
            "データ透明性_理由",
            "文脈歪曲リスク_スコア",
            "文脈歪曲リスク_理由",
            "害の可能性_スコア",
            "害の可能性_理由",
            "拡散性_スコア",
            "拡散性_理由",
            "訂正対応_スコア",
            "訂正対応_理由",
            
            # 総合評価
            "総合スコア",
            "判定ラベル",
            "処理時間_秒",
            "モデルバージョン",
            "全体的な信頼度",
            
            # NLI分析結果
            "支持エビデンス数",
            "反対エビデンス数",
            "中立エビデンス数",
            "エビデンス全体の立場",
            
            # メタ情報
            "評価者コメント",
            "レビュー済み",
            "正解ラベル"  # 人手評価の正解
        ]
        
        return pd.DataFrame(columns=columns)
    
    def log_evaluation(
        self,
        log_data: Dict = None,
        original_text: str = None,
        request_data: Dict = None,
        response_data: Dict = None,
        processing_time: float = None,
        evaluator_comment: str = ""
    ) -> int:
        """評価結果をログに記録"""
        
        # 簡易ログデータフォーマットの場合
        if log_data is not None:
            # 既存のデータフレームに追加（log_dataをそのまま使用）
            new_row = pd.DataFrame([log_data])
            self.df = pd.concat([self.df, new_row], ignore_index=True)
            self.save_to_excel()
            return len(self.df) - 1
        
        # 従来の詳細フォーマットの場合
        new_row = {
            # 基本情報
            "評価日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "原文": original_text,
            "出典URL": request_data.get("source_url", "") if request_data else "",
            "トピック": request_data.get("topic", "") if request_data else "",
            "言語": request_data.get("lang", "ja") if request_data else "ja",
            
            # 抽出された主張情報（もし含まれていれば）
            "抽出された主張": response_data.get("extracted_claim", {}).get("text", "") if response_data else "",
            "主張タイプ": response_data.get("extracted_claim", {}).get("type", "") if response_data else "",
            "主張の信頼度": response_data.get("extracted_claim", {}).get("confidence", 0) if response_data else 0,
        }
        
        # エビデンス情報を追加
        evidence_list = response_data.get("evidence_top3", []) if response_data else []
        for i in range(3):
            if i < len(evidence_list):
                evidence = evidence_list[i]
                new_row[f"エビデンス{i+1}_PMID"] = evidence.get("source", "")
                new_row[f"エビデンス{i+1}_タイトル"] = evidence.get("title", "")
                new_row[f"エビデンス{i+1}_要約"] = evidence.get("summary", "")
                new_row[f"エビデンス{i+1}_立場"] = evidence.get("stance", "")
                new_row[f"エビデンス{i+1}_信頼度"] = evidence.get("relevance_score", 0)
            else:
                new_row[f"エビデンス{i+1}_PMID"] = ""
                new_row[f"エビデンス{i+1}_タイトル"] = ""
                new_row[f"エビデンス{i+1}_要約"] = ""
                new_row[f"エビデンス{i+1}_立場"] = ""
                new_row[f"エビデンス{i+1}_信頼度"] = 0
        
        # 9軸スコアと理由を追加
        axis_scores = response_data.get("axis_scores", {}) if response_data else {}
        rationales = response_data.get("rationales", []) if response_data else []
        
        # 理由を軸ごとに整理
        reasons_by_axis = {}
        for rationale in rationales:
            axis = rationale.get("axis", "")
            reasoning = rationale.get("reasoning", "")
            reasons_by_axis[axis] = reasoning
        
        # 各軸のスコアと理由を記録
        axis_mapping = {
            "clarity": "明確性",
            "evidence_quality": "証拠の質",
            "consensus": "学術合意",
            "biological_plausibility": "生物学的妥当性",
            "transparency": "データ透明性",
            "context_distortion": "文脈歪曲リスク",
            "harm_potential": "害の可能性",
            "virality": "拡散性",
            "correction_response": "訂正対応"
        }
        
        for eng_axis, jp_axis in axis_mapping.items():
            score = axis_scores.get(eng_axis, 0)
            reason = reasons_by_axis.get(eng_axis, "理由なし")
            
            new_row[f"{jp_axis}_スコア"] = score
            new_row[f"{jp_axis}_理由"] = reason
        
        # 総合評価
        new_row["総合スコア"] = response_data.get("total_score", 0) if response_data else 0
        new_row["判定ラベル"] = response_data.get("label", "") if response_data else ""
        new_row["処理時間_秒"] = processing_time if processing_time else 0
        new_row["モデルバージョン"] = response_data.get("metadata", {}).get("model_version", "") if response_data else ""
        new_row["全体的な信頼度"] = response_data.get("metadata", {}).get("confidence", 0) if response_data else 0
        
        # NLI分析結果（もし含まれていれば）
        stance_summary = response_data.get("stance_summary", {}) if response_data else {}
        new_row["支持エビデンス数"] = stance_summary.get("support_count", 0)
        new_row["反対エビデンス数"] = stance_summary.get("contradict_count", 0)
        new_row["中立エビデンス数"] = stance_summary.get("neutral_count", 0)
        new_row["エビデンス全体の立場"] = stance_summary.get("overall_stance", "")
        
        # メタ情報
        new_row["評価者コメント"] = evaluator_comment
        new_row["レビュー済み"] = False
        new_row["正解ラベル"] = ""  # 後で人手で入力
        
        # データフレームに追加
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Excelファイルに保存
        self.save_to_excel()
        
        # 追加された行のインデックスを返す
        return len(self.df) - 1
    
    def save_to_excel(self):
        """データフレームをExcelファイルに保存"""
        try:
            # インデックス列も含めて保存
            self.df.to_excel(self.excel_file, index=True, index_label="ID")
            print(f"ログが保存されました: {self.excel_file}")
        except Exception as e:
            print(f"Excelファイル保存エラー: {e}")
    
    def get_evaluation_by_id(self, eval_id: int) -> Optional[Dict]:
        """IDで評価結果を取得"""
        if eval_id < len(self.df):
            return self.df.iloc[eval_id].to_dict()
        return None
    
    def get_recent_evaluations(self, n: int = 10) -> pd.DataFrame:
        """最近のn件の評価を取得"""
        return self.df.tail(n)
    
    def get_statistics(self) -> Dict:
        """評価統計を取得"""
        if len(self.df) == 0:
            return {"total_evaluations": 0}
        
        stats = {
            "total_evaluations": len(self.df),
            "average_score": self.df["総合スコア"].mean(),
            "label_distribution": self.df["判定ラベル"].value_counts().to_dict(),
            "average_processing_time": self.df["処理時間_秒"].mean(),
            "latest_evaluation": self.df["評価日時"].max()
        }
        
        return stats
    
    def export_for_review(self, output_file: str = None) -> str:
        """レビュー用のExcelファイルをエクスポート"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_dir / f"evaluation_review_{timestamp}.xlsx"
        
        # レビュー用に列を整理
        review_columns = [
            "ID", "評価日時", "原文", "総合スコア", "判定ラベル",
            "明確性_スコア", "証拠の質_スコア", "学術合意_スコア",
            "エビデンス1_PMID", "エビデンス1_立場",
            "評価者コメント", "正解ラベル", "レビュー済み"
        ]
        
        # IDを列として追加
        review_df = self.df.copy()
        review_df.insert(0, "ID", review_df.index)
        
        # 指定した列のみを含むデータフレームを作成
        available_columns = [col for col in review_columns if col in review_df.columns]
        review_df = review_df[available_columns]
        
        review_df.to_excel(output_file, index=False)
        return str(output_file)


# グローバルロガーインスタンス
evaluation_logger = EvaluationLogger()