import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("DuckDNS.ConfigManager")

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".duckdns")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.history_file = os.path.join(self.config_dir, "history.json")
        
        # Ensure the config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
    
    def load_config(self):
        """Load the configuration from file or return default."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("Configuration loaded successfully")
                    return config
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                return self.get_default_config()
        else:
            logger.info("No configuration file found, using defaults")
            return self.get_default_config()
    
    def save_config(self, config):
        """Save the configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def load_history(self):
        """Load the update history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    logger.info(f"Loaded {len(history)} history entries")
                    return history
            except Exception as e:
                logger.error(f"Error loading history: {str(e)}")
                return []
        else:
            logger.info("No history file found")
            return []
    
    def save_history(self, history):
        """Save the update history to file."""
        try:
            # Limit history size to last 1000 entries
            if len(history) > 1000:
                history = history[-1000:]
            
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
            logger.info(f"Saved {len(history)} history entries")
            return True
        except Exception as e:
            logger.error(f"Error saving history: {str(e)}")
            return False
    
    def get_default_config(self):
        """Return default configuration."""
        return {
            "domains": "",
            "token": "",
            "update_ipv4": True,
            "use_custom_ipv4": False,
            "custom_ipv4": "",
            "update_ipv6": False,
            "custom_ipv6": "",
            "auto_update": False,
            "update_interval": 30,  # minutes
            "minimize_to_tray": True,
            "start_minimized": False
        }