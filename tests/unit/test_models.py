"""Unit tests for database models."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import (
    Base,
    User,
    Project,
    TestCaseModel,
    Indicator,
    DataFile,
    Signal,
    TestResultModel,
    IndicatorResult,
    Report,
    OperationLog,
    init_database,
)


class TestDatabaseModels:
    """Tests for database ORM models."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create in-memory database engine."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create database session."""
        with Session(engine) as session:
            yield session

    def test_create_user(self, session):
        """Test creating a user."""
        user = User(
            username="testuser",
            password_hash="hashed_password",
            email="test@example.com",
            full_name="Test User",
            role="engineer",
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == "engineer"
        assert user.is_active is True

    def test_create_project(self, session):
        """Test creating a project."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(
            name="Test Project",
            description="Test description",
            owner_id=user.id,
            test_phase="HIL",
        )
        session.add(project)
        session.commit()

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.test_phase == "HIL"

    def test_project_user_relationship(self, session):
        """Test project-user relationship."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        # Test relationship
        assert project.owner.username == "owner"
        assert len(user.projects) == 1
        assert user.projects[0].name == "Test"

    def test_create_test_case(self, session):
        """Test creating a test case."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        test_case = TestCaseModel(
            project_id=project.id,
            case_id="TC001",
            name="Test Case 1",
            test_type="functional",
            priority="P1",
        )
        session.add(test_case)
        session.commit()

        assert test_case.id is not None
        assert test_case.case_id == "TC001"

    def test_create_indicator(self, session):
        """Test creating an indicator."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        test_case = TestCaseModel(
            project_id=project.id,
            case_id="TC001",
            name="Test Case",
        )
        session.add(test_case)
        session.commit()

        indicator = Indicator(
            test_case_id=test_case.id,
            name="Speed",
            signal_name="VehicleSpeed",
            indicator_type="single_value",
            unit="km/h",
            lower_limit=0.0,
            upper_limit=200.0,
        )
        session.add(indicator)
        session.commit()

        assert indicator.id is not None
        assert indicator.name == "Speed"

    def test_create_data_file(self, session):
        """Test creating a data file record."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        data_file = DataFile(
            project_id=project.id,
            file_name="test.blf",
            file_path="/data/test.blf",
            file_size=1024,
            file_type="blf",
        )
        session.add(data_file)
        session.commit()

        assert data_file.id is not None
        assert data_file.file_name == "test.blf"

    def test_create_signal(self, session):
        """Test creating a signal record."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        data_file = DataFile(
            project_id=project.id,
            file_name="test.blf",
            file_path="/data/test.blf",
            file_type="blf",
        )
        session.add(data_file)
        session.commit()

        signal = Signal(
            data_file_id=data_file.id,
            name="VehicleSpeed",
            unit="km/h",
            data_type="float",
            value_count=1000,
        )
        session.add(signal)
        session.commit()

        assert signal.id is not None
        assert signal.name == "VehicleSpeed"

    def test_create_test_result(self, session):
        """Test creating a test result."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        test_case = TestCaseModel(
            project_id=project.id,
            case_id="TC001",
            name="Test Case",
        )
        session.add(test_case)
        session.commit()

        result = TestResultModel(
            test_case_id=test_case.id,
            result="pass",
        )
        session.add(result)
        session.commit()

        assert result.id is not None
        assert result.result == "pass"

    def test_create_indicator_result(self, session):
        """Test creating an indicator result."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        test_case = TestCaseModel(
            project_id=project.id,
            case_id="TC001",
            name="Test Case",
        )
        session.add(test_case)
        session.commit()

        indicator = Indicator(
            test_case_id=test_case.id,
            name="Speed",
            indicator_type="single_value",
        )
        session.add(indicator)
        session.commit()

        test_result = TestResultModel(
            test_case_id=test_case.id,
            result="pass",
        )
        session.add(test_result)
        session.commit()

        indicator_result = IndicatorResult(
            test_result_id=test_result.id,
            indicator_id=indicator.id,
            calculated_value=50.0,
            result="pass",
        )
        session.add(indicator_result)
        session.commit()

        assert indicator_result.id is not None
        assert indicator_result.calculated_value == 50.0

    def test_create_report(self, session):
        """Test creating a report."""
        user = User(username="owner", password_hash="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        report = Report(
            project_id=project.id,
            name="Test Report",
            report_type="formal",
            format="docx",
            generated_by=user.id,
        )
        session.add(report)
        session.commit()

        assert report.id is not None
        assert report.name == "Test Report"

    def test_create_operation_log(self, session):
        """Test creating an operation log."""
        user = User(username="user", password_hash="hash")
        session.add(user)
        session.commit()

        log = OperationLog(
            user_id=user.id,
            operation="login",
            target_type="session",
        )
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.operation == "login"

    def test_user_repr(self, session):
        """Test user string representation."""
        user = User(username="testuser", password_hash="hash")
        assert "testuser" in repr(user)

    def test_project_repr(self, session):
        """Test project string representation."""
        project = Project(name="Test Project")
        assert "Test Project" in repr(project)


class TestInitDatabase:
    """Tests for database initialization."""

    def test_init_database(self, tmp_path):
        """Test database initialization."""
        db_path = tmp_path / "test_init.db"
        db_url = f"sqlite:///{db_path}"
        init_database(db_url)

        assert db_path.exists()
