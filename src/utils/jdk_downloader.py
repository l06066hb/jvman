import os
import json
import requests
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime
import time

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
            'Eclipse Temurin (Adoptium)': ['23', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
            'Amazon Corretto': ['23', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', '10', '9', '8'],
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
            '22': {
                'release_date': '2024-03-19',
                'version_detail': '22',
                'features': [
                    '作用域值（Scoped Values）',
                    '字符串模板（正式版）',
                    '未命名模式和变量（正式版）',
                    '外部函数和内存 API（第二次预览）',
                    '矢量 API（第九次孵化）'
                ],
                'lts': False
            },
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

        # 检查是否是 EA 版本
        is_ea = False
        is_temurin = False
        try:
            if vendor == 'OpenJDK':
                # 检查是否是 EA 版本
                if version in version_features:
                    # 如果在版本特性映射中，说明是已发布的正式版本
                    is_ea = False
                else:
                    # 检查是否是 EA 版本
                    ea_url = f'https://jdk.java.net/{version}'
                    response = requests.get(ea_url, timeout=5)
                    if response.status_code == 200:
                        # 更精确的 EA 检测：检查当前版本的下载链接是否包含 ea 或 early_access
                        import re
                        download_links = re.findall(r'https://download\.java\.net/java/[^"]+?openjdk-[^"]+?windows-x64_bin\.(?:zip|tar\.gz)', response.text)
                        if download_links:
                            is_ea = any('ea' in link.lower() or 'early_access' in link.lower() for link in download_links)
                        else:
                            # 如果找不到下载链接，检查页面内容
                            is_ea = 'early access' in response.text.lower() and f'jdk {version}' in response.text.lower()
                    
                    # 如果不是 EA 版本，检查是否有正式发布版本
                    if not is_ea:
                        ga_url = 'https://jdk.java.net/archive/'
                        response = requests.get(ga_url, timeout=5)
                        if response.status_code == 200:
                            # 检查是否存在该版本的 GA 发布
                            pattern = f'jdk{version}[^"]*?/GPL/openjdk-{version}[^"]*?windows-x64_bin\.(?:zip|tar\.gz)'
                            if not re.search(pattern, response.text, re.I):
                                # 如果既不是 EA 也找不到 GA 版本，尝试使用 Temurin
                                temurin_url = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot"
                                response = requests.get(temurin_url, timeout=5)
                                if response.status_code == 200:
                                    is_temurin = True
        except:
            pass

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
            'is_lts': version_features.get(version, {}).get('lts', False),
            'is_ea': is_ea,
            'is_temurin': is_temurin
        }

        try:
            if vendor == 'Oracle JDK':
                features = [
                    '✓ 商业特性支持',
                    '✓ GraalVM 企业版集成',
                    '✓ 高级监控和诊断工具',
                    '✓ 飞行记录器(JFR)',
                    '✓ 任务控制(JMC)',
                    '✓ 应用程序类数据共享'
                ]
                
                # 添加版本特定标记
                if base_info['is_lts']:
                    features.insert(0, '✓ 长期技术支持（LTS）')
                    base_info['support_policy'] = '商业支持 + Oracle 长期技术支持（至少 8 年）'
                    base_info['release_notes'] = '官方 JDK 发行版，提供全面的商业支持和企业特性，建议用于生产环境'
                else:
                    features.insert(0, '⚠️ 短期支持版本（非 LTS）')
                    base_info['support_policy'] = '商业支持（6 个月）'
                    base_info['release_notes'] = '非长期支持版本，建议仅用于测试和开发环境，或等待 LTS 版本'
                
                # 添加许可提醒
                features.append('⚠️ 需要 Oracle 订阅许可（生产环境使用）')
                
                base_info['features'] = features
                
            elif vendor == 'OpenJDK':
                features = [
                    '✓ 开源参考实现',
                    '✓ 社区驱动开发',
                    '✓ 标准Java特性',
                    '✓ 快速迭代更新',
                    '✓ 透明的开发过程'
                ]
                
                # 添加版本特定标记
                if is_ea:
                    features.insert(0, '⚠️ 预览版本（Early Access）')
                    base_info['support_policy'] = '预览版本，仅供测试使用'
                    base_info['release_notes'] = '早期访问版本，可能包含不稳定特性，不建议用于生产环境'
                elif is_temurin:
                    features.insert(0, '📦 由 Eclipse Temurin 提供的构建版本')
                    base_info['support_policy'] = '社区支持 + Eclipse Foundation 支持'
                    base_info['release_notes'] = '由 Eclipse Temurin 提供的稳定构建版本，可用于生产环境'
                elif not base_info['is_lts']:
                    features.insert(0, '⚠️ 短期支持版本（非 LTS）')
                    base_info['support_policy'] = '短期社区支持（6 个月）'
                    base_info['release_notes'] = '非长期支持版本，建议仅用于测试和开发环境，或等待 LTS 版本'
                else:
                    features.insert(0, '✓ 长期支持版本（LTS）')
                    base_info['support_policy'] = '长期社区支持（至少 4 年）'
                    base_info['release_notes'] = 'Java SE 平台的开源参考实现，由 OpenJDK 社区维护，建议用于生产环境'
                
                base_info['features'] = features
            
            elif vendor == 'Amazon Corretto':
                features = [
                        '✓ AWS 云平台优化',
                        '✓ 长期安全补丁',
                        '✓ 企业级性能调优',
                        '✓ 亚马逊生产环境验证',
                        '✓ 跨平台支持'
                ]
                
                # 添加版本特定标记
                if base_info['is_lts']:
                    features.insert(0, '✓ 长期支持版本（LTS）')
                    base_info['support_policy'] = 'Amazon 免费长期支持（至少 4 年）'
                    base_info['release_notes'] = '由亚马逊开发和维护的 OpenJDK 行版，针对 AWS 优化，建议用于生产环境'
                else:
                    features.insert(0, '⚠️ 短期支持版本（非 LTS）')
                    base_info['support_policy'] = 'Amazon 支持（6 个月）'
                    base_info['release_notes'] = '非长期支持版本，建议仅用于测试和开发环境，或等待 LTS 版本'
                
                base_info.update({
                    'features': features
                })
            
            elif vendor == 'Azul Zulu':
                features = [
                        '✓ 完整 TCK 认证',
                        '✓ 性能优化版本',
                        '✓ 可构建定制版本',
                        '✓ 云原生支持',
                        '✓ 容器优化'
                ]
                
                # 添加版本特定标记
                if base_info['is_lts']:
                    features.insert(0, '✓ 长期支持版本（LTS）')
                    base_info['support_policy'] = '社区版免费长期支持 + 商业版付费支持（至少 8 年）'
                    base_info['release_notes'] = '由 Azul Systems 提供的 OpenJDK 构建版本，提供企业级支持，建议用于生产环境'
                else:
                    features.insert(0, '⚠️ 短期支持版本（非 LTS）')
                    base_info['support_policy'] = '社区版支持（6 个月）'
                    base_info['release_notes'] = '非长期支持版本，建议仅用于测试和开发环境，或等待 LTS 版本'
                
                base_info.update({
                    'features': features
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
                .warning-badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-left: 8px;
                    background-color: {'#EA4335' if base_info['is_ea'] else '#FBBC05'};
                    color: white;
                }}
                .provider-badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-left: 8px;
                    background-color: #4285F4;
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
                .warning-text {{
                    color: #EA4335;
                    font-weight: bold;
                    margin: 8px 0;
                }}
            </style>
            <div class='title'>
                <div class='version-info'>
                    JDK {base_info['version']} ({base_info['version_detail']})
                    <span class='vendor'>{vendor}</span>
                    <span class='badge'>{('LTS' if base_info['is_lts'] else '短期支持')}</span>
                    {f'<span class="warning-badge">预览版本</span>' if base_info['is_ea'] else ''}
                    {f'<span class="provider-badge">Temurin</span>' if base_info['is_temurin'] else ''}
                </div>
            </div>
            
            {f'<div class="warning-text">⚠️ 此版本为预览版本，仅供测试使用，不建议在生产环境中使用。</div>' if base_info['is_ea'] else ''}
            {f'<div class="warning-text">⚠️ 此版本为短期支持版本，建议仅用于开发和测试环境。</div>' if not base_info['is_lts'] and not base_info['is_ea'] else ''}
            
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
                # OpenJDK 官方下载链接
                version_map = {
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
                
                # 如果版本不在映射表中，尝试获取最新链接
                if version not in version_map:
                    try:
                        # 1. 先检查是否有 EA（早期访问）版本
                        ea_url = f'https://jdk.java.net/{version}'
                        response = requests.get(ea_url, timeout=5)
                        if response.status_code == 200:
                            # 从页面解析实际下载链接
                            import re
                            match = re.search(r'https://download\.java\.net/java/[^"]+?openjdk-[^"]+?windows-x64_bin\.(?:zip|tar\.gz)', response.text)
                            if match:
                                # 更新版本映射表
                                version_map[version] = match.group(0)
                                return match.group(0)
                        
                        # 2. 如果没有 EA 版本，检查正式发布版本
                        ga_url = f'https://jdk.java.net/archive/'
                        response = requests.get(ga_url, timeout=5)
                        if response.status_code == 200:
                            pattern = f'https://download\\.java\\.net/java/GA/jdk{version}[^"]+?windows-x64_bin\\.(?:zip|tar\\.gz)'
                            match = re.search(pattern, response.text)
                            if match:
                                # 更新版本映射表
                                version_map[version] = match.group(0)
                                return match.group(0)
                        
                        # 3. 如果都没有找到，尝试使用 Eclipse Temurin
                        logger.warning(f"未找到 OpenJDK {version} 的直接下载链接，尝试使用 Eclipse Temurin")
                        temurin_url = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse"
                        temurin_response = requests.get(temurin_url, timeout=5)
                        if temurin_response.status_code == 200:
                            data = temurin_response.json()
                            if data and len(data) > 0:
                                binary = data[0].get('binary')
                                if binary:
                                    link = binary.get('package', {}).get('link')
                                    if link:
                                        # 更新版本映射表
                                        version_map[version] = link
                                        return link
                    except Exception as e:
                        logger.error(f"检查 OpenJDK {version} 版本下载链接失败: {str(e)}")
                
                return version_map.get(version)
            
            elif vendor == 'Eclipse Temurin (Adoptium)':
                # Eclipse Temurin 下载链接
                version_map = {
                    '23': 'https://github.com/adoptium/temurin23-binaries/releases/download/jdk-23-ea+36/OpenJDK23U-jdk_x64_windows_hotspot_ea_23-0-36.zip',
                    '22': 'https://github.com/adoptium/temurin22-binaries/releases/download/jdk-22%2B36/OpenJDK22U-jdk_x64_windows_hotspot_22_36.zip',
                    '21': 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip',
                    '20': 'https://github.com/adoptium/temurin20-binaries/releases/download/jdk-20.0.2%2B9/OpenJDK20U-jdk_x64_windows_hotspot_20.0.2_9.zip',
                    '19': 'https://github.com/adoptium/temurin19-binaries/releases/download/jdk-19.0.2%2B7/OpenJDK19U-jdk_x64_windows_hotspot_19.0.2_7.zip',
                    '18': 'https://github.com/adoptium/temurin18-binaries/releases/download/jdk-18.0.2.1%2B1/OpenJDK18U-jdk_x64_windows_hotspot_18.0.2.1_1.zip',
                    '17': 'https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip',
                    '16': 'https://github.com/adoptium/temurin16-binaries/releases/download/jdk-16.0.2%2B7/OpenJDK16U-jdk_x64_windows_hotspot_16.0.2_7.zip',
                    '15': 'https://github.com/adoptium/temurin15-binaries/releases/download/jdk-15.0.2%2B7/OpenJDK15U-jdk_x64_windows_hotspot_15.0.2_7.zip',
                    '14': 'https://github.com/adoptium/temurin14-binaries/releases/download/jdk-14.0.2%2B12/OpenJDK14U-jdk_x64_windows_hotspot_14.0.2_12.zip',
                    '13': 'https://github.com/adoptium/temurin13-binaries/releases/download/jdk-13.0.2%2B8/OpenJDK13U-jdk_x64_windows_hotspot_13.0.2_8.zip',
                    '12': 'https://github.com/adoptium/temurin12-binaries/releases/download/jdk-12.0.2%2B10/OpenJDK12U-jdk_x64_windows_hotspot_12.0.2_10.zip',
                    '11': 'https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_x64_windows_hotspot_11.0.22_7.zip',
                    '10': 'https://github.com/adoptium/temurin10-binaries/releases/download/jdk-10.0.2%2B13.1/OpenJDK10U-jdk_x64_windows_hotspot_10.0.2_13.zip',
                    '9': 'https://github.com/adoptium/temurin9-binaries/releases/download/jdk-9.0.4%2B11/OpenJDK9U-jdk_x64_windows_hotspot_9.0.4_11.zip',
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

    def download_jdk(self, vendor, version, target_dir, progress_callback=None):
        """下载指定版本的JDK"""
        file_name = None
        response = None
        file_handle = None
        try:
            # 获取下载链接
            download_url = self._get_download_url(vendor, version)
            if not download_url:
                # 根据不同供应商提供不同的手动下载指导
                if vendor == 'Oracle JDK':
                    manual_url = 'https://www.oracle.com/java/technologies/downloads/'
                    return False, f"需要登录 Oracle 账号才能下载。\n\n请按以下步骤操作：\n1. 访问 {manual_url}\n2. 登录 Oracle 账号（如果没有请先注册）\n3. 下载 JDK {version}\n4. 将下载的文件放到目录：{target_dir}", None
                elif vendor == 'OpenJDK':
                    manual_url = 'https://jdk.java.net/'
                    return False, f"无法获取直接下载链接。\n\n请按以下步骤手动下载：\n1. 访问 {manual_url}\n2. 选择 JDK {version}\n3. 下载 Windows 版本\n4. 将下载的文件放到目录：{target_dir}", None
                elif vendor == 'Amazon Corretto':
                    manual_url = 'https://aws.amazon.com/corretto/'
                    return False, f"下载链接获取失败。\n\n请按以下步骤手动下载：\n1. 访问 {manual_url}\n2. 选择 Corretto {version}\n3. 下载 Windows x64 版本\n4. 将下载的文件放到目录：{target_dir}", None
                elif vendor == 'Azul Zulu':
                    manual_url = 'https://www.azul.com/downloads/'
                    return False, f"下载链接获取失败。\n\n请按以下步骤手动下载：\n1. 访问 {manual_url}\n2. 选择 Zulu JDK {version}\n3. 下载 Windows x64 版本\n4. 将下载的文件放到目录：{target_dir}", None
                else:
                    return False, f"无法获取下载链接。请访问 {vendor} 官网手动下载 JDK {version} 版本。", None

            # 创建目标目录
            os.makedirs(target_dir, exist_ok=True)
            file_name = os.path.join(target_dir, f"jdk-{version}.zip")

            # 下载文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }

            try:
                # 先检查链接是否可用
                head_response = requests.head(download_url, headers=headers, timeout=10)
                if head_response.status_code == 403:
                    # 特殊处理 403 错误（通常是需要登录）
                    if vendor == 'Oracle JDK':
                        manual_url = 'https://www.oracle.com/java/technologies/downloads/'
                        return False, f"需要登录 Oracle 账号才能下载。\n\n请按以下步骤操作：\n1. 访问 {manual_url}\n2. 登录 Oracle 账号（如果没有请先注册）\n3. 下载 JDK {version}\n4. 将下载的文件放到目录：{target_dir}", None
                    return False, f"访问下载链接被拒绝（HTTP 403）。请尝试手动下载或稍后重试。\n下载链接：{download_url}", None
                elif head_response.status_code != 200:
                    return False, f"下载链接无效（HTTP {head_response.status_code}）。请尝试手动下载或稍后重试。\n下载链接：{download_url}", None

                # 开始下载
                response = requests.get(download_url, headers=headers, stream=True, timeout=30)
                if response.status_code != 200:
                    return False, f"下载失败（HTTP {response.status_code}）。请尝试手动下载或稍后重试。\n下载链接：{download_url}", None

                total_size = int(response.headers.get('content-length', 0))
                if total_size == 0:
                    return False, f"无法获取文件大小信息。请尝试手动下载：\n{download_url}", None

                block_size = 1024 * 1024  # 1MB
                downloaded_size = 0
                last_progress_time = time.time()

                # 打开文件
                file_handle = open(file_name, 'wb')
                
                # 如果progress_callback有file_handle属性，设置它
                if hasattr(progress_callback, 'set_handles'):
                    progress_callback.set_handles(response, file_handle)
                
                # 下载数据
                for data in response.iter_content(block_size):
                    # 检查是否取消下载
                    if hasattr(progress_callback, 'cancelled') and progress_callback.cancelled:
                        file_handle.close()
                        response.close()
                        if os.path.exists(file_name):
                            try:
                                os.remove(file_name)
                            except Exception as e:
                                logger.error(f"删除取消的下载文件失败: {str(e)}")
                        return False, "下载已取消", None

                    downloaded_size += len(data)
                    file_handle.write(data)
                    
                    # 限制进度回调的频率，每0.1秒最多一次
                    current_time = time.time()
                    if progress_callback and (current_time - last_progress_time >= 0.1):
                        progress_callback(downloaded_size, total_size)
                        last_progress_time = current_time

                # 最后一次进度更新
                if progress_callback:
                    progress_callback(downloaded_size, total_size)

                # 关闭文件和响应
                file_handle.close()
                file_handle = None
                response.close()
                response = None

                # 验证下载的文件大小
                if os.path.getsize(file_name) != total_size:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    return False, f"下载的文件不完整。\n\n请尝试以下方法：\n1. 检查网络连接\n2. 使用手动下载：{download_url}\n3. 将下载的文件放到目录：{target_dir}", None

                # 获取版本信息
                version_info = self.get_version_info(vendor, version)
                
                # 准备JDK信息
                jdk_info = {
                    'path': file_name,  # 先使用zip文件路径，解压后会更新为实际JDK目录
                    'version': version,
                    'type': 'downloaded',
                    'vendor': vendor,  # 添加发行商信息
                    'features': version_info.get('features', []) if version_info else [],
                    'import_time': int(datetime.now().timestamp())
                }

                # 如果是 OpenJDK 且使用了 Temurin 构建
                if vendor == 'OpenJDK' and version_info and 'is_temurin' in version_info and version_info['is_temurin']:
                    jdk_info['vendor'] = 'Eclipse Temurin'

                return True, "下载成功", jdk_info

            except requests.Timeout:
                if file_handle:
                    file_handle.close()
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, f"下载超时。\n\n请尝试以下方法：\n1. 检查网络连接\n2. 使用手动下载：{download_url}\n3. 将下载的文件放到目录：{target_dir}", None
            except requests.ConnectionError:
                if file_handle:
                    file_handle.close()
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, f"网络连接错误。\n\n请尝试以下方法：\n1. 检查网络连接\n2. 检查代理设置\n3. 使用手动下载：{download_url}\n4. 将下载的文件放到目录：{target_dir}", None
            except Exception as e:
                if file_handle:
                    file_handle.close()
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, f"下载过程中出错: {str(e)}\n\n请尝试手动下载：\n{download_url}", None
            finally:
                if response:
                    response.close()
                if file_handle:
                    file_handle.close()

        except Exception as e:
            if file_handle:
                file_handle.close()
            if response:
                response.close()
            if file_name and os.path.exists(file_name):
                os.remove(file_name)
            logger.error(f"下载JDK失败: {str(e)}")
            return False, f"下载失败: {str(e)}\n\n请尝试手动下载对应版本的JDK。", None

    def _get_download_url(self, vendor, version):
        """获取下载链接"""
        try:
            # 直接返回 _get_download_link 的结果
            return self._get_download_link(vendor, version)
            
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