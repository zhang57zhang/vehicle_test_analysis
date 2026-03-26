"""
Database operations module.

Provides high-level database operations for the vehicle test analysis system.
"""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import create_engine, desc, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import (
    Base,
    DataFile,
    Indicator,
    IndicatorResult,
    OperationLog,
    Project,
    Report,
    Signal,
    TestCaseModel,
    TestResultModel,
    User,
)

T = TypeVar("T", bound=Base)


class DatabaseManager:
    """
    Database manager for handling all database operations.
    """

    def __init__(self, database_url: str = "sqlite:///database/vehicle_test.db"):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL.
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._initialized = False

    def initialize(self) -> None:
        """Initialize database tables."""
        if not self._initialized:
            # Ensure database directory exists
            if self.database_url.startswith("sqlite:///"):
                db_path = Path(self.database_url.replace("sqlite:///", ""))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            Base.metadata.create_all(self.engine)
            self._initialized = True

    @contextmanager
    def session(self):
        """
        Context manager for database sessions.

        Yields:
            SQLAlchemy Session object.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== User Operations ====================

    def create_user(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "engineer",
    ) -> User:
        """
        Create a new user.

        Args:
            username: Username.
            password_hash: Hashed password.
            email: Email address.
            full_name: Full name.
            role: User role (admin, engineer, viewer).

        Returns:
            Created User object.
        """
        with self.session() as session:
            user = User(
                username=username,
                password_hash=password_hash,
                email=email,
                full_name=full_name,
                role=role,
            )
            session.add(user)
            session.flush()
            session.refresh(user)
            return User(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
            )

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.session() as session:
            user = session.get(User, user_id)
            if user:
                return self._detach(user)
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        with self.session() as session:
            user = session.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()
            if user:
                return self._detach(user)
            return None

    def list_users(self, active_only: bool = True) -> List[User]:
        """List all users."""
        with self.session() as session:
            query = select(User)
            if active_only:
                query = query.where(User.is_active == True)
            users = session.execute(query).scalars().all()
            return [self._detach(u) for u in users]

    # ==================== Project Operations ====================

    def create_project(
        self,
        name: str,
        owner_id: int,
        description: Optional[str] = None,
        test_phase: str = "HIL",
        vehicle_info: Optional[str] = None,
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name.
            owner_id: Owner user ID.
            description: Project description.
            test_phase: Test phase (MIL, HIL, DVP, Vehicle).
            vehicle_info: Vehicle information.

        Returns:
            Created Project object.
        """
        with self.session() as session:
            project = Project(
                name=name,
                owner_id=owner_id,
                description=description,
                test_phase=test_phase,
                vehicle_info=vehicle_info,
            )
            session.add(project)
            session.flush()
            session.refresh(project)
            return self._detach(project)

    def get_project(self, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        with self.session() as session:
            project = session.get(Project, project_id)
            if project:
                return self._detach(project)
            return None

    def list_projects(
        self,
        owner_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Project]:
        """
        List projects with optional filters.

        Args:
            owner_id: Filter by owner ID.
            status: Filter by status.

        Returns:
            List of Project objects.
        """
        with self.session() as session:
            query = select(Project)
            if owner_id:
                query = query.where(Project.owner_id == owner_id)
            if status:
                query = query.where(Project.status == status)
            query = query.order_by(desc(Project.created_at))
            projects = session.execute(query).scalars().all()
            return [self._detach(p) for p in projects]

    def update_project(
        self,
        project_id: int,
        **kwargs,
    ) -> Optional[Project]:
        """
        Update project attributes.

        Args:
            project_id: Project ID.
            **kwargs: Attributes to update.

        Returns:
            Updated Project object or None.
        """
        with self.session() as session:
            project = session.get(Project, project_id)
            if not project:
                return None
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            session.flush()
            session.refresh(project)
            return self._detach(project)

    def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        with self.session() as session:
            project = session.get(Project, project_id)
            if project:
                session.delete(project)
                return True
            return False

    # ==================== Test Case Operations ====================

    def create_test_case(
        self,
        project_id: int,
        case_id: str,
        name: str,
        description: Optional[str] = None,
        test_type: str = "functional",
        priority: str = "P2",
        preconditions: Optional[str] = None,
        test_steps: Optional[str] = None,
        expected_result: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> TestCaseModel:
        """Create a new test case."""
        with self.session() as session:
            test_case = TestCaseModel(
                project_id=project_id,
                case_id=case_id,
                name=name,
                description=description,
                test_type=test_type,
                priority=priority,
                preconditions=preconditions,
                test_steps=test_steps,
                expected_result=expected_result,
                source_file=source_file,
            )
            session.add(test_case)
            session.flush()
            session.refresh(test_case)
            return self._detach(test_case)

    def get_test_case(self, test_case_id: int) -> Optional[TestCaseModel]:
        """Get test case by ID."""
        with self.session() as session:
            test_case = session.get(TestCaseModel, test_case_id)
            if test_case:
                return self._detach(test_case)
            return None

    def list_test_cases(
        self,
        project_id: int,
        test_type: Optional[str] = None,
    ) -> List[TestCaseModel]:
        """List test cases for a project."""
        with self.session() as session:
            query = select(TestCaseModel).where(TestCaseModel.project_id == project_id)
            if test_type:
                query = query.where(TestCaseModel.test_type == test_type)
            test_cases = session.execute(query).scalars().all()
            return [self._detach(tc) for tc in test_cases]

    # ==================== Indicator Operations ====================

    def create_indicator(
        self,
        test_case_id: int,
        name: str,
        signal_name: Optional[str] = None,
        indicator_type: str = "single_value",
        formula: Optional[str] = None,
        unit: Optional[str] = None,
        lower_limit: Optional[float] = None,
        upper_limit: Optional[float] = None,
        target_value: Optional[float] = None,
        tolerance: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Indicator:
        """Create a new indicator."""
        with self.session() as session:
            indicator = Indicator(
                test_case_id=test_case_id,
                name=name,
                signal_name=signal_name,
                indicator_type=indicator_type,
                formula=formula,
                unit=unit,
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                target_value=target_value,
                tolerance=tolerance,
                description=description,
            )
            session.add(indicator)
            session.flush()
            session.refresh(indicator)
            return self._detach(indicator)

    def get_indicator(self, indicator_id: int) -> Optional[Indicator]:
        """Get indicator by ID."""
        with self.session() as session:
            indicator = session.get(Indicator, indicator_id)
            if indicator:
                return self._detach(indicator)
            return None

    def list_indicators(self, test_case_id: int) -> List[Indicator]:
        """List indicators for a test case."""
        with self.session() as session:
            query = select(Indicator).where(Indicator.test_case_id == test_case_id)
            indicators = session.execute(query).scalars().all()
            return [self._detach(i) for i in indicators]

    # ==================== Data File Operations ====================

    def create_data_file(
        self,
        project_id: int,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int = 0,
        file_hash: Optional[str] = None,
        collection_time: Optional[datetime] = None,
        time_range_start: Optional[float] = None,
        time_range_end: Optional[float] = None,
        data_points: Optional[int] = None,
        signal_count: Optional[int] = None,
        file_metadata: Optional[str] = None,
    ) -> DataFile:
        """Create a new data file record."""
        with self.session() as session:
            data_file = DataFile(
                project_id=project_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                collection_time=collection_time,
                time_range_start=time_range_start,
                time_range_end=time_range_end,
                data_points=data_points,
                signal_count=signal_count,
                file_metadata=file_metadata,
            )
            session.add(data_file)
            session.flush()
            session.refresh(data_file)
            return self._detach(data_file)

    def get_data_file(self, data_file_id: int) -> Optional[DataFile]:
        """Get data file by ID."""
        with self.session() as session:
            data_file = session.get(DataFile, data_file_id)
            if data_file:
                return self._detach(data_file)
            return None

    def list_data_files(self, project_id: int) -> List[DataFile]:
        """List data files for a project."""
        with self.session() as session:
            query = select(DataFile).where(DataFile.project_id == project_id)
            data_files = session.execute(query).scalars().all()
            return [self._detach(df) for df in data_files]

    # ==================== Signal Operations ====================

    def create_signal(
        self,
        data_file_id: int,
        name: str,
        data_type: str = "float",
        message_id: Optional[int] = None,
        message_name: Optional[str] = None,
        dbc_file: Optional[str] = None,
        unit: Optional[str] = None,
        sample_rate: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        value_count: int = 0,
    ) -> Signal:
        """Create a new signal record."""
        with self.session() as session:
            signal = Signal(
                data_file_id=data_file_id,
                name=name,
                data_type=data_type,
                message_id=message_id,
                message_name=message_name,
                dbc_file=dbc_file,
                unit=unit,
                sample_rate=sample_rate,
                min_value=min_value,
                max_value=max_value,
                value_count=value_count,
            )
            session.add(signal)
            session.flush()
            session.refresh(signal)
            return self._detach(signal)

    def list_signals(self, data_file_id: int) -> List[Signal]:
        """List signals for a data file."""
        with self.session() as session:
            query = select(Signal).where(Signal.data_file_id == data_file_id)
            signals = session.execute(query).scalars().all()
            return [self._detach(s) for s in signals]

    # ==================== Test Result Operations ====================

    def create_test_result(
        self,
        test_case_id: int,
        result: str,
        notes: Optional[str] = None,
    ) -> TestResultModel:
        """Create a new test result."""
        with self.session() as session:
            test_result = TestResultModel(
                test_case_id=test_case_id,
                result=result,
                notes=notes,
            )
            session.add(test_result)
            session.flush()
            session.refresh(test_result)
            return self._detach(test_result)

    def get_test_result(self, test_result_id: int) -> Optional[TestResultModel]:
        """Get test result by ID."""
        with self.session() as session:
            test_result = session.get(TestResultModel, test_result_id)
            if test_result:
                return self._detach(test_result)
            return None

    def adjust_test_result(
        self,
        test_result_id: int,
        adjusted_result: str,
        adjustment_reason: str,
        adjusted_by: int,
    ) -> Optional[TestResultModel]:
        """Adjust a test result."""
        with self.session() as session:
            test_result = session.get(TestResultModel, test_result_id)
            if not test_result:
                return None
            test_result.result_adjusted = adjusted_result
            test_result.adjustment_reason = adjustment_reason
            test_result.adjusted_by = adjusted_by
            test_result.adjusted_at = datetime.utcnow()
            session.flush()
            session.refresh(test_result)
            return self._detach(test_result)

    # ==================== Indicator Result Operations ====================

    def create_indicator_result(
        self,
        test_result_id: int,
        indicator_id: int,
        result: str,
        calculated_value: Optional[float] = None,
        raw_value: Optional[float] = None,
        data_source: Optional[str] = None,
        calculation_details: Optional[str] = None,
        time_range_start: Optional[float] = None,
        time_range_end: Optional[float] = None,
        data_points_used: Optional[int] = None,
    ) -> IndicatorResult:
        """Create a new indicator result."""
        with self.session() as session:
            indicator_result = IndicatorResult(
                test_result_id=test_result_id,
                indicator_id=indicator_id,
                result=result,
                calculated_value=calculated_value,
                raw_value=raw_value,
                data_source=data_source,
                calculation_details=calculation_details,
                time_range_start=time_range_start,
                time_range_end=time_range_end,
                data_points_used=data_points_used,
            )
            session.add(indicator_result)
            session.flush()
            session.refresh(indicator_result)
            return self._detach(indicator_result)

    def list_indicator_results(self, test_result_id: int) -> List[IndicatorResult]:
        """List indicator results for a test result."""
        with self.session() as session:
            query = select(IndicatorResult).where(
                IndicatorResult.test_result_id == test_result_id
            )
            results = session.execute(query).scalars().all()
            return [self._detach(r) for r in results]

    # ==================== Report Operations ====================

    def create_report(
        self,
        project_id: int,
        name: str,
        generated_by: int,
        report_type: str = "formal",
        format: str = "docx",
        file_path: Optional[str] = None,
        template_used: Optional[str] = None,
    ) -> Report:
        """Create a new report record."""
        with self.session() as session:
            report = Report(
                project_id=project_id,
                name=name,
                generated_by=generated_by,
                report_type=report_type,
                format=format,
                file_path=file_path,
                template_used=template_used,
            )
            session.add(report)
            session.flush()
            session.refresh(report)
            return self._detach(report)

    def get_report(self, report_id: int) -> Optional[Report]:
        """Get report by ID."""
        with self.session() as session:
            report = session.get(Report, report_id)
            if report:
                return self._detach(report)
            return None

    def list_reports(self, project_id: int) -> List[Report]:
        """List reports for a project."""
        with self.session() as session:
            query = select(Report).where(Report.project_id == project_id)
            query = query.order_by(desc(Report.generated_at))
            reports = session.execute(query).scalars().all()
            return [self._detach(r) for r in reports]

    # ==================== Operation Log Operations ====================

    def log_operation(
        self,
        user_id: int,
        operation: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> OperationLog:
        """Log a user operation."""
        with self.session() as session:
            log = OperationLog(
                user_id=user_id,
                operation=operation,
                target_type=target_type,
                target_id=target_id,
                details=details,
                ip_address=ip_address,
            )
            session.add(log)
            session.flush()
            session.refresh(log)
            return self._detach(log)

    def list_operation_logs(
        self,
        user_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[OperationLog]:
        """List operation logs."""
        with self.session() as session:
            query = select(OperationLog)
            if user_id:
                query = query.where(OperationLog.user_id == user_id)
            query = query.order_by(desc(OperationLog.created_at)).limit(limit)
            logs = session.execute(query).scalars().all()
            return [self._detach(l) for l in logs]

    # ==================== Utility Methods ====================

    def _detach(self, obj: T) -> T:
        """
        Detach an object from the session by creating a copy.

        This allows the object to be used after the session is closed.
        """
        # Create a new instance with the same attributes
        cls = type(obj)
        kwargs = {}
        for column in cls.__table__.columns:
            kwargs[column.name] = getattr(obj, column.name)
        return cls(**kwargs)

    def count_records(self, model: Type[Base]) -> int:
        """Count records in a table."""
        with self.session() as session:
            return session.execute(select(func.count()).select_from(model)).scalar()

    def execute_raw(self, sql: str) -> Any:
        """Execute raw SQL."""
        with self.session() as session:
            return session.execute(sql)
