# TransQ - 翻译结果整理工具

翻译结果整理工具，用于处理 manga-translator 翻译后的图片文件夹。

## 功能

- ✅ 扫描所有 `original_images` 目录
- ✅ 通过 `translation_map.json` 比较 `original_images` 和 `result` 文件数量
- ✅ 补全 `result` 内缺失的原图
- ✅ 删除 `original_images` 到回收站（确保 result 内是唯一且完整的）
- ✅ 删除 `manga_translator_work` 下的 `inpainted` 和 `json` 文件

## 使用方法

### 预览模式（不执行，只查看将要进行的操作）

```bash
python -m transq <扫描路径> --dry-run
```

### 执行模式

```bash
python -m transq <扫描路径>
```

### 示例

```bash
# 预览模式
python -m transq D:\1VSCODE\Projects\ImageAll\manga-translator-ui\result --dry-run

# 执行模式
python -m transq D:\1VSCODE\Projects\ImageAll\manga-translator-ui\result
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
   - 删除 `original_images` 目录到回收站
   - 删除 `manga_translator_work/inpainted` 到回收站
   - 删除 `manga_translator_work/*.json` 到回收站

## 安全特性

- ✅ 所有删除操作都发送到回收站，可恢复
- ✅ 支持预览模式，先查看再执行
- ✅ 详细的日志输出，记录所有操作

## 依赖

- `send2trash`: 用于安全删除文件到回收站

## 安装依赖

```bash
pip install send2trash
```
