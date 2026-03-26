"""
Vehicle Test Analysis - Database Models
========================================

SQLAlchemy ORM models for the vehicle test analysis system.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(
        String(50), default="engineer"
    )  # admin, engineer, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    operation_logs: Mapped[list["OperationLog"]] = relationship(
        "OperationLog", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Project(Base):
    """Project model for organizing test data."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    test_phase: Mapped[str] = mapped_column(
        String(50), default="HIL"
    )  # MIL, HIL, DVP, Vehicle
    vehicle_info: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, archived, deleted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    test_cases: Mapped[list["TestCaseModel"]] = relationship(
        "TestCaseModel", back_populates="project", cascade="all, delete-orphan"
    )
    data_files: Mapped[list["DataFile"]] = relationship(
        "DataFile", back_populates="project", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', phase='{self.test_phase}')>"


class TestCaseModel(Base):
    """Test case definition model."""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # External ID from Excel
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    test_type: Mapped[str] = mapped_column(
        String(50), default="functional"
    )  # functional, performance, safety
    priority: Mapped[str] = mapped_column(String(20), default="P2")  # P0, P1, P2, P3
    preconditions: Mapped[Optional[str]] = mapped_column(Text)
    test_steps: Mapped[Optional[str]] = mapped_column(Text)
    expected_result: Mapped[Optional[str]] = mapped_column(Text)
    source_file: Mapped[Optional[str]] = mapped_column(
        String(500)
    )  # Original Excel file
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="test_cases")
    indicators: Mapped[list["Indicator"]] = relationship(
        "Indicator", back_populates="test_case", cascade="all, delete-orphan"
    )
    test_results: Mapped[list["TestResultModel"]] = relationship(
        "TestResultModel", back_populates="test_case", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestCaseModel(id={self.id}, case_id='{self.case_id}', name='{self.name}')>"


class Indicator(Base):
    """Test indicator/metric definition model."""

    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    signal_name: Mapped[Optional[str]] = mapped_column(String(200))
    signal_source: Mapped[Optional[str]] = mapped_column(String(200))  # DBC file, etc.
    indicator_type: Mapped[str] = mapped_column(
        String(50), default="single_value"
    )  # single_value, calculated, time_domain, statistical
    formula: Mapped[Optional[str]] = mapped_column(Text)  # For calculated indicators
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    lower_limit: Mapped[Optional[float]] = mapped_column(Float)
    upper_limit: Mapped[Optional[float]] = mapped_column(Float)
    target_value: Mapped[Optional[float]] = mapped_column(Float)
    tolerance: Mapped[Optional[float]] = mapped_column(Float)
    judgment_criteria: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    test_case: Mapped["TestCaseModel"] = relationship(
        "TestCaseModel", back_populates="indicators"
    )
    results: Mapped[list["IndicatorResult"]] = relationship(
        "IndicatorResult", back_populates="indicator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Indicator(id={self.id}, name='{self.name}', type='{self.indicator_type}')>"


class DataFile(Base):
    """Imported data file model."""

    __tablename__ = "data_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # Bytes
    file_type: Mapped[str] = mapped_column(String(50))  # blf, asc, mdf, csv, etc.
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA256
    collection_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    time_range_start: Mapped[Optional[float]] = mapped_column(
        Float
    )  # Timestamp in seconds
    time_range_end: Mapped[Optional[float]] = mapped_column(Float)
    data_points: Mapped[Optional[int]] = mapped_column(Integer)
    signal_count: Mapped[Optional[int]] = mapped_column(Integer)
    file_metadata: Mapped[Optional[str]] = mapped_column(Text)  # JSON format
    import_status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, parsing, parsed, error
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="data_files")
    signals: Mapped[list["Signal"]] = relationship(
        "Signal", back_populates="data_file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataFile(id={self.id}, name='{self.file_name}', type='{self.file_type}')>"


class Signal(Base):
    """Signal metadata model."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_file_id: Mapped[int] = mapped_column(
        ForeignKey("data_files.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(Integer)  # CAN message ID
    message_name: Mapped[Optional[str]] = mapped_column(String(200))
    dbc_file: Mapped[Optional[str]] = mapped_column(String(500))
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    data_type: Mapped[str] = mapped_column(String(50))  # float, int, bool, string
    sample_rate: Mapped[Optional[float]] = mapped_column(Float)  # Hz
    min_value: Mapped[Optional[float]] = mapped_column(Float)
    max_value: Mapped[Optional[float]] = mapped_column(Float)
    value_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    data_file: Mapped["DataFile"] = relationship("DataFile", back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal(id={self.id}, name='{self.name}', unit='{self.unit}')>"


class TestResultModel(Base):
    """Test execution result model."""

    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id"), nullable=False
    )
    execution_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    result: Mapped[str] = mapped_column(String(50))  # pass, fail, inconclusive, not_run
    result_adjusted: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # Manual adjustment
    adjustment_reason: Mapped[Optional[str]] = mapped_column(Text)
    adjusted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    adjusted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    test_case: Mapped["TestCaseModel"] = relationship(
        "TestCaseModel", back_populates="test_results"
    )
    indicator_results: Mapped[list["IndicatorResult"]] = relationship(
        "IndicatorResult", back_populates="test_result", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestResultModel(id={self.id}, result='{self.result}')>"


class IndicatorResult(Base):
    """Individual indicator calculation result model."""

    __tablename__ = "indicator_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_result_id: Mapped[int] = mapped_column(
        ForeignKey("test_results.id"), nullable=False
    )
    indicator_id: Mapped[int] = mapped_column(
        ForeignKey("indicators.id"), nullable=False
    )
    calculated_value: Mapped[Optional[float]] = mapped_column(Float)
    raw_value: Mapped[Optional[float]] = mapped_column(
        Float
    )  # Before any transformation
    result: Mapped[str] = mapped_column(String(50))  # pass, fail, inconclusive
    data_source: Mapped[Optional[str]] = mapped_column(
        Text
    )  # JSON: file, time range, etc.
    calculation_details: Mapped[Optional[str]] = mapped_column(
        Text
    )  # JSON: formula, intermediate values
    time_range_start: Mapped[Optional[float]] = mapped_column(Float)
    time_range_end: Mapped[Optional[float]] = mapped_column(Float)
    data_points_used: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    test_result: Mapped["TestResultModel"] = relationship(
        "TestResultModel", back_populates="indicator_results"
    )
    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="results")

    def __repr__(self) -> str:
        return f"<IndicatorResult(id={self.id}, value={self.calculated_value}, result='{self.result}')>"


class Report(Base):
    """Generated report model."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(50), default="formal"
    )  # formal, audit
    format: Mapped[str] = mapped_column(String(20), default="docx")  # docx, pdf
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    template_used: Mapped[Optional[str]] = mapped_column(String(200))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(
        String(50), default="generated"
    )  # generated, reviewed, approved, archived

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, name='{self.name}', type='{self.report_type}')>"


class OperationLog(Base):
    """User operation log model."""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # project, test_case, report, etc.
    target_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[Optional[str]] = mapped_column(Text)  # JSON format
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="operation_logs")

    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, operation='{self.operation}')>"


# Database initialization function
def init_database(database_url: str = "sqlite:///database/vehicle_test.db") -> None:
    """Initialize database and create all tables."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully.")
