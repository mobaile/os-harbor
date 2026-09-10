# OS Harbor：把 Linux 系统当作一个文件来管理

> **这是一个未经验证的多系统管理构想，不是可用的安装或启动工具。核心的裸机安装、单文件启动及系统兼容性均未验证。仓库中的代码仅为早期实验，不代表方案可行，不应直接用于重要设备。本项目仅供思路交流与参考，目前没有继续开发计划。**

**Unverified concept, not a working installer or boot manager.** Bare-metal installation, image boot and compatibility have not been validated. The code is an early experiment, shared for reference and inspiration. No further development is currently planned.

## 为什么留下这个项目

多系统安装通常意味着为每个系统划分空间、处理引导和承担恢复成本。这里想探索另一种体验：保留现有 Windows，把其他系统当作文件来安装、选择、备份和移除。

理想状态是：**安装器眼里是一块硬盘，用户眼里始终是一个文件。** 希望以后有类似想法的人能借鉴这里的思路、看到尚未解决的问题，而不必把它误认为现成方案。

## 核心思路

- 现有 Windows 保持原有安装方式，并作为默认启动系统。
- 所有 Linux 共用一个 Linux 文件系统仓库分区，例如 ext4；不为每个系统单独划一个物理分区。
- 每个 Linux 对应一个标准 GPT RAW 磁盘文件，包含系统自己的引导分区、根文件系统和用户数据。
- 裸机安装环境将 RAW 映射为块设备，让安装器直接安装进去；以后从**同一文件**裸机运行，而不是转换成另一个运行格式。
- 外部引导环境准备存储映射和早期启动内容；镜像内部不安装 OS Harbor 专用驱动、服务或 hook。
- Windows 管理入口选择系统并安排一次性启动；备份、克隆和恢复围绕离线 RAW 文件进行。

```text
物理磁盘
├── 现有 Windows 与原有引导
└── 公共 Linux 镜像仓库（设想为 ext4）
    └── systems/
        ├── Omarchy.raw
        ├── Ubuntu.raw
        └── Fedora.raw

独立引导／维护环境
└── 找到所选 RAW → 启动该系统自己的内核 → 建立映射 → 进入系统
```

图中的多个发行版仅用于表达愿景，**不是支持列表**。Omarchy 也没有通过本项目的端到端验证。

“一个文件”指完整系统状态保存在 RAW 中。引导环境、任务索引、日志和可重建的启动缓存仍在外部；这不意味着 UEFI 天然可以直接运行任意磁盘文件。

## 哪些是现成能力，哪些只是设想

| 层次 | 已知能力或当前状态 |
|---|---|
| 标准组件 | Linux loop、QEMU NBD、GPT 和 initramfs 提供了组成这个方向的部分基础能力，见构想文档中的官方参考资料。 |
| 项目设想 | 原版裸机安装器直接安装进 RAW，外置适配后从同一文件运行。整个组合未验证。 |
| 未解决问题 | 安装器是否接受目标设备、物理磁盘写入隔离、目标内核与模块匹配、根切换和关机顺序、更新后启动、加密与硬件兼容。 |
| 现有实验代码 | 围绕较早的 NTFS + 固定 VHD + Ventoy 路线，涉及登记、链接构建、配置部署和一致性检查。 |
| 缺失实现 | RAW 仓库、裸机安装隔离、外置启动适配、Windows 图形管理器和一次性启动编排均未实现。 |

将普通文件映射为块设备，不等于安装器一定接受它；拼接 initramfs，不等于启动逻辑自动完成。代码测试或配置校验通过，也不等于真实系统可以启动。

## 从哪里阅读

- **[完整构想、方案演变与研究难题](docs/CONCEPT.md)**：本仓库主要希望分享的内容。
- [历史验证记录](docs/VALIDATION.md)：说明早期测试的实际边界。
- [历史 CLI 参考](docs/FULL-CLI-REFERENCE.md)、[历史镜像准备笔记](docs/IMAGE-PREPARATION.md)、[历史部署恢复说明](docs/RECOVERY.md)、[历史依赖记录](docs/DEPENDENCIES.md)：用于理解旧实验，不是新构想的安装教程。
- `osharbor/`、`scripts/`、`tests/`：保留的早期实验代码，见 [代码说明](docs/EXPERIMENTAL-CODE.md)。

项目没有已验证的安装步骤，没有可用版本，也不承诺后续交付。这里保留的是一个问题、一种可能的架构，以及可供后来者继续研究的线索。
