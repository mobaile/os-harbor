# 评估与验证记录 · 2026-09-10

> **未经端到端验证，仅供源码与思路参考。本文分别记录 RAW 构想的架构与源码审查，以及早期 Ventoy 路线的代码检查；两者都不是实机安装或启动成功的证明。项目目前没有继续开发计划。本文不是安装教程，示例不是已执行的操作。当前项目定位见 [README](../README.md)，设计思路见 [CONCEPT](CONCEPT.md)。**

## RAW 构想：架构与源码审查

审查日期：2026-09-10。Omarchy 源码基线为 [`omacom/omarchy-iso` 的 `a23f8d464dcb0616a61bfaa8026e23d0533da209`](https://github.com/omacom/omarchy-iso/tree/a23f8d464dcb0616a61bfaa8026e23d0533da209)，提交时间为 2026-09-07（UTC−04:00）。本次未验证对应发布 ISO、运行时依赖和实机行为。

| 项目 | 证据与结论 | 边界 |
|---|---|---|
| 默认交互安装列表 | 源码确认：设备名前缀白名单不包含 `nbd` 或 `loop`。 | 排除直接在该界面选择 NBD 的路径；未否定所有安装入口。 |
| EFI 安装与完成检查 | 源码确认：创建 Limine 项、调整启动顺序，最终检查该项存在。 | 仅禁止固件写入不足以让流程正常完成；兼容处理未实现。 |
| 官方自动安装入口 | 上游说明支持 `cidata` 配置并跳过交互配置器。 | 不证明 NBD 分区、引导安装或完成检查成功。 |
| 文件到块设备 | loop、QEMU NBD 和 LIO 有对应文档；LIO 支持文件后端与本地 SCSI 呈现。 | 本项目未运行这些后端的 RAW 安装实验。 |
| 目标内核交接 | ZFSBootMenu 为维护 Linux 使用 kexec 提供实际架构参考。 | 不证明 OS Harbor 的 RAW 启动、硬件兼容或关机。 |
| 外置关机环境 | systemd 文档明确支持 `/run/initramfs/shutdown` 接口。 | 在内存中准备环境、不向 RAW 安装项目专用代码，是候选设计；尚未实现和测试。 |
| 完整生命周期 | 无本项目运行证据。 | 裸机安装、可写桌面、关机、冷启动、内核更新及缓存重建全部待验证。 |

具体源码行、官方资料和候选路径见[技术依据与案例审查](FEASIBILITY-EVIDENCE.md)；宏观分析与验证方法见 [CONCEPT](CONCEPT.md)。本次判断是“核心路径有技术依据，当前直接 NBD 交互安装存在不兼容，值得开展限定范围原型验证”，不能登记为安装或启动测试通过。

后续 RAW 实验应分别记录安装与运行结果，至少包含：ISO 来源及 SHA-256、安装器提交和依赖版本、测试硬件、映射后端和运行内核、是否修改安装器或镜像、非目标磁盘写入隔离结果、ESP 与固件变量前后状态、关机和冷启动结果、内核更新及缓存重建结果、证据路径。先用准备好的镜像验证运行，也不能将“裸机安装”标为通过。

## 历史 Ventoy 代码检查

以下保留早期记录；本次文档更新没有重新执行这些检查，也未新增真实部署或启动结果。

| 项目 | 结果 |
|---|---|
| Python 单元/流程测试 | 19 项通过，使用临时目录与官方链接生成器替身 |
| CLI 帮助与 PowerShell 脚本语法 | 通过 |
| 官方 VentoyVlnk 实际执行 | 待验证，工具未提供 |
| Windows VHDX 裸机启动 | 待验证，无已登记镜像 |
| Omarchy 固定 VHD 裸机启动 | 实验性、待验证 |
| GPU/网络/内核更新后重启 | 待验证 |
| 拔U盘原 Windows 直启 | 待验证，未重启 |
| ESP/BCD 前后对比 | 待验证，未进行镜像部署/启动 |

历史实验未进行真实部署或启动验证。主机检测细节和私人报告不作为公开项目资料；以下测试记录仅描述旧代码检查，不能作为新 RAW 构想的验证结果。

以下字段仅为旧 Ventoy 路线的实机记录示例，未填入真实结果。若继续该路线，应追加独立记录，不用格式检查的通过状态覆盖启动待验证状态；RAW 实验使用上文要求的字段，不沿用 Ventoy 版本字段：

```json
{"system_id":"omarchy","result":"pending","tested_at":null,"os_version":null,"kernel":null,"ventoy_version":null,"vtoyboot_version":null,"plugin_sha256":null,"gpu":null,"network":null,"cold_boot":null,"after_update_boot":null,"original_windows_boot":null,"evidence_paths":[]}
```
