from typing import Dict, List, Optional
from dataclasses import dataclass
import re
from datetime import datetime, timedelta
from src.core.extract import ExtractedClaim
from src.utils.pubmed import PubMedArticle
from src.core.nli import analyze_claim_evidence_stance


@dataclass
class ScoreComponents:
    """スコア構成要素"""
    clarity: int = 0
    evidence_quality: int = 0
    consensus: int = 0
    biological_plausibility: int = 0
    transparency: int = 0
    context_distortion: int = 0
    harm_potential: int = 0
    virality: int = 0
    correction_response: int = 0


class EvidenceScorer:
    """エビデンスベースのスコアリングクラス"""
    
    def __init__(self):
        # 危険なフレーズ辞書
        self.harmful_phrases = {
            "医療忌避": ["ワクチンは不要", "医者に行くな", "薬を飲むな", "治療を拒否"],
            "科学否定": ["科学は嘘", "研究は信用できない", "データは改ざん"],
            "差別誘発": ["○○人は", "○○は劣っている", "遺伝的に"],
            "経済詐欺": ["必ず痩せる", "絶対に治る", "副作用なし", "今だけ特価"]
        }
        
        # 信頼できる機関のキーワード
        self.trusted_sources = [
            "WHO", "CDC", "厚生労働省", "日本医師会", "学会",
            "Cochrane", "PubMed", "NEJM", "Lancet", "JAMA"
        ]
        
        # 研究デザインの質的評価
        self.study_quality_scores = {
            "meta-analysis": 5,
            "randomized_controlled_trial": 4,
            "cohort_study": 3,
            "case_control": 2,
            "cross_sectional": 2,
            "case_report": 1,
            "review": 2,
            "other": 1
        }
    
    def calculate_comprehensive_score(
        self,
        claim: ExtractedClaim,
        evidence_list: List[Dict],
        original_text: str,
        source_url: Optional[str] = None
    ) -> Dict:
        """包括的なスコア計算"""
        
        scores = ScoreComponents()
        
        # NLI分析を実行
        analyzed_evidence, stance_summary = analyze_claim_evidence_stance(claim.text, evidence_list)
        
        # 1. 主張の明確性 (10%)
        scores.clarity = self._score_clarity(claim)
        
        # 2. 証拠の質 (20%) - NLI結果を考慮
        scores.evidence_quality = self._score_evidence_quality_with_nli(evidence_list, stance_summary)
        
        # 3. 学術合意 (15%) - NLI結果を考慮
        scores.consensus = self._score_consensus_with_nli(claim, evidence_list, stance_summary)
        
        # 4. 生物学的妥当性 (10%)
        scores.biological_plausibility = self._score_biological_plausibility(claim)
        
        # 5. データ透明性 (10%)
        scores.transparency = self._score_transparency(original_text, source_url, evidence_list)
        
        # 6. 文脈歪曲リスク (10%)
        scores.context_distortion = self._score_context_distortion(claim, original_text)
        
        # 7. 害の可能性 (15%)
        scores.harm_potential = self._score_harm_potential(original_text)
        
        # 8. 拡散性 (5%)
        scores.virality = self._score_virality(original_text)
        
        # 9. 訂正対応 (5%)
        scores.correction_response = 0  # 初回評価では0
        
        # 重み付き合計計算
        total_score = (
            scores.clarity * 10 +
            scores.evidence_quality * 20 +
            scores.consensus * 15 +
            scores.biological_plausibility * 10 +
            scores.transparency * 10 +
            scores.context_distortion * 10 +
            scores.harm_potential * 15 +
            scores.virality * 5 +
            scores.correction_response * 5
        ) // 5
        
        # 安全装置：害の可能性が高い場合の最大スコア制限
        if scores.harm_potential <= 1:
            total_score = min(total_score, 74)  # "根拠薄い"まで
        
        # ラベル決定
        label = self._determine_label(total_score)
        
        return {
            "total_score": total_score,
            "label": label,
            "scores": scores,
            "rationales": self._generate_rationales_with_nli(scores, claim, evidence_list, stance_summary),
            "analyzed_evidence": analyzed_evidence,
            "stance_summary": stance_summary
        }
    
    def _score_clarity(self, claim: ExtractedClaim) -> int:
        """主張の明確性を評価"""
        score = 2  # ベーススコア
        
        # 主語・述語・目的語が明確か
        if claim.subject and claim.predicate and claim.object:
            score += 2
        elif claim.subject and claim.predicate:
            score += 1
        
        # 効果量が明記されているか
        if claim.effect_size:
            score += 1
        
        # 文が短すぎず長すぎないか
        text_length = len(claim.text)
        if 20 <= text_length <= 200:
            score += 0
        elif text_length < 20:
            score -= 1
        
        return max(0, min(5, score))
    
    def _score_evidence_quality(self, evidence_list: List[Dict]) -> int:
        """証拠の質を評価"""
        if not evidence_list:
            return 0
        
        max_quality = 0
        for evidence in evidence_list:
            study_type = evidence.get("study_type", "other")
            quality = self.study_quality_scores.get(study_type, 1)
            max_quality = max(max_quality, quality)
        
        # エビデンス数によるボーナス
        evidence_count = len(evidence_list)
        if evidence_count >= 3:
            max_quality = min(5, max_quality + 1)
        
        return max_quality
    
    def _score_evidence_quality_with_nli(self, evidence_list: List[Dict], stance_summary: Dict) -> int:
        """NLI結果を考慮した証拠の質評価"""
        base_score = self._score_evidence_quality(evidence_list)
        
        # NLI分析結果によるボーナス/ペナルティ
        total_evidence = stance_summary.get("total_evidence", 0)
        support_count = stance_summary.get("support_count", 0)
        contradict_count = stance_summary.get("contradict_count", 0)
        
        if total_evidence == 0:
            return 0
        
        # 支持エビデンスが多い場合のボーナス
        support_ratio = support_count / total_evidence
        if support_ratio >= 0.7:
            base_score = min(5, base_score + 1)
        elif support_ratio >= 0.5:
            # 変更なし
            pass
        else:
            # 支持エビデンスが少ない場合のペナルティ
            base_score = max(1, base_score - 1)
        
        # 矛盾エビデンスが多い場合のペナルティ
        contradict_ratio = contradict_count / total_evidence
        if contradict_ratio >= 0.5:
            base_score = max(1, base_score - 1)
        
        return base_score
    
    def _score_consensus(self, claim: ExtractedClaim, evidence_list: List[Dict]) -> int:
        """学術合意との整合性を評価"""
        score = 2  # ベーススコア
        
        # エビデンスの一貫性
        if len(evidence_list) >= 2:
            # 複数のエビデンスがある場合
            score += 1
        
        if len(evidence_list) >= 5:
            # 多くのエビデンスがある場合
            score += 1
        
        # 信頼できる機関からの引用があるか
        text_combined = claim.text + " " + " ".join([e.get("title", "") for e in evidence_list])
        trusted_mentions = sum(1 for source in self.trusted_sources if source in text_combined)
        if trusted_mentions >= 1:
            score += 1
        
        return max(0, min(5, score))
    
    def _score_consensus_with_nli(self, claim: ExtractedClaim, evidence_list: List[Dict], stance_summary: Dict) -> int:
        """NLI結果を考慮した学術合意評価"""
        base_score = self._score_consensus(claim, evidence_list)
        
        # NLI分析による合意度の評価
        total_evidence = stance_summary.get("total_evidence", 0)
        support_count = stance_summary.get("support_count", 0)
        contradict_count = stance_summary.get("contradict_count", 0)
        overall_stance = stance_summary.get("overall_stance", "neutral")
        confidence = stance_summary.get("confidence", 0.0)
        
        if total_evidence == 0:
            return base_score
        
        # エビデンス間の合意度
        if overall_stance == "support" and confidence >= 0.7:
            # 強い支持のコンセンサス
            base_score = min(5, base_score + 2)
        elif overall_stance == "support" and confidence >= 0.5:
            # 中程度の支持
            base_score = min(5, base_score + 1)
        elif overall_stance == "contradict" and confidence >= 0.7:
            # 強い反対のコンセンサス
            base_score = max(0, base_score - 2)
        elif contradict_count > 0 and support_count > 0:
            # エビデンス間で意見が分かれている
            disagreement_ratio = min(contradict_count, support_count) / total_evidence
            if disagreement_ratio >= 0.3:
                base_score = max(1, base_score - 1)
        
        return base_score
    
    def _score_biological_plausibility(self, claim: ExtractedClaim) -> int:
        """生物学的妥当性を評価"""
        score = 3  # ベーススコア（中立）
        
        # 非現実的な主張のチェック
        implausible_patterns = [
            r"水だけで.*(治る|完治)",
            r"思考だけで.*(治療|治る)",
            r"100[%％].*効果",
            r"副作用.*一切.*ない",
            r"即座に.*治る"
        ]
        
        for pattern in implausible_patterns:
            if re.search(pattern, claim.text):
                score -= 2
                break
        
        # 妥当性のある表現
        plausible_patterns = [
            r"改善.*可能性",
            r"リスク.*低減",
            r"効果.*報告",
            r"研究.*示唆"
        ]
        
        for pattern in plausible_patterns:
            if re.search(pattern, claim.text):
                score += 1
                break
        
        return max(0, min(5, score))
    
    def _score_transparency(self, text: str, source_url: Optional[str], evidence_list: List[Dict]) -> int:
        """データ透明性を評価"""
        score = 0
        
        # 出典URLが提供されているか
        if source_url:
            score += 2
        
        # エビデンスが提供されているか
        if evidence_list:
            score += 2
        
        # 方法論の言及があるか
        methodology_keywords = ["研究", "調査", "実験", "分析", "統計", "被験者"]
        if any(keyword in text for keyword in methodology_keywords):
            score += 1
        
        return max(0, min(5, score))
    
    def _score_context_distortion(self, claim: ExtractedClaim, text: str) -> int:
        """文脈歪曲リスクを評価（高スコア = 低リスク）"""
        score = 3  # ベーススコア
        
        # 相関と因果の混同
        causal_without_evidence = [
            r"(.+)が(.+)を引き起こす",
            r"(.+)が原因で(.+)",
            r"(.+)のせいで(.+)"
        ]
        
        for pattern in causal_without_evidence:
            if re.search(pattern, text) and not any(
                keyword in text for keyword in ["研究", "実験", "証明", "エビデンス"]
            ):
                score -= 1
                break
        
        # 過剰一般化
        overgeneralization_patterns = [
            r"すべて.*",
            r"必ず.*",
            r"絶対.*",
            r"100[%％].*"
        ]
        
        for pattern in overgeneralization_patterns:
            if re.search(pattern, text):
                score -= 1
                break
        
        # 限界の言及があるか
        limitation_keywords = ["限界", "制限", "条件", "個人差", "場合による"]
        if any(keyword in text for keyword in limitation_keywords):
            score += 1
        
        return max(0, min(5, score))
    
    def _score_harm_potential(self, text: str) -> int:
        """害の可能性を評価（高スコア = 低害）"""
        score = 5  # ベーススコア（無害）
        
        # 有害フレーズのチェック
        for category, phrases in self.harmful_phrases.items():
            for phrase in phrases:
                if phrase in text:
                    if category == "医療忌避":
                        score = 0  # 最も危険
                    elif category == "科学否定":
                        score = min(score, 1)
                    elif category == "差別誘発":
                        score = min(score, 1)
                    elif category == "経済詐欺":
                        score = min(score, 2)
        
        # 安全性への言及
        safety_keywords = ["安全", "副作用", "リスク", "注意", "医師に相談"]
        safety_mentions = sum(1 for keyword in safety_keywords if keyword in text)
        if safety_mentions >= 2:
            score = min(5, score + 1)
        
        return max(0, min(5, score))
    
    def _score_virality(self, text: str) -> int:
        """拡散性を評価"""
        score = 3  # ベーススコア
        
        # センセーショナルな表現
        viral_patterns = [
            r"驚愕",
            r"衝撃",
            r"緊急",
            r"拡散希望",
            r"シェア",
            r"信じられない"
        ]
        
        viral_count = sum(1 for pattern in viral_patterns if re.search(pattern, text))
        score -= viral_count
        
        return max(0, min(5, score))
    
    def _determine_label(self, total_score: int) -> str:
        """総合スコアからラベルを決定"""
        if total_score >= 90:
            return "True"
        elif total_score >= 75:
            return "Mostly True"
        elif total_score >= 55:
            return "Unsupported"
        elif total_score >= 35:
            return "False"
        else:
            return "Fabricated"
    
    def _generate_rationales(self, scores: ScoreComponents, claim: ExtractedClaim, evidence_list: List[Dict]) -> List[Dict]:
        """判定理由を生成"""
        rationales = []
        
        # 主要な軸についてのみ理由を生成
        if scores.clarity <= 2:
            rationales.append({
                "axis": "clarity",
                "score": scores.clarity,
                "reasoning": "主張の内容が曖昧で、具体的な効果量や条件が不明確です。"
            })
        
        if scores.evidence_quality <= 2:
            rationales.append({
                "axis": "evidence_quality",
                "score": scores.evidence_quality,
                "reasoning": "高品質なエビデンス（メタ解析、RCT等）が不足しています。"
            })
        
        if scores.harm_potential <= 2:
            rationales.append({
                "axis": "harm_potential",
                "score": scores.harm_potential,
                "reasoning": "医療忌避や健康リスクを誘発する可能性があります。"
            })
        
        # 良い点も含める
        if scores.evidence_quality >= 4:
            rationales.append({
                "axis": "evidence_quality",
                "score": scores.evidence_quality,
                "reasoning": f"質の高いエビデンス（{len(evidence_list)}件）が見つかりました。"
            })
        
        return rationales
    
    def _generate_rationales_with_nli(self, scores: ScoreComponents, claim: ExtractedClaim, evidence_list: List[Dict], stance_summary: Dict) -> List[Dict]:
        """NLI結果を含む判定理由の生成"""
        rationales = []
        
        # 基本的な理由
        base_rationales = self._generate_rationales(scores, claim, evidence_list)
        rationales.extend(base_rationales)
        
        # NLI分析結果による追加理由
        total_evidence = stance_summary.get("total_evidence", 0)
        support_count = stance_summary.get("support_count", 0)
        contradict_count = stance_summary.get("contradict_count", 0)
        overall_stance = stance_summary.get("overall_stance", "neutral")
        
        if total_evidence > 0:
            if overall_stance == "support" and support_count >= 2:
                rationales.append({
                    "axis": "evidence_quality",
                    "score": scores.evidence_quality,
                    "reasoning": f"NLI分析により、{support_count}件のエビデンスが主張を支持していることが確認されました。"
                })
            elif overall_stance == "contradict" and contradict_count >= 2:
                rationales.append({
                    "axis": "consensus",
                    "score": scores.consensus,
                    "reasoning": f"NLI分析により、{contradict_count}件のエビデンスが主張と矛盾していることが確認されました。"
                })
            elif support_count > 0 and contradict_count > 0:
                rationales.append({
                    "axis": "consensus",
                    "score": scores.consensus,
                    "reasoning": f"エビデンス間で意見が分かれています（支持{support_count}件、反対{contradict_count}件）。"
                })
        
        return rationales


def calculate_evidence_score(claim_dict: Dict, evidence_list: List[Dict], original_text: str, source_url: Optional[str] = None) -> Dict:
    """メイン関数：エビデンスベースのスコア計算"""
    # ExtractedClaimオブジェクトを再構築
    claim = ExtractedClaim(
        text=claim_dict.get("text", original_text),
        confidence=claim_dict.get("confidence", 0.5),
        claim_type=claim_dict.get("type", "general"),
        subject=claim_dict.get("subject"),
        predicate=claim_dict.get("predicate"),
        object=claim_dict.get("object"),
        effect_size=claim_dict.get("effect_size")
    )
    
    scorer = EvidenceScorer()
    result = scorer.calculate_comprehensive_score(claim, evidence_list, original_text, source_url)
    
    return result