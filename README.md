# OS Harbor：让 AI 帮你在现有 Windows 电脑上运行 Omarchy

现在只做一件事：**保留已经装好的 Windows，在 SSD 上准备一个 Omarchy 系统镜像，由 AI 完成尽可能多的准备和部署工作，最后通过 Ventoy U 盘启动 Omarchy。**

使用 Windows 时照常启动电脑；使用 Omarchy 时插入 U 盘，从临时启动菜单进入 Omarchy。Windows 无需重装、克隆或制作镜像，也不需要 Windows VHD 启动插件。

本说明采用项目现有的“SSD 镜像 + U 盘引导”路线。它需要重启切换系统，不能在 Windows 桌面里同时运行裸机 Omarchy。准备阶段的虚拟机用于安装和维护镜像，最后的目标是在真实硬件上运行。

**当前状态：登记、构建链接、部署和一致性校验已有代码；从零自动制作 Omarchy 镜像、跨重启接管和真实硬件启动尚未实现或验证。下面是简化后的执行说明，不能理解成已经存在一个全自动安装按钮。** 本次调整说明，不执行系统安装或重启。

## 1. 你只需要给 AI 这一段任务

> 我当前在一套正常使用的 Windows 上。请按本项目 README，只准备一个 Omarchy 系统，沿用 SSD 镜像加 Ventoy U 盘引导方案，不处理 Windows 镜像。先检查当前电脑和已有资源，尽量复用，不覆盖现有虚拟机。自动完成能完成的检查、官方文件获取与校验、独立镜像制作、Linux 内启动准备、登记、构建和 U 盘部署。普通操作直接继续，不要每一步都问我；缺少控制能力时说明具体卡在哪里，只把必要的一步交给我。需要擦除未授权设备、调整主机固件、输入个人密码或重启时，再给我明确的操作说明。每完成一个阶段保存真实结果和下一步，重启前保存恢复工作所需的路径和日志。最终以 Omarchy 真实启动、基本硬件可用、关机后原 Windows 能直接启动为验收标准。

AI 开始后先做检查，不需要你提前学会全部命令。首次检查结束应给你一句明确结论，例如：“现有 U 盘可直接使用，缺少固定 VHD；接下来创建独立测试镜像。”资源路径能够自动发现时直接填写，不能确定是哪块 U 盘时才请你指出设备。

这段话是交给 AI 的工作指令，不是 CLI 支持的新子命令。下面说明每个阶段到底做什么、谁来做、完成的标准是什么。

## 2. 最终电脑会是什么样

```text
现有 Windows：继续保留，平时照常使用
    │
    └─ SSD 的 NTFS 卷
         └─ Systems/Omarchy.vhd.vtoy   Omarchy 系统、应用和个人文件

Ventoy U 盘
    └─ Omarchy 启动链接和菜单         指向 SSD 上的系统镜像
```

镜像是一个包含完整 Linux 系统的虚拟硬盘文件，不是 ISO 安装包。Omarchy 运行后的文件和设置会写回这个镜像，不是重启就丢失的试用环境。U 盘保存的是引导入口，不是整份系统备份；源 SSD 必须保持连接。

第一轮只保留一个 Omarchy 条目，使用独立登记表 `state/omarchy.json`，避免混入以前的 Windows 条目。代码里的 Windows 功能暂时保留，当前任务不使用。

建议资源如下，AI 会根据实际剩余空间和硬件调整：

| 资源 | 本次用途 |
|---|---|
| 现有 Windows、Python 3.11+、PowerShell | 运行准备和部署命令 |
| 本地有盘符的 NTFS 卷 | 保存镜像，例如 `D:\Systems`；与 Ventoy 数据卷分开 |
| 新建固定 VHD，建议 96 GiB | Omarchy 安装目标；固定盘会立即占用接近完整容量 |
| Omarchy 官方 ISO | 仅用于把系统安装到新 VHD |
| 能使用固定 VHD 的 UEFI 虚拟机环境 | 制作和维护 Linux 镜像，优先检查已有环境 |
| Ventoy U 盘、官方 VentoyVlnk | 从 U 盘启动 SSD 镜像 |
| 官方 vtoyboot | 在镜像内准备 Linux 启动链路 |

本机历史记录中曾发现 `D:\VMwareMachine\omarchy-4.0.2.iso`、现有 Omarchy VMware 虚拟机和 `F:` Ventoy U 盘。这些是待重新检查的线索，不能直接认定文件仍有效或盘符没变。已有挂起中的 VMDK 不直接作为本项目镜像，也不覆盖它。

## 3. AI 自动执行的完整流程

### 第一步：检查电脑，确认路线可行

**AI 做：** 检查 Python、UEFI、可用虚拟机工具、ISO、NTFS 卷剩余空间、源卷加密状态、U 盘型号/盘符/分区；保存只读主机报告。检查现有 Ventoy 配置，确认没有会隐藏条目的过滤规则。

当前代码对目标 U 盘要求：USB 总线、非系统盘/启动盘、数据卷卷标为 `Ventoy`、exFAT 或 NTFS，同盘恰好一个 `VTOYEFI` 卷。这些是程序的检查条件，不是给普通磁盘改个卷标就算安装 Ventoy。

**你可能需要做：** 插入准备使用的 U 盘；机器有多个不易区分的候选设备时指出哪一个。若确实缺少管理员权限，处理当前具体操作的系统授权提示。

**完成标准：** AI 给出实际使用的镜像路径、U 盘设备身份、软件来源和缺失项。路径使用实测值，不沿用示例 `F:` 猜测目标。

如果发现源卷只能在 Windows 登录后解锁，或者实际 Omarchy 版本的引导器、加密布局与 vtoyboot 组合未确认，AI 先验证可行性。不能省略这些问题后直接承诺“一定能裸机启动”。

### 第二步：准备官方文件和工具

**AI 做：** 优先检查已有文件，缺少时从官方来源下载，完整解压，记录版本、来源链接和 SHA256；有可信发布校验值时比对。AI 计算本地 SHA256 仅能固定文件身份，不能单靠它证明发布者。

来源：

- [Omarchy 官方网站](https://omarchy.org/)：安装 ISO。
- [Ventoy 官方发行页](https://github.com/ventoy/Ventoy/releases)：Ventoy Windows 包与 VentoyVlnk。
- [vtoyboot 官方发行页](https://github.com/ventoy/vtoyboot/releases)：Linux 镜像内准备工具。

已有可用 Ventoy U 盘直接复用。没有 Ventoy 时，AI 先展示待处理设备的型号、容量和当前分区，再处理安装。首次安装 Ventoy 会涉及清空目标 U 盘，未明确授权擦除该设备时，必须把这一项交给你决定；之后不反复询问同一授权。

**你可能需要做：** 只有目标 U 盘需要首次擦除、系统安装器需要人工处理时介入。无需自己搜索下载地址、计算哈希或整理工具目录。

**完成标准：** ISO、VentoyVlnk、vtoyboot 均有真实可访问路径和来源记录。不下载 `ventoy_vhdboot.img`，这次不使用 Windows 镜像启动功能。

### 第三步：安装一个独立 Omarchy 镜像

**AI 做：** 通过可用的虚拟机命令行或界面控制能力，新建 UEFI 虚拟机和固定 VHD，仅连接新磁盘和 Omarchy ISO，安装到该虚拟磁盘。建议最终镜像路径为 `D:\Systems\Omarchy.vhd.vtoy`，安装阶段先使用 `Omarchy.vhd`。

当前登记代码只接受**固定 VHD + `.vhd.vtoy` 后缀**，不能使用动态 VHD、VHDX、VMDK 或快照差分盘。Ventoy 官方也要求新建受支持的固定虚拟盘，并在安装前配置 UEFI；完整条件见 [Linux vDisk 官方说明](https://www.ventoy.net/en/plugin_vtoyboot.html)。

Omarchy 官方安装说明指出，ISO 安装会擦除选中的磁盘并默认使用全盘加密。因此安装器只能看到本次新建的虚拟磁盘，AI 必须核对容量和连接关系；不能将主机物理盘传给安装器。加密、引导器及 initramfs 的实际组合需要针对该 ISO 验证，不能因为 Omarchy 基于 Arch 就认定兼容。[Omarchy 官方安装说明](https://learn.omacom.io/2/the-omarchy-manual/50/getting-started)

**你可能需要做：** 输入个人账户密码、磁盘解锁密码等私密内容。如果 AI 当前没有可用的虚拟机界面或 guest 控制通道，它应停在具体界面，告诉你“现在选哪一项、完成后看到什么”，而不是把整个安装过程交还给你。密码不写入项目日志。

**完成标准：** 镜像中的 Omarchy 能进入桌面或可用终端，AI 能获取系统版本和磁盘布局。这里只证明虚拟机安装成功，还没有证明真实电脑能启动。

若现有虚拟机环境无法满足固定 VHD 制作条件，AI 先说明缺什么、安装其他工具是否要求主机重启。更换虚拟机工具不是项目已内置的一键功能。

### 第四步：在 Linux 内做好启动准备

**AI 做：** 使用实际可用的 guest 执行通道，例如已配置并获得授权的 SSH、虚拟机 guest 执行接口或界面终端，将完整 vtoyboot 发行包和 `scripts/Prepare-Omarchy.sh` 放入新系统。核对执行环境是这台测试 guest 后，以 root 运行包装脚本。

脚本会检查传入的官方脚本 SHA256，记录系统、内核和磁盘信息，执行 vtoyboot，日志在 `/var/log/osharbor-vtoyboot-<时间>.log`。AI 保存退出码和日志，不能只看窗口关闭就当作成功。

**你可能需要做：** 输入 sudo 或解锁密码；如果 guest 通道暂不可用，只执行 AI 给出的那条终端命令。其余文件准备、路径填写、结果检查仍由 AI 处理。

**完成标准：** 准备脚本退出成功，日志已保存，Omarchy 正常关机，虚拟盘未挂载、没有保存状态或后台写入。之后 AI 将 `Omarchy.vhd` 追加后缀为 `Omarchy.vhd.vtoy`。

如果 vtoyboot 拒绝当前布局或准备失败，AI 保存原因并排查，不跳过此阶段发布链接，也不擅自换一个 Linux 发行版代替 Omarchy。

### 第五步：AI 登记、构建、部署和验证

**AI 做：** 将这一份镜像登记到 `state/omarchy.json`，调用官方 VentoyVlnk 构建新的 bundle，先验证本地内容，再部署到重新核实的 U 盘，最后验证 U 盘实际内容。每条命令检查退出码，失败即先排查，不继续下一步。

部署保存旧 `ventoy.json` 的恢复备份，再写链接和菜单。当前程序会替换 `/os-harbor/` 下的托管别名；如果以前已部署其他 OS Harbor 系统，AI 需将原配置保存好，并说明此次菜单将切换为单个 Omarchy。其他用户配置按程序规则保留，无法兼容的配置先整合。

**你需要做：** 正常情况下无需操作。

**完成标准：** `verify --target` 返回 `consistency: passed`，数量为 1；AI 保存本次 bundle、generation、U 盘身份和恢复备份路径。此时只称为“已准备好进行启动测试”，`boot: pending` 仍是正确状态。

现有 `doctor --target` 无条件检查 Windows 插件，纯 Omarchy 也可能因这个无关项返回 1。AI 必须逐项读报告，将此项明确标为本场景不适用，不能为消除提示额外装 Windows 插件，也不能忽略其他 blocked。当前 `deploy` 和 `verify` 对纯 Omarchy bundle 不要求该插件。

### 第六步：你重启一次，完成真实启动

**AI 在重启前做：** 保存进度文件、主机基线、恢复路径，并给出准确的 U 盘设备和菜单名称。主机一旦切换系统，原 Windows 内运行的自动化进程会中断；当前项目没有跨系统自动接管功能。

**你做：**

1. 保存 Windows 工作，保持 SSD 和 U 盘连接，正常重启。
2. 按这台电脑实际的临时启动菜单按键，选择 U 盘 UEFI 启动项，再选 `Omarchy [实验性·待验证]`。具体按键由 AI 按机器型号确认，不统一假定 F12。
3. 若出现加密解锁界面，输入你自己设置的密码；不要把密码发到项目日志里。
4. 进入桌面后检查显示、网络、键盘鼠标和声音。失败则记下报错全文或拍照，交给 AI 继续排查。

如果固件设置阻止启动，AI 先说明具体原因、对现有 Windows 的影响和恢复方式，再由你处理必要的固件界面操作；不能照搬安装文档就直接关闭主机 TPM 或改动 Windows 启动配置。

**完成标准：** Omarchy 从 SSD 镜像在真实硬件启动，能够使用桌面、网络、输入设备和声音，正常关机并再次冷启动；随后拔掉 U 盘确认原 Windows 可以直接启动。AI 根据实际结果记录通过、失败或未测试。

若 Omarchy 内没有可用的 AI 控制通道，先由你完成上述最小验收，回到 Windows 后把结果交回原任务。不要承诺重启后 AI 会自动出现或自动继续。

## 4. 必要的手动操作只集中在这些地方

| 情况 | 你要做什么 | AI 应先准备什么 |
|---|---|---|
| 缺少或无法唯一识别目标 U 盘 | 插入设备或指出哪块盘 | 列出实际型号、容量和盘符 |
| 新 U 盘需要清空 | 决定是否擦除该具体设备 | 检查现有内容，说明影响范围 |
| 安装驱动/虚拟化组件需要系统交互 | 处理当前授权提示，必要时重启 | 准备安装文件和恢复进度 |
| 密码或解锁界面 | 自己输入 | 定位到正确界面，不把密码留在日志 |
| AI 无法访问安装器/guest 界面 | 完成当前一个步骤 | 给出精确操作及成功标志 |
| 切换到 Omarchy | 重启、选择启动设备 | 完成部署校验，保存恢复记录 |
| 真实硬件体验验收 | 确认显示、声音等实际效果 | 给出简短验收项，接收错误后继续排查 |

下载、哈希、路径选择、命令拼接、登记、构建、配置备份和结果整理都应由 AI 承担。已有充分授权的普通步骤直接继续，不把“每一步都让用户确认”作为自动化流程。

## 5. 给 AI 使用的现有命令

这部分是实施参考，你不需要手动逐条复制。**先完成镜像制作再执行；这些命令本身不会安装 Omarchy。** 示例默认在项目目录执行，解释器、工具路径、镜像位置和 U 盘盘符均需先实测。

```powershell
Set-Location -LiteralPath 'D:\CodeProjects\os-harbor'
python --version
python -m osharbor --help
New-Item -ItemType Directory -Force -Path '.\reports' | Out-Null
.\scripts\Inspect-Host.ps1 -OutputPath '.\reports\host-before.json'
```

如果 `python` 是商店占位符，AI 应找到实际 Python 3.11+ 解释器并统一使用其绝对路径，不要求你手工修好 PATH 才能继续。`Inspect-Host.ps1` 查询失败的项应标记未采集；它不自动挂载或计算 ESP 文件哈希。

第一次登记，后续更新不重复登记：

```powershell
python -m osharbor --registry '.\state\omarchy.json' register 'D:\Systems\Omarchy.vhd.vtoy' --id omarchy --name 'Omarchy' --type omarchy
python -m osharbor --registry '.\state\omarchy.json' list
python -m osharbor --registry '.\state\omarchy.json' doctor --target 'F:\' --vlnk-tool '.\tools\VentoyVlnk.exe' --report '.\reports\omarchy-doctor.json'
```

`--registry` 是全局参数，必须放在子命令之前。已经有同 ID 或同路径时先读登记表核实，不反复执行 `register`。

以下在镜像离线且前置条件通过后执行；每个外部命令失败会停止此段：

```powershell
$ErrorActionPreference = 'Stop'
$VlnkTool = '.\tools\VentoyVlnk.exe'
$ToolHash = (Get-FileHash -LiteralPath $VlnkTool -Algorithm SHA256).Hash
$Bundle = '.\artifacts\omarchy-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$Target = 'F:\' # 必须替换为本次核实的数据分区。

python -m osharbor --registry '.\state\omarchy.json' build --output $Bundle --vlnk-tool $VlnkTool --tool-sha256 $ToolHash
if ($LASTEXITCODE -ne 0) { throw '构建失败，停止部署' }
python -m osharbor verify --bundle $Bundle
if ($LASTEXITCODE -ne 0) { throw '本地校验失败，停止部署' }
python -m osharbor deploy --bundle $Bundle --target $Target
if ($LASTEXITCODE -ne 0) { throw '部署失败，检查恢复记录' }
python -m osharbor verify --bundle $Bundle --target $Target
if ($LASTEXITCODE -ne 0) { throw 'U盘校验失败，不进入启动验收' }
```

bundle 输出目录必须不存在。退出码 0 表示命令成功，1 表示 doctor 有 blocked，2 表示参数、校验或执行失败。doctor 的无关 Windows 插件项按前文单独判断。

Linux 内准备脚本的调用形式如下，实际路径和校验值由 AI 填好；此命令只在新建的 Omarchy guest 内执行：

```bash
sudo bash /实际路径/Prepare-Omarchy.sh /完整发行包目录/vtoyboot.sh 实际的64位SHA256
```

## 6. 重启前必须保存的进度

AI 在执行过程中维护 `reports/omarchy-progress.md`，它是需要在实施时创建的交接记录，当前 CLI 不会自动生成。每完成一个阶段就更新，而不是最后凭记忆填写。

记录内容保持简单：

- 当前阶段、已经成功的操作、具体失败原因和下一步。
- 实际 Python、ISO、VentoyVlnk、vtoyboot 路径及版本/哈希。
- 虚拟机名称、镜像路径、关机和挂载状态、实际系统/内核/引导器/加密布局。
- U 盘型号、磁盘身份、最近核实的盘符；盘符在恢复执行时仍要重新检测。
- 登记表、当前 bundle、generation、配置备份路径、准备日志路径。
- 裸机验收结果和需要你做的下一步，不包含账户密码或恢复密钥。

重启回来后，告诉 AI：“读取 reports/omarchy-progress.md，从上次的 Omarchy 步骤继续。” AI 应重新核对现场状态后续做，避免重复安装镜像、重复登记或覆盖上一份成果。

## 7. 装好之后怎么日常使用

**切换系统：** 平时直接启动原 Windows。要用 Omarchy，重启并从 U 盘入口启动；用完正常关机，再回 Windows。它不支持同一镜像一边在虚拟机中运行、一边裸机启动。

**更新 Omarchy：** 普通软件和系统数据写入镜像。涉及内核、驱动或整体系统更新时，在 Omarchy 内重跑 vtoyboot 准备，正常关机后回到 Windows，让 AI 重建、验证和部署。该更新要求来自 [Ventoy Linux vDisk 说明](https://www.ventoy.net/en/plugin_vtoyboot.html)。

**普通运行后：** 当前代码也会记录镜像修改时间和首尾指纹，正常运行后旧 bundle 可能无法再通过校验。让 AI 关机后用新目录重建并部署，这是本原型目前的工作方式；并不表示每次普通运行都必须重装系统。

**备份：** AI 在镜像关机且解除挂载后复制完整 VHD 文件，保存登记表与配置记录。96 GiB 固定盘的一份完整副本还需要接近 96 GiB 空间。不能用小型 bundle 或 U 盘替代系统镜像备份。

**菜单出现多份 Omarchy：** 新构建会产生新代次，旧目录不自动删除。AI 核对当前 `ventoy.json` 和 manifest 中的 generation，验证新代次后将不用的旧代次完整移到 U 盘之外。仅删除别名或移动到 U 盘另一个普通目录，旧链接仍可能被扫描。

## 8. 失败时怎么恢复

**安装阶段失败：** 保留已有 Windows 和原有虚拟机。AI 收集新建测试虚拟机里的错误，修复新镜像或重新制作，不直接安装到主机实体盘，也不为了绕过问题修改 Windows 的 BCD。

**构建阶段失败：** 没有进入部署时不会因此更新 U 盘菜单。AI 检查工具来源、固定 VHD 格式、离线状态和路径，修复后使用新的 bundle 目录构建。

**部署或启动失败：** 先保存错误。无法进入 Omarchy 时，通过正常关机、拔 U 盘再开机，尝试回原 Windows；若仍无法回 Windows，将此视为单独故障继续排查，不能声称恢复已成功。

AI 回退 U 盘的步骤：

1. 重新核对目标设备，确认没有正在运行的部署进程，读取进度中保存的备份目录 `ventoy/os-harbor-backups/<事务ID>/recovery.json`。
2. 先把 U 盘当前 `ventoy.json` 另存到本机 reports。若 `config_existed` 为 true，将该事务保存的旧 `ventoy.json` 复制回 U 盘 `ventoy/ventoy.json`；若为 false，将当前新配置移到本机备份目录，恢复原先没有配置的状态。
3. 核对实际菜单配置。`status: prepared` 不一定表示配置从未提交，最后写状态失败也会留下这个值。
4. 将失败的新代次移到 U 盘外，避免 Ventoy 继续扫描；保留需要使用的旧代次。
5. 使用对应的旧 bundle 校验（源镜像未变化时），或者记录实际菜单验收结果。回退后新 bundle 验证失败是预期现象。

强制中断可能遗留 `ventoy/.osharbor.lock`，AI 只有确认没有部署进程后才移除它。断电可能导致文件和配置不一致，不能仅凭存在备份就认为回退成功。

配置回退不会撤销 Omarchy 镜像内的数据变化；系统更新失败要使用离线镜像备份恢复。Windows 正常启动和 Omarchy 成功启动分别验收。

## 9. 这次简化后的能力边界

| 环节 | 当前实际情况 |
|---|---|
| 登记一个 Omarchy 镜像 | 已实现，使用独立登记表即可 |
| 官方链接生成、菜单部署、配置备份、一致性验证 | 已实现代码；真实工具执行和裸机链路仍待实测 |
| 检查、下载、命令编排、日志整理 | 可由有相应工具权限的 AI 执行，CLI 未内置完整编排 |
| 自动创建虚拟机、安装 Omarchy | 需要 AI 调用实际可用的虚拟机/界面工具；项目没有内置安装器 |
| Linux 内执行 vtoyboot | 已有包装脚本；需要可用的 guest 通道和必要权限 |
| 重启后继续控制 | 当前项目未实现；先保存进度，由用户完成启动并交回结果 |
| 真实 Omarchy + vtoyboot 兼容性 | 实验性，虚拟机成功和格式检查都不能替代裸机验收 |

后续代码简化应优先做三件事：纯 Omarchy 诊断不再检查 Windows 插件；增加可保存进度和恢复执行的单系统编排入口；接入实际可用的虚拟机与 guest 自动化通道。以上是待开发项，不是当前已有命令。

原先的多系统参数手册保留在 `docs/FULL-CLI-REFERENCE.md`，供维护代码时查阅。本次使用从检查、安装到恢复均已在本页讲完，不需要先读那份手册。
