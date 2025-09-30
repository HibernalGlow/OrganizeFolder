import yaml
import tomli
from pathlib import Path
from typing import Dict, Any, List

class OrganizefGenerator:
    def __init__(self, config_path: Path, rules_dir: Path):
        self.config_path = config_path
        self.rules_dir = rules_dir
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'rb') as f:
            return tomli.load(f)

    def generate_yaml(self, profile_name: str, paths: List[str]) -> str:
        if profile_name not in self.config['profiles']:
            raise ValueError(f"Profile {profile_name} not found")

        profile = self.config['profiles'][profile_name]
        rules = []

        for rule_config in profile['rules']:
            if not rule_config['enabled']:
                continue

            rule_id = rule_config['id']
            params = rule_config['params'].copy()

            # Load rule YAML
            rule_path = self.rules_dir / f"{rule_id}.yaml"
            with open(rule_path, 'r', encoding='utf-8') as f:
                rule_yaml = yaml.safe_load(f)

            # Process params
            # For multiple paths, create locations list
            locations = []
            for path in paths:
                loc = {'path': path}
                if 'exclude_dirs' in params:
                    loc['exclude_dirs'] = params['exclude_dirs']
                locations.append(loc)
            params['locations'] = locations

            self.replace_placeholders(rule_yaml, params)

            rules.extend(rule_yaml['rules'])

        # Merge into final YAML
        final_config = {'rules': rules}
        return yaml.dump(final_config, default_flow_style=False, allow_unicode=True)

    def replace_placeholders(self, data: Any, params: Dict[str, Any]):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    param_key = value[2:-1]
                    if param_key in params:
                        data[key] = params[param_key]
                    else:
                        raise ValueError(f"Parameter {param_key} not found")
                else:
                    self.replace_placeholders(value, params)
        elif isinstance(data, list):
            for item in data:
                self.replace_placeholders(item, params)