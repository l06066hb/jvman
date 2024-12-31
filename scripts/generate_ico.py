import os
from PIL import Image, ImageEnhance
import sys
import shutil

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
        print(f"Error: Source PNG file not found at {source_png}")
        return
        
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
        if os.system('iconutil -c icns "{}" -o "{}"'.format(iconset_dir, target_icns)) == 0:
            print(f"Generated macOS ICNS: {target_icns}")
        else:
            print("Failed to generate ICNS file. Make sure you're on macOS with iconutil installed.")
            
        # 清理临时文件
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)
            
    except Exception as e:
        print(f"Error generating ICNS file: {e}")

def generate_app_icons():
    """生成所有平台的图标"""
    source_png = os.path.join('resources', 'icons', 'app_large.png')
    
    if not os.path.exists(source_png):
        print(f"Error: Source PNG file not found at {source_png}")
        return
    
    # 生成PNG图标（所有平台通用）
    try:
        img = Image.open(source_png)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 生成256x256的主图标
        main_icon = img.resize((256, 256), Image.Resampling.LANCZOS)
        main_icon_path = os.path.join('resources', 'icons', 'app_256.png')
        main_icon.save(main_icon_path, 'PNG', optimize=True, quality=100)
        print(f"Generated main PNG icon: {main_icon_path}")
        
    except Exception as e:
        print(f"Error generating PNG icon: {e}")
        return
    
    # 生成Windows ICO
    generate_windows_ico()
    
    # 在macOS上生成ICNS
    if sys.platform == 'darwin':
        generate_macos_icns()
    
    print("\nIcon generation completed!")
    print("Windows: Use app.ico")
    print("macOS: Use app.icns")
    print("Linux: Use app_256.png")

if __name__ == '__main__':
    generate_app_icons() 