from PyInstaller.utils.hooks import collect_all

# 收集所有loguru相关的文件
datas, binaries, hiddenimports = collect_all('loguru')

# 添加额外的隐藏导入
hiddenimports.extend([
    'loguru.handlers',
    'loguru._logger',
    'loguru._file_sink',
    'loguru._recattrs',
    'loguru._datetime',
]) 