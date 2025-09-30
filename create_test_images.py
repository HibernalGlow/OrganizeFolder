#!/usr/bin/env python3#!/usr/bin/env python3#!/usr/bin/env python3

"""

创建测试图片文件用于测试列表参数功能""""""

"""

创建测试图片文件用于测试列表参数功能创建测试图片文件用于测试 organizef 图片分类功能

from pathlib import Path

from PIL import Image, ImageDraw""""""



def create_test_images():

    """创建各种格式的测试图片"""

import osimport os

    # 创建临时测试目录

    test_dir = Path("test_images")from pathlib import Pathimport sys

    test_dir.mkdir(exist_ok=True)

from PIL import Image, ImageDrawfrom pathlib import Path

    print(f"创建测试图片到: {test_dir}")

from PIL import Image, ImageDraw

    # 定义测试图片规格 - 针对新的列表参数逻辑

    test_specs = [def create_test_images():import tempfile

        # (文件名, 尺寸, 颜色, 描述)

        ("large_2500x1800.jpg", (2500, 1800), "red", "大图片 - 宽度2500 > 2000"),    """创建各种格式的测试图片"""

        ("large_3000x2000.png", (3000, 2000), "blue", "大图片 - 宽度3000 > 2000"),

        ("medium_800x600.jpg", (800, 600), "green", "中等图片 - 不匹配任何条件"),def create_test_images():

        ("small_100x100.jpg", (100, 100), "yellow", "小图片 - 100x100 < 500"),

        ("small_200x150.png", (200, 150), "purple", "小图片 - 200x150 < 500"),    # 创建临时测试目录    """创建各种格式的测试图片"""

        ("tiny_50x50.bmp", (50, 50), "orange", "极小图片 - 50x50 < 500"),

        ("hd_1920x1080.jpg", (1920, 1080), "cyan", "HD图片 - 宽度1920"),    test_dir = Path("test_images")

        ("fhd_1920x1080.png", (1920, 1080), "magenta", "Full HD图片"),

    ]    test_dir.mkdir(exist_ok=True)    # 创建临时测试目录



    created_files = []    test_dir = Path("test_images")



    for filename, size, color, desc in test_specs:    print(f"创建测试图片到: {test_dir}")    test_dir.mkdir(exist_ok=True)

        try:

            # 创建图片

            img = Image.new('RGB', size, color=color)

    # 定义测试图片规格 - 针对新的列表参数逻辑    print(f"创建测试图片到: {test_dir}")

            # 添加文字标签

            draw = ImageDraw.Draw(img)    test_specs = [

            text = f"{size[0]}x{size[1]}\n{desc}"

            draw.text((10, 10), text, fill='white')        # (文件名, 尺寸, 颜色, 描述)    # 定义测试图片规格



            # 保存图片        ("large_2500x1800.jpg", (2500, 1800), "red", "大图片 - 宽度2500 > 2000"),    test_specs = [

            filepath = test_dir / filename

            format_name = filename.split('.')[-1].upper()        ("large_3000x2000.png", (3000, 2000), "blue", "大图片 - 宽度3000 > 2000"),        # (文件名, 尺寸, 颜色, 描述)



            if format_name == 'JPG':        ("medium_800x600.jpg", (800, 600), "green", "中等图片 - 不匹配任何条件"),        ("small_100x100.jpg", (100, 100), "red", "小图片"),

                format_name = 'JPEG'

        ("small_100x100.jpg", (100, 100), "yellow", "小图片 - 100x100 < 500"),        ("small_200x150.png", (200, 150), "blue", "小图片"),

            img.save(filepath, format_name)

            print(f"✓ 创建 {filename} ({size[0]}x{size[1]}) - {desc}")        ("small_200x150.png", (200, 150), "purple", "小图片 - 200x150 < 500"),        ("medium_800x600.jpg", (800, 600), "green", "中等图片"),

            created_files.append(filepath)

        ("tiny_50x50.bmp", (50, 50), "orange", "极小图片 - 50x50 < 500"),        ("large_2500x1800.jpg", (2500, 1800), "yellow", "大图片"),

        except Exception as e:

            print(f"✗ 创建 {filename} 失败: {e}")        ("hd_1920x1080.jpg", (1920, 1080), "cyan", "HD图片 - 宽度1920"),        ("large_3000x2000.png", (3000, 2000), "purple", "大图片"),



    print(f"\n创建完成! 共 {len(created_files)} 个文件")        ("fhd_1920x1080.png", (1920, 1080), "magenta", "Full HD图片"),        ("tiny_50x50.bmp", (50, 50), "orange", "极小图片"),

    print("\n预期行为 (使用默认参数 [2000], [2000], [500], [500]):")

    print("- 大图片 (>2000px): large_2500x1800.jpg, large_3000x2000.png, hd_1920x1080.jpg, fhd_1920x1080.png")    ]    ]

    print("- 小图片 (<500px): small_100x100.jpg, small_200x150.png, tiny_50x50.bmp")

    print("- 不移动: medium_800x600.jpg")



    return test_dir    created_files = []    created_files = []



if __name__ == "__main__":

    create_test_images()
    for filename, size, color, desc in test_specs:    for filename, size, color, desc in test_specs:

        try:        try:

            # 创建图片            # 创建图片

            img = Image.new('RGB', size, color=color)            img = Image.new('RGB', size, color=color)



            # 添加文字标签            # 添加文字标签

            draw = ImageDraw.Draw(img)            draw = ImageDraw.Draw(img)

            text = f"{size[0]}x{size[1]}\n{desc}"            text = f"{size[0]}x{size[1]}\n{desc}"

            draw.text((10, 10), text, fill='white')            draw.text((10, 10), text, fill='white')



            # 保存图片            # 保存图片

            filepath = test_dir / filename            filepath = test_dir / filename

            format_name = filename.split('.')[-1].upper()            format_name = filename.split('.')[-1].upper()



            if format_name == 'JPG':            if format_name == 'JPG':

                format_name = 'JPEG'                format_name = 'JPEG'



            img.save(filepath, format_name)            img.save(filepath, format_name)

            print(f"✓ 创建 {filename} ({size[0]}x{size[1]}) - {desc}")            print(f"✓ 创建 {filename} ({size[0]}x{size[1]}) - {desc}")

            created_files.append(filepath)            created_files.append(filepath)



        except Exception as e:        except Exception as e:

            print(f"✗ 创建 {filename} 失败: {e}")            print(f"✗ 创建 {filename} 失败: {e}")



    print(f"\n创建完成! 共 {len(created_files)} 个文件")    # 尝试创建 AVIF 格式

    print("\n预期行为 (使用默认参数 [2000], [2000], [500], [500]):")    try:

    print("- 大图片 (>2000px): large_2500x1800.jpg, large_3000x2000.png, hd_1920x1080.jpg, fhd_1920x1080.png")        img = Image.new('RGB', (1200, 800), color='cyan')

    print("- 小图片 (<500px): small_100x100.jpg, small_200x150.png, tiny_50x50.bmp")        draw = ImageDraw.Draw(img)

    print("- 不移动: medium_800x600.jpg")        draw.text((10, 10), "1200x800\nAVIF测试", fill='black')



    return test_dir        avif_path = test_dir / 'medium_1200x800.avif'

        img.save(avif_path, 'AVIF')

if __name__ == "__main__":        print("✓ 创建 medium_1200x800.avif (1200x800) - AVIF测试")

    create_test_images()        created_files.append(avif_path)
    except Exception as e:
        print(f"✗ 创建 AVIF 失败: {e}")

    # 尝试创建 JXL 格式
    try:
        img = Image.new('RGB', (1500, 1000), color='magenta')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "1500x1000\nJXL测试", fill='white')

        jxl_path = test_dir / 'large_1500x1000.jxl'
        img.save(jxl_path, 'JXL')
        print("✓ 创建 large_1500x1000.jxl (1500x1000) - JXL测试")
        created_files.append(jxl_path)
    except Exception as e:
        print(f"✗ 创建 JXL 失败: {e}")

    # 创建一些其他格式
    other_specs = [
        ("test_400x300.webp", (400, 300), "lime", "WEBP"),
        ("test_600x400.tiff", (600, 400), "navy", "TIFF"),
    ]

    for filename, size, color, format_name in other_specs:
        try:
            img = Image.new('RGB', size, color=color)
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"{size[0]}x{size[1]}", fill='white')

            filepath = test_dir / filename
            img.save(filepath, format_name)
            print(f"✓ 创建 {filename} ({size[0]}x{size[1]}) - {format_name}")
            created_files.append(filepath)
        except Exception as e:
            print(f"✗ 创建 {filename} 失败: {e}")

    print(f"\n创建完成! 共 {len(created_files)} 个文件")
    print("\n文件列表:")
    for f in created_files:
        size = f.stat().st_size
        print(f"  {f.name} ({size} bytes)")

    return test_dir

def main():
    """主函数"""
    try:
        test_dir = create_test_images()
        print(f"\n测试目录: {test_dir.absolute()}")
        print("现在可以运行 organizef 来测试图片分类功能")

    except Exception as e:
        print(f"创建测试图片时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()