import os
import json
import requests
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class VersionUpdateThread(QThread):
    """版本更新线程"""
    def __init__(self, downloader):
        super().__init__()
        self.downloader = downloader
        
    def run(self):
        """运行线程"""
        try:
            # Oracle JDK
            oracle_versions = self.downloader._get_oracle_versions()
            if oracle_versions:
                self.downloader.api_config['Oracle JDK']['versions'] = oracle_versions
            
            # OpenJDK
            openjdk_versions = self.downloader._get_openjdk_versions()
            if openjdk_versions:
                self.downloader.api_config['OpenJDK']['versions'] = openjdk_versions
            
            # Adoptium
            adoptium_versions = self.downloader._get_adoptium_versions()
            if adoptium_versions:
                self.downloader.api_config['Eclipse Temurin (Adoptium)']['versions'] = adoptium_versions
            
            # Corretto
            corretto_versions = self.downloader._get_corretto_versions()
            if corretto_versions:
                self.downloader.api_config['Amazon Corretto']['versions'] = corretto_versions
            
            # Zulu
            zulu_versions = self.downloader._get_zulu_versions()
            if zulu_versions:
                self.downloader.api_config['Azul Zulu']['versions'] = zulu_versions
                
        except Exception as e:
            logger.error(f"更新版本列表失败: {str(e)}")

class JDKDownloader(QObject):
    """JDK下载管理器"""
    
    # 定义信号
    download_progress = pyqtSignal(int, int)  # 当前大小，总大小
    download_complete = pyqtSignal(bool, str)  # 成功标志，消息

    def __init__(self):
        """初始化下载器"""
        super().__init__()
        
        # 初始化版本更新线程
        self.update_thread = None
        
        # 基础版本列表（作为备选）
        self.base_versions = {
            'Oracle JDK': ['23', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
            'OpenJDK': ['23', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
            'Eclipse Temurin (Adoptium)': ['23', '21', '17', '11', '8'],
            'Amazon Corretto': ['23', '21', '17', '11', '8'],
            'Azul Zulu': ['23', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8']
        }
        
        # 初始化版本信息缓存
        self.version_info_cache = {}
        
        # 初始化 API 配置
        self._init_api_config()
        
    def _init_api_config(self):
        """初始化 API 配置"""
        self.api_config = {
            'Oracle JDK': {
                'api_url': 'https://www.oracle.com/java/technologies/downloads/archive/',
                'versions': self.base_versions['Oracle JDK'],
                'auth_required': True
            },
            'OpenJDK': {
                'api_url': 'https://jdk.java.net/archive/',
                'versions': self.base_versions['OpenJDK'],
                'auth_required': False
            },
            'Eclipse Temurin (Adoptium)': {
                'api_url': 'https://api.adoptium.net/v3/assets/latest/{version}/hotspot',
                'versions': self.base_versions['Eclipse Temurin (Adoptium)'],
                'auth_required': False
            },
            'Amazon Corretto': {
                'api_url': 'https://corretto.aws/downloads/latest/',
                'versions': self.base_versions['Amazon Corretto'],
                'auth_required': False
            },
            'Azul Zulu': {
                'api_url': 'https://api.azul.com/zulu/download/community/v1.0/',
                'versions': self.base_versions['Azul Zulu'],
                'auth_required': False
            }
        }
        
        # 异步更新版本列表
        self._async_update_versions()
        
    def _async_update_versions(self):
        """异步更新版本列表"""
        try:
            # 如果存在旧的更新线程，先停止它
            if self.update_thread and self.update_thread.isRunning():
                self.update_thread.quit()
                self.update_thread.wait()
            
            # 创建并启动新的更新线程
            self.update_thread = VersionUpdateThread(self)
            self.update_thread.start()
        except Exception as e:
            logger.error(f"异步更新版本列表失败: {str(e)}")
            
    def __del__(self):
        """析构函数"""
        try:
            # 确保线程正确退出
            if self.update_thread and self.update_thread.isRunning():
                self.update_thread.quit()
                self.update_thread.wait()
        except Exception as e:
            logger.error(f"清理线程失败: {str(e)}")

    def get_available_versions(self, vendor):
        """获取指定发行版可用的JDK版本列表"""
        try:
            if vendor in self.api_config:
                return self.api_config[vendor]['versions']
            return []
        except Exception as e:
            logger.error(f"获取JDK版本列表失败: {str(e)}")
            # 如果出错，返回基础版本列表
            return self.base_versions.get(vendor, [])

    def get_version_info(self, vendor, version):
        """获取版本详细信息"""
        cache_key = f"{vendor}-{version}"
        if cache_key in self.version_info_cache:
            return self.version_info_cache[cache_key]
            
        try:
            info = self._fetch_version_info(vendor, version)
            self.version_info_cache[cache_key] = info
            return info
        except Exception as e:
            logger.error(f"获取版本信息失败: {str(e)}")
            return None

    def _fetch_version_info(self, vendor, version):
        """从API获取版本信息"""
        # JDK版本特性映射
        version_features = {
            '21': {
                'release_date': '2023-09-19',
                'version_detail': '21.0.2',
                'features': [
                    '字符串模板（预览）',
                    '序列化集合（预览）',
                    '虚拟线程（正式版）',
                    '记录模式（正式版）',
                    '分代 ZGC',
                    '外部函数和内存 API（预览）'
                ],
                'lts': True
            },
            '17': {
                'release_date': '2021-09-14',
                'version_detail': '17.0.10',
                'features': [
                    '密封类（正式版）',
                    '模式匹配 Switch（预览）',
                    '增强的伪随机数生成器',
                    'macOS AArch64 支持',
                    '新的 macOS 渲染管线'
                ],
                'lts': True
            },
            '11': {
                'release_date': '2018-09-25',
                'version_detail': '11.0.22',
                'features': [
                    'HTTP Client（标准）',
                    'Lambda 参数的局部变量语法',
                    '启动单文件源代码程序',
                    'Unicode 10',
                    '动态类文件常量',
                    'Epsilon GC'
                ],
                'lts': True
            },
            '8': {
                'release_date': '2014-03-18',
                'version_detail': '8u402',
                'features': [
                    'Lambda 表达式',
                    '方法引用',
                    '默认方法',
                    'Stream API',
                    '新的日期时间 API',
                    'Optional 类'
                ],
                'lts': True
            }
        }

        base_info = {
            'version': version,
            'version_detail': version_features.get(version, {}).get('version_detail', version),
            'release_date': version_features.get(version, {}).get('release_date', '获取中...'),
            'jvm_impl': 'HotSpot',
            'arch': 'x86_64',
            'os': 'Windows',
            'features': [],
            'release_notes': '',
            'support_policy': '',
            'version_features': version_features.get(version, {}).get('features', []),
            'is_lts': version_features.get(version, {}).get('lts', False)
        }

        try:
            if vendor == 'Eclipse Temurin (Adoptium)':
                url = self.api_config[vendor]['api_url'].format(version=version)
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        release = data[0]
                        base_info.update({
                            'release_date': release.get('release_name', base_info['release_date']),
                            'features': [
                                '✓ Eclipse Adoptium 质量认证',
                                '✓ 企业级生产就绪',
                                '✓ TCK 合规认证',
                                '✓ AQAvit 质量验证',
                                '✓ 持续的安全更新'
                            ],
                            'support_policy': '社区支持 + Eclipse Foundation 支持',
                            'release_notes': '基于 OpenJDK，由 Eclipse Foundation 维护的高质量构建版本'
                        })
            
            elif vendor == 'Oracle JDK':
                base_info.update({
                    'features': [
                        '✓ 商业特性支持',
                        '✓ GraalVM 企业版集成',
                        '✓ 高级监控和诊断工具',
                        '✓ 飞行记录器(JFR)',
                        '✓ 任务控制(JMC)',
                        '✓ 应用程序类数据共享'
                    ],
                    'support_policy': '商业支持 + 长期技术支持(LTS)',
                    'release_notes': '官方JDK发行版，提供全面的商业支持和企业特性'
                })
            
            elif vendor == 'OpenJDK':
                base_info.update({
                    'features': [
                        '✓ 开源参考实现',
                        '✓ 社区驱动开发',
                        '✓ 标准Java特性',
                        '✓ 快速迭代更新',
                        '✓ 透明的开发程'
                    ],
                    'support_policy': '社区支持',
                    'release_notes': 'Java SE 平台的开源参考实现，由 OpenJDK 社区维护'
                })
            
            elif vendor == 'Amazon Corretto':
                base_info.update({
                    'features': [
                        '✓ AWS 云平台优化',
                        '✓ 长期安全补丁',
                        '✓ 企业级性能调优',
                        '✓ 亚马逊生产环境验证',
                        '✓ 跨平台支持'
                    ],
                    'support_policy': 'Amazon 免费长期支持(LTS)',
                    'release_notes': '由亚马逊开发和维护的OpenJDK发行版，针对AWS优化'
                })
            
            elif vendor == 'Azul Zulu':
                base_info.update({
                    'features': [
                        '✓ 完整 TCK 认证',
                        '✓ 性能优化版本',
                        '✓ 可构建定制版本',
                        '✓ 云原生支持',
                        '✓ 容器优化'
                    ],
                    'support_policy': '社区版免费 + 商业版付费支持',
                    'release_notes': '由Azul Systems提供的OpenJDK构建版本，提供企业级支持'
                })

            # 获取下载链接
            download_link = self._get_download_link(vendor, version)

            # 构建格式化的版本信息
            info_text = f"""<style>
                .title {{ 
                    color: #1a73e8; 
                    font-weight: bold; 
                    font-size: 14px; 
                    margin-bottom: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }}
                .version-info {{
                    display: flex;
                    align-items: center;
                }}
                .vendor {{
                    color: #666666;
                    font-size: 12px;
                    font-weight: normal;
                    margin-left: 10px;
                    padding-left: 10px;
                    border-left: 2px solid #E0E0E0;
                }}
                .section {{ margin: 8px 0; }}
                .label {{ color: #666666; font-weight: bold; }}
                .value {{ color: #2C3E50; }}
                .feature {{ color: #2C3E50; margin: 3px 0; }}
                .note {{ color: #666666; font-style: italic; margin-top: 8px; }}
                .badge {{ 
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-left: 8px;
                    background-color: {'#1a73e8' if base_info['is_lts'] else '#34A853'};
                    color: white;
                }}
                .version-feature {{
                    color: #1a73e8;
                    margin: 3px 0;
                    padding-left: 20px;
                    position: relative;
                }}
                .version-feature::before {{
                    content: "•";
                    position: absolute;
                    left: 8px;
                    color: #1a73e8;
                }}
                .divider {{
                    border-top: 1px solid #E0E0E0;
                    margin: 12px 0;
                }}
                .download-link {{
                    color: #1a73e8;
                    text-decoration: none;
                    margin-top: 10px;
                    display: block;
                }}
                .download-link:hover {{
                    text-decoration: underline;
                }}
            </style>
            <div class='title'>
                <div class='version-info'>
                    JDK {base_info['version']} ({base_info['version_detail']})
                    <span class='vendor'>{vendor}</span>
                </div>
                <span class='badge'>{('LTS' if base_info['is_lts'] else '短期支持')}</span>
            </div>
            
            <div class='section'>
                <span class='label'>发布时间:</span>
                <span class='value'> {base_info['release_date']}</span>
            </div>
            
            <div class='section'>
                <span class='label'>运行环境:</span>
                <span class='value'> {base_info['jvm_impl']} VM, {base_info['arch']}, {base_info['os']}</span>
            </div>
            
            <div class='section'>
                <div class='label'>发行版特性:</div>
                {"".join(f"<div class='feature'>{feature}</div>" for feature in base_info['features'])}
            </div>
            
            <div class='divider'></div>
            
            <div class='section'>
                <div class='label'>版本新特性:</div>
                {"".join(f"<div class='version-feature'>{feature}</div>" for feature in base_info['version_features'])}
            </div>
            
            <div class='divider'></div>
            
            <div class='section'>
                <span class='label'>支持策略:</span>
                <span class='value'> {base_info['support_policy']}</span>
            </div>
            
            <div class='note'>{base_info['release_notes']}</div>
            
            {f'<a href="{download_link}" class="download-link" target="_blank">➜ 点击前往官方下载页面</a>' if download_link else ''}"""

            return info_text
        except Exception as e:
            logger.error(f"获取版本信息失败: {str(e)}")
            return "暂无版本信息"

    def _get_download_link(self, vendor, version):
        """获取官方下载链接"""
        try:
            if vendor == 'Oracle JDK':
                return 'https://www.oracle.com/java/technologies/downloads/'
            
            elif vendor == 'OpenJDK':
                return 'https://jdk.java.net/'
            
            elif vendor == 'Eclipse Temurin (Adoptium)':
                return 'https://adoptium.net/temurin/releases/'
            
            elif vendor == 'Amazon Corretto':
                return 'https://aws.amazon.com/corretto/'
            
            elif vendor == 'Azul Zulu':
                return 'https://www.azul.com/downloads/'
            
            return None
            
        except Exception as e:
            logger.error(f"获取下载链接失败: {str(e)}")
            return None

    def download_jdk(self, vendor, version, target_dir, progress_callback=None):
        """下载指定版本的JDK"""
        try:
            # 获取下载链接
            download_url = self._get_download_url(vendor, version)
            if not download_url:
                if vendor == 'Oracle JDK':
                    return False, "需要登录 Oracle 账号才能下载，请前往官网手动下载"
                else:
                    return False, "无法获取下载链接，请尝试手动下载"

            # 创建目标目录
            os.makedirs(target_dir, exist_ok=True)
            file_name = os.path.join(target_dir, f"jdk-{version}.zip")

            # 下载文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            try:
                # 先检查链接是否可用
                head_response = requests.head(download_url, headers=headers, timeout=10)
                if head_response.status_code != 200:
                    return False, f"下载链接无效，HTTP状态码: {head_response.status_code}"

                # 开始下载
                response = requests.get(download_url, headers=headers, stream=True, timeout=30)
                if response.status_code != 200:
                    return False, f"下载失败，HTTP状态码: {response.status_code}"

                total_size = int(response.headers.get('content-length', 0))
                if total_size == 0:
                    return False, "无法获取文件大小信息"

                block_size = 1024 * 1024  # 1 MB
                downloaded_size = 0

                with open(file_name, 'wb') as f:
                    for data in response.iter_content(block_size):
                        downloaded_size += len(data)
                        f.write(data)
                        # 发送进度回调
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)

                # 验证下载的文件大小
                if os.path.getsize(file_name) != total_size:
                    os.remove(file_name)
                    return False, "下载的文件不完整，请重试"

                return True, "下载完成"

            except requests.Timeout:
                return False, "下载超时，请检查网络连接"
            except requests.ConnectionError:
                return False, "网络连接错误，请检查网络设置"
            except Exception as e:
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, f"下载过程中出错: {str(e)}"

        except Exception as e:
            logger.error(f"下载JDK失败: {str(e)}")
            return False, str(e)

    def _get_download_url(self, vendor, version):
        """获取下载链接"""
        try:
            if vendor == 'Eclipse Temurin (Adoptium)':
                # 使用 Adoptium API v3 获取下载链接
                url = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        binary = data[0].get('binary')
                        if binary:
                            return binary.get('package', {}).get('link')
            
            elif vendor == 'OpenJDK':
                # OpenJDK 官方下载链接
                version_map = {
                    '23': 'https://download.java.net/java/GA/jdk23/36/GPL/openjdk-23_windows-x64_bin.zip',
                    '22': 'https://download.java.net/java/GA/jdk22/4184dcf0b2d7-1/17/GPL/openjdk-22_windows-x64_bin.zip',
                    '21': 'https://download.java.net/java/GA/jdk21.0.2/f2283984656d49d69e91c558476027ac/13/GPL/openjdk-21.0.2_windows-x64_bin.zip',
                    '20': 'https://download.java.net/java/GA/jdk20.0.2/6e380f22cbe7469fa75fb448bd903d8e/9/GPL/openjdk-20.0.2_windows-x64_bin.zip',
                    '19': 'https://download.java.net/java/GA/jdk19.0.2/fdb695a9d9064ad6b064dc6df578380c/7/GPL/openjdk-19.0.2_windows-x64_bin.zip',
                    '18': 'https://download.java.net/java/GA/jdk18.0.2.1/db379da656dc47308e138f21b33976fa/1/GPL/openjdk-18.0.2.1_windows-x64_bin.zip',
                    '17': 'https://download.java.net/java/GA/jdk17.0.10/f81d6d7e987c4195b39a77500ee79993/7/GPL/openjdk-17.0.10_windows-x64_bin.zip',
                    '16': 'https://download.java.net/java/GA/jdk16.0.2/d4a915d82b4c4fbb9bde534da945d746/7/GPL/openjdk-16.0.2_windows-x64_bin.zip',
                    '15': 'https://download.java.net/java/GA/jdk15.0.2/0d1cfde4252546c6931946de8db48ee2/7/GPL/openjdk-15.0.2_windows-x64_bin.zip',
                    '14': 'https://download.java.net/java/GA/jdk14.0.2/205943a0976c4ed48cb16f1043c5c647/12/GPL/openjdk-14.0.2_windows-x64_bin.zip',
                    '13': 'https://download.java.net/java/GA/jdk13.0.2/d4173c853231432d94f001e99d882ca7/8/GPL/openjdk-13.0.2_windows-x64_bin.zip',
                    '12': 'https://download.java.net/java/GA/jdk12.0.2/e482c34c86bd4bf8b56c0b35558996b9/10/GPL/openjdk-12.0.2_windows-x64_bin.zip',
                    '11': 'https://download.java.net/java/GA/jdk11.0.22/d3fd698c6a1c4aa6ad1fca312585d76b/7/GPL/openjdk-11.0.22_windows-x64_bin.zip',
                    '10': 'https://download.java.net/java/GA/jdk10/10.0.2/19aef61b38124481863b1413dce1855f/13/openjdk-10.0.2_windows-x64_bin.tar.gz',
                    '9': 'https://download.java.net/java/GA/jdk9/9.0.4/binaries/openjdk-9.0.4_windows-x64_bin.tar.gz',
                    '8': 'https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u402-b06/OpenJDK8U-jdk_x64_windows_hotspot_8u402b06.zip'
                }
                return version_map.get(version)
            
            elif vendor == 'Amazon Corretto':
                # Amazon Corretto 最新下载链接
                if version == '21':
                    return 'https://corretto.aws/downloads/latest/amazon-corretto-21-x64-windows-jdk.zip'
                elif version == '17':
                    return 'https://corretto.aws/downloads/latest/amazon-corretto-17-x64-windows-jdk.zip'
                elif version == '11':
                    return 'https://corretto.aws/downloads/latest/amazon-corretto-11-x64-windows-jdk.zip'
                elif version == '8':
                    return 'https://corretto.aws/downloads/latest/amazon-corretto-8-x64-windows-jdk.zip'
            
            elif vendor == 'Azul Zulu':
                # Azul Zulu 最新下载链接
                if version == '21':
                    return 'https://cdn.azul.com/zulu/bin/zulu21.32.17-ca-jdk21.0.2-win_x64.zip'
                elif version == '17':
                    return 'https://cdn.azul.com/zulu/bin/zulu17.48.15-ca-jdk17.0.10-win_x64.zip'
                elif version == '11':
                    return 'https://cdn.azul.com/zulu/bin/zulu11.70.15-ca-jdk11.0.22-win_x64.zip'
                elif version == '8':
                    return 'https://cdn.azul.com/zulu/bin/zulu8.76.0.17-ca-jdk8.0.402-win_x64.zip'
            
            # 如果没有找到下载链接，返回 None
            return None
            
        except Exception as e:
            logger.error(f"获取下载链接失败: {str(e)}")
            return None

    def _get_oracle_versions(self):
        """获取Oracle JDK版本列表"""
        try:
            import requests
            response = requests.get('https://www.oracle.com/java/technologies/downloads/', timeout=5)
            if response.status_code == 200:
                import re
                # 查找最新版本号
                latest_version = re.search(r'Java (\d+)', response.text)
                if latest_version:
                    latest = latest_version.group(1)
                    versions = self.base_versions['Oracle JDK']
                    if latest not in versions:
                        versions.insert(0, latest)
                    return versions
        except Exception as e:
            logger.error(f"获取Oracle JDK版本列表失败: {str(e)}")
        return self.base_versions['Oracle JDK']

    def _get_openjdk_versions(self):
        """获取OpenJDK版本列表"""
        try:
            import requests
            response = requests.get('https://jdk.java.net/', timeout=5)
            if response.status_code == 200:
                import re
                # 查找最新版本号
                latest_version = re.search(r'JDK (\d+)', response.text)
                if latest_version:
                    latest = latest_version.group(1)
                    versions = self.base_versions['OpenJDK']
                    if latest not in versions:
                        versions.insert(0, latest)
                    return versions
        except Exception as e:
            logger.error(f"获取OpenJDK版本列表失败: {str(e)}")
        return self.base_versions['OpenJDK']

    def _get_adoptium_versions(self):
        """获取Adoptium版本列表"""
        try:
            import requests
            response = requests.get('https://api.adoptium.net/v3/info/available_releases', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'available_releases' in data:
                    latest = str(max(data['available_releases']))
                    versions = self.base_versions['Eclipse Temurin (Adoptium)']
                    if latest not in versions:
                        versions.insert(0, latest)
                    return versions
        except Exception as e:
            logger.error(f"获取Adoptium版本列表失败: {str(e)}")
        return self.base_versions['Eclipse Temurin (Adoptium)']

    def _get_corretto_versions(self):
        """获取Amazon Corretto版本列表"""
        try:
            import requests
            # 使用 GitHub API 获取 Corretto 版本信息
            response = requests.get(
                'https://api.github.com/repos/corretto/corretto-jdk/releases',
                timeout=10,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            if response.status_code == 200:
                data = response.json()
                versions = set()
                for release in data:
                    # 从 tag_name 中提取版本号
                    if isinstance(release, dict) and 'tag_name' in release:
                        import re
                        version_match = re.search(r'(\d+)\.', release['tag_name'])
                        if version_match:
                            major_version = version_match.group(1)
                            if major_version.isdigit():
                                versions.add(major_version)
                
                if versions:
                    # 转换为列表并按数字大小排序
                    versions = sorted(list(versions), key=lambda x: int(x), reverse=True)
                    # 更新基础版本列表
                    base_versions = self.base_versions['Amazon Corretto']
                    # 添加新版本到列表开头
                    for version in versions:
                        if version not in base_versions:
                            base_versions.insert(0, version)
                    return base_versions
        except Exception as e:
            logger.error(f"获取Corretto版本列表失败: {str(e)}")
        return self.base_versions['Amazon Corretto']

    def _get_zulu_versions(self):
        """获取Azul Zulu版本列表"""
        try:
            import requests
            response = requests.get('https://api.azul.com/zulu/download/community/v1.0/bundles/available', timeout=5)
            if response.status_code == 200:
                data = response.json()
                versions = set()
                for bundle in data:
                    if isinstance(bundle, dict) and 'jdk_version' in bundle:
                        major_version = bundle['jdk_version'].split('.')[0]
                        try:
                            # 确保版本号是数字
                            if major_version.isdigit():
                                versions.add(major_version)
                        except:
                            continue
                
                if versions:
                    # 转换为列表并按数字大小排序
                    versions = sorted(list(versions), key=lambda x: int(x), reverse=True)
                    # 更新基础版本列表
                    base_versions = self.base_versions['Azul Zulu']
                    # 添加新版本到列表开头
                    for version in versions:
                        if version not in base_versions:
                            base_versions.insert(0, version)
                    return base_versions
        except Exception as e:
            logger.error(f"获取Zulu版本列表失败: {str(e)}")
        return self.base_versions['Azul Zulu'] 