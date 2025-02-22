from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # API Key entry
        self.api_key_label = QLabel("Financial Modeling Prep API Key:")
        self.api_key_input = QLineEdit()
        layout.addWidget(self.api_key_label)
        layout.addWidget(self.api_key_input)

        # Buttons layout
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def load_settings(self):
        settings = QSettings("MyCompany", "InvestmentTool")
        api_key = settings.value("FMP_API_KEY", "")
        self.api_key_input.setText(api_key)

    def save_settings(self):
        settings = QSettings("MyCompany", "InvestmentTool")
        settings.setValue("FMP_API_KEY", self.api_key_input.text().strip())
        self.accept()
