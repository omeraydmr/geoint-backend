"""Geographic models for GEOINT functionality"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class RegionType(enum.Enum):
    """Types of geographic regions"""
    PROVINCE = "PROVINCE"
    DISTRICT = "DISTRICT"
    NEIGHBORHOOD = "NEIGHBORHOOD"


class Province(Base):
    """Turkish provinces (İller) - 81 total"""
    __tablename__ = "provinces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(2), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    region = Column(String(50))  # Marmara, Ege, etc.
    population = Column(Integer)
    area_km2 = Column(Float)

    # Geospatial columns with GIST indexes for spatial queries
    geom = Column(Geometry('MULTIPOLYGON', srid=4326), nullable=False)
    centroid = Column(Geometry('POINT', srid=4326))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    districts = relationship("District", back_populates="province", cascade="all, delete-orphan")

    # Spatial indexes (GIST) for optimal query performance
    __table_args__ = (
        Index('idx_provinces_geom_gist', 'geom', postgresql_using='gist'),
        Index('idx_provinces_centroid_gist', 'centroid', postgresql_using='gist'),
    )

    def __repr__(self):
        return f"<Province {self.code}: {self.name}>"


class District(Base):
    """Turkish districts (İlçeler) - ~970 total"""
    __tablename__ = "districts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    province_id = Column(UUID(as_uuid=True), ForeignKey('provinces.id'), nullable=False)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    population = Column(Integer)
    area_km2 = Column(Float)

    # Geospatial columns with GIST indexes for spatial queries
    geom = Column(Geometry('MULTIPOLYGON', srid=4326), nullable=False)
    centroid = Column(Geometry('POINT', srid=4326))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    province = relationship("Province", back_populates="districts")
    neighborhoods = relationship("Neighborhood", back_populates="district", cascade="all, delete-orphan")

    # Indexes (including spatial GIST indexes)
    __table_args__ = (
        Index('idx_districts_province', 'province_id'),
        Index('idx_districts_geom_gist', 'geom', postgresql_using='gist'),
        Index('idx_districts_centroid_gist', 'centroid', postgresql_using='gist'),
    )

    def __repr__(self):
        return f"<District {self.code}: {self.name}>"


class Neighborhood(Base):
    """Turkish neighborhoods (Mahalleler) - ~50,000 total"""
    __tablename__ = "neighborhoods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id = Column(UUID(as_uuid=True), ForeignKey('districts.id'), nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    neighborhood_type = Column(String(20))  # 'Mahalle', 'Köy', etc.

    # Geospatial columns with GIST indexes for spatial queries
    geom = Column(Geometry('MULTIPOLYGON', srid=4326))
    centroid = Column(Geometry('POINT', srid=4326))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    district = relationship("District", back_populates="neighborhoods")

    # Indexes (including spatial GIST indexes)
    __table_args__ = (
        Index('idx_neighborhoods_district', 'district_id'),
        Index('idx_neighborhoods_geom_gist', 'geom', postgresql_using='gist'),
        Index('idx_neighborhoods_centroid_gist', 'centroid', postgresql_using='gist'),
    )

    def __repr__(self):
        return f"<Neighborhood {self.code}: {self.name}>"


class GEOINTScore(Base):
    """
    GEOINT scores for keywords by region

    Formula: Score = (0.4 × Search_Index) + (0.25 × Trend_Score) +
                     (0.20 × Demo_Fit) + (0.15 × Competition_Gap)
    """
    __tablename__ = "geoint_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey('keywords.id', ondelete='CASCADE'), nullable=False)

    # Region reference (polymorphic)
    region_type = Column(Enum(RegionType, name="regiontype", create_type=False), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)

    # Score components (0-100)
    search_index = Column(Float, default=0)
    trend_score = Column(Float, default=0)
    demographic_fit = Column(Float, default=0)
    competition_gap = Column(Float, default=0)

    # Composite score (0-100)
    geoint_score = Column(Float, nullable=False, index=True)

    # Trend metadata
    trend_direction = Column(String(10))  # 'up', 'down', 'stable'
    trend_change_pct = Column(Float)

    # Raw data for debugging/analysis
    raw_data = Column(JSONB)

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_geoint_keyword', 'keyword_id'),
        Index('idx_geoint_region', 'region_type', 'region_id'),
        Index('idx_geoint_score', 'geoint_score'),
        Index('idx_geoint_keyword_region', 'keyword_id', 'region_type', 'region_id', unique=True),
    )

    def __repr__(self):
        return f"<GEOINTScore {self.keyword_id[:8]}... - {self.region_type.value}: {self.geoint_score}>"
