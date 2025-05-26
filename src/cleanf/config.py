DELETE_PATTERNS = [
    {"pattern": r".*\.bak$", "type": "file", "description": "备份文件"},
    {"pattern": r"^temp_.*$", "type": "dir", "description": "临时文件夹"},
    {"pattern": r".*\.trash$", "type": "both", "description": "垃圾文件和文件夹"},
    {"pattern": r"^\[#hb\].*\.txt$", "type": "file", "description": "以[#hb]开头的txt文件"},
] 