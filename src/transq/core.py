"""
翻译结果整理工具
扫描翻译后的 original_images 文件夹，确保 result 目录完整且唯一
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple
import send2trash
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TranslationMap:
    """翻译映射数据"""
    original_images_dir: Path
    result_dir: Path
    translation_map_file: Path
    original_files: Set[str]
    result_files: Set[str]
    missing_files: Set[str]
    extra_files: Set[str]


class TransqProcessor:
    """翻译结果整理处理器"""
    
    def __init__(self, root_path: Path, dry_run: bool = False):
        """
        初始化处理器
        
        Args:
            root_path: 根目录路径
            dry_run: 是否只预览不执行
        """
        self.root_path = Path(root_path)
        self.dry_run = dry_run
        self.stats = {
            'scanned_dirs': 0,
            'copied_files': 0,
            'deleted_originals': 0,
            'deleted_work_files': 0,
            'errors': 0
        }
    
    def scan_original_images_dirs(self) -> List[Path]:
        """
        扫描所有 original_images 目录
        
        Returns:
            original_images 目录列表
        """
        original_images_dirs = []
        
        for original_images in self.root_path.rglob('original_images'):
            if original_images.is_dir():
                result_dir = original_images / 'manga_translator_work' / 'result'
                if result_dir.exists():
                    original_images_dirs.append(original_images)
                    logger.info(f"找到 original_images: {original_images}")
        
        logger.info(f"共找到 {len(original_images_dirs)} 个 original_images 目录")
        return original_images_dirs
    
    def load_translation_map(self, result_dir: Path) -> Dict:
        """
        加载 translation_map.json
        
        Args:
            result_dir: result 目录路径
            
        Returns:
            翻译映射字典
        """
        translation_map_file = result_dir / 'translation_map.json'
        
        if not translation_map_file.exists():
            logger.warning(f"translation_map.json 不存在: {translation_map_file}")
            return {}
        
        try:
            with open(translation_map_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"加载 translation_map.json: {len(data)} 条映射")
                return data
        except Exception as e:
            logger.error(f"加载 translation_map.json 失败: {e}")
            return {}
    
    def analyze_directory(self, original_images_dir: Path) -> TranslationMap:
        """
        分析目录结构
        
        Args:
            original_images_dir: original_images 目录路径
            
        Returns:
            翻译映射数据
        """
        result_dir = original_images_dir / 'manga_translator_work' / 'result'
        translation_map_file = result_dir / 'translation_map.json'
        
        # 只统计 original_images 下的文件，不包括子目录
        original_files = {f.name for f in original_images_dir.iterdir() if f.is_file()}
        result_files = {f.name for f in result_dir.iterdir() if f.is_file() and f.name != 'translation_map.json'}
        
        translation_map = self.load_translation_map(result_dir)
        
        original_in_map = set(translation_map.keys())
        
        missing_files = original_in_map - result_files
        extra_files = result_files - original_in_map
        
        return TranslationMap(
            original_images_dir=original_images_dir,
            result_dir=result_dir,
            translation_map_file=translation_map_file,
            original_files=original_files,
            result_files=result_files,
            missing_files=missing_files,
            extra_files=extra_files
        )
    
    def copy_missing_files(self, trans_map: TranslationMap) -> int:
        """
        复制缺失的原图到 result 目录
        
        Args:
            trans_map: 翻译映射数据
            
        Returns:
            复制的文件数量
        """
        copied_count = 0
        
        for filename in trans_map.missing_files:
            src_file = trans_map.original_images_dir / filename
            dst_file = trans_map.result_dir / filename
            
            if src_file.exists():
                if self.dry_run:
                    logger.info(f"[预览] 将复制: {src_file} -> {dst_file}")
                    copied_count += 1
                else:
                    try:
                        shutil.copy2(src_file, dst_file)
                        logger.info(f"✅ 复制: {src_file.name} -> result")
                        copied_count += 1
                    except Exception as e:
                        logger.error(f"❌ 复制失败 {src_file}: {e}")
                        self.stats['errors'] += 1
        
        return copied_count
    
    def delete_original_images_to_trash(self, trans_map: TranslationMap) -> int:
        """
        删除 original_images 目录到回收站
        
        Args:
            trans_map: 翻译映射数据
            
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        
        if self.dry_run:
            logger.info(f"[预览] 将删除到回收站: {trans_map.original_images_dir}")
            return len(list(trans_map.original_images_dir.iterdir()))
        
        try:
            send2trash.send2trash(str(trans_map.original_images_dir))
            logger.info(f"🗑️ 已删除到回收站: {trans_map.original_images_dir}")
            deleted_count = len(trans_map.original_files)
        except Exception as e:
            logger.error(f"❌ 删除失败 {trans_map.original_images_dir}: {e}")
            self.stats['errors'] += 1
        
        return deleted_count
    
    def clean_manga_translator_work(self, original_images_dir: Path) -> Tuple[int, int]:
        """
        清理 manga_translator_work 目录下的 inpainted 和 json 文件
        
        Args:
            original_images_dir: original_images 目录路径
            
        Returns:
            (删除的 inpainted 数量, 删除的 json 数量)
        """
        work_dir = original_images_dir / 'manga_translator_work'
        
        if not work_dir.exists():
            logger.info(f"manga_translator_work 目录不存在: {work_dir}")
            return 0, 0
        
        deleted_inpainted = 0
        deleted_json = 0
        
        for item in work_dir.iterdir():
            if item.is_dir() and item.name == 'inpainted':
                if self.dry_run:
                    logger.info(f"[预览] 将删除: {item}")
                    deleted_inpainted += len(list(item.rglob('*')))
                else:
                    try:
                        send2trash.send2trash(str(item))
                        logger.info(f"🗑️ 已删除到回收站: {item}")
                        deleted_inpainted += 1
                    except Exception as e:
                        logger.error(f"❌ 删除失败 {item}: {e}")
                        self.stats['errors'] += 1
            
            elif item.is_file() and item.suffix == '.json':
                if self.dry_run:
                    logger.info(f"[预览] 将删除: {item}")
                    deleted_json += 1
                else:
                    try:
                        send2trash.send2trash(str(item))
                        logger.info(f"🗑️ 已删除到回收站: {item}")
                        deleted_json += 1
                    except Exception as e:
                        logger.error(f"❌ 删除失败 {item}: {e}")
                        self.stats['errors'] += 1
        
        return deleted_inpainted, deleted_json
    
    def process_directory(self, original_images_dir: Path) -> bool:
        """
        处理单个目录
        
        Args:
            original_images_dir: original_images 目录路径
            
        Returns:
            是否处理成功
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"处理目录: {original_images_dir}")
        logger.info(f"{'='*60}")
        
        try:
            trans_map = self.analyze_directory(original_images_dir)
            
            logger.info(f"original_images 文件数: {len(trans_map.original_files)}")
            logger.info(f"result 文件数: {len(trans_map.result_files)}")
            logger.info(f"缺失文件数: {len(trans_map.missing_files)}")
            logger.info(f"多余文件数: {len(trans_map.extra_files)}")
            
            if trans_map.missing_files:
                logger.info(f"\n缺失文件列表: {sorted(trans_map.missing_files)}")
            
            # 1. 补全缺失的原图
            copied = self.copy_missing_files(trans_map)
            self.stats['copied_files'] += copied
            
            # 2. 清理 manga_translator_work 下的 inpainted 和 json
            deleted_inpainted, deleted_json = self.clean_manga_translator_work(original_images_dir)
            self.stats['deleted_work_files'] += deleted_inpainted + deleted_json
            
            # 3. 移动 result 到 original_images 的父目录
            parent_dir = original_images_dir.parent
            new_result_dir = parent_dir / 'result'
            
            if self.dry_run:
                logger.info(f"[预览] 将移动: {trans_map.result_dir} -> {new_result_dir}")
            else:
                if new_result_dir.exists():
                    logger.warning(f"目标 result 目录已存在，跳过移动: {new_result_dir}")
                else:
                    try:
                        shutil.move(str(trans_map.result_dir), str(new_result_dir))
                        logger.info(f"✅ 移动 result: {trans_map.result_dir} -> {new_result_dir}")
                    except Exception as e:
                        logger.error(f"❌ 移动 result 失败: {e}")
                        self.stats['errors'] += 1
            
            # 4. 删除整个 original_images 目录到回收站
            if copied > 0 or len(trans_map.missing_files) == 0:
                deleted = self.delete_original_images_to_trash(trans_map)
                self.stats['deleted_originals'] += deleted
            
            self.stats['scanned_dirs'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理目录失败 {original_images_dir}: {e}")
            self.stats['errors'] += 1
            return False
    
    def run(self) -> Dict:
        """
        运行整理任务
        
        Returns:
            统计数据
        """
        logger.info(f"开始扫描目录: {self.root_path}")
        logger.info(f"模式: {'预览模式' if self.dry_run else '执行模式'}")
        
        original_images_dirs = self.scan_original_images_dirs()
        
        if not original_images_dirs:
            logger.warning("未找到任何 original_images 目录")
            return self.stats
        
        for original_images_dir in original_images_dirs:
            self.process_directory(original_images_dir)
        
        logger.info(f"\n{'='*60}")
        logger.info("处理完成！统计信息：")
        logger.info(f"{'='*60}")
        logger.info(f"扫描目录数: {self.stats['scanned_dirs']}")
        logger.info(f"复制文件数: {self.stats['copied_files']}")
        logger.info(f"删除原图数: {self.stats['deleted_originals']}")
        logger.info(f"删除工作文件数: {self.stats['deleted_work_files']}")
        logger.info(f"错误数: {self.stats['errors']}")
        
        return self.stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='翻译结果整理工具')
    parser.add_argument('path', type=str, help='要扫描的根目录路径')
    parser.add_argument('--dry-run', action='store_true', help='只预览不执行')
    
    args = parser.parse_args()
    
    processor = TransqProcessor(Path(args.path), dry_run=args.dry_run)
    processor.run()


if __name__ == '__main__':
    main()
