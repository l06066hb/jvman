import os
import json
import requests
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime
import time
from src.utils.i18n_manager import i18n_manager

# 确保国际化管理器被正确初始化
_ = i18n_manager.get_text

class VersionUpdateThread(QThread):
    """版本更新线程"""
    def __init__(self, downloader):
        super().__init__()
        self.downloader = downloader
        # 确保在线程中也能使用国际化
        self._ = i18n_manager.get_text
        
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
            logger.error(_("log.error.fetch_failed").format(error=str(e)))

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
        
        # 连接语言变更信号
        i18n_manager.language_changed.connect(self._on_language_changed)

    def _on_language_changed(self):
        """处理语言变更"""
        # 清除版本信息缓存
        self.version_info_cache.clear()
        
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
            logger.error(_("downloader.log.error.async_update_failed").format(error=str(e)))
            
    def __del__(self):
        """析构函数"""
        try:
            # 确保线程正确退出
            if self.update_thread and self.update_thread.isRunning():
                self.update_thread.quit()
                self.update_thread.wait()
        except Exception as e:
            logger.error(_("downloader.log.error.cleanup_thread_failed").format(error=str(e)))

    def get_available_versions(self, vendor):
        """获取指定发行版可用的JDK版本列表"""
        try:
            logger.debug(_("downloader.log.debug.fetching_versions").format(vendor=vendor))
            if vendor not in self.api_config:
                logger.error(_("downloader.error.unsupported_vendor").format(vendor=vendor))
                return self.base_versions.get(vendor, [])
                
            if 'versions' not in self.api_config[vendor]:
                logger.error(_("downloader.error.no_versions_found").format(vendor=vendor))
                return self.base_versions.get(vendor, [])
                
            versions = self.api_config[vendor]['versions']
            if not versions:
                logger.warning(_("downloader.warning.empty_versions").format(vendor=vendor))
                return self.base_versions.get(vendor, [])
                
            return versions
            
        except Exception as e:
            logger.error(_("downloader.log.error.fetch_failed").format(error=str(e)))
            logger.debug(f"API Config: {self.api_config}")
            # 如果出错，返回基础版本列表
            return self.base_versions.get(vendor, [])

    def get_version_info(self, vendor, version):
        """获取版本详细信息"""
        try:
            logger.debug(_("downloader.log.debug.getting_info").format(vendor=vendor, version=version))
            # 在缓存键中加入当前语言
            current_lang = i18n_manager.current_lang
            cache_key = f"{vendor}-{version}-{current_lang}"
            
            if cache_key in self.version_info_cache:
                return self.version_info_cache[cache_key]
                
            info = self._fetch_version_info(vendor, version)
            if info:
                self.version_info_cache[cache_key] = info
                return info
            raise Exception(_("downloader.error.no_version_info"))
        except Exception as e:
            logger.error(_("downloader.log.error.info_failed").format(error=str(e)))
            return None

    def _fetch_version_info(self, vendor, version):
        print(vendor,version)
        """从API获取版本信息"""
        # JDK版本特性映射
        version_features = {
            '23': {
                'release_date': '2024-09-17',
                'version_detail': '23',
                'features': [
                    'version.feature.23.generics',
                    'version.feature.23.string_templates',
                    'version.feature.23.unnamed_patterns',
                    'version.feature.23.foreign_memory',
                    'version.feature.23.vector_api'
                ],
                'lts': False
            },
            '22': {
                'release_date': '2024-03-19',
                'version_detail': '22',
                'features': [
                    _('version.feature.22.scoped_values'),
                    _('version.feature.22.string_templates'),
                    _('version.feature.22.unnamed_patterns'),
                    _('version.feature.22.foreign_memory'),
                    _('version.feature.22.vector_api')
                ],
                'lts': False
            },
            '21': {
                'release_date': '2023-09-19',
                'version_detail': '21.0.2',
                'features': [
                    _('version.feature.21.string_templates'),
                    _('version.feature.21.sequence_collections'),
                    _('version.feature.21.virtual_threads'),
                    _('version.feature.21.record_patterns'),
                    _('version.feature.21.zgc'),
                    _('version.feature.21.foreign_memory')
                ],
                'lts': True
            },
            '17': {
                'release_date': '2021-09-14',
                'version_detail': '17.0.10',
                'features': [
                    _('version.feature.17.sealed_classes'),
                    _('version.feature.17.switch_patterns'),
                    _('version.feature.17.random_generator'),
                    _('version.feature.17.macos_aarch64'),
                    _('version.feature.17.macos_rendering')
                ],
                'lts': True
            },
            '11': {
                'release_date': '2018-09-25',
                'version_detail': '11.0.22',
                'features': [
                    _('version.feature.11.http_client'),
                    _('version.feature.11.lambda_vars'),
                    _('version.feature.11.single_file'),
                    _('version.feature.11.unicode_10'),
                    _('version.feature.11.dynamic_constants'),
                    _('version.feature.11.epsilon_gc')
                ],
                'lts': True
            },
            '8': {
                'release_date': '2014-03-18',
                'version_detail': '8u402',
                'features': [
                    _('version.feature.8.lambda'),
                    _('version.feature.8.method_ref'),
                    _('version.feature.8.default_methods'),
                    _('version.feature.8.stream_api'),
                    _('version.feature.8.date_time'),
                    _('version.feature.8.optional')
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
            'release_date': version_features.get(version, {}).get('release_date', _('common.loading')),
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
                    _('vendor.oracle.feature.commercial'),
                    _('vendor.oracle.feature.graalvm'),
                    _('vendor.oracle.feature.monitoring'),
                    _('vendor.oracle.feature.jfr'),
                    _('vendor.oracle.feature.jmc'),
                    _('vendor.oracle.feature.cds')
                ]
                
                # 添加版本特定标记
                if base_info['is_lts']:
                    features.insert(0, _('vendor.oracle.feature.lts'))
                    base_info['support_policy'] = _('vendor.oracle.support.lts')
                    base_info['release_notes'] = _('vendor.oracle.notes.lts')
                else:
                    features.insert(0, _('vendor.oracle.feature.sts'))
                    base_info['support_policy'] = _('vendor.oracle.support.sts')
                    base_info['release_notes'] = _('vendor.oracle.notes.sts')
                
                # 添加许可提醒
                features.append(_('vendor.oracle.feature.license'))
                
                # 设置发行商特性
                base_info['features'] = features
                # 确保版本特性使用正确的国际化文本
                if version in version_features:
                    base_info['version_features'] = [_(feature) for feature in version_features[version]['features']]
                
            elif vendor == 'OpenJDK':
                features = [
                    _('vendor.openjdk.feature.reference'),
                    _('vendor.openjdk.feature.community'),
                    _('vendor.openjdk.feature.standard'),
                    _('vendor.openjdk.feature.updates'),
                    _('vendor.openjdk.feature.transparent')
                ]
                
                # 添加版本特定标记
                if is_ea:
                    features.insert(0, _('vendor.openjdk.feature.ea'))
                    base_info['support_policy'] = _('vendor.openjdk.support.ea')
                    base_info['release_notes'] = _('vendor.openjdk.notes.ea')
                elif is_temurin:
                    features.insert(0, _('vendor.openjdk.feature.temurin'))
                    base_info['support_policy'] = _('vendor.openjdk.support.temurin')
                    base_info['release_notes'] = _('vendor.openjdk.notes.temurin')
                elif not base_info['is_lts']:
                    features.insert(0, _('vendor.openjdk.feature.sts'))
                    base_info['support_policy'] = _('vendor.openjdk.support.sts')
                    base_info['release_notes'] = _('vendor.openjdk.notes.sts')
                else:
                    features.insert(0, _('vendor.openjdk.feature.lts'))
                    base_info['support_policy'] = _('vendor.openjdk.support.lts')
                    base_info['release_notes'] = _('vendor.openjdk.notes.lts')
                
                base_info['features'] = features
            
            elif vendor == 'Amazon Corretto':
                features = [
                    _('vendor.corretto.feature.aws'),
                    _('vendor.corretto.feature.security'),
                    _('vendor.corretto.feature.performance'),
                    _('vendor.corretto.feature.production'),
                    _('vendor.corretto.feature.platform')
                ]
                
                # 添加版本特定标记
                if base_info['is_lts']:
                    features.insert(0, _('vendor.corretto.feature.lts'))
                    base_info['support_policy'] = _('vendor.corretto.support.lts')
                    base_info['release_notes'] = _('vendor.corretto.notes.lts')
                else:
                    features.insert(0, _('vendor.corretto.feature.sts'))
                    base_info['support_policy'] = _('vendor.corretto.support.sts')
                    base_info['release_notes'] = _('vendor.corretto.notes.sts')
                
                base_info.update({
                    'features': features
                })
            
            elif vendor == 'Azul Zulu':
                features = [
                    _('vendor.zulu.feature.tck'),
                    _('vendor.zulu.feature.performance'),
                    _('vendor.zulu.feature.custom'),
                    _('vendor.zulu.feature.cloud'),
                    _('vendor.zulu.feature.container')
                ]
                
                # 添加版本特定标记
                if base_info['is_lts']:
                    features.insert(0, _('vendor.zulu.feature.lts'))
                    base_info['support_policy'] = _('vendor.zulu.support.lts')
                    base_info['release_notes'] = _('vendor.zulu.notes.lts')
                else:
                    features.insert(0, _('vendor.zulu.feature.sts'))
                    base_info['support_policy'] = _('vendor.zulu.support.sts')
                    base_info['release_notes'] = _('vendor.zulu.notes.sts')
                
                base_info.update({
                    'features': features
                })

            # 获取下载链接
            download_link = self._get_download_link(vendor, version)

            # 预先获取所有需要的翻译文本
            translations = {
                'title': _("version.info.detail.title"),
                'release_date': _("jdk.info.release_date"),
                'runtime': _("version.info.detail.runtime"),
                'features': _("jdk.info.features"),
                'version_features': _("jdk.info.version_features"),
                'support_policy': _("jdk.info.support_policy"),
                'download_link': _("version.info.download_link"),
                'badge': {
                    'lts': _("version.badge.lts"),
                    'sts': _("version.badge.sts"),
                    'ea': _("version.badge.ea"),
                    'temurin': _("version.badge.temurin")
                },
                'warning': {
                    'ea': _("version.warning.ea"),
                    'sts': _("version.warning.sts")
                }
            }

            # 确保所有特性文本都被翻译
            base_info['features'] = [_(feature) if isinstance(feature, str) else feature 
                                   for feature in base_info['features']]
            base_info['version_features'] = [_(feature) if isinstance(feature, str) else feature 
                                           for feature in base_info['version_features']]
            base_info['support_policy'] = _(base_info['support_policy']) if isinstance(base_info['support_policy'], str) else base_info['support_policy']
            base_info['release_notes'] = _(base_info['release_notes']) if isinstance(base_info['release_notes'], str) else base_info['release_notes']

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
                    {translations['title']} {base_info['version']} ({base_info['version_detail']})
                    <span class='vendor'>{vendor}</span>
                    <span class='badge'>{translations['badge']['lts'] if base_info['is_lts'] else translations['badge']['sts']}</span>
                    {f'<span class="warning-badge">{translations["badge"]["ea"]}</span>' if base_info['is_ea'] else ''}
                    {f'<span class="provider-badge">{translations["badge"]["temurin"]}</span>' if base_info['is_temurin'] else ''}
                </div>
            </div>
            
            {f'<div class="warning-text">{translations["warning"]["ea"]}</div>' if base_info['is_ea'] else ''}
            {f'<div class="warning-text">{translations["warning"]["sts"]}</div>' if not base_info['is_lts'] and not base_info['is_ea'] else ''}
            
            <div class='section'>
                <span class='label'>{translations['release_date']}:</span>
                <span class='value'> {base_info['release_date']}</span>
            </div>
            
            <div class='section'>
                <span class='label'>{translations['runtime']}:</span>
                <span class='value'> {base_info['jvm_impl']} VM, {base_info['arch']}, {base_info['os']}</span>
            </div>
            
            <div class='section'>
                <div class='label'>{translations['features']}:</div>
                {"".join(f"<div class='feature'>{feature}</div>" for feature in base_info['features'])}
            </div>
            
            <div class='divider'></div>
            
            <div class='section'>
                <div class='label'>{translations['version_features']}:</div>
                {"".join(f"<div class='version-feature'>{feature}</div>" for feature in base_info['version_features'])}
            </div>
            
            <div class='divider'></div>
            
            <div class='section'>
                <span class='label'>{translations['support_policy']}:</span>
                <span class='value'> {base_info['support_policy']}</span>
            </div>
            
            <div class='note'>{base_info['release_notes']}</div>
            
            {f'<a href="{download_link}" class="download-link" target="_blank">{translations["download_link"]}</a>' if download_link else ''}"""

            return info_text
        except Exception as e:
            logger.error(_("version.info.detail.get_failed").format(error=str(e)))
            return _("version.info.not_available")

    def _get_download_link(self, vendor, version):
        """获取官方下载链接"""
        try:
            # 获取当前平台信息
            from .platform_manager import platform_manager
            is_windows = platform_manager.is_windows
            is_macos = platform_manager.is_macos
            is_linux = platform_manager.is_linux
            arch = platform_manager.get_arch()  # 获取系统架构
            
            # 根据平台选择文件扩展名和系统标识
            if is_windows:
                ext = 'zip'
                os_name = 'windows'
            elif is_macos:
                ext = 'tar.gz'
                os_name = 'macos'
            else:  # Linux
                ext = 'tar.gz'
                os_name = 'linux'
            
            if vendor == 'Oracle JDK':
                return 'https://www.oracle.com/java/technologies/downloads/'
            
            elif vendor == 'OpenJDK':
                # OpenJDK 官方下载链接
                version_map = {
                    '23': f'https://download.java.net/java/early_access/jdk23/36/GPL/openjdk-23-ea+36_{os_name}-{arch}_bin.{ext}',
                    '22': f'https://download.java.net/java/GA/jdk22/830ec9fcccef480bb3e73fb7ecafe059/36/GPL/openjdk-22_{os_name}-{arch}_bin.{ext}',
                    '21': f'https://download.java.net/java/GA/jdk21.0.2/f2283984656d49d69e91c558476027ac/13/GPL/openjdk-21.0.2_{os_name}-{arch}_bin.{ext}',
                    '20': f'https://download.java.net/java/GA/jdk20.0.2/6e380f22cbe7469fa75fb448bd903d8e/9/GPL/openjdk-20.0.2_{os_name}-{arch}_bin.{ext}',
                    '19': f'https://download.java.net/java/GA/jdk19.0.2/fdb695a9d9064ad6b064dc6df578380c/7/GPL/openjdk-19.0.2_{os_name}-{arch}_bin.{ext}',
                    '18': f'https://download.java.net/java/GA/jdk18.0.2.1/db379da656dc47308e138f21b33976fa/1/GPL/openjdk-18.0.2.1_{os_name}-{arch}_bin.{ext}',
                    '17': f'https://download.java.net/java/GA/jdk17.0.10/f81d6d7e987c4195b39a77500ee79993/7/GPL/openjdk-17.0.10_{os_name}-{arch}_bin.{ext}',
                    '16': f'https://download.java.net/java/GA/jdk16.0.2/d4a915d82b4c4fbb9bde534da945d746/7/GPL/openjdk-16.0.2_{os_name}-{arch}_bin.{ext}',
                    '15': f'https://download.java.net/java/GA/jdk15.0.2/0d1cfde4252546c6931946de8db48ee2/7/GPL/openjdk-15.0.2_{os_name}-{arch}_bin.{ext}',
                    '14': f'https://download.java.net/java/GA/jdk14.0.2/205943a0976c4ed48cb16f1043c5c647/12/GPL/openjdk-14.0.2_{os_name}-{arch}_bin.{ext}',
                    '13': f'https://download.java.net/java/GA/jdk13.0.2/d4173c853231432d94f001e99d882ca7/8/GPL/openjdk-13.0.2_{os_name}-{arch}_bin.{ext}',
                    '12': f'https://download.java.net/java/GA/jdk12.0.2/e482c34c86bd4bf8b56c0b35558996b9/10/GPL/openjdk-12.0.2_{os_name}-{arch}_bin.{ext}',
                    '11': f'https://download.java.net/java/GA/jdk11.0.22/d3fd698c6a1c4aa6ad1fca312585d76b/7/GPL/openjdk-11.0.22_{os_name}-{arch}_bin.{ext}',
                    '10': f'https://download.java.net/java/GA/jdk10/10.0.2/19aef61b38124481863b1413dce1855f/13/openjdk-10.0.2_{os_name}-{arch}_bin.{ext}',
                    '9': f'https://download.java.net/java/GA/jdk9/9.0.4/binaries/openjdk-9.0.4_{os_name}-{arch}_bin.{ext}',
                    '8': f'https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u402-b06/OpenJDK8U-jdk_{arch}_{os_name}_hotspot_8u402b06.{ext}'
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
                            patterns = [
                                f'https://download\\.java\\.net/java/early_access/jdk{version}/[^"]+?/GPL/openjdk-{version}-ea\\+[^"]+?_{os_name}-{arch}_bin\\.{ext}',
                                f'https://download\\.java\\.net/java/early_access/jdk{version}/[^"]+?/GPL/openjdk-{version}\\+[^"]+?_{os_name}-{arch}_bin\\.{ext}',
                                f'https://download\\.java\\.net/java/GA/jdk{version}[^"]+?/GPL/openjdk-{version}[^"]+?_{os_name}-{arch}_bin\\.{ext}',
                                f'https://download\\.java\\.net/java/GA/jdk{version}[^"]+?/binaries/openjdk-{version}[^"]+?_{os_name}-{arch}_bin\\.{ext}'
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, response.text)
                                if match:
                                    # 更新版本映射表
                                    version_map[version] = match.group(0)
                                    return match.group(0)
                        
                        # 2. 如果没有 EA 版本，检查正式发布版本
                        ga_url = f'https://jdk.java.net/archive/'
                        response = requests.get(ga_url, timeout=5)
                        if response.status_code == 200:
                            patterns = [
                                f'https://download\\.java\\.net/java/GA/jdk{version}[^"]+?/GPL/openjdk-{version}[^"]+?_{os_name}-{arch}_bin\\.{ext}',
                                f'https://download\\.java\\.net/java/GA/jdk{version}[^"]+?/binaries/openjdk-{version}[^"]+?_{os_name}-{arch}_bin\\.{ext}'
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, response.text)
                                if match:
                                    # 更新版本映射表
                                    version_map[version] = match.group(0)
                                    return match.group(0)
                        
                        # 3. 如果都没有找到，尝试使用 Eclipse Temurin
                        logger.warning(_("downloader.log.warning.use_temurin").format(version=version))
                        temurin_url = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot"
                        params = {
                            'architecture': arch,
                            'image_type': 'jdk',
                            'os': os_name,
                            'vendor': 'eclipse',
                            'page_size': 1
                        }
                        temurin_response = requests.get(temurin_url, params=params, timeout=5)
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
                        logger.error(_("downloader.log.error.check_link_failed").format(version=version, error=str(e)))
                
                return version_map.get(version)
            
            elif vendor == 'Eclipse Temurin (Adoptium)':
                # Eclipse Temurin 下载链接
                version_map = {
                    '23': f'https://github.com/adoptium/temurin23-binaries/releases/download/jdk-23-ea+36/OpenJDK23U-jdk_{arch}_{os_name}_hotspot_ea_23-0-36.{ext}',
                    '22': f'https://github.com/adoptium/temurin22-binaries/releases/download/jdk-22%2B36/OpenJDK22U-jdk_{arch}_{os_name}_hotspot_22_36.{ext}',
                    '21': f'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_{arch}_{os_name}_hotspot_21.0.2_13.{ext}',
                    '20': f'https://github.com/adoptium/temurin20-binaries/releases/download/jdk-20.0.2%2B9/OpenJDK20U-jdk_{arch}_{os_name}_hotspot_20.0.2_9.{ext}',
                    '19': f'https://github.com/adoptium/temurin19-binaries/releases/download/jdk-19.0.2%2B7/OpenJDK19U-jdk_{arch}_{os_name}_hotspot_19.0.2_7.{ext}',
                    '18': f'https://github.com/adoptium/temurin18-binaries/releases/download/jdk-18.0.2.1%2B1/OpenJDK18U-jdk_{arch}_{os_name}_hotspot_18.0.2.1_1.{ext}',
                    '17': f'https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_{arch}_{os_name}_hotspot_17.0.10_7.{ext}',
                    '16': f'https://github.com/adoptium/temurin16-binaries/releases/download/jdk-16.0.2%2B7/OpenJDK16U-jdk_{arch}_{os_name}_hotspot_16.0.2_7.{ext}',
                    '15': f'https://github.com/adoptium/temurin15-binaries/releases/download/jdk-15.0.2%2B7/OpenJDK15U-jdk_{arch}_{os_name}_hotspot_15.0.2_7.{ext}',
                    '14': f'https://github.com/adoptium/temurin14-binaries/releases/download/jdk-14.0.2%2B12/OpenJDK14U-jdk_{arch}_{os_name}_hotspot_14.0.2_12.{ext}',
                    '13': f'https://github.com/adoptium/temurin13-binaries/releases/download/jdk-13.0.2%2B8/OpenJDK13U-jdk_{arch}_{os_name}_hotspot_13.0.2_8.{ext}',
                    '12': f'https://github.com/adoptium/temurin12-binaries/releases/download/jdk-12.0.2%2B10/OpenJDK12U-jdk_{arch}_{os_name}_hotspot_12.0.2_10.{ext}',
                    '11': f'https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_{arch}_{os_name}_hotspot_11.0.22_7.{ext}',
                    '10': f'https://github.com/adoptium/temurin10-binaries/releases/download/jdk-10.0.2%2B13.1/OpenJDK10U-jdk_{arch}_{os_name}_hotspot_10.0.2_13.{ext}',
                    '9': f'https://github.com/adoptium/temurin9-binaries/releases/download/jdk-9.0.4%2B11/OpenJDK9U-jdk_{arch}_{os_name}_hotspot_9.0.4_11.{ext}',
                    '8': f'https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u402-b06/OpenJDK8U-jdk_{arch}_{os_name}_hotspot_8u402b06.{ext}'
                }
                
                # 如果版本不在映射表中，尝试从 API 获取
                if version not in version_map:
                    try:
                        api_url = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot"
                        params = {
                            'architecture': arch,
                            'image_type': 'jdk',
                            'os': os_name,
                            'vendor': 'eclipse',
                            'page_size': 1
                        }
                        response = requests.get(api_url, params=params, timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            if data and len(data) > 0:
                                binary = data[0].get('binary')
                                if binary:
                                    link = binary.get('package', {}).get('link')
                                    if link:
                                        version_map[version] = link
                                        return link
                    except Exception as e:
                        logger.error(f"获取 Temurin {version} 下载链接失败: {str(e)}")
                
                return version_map.get(version)
            
            elif vendor == 'Amazon Corretto':
                # Amazon Corretto 下载链接
                if is_windows:
                    os_suffix = 'windows'
                elif is_macos:
                    os_suffix = 'macos'
                else:
                    os_suffix = 'linux'
                
                # 尝试获取具体版本号
                try:
                    api_url = f"https://corretto.aws/downloads/latest/{version}"
                    response = requests.get(api_url, allow_redirects=False, timeout=5)
                    if response.status_code == 302:
                        redirect_url = response.headers.get('Location', '')
                        if redirect_url:
                            # 从重定向URL中提取完整版本号
                            import re
                            version_match = re.search(r'amazon-corretto-([^-]+)', redirect_url)
                            if version_match:
                                full_version = version_match.group(1)
                                return f'https://corretto.aws/downloads/resources/{full_version}/amazon-corretto-{full_version}-{arch}-{os_suffix}-jdk.{ext}'
                except Exception as e:
                    logger.error(f"获取 Corretto {version} 版本信息失败: {str(e)}")
                
                # 如果无法获取具体版本号，使用通用链接
                return f'https://corretto.aws/downloads/latest/amazon-corretto-{version}-{arch}-{os_suffix}-jdk.{ext}'
            
            elif vendor == 'Azul Zulu':
                # Azul Zulu 下载链接
                if is_windows:
                    os_suffix = 'win'
                elif is_macos:
                    os_suffix = 'macosx'
                else:
                    os_suffix = 'linux'
                
                # 尝试获取最新版本信息
                try:
                    api_url = "https://api.azul.com/zulu/download/community/v1.0/bundles/latest/"
                    params = {
                        'jdk_version': version,
                        'os': os_suffix,
                        'arch': arch,
                        'ext': ext,
                        'bundle_type': 'jdk'
                    }
                    response = requests.get(api_url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data and 'url' in data:
                            return data['url']
                except Exception as e:
                    logger.error(f"获取 Zulu {version} 下载链接失败: {str(e)}")
                
                # 如果API调用失败，使用预定义的版本映射
                version_map = {
                    '21': f'https://cdn.azul.com/zulu/bin/zulu21.32.17-ca-jdk21.0.2-{os_suffix}_{arch}.{ext}',
                    '17': f'https://cdn.azul.com/zulu/bin/zulu17.48.15-ca-jdk17.0.10-{os_suffix}_{arch}.{ext}',
                    '11': f'https://cdn.azul.com/zulu/bin/zulu11.70.15-ca-jdk11.0.22-{os_suffix}_{arch}.{ext}',
                    '8': f'https://cdn.azul.com/zulu/bin/zulu8.76.0.17-ca-jdk8.0.402-{os_suffix}_{arch}.{ext}'
                }
                return version_map.get(version)
            
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
            # 获取平台信息
            from .platform_manager import platform_manager
            is_windows = platform_manager.is_windows
            is_macos = platform_manager.is_macos
            
            # 根据平台选择文件扩展名
            ext = 'zip' if is_windows else 'tar.gz'
            
            # 获取下载链接
            download_url = self._get_download_url(vendor, version)
            if not download_url:
                # 根据不同供应商提供不同的手动下载指导
                if vendor == 'Oracle JDK':
                    manual_url = 'https://www.oracle.com/java/technologies/downloads/'
                    return False, _("downloader.manual.oracle").format(
                        url=manual_url,
                        version=version,
                        dir=target_dir
                    ), None
                elif vendor == 'OpenJDK':
                    manual_url = 'https://jdk.java.net/'
                    return False, _("downloader.manual.openjdk").format(
                        url=manual_url,
                        version=version,
                        dir=target_dir
                    ), None
                elif vendor == 'Amazon Corretto':
                    manual_url = 'https://aws.amazon.com/corretto/'
                    return False, _("downloader.manual.corretto").format(
                        url=manual_url,
                        version=version,
                        dir=target_dir
                    ), None
                elif vendor == 'Azul Zulu':
                    manual_url = 'https://www.azul.com/downloads/'
                    return False, _("downloader.manual.zulu").format(
                        url=manual_url,
                        version=version,
                        dir=target_dir
                    ), None
                else:
                    return False, _("downloader.manual.other").format(
                        vendor=vendor,
                        version=version
                    ), None

            # 创建目标目录
            os.makedirs(target_dir, exist_ok=True)
            file_name = os.path.join(target_dir, f"jdk-{version}.{ext}")

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
                        return False, _("downloader.error.oracle_auth").format(
                            url=manual_url,
                            version=version,
                            dir=target_dir
                        ), None
                    return False, _("downloader.error.access_denied").format(url=download_url), None
                elif head_response.status_code != 200:
                    return False, _("downloader.error.invalid_url").format(
                        status=head_response.status_code,
                        url=download_url
                    ), None

                # 开始下载
                response = requests.get(download_url, headers=headers, stream=True, timeout=30)
                if response.status_code != 200:
                    return False, _("downloader.error.download_failed").format(
                        status=response.status_code,
                        url=download_url
                    ), None

                total_size = int(response.headers.get('content-length', 0))
                if total_size == 0:
                    return False, _("downloader.error.no_size").format(url=download_url), None

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
                                logger.error(_("downloader.error.cleanup_failed").format(error=str(e)))
                        return False, _("downloader.status.cancelled"), None

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
                    return False, _("downloader.error.incomplete").format(
                        url=download_url,
                        dir=target_dir
                    ), None

                # 获取版本信息
                version_info = self.get_version_info(vendor, version)
                
                # 准备JDK信息
                jdk_info = {
                    'path': file_name,  # 先使用压缩文件路径，解压后会更新为实际JDK目录
                    'version': version,
                    'type': 'downloaded',
                    'vendor': vendor,  # 添加发行商信息
                    'features': version_info.get('features', []) if version_info else [],
                    'import_time': int(datetime.now().timestamp())
                }

                # 如果是 OpenJDK 且使用了 Temurin 构建
                if vendor == 'OpenJDK' and version_info and 'is_temurin' in version_info and version_info['is_temurin']:
                    jdk_info['vendor'] = 'Eclipse Temurin'

                return True, _("downloader.status.success"), jdk_info

            except requests.Timeout:
                if file_handle:
                    file_handle.close()
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, _("downloader.error.timeout").format(
                    url=download_url,
                    dir=target_dir
                ), None
            except requests.ConnectionError:
                if file_handle:
                    file_handle.close()
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, _("downloader.error.connection").format(
                    url=download_url,
                    dir=target_dir
                ), None
            except Exception as e:
                if file_handle:
                    file_handle.close()
                if os.path.exists(file_name):
                    os.remove(file_name)
                return False, _("downloader.error.general").format(
                    error=str(e),
                    url=download_url
                ), None
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
            logger.error(_("downloader.error.download_failed").format(error=str(e)))
            return False, _("downloader.error.manual_required").format(error=str(e)), None

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
            logger.error(_("downloader.log.error.fetch_adoptium_failed").format(error=str(e)))
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
            logger.error(_("downloader.log.error.fetch_zulu_failed").format(error=str(e)))
        return self.base_versions['Azul Zulu'] 