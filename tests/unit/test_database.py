"""Unit tests for database module."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

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
    init_database,
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


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_initialize(self, temp_db):
        """Test database initialization."""
        assert temp_db._initialized is True

    def test_session_context(self, temp_db):
        """Test session context manager."""
        with temp_db.session() as session:
            assert session is not None


class TestUserOperations:
    """Tests for user operations."""

    def test_create_user(self, temp_db):
        """Test creating a user."""
        user = temp_db.create_user(
            username="testuser",
            password_hash="hashed_password",
            email="test@example.com",
            full_name="Test User",
            role="engineer",
        )
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "engineer"
        assert user.is_active is True

    def test_get_user(self, temp_db):
        """Test getting a user by ID."""
        created = temp_db.create_user(
            username="testuser",
            password_hash="hashed_password",
        )
        
        user = temp_db.get_user(created.id)
        assert user is not None
        assert user.username == "testuser"

    def test_get_user_not_found(self, temp_db):
        """Test getting a non-existent user."""
        user = temp_db.get_user(999)
        assert user is None

    def test_get_user_by_username(self, temp_db):
        """Test getting a user by username."""
        temp_db.create_user(
            username="testuser",
            password_hash="hashed_password",
        )
        
        user = temp_db.get_user_by_username("testuser")
        assert user is not None
        assert user.username == "testuser"

    def test_list_users(self, temp_db):
        """Test listing users."""
        temp_db.create_user("user1", "hash1")
        temp_db.create_user("user2", "hash2")
        
        users = temp_db.list_users()
        assert len(users) == 2


class TestProjectOperations:
    """Tests for project operations."""

    def test_create_project(self, temp_db):
        """Test creating a project."""
        user = temp_db.create_user("testuser", "hash")
        
        project = temp_db.create_project(
            name="Test Project",
            owner_id=user.id,
            description="Test description",
            test_phase="HIL",
        )
        
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.owner_id == user.id
        assert project.test_phase == "HIL"

    def test_get_project(self, temp_db):
        """Test getting a project by ID."""
        user = temp_db.create_user("testuser", "hash")
        created = temp_db.create_project("Test Project", user.id)
        
        project = temp_db.get_project(created.id)
        assert project is not None
        assert project.name == "Test Project"

    def test_list_projects(self, temp_db):
        """Test listing projects."""
        user = temp_db.create_user("testuser", "hash")
        temp_db.create_project("Project 1", user.id)
        temp_db.create_project("Project 2", user.id)
        
        projects = temp_db.list_projects()
        assert len(projects) == 2

    def test_list_projects_by_owner(self, temp_db):
        """Test listing projects by owner."""
        user1 = temp_db.create_user("user1", "hash1")
        user2 = temp_db.create_user("user2", "hash2")
        
        temp_db.create_project("Project 1", user1.id)
        temp_db.create_project("Project 2", user2.id)
        
        projects = temp_db.list_projects(owner_id=user1.id)
        assert len(projects) == 1
        assert projects[0].name == "Project 1"

    def test_update_project(self, temp_db):
        """Test updating a project."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        updated = temp_db.update_project(
            project.id,
            name="Updated Project",
            description="New description",
        )
        
        assert updated is not None
        assert updated.name == "Updated Project"
        assert updated.description == "New description"

    def test_delete_project(self, temp_db):
        """Test deleting a project."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        result = temp_db.delete_project(project.id)
        assert result is True
        
        deleted = temp_db.get_project(project.id)
        assert deleted is None


class TestCaseOperations:
    """Tests for test case operations."""

    def test_create_test_case(self, temp_db):
        """Test creating a test case."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        test_case = temp_db.create_test_case(
            project_id=project.id,
            case_id="TC001",
            name="Test Case 1",
            test_type="functional",
            priority="P1",
        )
        
        assert test_case.id is not None
        assert test_case.case_id == "TC001"
        assert test_case.name == "Test Case 1"
        assert test_case.test_type == "functional"

    def test_get_test_case(self, temp_db):
        """Test getting a test case by ID."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        created = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        
        test_case = temp_db.get_test_case(created.id)
        assert test_case is not None
        assert test_case.case_id == "TC001"

    def test_list_test_cases(self, temp_db):
        """Test listing test cases."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        temp_db.create_test_case(project.id, "TC002", "Test Case 2")
        
        test_cases = temp_db.list_test_cases(project.id)
        assert len(test_cases) == 2


class TestIndicatorOperations:
    """Tests for indicator operations."""

    def test_create_indicator(self, temp_db):
        """Test creating an indicator."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        
        indicator = temp_db.create_indicator(
            test_case_id=test_case.id,
            name="Response Time",
            signal_name="VehicleSpeed",
            indicator_type="time_domain",
            unit="s",
            upper_limit=1.0,
        )
        
        assert indicator.id is not None
        assert indicator.name == "Response Time"
        assert indicator.signal_name == "VehicleSpeed"

    def test_get_indicator(self, temp_db):
        """Test getting an indicator by ID."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        created = temp_db.create_indicator(test_case.id, "Indicator 1")
        
        indicator = temp_db.get_indicator(created.id)
        assert indicator is not None
        assert indicator.name == "Indicator 1"

    def test_list_indicators(self, temp_db):
        """Test listing indicators."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        
        temp_db.create_indicator(test_case.id, "Indicator 1")
        temp_db.create_indicator(test_case.id, "Indicator 2")
        
        indicators = temp_db.list_indicators(test_case.id)
        assert len(indicators) == 2


class TestDataFileOperations:
    """Tests for data file operations."""

    def test_create_data_file(self, temp_db):
        """Test creating a data file record."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        data_file = temp_db.create_data_file(
            project_id=project.id,
            file_name="test.blf",
            file_path="/data/test.blf",
            file_type="blf",
            file_size=1024,
        )
        
        assert data_file.id is not None
        assert data_file.file_name == "test.blf"
        assert data_file.file_type == "blf"

    def test_get_data_file(self, temp_db):
        """Test getting a data file by ID."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        created = temp_db.create_data_file(
            project.id, "test.blf", "/data/test.blf", "blf"
        )
        
        data_file = temp_db.get_data_file(created.id)
        assert data_file is not None
        assert data_file.file_name == "test.blf"

    def test_list_data_files(self, temp_db):
        """Test listing data files."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        temp_db.create_data_file(project.id, "file1.blf", "/data/file1.blf", "blf")
        temp_db.create_data_file(project.id, "file2.mf4", "/data/file2.mf4", "mf4")
        
        data_files = temp_db.list_data_files(project.id)
        assert len(data_files) == 2


class TestSignalOperations:
    """Tests for signal operations."""

    def test_create_signal(self, temp_db):
        """Test creating a signal record."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        data_file = temp_db.create_data_file(
            project.id, "test.blf", "/data/test.blf", "blf"
        )
        
        signal = temp_db.create_signal(
            data_file_id=data_file.id,
            name="VehicleSpeed",
            data_type="float",
            unit="km/h",
        )
        
        assert signal.id is not None
        assert signal.name == "VehicleSpeed"
        assert signal.unit == "km/h"

    def test_list_signals(self, temp_db):
        """Test listing signals."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        data_file = temp_db.create_data_file(
            project.id, "test.blf", "/data/test.blf", "blf"
        )
        
        temp_db.create_signal(data_file.id, "Signal1", "float")
        temp_db.create_signal(data_file.id, "Signal2", "float")
        
        signals = temp_db.list_signals(data_file.id)
        assert len(signals) == 2


class TestTestResultOperations:
    """Tests for test result operations."""

    def test_create_test_result(self, temp_db):
        """Test creating a test result."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        
        result = temp_db.create_test_result(
            test_case_id=test_case.id,
            result="pass",
            notes="All checks passed",
        )
        
        assert result.id is not None
        assert result.result == "pass"
        assert result.notes == "All checks passed"

    def test_adjust_test_result(self, temp_db):
        """Test adjusting a test result."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        result = temp_db.create_test_result(test_case.id, "fail")
        
        adjusted = temp_db.adjust_test_result(
            result.id,
            adjusted_result="pass",
            adjustment_reason="False positive",
            adjusted_by=user.id,
        )
        
        assert adjusted is not None
        assert adjusted.result_adjusted == "pass"
        assert adjusted.adjustment_reason == "False positive"


class TestIndicatorResultOperations:
    """Tests for indicator result operations."""

    def test_create_indicator_result(self, temp_db):
        """Test creating an indicator result."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        indicator = temp_db.create_indicator(test_case.id, "Indicator 1")
        test_result = temp_db.create_test_result(test_case.id, "pass")
        
        result = temp_db.create_indicator_result(
            test_result_id=test_result.id,
            indicator_id=indicator.id,
            result="pass",
            calculated_value=0.5,
            raw_value=0.5,
        )
        
        assert result.id is not None
        assert result.result == "pass"
        assert result.calculated_value == 0.5

    def test_list_indicator_results(self, temp_db):
        """Test listing indicator results."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        indicator1 = temp_db.create_indicator(test_case.id, "Indicator 1")
        indicator2 = temp_db.create_indicator(test_case.id, "Indicator 2")
        test_result = temp_db.create_test_result(test_case.id, "pass")
        
        temp_db.create_indicator_result(
            test_result.id, indicator1.id, "pass", 0.5
        )
        temp_db.create_indicator_result(
            test_result.id, indicator2.id, "pass", 1.0
        )
        
        results = temp_db.list_indicator_results(test_result.id)
        assert len(results) == 2


class TestReportOperations:
    """Tests for report operations."""

    def test_create_report(self, temp_db):
        """Test creating a report record."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        report = temp_db.create_report(
            project_id=project.id,
            name="Test Report",
            generated_by=user.id,
            report_type="formal",
            format="docx",
        )
        
        assert report.id is not None
        assert report.name == "Test Report"
        assert report.format == "docx"

    def test_get_report(self, temp_db):
        """Test getting a report by ID."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        created = temp_db.create_report(project.id, "Test Report", user.id)
        
        report = temp_db.get_report(created.id)
        assert report is not None
        assert report.name == "Test Report"

    def test_list_reports(self, temp_db):
        """Test listing reports."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        
        temp_db.create_report(project.id, "Report 1", user.id)
        temp_db.create_report(project.id, "Report 2", user.id)
        
        reports = temp_db.list_reports(project.id)
        assert len(reports) == 2


class TestOperationLogOperations:
    """Tests for operation log operations."""

    def test_log_operation(self, temp_db):
        """Test logging an operation."""
        user = temp_db.create_user("testuser", "hash")
        
        log = temp_db.log_operation(
            user_id=user.id,
            operation="create_project",
            target_type="project",
            target_id=1,
            details='{"name": "Test Project"}',
        )
        
        assert log.id is not None
        assert log.operation == "create_project"
        assert log.target_type == "project"

    def test_list_operation_logs(self, temp_db):
        """Test listing operation logs."""
        user = temp_db.create_user("testuser", "hash")
        
        temp_db.log_operation(user.id, "operation1")
        temp_db.log_operation(user.id, "operation2")
        
        logs = temp_db.list_operation_logs()
        assert len(logs) == 2

    def test_list_operation_logs_by_user(self, temp_db):
        """Test listing operation logs by user."""
        user1 = temp_db.create_user("user1", "hash1")
        user2 = temp_db.create_user("user2", "hash2")
        
        temp_db.log_operation(user1.id, "operation1")
        temp_db.log_operation(user2.id, "operation2")
        
        logs = temp_db.list_operation_logs(user_id=user1.id)
        assert len(logs) == 1


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_count_records(self, temp_db):
        """Test counting records."""
        temp_db.create_user("user1", "hash1")
        temp_db.create_user("user2", "hash2")
        
        count = temp_db.count_records(User)
        assert count == 2


class TestModels:
    """Tests for model classes."""

    def test_user_repr(self, temp_db):
        """Test User __repr__."""
        user = temp_db.create_user("testuser", "hash")
        assert "testuser" in repr(user)

    def test_project_repr(self, temp_db):
        """Test Project __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        assert "Test Project" in repr(project)

    def test_test_case_repr(self, temp_db):
        """Test TestCase __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        assert "TC001" in repr(test_case)

    def test_indicator_repr(self, temp_db):
        """Test Indicator __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        indicator = temp_db.create_indicator(test_case.id, "Indicator 1")
        assert "Indicator 1" in repr(indicator)

    def test_data_file_repr(self, temp_db):
        """Test DataFile __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        data_file = temp_db.create_data_file(
            project.id, "test.blf", "/data/test.blf", "blf"
        )
        assert "test.blf" in repr(data_file)

    def test_signal_repr(self, temp_db):
        """Test Signal __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        data_file = temp_db.create_data_file(
            project.id, "test.blf", "/data/test.blf", "blf"
        )
        signal = temp_db.create_signal(data_file.id, "VehicleSpeed", "float")
        assert "VehicleSpeed" in repr(signal)

    def test_test_result_repr(self, temp_db):
        """Test TestResult __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        result = temp_db.create_test_result(test_case.id, "pass")
        assert "pass" in repr(result)

    def test_indicator_result_repr(self, temp_db):
        """Test IndicatorResult __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        test_case = temp_db.create_test_case(project.id, "TC001", "Test Case 1")
        indicator = temp_db.create_indicator(test_case.id, "Indicator 1")
        test_result = temp_db.create_test_result(test_case.id, "pass")
        result = temp_db.create_indicator_result(
            test_result.id, indicator.id, "pass", 0.5
        )
        assert "pass" in repr(result)

    def test_report_repr(self, temp_db):
        """Test Report __repr__."""
        user = temp_db.create_user("testuser", "hash")
        project = temp_db.create_project("Test Project", user.id)
        report = temp_db.create_report(project.id, "Test Report", user.id)
        assert "Test Report" in repr(report)

    def test_operation_log_repr(self, temp_db):
        """Test OperationLog __repr__."""
        user = temp_db.create_user("testuser", "hash")
        log = temp_db.log_operation(user.id, "test_operation")
        assert "test_operation" in repr(log)
