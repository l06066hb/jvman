#!/usr/bin/env python
import os
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
import sys
from loguru import logger
import requests
import html
import time
from urllib.parse import quote
import random
import hashlib

def update_version(version_type='patch'):
    """更新版本号
    version_type: major, minor, patch
    """
    with open('config/app.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 解析当前版本号
    current = config['version'].split('.')
    major, minor, patch = map(int, current)
    
    # 更新版本号
    if version_type == 'major':
        major += 1
        minor = patch = 0
    elif version_type == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    new_version = f"{major}.{minor}.{patch}"
    config['version'] = new_version
    
    # 写入新版本号
    with open('config/app.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    return new_version

def update_readme_version(version, file_path):
    """更新 README 中的版本信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新版本徽章
        version_badge_pattern = r'!\[Version\]\([^)]+\)'
        new_version_badge = f'![Version](https://img.shields.io/badge/version-{version}-blue)'
        if re.search(version_badge_pattern, content):
            content = re.sub(version_badge_pattern, new_version_badge, content)
        else:
            # 如果没有找到版本徽章，在文件开头添加（在标题后面）
            title_end = content.find('\n', content.find('#'))
            if title_end != -1:
                content = content[:title_end] + f'\n\n{new_version_badge}' + content[title_end:]
        
        # 更新版本号文本
        version_pattern = r'当前版本[：:]\s*v?\d+\.\d+\.\d+'
        version_en_pattern = r'Current Version[：:]\s*v?\d+\.\d+\.\d+'
        new_version_text = f'当前版本: v{version}'
        new_version_text_en = f'Current Version: v{version}'
        
        if re.search(version_pattern, content):
            content = re.sub(version_pattern, new_version_text, content)
        if re.search(version_en_pattern, content):
            content = re.sub(version_en_pattern, new_version_text_en, content)
        
        # 移除更新日志部分（如果存在）
        changelog_pattern = r'## 更新日志[\s\S]*?(?=##|$)'
        changelog_en_pattern = r'## Changelog[\s\S]*?(?=##|$)'
        
        # 替换为更新日志链接
        changelog_link_zh = "\n## 更新日志\n\n详细的更新历史请查看 [CHANGELOG.md](CHANGELOG.md)\n\n"
        changelog_link_en = "\n## Changelog\n\nFor detailed release notes, please check [CHANGELOG.md](CHANGELOG.md)\n\n"
        
        if re.search(changelog_pattern, content):
            content = re.sub(changelog_pattern, changelog_link_zh, content)
        if re.search(changelog_en_pattern, content):
            content = re.sub(changelog_en_pattern, changelog_link_en, content)
        
        # 如果没有找到更新日志部分，在文件末尾添加链接
        if '更新日志' not in content and 'Changelog' not in content:
            if file_path.endswith('_zh.md'):
                content += changelog_link_zh
            else:
                content += changelog_link_en
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated version in {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to update version in {file_path}: {str(e)}")
        return False

class Translator:
    """翻译器类"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        # 从环境变量或配置文件获取百度翻译 API 密钥
        self.baidu_appid = os.getenv('BAIDU_TRANSLATE_APPID')
        self.baidu_secret = os.getenv('BAIDU_TRANSLATE_SECRET')
        
        if not self.baidu_appid or not self.baidu_secret:
            # 尝试从配置文件读取
            try:
                with open('config/translate.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.baidu_appid = config.get('baidu_appid')
                    self.baidu_secret = config.get('baidu_secret')
            except Exception as e:
                logger.warning(f"无法加载翻译配置: {str(e)}")
    
    def translate_baidu(self, text, target_lang='en'):
        """使用百度翻译 API 进行翻译"""
        try:
            if not self.baidu_appid or not self.baidu_secret:
                logger.error("未配置百度翻译 API 密钥")
                return None
            
            # 转换语言代码
            lang_map = {
                'en': 'en',
                'zh': 'zh',
                'en_US': 'en',
                'zh_CN': 'zh'
            }
            target = lang_map.get(target_lang, 'en')
            
            # 准备请求参数
            salt = str(random.randint(32768, 65536))
            sign = self.baidu_appid + text + salt + self.baidu_secret
            sign = hashlib.md5(sign.encode('utf-8')).hexdigest()
            
            params = {
                'appid': self.baidu_appid,
                'q': text,
                'from': 'auto',
                'to': target,
                'salt': salt,
                'sign': sign
            }
            
            url = 'https://api.fanyi.baidu.com/api/trans/vip/translate'
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if 'trans_result' in result:
                    return result['trans_result'][0]['dst']
                else:
                    logger.error(f"翻译失败: {result.get('error_msg', '未知错误')}")
            return None
        except Exception as e:
            logger.error(f"翻译请求失败: {str(e)}")
            return None
    
    def translate_with_retry(self, text, target_lang='en', max_retries=3, delay=1):
        """带重试机制的翻译"""
        if not text:
            return text
        
        for i in range(max_retries):
            try:
                result = self.translate_baidu(text, target_lang)
                if result:
                    # 修正一些常见的翻译问题
                    result = self.post_process_translation(result)
                    return result
                time.sleep(delay)
            except Exception as e:
                logger.warning(f"翻译尝试 {i+1} 失败: {str(e)}")
                if i < max_retries - 1:
                    time.sleep(delay)
        
        logger.error(f"翻译在 {max_retries} 次尝试后失败")
        return text
    
    def post_process_translation(self, text):
        """对翻译结果进行后处理"""
        # 修正技术术语
        tech_terms = {
            'jdk': 'JDK',
            'gui': 'GUI',
            'cli': 'CLI',
            'api': 'API',
            'dmg': 'DMG',
            'github': 'GitHub',
            'gitee': 'Gitee',
            'pyqt': 'PyQt',
            'windows': 'Windows',
            'macos': 'macOS',
            'linux': 'Linux',
        }
        
        result = text
        # 保持技术术语的正确大小写
        for term_lower, term_correct in tech_terms.items():
            result = re.sub(rf'\b{term_lower}\b', term_correct, result, flags=re.IGNORECASE)
        
        # 确保句子首字母大写
        result = result[0].upper() + result[1:] if result else result
        
        # 修正常见的翻译问题
        result = result.replace(' the JDK', ' JDK')  # 移除不必要的冠词
        result = result.replace('the GUI', 'GUI')
        result = re.sub(r'a\s+(?:JDK|GUI|CLI|API)', lambda m: m.group(0).replace('a ', ''), result)
        
        return result

class ChangelogManager:
    """更新日志管理器"""

    def __init__(self):
        self.emoji_map = {
            'Added': '✨',
            'Changed': '🔄',
            'Fixed': '🐛',
            'Documentation': '📚',
            'Security': '🔒',
            'Improved': '⚡',
            'Other': '🔧'
        }
        self.translator = Translator()

    def translate(self, text):
        """翻译文本"""
        return self.translator.translate_with_retry(text)

    def get_emoji(self, content):
        """获取对应的 emoji"""
        content_lower = content.lower()
        for key, emoji in self.emoji_map.items():
            if key.lower() in content_lower:
                return emoji
        return '🔧'  # 默认 emoji

    def check_version_exists(self, version, file_path):
        """检查版本是否已存在于更新日志中"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 使用正则表达式检查版本是否存在
                    version_pattern = rf'## \[{version}\] - \d{{4}}-\d{{2}}-\d{{2}}'
                    return bool(re.search(version_pattern, content))
            return False
        except Exception as e:
            logger.error(f"检查版本是否存在时出错: {str(e)}")
            return False

    def get_latest_changes(self, file_path):
        """获取最新版本的更新内容"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 匹配最新版本的内容
                    latest_section = re.search(r'## \[[\d.]+\] - \d{4}-\d{2}-\d{2}\n\n(.*?)(?=\n## \[|$)', 
                                            content, re.DOTALL)
                    if latest_section:
                        return latest_section.group(1).strip()
            return None
        except Exception as e:
            logger.error(f"获取最新更新内容时出错: {str(e)}")
            return None

    def generate_changelog(self, version, changes, file_path):
        """生成更新日志"""
        try:
            # 检查版本是否已存在
            if self.check_version_exists(version, file_path):
                logger.info(f"版本 {version} 的更新日志已存在，跳过生成")
                return True

            today = datetime.now().strftime('%Y-%m-%d')
            new_content = f"\n## [{version}] - {today}\n\n"

            # 按类型分组更改
            grouped_changes = {}
            for change in changes:
                change_type = change['type']
                if change_type not in grouped_changes:
                    grouped_changes[change_type] = []
                grouped_changes[change_type].append(change['description'])

            # 生成更新内容
            for change_type, descriptions in grouped_changes.items():
                if descriptions:
                    new_content += f"### {change_type}\n"
                    for desc in descriptions:
                        emoji = self.get_emoji(change_type)
                        new_content += f"- {emoji} {desc}\n"
                    new_content += "\n"

            # 更新文件
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 在第一个版本标题之前插入新内容
                pattern = r'(## \[[\d.]+\])'
                if re.search(pattern, content):
                    content = re.sub(pattern, f'{new_content}\\1', content, 1)
                else:
                    content += new_content
            else:
                # 创建新文件
                header = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""
                content = header + new_content

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        except Exception as e:
            logger.error(f"生成更新日志失败: {str(e)}")
            return False

    def update_changelog(self, version, changes):
        """更新中英文更新日志"""
        # 更新中文更新日志
        self.generate_changelog(version, changes, 'CHANGELOG.md')
        
        # 翻译并更新英文更新日志
        en_changes = []
        for change in changes:
            en_change = change.copy()
            en_change['description'] = self.translate(change['description'])
            en_changes.append(en_change)
        
        self.generate_changelog(version, en_changes, 'CHANGELOG.en.md')
        
        # 准备并返回 README 更新内容
        return self.prepare_readme_updates(changes)

    def prepare_readme_updates(self, changes):
        """准备 README 更新内容"""
        zh_updates = []
        en_updates = []
        
        # 从中文版本生成更新内容
        for change in changes:
            if len(zh_updates) >= 6:  # 总共最多6个
                break
            emoji = self.get_emoji(change['type'])
            description = change.get('description', '')
            zh_updates.append(f"- {emoji} [{change['type']}] {description}")
            # 为英文版本翻译
            translated_description = self.translate(description)
            en_updates.append(f"- {emoji} [{change['type']}] {translated_description}")
        
        return zh_updates, en_updates

def update_readme_files(version, updates_zh, updates_en):
    """更新 README 文件"""
    try:
        # 更新中文版 README
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新版本徽章
        version_badge_pattern = r'!\[Version\]\([^)]+\)'
        new_version_badge = f'![Version](https://img.shields.io/badge/version-{version}-blue)'
        if re.search(version_badge_pattern, content):
            content = re.sub(version_badge_pattern, new_version_badge, content)
        
        # 更新最新版本部分（中文）
        version_section = f"""## 最新版本

v{version} 的主要更新：
{chr(10).join(updates_zh)}

完整的更新历史请查看 [CHANGELOG.md](CHANGELOG.md)"""
        
        content = re.sub(
            r'## 最新版本\n\nv[\d.]+[^\n]*\n(?:- [^\n]*\n)*\n完整的更新历史请查看[^\n]*\n',
            version_section + '\n\n',
            content
        )
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新英文版 README
        with open('README.en.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if re.search(version_badge_pattern, content):
            content = re.sub(version_badge_pattern, new_version_badge, content)
        
        # 更新最新版本部分（英文）
        version_section = f"""## Latest Version

v{version} Major Updates:
{chr(10).join(updates_en)}

For complete release notes, please check [CHANGELOG.en.md](CHANGELOG.en.md)"""
        
        content = re.sub(
            r'## Latest Version\n\nv[\d.]+[^\n]*\n(?:- [^\n]*\n)*\n[^\n]*\n',
            version_section + '\n\n',
            content
        )
        
        with open('README.en.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"Failed to update README files: {str(e)}")
        return False

def validate_release():
    """发布前验证"""
    try:
        # 检查代码风格
        logger.info("Checking code style...")
        result = subprocess.run(['black', '--check', 'src/'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("Code style check failed. Running black to format code...")
            subprocess.run(['black', 'src/'])
            logger.info("Code formatting completed.")
        
        # 检查必要文件是否存在
        required_files = [
            'config/app.json',
            'CHANGELOG.md',
            'CHANGELOG.en.md',
            'README.md',  # 中文版 README
            'README.en.md',  # 英文版 README
            'requirements/requirements.txt',
            'requirements/requirements-dev.txt'
        ]
        for file in required_files:
            if not os.path.exists(file):
                logger.error(f"Required file missing: {file}")
                return False
        
        # 检查版本一致性
        try:
            with open('config/app.json', 'r', encoding='utf-8') as f:
                config_version = json.load(f)['version']
            
            # 检查 README 中的版本号
            for readme in ['README.md', 'README.en.md']:  # 更新文件名
                with open(readme, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f'version-{config_version}-' not in content and f'Version: v{config_version}' not in content:
                        logger.warning(f"Version mismatch in {readme}")
        except Exception as e:
            logger.error(f"Failed to check version consistency: {str(e)}")
            return False
        
        # 检查 Git 仓库配置
        try:
            # 检查是否有 Gitee 远程仓库
            gitee_remote = subprocess.run(['git', 'remote', 'get-url', 'gitee'], 
                                       capture_output=True, text=True)
            if gitee_remote.returncode != 0:
                logger.error("Gitee remote repository not configured!")
                return False
            
            # 检查是否有 GitHub 远程仓库
            github_remote = subprocess.run(['git', 'remote', 'get-url', 'github'], 
                                        capture_output=True, text=True)
            if github_remote.returncode != 0:
                logger.error("GitHub remote repository not configured!")
                return False
        except Exception as e:
            logger.error(f"Failed to check Git remotes: {str(e)}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return False

def sync_with_remote():
    """同步远程仓库"""
    try:
        # 获取当前分支
        current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                     capture_output=True, text=True).stdout.strip()
        
        # 同步 Gitee
        logger.info("Syncing with Gitee...")
        subprocess.run(['git', 'pull', 'gitee', current_branch])
        subprocess.run(['git', 'push', 'gitee', current_branch])
        
        # 同步 GitHub
        logger.info("Syncing with GitHub...")
        subprocess.run(['git', 'pull', 'github', current_branch])
        subprocess.run(['git', 'push', 'github', current_branch])
        
        return True
    except Exception as e:
        logger.error(f"Failed to sync with remotes: {str(e)}")
        return False

def create_git_tag(version):
    """创建 Git 标签"""
    try:
        # 检查是否有未提交的更改
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            logger.error("There are uncommitted changes!")
            return False
        
        # 创建标签
        tag_name = f"v{version}"
        subprocess.run(['git', 'tag', tag_name])
        
        # 推送到 Gitee
        logger.info("Pushing tag to Gitee...")
        subprocess.run(['git', 'push', 'gitee', tag_name])
        
        # 推送到 GitHub
        logger.info("Pushing tag to GitHub...")
        subprocess.run(['git', 'push', 'github', tag_name])
        
        logger.info(f"Created and pushed tag: {tag_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to create git tag: {str(e)}")
        return False

def main():
    """主函数"""
    try:
        # 1. 验证发布环境
        logger.info("Validating release environment...")
        if not validate_release():
            logger.error("Release validation failed!")
            return False
        
        # 2. 同步远程仓库
        logger.info("Syncing with remote repositories...")
        if not sync_with_remote():
            logger.error("Failed to sync with remote repositories!")
            return False
        
        # 3. 获取版本类型
        version_type = input("Enter version type (major/minor/patch) [patch]: ").strip().lower() or 'patch'
        if version_type not in ['major', 'minor', 'patch']:
            logger.error("Invalid version type!")
            return False
        
        # 4. 更新版本号
        new_version = update_version(version_type)
        logger.info(f"Updated version to {new_version}")
        
        # 5. 获取更新内容
        manager = ChangelogManager()
        changes = []
        use_cursor = input("Use existing changelog from cursor? (y/N): ").strip().lower() == 'y'
        
        if use_cursor:
            # 从现有的 changelog 中读取更改
            logger.info("Reading changes from existing changelog...")
            with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找最新版本的更改
            latest_section = re.search(r'## \[[\d.]+\] - \d{4}-\d{2}-\d{2}\n\n(.*?)(?=\n## \[|$)', 
                                     content, re.DOTALL)
            if not latest_section:
                logger.error("Failed to read changes from cursor!")
                return False
            
            # 解析更改内容
            current_type = None
            for line in latest_section.group(1).split('\n'):
                if line.startswith('### '):
                    current_type = line[4:].strip()
                elif line.startswith('- '):
                    # 移除可能存在的 emoji
                    description = re.sub(r'^- [^\s]+ ', '', line).strip()
                    if description:
                        changes.append({
                            'type': current_type,
                            'description': description
                        })
        else:
            # 手动输入更改
            change_types = ['Added', 'Changed', 'Fixed', 'Documentation', 'Security']
            print("\nEnter changes (empty line to finish each section):")
            for change_type in change_types:
                print(f"\n{change_type}:")
                while True:
                    description = input("- ").strip()
                    if not description:
                        break
                    changes.append({
                        'type': change_type,
                        'description': description
                    })
        
        # 6. 更新更新日志
        logger.info("Updating changelog...")
        updates_zh, updates_en = manager.update_changelog(new_version, changes)
        
        # 7. 更新 README 文件
        logger.info("Updating README files...")
        if not update_readme_files(new_version, updates_zh, updates_en):
            logger.error("Failed to update README files!")
            return False
        
        # 8. 提交更改
        logger.info("Committing changes...")
        commit_message = f"release: v{new_version}\n\n"
        
        # 按类型分组更改
        grouped_changes = {}
        for change in changes:
            change_type = change['type']
            if change_type not in grouped_changes:
                grouped_changes[change_type] = []
            grouped_changes[change_type].append(change['description'])
        
        # 生成提交信息
        for change_type, descriptions in grouped_changes.items():
            if descriptions:
                commit_message += f"{change_type}:\n"
                for description in descriptions:
                    commit_message += f"- {description}\n"
        
        subprocess.run(['git', 'add', '.'])
        subprocess.run(['git', 'commit', '-m', commit_message])
        
        # 9. 创建标签
        logger.info("Creating tag...")
        tag_message = f"Release version {new_version}\n\n"
        
        # 获取最新版本的更新日志内容
        latest_changes = manager.get_latest_changes('CHANGELOG.md')
        if latest_changes:
            tag_message += latest_changes
        
        subprocess.run(['git', 'tag', '-a', f'v{new_version}', '-m', tag_message])
        
        # 10. 推送更改
        logger.info("Pushing changes...")
        subprocess.run(['git', 'push', 'origin', 'master'])
        subprocess.run(['git', 'push', 'origin', f'v{new_version}'])
        
        logger.info("Release process completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Release process failed: {str(e)}")
        return False

if __name__ == '__main__':
    # 配置日志
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <white>{message}</white>")
    logger.add("logs/release.log", rotation="1 MB", retention="10 days")
    
    # 执行发布流程
    success = main()
    sys.exit(0 if success else 1) 