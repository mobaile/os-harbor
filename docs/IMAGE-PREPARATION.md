# 镜像制作与实机验收

## 已发现安装介质

2026-09-10 只读扫描 `D:\VMwareMachine`：

| 类型 | 文件 | 大小（字节） |
|---|---|---:|
| Omarchy | `D:\VMwareMachine\omarchy-4.0.2.iso` | 6227752960 |
| Windows | `D:\VMwareMachine\zh-cn_windows_11_business_editions_version_25h2_updated_aug_2026_x64_dvd_eab7a27b.iso` | 8846692352 |

版本来自文件名，尚未验证 ISO 内部版本、发布者签名或官方校验和。ISO 不是已安装系统，不能直接登记为 VHD。另有现存 Omarchy VMware 虚拟机（UEFI、分卷 VMDK、有挂起状态文件）；不覆盖其虚拟磁盘，不直接复制挂起中的磁盘作为一致性镜像，也不把 WSL 的 ext4.vhdx 当 Windows 镜像。

## Windows 11

首选在隔离的 UEFI 虚拟机中创建全新 VHDX（建议 128 GiB），只连接该测试虚拟磁盘和上述安装 ISO，不连接主机原始磁盘。可使用支持 VHDX 的 Hyper-V 第二代虚拟机；没有该功能时先配置受支持的虚拟机工具，不自动启用系统特性。

安装 Windows 11，按 ISO 中实际提供的版本选择，完成首次启动后正常关机，不保存运行状态。不要将宿主机 ESP 映射给虚拟机。镜像内部的 ESP 是镜像文件内容，与主机 ESP 分开。安装过程中不要启用镜像内部 BitLocker；若安装自动加密，先在测试系统内确认解密完成。

关机并解除挂载后运行 `scripts/Inspect-Image.ps1 -Path <VHDX路径>`，登记到工具。VHDX 文件头检查只检测格式，不保证 Windows 安装正确。使用 Windows 插件实际验证裸机启动，遇到兼容性问题保存报错与插件版本。

Microsoft 的原生启动文档说明了 VHDX 部署过程，但其中的主机分区重建和 BCD 写入步骤不属于本项目：
https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/boot-to-vhd--native-boot--add-a-virtual-hard-disk-to-the-boot-menu

## Omarchy（实验性）

1. 用支持固定 VHD 的虚拟机工具创建**新**的 96 GiB 固定 VHD，在安装前选择 UEFI。官方 vtoyboot 文档使用 VirtualBox；首轮复现采用该路线。不要使用动态 VHD、VHDX、差分盘或虚拟机快照。
2. 虚拟机仅连接新 VHD 和 Omarchy ISO。按照安装器实际要求分配 CPU、内存和网络；所有分区操作限于这块虚拟磁盘。记录安装器版本、引导器、内核及 initramfs 工具。若安装器拒绝该环境，记录失败，不冒充支持。
3. 安装后进入镜像中的 Linux。下载官方 vtoyboot 发行包并完整解压；验证发布版本与包校验和，再记录其中 vtoyboot.sh 的 SHA256。
4. 将项目 `scripts/Prepare-Omarchy.sh` 复制到 guest，在 guest 内执行 `sudo bash Prepare-Omarchy.sh /实际目录/vtoyboot.sh <脚本SHA256>`。脚本调用官方脚本并保存日志；无法判断你是否在 guest，执行位置必须核实。
5. 正常关机，解除虚拟磁盘挂载，给文件追加 `.vtoy`：最终 `Omarchy.vhd.vtoy`。登记、生成链接并部署。
6. 裸机验证图形桌面、GPU、网络、声音、存储；记录与虚拟机启动的区别。更新内核/驱动后，在系统内重新运行准备脚本，再关机并重建链接。不能保证 Omarchy 与 vtoyboot 兼容。

官方约束：https://www.ventoy.net/en/plugin_vtoyboot.html

## 实机验收

开始前运行 `scripts/Inspect-Host.ps1` 保存分区、BCD、固件启动项报告。拒绝访问必须标记为未采集，不能视作未变化。ESP 文件哈希需另行只读采集；该脚本不自动挂载 ESP。

保存工作后由使用者通过主板临时启动菜单选择U盘，分别启动镜像。每个系统记录：系统/内核/驱动版本、Ventoy/插件版本、冷启动、桌面、网络、GPU、关机、再次启动、错误日志。完成后拔掉U盘，确认原 Windows 直启，并重新采集主机报告比较。实机重启会中断当前工作，本项目不自动触发。

若主机 Secure Boot 或镜像存储卷加密阻止链路，记录具体状态并单独确定兼容路线，不自动更改。克隆/备份只在镜像离线后进行完整文件复制，首版不提供在线快照。
