#!/usr/bin/env python3
"""
从synct生成的预览JSON文件中提取一级文件夹路径的工具

使用方法:
    python extract_first_level_folders.py [json_file_path]
    
如果不指定json_file_path，会在当前目录查找synct_preview.json
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Optional
import argparse


def find_preview_json(start_dir: str = ".") -> Optional[str]:
    """在指定目录及其子目录中查找synct_preview.json文件"""
    start_path = Path(start_dir)
    
    # 首先在当前目录查找
    json_file = start_path / "synct_preview.json"
    if json_file.exists():
        return str(json_file)
    
    # 在子目录中查找
    for json_file in start_path.rglob("synct_preview.json"):
        return str(json_file)
    
    return None


def extract_first_level_folders(json_file_path: str) -> List[str]:
    """从JSON文件中提取一级文件夹路径"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 获取一级文件夹列表
        first_level_folders = data.get("一级文件夹", [])
        
        if not first_level_folders:
            print("⚠️ JSON文件中没有找到一级文件夹信息")
            return []
        
        return first_level_folders
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {json_file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
        return []
    except Exception as e:
        print(f"❌ 读取文件时发生错误: {e}")
        return []


def save_to_file(folders: List[str], output_file: str) -> bool:
    """将文件夹路径保存到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# synct 一级文件夹路径列表\n")
            f.write(f"# 总计: {len(folders)} 个文件夹\n\n")
            for folder in folders:
                f.write(f"{folder}\n")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")
        return False


def copy_to_clipboard(folders: List[str]) -> bool:
    """复制路径列表到剪贴板"""
    try:
        import pyperclip
        content = "\n".join(folders)
        pyperclip.copy(content)
        return True
    except ImportError:
        print("⚠️ 未安装pyperclip，无法复制到剪贴板")
        return False
    except Exception as e:
        print(f"⚠️ 复制到剪贴板失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="从synct预览JSON中提取一级文件夹路径")
    parser.add_argument("json_file", nargs="?", help="JSON文件路径（可选，默认查找synct_preview.json）")
    parser.add_argument("-o", "--output", help="输出文件路径（可选）")
    parser.add_argument("-c", "--clipboard", action="store_true", help="复制到剪贴板")
    parser.add_argument("--no-display", action="store_true", help="不在控制台显示路径")
    
    args = parser.parse_args()
    
    # 确定JSON文件路径
    if args.json_file:
        json_file_path = args.json_file
    else:
        json_file_path = find_preview_json()
        if not json_file_path:
            print("❌ 未找到synct_preview.json文件")
            print("请指定JSON文件路径或在包含该文件的目录中运行")
            sys.exit(1)
    
    print(f"📁 读取JSON文件: {json_file_path}")
    
    # 提取一级文件夹路径
    folders = extract_first_level_folders(json_file_path)
    
    if not folders:
        sys.exit(1)
    
    print(f"✅ 找到 {len(folders)} 个一级文件夹")
    
    # 显示路径
    if not args.no_display:
        print("\n📋 一级文件夹路径:")
        for i, folder in enumerate(folders, 1):
            print(f"  {i}. {folder}")
    
    # 保存到文件
    if args.output:
        if save_to_file(folders, args.output):
            print(f"\n💾 已保存到文件: {args.output}")
        else:
            sys.exit(1)
    
    # 复制到剪贴板
    if args.clipboard:
        if copy_to_clipboard(folders):
            print("\n📋 已复制到剪贴板")
    
    print(f"\n🎉 完成！共处理 {len(folders)} 个一级文件夹路径")


if __name__ == "__main__":
    main()
