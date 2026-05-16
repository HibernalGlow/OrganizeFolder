# TransQ - 翻译结果整理工具

翻译结果整理工具，用于处理 manga-translator 翻译后的图片文件夹。

## 功能

- ✅ 扫描所有 `original_images` 目录
- ✅ 通过 `translation_map.json` 比较 `original_images` 和 `result` 文件数量
- ✅ 补全 `result` 内缺失的原图
- ✅ 删除 `original_images` 到回收站（确保 result 内是唯一且完整的）
- ✅ 删除 `manga_translator_work` 下的 `inpainted` 和 `json` 文件

## 使用方法

### 无参数启动（显示帮助）

```bash
transq
```

### 预览模式（默认，不执行，只查看将要进行的操作）

```bash
transq <扫描路径>
```

### 执行模式

```bash
transq <扫描路径> --execute
```

### 示例

```bash
# 预览模式
transq "E:\1Hub\EH\2EHV\tr\soul-ibm5100-7702-20260101-PIXIV FANBOX\2023"

# 执行模式
transq "E:\1Hub\EH\2EHV\tr\soul-ibm5100-7702-20260101-PIXIV FANBOX\2023" --execute
```

## 输出示例

### 无参数启动

```
╭───────────────────────────────────────╮
│ 翻译结果整理工具                      │
│                                       │
│ 用法:                                 │
│   transq <路径>              预览模式 │
│   transq <路径> --execute    执行模式 │
│                                       │
│ 示例:                                 │
│   transq "E:\翻译结果" --dry-run      │
│   transq "E:\翻译结果" --execute      │
│                                       │
│ 功能:                                 │
│   • 扫描所有 original_images 目录     │
│   • 补全 result 内缺失的原图          │
│   • 删除工作文件到回收站              │
│   • 移动 result 到正确位置            │
│   • 删除 original_images 到回收站     │
╰───────────────────────────────────────╯
```

### 预览结果

```
╭───────────────────────────────────────────────────────────────────────────╮
│ 翻译结果整理工具                                                          │
│ 扫描目录: E:\1Hub\EH\2EHV\tr\soul-ibm5100-7702-20260101-PIXIV FANBOX\2023 │
│ 模式: 预览模式                                                            │
╰───────────────────────────────────────────────────────────────────────────╯

✓ 共找到 46 个 original_images 目录

  处理目录... ---------------------------------------- 100%

┌────────────────────────────────────┐
│ 预览结果                           │
│ 以下是将要执行的操作（未实际执行） │
└────────────────────────────────────┘
┌────────────────┬──────┐
│ 统计项         │ 数量 │
├────────────────┼──────┤
│ 扫描目录数     │   46 │
│ 复制文件数     │  487 │
│ 删除原图数     │  581 │
│ 删除工作文件数 │  301 │
│ 错误数         │    0 │
└────────────────┴──────┘

提示: 使用 --execute 参数执行实际操作
示例: transq "路径" --execute
```

## 目录结构

工具会扫描以下目录结构：

```
<扫描路径>/
├── <文件夹1>/
│   ├── original_images/          # 原图目录（将被删除到回收站）
│   ├── result/                   # 翻译结果目录（确保完整）
│   │   ├── translation_map.json  # 翻译映射文件
│   │   ├── image1.jpg            # 翻译后的图片
│   │   └── image2.jpg
│   └── manga_translator_work/    # 工作目录
│       ├── inpainted/            # 将被删除到回收站
│       └── *.json                # 将被删除到回收站
└── <文件夹2>/
    └── ...
```

## 工作流程

1. **扫描**：递归扫描所有 `original_images` 目录
2. **分析**：读取 `translation_map.json`，比较 `original_images` 和 `result` 文件数量
3. **补全**：将缺失的原图复制到 `result` 目录
4. **清理**：
   - 删除 `manga_translator_work/inpainted` 到回收站
   - 删除 `manga_translator_work/*.json` 到回收站
5. **移动**：将 `result` 目录移动到 `original_images` 的父目录
6. **删除**：删除整个 `original_images` 目录到回收站

## 目录结构

工具会扫描以下目录结构：

```
<扫描路径>/
├── <文件夹1>/
│   ├── original_images/              # 原图目录（将被删除到回收站）
│   │   ├── image1.jpg                # 原图文件
│   │   ├── image2.jpg
│   │   └── manga_translator_work/    # 工作目录
│   │       ├── inpainted/            # 将被删除到回收站
│   │       ├── result/               # 翻译结果（将被移动到父目录）
│   │       │   ├── translation_map.json
│   │       │   ├── image1.jpg
│   │       │   └── image2.jpg
│   │       └── *.json                # 将被删除到回收站
│   └── .archive_source.txt
└── <文件夹2>/
    └── ...
```

## 处理后的目录结构

```
<扫描路径>/
├── <文件夹1>/
│   ├── result/                       # 翻译结果（从 original_images/manga_translator_work/result 移动）
│   │   ├── translation_map.json
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   └── .archive_source.txt
└── <文件夹2>/
    └── ...
```
