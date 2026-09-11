# 技术依据与案例审查 · 2026-09-10

> **本文记录具体组件和系统的资料、源码及候选适配方向，不是安装教程，也不是实机验证结果。项目宏观设计见 [CONCEPT](CONCEPT.md)，实际检查范围见 [VALIDATION](VALIDATION.md)。**

主体架构不绑定具体系统。这里以已查证的技术和案例说明实现依据与限制；某个案例的不兼容不等于整个架构不可行，组件能力也不等于完整方案已成立。

## 1. 已查证的技术机制

本轮技术研究主要基于 Linux 的存储和早期用户空间机制，以及 UEFI 的启动接口。它不构成对其他内核或启动框架的可行性证明。

| 机制 | 官方依据 | 对本项目的意义与限制 |
|---|---|---|
| loop | [losetup][losetup] 支持文件映射和分区扫描。 | 可作为运行阶段的候选后端；未验证完整 RAW 根文件系统启动。 |
| QEMU NBD | [官方文档](https://www.qemu.org/docs/master/tools/qemu-nbd.html)支持将镜像连接成 Linux NBD 块设备。 | 可作为安装候选目标；设备可见不等于安装器接受。 |
| LIO FILEIO / 本地 loopback | [targetcli 手册][targetcli]支持文件后端及本机 SCSI 呈现。 | 可研究减少安装器设备命名差异；不解决 EFI 写入与权限边界。 |
| 早期存储准备 | [initrd 文档](https://docs.kernel.org/admin-guide/initrd.html)与 [GRUB 说明][grub-loopback]描述根设备准备的职责。 | 目标内核必须建立自己的存储映射，不能继承引导器的文件读取能力。 |
| 内核交接 | [ZFSBootMenu][zfsbootmenu]采用维护 Linux 加载目标内核并通过 kexec 交接。 | 这是交接架构的实际参考，不是本项目 RAW 路线的验证。 |
| 外置关机环境 | [systemd initrd 接口][systemd-initrd]支持返回早期环境清理存储。 | 为镜像内不安装项目专用 hook 提供候选实现依据。 |

## 2. 安装器案例：Omarchy ISO

QEMU NBD 可在 Linux 中把磁盘镜像绑定为 `/dev/nbdX`。这提供候选安装目标，但安装器的设备筛选、分区命名、引导安装和自动重启行为仍需逐项验证。[QEMU NBD 官方文档](https://www.qemu.org/docs/master/tools/qemu-nbd.html)

**2026-09-10 源码审查发现，默认交互式 Omarchy 安装流程不能直接沿用上述 NBD 路径。** 审查固定在 `omacom/omarchy-iso` 提交 `a23f8d464dcb0616a61bfaa8026e23d0533da209`（提交时间为 2026-09-07，UTC−04:00）；没有据此认定某个发布 ISO 使用完全相同的代码和依赖。

| 源码事实 | 对方案的影响 |
|---|---|
| `disk_form()` 按磁盘类型及设备名前缀筛选，白名单不包含 `nbd` 或 `loop`。[设备筛选源码][omarchy-disks] | `/dev/nbd0` 即使已成功连接，也不会出现在默认交互安装列表中。 |
| EFI 安装函数调用 `efibootmgr` 创建 Limine 启动项、调整启动顺序；安装完成检查还要求存在 Limine 项。[EFI 安装源码][omarchy-efi]、[完成检查源码][omarchy-validation] | 单纯拒绝固件写入会使该流程报错；放任写入又会改变原启动状态，必须设计兼容处理。 |
| 官方支持通过标为 `cidata` 的介质提供自动安装配置，跳过交互配置器。[自动安装说明][omarchy-autoinstall] | 可以研究通过官方配置指定目标，但这只绕过界面，不证明后续分区和安装接受 NBD。 |

另一条候选路径是 `RAW → LIO FILEIO → tcm_loop → 本机 SCSI 块设备`。LIO 支持以文件作为后端，并通过本地 loopback 将存储对象呈现为 SCSI 设备。因此可研究以 `/dev/sdX` 形式提供安装目标，减少设备命名差异；是否能完成 Omarchy 安装仍需实测。这里的 `tcm_loop` 与 Linux 的 `/dev/loopX` 是不同机制，也不涉及虚拟机安装。[targetcli 官方手册][targetcli]

NBD 和 LIO 都只是候选后端。官方自动安装配置或本地 SCSI 映射不会自动解决 EFI 注册与安装完成检查，也不能代替物理盘写入隔离。若最终需要修改安装器，应明确记为对“原版安装器”约束的妥协，不能用镜像内没有专用代码来掩盖这项变化。

安装环境的交接也必须具体化：在维护 Linux 中建立映射后，另行启动 ISO 的内核不会继承这些映射。候选实现需要在选定的安装内核中先建立映射，再运行安装器，或者在维护内核下提供安装器需要的用户空间。前者要解决 Live 环境准备，后者要验证设备、服务及固件环境兼容；不能把“启动原版 ISO”和“运行其中的原版安装器”视为同一件事。

安装环境需要保护实际物理盘和固件变量。把危险磁盘从界面隐藏并不构成写入隔离；仓库所在盘还必须由维护层正常访问，因此不能简单假设“把所有真实盘设为只读”就解决问题。设备权限、命名空间和安装器权限边界都是待研究内容。

正式验证需要同时固定 ISO 校验值、安装器版本和实际依赖版本。以上源码事实排除了默认交互流程直接使用 NBD 的简单路径，不构成对所有安装入口或其他发行版的否定。

## 3. 启动、关机与生命周期适配

以下是基于本轮所查 Linux 机制的候选实现说明；没有在本项目中运行验证。

### 启动路径

外部环境读到镜像以后，目标内核仍需要自己识别物理存储、挂载仓库、建立文件到块设备的映射，再发现真正的根分区。loop 支持文件到块设备的映射和分区扫描；initramfs 可在根切换前完成这些准备。GRUB 也明确指出，引导器能读取镜像，并不代表目标系统自动能找到自己的根文件系统。[losetup 文档][losetup]、[Linux initrd 文档](https://docs.kernel.org/admin-guide/initrd.html)、[GRUB loopback 启动说明][grub-loopback]

候选办法是从镜像提取目标内核和 initramfs，在外部构建适配副本，再由维护 Linux 通过 kexec 交接到目标内核。ZFSBootMenu 已采用维护 Linux 查找目标内核和 initramfs、通过 kexec 启动的架构，提供了这一交接方式的实际参考；它没有证明本项目的 RAW 映射和关机链路。硬件重新初始化、固件状态和驱动兼容仍需实测。也可以研究由外部引导器直接加载目标内核，两种方式均未在本项目实现。[ZFSBootMenu 官方说明][zfsbootmenu]

Linux 的 initramfs 格式支持组合归档，但这不意味着附加脚本会自动运行。实现仍需明确入口和执行顺序，并针对目标 initramfs 框架适配，加载与目标内核版本匹配的存储、ext4、loop 和根文件系统模块。[Linux initramfs 格式文档](https://docs.kernel.org/driver-api/early-userspace/buffer-format.html)

这条候选路径可基于标准存储驱动构建，不以开发新的项目专用内核驱动为前提；但目标内核仍须具备所需功能或可取得匹配模块。加密根分区、Btrfs 子卷、swap、休眠和 Secure Boot 都会增加条件，不宣称一套外部片段能启动任意 Linux。

### 运行与关机路径

进入目标系统后，外层仓库及映射必须持续可用。systemd 提供标准接口：若存在 `/run/initramfs/shutdown`，关机阶段可以切换到该目录中的环境，执行存储清理；initramfs 负责事先准备可用的目录、程序和依赖。[systemd initrd 接口][systemd-initrd]

基于该接口，可研究由外部 initramfs 在内存中准备关机环境，保留所需挂载，并在退出目标系统后释放存储。这不要求把 OS Harbor 专用 hook 持久安装到 RAW 内，但也不是放入一个脚本就自动可靠。

```text
目标系统停止服务，释放 swap 等使用者
    → 切回内存中的关机环境
    → 卸载镜像内部各文件系统
    → 关闭内层加密映射（如有）
    → 释放 loop 映射
    → 同步并卸载外层仓库
```

上述顺序是待实现的依赖关系，不是已测试的关机脚本。必须验证根切换前后挂载如何保留、systemd 如何处理这些挂载、清理失败如何报告，以及连续关机和冷启动后的数据一致性。运行阶段采用 loop 可以避免依赖用户态 NBD 服务持续存活；安装阶段采用哪种后端则可独立验证。

### 生命周期

备份和克隆应在离线状态复制完整 RAW。系统可写运行是预期行为，不应仅因文件修改时间改变就认为镜像失效。不在镜像内安装更新 hook 的候选办法，是外部环境在启动前重新识别实际内核、模块和启动参数，并重建必要缓存。目标系统更新 `/boot` 或内部 ESP 时，应写入 RAW 内对应的原始文件系统，外部副本仍只作缓存；缓存回退不能撤销镜像内部更新。

克隆会复制内部 UUID，不能全局按 UUID 随意寻找根设备；应限定在本次选中镜像的映射设备内。并发写入、空间不足、复制中断和断电恢复也必须纳入未来实现。上述管理行为目前均未实现。

第一轮验证可预分配 RAW 空间，减少镜像内部仍有空闲、外层仓库却先耗尽的变量；这不替代空间检查或故障恢复。CPU、GPU 直接使用真实硬件也不代表存储性能等同物理分区，仍需测量额外映射和文件系统层次下的延迟、随机读写和持续写入。

## 4. 仓库与主系统入口的技术条件

以下保留针对当前候选存储和主系统环境的技术分析，不将这些选择写成宏观架构的唯一实现。

候选布局为 ext4 仓库中的 `/systems/<系统名>.raw`。初步研究可使用独立测试磁盘与独立 USB 引导环境，避免一开始就处理 Windows 分区缩容。安装维护任务、结果和可重建索引可放在双方能访问的交换区；镜像路径应以仓库 UUID 和相对路径识别，不能依赖固定盘符或设备编号。

Windows 不必直接写 ext4：可把工作排入 Linux 维护环境，在下一次启动执行。这牺牲即时管理体验，但能避免自制 Windows 文件系统写入驱动。WSL 也不是所有布局的通用答案：其物理盘挂载需要附加整个磁盘，不能直接挂载仍被 Windows 占用的启动盘上的分区。[微软 WSL 文档](https://learn.microsoft.com/en-us/windows/wsl/wsl2-mount-disk)

UEFI 的 `BootNext` 提供一次性启动机制，规范要求在交接给指定启动项前删除该变量。这为保留 Windows 默认启动顺序提供基础；Windows 侧设置、固件实际行为和失败后的返回仍需验证。[UEFI Boot Manager 规范](https://uefi.org/specs/UEFI/2.11/03_Boot_Manager.html)

## 5. 证据与复现边界

本次检查是资料阅读和源码审查，没有执行 RAW 安装、裸机启动、固件写入或关机验证。上游源码提交不能代替发布 ISO 及其实际依赖的校验值。

后续试验应固定目标版本与硬件，按 [CONCEPT](CONCEPT.md) 的两条验证线分别取得证据，再完成同一 RAW 的实机安装与运行。当前案例发现不能直接推广到其他发行版、其他版本或其他安装入口。

早期路线使用的 [Ventoy / vtoyboot](https://www.ventoy.net/en/plugin_vtoyboot.html)另有镜像准备要求，其代码检查也不能验证当前 RAW 架构。OS Harbor 与本文引用的上游项目没有隶属或背书关系。

[omarchy-disks]: https://github.com/omacom/omarchy-iso/blob/a23f8d464dcb0616a61bfaa8026e23d0533da209/configs/airootfs/root/configurator#L864-L893
[omarchy-efi]: https://github.com/omacom/omarchy-iso/blob/a23f8d464dcb0616a61bfaa8026e23d0533da209/configs/airootfs/usr/share/omarchy-iso/orchestrator/phases_impl.py#L400-L474
[omarchy-validation]: https://github.com/omacom/omarchy-iso/blob/a23f8d464dcb0616a61bfaa8026e23d0533da209/configs/airootfs/usr/share/omarchy-iso/orchestrator/phases_impl.py#L1644-L1687
[omarchy-autoinstall]: https://github.com/omacom/omarchy-iso/blob/a23f8d464dcb0616a61bfaa8026e23d0533da209/README.md#autoinstall
[targetcli]: https://raw.githubusercontent.com/open-iscsi/targetcli-fb/master/targetcli.8
[losetup]: https://man7.org/linux/man-pages/man8/losetup.8.html
[grub-loopback]: https://www.gnu.org/software/grub/manual/grub/html_node/Loopback-booting.html
[systemd-initrd]: https://systemd.io/INITRD_INTERFACE/
[zfsbootmenu]: https://zfsbootmenu.org/en/latest/
