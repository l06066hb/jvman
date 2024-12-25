import os
import sys
import ctypes
import winreg
from loguru import logger

def check_admin_rights():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_junction(source_path, target_path):
    """创建目录联接（Junction）"""
    try:
        if os.path.exists(target_path):
            os.remove(target_path)
        
        # 使用mklink /J命令创建junction
        os.system(f'mklink /J "{target_path}" "{source_path}"')
        return True
    except Exception as e:
        logger.error(f"创建目录联接失败: {str(e)}")
        return False

def set_environment_variable(name, value):
    """设置系统环境变量"""
    try:
        # 打开系统环境变量注册表键
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'System\CurrentControlSet\Control\Session Manager\Environment',
            0,
            winreg.KEY_ALL_ACCESS
        )
        
        # 设置环境变量
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)
        
        # 通知系统环境变量已更改
        os.system('rundll32.exe user32.dll,UpdatePerUserSystemParameters')
        return True
    except Exception as e:
        logger.error(f"设置环境变量失败: {str(e)}")
        return False

def get_environment_variable(name):
    """获取系统环境变量值"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'System\CurrentControlSet\Control\Session Manager\Environment',
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return value
    except Exception as e:
        logger.error(f"获取环境变量失败: {str(e)}")
        return None

def update_path_variable(new_path):
    """更新PATH环境变量"""
    try:
        current_path = get_environment_variable('Path')
        paths = current_path.split(';')
        
        # 移除旧的JDK路径（如果存在）
        paths = [p for p in paths if 'jdk' not in p.lower()]
        
        # 添加新路径
        if new_path not in paths:
            paths.append(new_path)
        
        # 更新PATH
        new_path_value = ';'.join(filter(None, paths))
        return set_environment_variable('Path', new_path_value)
    except Exception as e:
        logger.error(f"更新PATH环境变量失败: {str(e)}")
        return False 