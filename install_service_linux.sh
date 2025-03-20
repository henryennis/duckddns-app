#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)
SCRIPT_PATH="${SCRIPT_DIR}/duckddns_app/duckdns_updater.py"
SERVICE_NAME="duckdns-updater"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Duck DNS Updater Service Installer for Linux"
echo "============================================"

function install_service {
    echo ""
    echo "Installing Duck DNS Updater service..."
    
    # Create service file
    cat > "${SERVICE_NAME}.service" << EOL
[Unit]
Description=Duck DNS Updater Service
After=network.target

[Service]
ExecStart=${PYTHON_PATH} ${SCRIPT_PATH}
WorkingDirectory=${SCRIPT_DIR}
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=${SERVICE_NAME}
User=$(whoami)
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOL

    # Install the service file
    sudo mv "${SERVICE_NAME}.service" "${SERVICE_FILE}"
    
    # Reload systemd manager configuration
    sudo systemctl daemon-reload
    
    # Enable the service to start on boot
    sudo systemctl enable "${SERVICE_NAME}"
    
    # Start the service
    sudo systemctl start "${SERVICE_NAME}"
    
    echo "Duck DNS Updater service has been installed and started."
    echo "You can check its status with: sudo systemctl status ${SERVICE_NAME}"
}

function uninstall_service {
    echo ""
    echo "Uninstalling Duck DNS Updater service..."
    
    # Stop the service if it's running
    sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    
    # Disable the service
    sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
    
    # Remove the service file
    if [ -f "${SERVICE_FILE}" ]; then
        sudo rm "${SERVICE_FILE}"
        sudo systemctl daemon-reload
    fi
    
    echo "Duck DNS Updater service has been uninstalled."
}

case "$1" in
    --install)
        install_service
        ;;
    --uninstall)
        uninstall_service
        ;;
    *)
        echo ""
        echo "Usage:"
        echo "  $0 --install   : Install Duck DNS Updater as a system service"
        echo "  $0 --uninstall : Remove Duck DNS Updater system service"
        exit 1
        ;;
esac

exit 0