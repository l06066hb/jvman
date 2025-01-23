import ssl
import hashlib
import urllib.parse
from loguru import logger
import os
import requests

class SecurityManager:
    """安全管理器（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            from .config_manager import ConfigManager
            self.config_manager = ConfigManager()
            self.initialized = True

    def validate_url(self, url):
        """验证 URL 的安全性"""
        try:
            parsed = urllib.parse.urlparse(url)
            
            # 检查协议
            if parsed.scheme not in ['https']:
                raise ValueError("仅允许 HTTPS 协议")

            # 检查域名是否在白名单中
            allowed_domains = self.config_manager.get('update.allowed_domains', [])
            if parsed.netloc not in allowed_domains:
                raise ValueError("域名不在白名单中")

            # 检查 URL 是否包含危险字符
            dangerous_chars = ['..', ';', '&', '|', '>', '<', '$', '`', '{', '}']
            if any(char in url for char in dangerous_chars):
                raise ValueError("URL 包含危险字符")

            return True

        except Exception as e:
            logger.error(f"URL 验证失败: {str(e)}")
            return False

    def verify_file_hash(self, file_path, expected_hash, algorithm='sha256'):
        """验证文件哈希值"""
        try:
            hash_algorithms = self.config_manager.get('update.hash_algorithms', ['sha256'])
            if algorithm not in hash_algorithms:
                raise ValueError(f"不支持的哈希算法: {algorithm}")

            hash_func = getattr(hashlib, algorithm)()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)

            actual_hash = hash_func.hexdigest()
            return actual_hash == expected_hash

        except Exception as e:
            logger.error(f"文件哈希验证失败: {str(e)}")
            return False

    def create_ssl_context(self):
        """创建安全的 SSL 上下文"""
        try:
            context = ssl.create_default_context()
            if self.config_manager.get('security.ssl_verification', True):
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = True
            return context
        except Exception as e:
            logger.error(f"创建 SSL 上下文失败: {str(e)}")
            return None

    def secure_download(self, url, target_path):
        """安全地下载文件"""
        temp_file = None
        try:
            # 验证 URL
            if not self.validate_url(url):
                raise ValueError("无效的下载 URL")

            # 创建 SSL 上下文
            ssl_context = self.create_ssl_context()
            if not ssl_context:
                raise ValueError("无法创建安全的 SSL 上下文")

            # 设置请求头
            headers = {
                'User-Agent': f'jvman/{self.config_manager.get("version")}',
                'Accept': 'application/octet-stream'
            }

            # 下载文件
            response = requests.get(
                url,
                headers=headers,
                verify=True,
                stream=True
            )

            # 检查文件大小
            content_length = int(response.headers.get('content-length', 0))
            max_size = self.config_manager.get('security.max_download_size', 104857600)
            if content_length > max_size:
                raise ValueError("文件大小超过限制")

            # 检查文件类型
            file_ext = os.path.splitext(url)[1].lower()
            allowed_types = self.config_manager.get('security.allowed_file_types', ['.zip'])
            if file_ext not in allowed_types:
                raise ValueError("不支持的文件类型")

            # 下载文件
            temp_file = target_path + '.tmp'
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # 验证文件哈希（如果提供了哈希值）
            expected_hash = response.headers.get('X-Checksum-Sha256')
            if expected_hash and not self.verify_file_hash(temp_file, expected_hash):
                raise ValueError("文件哈希验证失败")

            # 移动临时文件到目标位置
            os.replace(temp_file, target_path)
            return True

        except Exception as e:
            logger.error(f"安全下载失败: {str(e)}")
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return False 