from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from src.config import settings

Base = declarative_base()


class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    text_content = Column(Text, nullable=False)
    source_url = Column(String(500))
    text_id = Column(String(100))
    topic = Column(String(50))
    language = Column(String(5), default="ja")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    scores = relationship("Score", back_populates="claim", cascade="all, delete-orphan")
    claim_evidence = relationship("ClaimEvidence", back_populates="claim", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    pmid = Column(String(20), unique=True, index=True)
    doi = Column(String(100), unique=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    authors = Column(Text)
    journal = Column(String(200))
    publication_date = Column(DateTime)
    study_type = Column(String(50))
    url = Column(String(500))
    source_type = Column(String(20), default="pubmed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    claim_evidence = relationship("ClaimEvidence", back_populates="evidence")


class Score(Base):
    __tablename__ = "scores"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, unique=True)
    total_score = Column(Integer, nullable=False)
    label = Column(String(20), nullable=False)
    
    # 9軸スコア
    clarity_score = Column(Integer, nullable=False)
    evidence_quality_score = Column(Integer, nullable=False)
    consensus_score = Column(Integer, nullable=False)
    biological_plausibility_score = Column(Integer, nullable=False)
    transparency_score = Column(Integer, nullable=False)
    context_distortion_score = Column(Integer, nullable=False)
    harm_potential_score = Column(Integer, nullable=False)
    virality_score = Column(Integer, nullable=False)
    correction_response_score = Column(Integer, nullable=False)
    
    confidence = Column(Float)
    processing_time = Column(Float)
    model_version = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    claim = relationship("Claim", back_populates="scores")
    rationales = relationship("Rationale", back_populates="score", cascade="all, delete-orphan")


class Rationale(Base):
    __tablename__ = "rationales"
    
    id = Column(Integer, primary_key=True, index=True)
    score_id = Column(Integer, ForeignKey("scores.id"), nullable=False)
    axis = Column(String(50), nullable=False)
    axis_score = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    score = relationship("Score", back_populates="rationales")


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    stance = Column(String(20))  # support, contradict, neutral
    relevance_score = Column(Float)
    summary = Column(Text)
    rank_position = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    claim = relationship("Claim", back_populates="claim_evidence")
    evidence = relationship("Evidence", back_populates="claim_evidence")


# Database setup
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()