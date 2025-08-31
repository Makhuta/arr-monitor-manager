import os
import yaml
import uuid
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manage Sonarr/Radarr configurations in YAML file"""
    
    def __init__(self, config_file='configs.yaml'):
        self.config_file = config_file
        self.configs = self._load_configs()
    
    def _load_configs(self) -> Dict:
        """Load configurations from YAML file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    configs = yaml.safe_load(f) or {}
                    logger.info(f'Loaded {len(configs)} configurations from {self.config_file}')
                    return configs
            else:
                logger.info(f'Configuration file {self.config_file} not found, starting with empty configs')
                return {}
        except Exception as e:
            logger.error(f'Error loading configuration file: {str(e)}')
            return {}
    
    def _save_configs(self) -> bool:
        """Save configurations to YAML file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(self.configs, f, default_flow_style=False, sort_keys=True)
            logger.info(f'Saved {len(self.configs)} configurations to {self.config_file}')
            return True
        except Exception as e:
            logger.error(f'Error saving configuration file: {str(e)}')
            return False
    
    def add_config(self, name: str, service_type: str, ip_address: str, 
                   api_token: str, quality_score: Optional[int] = None, 
                   format_name: Optional[str] = None) -> str:
        """Add a new configuration"""
        config_id = str(uuid.uuid4())
        webhook_token = str(uuid.uuid4())
        
        config = {
            'id': config_id,
            'name': name,
            'service_type': service_type,
            'ip_address': ip_address,
            'api_token': api_token,
            'webhook_token': webhook_token,
            'quality_score': quality_score,
            'format_name': format_name if format_name else None
        }
        
        self.configs[config_id] = config
        self._save_configs()
        logger.info(f'Added new configuration: {name} (ID: {config_id})')
        return webhook_token
    
    def delete_config(self, config_id: str) -> bool:
        """Delete a configuration by ID"""
        if config_id in self.configs:
            config_name = self.configs[config_id].get('name', 'Unknown')
            del self.configs[config_id]
            self._save_configs()
            logger.info(f'Deleted configuration: {config_name} (ID: {config_id})')
            return True
        return False
    
    def get_config(self, config_id: str) -> Optional[Dict]:
        """Get a specific configuration by ID"""
        return self.configs.get(config_id)
    
    def get_config_by_name(self, name: str) -> Optional[Dict]:
        """Get a configuration by name (returns first match)"""
        for config in self.configs.values():
            if config.get('name') == name:
                return config
        return None
    
    def get_all_configs(self) -> Dict:
        """Get all configurations"""
        return self.configs.copy()
    
    def get_config_by_token(self, webhook_token: str) -> Optional[Dict]:
        """Find configuration by webhook token"""
        for config in self.configs.values():
            if config.get('webhook_token') == webhook_token:
                return config
        return None
    
    def regenerate_webhook_token(self, config_id: str) -> Optional[str]:
        """Regenerate webhook token for a configuration"""
        if config_id in self.configs:
            new_token = str(uuid.uuid4())
            self.configs[config_id]['webhook_token'] = new_token
            config_name = self.configs[config_id].get('name', 'Unknown')
            self._save_configs()
            logger.info(f'Regenerated webhook token for: {config_name} (ID: {config_id})')
            return new_token
        return None
    
    def update_config(self, config_id: str, **kwargs) -> bool:
        """Update an existing configuration"""
        if config_id in self.configs:
            for key, value in kwargs.items():
                if key in ['name', 'service_type', 'ip_address', 'api_token', 'quality_score', 'format_name']:
                    self.configs[config_id][key] = value
            config_name = self.configs[config_id].get('name', 'Unknown')
            self._save_configs()
            logger.info(f'Updated configuration: {config_name} (ID: {config_id})')
            return True
        return False
