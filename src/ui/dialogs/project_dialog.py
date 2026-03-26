# -*- coding: utf-8 -*-
"""
Project management dialogs.
"""

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ProjectInfo:
    """Project information container."""

    id: int
    name: str
    description: Optional[str]
    test_phase: str
    vehicle_info: Optional[str]


class ProjectDialog(QDialog):
    """
    Dialog for creating a new project.
    """

    def __init__(self, db_manager, owner_id: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db = db_manager
        self._owner_id = owner_id
        self._project = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("New Project")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Enter project name")
        self._name_edit.setMaxLength(200)
        form_layout.addRow("Project Name *:", self._name_edit)

        self._phase_combo = QComboBox()
        self._phase_combo.addItems(["MIL", "HIL", "DVP", "Vehicle"])
        self._phase_combo.setCurrentText("HIL")
        form_layout.addRow("Test Phase:", self._phase_combo)

        self._vehicle_edit = QLineEdit()
        self._vehicle_edit.setPlaceholderText("e.g., Model X 2024")
        form_layout.addRow("Vehicle Info:", self._vehicle_edit)

        self._description_edit = QPlainTextEdit()
        self._description_edit.setPlaceholderText("Project description...")
        self._description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self._description_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("Create")

    def _on_accept(self) -> None:
        """Handle accept button."""
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            return

        test_phase = self._phase_combo.currentText()
        vehicle_info = self._vehicle_edit.text().strip() or None
        description = self._description_edit.toPlainText().strip() or None

        try:
            project = self._db.create_project(
                name=name,
                owner_id=self._owner_id,
                description=description,
                test_phase=test_phase,
                vehicle_info=vehicle_info,
            )
            self._project = ProjectInfo(
                id=project.id,
                name=project.name,
                description=project.description,
                test_phase=project.test_phase,
                vehicle_info=project.vehicle_info,
            )
            self.accept()
        except Exception:
            self._name_edit.setFocus()

    def get_project(self) -> Optional[ProjectInfo]:
        """Get created project info."""
        return self._project


class EditProjectDialog(QDialog):
    """
    Dialog for editing an existing project.
    """

    def __init__(self, db_manager, project_id: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db = db_manager
        self._project_id = project_id
        self._setup_ui()
        self._load_project()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Edit Project")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(200)
        form_layout.addRow("Project Name *:", self._name_edit)

        self._phase_combo = QComboBox()
        self._phase_combo.addItems(["MIL", "HIL", "DVP", "Vehicle"])
        form_layout.addRow("Test Phase:", self._phase_combo)

        self._vehicle_edit = QLineEdit()
        form_layout.addRow("Vehicle Info:", self._vehicle_edit)

        self._description_edit = QPlainTextEdit()
        self._description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self._description_edit)

        self._status_combo = QComboBox()
        self._status_combo.addItems(["active", "archived", "deleted"])
        form_layout.addRow("Status:", self._status_combo)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_project(self) -> None:
        """Load project data into form."""
        project = self._db.get_project(self._project_id)
        if project:
            self._name_edit.setText(project.name)
            self._phase_combo.setCurrentText(project.test_phase)
            self._vehicle_edit.setText(project.vehicle_info or "")
            self._description_edit.setPlainText(project.description or "")
            self._status_combo.setCurrentText(project.status)

    def _on_accept(self) -> None:
        """Handle accept button."""
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            return

        self._db.update_project(
            self._project_id,
            name=name,
            test_phase=self._phase_combo.currentText(),
            vehicle_info=self._vehicle_edit.text().strip() or None,
            description=self._description_edit.toPlainText().strip() or None,
            status=self._status_combo.currentText(),
        )
        self.accept()
