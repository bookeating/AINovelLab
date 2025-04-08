# AI小说工具打包指南

本文档详细介绍了如何将AI小说工具打包为可执行文件。

## 环境准备

打包前需要安装以下工具和依赖：

1. Python 3.8+
2. PyInstaller 5.13.0+
3. 项目所有依赖包（requirements.txt中列出）

## 基本打包步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install pyinstaller==5.13.2
```

### 2. 使用spec文件打包

项目根目录已包含预先配置好的`AINovelLab.spec`文件，直接使用此文件进行打包：

```bash
pyinstaller AINovelLab.spec
```

打包后的文件将生成在`dist/AINovelLab`目录下。

### 3. 打包成ZIP压缩包

为方便分发，将生成的目录打包为ZIP文件：

```bash
# Windows (PowerShell)
Compress-Archive -Path dist/AINovelLab -DestinationPath dist/AINovelLab.zip

# Linux/Mac
cd dist && zip -r AINovelLab.zip AINovelLab
```

## spec文件说明

`AINovelLab.spec`文件包含了打包配置，主要设置如下：

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['run.py'],  # 入口脚本
    pathex=[],
    binaries=[],
    # 需要包含的数据文件和目录
    datas=[
        ('resources', 'resources'), 
        ('data', 'data'), 
        ('config', 'config'), 
        ('api_keys.json', '.'), 
        ('src', 'src'), 
        ('src/gui', 'gui')
    ],
    # 隐式导入的模块
    hiddenimports=[
        'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui', 
        'ebooklib', 'ebooklib.epub', 'bs4', 'bs4.builder', 
        'tqdm', 'requests', 'lxml'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
```

## 自定义打包配置

如果需要修改打包配置，可以编辑`AINovelLab.spec`文件：

### 添加新的数据文件

如果你添加了新的资源文件或目录，需要更新`datas`列表：

```python
datas=[
    # 现有配置
    ('your_new_folder', 'destination_folder'),
    ('your_new_file.txt', '.'),
],
```

### 添加新的依赖模块

如果添加了新的依赖模块，可能需要在`hiddenimports`中添加：

```python
hiddenimports=[
    # 现有导入
    'your_new_module',
],
```

## 常见问题解决

### 1. 找不到模块或文件

如果打包后运行时报错找不到某模块或文件，可能是忘记添加到`datas`或`hiddenimports`中：

```python
# 添加缺失的模块
hiddenimports=['missing_module'],

# 添加缺失的文件
datas=[('missing_file.txt', '.')],
```

### 2. 动态导入问题

如果程序使用动态导入（如使用`importlib`），确保这些模块也添加到`hiddenimports`：

```python
hiddenimports=['module.that.is.dynamically.imported'],
```

### 3. 压缩exe文件

默认配置使用UPX压缩，如果需要禁用：

```python
exe = EXE(
    # ...
    upx=False,  # 设置为False禁用UPX压缩
    # ...
)
```

## 跨平台打包

### Windows打包

默认配置适用于Windows系统，无需额外修改。

### macOS打包

在macOS上打包需要注意以下几点：

1. 可能需要修改某些路径分隔符
2. 考虑添加`target_arch`参数以支持特定架构

```python
exe = EXE(
    # ...
    target_arch='x86_64',  # 或 'arm64' 用于M1/M2 Mac
    # ...
)
```

### Linux打包

Linux打包通常较为简单，但可能需要处理库依赖问题：

```python
exe = EXE(
    # ...
    # 可能需要添加特定于Linux的设置
    # ...
)
```

## 版本号管理

每次打包前，请更新`src/version.py`文件中的版本信息：

```python
VERSION = "x.y.z"
VERSION_INFO = (x, y, z)
BUILD_DATE = "YYYY-MM-DD"
BUILD_TYPE = "release"  # 或 "beta", "alpha", "dev"
```

## 打包后检查

打包完成后，建议进行以下检查：

1. 确保`AINovelLab.exe`能正常启动
2. 测试所有主要功能
3. 检查API密钥配置是否可正常修改
4. 检查资源文件是否正确包含
5. 验证程序在没有Python环境的计算机上能否运行

## 最佳实践

1. 每次发布前清理`dist`和`build`目录
2. 使用版本控制管理spec文件的变更
3. 为每个版本创建发布说明
4. 保持打包环境与开发环境一致
5. 考虑使用CI/CD自动化打包流程 