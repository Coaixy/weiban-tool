# Weiban-Tool
基于Python打造的微伴辅助工具，支持自动登录、自动刷课、题库提取、自动答题等功能。

## 注意事项
仅供学习参考, 不能用于非法用途，请在下载后24h内删除。

[![仓库访问次数](https://badges.toozhao.com/badges/01J4X431GX8JJ8F43S0ES0ANXY/green.svg)]( "")

## 使用方法

### 前提条件
安装有Python3.11-3.12版本 可以通过官网: https://www.python.org/downloads/ 下载安装
也可以通过群文件的安装包进行安装 (勾选path选项)

电脑的Vc支持库需要完整 (遇到不完整情况可以去群文件安装)

### 下载源码
https://github.com/Coaixy/weiban-tool/releases 

下载最新的Source Code 并解压到一个文件夹

### 安装依赖

进入解压后的文件夹，按住shift键，点击鼠标右键，选择在此处打开命令窗口

输入以下命令安装依赖

````shell
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
pip config set install.trusted-host mirrors.aliyun.com
pip install -r requirements.txt
````

### 运行工具

在命令窗口输入以下命令运行工具

````shell
python main.py
````

### 使用工具
根据提示输入相关的信息

考试时间为最终的考试时间不是你的考试项目的总时间

例如：输入的考试时间为240 你最终的考试时间为4分钟

### 注意

在使用工具的时候请不要关闭命令窗口，否则程序会停止运行

考试会有等待时间请耐心等待


## 完成情况
- [x] 自动登录
- [x] 自动刷课
- [x] 题库提取
- [x] 自动答题
- [ ] 网页版

## 贡献者

<img src="https://contrib.rocks/image?repo=coaixy/weiban-tool" />

有问题请及时反馈

群号：443195213

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=coaixy/weiban-tool&type=Date)](https://star-history.com/#coaixy/weiban-tool&Date)
