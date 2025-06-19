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
    "cache_folders": {
        "name": "缓存文件夹清理",
        "description": "删除常见的缓存文件夹",
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r"^__pycache__$", "type": "dir", "description": "Python缓存文件夹"},
            {"pattern": r"^\.cache$", "type": "dir", "description": "通用缓存文件夹"},
            {"pattern": r"^node_modules$", "type": "dir", "description": "Node.js模块文件夹"},
            {"pattern": r"^\.git$", "type": "dir", "description": "Git版本控制文件夹"}
        ],
        "enabled": False  # 默认不启用，因为可能误删重要文件
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
    "thumbnail_files": {
        "name": "缩略图文件清理", 
        "description": "删除系统生成的缩略图文件",
        "function": "remove_backup_and_temp",
        "patterns": [
            {"pattern": r"^Thumbs\.db$", "type": "file", "description": "Windows缩略图数据库"},
            {"pattern": r"^\.DS_Store$", "type": "file", "description": "macOS文件夹属性文件"},
            {"pattern": r"^desktop\.ini$", "type": "file", "description": "Windows文件夹配置文件"}
        ],
        "enabled": False  # 默认不启用
    }
}

# 预设组合配置
PRESET_COMBINATIONS = {
    "basic": {
        "name": "基础清理",
        "description": "删除空文件夹和基本备份文件",
        "presets": ["empty_folders", "backup_files"]
    },
    "standard": {
        "name": "标准清理", 
        "description": "基础清理 + 临时文件和垃圾文件",
        "presets": ["empty_folders", "backup_files", "temp_folders", "trash_files"]
    },
    "advanced": {
        "name": "高级清理",
        "description": "标准清理 + [#hb]文本文件",
        "presets": ["empty_folders", "backup_files", "temp_folders", "trash_files", "hb_txt_files"]
    },
    "development": {
        "name": "开发环境清理",
        "description": "适用于开发环境的清理，包含缓存文件夹",
        "presets": ["empty_folders", "backup_files", "temp_folders", "cache_folders"]
    },
    "system": {
        "name": "系统文件清理",
        "description": "清理系统生成的文件，如缩略图等",
        "presets": ["empty_folders", "thumbnail_files"]
    },
    "complete": {
        "name": "完整清理",
        "description": "包含所有清理项目（谨慎使用）",
        "presets": list(CLEANING_PRESETS.keys())
    }
}