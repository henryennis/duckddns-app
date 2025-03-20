import sys
import os
import time
import json
import logging
import requests
import ipaddress
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QLineEdit, QPushButton, QComboBox, QFormLayout,
                              QTabWidget, QTextEdit, QCheckBox, QMessageBox, QSystemTrayIcon,
                              QMenu, QSpinBox, QGroupBox)
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QSettings
from PySide6.QtGui import QIcon, QAction

from duckddns_app.config_manager import ConfigManager
from duckddns_app.ip_utils import get_ipv4, get_ipv6

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.expanduser("~"), "duckdns_updater.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DuckDNS Updater")

class UpdateThread(QThread):
    update_complete = Signal(dict)
    
    def __init__(self, domains, token, update_ipv4=True, update_ipv6=True, ipv4=None, ipv6=None):
        super().__init__()
        self.domains = domains
        self.token = token
        self.update_ipv4 = update_ipv4
        self.update_ipv6 = update_ipv6
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        
    def run(self):
        try:
            result = self.update_duckdns()
            self.update_complete.emit(result)
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            self.update_complete.emit({
                "success": False,
                "message": f"Update failed: {str(e)}",
                "ipv4": None,
                "ipv6": None,
                "timestamp": datetime.now().isoformat()
            })
    
    def update_duckdns(self):
        params = {
            'domains': self.domains,
            'token': self.token,
            'verbose': 'true'
        }
        
        # Handle IP settings
        if self.update_ipv4:
            if self.ipv4:
                params['ip'] = self.ipv4
            else:
                detected_ipv4 = get_ipv4()
                if detected_ipv4:
                    params['ip'] = detected_ipv4
        
        if self.update_ipv6 and self.ipv6:
            params['ipv6'] = self.ipv6
        
        try:
            response = requests.get('https://www.duckdns.org/update', params=params, timeout=10)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                if lines[0] == 'OK':
                    ipv4 = lines[1] if len(lines) > 1 and lines[1] and lines[1] != 'NOCHANGE' else None
                    ipv6 = lines[2] if len(lines) > 2 and lines[2] and lines[2] != 'NOCHANGE' else None
                    update_status = lines[3] if len(lines) > 3 else "UPDATED"
                    
                    return {
                        "success": True,
                        "message": f"Update successful: {update_status}",
                        "ipv4": ipv4,
                        "ipv6": ipv6,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "message": "Update failed: Invalid response",
                        "ipv4": None,
                        "ipv6": None,
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                return {
                    "success": False,
                    "message": f"Update failed: HTTP {response.status_code}",
                    "ipv4": None,
                    "ipv6": None,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Network error: {str(e)}")
            return {
                "success": False,
                "message": f"Network error: {str(e)}",
                "ipv4": None,
                "ipv6": None,
                "timestamp": datetime.now().isoformat()
            }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duck DNS Updater")
        self.resize(600, 500)
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.update_history = self.config_manager.load_history()
        
        self.init_ui()
        self.setup_tray_icon()
        self.setup_timer()
        
        # Automatically start first update if enabled
        if self.config.get('auto_update', False):
            QTimer.singleShot(1000, self.update_dns)
        
    def init_ui(self):
        # Main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Create tabs
        config_tab = self.create_config_tab()
        status_tab = self.create_status_tab()
        history_tab = self.create_history_tab()
        
        # Add tabs
        tabs.addTab(config_tab, "Configuration")
        tabs.addTab(status_tab, "Status")
        tabs.addTab(history_tab, "History")
        
        main_layout.addWidget(tabs)
        
        # Add update button
        update_button = QPushButton("Update Now")
        update_button.clicked.connect(self.update_dns)
        main_layout.addWidget(update_button)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def create_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Domain and token settings
        account_group = QGroupBox("Account Settings")
        account_layout = QFormLayout()
        
        self.domains_input = QLineEdit(self.config.get('domains', ''))
        self.domains_input.setPlaceholderText("example1,example2")
        account_layout.addRow("Domains:", self.domains_input)
        
        self.token_input = QLineEdit(self.config.get('token', ''))
        self.token_input.setPlaceholderText("Your Duck DNS token")
        account_layout.addRow("Token:", self.token_input)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # IP settings
        ip_group = QGroupBox("IP Settings")
        ip_layout = QFormLayout()
        
        self.update_ipv4_check = QCheckBox("Update IPv4")
        self.update_ipv4_check.setChecked(self.config.get('update_ipv4', True))
        ip_layout.addRow(self.update_ipv4_check)
        
        self.use_custom_ipv4_check = QCheckBox("Use custom IPv4")
        self.use_custom_ipv4_check.setChecked(self.config.get('use_custom_ipv4', False))
        ip_layout.addRow(self.use_custom_ipv4_check)
        
        self.custom_ipv4_input = QLineEdit(self.config.get('custom_ipv4', ''))
        self.custom_ipv4_input.setPlaceholderText("Custom IPv4 address")
        self.custom_ipv4_input.setEnabled(self.use_custom_ipv4_check.isChecked())
        ip_layout.addRow("Custom IPv4:", self.custom_ipv4_input)
        
        self.update_ipv6_check = QCheckBox("Update IPv6")
        self.update_ipv6_check.setChecked(self.config.get('update_ipv6', False))
        ip_layout.addRow(self.update_ipv6_check)
        
        self.custom_ipv6_input = QLineEdit(self.config.get('custom_ipv6', ''))
        self.custom_ipv6_input.setPlaceholderText("Custom IPv6 address")
        ip_layout.addRow("Custom IPv6:", self.custom_ipv6_input)
        
        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)
        
        # Update settings
        update_group = QGroupBox("Update Settings")
        update_layout = QFormLayout()
        
        self.auto_update_check = QCheckBox("Enable automatic updates")
        self.auto_update_check.setChecked(self.config.get('auto_update', False))
        update_layout.addRow(self.auto_update_check)
        
        self.update_interval_input = QSpinBox()
        self.update_interval_input.setMinimum(5)
        self.update_interval_input.setMaximum(1440)
        self.update_interval_input.setValue(self.config.get('update_interval', 30))
        update_layout.addRow("Update interval (minutes):", self.update_interval_input)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # App settings
        app_group = QGroupBox("Application Settings")
        app_layout = QFormLayout()
        
        self.minimize_to_tray_check = QCheckBox("Minimize to tray")
        self.minimize_to_tray_check.setChecked(self.config.get('minimize_to_tray', True))
        app_layout.addRow(self.minimize_to_tray_check)
        
        self.start_minimized_check = QCheckBox("Start minimized")
        self.start_minimized_check.setChecked(self.config.get('start_minimized', False))
        app_layout.addRow(self.start_minimized_check)
        
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)
        
        # Connect signals
        self.use_custom_ipv4_check.toggled.connect(self.custom_ipv4_input.setEnabled)
        
        # Save button
        save_button = QPushButton("Save Configuration")
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)
        
        tab.setLayout(layout)
        return tab
    
    def create_status_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Status information
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(QLabel("Current Status:"))
        layout.addWidget(self.status_text)
        
        # If we have a previous update, display it
        if self.update_history:
            last_update = self.update_history[-1]
            self.display_status(last_update)
        else:
            self.status_text.setText("No updates performed yet.")
        
        tab.setLayout(layout)
        return tab
    
    def create_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        layout.addWidget(QLabel("Update History:"))
        layout.addWidget(self.history_text)
        
        # Display history
        self.update_history_display()
        
        # Clear history button
        clear_button = QPushButton("Clear History")
        clear_button.clicked.connect(self.clear_history)
        layout.addWidget(clear_button)
        
        tab.setLayout(layout)
        return tab
    
    def update_history_display(self):
        if not self.update_history:
            self.history_text.setText("No update history available.")
            return
            
        history_text = ""
        for entry in reversed(self.update_history[-50:]):  # Show last 50 entries
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            status = "✓" if entry['success'] else "✗"
            message = entry['message']
            ipv4 = entry.get('ipv4', 'Not updated')
            ipv6 = entry.get('ipv6', 'Not updated')
            
            entry_text = f"[{timestamp}] {status} - {message}\n"
            entry_text += f"   IPv4: {ipv4}\n"
            entry_text += f"   IPv6: {ipv6}\n\n"
            
            history_text += entry_text
            
        self.history_text.setText(history_text)
    
    def display_status(self, status):
        if not status:
            self.status_text.setText("No status available.")
            return
            
        timestamp = datetime.fromisoformat(status['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        success_text = "Success" if status['success'] else "Failed"
        status_text = f"Last Update: {timestamp}\n"
        status_text += f"Status: {success_text}\n"
        status_text += f"Message: {status['message']}\n\n"
        
        current_ipv4 = status.get('ipv4', get_ipv4() or 'Unknown')
        current_ipv6 = status.get('ipv6', get_ipv6() or 'Not detected')
        
        status_text += f"Current IPv4: {current_ipv4}\n"
        status_text += f"Current IPv6: {current_ipv6}\n"
        
        self.status_text.setText(status_text)
    
    def save_config(self):
        self.config = {
            'domains': self.domains_input.text().strip(),
            'token': self.token_input.text().strip(),
            'update_ipv4': self.update_ipv4_check.isChecked(),
            'use_custom_ipv4': self.use_custom_ipv4_check.isChecked(),
            'custom_ipv4': self.custom_ipv4_input.text().strip(),
            'update_ipv6': self.update_ipv6_check.isChecked(),
            'custom_ipv6': self.custom_ipv6_input.text().strip(),
            'auto_update': self.auto_update_check.isChecked(),
            'update_interval': self.update_interval_input.value(),
            'minimize_to_tray': self.minimize_to_tray_check.isChecked(),
            'start_minimized': self.start_minimized_check.isChecked()
        }
        
        self.config_manager.save_config(self.config)
        self.setup_timer()  # Reconfigure the timer with new settings
        
        QMessageBox.information(self, "Configuration Saved", 
                              "Your configuration has been saved successfully.")
    
    def update_dns(self):
        domains = self.config.get('domains', '')
        token = self.config.get('token', '')
        
        if not domains or not token:
            QMessageBox.warning(self, "Configuration Missing", 
                              "Please enter your domains and token in the Configuration tab.")
            return
        
        # Get IP settings from config
        update_ipv4 = self.config.get('update_ipv4', True)
        use_custom_ipv4 = self.config.get('use_custom_ipv4', False)
        custom_ipv4 = self.config.get('custom_ipv4', '')
        update_ipv6 = self.config.get('update_ipv6', False)
        custom_ipv6 = self.config.get('custom_ipv6', '')
        
        # Set up IP addresses for the update
        ipv4 = custom_ipv4 if use_custom_ipv4 and custom_ipv4 else None
        ipv6 = custom_ipv6 if update_ipv6 and custom_ipv6 else None
        
        # Start update thread
        self.update_thread = UpdateThread(
            domains=domains,
            token=token,
            update_ipv4=update_ipv4,
            update_ipv6=update_ipv6,
            ipv4=ipv4,
            ipv6=ipv6
        )
        self.update_thread.update_complete.connect(self.on_update_complete)
        self.update_thread.start()
        
        QMessageBox.information(self, "Update Started", 
                              "Duck DNS update has been initiated. Please wait...")
    
    def on_update_complete(self, result):
        # Update history
        self.update_history.append(result)
        self.config_manager.save_history(self.update_history)
        
        # Update the UI
        self.display_status(result)
        self.update_history_display()
        
        # Show notification
        if self.tray_icon and self.tray_icon.isVisible():
            status_text = "successful" if result['success'] else "failed"
            self.tray_icon.showMessage(
                "Duck DNS Update",
                f"Update {status_text}: {result['message']}",
                QSystemTrayIcon.Information,
                5000
            )
    
    def clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear the update history?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.update_history = []
            self.config_manager.save_history(self.update_history)
            self.update_history_display()
    
    def setup_timer(self):
        # Remove any existing timer
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        
        # Create new timer if auto-update is enabled
        if self.config.get('auto_update', False):
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.update_dns)
            interval_ms = self.config.get('update_interval', 30) * 60 * 1000  # Convert minutes to ms
            self.update_timer.start(interval_ms)
    
    def setup_tray_icon(self):
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Duck DNS Updater")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        quit_action = QAction("Quit", self)
        update_action = QAction("Update Now", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        update_action.triggered.connect(self.update_dns)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(update_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isHidden():
                self.show()
            else:
                self.hide()
    
    def closeEvent(self, event):
        if self.config.get('minimize_to_tray', True) and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Duck DNS Updater",
                "Application minimized to system tray",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            event.accept()
            self.quit_application()
    
    def quit_application(self):
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        self.tray_icon.hide()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    
    # Check if we should start minimized
    if not window.config.get('start_minimized', False):
        window.show()
    
    sys.exit(app.exec())