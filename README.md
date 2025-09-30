# organizef

一个围绕 [organize](https://github.com/tfeldmann/organize) 构建的规则生成器，用于将常见的 dissolvef / cleanf / mergef 工作流程整合到一套 declarative 配置中。新版架构移除了 Jinja 模板和内联 Python 代码，全部规则都由内置的 Python builder 组合生成，最终输出可直接交给 `organize run` 的纯 YAML 文件。

## 快速开始

1. 在当前仓库根目录执行
	 ```powershell
	 python -m organizef list --config src\organizef\config.toml
	 ```
	 查看可用的 profile 组合。
2. 选择一个或多个 profile，指定要处理的目录后生成 YAML：
	 ```powershell
	 python -m organizef generate `
		 --config src\organizef\config.toml `
		 --profile clean_basic `
		 --location D:\Media `
		 --dry-run
	 ```
3. 确认输出后，移除 `--dry-run` 或加上 `--run` 让 organize 直接执行。

## 可用的规则构建器

| builder 名称        | 功能概述                                    | 关键 context 参数                        |
| ------------------- | ------------------------------------------- | ---------------------------------------- |
| `clean_empty`       | 删除空文件夹                                | `name`, `subfolders`, `max_depth`        |
| `clean_patterns`    | 通过正则批量删除临时文件                    | `patterns`, `case_sensitive`             |
| `dissolve_nested`   | 扁平化仅含单子目录的嵌套结构                | `exclude`, `preview`                     |
| `dissolve_media`    | 释放仅包含一个媒体文件的文件夹              | `extensions`, `exclude`, `preview`       |
| `dissolve_archive`  | 释放仅包含一个压缩包的文件夹                | `extensions`, `exclude`, `preview`       |
| `dissolve_direct`   | 将匹配目录内容直接上移到父级                | `patterns`, `file_conflict`, `dir_conflict`, `preview` |
| `merge_parts`       | 合并 `name-part1/part2` 形式的目录并重命名  | `backup`, `preview`                      |

所有构建器都会在生成的 YAML 中附加对应的 `shell` 操作，调用 `organizef.scripts` 下的专用子命令，从而在最终配置中完全避免内联代码。

## 示例配置

项目自带的 `src/organizef/config.toml` 演示了如何组合 profile：

```toml
[[profiles]]
key = "clean_basic"
description = "删除空目录与常见临时文件"

	[[profiles.rules]]
	builder = "clean_empty"
	context = { name = "删除空目录" }

	[[profiles.rules]]
	builder = "clean_patterns"
	context = { patterns = ["\\.tmp$", "\\.bak$", "~$"], case_sensitive = false }

[[profiles]]
key = "dissolve_media"
description = "释放媒体与压缩包"

	[[profiles.rules]]
	builder = "dissolve_media"
	context = { extensions = [".mp4", ".mkv", ".webm"], preview = false }

	[[profiles.rules]]
	builder = "dissolve_archive"
	context = { extensions = [".zip", ".rar", ".7z"] }
```

根据需要复制 profile、调整 `context` 即可定制生成的 organize 规则。

## 执行脚本

当 YAML 中出现 `shell: "python -m organizef.scripts.*"` 时，organize 会调用：

- `organizef.scripts.dissolve`：负责 nested/media/direct/archive 等解散逻辑；
- `organizef.scripts.merge`：负责合并 `part` 目录并可选备份。

运行 `organize sim` 时这些脚本不会真正执行，只会展示计划命令；只有 `organize run` 会触发实际移动/合并操作。

## 注意事项

- 保持 `python_command` 与 `organize_command` 设置正确，Windows 下若路径包含空格可直接写入完整路径。
- 若需要排除特定目录或文件，请在对应 builder 的 `context` 中编辑 `exclude`/`patterns`。
- 建议先使用 `--dry-run` 或 `organize sim` 观察输出，再执行正式操作。
