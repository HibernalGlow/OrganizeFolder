import pytest
import yaml
from unittest.mock import patch
from pathlib import Path
from organizef.generator import OrganizefGenerator

def test_cli_profile_selection(tmp_path):
    """Test profile selection in CLI"""
    # Create test config
    config_content = """
[profiles.test_profile]
description = "Test profile"
rules = [
    { id = "clean_empty_dirs", enabled = true, params = {} }
]
"""
    config_file = tmp_path / 'config.toml'
    with open(config_file, 'w') as f:
        f.write(config_content)

    # Create test rule
    rules_dir = tmp_path / 'rules'
    rules_dir.mkdir()
    rule_content = """
rules:
  - name: "Test Rule"
    locations: ${locations}
    actions:
      - echo: "test"
"""
    with open(rules_dir / 'clean_empty_dirs.yaml', 'w') as f:
        f.write(rule_content)

    generator = OrganizefGenerator(config_file, rules_dir)

    # Mock rich prompt
    with patch('rich.prompt.Prompt.ask', return_value='1'), \
         patch('organizef.input.get_paths', return_value=['/test/path']):
        yaml_content = generator.generate_yaml('test_profile', ['/test/path'])
        assert 'rules' in yaml_content

def test_cli_path_from_clipboard(tmp_path):
    """Test getting path from clipboard"""
    config_content = """
[profiles.test]
rules = [
    { id = "clean_empty_dirs", enabled = true, params = {} }
]
"""
    config_file = tmp_path / 'config.toml'
    with open(config_file, 'w') as f:
        f.write(config_content)

    rules_dir = tmp_path / 'rules'
    rules_dir.mkdir()
    rule_content = """
rules:
  - name: "Test"
    locations: ${locations}
    actions:
      - echo: "test"
"""
    with open(rules_dir / 'clean_empty_dirs.yaml', 'w') as f:
        f.write(rule_content)

    generator = OrganizefGenerator(config_file, rules_dir)

    with patch('pyperclip.paste', return_value='/clipboard/path'):
        yaml_content = generator.generate_yaml('test', ['/clipboard/path'])
        assert '/clipboard/path' in yaml_content

def test_cli_multiple_paths(tmp_path):
    """Test multiple paths handling"""
    config_content = """
[profiles.test]
rules = [
    { id = "clean_empty_dirs", enabled = true, params = {} }
]
"""
    config_file = tmp_path / 'config.toml'
    with open(config_file, 'w') as f:
        f.write(config_content)

    rules_dir = tmp_path / 'rules'
    rules_dir.mkdir()
    rule_content = """
rules:
  - name: "Test"
    locations: ${locations}
    actions:
      - echo: "test"
"""
    with open(rules_dir / 'clean_empty_dirs.yaml', 'w') as f:
        f.write(rule_content)

    generator = OrganizefGenerator(config_file, rules_dir)

    paths = ['/path1', '/path2', '/path3']
    yaml_content = generator.generate_yaml('test', paths)
    parsed = yaml.safe_load(yaml_content)

    assert len(parsed['rules'][0]['locations']) == 3
    for i, path in enumerate(paths):
        assert parsed['rules'][0]['locations'][i]['path'] == path

def test_cli_dry_run(tmp_path):
    """Test dry run output"""
    config_content = """
[profiles.test]
rules = [
    { id = "clean_empty_dirs", enabled = true, params = {} }
]
"""
    config_file = tmp_path / 'config.toml'
    with open(config_file, 'w') as f:
        f.write(config_content)

    rules_dir = tmp_path / 'rules'
    rules_dir.mkdir()
    rule_content = """
rules:
  - name: "Test"
    locations: ${locations}
    actions:
      - echo: "test"
"""
    with open(rules_dir / 'clean_empty_dirs.yaml', 'w') as f:
        f.write(rule_content)

    generator = OrganizefGenerator(config_file, rules_dir)

    yaml_content = generator.generate_yaml('test', ['/test/path'])
    assert isinstance(yaml_content, str)
    assert 'rules:' in yaml_content