import os
import json
from loguru import logger

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file='config/settings.json'):
        self.config_file = config_file
        self.config = {}  # 初始化为空字典
        self.load()  # 加载配置
        
    def load(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            return self.config
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            self.config = {}
            return self.config

    def save(self):
        """保存配置"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 保存配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
                f.flush()  # 确保写入磁盘
                os.fsync(f.fileno())  # 强制同步到磁盘
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            raise Exception(f"保存配置失败: {str(e)}")

    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        self.save()

    def add_mapped_jdk(self, jdk_info):
        """添加映射的JDK"""
        mapped_jdks = self.get('mapped_jdks', [])
        
        # 检查是否已存在相同路径的JDK
        for existing_jdk in mapped_jdks:
            try:
                if os.path.samefile(existing_jdk['path'], jdk_info['path']):
                    return False
            except Exception:
                continue
                
        # 检查是否已存在相同版本的JDK
        for existing_jdk in mapped_jdks:
            if existing_jdk['version'] == jdk_info['version'] and existing_jdk['path'] == jdk_info['path']:
                return False
                
        mapped_jdks.append(jdk_info)
        self.set('mapped_jdks', mapped_jdks)
        return True

    def add_downloaded_jdk(self, jdk_info):
        """添加下载的JDK"""
        try:
            # 重新加载配置以确保获取最新数据
            self.load()
            
            downloaded_jdks = self.get('downloaded_jdks', [])
            
            # 检查是否已存在相同路径的JDK
            for existing_jdk in downloaded_jdks:
                if existing_jdk['path'] == jdk_info['path']:
                    # 更新现有JDK的信息
                    existing_jdk.update(jdk_info)
                    self.set('downloaded_jdks', downloaded_jdks)
                    logger.debug(f"更新已存在的JDK信息: {jdk_info}")
                    return True
            
            # 如果不存在，添加新的JDK
            jdk_info['type'] = 'downloaded'  # 确保设置了类型
            downloaded_jdks.append(jdk_info)
            self.set('downloaded_jdks', downloaded_jdks)
            logger.debug(f"成功添加下载的JDK: {jdk_info}")
            return True
            
        except Exception as e:
            logger.error(f"添加下载的JDK失败: {str(e)}")
            raise Exception(f"添加下载的JDK失败: {str(e)}")

    def remove_jdk(self, jdk_path, is_mapped=True):
        """移除JDK记录"""
        key = 'mapped_jdks' if is_mapped else 'downloaded_jdks'
        jdks = self.get(key, [])
        jdks = [jdk for jdk in jdks if jdk['path'] != jdk_path]
        return self.set(key, jdks)

    def get_all_jdks(self):
        """获取所有JDK列表"""
        try:
            # 重新加载配置以确保获取最新数据
            self.load()
            
            # 获取所有类型的JDK
            jdks = []
            
            # 获取映射的JDK
            mapped_jdks = self.get('mapped_jdks', [])
            for jdk in mapped_jdks:
                if not jdk.get('type'):
                    jdk['type'] = 'mapped'
                jdks.append(jdk)
            
            # 获取下载的JDK
            downloaded_jdks = self.get('downloaded_jdks', [])
            for jdk in downloaded_jdks:
                if not jdk.get('type'):
                    jdk['type'] = 'downloaded'
                jdks.append(jdk)
            
            # 获取其他JDK（如果有）
            other_jdks = self.get('jdks', [])
            jdks.extend(other_jdks)
            
            # 过滤掉重复的JDK（基于路径）
            unique_jdks = []
            paths = set()
            for jdk in jdks:
                if jdk['path'] not in paths:
                    paths.add(jdk['path'])
                    unique_jdks.append(jdk)
            
            return unique_jdks
        except Exception as e:
            logger.error(f"获取JDK列表失败: {str(e)}")
            return []

    def get_current_jdk(self):
        """获取当前使用的JDK信息"""
        junction_path = self.get('junction_path')
        if not junction_path or not os.path.exists(junction_path):
            return None
            
        try:
            # 获取软链接指向的实际路径
            real_path = os.path.realpath(junction_path)
            
            # 在所有JDK中查找匹配的
            for jdk in self.get_all_jdks():
                try:
                    if os.path.samefile(jdk['path'], real_path):
                        return jdk
                except Exception:
                    continue
                    
            return None
        except Exception as e:
            logger.error(f"获取当前JDK失败: {str(e)}")
            return None 

    def set_auto_start(self, enabled):
        """设置自启动状态"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "JDK Version Manager"
            exe_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'jvman.exe'))
            
            # 打开注册表项
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            if enabled:
                # 添加自启动项
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    # 删除自启动项
                    winreg.DeleteValue(key, app_name)
                except WindowsError:
                    pass  # 如果键不存在，忽略错误
            
            winreg.CloseKey(key)
            self.set('auto_start', enabled)
            return True
        except Exception as e:
            logger.error(f"设置自启动失败: {str(e)}")
            return False

    def get_auto_start_status(self):
        """获取自启动状态"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "JDK Version Manager"
            
            # 打开注册表项
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            
            try:
                winreg.QueryValueEx(key, app_name)
                is_auto_start = True
            except WindowsError:
                is_auto_start = False
            
            winreg.CloseKey(key)
            return is_auto_start
        except Exception as e:
            logger.error(f"获取自启动状态失败: {str(e)}")
            return False 

    def add_jdk(self, jdk_info):
        """添加JDK到配置"""
        try:
            if jdk_info.get('type') == 'mapped':
                return self.add_mapped_jdk(jdk_info)
            elif jdk_info.get('type') == 'downloaded':
                return self.add_downloaded_jdk(jdk_info)
            else:
                # 获取当前的JDK列表
                jdks = self.get('jdks', [])
                
                # 检查是否已存在相同路径的JDK
                for jdk in jdks:
                    if jdk['path'] == jdk_info['path']:
                        # 如果存在，更新信息
                        jdk.update(jdk_info)
                        self.save()
                        return True
                
                # 如果不存在，添加到列表
                jdks.append(jdk_info)
                self.set('jdks', jdks)
                return True
            
        except Exception as e:
            logger.error(f"添加JDK到配置失败: {str(e)}")
            raise Exception(f"添加JDK到配置失败: {str(e)}")

    def remove_jdk(self, jdk_path, is_mapped=False):
        """从配置中移除JDK"""
        try:
            if is_mapped:
                mapped_jdks = self.get('mapped_jdks', [])
                self.set('mapped_jdks', [jdk for jdk in mapped_jdks if jdk['path'] != jdk_path])
            else:
                downloaded_jdks = self.get('downloaded_jdks', [])
                self.set('downloaded_jdks', [jdk for jdk in downloaded_jdks if jdk['path'] != jdk_path])
                
                # 同时也从 jdks 列表中移除
                jdks = self.get('jdks', [])
                self.set('jdks', [jdk for jdk in jdks if jdk['path'] != jdk_path])
        except Exception as e:
            logger.error(f"从配置中移除JDK失败: {str(e)}")
            raise Exception(f"从配置中移除JDK失败: {str(e)}") 