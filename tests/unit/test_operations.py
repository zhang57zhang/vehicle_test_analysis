"""
Unit tests for database operations module - focused on coverage gaps.

This test file specifically targets uncovered branches in operations.py
to achieve 95%+ coverage.
"""

import os
import tempfile
from datetime import datetime

import pytest

from src.database.models import (
    Base,
    DataFile,
    Indicator,
    IndicatorResult,
    OperationLog,
    Project,
    Report,
    Signal,
    TestCase,
    TestResult,
    User,
)
from src.database.operations import DatabaseManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db_url = f"sqlite:///{db_path}"
    db_manager = DatabaseManager(db_url)
    db_manager.initialize()
    
    yield db_manager
    
    # Cleanup - dispose engine first to close all connections
    db_manager.engine.dispose()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def sample_user(temp_db):
    """Create a sample user for testing."""
    return temp_db.create_user("testuser", "hashed_password", "test@example.com")


@pytest.fixture
def sample_project(temp_db, sample_user):
    """Create a sample project for testing."""
    return temp_db.create_project("Test Project", sample_user.id)


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization."""

    def test_initialize_creates_directory(self):
        """Test that initialize creates the database directory for SQLite URLs."""
        # Use a path with a subdirectory that doesn't exist
        tmpdir = tempfile.mkdtemp()
        try:
            subdir = os.path.join(tmpdir, "nested", "deep")
            db_path = os.path.join(subdir, "test.db")
            db_url = f"sqlite:///{db_path}"
            
            # Directory should not exist yet
            assert not os.path.exists(subdir)
            
            db_manager = DatabaseManager(db_url)
            db_manager.initialize()
            
            # Directory should now exist
            assert os.path.exists(subdir)
            assert db_manager._initialized is True
            
            # Close the engine to release the file lock on Windows
            db_manager.engine.dispose()
        finally:
            # Cleanup - try to remove the directory
            import shutil
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def test_initialize_idempotent(self, temp_db):
        """Test that initialize can be called multiple times safely."""
        assert temp_db._initialized is True
        temp_db.initialize()  # Should not raise
        assert temp_db._initialized is True

    def test_session_context_exception_handling(self, temp_db):
        """Test that session context manager handles exceptions correctly."""
        # Test that exception causes rollback and is re-raised
        with pytest.raises(ValueError):
            with temp_db.session() as session:
                raise ValueError("Test exception")
        
        # Session should still work after exception
        with temp_db.session() as session:
            assert session is not None


class TestUserOperationsCoverage:
    """Tests for uncovered user operation branches."""

    def test_get_user_by_username_not_found(self, temp_db):
        """Test getting a user by username that doesn't exist."""
        user = temp_db.get_user_by_username("nonexistent")
        assert user is None

    def test_list_users_include_inactive(self, temp_db):
        """Test listing users including inactive ones."""
        user1 = temp_db.create_user("active_user", "hash1")
        user2 = temp_db.create_user("inactive_user", "hash2")
        
        # Deactivate user2
        with temp_db.session() as session:
            db_user = session.get(User, user2.id)
            db_user.is_active = False
        
        # List only active users
        active_users = temp_db.list_users(active_only=True)
        assert len(active_users) == 1
        assert active_users[0].username == "active_user"
        
        # List all users
        all_users = temp_db.list_users(active_only=False)
        assert len(all_users) == 2


class TestProjectOperationsCoverage:
    """Tests for uncovered project operation branches."""

    def test_list_projects_by_status(self, temp_db, sample_user):
        """Test listing projects filtered by status."""
        project1 = temp_db.create_project("Project 1", sample_user.id)
        project2 = temp_db.create_project("Project 2", sample_user.id)
        
        # Update project2 status
        with temp_db.session() as session:
            db_project = session.get(Project, project2.id)
            db_project.status = "archived"
        
        # List only active projects
        active_projects = temp_db.list_projects(status="active")
        assert len(active_projects) == 1
        assert active_projects[0].name == "Project 1"
        
        # List archived projects
        archived_projects = temp_db.list_projects(status="archived")
        assert len(archived_projects) == 1
        assert archived_projects[0].name == "Project 2"

    def test_update_project_not_found(self, temp_db):
        """Test updating a project that doesn't exist."""
        result = temp_db.update_project(999, name="New Name")
        assert result is None

    def test_delete_project_not_found(self, temp_db):
        """Test deleting a project that doesn't exist."""
        result = temp_db.delete_project(999)
        assert result is False


class TestCaseOperationsCoverage:
    """Tests for uncovered test case operation branches."""

    def test_get_test_case_not_found(self, temp_db):
        """Test getting a test case that doesn't exist."""
        result = temp_db.get_test_case(999)
        assert result is None


class TestIndicatorOperationsCoverage:
    """Tests for uncovered indicator operation branches."""

    def test_get_indicator_not_found(self, temp_db):
        """Test getting an indicator that doesn't exist."""
        result = temp_db.get_indicator(999)
        assert result is None


class TestDataFileOperationsCoverage:
    """Tests for uncovered data file operation branches."""

    def test_get_data_file_not_found(self, temp_db):
        """Test getting a data file that doesn't exist."""
        result = temp_db.get_data_file(999)
        assert result is None


class TestTestResultOperationsCoverage:
    """Tests for uncovered test result operation branches."""

    def test_get_test_result_not_found(self, temp_db):
        """Test getting a test result that doesn't exist."""
        result = temp_db.get_test_result(999)
        assert result is None

    def test_adjust_test_result_not_found(self, temp_db):
        """Test adjusting a test result that doesn't exist."""
        result = temp_db.adjust_test_result(
            999,
            adjusted_result="pass",
            adjustment_reason="Test",
            adjusted_by=1,
        )
        assert result is None


class TestReportOperationsCoverage:
    """Tests for uncovered report operation branches."""

    def test_get_report_not_found(self, temp_db):
        """Test getting a report that doesn't exist."""
        result = temp_db.get_report(999)
        assert result is None


class TestUtilityMethodsCoverage:
    """Tests for uncovered utility method branches."""

    def test_execute_raw(self, temp_db):
        """Test executing raw SQL."""
        from sqlalchemy import text
        result = temp_db.execute_raw(text("SELECT 1"))
        assert result is not None

    def test_execute_raw_with_data(self, temp_db, sample_user):
        """Test executing raw SQL that returns data."""
        from sqlalchemy import text
        result = temp_db.execute_raw(text("SELECT * FROM users"))
        assert result is not None


class TestFullParameterCoverage:
    """Tests for full parameter coverage in create methods."""

    def test_create_user_all_params(self, temp_db):
        """Test creating a user with all parameters."""
        user = temp_db.create_user(
            username="fulluser",
            password_hash="hash",
            email="full@example.com",
            full_name="Full User Name",
            role="admin",
        )
        assert user.username == "fulluser"
        assert user.email == "full@example.com"
        assert user.full_name == "Full User Name"
        assert user.role == "admin"

    def test_create_project_all_params(self, temp_db, sample_user):
        """Test creating a project with all parameters."""
        project = temp_db.create_project(
            name="Full Project",
            owner_id=sample_user.id,
            description="Full description",
            test_phase="MIL",
            vehicle_info="Test Vehicle",
        )
        assert project.name == "Full Project"
        assert project.description == "Full description"
        assert project.test_phase == "MIL"
        assert project.vehicle_info == "Test Vehicle"

    def test_create_test_case_all_params(self, temp_db, sample_project):
        """Test creating a test case with all parameters."""
        test_case = temp_db.create_test_case(
            project_id=sample_project.id,
            case_id="TC001",
            name="Test Case",
            description="Description",
            test_type="performance",
            priority="P0",
            preconditions="Preconditions",
            test_steps="Steps",
            expected_result="Expected",
            source_file="test.xlsx",
        )
        assert test_case.case_id == "TC001"
        assert test_case.description == "Description"
        assert test_case.test_type == "performance"
        assert test_case.priority == "P0"
        assert test_case.preconditions == "Preconditions"
        assert test_case.test_steps == "Steps"
        assert test_case.expected_result == "Expected"
        assert test_case.source_file == "test.xlsx"

    def test_create_indicator_all_params(self, temp_db, sample_project):
        """Test creating an indicator with all parameters."""
        test_case = temp_db.create_test_case(sample_project.id, "TC001", "Test")
        indicator = temp_db.create_indicator(
            test_case_id=test_case.id,
            name="Indicator",
            signal_name="Signal1",
            indicator_type="calculated",
            formula="a + b",
            unit="ms",
            lower_limit=0.0,
            upper_limit=100.0,
            target_value=50.0,
            tolerance=5.0,
            description="Description",
        )
        assert indicator.name == "Indicator"
        assert indicator.signal_name == "Signal1"
        assert indicator.indicator_type == "calculated"
        assert indicator.formula == "a + b"
        assert indicator.unit == "ms"
        assert indicator.lower_limit == 0.0
        assert indicator.upper_limit == 100.0
        assert indicator.target_value == 50.0
        assert indicator.tolerance == 5.0
        assert indicator.description == "Description"

    def test_create_data_file_all_params(self, temp_db, sample_project):
        """Test creating a data file with all parameters."""
        now = datetime.utcnow()
        data_file = temp_db.create_data_file(
            project_id=sample_project.id,
            file_name="test.blf",
            file_path="/data/test.blf",
            file_type="blf",
            file_size=1024,
            file_hash="abc123",
            collection_time=now,
            time_range_start=0.0,
            time_range_end=10.0,
            data_points=1000,
            signal_count=50,
            file_metadata='{"key": "value"}',
        )
        assert data_file.file_name == "test.blf"
        assert data_file.file_size == 1024
        assert data_file.file_hash == "abc123"
        assert data_file.collection_time is not None
        assert data_file.time_range_start == 0.0
        assert data_file.time_range_end == 10.0
        assert data_file.data_points == 1000
        assert data_file.signal_count == 50
        assert data_file.file_metadata == '{"key": "value"}'

    def test_create_signal_all_params(self, temp_db, sample_project):
        """Test creating a signal with all parameters."""
        data_file = temp_db.create_data_file(
            sample_project.id, "test.blf", "/data/test.blf", "blf"
        )
        signal = temp_db.create_signal(
            data_file_id=data_file.id,
            name="Signal1",
            data_type="float",
            message_id=0x123,
            message_name="Message1",
            dbc_file="test.dbc",
            unit="km/h",
            sample_rate=100.0,
            min_value=0.0,
            max_value=300.0,
            value_count=1000,
        )
        assert signal.name == "Signal1"
        assert signal.data_type == "float"
        assert signal.message_id == 0x123
        assert signal.message_name == "Message1"
        assert signal.dbc_file == "test.dbc"
        assert signal.unit == "km/h"
        assert signal.sample_rate == 100.0
        assert signal.min_value == 0.0
        assert signal.max_value == 300.0
        assert signal.value_count == 1000

    def test_create_indicator_result_all_params(self, temp_db, sample_project):
        """Test creating an indicator result with all parameters."""
        test_case = temp_db.create_test_case(sample_project.id, "TC001", "Test")
        indicator = temp_db.create_indicator(test_case.id, "Indicator")
        test_result = temp_db.create_test_result(test_case.id, "pass")
        
        result = temp_db.create_indicator_result(
            test_result_id=test_result.id,
            indicator_id=indicator.id,
            result="pass",
            calculated_value=42.5,
            raw_value=42.0,
            data_source='{"file": "test.blf"}',
            calculation_details='{"formula": "max"}',
            time_range_start=0.0,
            time_range_end=5.0,
            data_points_used=500,
        )
        assert result.result == "pass"
        assert result.calculated_value == 42.5
        assert result.raw_value == 42.0
        assert result.data_source == '{"file": "test.blf"}'
        assert result.calculation_details == '{"formula": "max"}'
        assert result.time_range_start == 0.0
        assert result.time_range_end == 5.0
        assert result.data_points_used == 500

    def test_create_report_all_params(self, temp_db, sample_user, sample_project):
        """Test creating a report with all parameters."""
        report = temp_db.create_report(
            project_id=sample_project.id,
            name="Full Report",
            generated_by=sample_user.id,
            report_type="audit",
            format="pdf",
            file_path="/reports/report.pdf",
            template_used="audit_template.docx",
        )
        assert report.name == "Full Report"
        assert report.report_type == "audit"
        assert report.format == "pdf"
        assert report.file_path == "/reports/report.pdf"
        assert report.template_used == "audit_template.docx"

    def test_log_operation_all_params(self, temp_db, sample_user):
        """Test logging an operation with all parameters."""
        log = temp_db.log_operation(
            user_id=sample_user.id,
            operation="create_project",
            target_type="project",
            target_id=1,
            details='{"name": "Test"}',
            ip_address="192.168.1.1",
        )
        assert log.operation == "create_project"
        assert log.target_type == "project"
        assert log.target_id == 1
        assert log.details == '{"name": "Test"}'
        assert log.ip_address == "192.168.1.1"


class TestListTestCasesWithFilter:
    """Tests for test case listing with type filter."""

    def test_list_test_cases_by_type(self, temp_db, sample_project):
        """Test listing test cases filtered by type."""
        temp_db.create_test_case(
            sample_project.id, "TC001", "Functional Test", test_type="functional"
        )
        temp_db.create_test_case(
            sample_project.id, "TC002", "Performance Test", test_type="performance"
        )
        
        functional_cases = temp_db.list_test_cases(
            sample_project.id, test_type="functional"
        )
        assert len(functional_cases) == 1
        assert functional_cases[0].test_type == "functional"
        
        performance_cases = temp_db.list_test_cases(
            sample_project.id, test_type="performance"
        )
        assert len(performance_cases) == 1
        assert performance_cases[0].test_type == "performance"


class TestUserNotFound:
    """Tests for user not found branches."""

    def test_get_user_not_found(self, temp_db):
        """Test getting a user that doesn't exist."""
        user = temp_db.get_user(999)
        assert user is None


class TestProjectNotFound:
    """Tests for project not found branches."""

    def test_get_project_not_found(self, temp_db):
        """Test getting a project that doesn't exist."""
        project = temp_db.get_project(999)
        assert project is None


class TestListOperations:
    """Tests for list operations."""

    def test_list_projects_by_owner(self, temp_db, sample_user):
        """Test listing projects filtered by owner."""
        user2 = temp_db.create_user("user2", "hash2")
        project1 = temp_db.create_project("Project 1", sample_user.id)
        project2 = temp_db.create_project("Project 2", user2.id)
        
        # List projects by owner
        user1_projects = temp_db.list_projects(owner_id=sample_user.id)
        assert len(user1_projects) == 1
        assert user1_projects[0].name == "Project 1"
        
        user2_projects = temp_db.list_projects(owner_id=user2.id)
        assert len(user2_projects) == 1
        assert user2_projects[0].name == "Project 2"

    def test_list_indicators(self, temp_db, sample_project):
        """Test listing indicators for a test case."""
        test_case = temp_db.create_test_case(sample_project.id, "TC001", "Test")
        indicator1 = temp_db.create_indicator(test_case.id, "Indicator 1")
        indicator2 = temp_db.create_indicator(test_case.id, "Indicator 2")
        
        indicators = temp_db.list_indicators(test_case.id)
        assert len(indicators) == 2

    def test_list_data_files(self, temp_db, sample_project):
        """Test listing data files for a project."""
        data_file1 = temp_db.create_data_file(
            sample_project.id, "file1.blf", "/data/file1.blf", "blf"
        )
        data_file2 = temp_db.create_data_file(
            sample_project.id, "file2.blf", "/data/file2.blf", "blf"
        )
        
        data_files = temp_db.list_data_files(sample_project.id)
        assert len(data_files) == 2

    def test_list_signals(self, temp_db, sample_project):
        """Test listing signals for a data file."""
        data_file = temp_db.create_data_file(
            sample_project.id, "test.blf", "/data/test.blf", "blf"
        )
        signal1 = temp_db.create_signal(data_file.id, "Signal1")
        signal2 = temp_db.create_signal(data_file.id, "Signal2")
        
        signals = temp_db.list_signals(data_file.id)
        assert len(signals) == 2

    def test_list_indicator_results(self, temp_db, sample_project):
        """Test listing indicator results for a test result."""
        test_case = temp_db.create_test_case(sample_project.id, "TC001", "Test")
        indicator = temp_db.create_indicator(test_case.id, "Indicator")
        test_result = temp_db.create_test_result(test_case.id, "pass")
        
        result1 = temp_db.create_indicator_result(
            test_result.id, indicator.id, "pass"
        )
        result2 = temp_db.create_indicator_result(
            test_result.id, indicator.id, "pass"
        )
        
        results = temp_db.list_indicator_results(test_result.id)
        assert len(results) == 2

    def test_list_reports(self, temp_db, sample_user, sample_project):
        """Test listing reports for a project."""
        report1 = temp_db.create_report(
            sample_project.id, "Report 1", sample_user.id
        )
        report2 = temp_db.create_report(
            sample_project.id, "Report 2", sample_user.id
        )
        
        reports = temp_db.list_reports(sample_project.id)
        assert len(reports) == 2

    def test_list_operation_logs(self, temp_db, sample_user):
        """Test listing operation logs."""
        log1 = temp_db.log_operation(sample_user.id, "operation1")
        log2 = temp_db.log_operation(sample_user.id, "operation2")
        
        logs = temp_db.list_operation_logs(user_id=sample_user.id)
        assert len(logs) == 2
        
        all_logs = temp_db.list_operation_logs()
        assert len(all_logs) == 2


class TestCountRecords:
    """Tests for count_records utility."""

    def test_count_records(self, temp_db, sample_user, sample_project):
        """Test counting records in a table."""
        count = temp_db.count_records(User)
        assert count == 1
        
        count = temp_db.count_records(Project)
        assert count == 1


class TestAdjustTestResult:
    """Tests for adjust_test_result."""

    def test_adjust_test_result_success(self, temp_db, sample_project):
        """Test adjusting a test result successfully."""
        test_case = temp_db.create_test_case(sample_project.id, "TC001", "Test")
        test_result = temp_db.create_test_result(test_case.id, "fail")
        
        adjusted = temp_db.adjust_test_result(
            test_result.id,
            adjusted_result="pass",
            adjustment_reason="False negative",
            adjusted_by=1,
        )
        assert adjusted is not None
        assert adjusted.result_adjusted == "pass"
        assert adjusted.adjustment_reason == "False negative"
        assert adjusted.adjusted_by == 1
