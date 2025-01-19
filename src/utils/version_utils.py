import os
import re
import subprocess
from datetime import datetime, timedelta
from loguru import logger
from .platform_manager import platform_manager
from utils.i18n_manager import i18n_manager
import sys

# 初始化i18n管理器
_ = i18n_manager.get_text

class VersionCache:
    """版本信息缓存"""
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)  # 缓存有效期5分钟
        
    def get(self, key):
        """获取缓存的版本信息"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < self.cache_duration:
                return entry['value']
            else:
                del self.cache[key]
        return None
        
    def set(self, key, value):
        """设置缓存"""
        self.cache[key] = {
            'value': value,
            'timestamp': datetime.now()
        }
        
    def clear(self):
        """清除缓存"""
        self.cache.clear()

class VersionUtils:
    """版本工具类"""
    
    def __init__(self):
        self.version_cache = VersionCache()
        
    def get_jdk_version(self, jdk_path, use_cache=True):
        """获取JDK版本信息"""
        try:
            if use_cache:
                cached_version = self.version_cache.get(jdk_path)
                if cached_version:
                    return cached_version
                    
            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, 'bin', java_executable)
            java_path = platform_manager.format_path(java_path)
            
            if not os.path.exists(java_path):
                return None
                
            result = self._run_java_version_cmd(java_path)
            if result and result.stderr:
                version = self._extract_version(result.stderr)
                if version and use_cache:
                    self.version_cache.set(jdk_path, version)
                return version
            return None
        except Exception as e:
            logger.error(f"{_('log.error.get_version_failed')}: {str(e)}")
            return None
            
    def get_vendor_info(self, jdk_path, use_cache=True):
        """获取JDK供应商信息"""
        try:
            cache_key = f"{jdk_path}_vendor"
            if use_cache:
                cached_info = self.version_cache.get(cache_key)
                if cached_info:
                    return cached_info
                    
            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, 'bin', java_executable)
            java_path = platform_manager.format_path(java_path)
            
            if not os.path.exists(java_path):
                return None
                
            result = self._run_java_version_cmd(java_path)
            if result and result.stderr:
                version_info = result.stderr.lower()
                vendor_info = {
                    'vendor': self._detect_vendor(version_info),
                    'version': self._extract_version(version_info),
                    'build': self._extract_build(version_info)
                }
                
                if use_cache:
                    self.version_cache.set(cache_key, vendor_info)
                return vendor_info
            return None
        except Exception as e:
            logger.error(f"{_('log.error.get_vendor_info_failed')}: {str(e)}")
            return None

    def get_system_java_version(self):
        """获取系统Java版本"""
        try:
            # 首先检查 JAVA_HOME
            java_home = os.environ.get('JAVA_HOME')
            if java_home:
                logger.debug(f"Checking JAVA_HOME: {java_home}")
                java_executable = platform_manager.get_java_executable()
                java_path = os.path.join(java_home, 'bin', java_executable)
                if os.path.exists(java_path):
                    result = self._run_java_version_cmd(java_path)
                    if result and result.stderr:
                        return result.stderr.strip()

            # 如果 JAVA_HOME 无效或未设置，直接尝试 java -version
            logger.debug("JAVA_HOME not found or invalid, trying system java")
            result = self._run_java_version_cmd('java')
            if result and result.stderr:
                return result.stderr.strip()

            logger.debug("No Java installation found")
            return _("local.system_version.not_installed")
        except Exception as e:
            logger.error(f"{_('log.error.get_system_version_failed')}: {str(e)}")
            return _("local.system_version.unknown")

    @staticmethod
    def run_process(cmd, **kwargs):
        """通用的进程执行方法"""
        try:
            # 基础进程参数
            process_args = {
                'text': False,  # 改为 False 以获取原始字节
                'timeout': kwargs.pop('timeout', 5)
            }

            # Windows 特定设置
            if platform_manager.is_windows:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                process_args.update({
                    'startupinfo': startupinfo,
                    'creationflags': subprocess.CREATE_NO_WINDOW,
                    'capture_output': True
                })
            else:
                process_args.update({
                    'stdout': subprocess.DEVNULL,
                    'stderr': subprocess.PIPE,
                    'stdin': subprocess.DEVNULL
                })

            # 合并剩余的自定义参数
            process_args.update(kwargs)

            # 执行命令
            result = subprocess.run(cmd, **process_args)
            
            # 处理输出编码
            if result.stderr:
                try:
                    # 首先尝试 UTF-8
                    stderr_text = result.stderr.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        # Windows 中文系统通常使用 GBK
                        if platform_manager.is_windows:
                            stderr_text = result.stderr.decode('gbk')
                        else:
                            # 其他编码尝试
                            stderr_text = result.stderr.decode('latin1')
                    except UnicodeDecodeError:
                        # 如果都失败了，使用 errors='replace' 来替换无法解码的字符
                        stderr_text = result.stderr.decode('utf-8', errors='replace')
                
                # 创建一个新的 CompletedProcess 对象，包含解码后的文本
                return subprocess.CompletedProcess(
                    args=result.args,
                    returncode=result.returncode,
                    stdout=None,
                    stderr=stderr_text
                )
            
            return result
            
        except subprocess.TimeoutExpired:
            logger.error(f"{_('log.error.process_timeout')}: {' '.join(cmd)}")
            return None
        except Exception as e:
            logger.error(f"{_('log.error.process_failed')}: {str(e)}")
            return None

    def _run_java_version_cmd(self, java_cmd):
        """运行java -version命令"""
        try:
            # 如果是 'java' 命令，尝试在 PATH 中查找完整路径
            if java_cmd == 'java':
                if platform_manager.is_windows:
                    # Windows 下查找 java.exe
                    paths = os.environ.get('PATH', '').split(os.pathsep)
                    for path in paths:
                        java_exe = os.path.join(path, 'java.exe')
                        if os.path.exists(java_exe):
                            java_cmd = java_exe
                            break
                else:
                    # Unix 系统下查找 java
                    try:
                        java_cmd = subprocess.check_output(['which', 'java'], text=True).strip()
                    except:
                        pass

            # 如果找不到 java 命令，返回特定错误
            if java_cmd == 'java' and not os.path.exists(java_cmd):
                return None

            # 格式化命令路径
            if not java_cmd == 'java':
                java_cmd = platform_manager.format_path(java_cmd)

            return self.run_process([java_cmd, '-version'])
        except Exception as e:
            logger.error(f"{_('log.error.run_java_cmd_failed')}: {str(e)}")
            return None

    def get_version_type(self, version):
        """获取版本类型（LTS、Current等）"""
        try:
            major_version = int(re.findall(r'\d+', version)[0])
            if major_version in [8, 11, 17, 21]:
                return _("local.version.type.lts")
            elif major_version >= 21:
                return _("local.version.type.latest")
            elif major_version >= 17:
                return _("local.version.type.interim")
            elif major_version >= 11:
                return _("local.version.type.old")
            else:
                return _("local.version.type.legacy")
        except:
            return _("local.version.type.unknown")

    def get_version_color(self, version_type):
        """获取版本类型对应的颜色"""
        colors = {
            _("local.version.type.lts"): "#17a2b8",      # 蓝绿色
            _("local.version.type.latest"): "#28a745",   # 绿色
            _("local.version.type.interim"): "#ffc107",  # 黄色
            _("local.version.type.old"): "#6c757d",      # 灰色
            _("local.version.type.legacy"): "#dc3545",   # 红色
            _("local.version.type.unknown"): "#6c757d"   # 灰色
        }
        return colors.get(version_type, "#6c757d")

    def _detect_vendor(self, version_info):
        """检测JDK供应商"""
        if 'openjdk' in version_info:
            if 'corretto' in version_info:
                return "Corretto"
            elif 'temurin' in version_info or 'adoptium' in version_info:
                return "Temurin"
            elif 'zulu' in version_info:
                return "Zulu"
            elif 'microsoft' in version_info:
                return "Microsoft"
            else:
                return "OpenJDK"
        elif 'java(tm)' in version_info or 'oracle' in version_info:
            return "Oracle"
        elif 'graalvm' in version_info:
            return "GraalVM"
        elif 'semeru' in version_info:
            return "Semeru"
        return _("local.vendor.unknown")
        
    def _extract_version(self, version_info):
        """提取版本号"""
        match = re.search(r'version "([^"]+)"', version_info)
        return match.group(1) if match else None
        
    def _extract_build(self, version_info):
        """提取构建号"""
        match = re.search(r'build ([^\s]+)', version_info)
        return match.group(1) if match else None
        
    def compare_versions(self, version1, version2):
        """比较两个版本号的大小"""
        try:
            v1_parts = [int(x) for x in re.findall(r'\d+', version1)]
            v2_parts = [int(x) for x in re.findall(r'\d+', version2)]
            
            # 补齐位数
            while len(v1_parts) < len(v2_parts):
                v1_parts.append(0)
            while len(v2_parts) < len(v1_parts):
                v2_parts.append(0)
                
            for i in range(len(v1_parts)):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            return 0
        except Exception:
            return 0

    def check_jdk_validity(self, jdk_path):
        """检查JDK路径是否有效"""
        try:
            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, 'bin', java_executable)
            java_path = platform_manager.format_path(java_path)
            
            if not os.path.exists(java_path):
                return False, _("local.error.invalid_jdk_path")
                
            result = self._run_java_version_cmd(java_path)
            if result and result.stderr and self._extract_version(result.stderr):
                return True, None
            return False, _("local.error.invalid_jdk_version")
        except Exception as e:
            logger.error(f"{_('log.error.check_jdk_failed')}: {str(e)}")
            return False, str(e)

# 创建全局版本工具实例
version_utils = VersionUtils() 