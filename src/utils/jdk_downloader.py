import os
import json
import requests
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

class JDKDownloader(QObject):
    """JDK下载管理器"""
    
    # 定义信号
    download_progress = pyqtSignal(int, int)  # 当前大小，总大小
    download_complete = pyqtSignal(bool, str)  # 成功标志，消息

    def __init__(self):
        super().__init__()
        # 各发行版的API配置
        self.api_config = {
            'Oracle JDK': {
                'api_url': 'https://www.oracle.com/java/technologies/downloads/archive/',
                'versions': ['21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
                'auth_required': True
            },
            'OpenJDK': {
                'api_url': 'https://jdk.java.net/archive/',
                'versions': ['21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
                'auth_required': False
            },
            'Eclipse Temurin (Adoptium)': {
                'api_url': 'https://api.adoptium.net/v3/assets/latest/{version}/hotspot',
                'versions': ['21', '17', '11', '8'],
                'auth_required': False
            },
            'Amazon Corretto': {
                'api_url': 'https://corretto.aws/downloads/latest/',
                'versions': ['21', '17', '11', '8'],
                'auth_required': False
            },
            'Azul Zulu': {
                'api_url': 'https://api.azul.com/zulu/download/community/v1.0/',
                'versions': ['21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
                'auth_required': False
            }
        }
        
        # 版本信息缓存
        self.version_info_cache = {}
        
    def get_available_versions(self, vendor):
        """获取指定发行版可用的JDK版本列表"""
        try:
            if vendor in self.api_config:
                return self.api_config[vendor]['versions']
            return []
        except Exception as e:
            logger.error(f"获取JDK版本列表失败: {str(e)}")
            return []

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
            '20': {
                'release_date': '2023-03-21',
                'features': [
                    '作用域值（预览）',
                    '记录模式（第四次预览）',
                    '虚拟线程（第二次预览）',
                    '结构化并发（预览）'
                ],
                'lts': False
            },
            '17': {
                'release_date': '2021-09-14',
                'features': [
                    '密封类（正式版���',
                    '模式匹配 Switch（预览）',
                    '增强的伪随机数生成器',
                    'macOS AArch64 支持',
                    '新的 macOS 渲染管线'
                ],
                'lts': True
            },
            '11': {
                'release_date': '2018-09-25',
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
                        '✓ 透明的开发过程'
                    ],
                    'support_policy': '社区支持',
                    'release_notes': 'Java SE 平台的开源参考实现��由 OpenJDK 社区维护'
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
                .title {{ color: #1a73e8; font-weight: bold; font-size: 14px; margin-bottom: 10px; }}
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
            <div class='title'>JDK {base_info['version']} - {vendor} 
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
                    download_link = self._get_download_link(vendor, version)
                    return False
                else:
                    return False

            # 创建目标目录
            os.makedirs(target_dir, exist_ok=True)
            file_name = os.path.join(target_dir, f"jdk-{version}.zip")

            # 下载文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(download_url, headers=headers, stream=True)
            if response.status_code != 200:
                return False

            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024  # 1 MB
            downloaded_size = 0

            with open(file_name, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded_size += len(data)
                    f.write(data)
                    # 发送进度回调
                    if progress_callback:
                        progress_callback(downloaded_size, total_size)

            return True

        except Exception as e:
            logger.error(f"下载JDK失败: {str(e)}")
            return False

    def _get_download_url(self, vendor, version):
        """获取下载链接"""
        try:
            if vendor == 'Eclipse Temurin (Adoptium)':
                # 使用 Adoptium API v3 获取下载链接
                url = f"https://api.adoptium.net/v3/assets/version/jdk-{version}?architecture=x64&heap_size=normal&image_type=jdk&jvm_impl=hotspot&os=windows&page=0&page_size=1&project=jdk&sort_method=DEFAULT&sort_order=DESC&vendor=eclipse"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        binary = data[0].get('binary')
                        if binary:
                            return binary.get('package', {}).get('link')
            
            elif vendor == 'OpenJDK':
                # OpenJDK 官方下载链接
                if version == '21':
                    return 'https://download.java.net/java/GA/jdk21.0.2/f2283984656d49d69e91c558476027ac/13/GPL/openjdk-21.0.2_windows-x64_bin.zip'
                elif version == '17':
                    return 'https://download.java.net/java/GA/jdk17.0.10/f81d6d7e987c4195b39a77500ee79993/7/GPL/openjdk-17.0.10_windows-x64_bin.zip'
                elif version == '11':
                    return 'https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_windows-x64_bin.zip'
            
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
            
            return None
            
        except Exception as e:
            logger.error(f"获取下载链接失败: {str(e)}")
            return None 