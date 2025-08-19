"""
路径过滤器模块

提供统一的路径过滤功能，支持黑名单检查、路径验证等操作
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
from loguru import logger
from rich.console import Console

console = Console()

class PathFilter:
    """路径过滤器类"""
    
    def __init__(self, config_file: str = "blacklist_config.json"):
        """
        初始化路径过滤器
        
        参数:
        config_file (str): 配置文件名
        """
        self.config_path = Path(__file__).parent / config_file
        self.blacklist_config = self._load_config()
        
    def _load_config(self) -> Dict:
        """
        加载黑名单配置文件
        
        返回:
        dict: 配置字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"已加载路径过滤配置文件: {self.config_path}")
                return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"无法加载路径过滤配置文件 {self.config_path}: {e}")
            return {}
    
    def get_blacklist(self, mode: str) -> List[str]:
        """
        获取指定模式的黑名单
        
        参数:
        mode (str): 模式名称
        
        返回:
        list: 黑名单关键词列表
        """
        blacklist = self.blacklist_config.get(mode, [])
        if blacklist:
            logger.info(f"已加载 {mode} 模式的 {len(blacklist)} 个黑名单关键词")
        else:
            logger.info(f"{mode} 模式的黑名单为空或不存在")
        return blacklist
    
    def is_blacklisted(self, path: Path, blacklist: List[str]) -> Tuple[bool, str]:
        """
        检查单个路径是否在黑名单中
        
        参数:
        path (Path): 要检查的路径
        blacklist (List[str]): 黑名单关键词列表
        
        返回:
        tuple: (是否在黑名单中, 匹配的关键词)
        """
        if not blacklist:
            return False, ""
            
        path_str = str(path).lower()
        path_name = path.name.lower()
        
        for keyword in blacklist:
            keyword_lower = keyword.lower()
            if keyword_lower in path_str or keyword_lower in path_name:
                return True, keyword
        
        return False, ""
    
    def filter_paths(self, paths: List[Path], mode: str, log_skipped: bool = True) -> Tuple[List[Path], List[Path], Dict[str, List[Path]]]:
        """
        批量过滤路径列表
        
        参数:
        paths (List[Path]): 要过滤的路径列表
        mode (str): 过滤模式
        log_skipped (bool): 是否记录跳过的路径
        
        返回:
        tuple: (有效路径列表, 跳过路径列表, 按关键词分组的跳过路径)
        """
        blacklist = self.get_blacklist(mode)
        valid_paths = []
        skipped_paths = []
        skipped_by_keyword = {}
        
        for path in paths:
            is_blocked, keyword = self.is_blacklisted(path, blacklist)
            
            if is_blocked:
                skipped_paths.append(path)
                if keyword not in skipped_by_keyword:
                    skipped_by_keyword[keyword] = []
                skipped_by_keyword[keyword].append(path)
                
                if log_skipped:
                    logger.info(f"跳过黑名单路径: {path} (关键词: {keyword})")
                    console.print(f"[yellow]跳过黑名单路径:[/yellow] {path} [dim](关键词: {keyword})[/dim]")
            else:
                valid_paths.append(path)
        
        # 输出统计信息
        total_paths = len(paths)
        valid_count = len(valid_paths)
        skipped_count = len(skipped_paths)
        
        logger.info(f"路径过滤完成 - 总计: {total_paths}, 有效: {valid_count}, 跳过: {skipped_count}")
        
        if skipped_count > 0 and log_skipped:
            console.print(f"[cyan]路径过滤统计:[/cyan] 总计 {total_paths} 个，有效 {valid_count} 个，跳过 {skipped_count} 个")
            
            # 按关键词分组显示跳过的路径
            for keyword, keyword_paths in skipped_by_keyword.items():
                console.print(f"  [yellow]关键词 '{keyword}':[/yellow] 跳过 {len(keyword_paths)} 个路径")
        
        return valid_paths, skipped_paths, skipped_by_keyword
    
    def add_to_blacklist(self, mode: str, keywords: List[str]) -> bool:
        """
        向指定模式的黑名单添加关键词
        
        参数:
        mode (str): 模式名称
        keywords (List[str]): 要添加的关键词列表
        
        返回:
        bool: 是否成功添加
        """
        try:
            if mode not in self.blacklist_config:
                self.blacklist_config[mode] = []
            
            # 去重添加
            current_blacklist = set(self.blacklist_config[mode])
            new_keywords = [kw for kw in keywords if kw not in current_blacklist]
            
            if new_keywords:
                self.blacklist_config[mode].extend(new_keywords)
                self._save_config()
                logger.info(f"向 {mode} 模式添加了 {len(new_keywords)} 个新关键词")
                return True
            else:
                logger.info(f"所有关键词已在 {mode} 模式的黑名单中")
                return True
                
        except Exception as e:
            logger.error(f"添加黑名单关键词失败: {e}")
            return False
    
    def remove_from_blacklist(self, mode: str, keywords: List[str]) -> bool:
        """
        从指定模式的黑名单移除关键词
        
        参数:
        mode (str): 模式名称
        keywords (List[str]): 要移除的关键词列表
        
        返回:
        bool: 是否成功移除
        """
        try:
            if mode not in self.blacklist_config:
                logger.warning(f"模式 {mode} 不存在于配置中")
                return False
            
            current_blacklist = self.blacklist_config[mode]
            removed_count = 0
            
            for keyword in keywords:
                if keyword in current_blacklist:
                    current_blacklist.remove(keyword)
                    removed_count += 1
            
            if removed_count > 0:
                self._save_config()
                logger.info(f"从 {mode} 模式移除了 {removed_count} 个关键词")
            
            return True
            
        except Exception as e:
            logger.error(f"移除黑名单关键词失败: {e}")
            return False
    
    def _save_config(self) -> bool:
        """
        保存配置到文件
        
        返回:
        bool: 是否保存成功
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.blacklist_config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get_statistics(self, mode: str = None) -> Dict:
        """
        获取黑名单统计信息
        
        参数:
        mode (str): 指定模式，如果为None则返回所有模式的统计
        
        返回:
        dict: 统计信息
        """
        if mode:
            blacklist = self.blacklist_config.get(mode, [])
            return {
                'mode': mode,
                'keyword_count': len(blacklist),
                'keywords': blacklist
            }
        else:
            stats = {}
            for mode_name, keywords in self.blacklist_config.items():
                if mode_name != 'description' and isinstance(keywords, list):
                    stats[mode_name] = {
                        'keyword_count': len(keywords),
                        'keywords': keywords
                    }
            return stats
    
    def validate_paths(self, paths: List[Path]) -> Tuple[List[Path], List[Path]]:
        """
        验证路径列表的有效性
        
        参数:
        paths (List[Path]): 要验证的路径列表
        
        返回:
        tuple: (有效路径列表, 无效路径列表)
        """
        valid_paths = []
        invalid_paths = []
        
        for path in paths:
            if path.exists():
                valid_paths.append(path)
            else:
                invalid_paths.append(path)
                logger.warning(f"路径不存在: {path}")
        
        return valid_paths, invalid_paths


# 创建全局路径过滤器实例
path_filter = PathFilter()


# 便捷函数
def filter_archive_paths(paths: List[Path], log_skipped: bool = True) -> Tuple[List[Path], List[Path]]:
    """
    过滤单压缩包解散模式的路径
    
    参数:
    paths (List[Path]): 要过滤的路径列表
    log_skipped (bool): 是否记录跳过的路径
    
    返回:
    tuple: (有效路径列表, 跳过路径列表)
    """
    valid_paths, skipped_paths, _ = path_filter.filter_paths(paths, 'single_archive_folder', log_skipped)
    return valid_paths, skipped_paths


def filter_direct_paths(paths: List[Path], log_skipped: bool = True) -> Tuple[List[Path], List[Path]]:
    """
    过滤直接解散模式的路径
    
    参数:
    paths (List[Path]): 要过滤的路径列表
    log_skipped (bool): 是否记录跳过的路径
    
    返回:
    tuple: (有效路径列表, 跳过路径列表)
    """
    valid_paths, skipped_paths, _ = path_filter.filter_paths(paths, 'direct_dissolve', log_skipped)
    return valid_paths, skipped_paths


def is_path_safe(path: Path, mode: str) -> bool:
    """
    检查单个路径是否安全（不在黑名单中）
    
    参数:
    path (Path): 要检查的路径
    mode (str): 检查模式
    
    返回:
    bool: 如果路径安全则返回True
    """
    blacklist = path_filter.get_blacklist(mode)
    is_blocked, _ = path_filter.is_blacklisted(path, blacklist)
    return not is_blocked


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description='路径过滤器测试')
    parser.add_argument('--mode', type=str, default='single_archive_folder', 
                      help='过滤模式')
    parser.add_argument('--stats', action='store_true', 
                      help='显示统计信息')
    parser.add_argument('paths', nargs='*', help='要测试的路径列表')
    
    args = parser.parse_args()
    
    filter_instance = PathFilter()
    
    if args.stats:
        stats = filter_instance.get_statistics()
        console.print("[bold cyan]黑名单统计信息:[/bold cyan]")
        for mode, info in stats.items():
            console.print(f"  [yellow]{mode}:[/yellow] {info['keyword_count']} 个关键词")
            for keyword in info['keywords']:
                console.print(f"    - {keyword}")
    
    if args.paths:
        test_paths = [Path(p) for p in args.paths]
        valid_paths, skipped_paths, _ = filter_instance.filter_paths(test_paths, args.mode)
        
        console.print(f"\n[bold green]测试结果:[/bold green]")
        console.print(f"有效路径: {len(valid_paths)} 个")
        console.print(f"跳过路径: {len(skipped_paths)} 个")
