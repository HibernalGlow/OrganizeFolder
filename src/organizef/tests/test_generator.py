import pytest
from pathlib import Path
import yaml
from organizef.generator import OrganizefGenerator

@pytest.fixture
def config_path(tmp_path):
    config_content = """
[profiles.clean_empty]
description = "Clean empty directories"
rules = [
    { id = "clean_empty_dirs", enabled = true, params = { exclude_dirs = ["important", "backup"] } }
]

[profiles.move_videos]
description = "Move video files"
rules = [
    { id = "move_videos", enabled = true, params = { video_extensions = ["mp4", "avi", "mkv"] } }
]
"""
    config_file = tmp_path / 'config.toml'
    with open(config_file, 'w') as f:
        f.write(config_content)
    return config_file

@pytest.fixture
def rules_dir(tmp_path):
    rules_dir = tmp_path / 'rules'
    rules_dir.mkdir()

    # Create clean_empty_dirs.yaml
    clean_rule = {
        'rules': [{
            'name': 'Remove empty directories',
            'locations': '${locations}',
            'subfolders': True,
            'targets': 'dirs',
            'filters': [{'empty': None}],
            'actions': [{'echo': 'Found empty directory: {path}'}, {'delete': None}]
        }]
    }
    with open(rules_dir / 'clean_empty_dirs.yaml', 'w') as f:
        yaml.dump(clean_rule, f)

    # Create move_videos.yaml
    video_rule = {
        'rules': [{
            'name': 'Move Videos to [video] Folder',
            'locations': '${locations}',
            'subfolders': True,
            'filters': [{'extension': '${video_extensions}'}],
            'actions': [{'move': '{location}/[video]/{path.relative_to(location)}'}]
        }]
    }
    with open(rules_dir / 'move_videos.yaml', 'w') as f:
        yaml.dump(video_rule, f)

    return rules_dir

def test_generate_clean_empty_yaml(config_path, rules_dir):
    generator = OrganizefGenerator(config_path, rules_dir)
    yaml_content = generator.generate_yaml('clean_empty', ['/test/path'])

    parsed = yaml.safe_load(yaml_content)
    assert 'rules' in parsed
    assert len(parsed['rules']) == 1

    rule = parsed['rules'][0]
    assert rule['name'] == 'Remove empty directories'
    assert len(rule['locations']) == 1
    assert rule['locations'][0]['path'] == '/test/path'
    assert rule['locations'][0]['exclude_dirs'] == ['important', 'backup']
    assert rule['subfolders'] is True
    assert rule['targets'] == 'dirs'
    assert 'empty' in rule['filters'][0]
    assert len(rule['actions']) == 2

def test_generate_move_videos_yaml(config_path, rules_dir):
    generator = OrganizefGenerator(config_path, rules_dir)
    yaml_content = generator.generate_yaml('move_videos', ['/test/path'])

    parsed = yaml.safe_load(yaml_content)
    assert 'rules' in parsed
    assert len(parsed['rules']) == 1

    rule = parsed['rules'][0]
    assert rule['name'] == 'Move Videos to [video] Folder'
    assert len(rule['locations']) == 1
    assert rule['locations'][0]['path'] == '/test/path'
    assert rule['subfolders'] is True
    assert rule['filters'][0]['extension'] == ['mp4', 'avi', 'mkv']
    assert rule['actions'][0]['move'] == '{location}/[video]/{path.relative_to(location)}'

def test_generate_multiple_paths(config_path, rules_dir):
    generator = OrganizefGenerator(config_path, rules_dir)
    yaml_content = generator.generate_yaml('clean_empty', ['/path1', '/path2'])

    parsed = yaml.safe_load(yaml_content)
    rule = parsed['rules'][0]
    assert len(rule['locations']) == 2
    assert rule['locations'][0]['path'] == '/path1'
    assert rule['locations'][1]['path'] == '/path2'
    # Both should have exclude_dirs
    assert rule['locations'][0]['exclude_dirs'] == ['important', 'backup']
    assert rule['locations'][1]['exclude_dirs'] == ['important', 'backup']

def test_invalid_profile(config_path, rules_dir):
    generator = OrganizefGenerator(config_path, rules_dir)
    with pytest.raises(ValueError, match="Profile nonexistent not found"):
        generator.generate_yaml('nonexistent', ['/test/path'])

def test_disabled_rule(config_path, rules_dir):
    # Modify config to disable rule
    config_content = """
[profiles.clean_empty]
description = "Clean empty directories"
rules = [
    { id = "clean_empty_dirs", enabled = false, params = { exclude_dirs = ["important", "backup"] } }
]
"""
    with open(config_path, 'w') as f:
        f.write(config_content)

    generator = OrganizefGenerator(config_path, rules_dir)
    yaml_content = generator.generate_yaml('clean_empty', ['/test/path'])

    parsed = yaml.safe_load(yaml_content)
    assert len(parsed['rules']) == 0  # No rules should be generated