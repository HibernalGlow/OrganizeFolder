# 默认删除模式
DELETE_PATTERNS = [
    {"pattern": r".*\.bak$", "type": "file", "description": "备份文件"},
    {"pattern": r"^temp_.*$", "type": "dir", "description": "临时文件夹"},
    {"pattern": r".*\.trash$", "type": "both", "description": "垃圾文件和文件夹"},
    {"pattern": r"^\[#hb\].*\.txt$", "type": "file", "description": "以[#hb]开头的txt文件"},
]

# 清理预设配置
CLEANING_PRESETS = {
    "empty_folders": {
        "name": "空文件夹清理",
        "description": "递归删除所有空文件夹",
        "function": "remove_empty_folders",
        "enabled": True
    },
    "backup_files": {
        "name": "备份文件清理", 
        "description": "删除.bak备份文件",
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r".*\.bak$", "type": "file", "description": "备份文件"}
        ],
        "enabled": True
    },
    "temp_folders": {
        "name": "临时文件夹清理",
        "description": "删除temp_开头的临时文件夹", 
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r"^temp_.*$", "type": "dir", "description": "临时文件夹"}
        ],
        "enabled": True
    },
    "trash_files": {
        "name": "垃圾文件清理",
        "description": "删除.trash文件和文件夹",
        "function": "remove_backup_and_temp", 
        "patterns": [
            {"pattern": r".*\.trash$", "type": "both", "description": "垃圾文件和文件夹"}
        ],
        "enabled": True
    },
    "hb_txt_files": {
        "name": "[#hb]文本文件清理",
        "description": "删除以[#hb]开头的txt文件",
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r"^\[#hb\].*\.txt$", "type": "file", "description": "以[#hb]开头的txt文件"}
        ],
        "enabled": True
    },
    "log_files": {
        "name": "日志文件清理",
        "description": "删除常见的日志文件",
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r".*\.log$", "type": "file", "description": "日志文件"},
            {"pattern": r".*\.log\.\d+$", "type": "file", "description": "轮转日志文件"}
        ],
        "enabled": False  # 默认不启用
    },
    "upscale": {
        "name": "upscale文件清理",
        "description": "删除常见的upscale文件",
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r".*\.upbak$", "type": "file", "description": "upbak文件"}
        ],
        "enabled": False  # 默认不启用
    }
}

# 预设组合配置
PRESET_COMBINATIONS = {
    "advanced": {
        "name": "高级清理",
        "description": "标准清理 + [#hb]文本文件",
        "presets": ["empty_folders", "backup_files", "temp_folders", "trash_files", "hb_txt_files"]
    },
    "upscale": {
        "name": "upscale环境清理",
        "description": "适用于upscale环境的清理，包含缓存文件夹",
        "presets": ["empty_folders", "backup_files", "temp_folders", "trash_files", "hb_txt_files", "log_files", "upscale"]
    },
    "complete": {
        "name": "完整清理",
        "description": "包含所有清理项目（谨慎使用）",
        "presets": list(CLEANING_PRESETS.keys())
    }
}