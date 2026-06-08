<p align="center">
  <img src="./images/favicon.png" width="120" alt="BlackPotBPanel V2" />
</p>

<p align="center">
  <a href="https://python.org/"><img src="https://img.shields.io/badge/python-%3E=3.10.x-green.svg" /></a>
  <a href="https://nodejs.org/zh-cn/"><img src="https://img.shields.io/badge/node-%3E%3D%2018.0.0-brightgreen" /></a>
</p>



# BlackPotBPanel V2
BlackPotBPanel 是一款仿照BT面板基于vue+fastapi开发的linux管理面板，写的比较垃圾，只实现了一些基本功能，后续可能会继续完善。

## 演示环境
(https://demo.panel.blackpotbp.cc)

账号：admin
密码：admin@123

## 环境要求
- Python 3.10 及以上版本
- 主流操作系统支持
--------------
| 操作系统 | 是否支持 | 
|-----|-----|
| Ubuntu 18.04+ | ✅ |
| Ubuntu 20.04+ | ✅ |
| Ubuntu 22.04+ | ✅ |
| Ubuntu 24.04+ | ✅ |
| RedHat 8+ | ✅ |
| CentOS 8+ | ✅ |
| CentOS Stream 8+ | ✅ |
| CentOS Stream 9| ✅ |
| CentOS Stream 10| ✅ |
| Rocky Linux 8+ | ✅ |
| Rocky Linux 9+ | ✅ |
| Rocky Linux 10+ | ✅ |
| Debian 12.0+ | ✅ |
| Debian 13.0+ | ✅ |
| AlmaLinux 8+ | ✅ |
| AlmaLinux 9+ | ✅ |
| AlmaLinux 10+ | ✅ |
| kylin-v10| ✅ |
| openEuler-24.03 | ✅ |
| uos-server-20.04 | ✅ |
| AnolisOS-8.0+ | ✅ |
| AnolisOS-23.0+ | ✅ |
| NingOS-v3 | ✅ |
| OpenCloud 9 | ✅ |
--------------
其余操作系统可尝试手动安装

 
## 一键安装脚本

### 国内
```bash
bash -c "$(curl -sSL https://gitee.com/ssgghshs/blackpotbpanel-v2/raw/master/install/install.sh)"
```

### 国外
请确保已添加github的镜像加速，否则会报错
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/ssgghshs/blackpotbpanel-v2/master/install/install2.sh)"
```

## 手动安装
请提前安装python3.10及以上版本，并创建好python的虚拟环境

### 前端
请提前安装nodejs 18及以上版本
1. 克隆仓库
```bash
cd blackpotbpanel-v2/web
```
2. 安装依赖
```bash
npm install
```
3. 运行项目
```bash
npm run dev
```
4. 打包到后端运行
```bash
npm run build
```
将dist文件的内容复制到backend目录下的web目录下，使用
__init__.py.prod文件将
__init__.py.prod改为__init__.py

``` bash
mv ./dist /opt/blackpotbpanel-v2/backend/
```



### 后端
1. 克隆仓库
```bash
git clone https://gitee.com/ssgghshs/blackpotbpanel-v2.git
cd blackpotbpanel-v2/backend
```
2.创建python虚拟环境
```bash
cd /opt/blackpotbpanel-v2
python3 -m venv venv
```

2. 安装依赖
```bash
cd /opt/blackpotbpanel-v2/backend
../venv/bin/pip install -r requirements.txt
```
3. 临时运行项目
```bash
../venv/bin/python main.py
```
4. 永久运行项目
```bash
cp Blackpotbpanel.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable Blackpotbpanel
systemctl start Blackpotbpanel
```


## 界面展示
### 登录功能
![登录界面](images/login.png)
### 首页功能
![首页功能](images/home.png)
### 容器管理，仅支持docker
![容器管理](images/docker.png)
![容器列表](images/containers.png)
![镜像列表](images/images.png)
![网络列表](images/networks.png)
![卷列表](images/volumes.png)
![compose列表](images/compose.png)
![容器宿主机列表](images/containerHost.png)
### 终端功能
![终端功能](images/cmd.png)
### 主机管理
![主机管理](images/host.png)
### 文件传输
![文件传输](images/fileTransfer.png)
### 定时任务
![定时任务](images/crontab.png)
### 脚本库
![脚本库](images/script.png)
### 文件管理
![文件管理](images/file.png)
### 数据库管理
![mysql管理](images/mysql.png)
![postgresql管理](images/pgsql.png)
![sqlite管理](images/sqlite.png)
### 防火墙管理
![防火墙管理](images/firewall.png)
### SSH服务
![SSH服务](images/service.png)
### WAF管理(Beta版本)
![WAF管理](images/waf.png)
### 日志管理
![日志管理](images/log.png)
### 系统设置
![系统设置](images/setting.png)

## 待完善功能
- 数据库管理，需要新增支持postgresql/redis/mongodb,以及mysql/sqlite的管理功能的完善
- WAF管理，有待重构，以及地区限制功能
- 防火墙/SSH管理需要新增接入Fail2ban
- 远程主机文件管理功能，需要新增上传/下载/删除/移动/重命名/创建目录/创建文件等功能


## 国际化
- 支持中文/英文/日文/韩文







