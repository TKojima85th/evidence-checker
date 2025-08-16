import requests
import time
from typing import List, Dict, Optional
from urllib.parse import quote
from dataclasses import dataclass
from datetime import datetime
import xml.etree.ElementTree as ET
from src.config import settings


@dataclass
class PubMedArticle:
    """PubMed記事の情報"""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_date: Optional[datetime]
    doi: Optional[str]
    study_type: Optional[str]
    url: str


class PubMedSearcher:
    """PubMed検索クラス"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = settings.ncbi_email
        self.api_key = settings.ncbi_api_key
        self.rate_limit_delay = 0.34 if not self.api_key else 0.1  # API キーありなら10req/sec、なしなら3req/sec
        
        # 研究デザインのキーワードマッピング
        self.study_type_keywords = {
            "meta-analysis": ["meta-analysis", "systematic review", "pooled analysis"],
            "randomized_controlled_trial": ["randomized controlled trial", "RCT", "randomized", "placebo"],
            "cohort_study": ["cohort study", "prospective", "longitudinal"],
            "case_control": ["case-control", "case control"],
            "cross_sectional": ["cross-sectional", "cross sectional", "survey"],
            "case_report": ["case report", "case series"],
            "review": ["review", "narrative review"]
        }
    
    def search_articles(self, query: str, max_results: int = 10) -> List[PubMedArticle]:
        """主張に関連する記事を検索"""
        try:
            # 検索クエリの最適化
            optimized_query = self._optimize_query(query)
            
            # PubMed IDを検索
            pmids = self._search_pmids(optimized_query, max_results)
            if not pmids:
                return []
            
            # 詳細情報を取得
            articles = self._fetch_article_details(pmids)
            
            # 関連度でソート
            articles = self._rank_articles(articles, query)
            
            return articles[:max_results]
            
        except Exception as e:
            print(f"PubMed検索エラー: {e}")
            return []
    
    def _optimize_query(self, query: str) -> str:
        """検索クエリを最適化"""
        # 日本語から英語への簡易変換
        translations = {
            "ビタミンD": "vitamin D",
            "免疫": "immune",
            "感染": "infection",
            "がん": "cancer",
            "癌": "cancer",
            "心臓病": "heart disease",
            "糖尿病": "diabetes",
            "高血圧": "hypertension",
            "コレステロール": "cholesterol",
            "血糖値": "blood glucose",
            "予防": "prevention",
            "治療": "treatment",
            "効果": "effect",
            "リスク": "risk",
            "健康": "health"
        }
        
        optimized = query
        for jp, en in translations.items():
            optimized = optimized.replace(jp, en)
        
        # 研究の質を向上させるフィルターを追加
        filters = [
            "AND (humans[MeSH Terms])",
            "AND (english[Language] OR japanese[Language])",
            "AND (\"last 10 years\"[PDat])"
        ]
        
        return optimized + " " + " ".join(filters)
    
    def _search_pmids(self, query: str, max_results: int) -> List[str]:
        """PubMed IDを検索"""
        url = f"{self.base_url}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "xml",
            "sort": "relevance"
        }
        
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        
        time.sleep(self.rate_limit_delay)
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            pmids = [id_elem.text for id_elem in root.findall(".//Id")]
            
            return pmids
            
        except Exception as e:
            print(f"PMID検索エラー: {e}")
            return []
    
    def _fetch_article_details(self, pmids: List[str]) -> List[PubMedArticle]:
        """記事の詳細情報を取得"""
        if not pmids:
            return []
        
        url = f"{self.base_url}efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        
        time.sleep(self.rate_limit_delay)
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            return self._parse_articles_xml(response.content)
            
        except Exception as e:
            print(f"記事詳細取得エラー: {e}")
            return []
    
    def _parse_articles_xml(self, xml_content: bytes) -> List[PubMedArticle]:
        """XMLから記事情報を解析"""
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article_elem in root.findall(".//PubmedArticle"):
                article = self._parse_single_article(article_elem)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            print(f"XML解析エラー: {e}")
        
        return articles
    
    def _parse_single_article(self, article_elem) -> Optional[PubMedArticle]:
        """単一記事の情報を解析"""
        try:
            # PMID
            pmid_elem = article_elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # タイトル
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            
            # アブストラクト
            abstract_elem = article_elem.find(".//Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            # 著者
            author_elems = article_elem.findall(".//Author")
            authors = []
            for author_elem in author_elems[:5]:  # 最初の5人まで
                lastname = author_elem.find("LastName")
                firstname = author_elem.find("ForeName")
                if lastname is not None and firstname is not None:
                    authors.append(f"{firstname.text} {lastname.text}")
            
            # ジャーナル
            journal_elem = article_elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # 出版日
            pub_date = self._parse_publication_date(article_elem)
            
            # DOI
            doi_elem = article_elem.find(".//ELocationID[@EIdType='doi']")
            doi = doi_elem.text if doi_elem is not None else None
            
            # 研究タイプの推定
            study_type = self._estimate_study_type(title + " " + abstract)
            
            # URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            return PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                doi=doi,
                study_type=study_type,
                url=url
            )
            
        except Exception as e:
            print(f"記事解析エラー: {e}")
            return None
    
    def _parse_publication_date(self, article_elem) -> Optional[datetime]:
        """出版日を解析"""
        try:
            pub_date_elem = article_elem.find(".//PubDate")
            if pub_date_elem is None:
                return None
            
            year_elem = pub_date_elem.find("Year")
            month_elem = pub_date_elem.find("Month")
            day_elem = pub_date_elem.find("Day")
            
            year = int(year_elem.text) if year_elem is not None else datetime.now().year
            month = self._parse_month(month_elem.text) if month_elem is not None else 1
            day = int(day_elem.text) if day_elem is not None else 1
            
            return datetime(year, month, day)
            
        except Exception:
            return None
    
    def _parse_month(self, month_str: str) -> int:
        """月の文字列を数値に変換"""
        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        
        if month_str.isdigit():
            return int(month_str)
        
        return month_map.get(month_str, 1)
    
    def _estimate_study_type(self, text: str) -> str:
        """研究タイプを推定"""
        text_lower = text.lower()
        
        for study_type, keywords in self.study_type_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return study_type
        
        return "other"
    
    def _rank_articles(self, articles: List[PubMedArticle], query: str) -> List[PubMedArticle]:
        """記事を関連度でランク付け"""
        query_words = set(query.lower().split())
        
        def calculate_relevance(article: PubMedArticle) -> float:
            score = 0.0
            
            # タイトルでの一致
            title_words = set(article.title.lower().split())
            title_matches = len(query_words & title_words)
            score += title_matches * 3.0
            
            # アブストラクトでの一致
            abstract_words = set(article.abstract.lower().split())
            abstract_matches = len(query_words & abstract_words)
            score += abstract_matches * 1.0
            
            # 研究タイプによるボーナス
            type_bonus = {
                "meta-analysis": 3.0,
                "randomized_controlled_trial": 2.5,
                "cohort_study": 2.0,
                "case_control": 1.5,
                "review": 1.2
            }
            score += type_bonus.get(article.study_type, 1.0)
            
            # 出版日による重み（新しいほど高い）
            if article.publication_date:
                years_old = (datetime.now() - article.publication_date).days / 365
                if years_old < 5:
                    score += 1.0
                elif years_old < 10:
                    score += 0.5
            
            return score
        
        # スコアでソート
        articles_with_score = [(article, calculate_relevance(article)) for article in articles]
        articles_with_score.sort(key=lambda x: x[1], reverse=True)
        
        return [article for article, score in articles_with_score]


def search_evidence(claim_text: str, max_results: int = 5) -> List[Dict]:
    """メイン関数：主張に対するエビデンスを検索"""
    searcher = PubMedSearcher()
    articles = searcher.search_articles(claim_text, max_results)
    
    evidence_list = []
    for article in articles:
        evidence_list.append({
            "pmid": article.pmid,
            "title": article.title,
            "abstract": article.abstract[:500] + "..." if len(article.abstract) > 500 else article.abstract,
            "authors": article.authors[:3],  # 最初の3人まで
            "journal": article.journal,
            "publication_date": article.publication_date.isoformat() if article.publication_date else None,
            "study_type": article.study_type,
            "url": article.url,
            "relevance_score": 0.8  # 仮の関連度スコア
        })
    
    return evidence_list