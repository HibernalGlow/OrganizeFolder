# mergef - 分段文件夹合并工具

## 功能概述

mergef 是一个强大的分段文件夹合并工具，支持多种命名格式的自动识别和合并。它可以处理各种常见的分段文件夹命名方式，并且支持用户自定义模式。

## 支持的命名格式

### 默认支持的格式

1. **经典Part格式**
   - `Movie part1`, `Movie part2`, `Movie part3`
   - `Game p1`, `Game p2`, `Game p3`

2. **横线数字格式**
   - `Movie-1-1`, `Movie-1-2`, `Movie-1-3`
   - `Series_2_1`, `Series_2_2`

3. **简单数字格式**
   - `Movie1`, `Movie2`, `Movie3`
   - `Document 1`, `Document 2`

4. **方括号格式**
   - `Movie[part1]`, `Movie[part2]`
   - `Series[p1]`, `Series[p2]`

5. **圆括号格式**
   - `Movie(part1)`, `Movie(part2)`
   - `Game(p1)`, `Game(p2)`

6. **点分隔格式**
   - `Movie.part1`, `Movie.part2`
   - `Series.p1`, `Series.p2`

7. **CD/光盘格式**
   - `Movie cd1`, `Movie cd2`
   - `Game disc1`, `Game disc2`

8. **卷格式**
   - `Archive vol1`, `Archive vol2`
   - `Backup volume1`, `Backup volume2`

## 使用方法

### 基本命令

```bash
# 基本合并操作（交互式）
mergef

# 命令行合并
mergef merge /path/to/folder

# 预览模式（不实际执行）
mergef merge --preview /path/to/folder

# 从剪贴板读取路径
mergef merge --clipboard

# 指定特定模式
mergef merge --pattern classic_part /path/to/folder
```

### 查看支持的模式

```bash
# 显示所有支持的模式
mergef patterns
```

### 配置管理

```bash
# 添加自定义模式
mergef config add --name "my_pattern" \
  --pattern "^(.+?)[-_](\d+)[-_](\d+)$" \
  --target "[-_]1[-_]1$" \
  --desc "自定义格式" \
  --example "Movie-1-1, Movie-1-2"

# 列出自定义模式
mergef config list

# 删除自定义模式
mergef config remove my_pattern

# 测试模式
mergef config test my_pattern "Movie-1-1"
```

## 自定义模式

### 正则表达式规则

自定义模式需要提供两个正则表达式：

1. **主模式** (`pattern`): 用于提取基本名称和识别分段文件夹
   - 必须使用括号 `()` 包围基本名称部分
   - 第一个捕获组应该是基本名称
   - 后续捕获组可以用于排序

2. **目标模式** (`target_pattern`): 用于识别目标文件夹（通常是第一个分段）

### 示例

#### 示例1: 支持 `part1-1`, `part1-2` 格式

```bash
mergef config add \
  --name "double_dash" \
  --pattern "^(.+?)[-_](\d+)[-_](\d+)$" \
  --target "[-_]1[-_]1$" \
  --desc "双数字格式：name-1-1, name-1-2" \
  --example "Movie-1-1, Movie-1-2"
```

#### 示例2: 支持自定义前缀

```bash
mergef config add \
  --name "section_format" \
  --pattern "^(.+?)[-_ ]*section[-_ ]*(\d+)$" \
  --target "[-_ ]*section[-_ ]*1$" \
  --desc "章节格式：name section1, name section2" \
  --example "Book section1, Book section2"
```

## 工作原理

1. **扫描文件夹**: 扫描指定路径下的所有一级文件夹
2. **模式匹配**: 使用配置的模式识别分段文件夹
3. **分组处理**: 将同基本名称的文件夹分组
4. **确定目标**: 识别目标文件夹（通常是编号最小的）
5. **合并操作**: 
   - 将其他分段文件夹的内容移动到目标文件夹
   - 删除空的分段文件夹
   - 重命名目标文件夹为基本名称

## 注意事项

- 合并操作会修改文件系统，建议先使用 `--preview` 模式查看将要执行的操作
- 工具会自动处理重名文件，添加数字后缀
- 支持同时处理多种不同格式的分段文件夹
- 自定义模式会被保存到用户配置文件中，下次运行时自动加载

## 配置文件位置

- Windows: `%APPDATA%\mergef\patterns.json`
- Linux/macOS: `~/.config/mergef/patterns.json`

## 依赖

- Python 3.7+
- typer
- rich
- pyperclip
- loguru
