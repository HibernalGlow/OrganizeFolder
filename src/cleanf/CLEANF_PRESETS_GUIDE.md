# cleanf 文件清理工具 - 多预设功能使用说明

## 功能概述

cleanf 现已支持多预设功能，提供灵活的清理选项，可以使用预设组合或自定义选择清理项目。

## 新增功能

### 1. 清理预设
- **空文件夹清理**: 递归删除所有空文件夹
- **备份文件清理**: 删除.bak备份文件  
- **临时文件夹清理**: 删除temp_开头的临时文件夹
- **垃圾文件清理**: 删除.trash文件和文件夹
- **[#hb]文本文件清理**: 删除以[#hb]开头的txt文件
- **缓存文件夹清理**: 删除常见的缓存文件夹(__pycache__, .cache, node_modules等)
- **日志文件清理**: 删除常见的日志文件(.log文件)
- **缩略图文件清理**: 删除系统生成的缩略图文件(Thumbs.db, .DS_Store等)

### 2. 预设组合
- **basic**: 基础清理 - 删除空文件夹和基本备份文件
- **standard**: 标准清理 - 基础清理 + 临时文件和垃圾文件  
- **advanced**: 高级清理 - 标准清理 + [#hb]文本文件
- **development**: 开发环境清理 - 适用于开发环境，包含缓存文件夹
- **system**: 系统文件清理 - 清理系统生成的文件，如缩略图等
- **complete**: 完整清理 - 包含所有清理项目（谨慎使用）

## 使用方法

### 1. 列出所有可用预设
```bash
python -m src.cleanf --list-presets
```

### 2. 使用预设组合
```bash
# 使用基础清理预设
python -m src.cleanf --preset basic /path/to/directory

# 使用标准清理预设
python -m src.cleanf --preset standard /path/to/directory

# 使用高级清理预设
python -m src.cleanf --preset advanced /path/to/directory
```

### 3. 交互式界面
```bash
# 启动交互式界面
python -m src.cleanf

# 或明确指定交互模式
python -m src.cleanf --interactive
```

在交互式界面中，您可以：
1. 选择路径输入方式（剪贴板、手动输入）
2. 选择清理模式：
   - 使用预设组合：从6个预设组合中选择
   - 自定义选择：从8个清理项目中任意组合选择
3. 设置排除关键词
4. 实时查看清理进度和结果

### 4. 传统命令行参数（向后兼容）
```bash
# 删除空文件夹
python -m src.cleanf --empty /path/to/directory

# 删除备份文件
python -m src.cleanf --backup /path/to/directory

# 执行所有操作
python -m src.cleanf --all /path/to/directory
```

### 5. 其他选项
```bash
# 从剪贴板读取路径
python -m src.cleanf --clipboard --preset standard

# 排除特定关键词
python -m src.cleanf --preset basic --exclude "important,keep" /path/to/directory
```

## 示例

### 基础清理示例
```bash
python -m src.cleanf --preset basic /Users/username/Downloads
```
这将删除Downloads文件夹中的空文件夹和.bak备份文件。

### 开发环境清理示例  
```bash
python -m src.cleanf --preset development /path/to/project
```
这将删除项目中的空文件夹、备份文件、临时文件夹和缓存文件夹（如__pycache__、node_modules等）。

### 交互式使用示例
1. 运行 `python -m src.cleanf`
2. 选择"1"从剪贴板读取路径（提前复制好要清理的文件夹路径）
3. 选择"1"使用预设组合
4. 选择"2"使用标准清理
5. 根据需要设置排除关键词
6. 确认开始清理

## 安全提示

- **缓存文件夹清理**、**日志文件清理**和**缩略图文件清理**默认不启用，避免误删重要文件
- 使用**complete**完整清理时请格外谨慎
- 建议首次使用时从**basic**或**standard**预设开始
- 清理前请确认没有重要文件在清理范围内
- 可以使用排除关键词保护特定文件夹

## 日志记录

每次运行都会在`logs/cleanf/`目录下生成详细的日志文件，记录：
- 清理操作的详细过程
- 删除的文件和文件夹列表
- 错误和警告信息
- 操作统计信息
