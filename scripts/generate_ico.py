import os
from PIL import Image, ImageEnhance
import sys
import shutil
import subprocess

def generate_windows_ico():
    """生成Windows ICO图标"""
    source_png = os.path.join('resources', 'icons', 'app_large.png')
    target_ico = os.path.join('resources', 'icons', 'app.ico')
    
    if not os.path.exists(source_png):
        print(f"Error: Source PNG file not found at {source_png}")
        return
        
    sizes = [256, 128, 64, 48, 32, 16]
    
    try:
        img = Image.open(source_png)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        images = []
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            if size <= 32:
                enhancer = ImageEnhance.Contrast(resized)
                resized = enhancer.enhance(1.1)
                enhancer = ImageEnhance.Sharpness(resized)
                resized = enhancer.enhance(1.2)
            images.append(resized)
        
        # 保存ICO文件
        images[0].save(
            target_ico,
            format='ICO',
            sizes=[(size, size) for size in sizes],
            append_images=images[1:],
            optimize=True,
            quality=100
        )
        print(f"Generated Windows ICO: {target_ico}")
        
    except Exception as e:
        print(f"Error generating ICO file: {e}")

def generate_macos_icns():
    """生成macOS ICNS图标"""
    source_png = os.path.join('resources', 'icons', 'app_large.png')
    target_icns = os.path.join('resources', 'icons', 'app.icns')
    
    if not os.path.exists(source_png):
        print(f"错误：源PNG文件不存在: {source_png}")
        return False
        
    try:
        img = Image.open(source_png)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        # macOS图标尺寸
        sizes = [1024, 512, 256, 128, 64, 32, 16]
        iconset_dir = os.path.join('resources', 'icons', 'app.iconset')
        os.makedirs(iconset_dir, exist_ok=True)
        
        # 生成不同尺寸的图标
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            # 普通分辨率
            resized.save(os.path.join(iconset_dir, f'icon_{size}x{size}.png'))
            # 高分辨率（@2x）
            if size * 2 <= 1024:
                resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                resized_2x.save(os.path.join(iconset_dir, f'icon_{size}x{size}@2x.png'))
        
        # 使用系统命令生成icns文件
        try:
            result = subprocess.run(
                ['iconutil', '-c', 'icns', iconset_dir, '-o', target_icns],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"已生成macOS ICNS: {target_icns}")
                return True
            else:
                print("生成ICNS文件失败。请确保在macOS上运行并已安装iconutil。")
                if result.stderr:
                    print(f"错误信息: {result.stderr}")
                return False
        except FileNotFoundError:
            print("错误：找不到iconutil命令。请确保在macOS上运行。")
            return False
        except Exception as e:
            print(f"执行iconutil命令时出错: {str(e)}")
            return False
            
    except Exception as e:
        print(f"生成ICNS文件时出错: {str(e)}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)
            print("已清理临时文件")

def generate_app_icons():
    """生成所有平台的图标"""
    source_png = os.path.join('resources', 'icons', 'app_large.png')
    
    # 检查源文件是否存在
    if not os.path.exists(source_png):
        print(f"错误：源PNG文件不存在: {source_png}")
        print("请确保在 resources/icons 目录下存在 app_large.png 文件")
        print("这个文件应该是一个高分辨率的PNG图像（建议至少1024x1024像素）")
        return
    
    try:
        # 检查图像尺寸和格式
        img = Image.open(source_png)
        if img.size[0] < 1024 or img.size[1] < 1024:
            print(f"警告：源图像尺寸较小 ({img.size[0]}x{img.size[1]})，建议使用至少1024x1024像素的图像")
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 生成PNG图标（所有平台通用）
        main_icon = img.resize((256, 256), Image.Resampling.LANCZOS)
        main_icon_path = os.path.join('resources', 'icons', 'app_256.png')
        main_icon.save(main_icon_path, 'PNG', optimize=True, quality=100)
        print(f"已生成主PNG图标: {main_icon_path}")
        
        # 生成Windows ICO
        print("\n正在生成Windows ICO图标...")
        generate_windows_ico()
        
        # 在macOS上生成ICNS
        if sys.platform == 'darwin':
            print("\n正在生成macOS ICNS图标...")
            if generate_macos_icns():
                print("ICNS图标生成成功！")
            else:
                print("ICNS图标生成失败，请检查错误信息")
        
        print("\n图标生成完成！")
        print("Windows: 使用 app.ico")
        print("macOS: 使用 app.icns")
        print("Linux: 使用 app_256.png")
        
    except Exception as e:
        print(f"生成图标时发生错误: {str(e)}")
        return

if __name__ == '__main__':
    generate_app_icons() 