# -*- coding: utf-8 -*-
"""
Login dialog for user authentication.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class LoginDialog(QDialog):
    """
    Dialog for user login.
    """

    login_successful = pyqtSignal(int, str, str)

    def __init__(self, auth_service, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth = auth_service
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Login - Vehicle Test Analysis")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)

        title_label = QLabel("Vehicle Test Analysis System")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("Enter username")
        self._username_edit.setMinimumHeight(30)
        form_layout.addRow("Username:", self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setPlaceholderText("Enter password")
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setMinimumHeight(30)
        self._password_edit.returnPressed.connect(self._on_login)
        form_layout.addRow("Password:", self._password_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_login)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._login_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._login_button.setText("Login")

        hint_label = QLabel("Default admin: admin / admin123")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: gray; font-size: 11px; margin-top: 10px;")
        layout.addWidget(hint_label)

    def _on_login(self) -> None:
        """Handle login button click."""
        username = self._username_edit.text().strip()
        password = self._password_edit.text()

        if not username:
            QMessageBox.warning(self, "Login Failed", "Please enter username")
            self._username_edit.setFocus()
            return

        if not password:
            QMessageBox.warning(self, "Login Failed", "Please enter password")
            self._password_edit.setFocus()
            return

        session = self._auth.login(username, password)

        if session:
            self.login_successful.emit(session.user_id, session.username, session.role)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Login Failed",
                "Invalid username or password, or account is disabled",
            )
            self._password_edit.clear()
            self._password_edit.setFocus()


class CreateUserDialog(QDialog):
    """
    Dialog for creating a new user (admin only).
    """

    user_created = pyqtSignal(int, str)

    def __init__(self, auth_service, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth = auth_service
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Create User")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("Username")
        form_layout.addRow("Username *:", self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("Password")
        form_layout.addRow("Password *:", self._password_edit)

        self._confirm_password_edit = QLineEdit()
        self._confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_password_edit.setPlaceholderText("Confirm password")
        form_layout.addRow("Confirm *:", self._confirm_password_edit)

        self._full_name_edit = QLineEdit()
        self._full_name_edit.setPlaceholderText("Full name")
        form_layout.addRow("Full Name:", self._full_name_edit)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("Email")
        form_layout.addRow("Email:", self._email_edit)

        role_layout = QVBoxLayout()
        self._role_group = QButtonGroup(self)

        self._admin_radio = QRadioButton("Admin")
        self._engineer_radio = QRadioButton("Engineer")
        self._viewer_radio = QRadioButton("Viewer")

        self._role_group.addButton(self._admin_radio, 0)
        self._role_group.addButton(self._engineer_radio, 1)
        self._role_group.addButton(self._viewer_radio, 2)

        role_layout.addWidget(self._admin_radio)
        role_layout.addWidget(self._engineer_radio)
        role_layout.addWidget(self._viewer_radio)

        self._engineer_radio.setChecked(True)
        form_layout.addRow("Role:", role_layout)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_create)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_create(self) -> None:
        """Handle create button click."""
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        confirm_password = self._confirm_password_edit.text()
        full_name = self._full_name_edit.text().strip() or None
        email = self._email_edit.text().strip() or None

        if not username:
            QMessageBox.warning(self, "Error", "Please enter username")
            return

        if not password:
            QMessageBox.warning(self, "Error", "Please enter password")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return

        role_map = {0: "admin", 1: "engineer", 2: "viewer"}
        role = role_map.get(self._role_group.checkedId(), "engineer")

        user_id = self._auth.create_user(
            username=username,
            password=password,
            email=email,
            full_name=full_name,
            role=role,
        )

        if user_id:
            self.user_created.emit(user_id, username)
            QMessageBox.information(
                self, "Success", f"User '{username}' created successfully"
            )
            self.accept()
        else:
            QMessageBox.warning(
                self, "Error", "Failed to create user. Username may already exist."
            )
