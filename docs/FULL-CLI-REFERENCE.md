# OS Harbor 0.1.0 完整使用说明

> **历史实验资料，未经端到端验证，仅供源码与思路参考。本文描述较早的 Ventoy 路线，不实现当前 RAW 构想，不是推荐执行的安装教程。项目目前没有继续开发计划。文中路径与盘符均为虚构示例；实际执行可能修改磁盘或配置。当前项目定位见 [README](../README.md)，设计思路见 [CONCEPT](CONCEPT.md)。**

OS Harbor 是在 Windows 上运行的命令行工具，用来登记系统镜像、调用官方 VentoyVlnk 生成链接，并把链接和菜单配置部署到已安装 Ventoy 的 U 盘。**系统文件保存在本机 SSD 的镜像文件里，U 盘负责引导和菜单。** 这条历史路线的目标是裸机运行；本项目未验证实际启动。

当前版本是原型：没有图形界面，不会自动安装操作系统。Windows 和 Omarchy 的真实裸机启动尚未完成验收，Omarchy 路线尤其属于实验性。`boot: pending` 表示未证明能启动，不能把它理解为成功。

这份说明包含从准备到恢复的完整流程。`docs/` 中的文件保留专题背景和历史记录，完成基本操作不需要来回查阅它们。

## 1. 先弄清楚要准备什么

| 名称 | 用途 | 放在哪里 |
|---|---|---|
| Windows / Omarchy ISO | 安装系统的介质，本身不是装好的系统 | 主机任意合适目录 |
| Windows11.vhdx | 已经安装好 Windows 的虚拟硬盘 | 主机独立于 Ventoy 数据卷的 NTFS 卷，例如 `D:\Systems` |
| Omarchy.vhd.vtoy | 已安装并做过 vtoyboot 准备的固定 VHD | 同上 |
| Ventoy U 盘 | 开机时提供启动菜单 | 插在准备启动镜像的电脑上 |
| VentoyVlnk.exe | 根据真实镜像位置生成小型链接文件 | 官方 Windows 发行包中的工具 |
| ventoy_vhdboot.img | Windows 镜像启动插件 | U 盘的 `ventoy` 目录 |
| vtoyboot | 在 Linux 镜像内部进行启动准备 | Omarchy 虚拟机内部 |
| registry / 登记表 | 记录镜像 ID、名称、卷标识和路径 | 默认 `state/systems.json` |
| bundle / 构建目录 | 一次生成的链接、菜单片段和清单 | 例如 `artifacts/build-001` |
| generation / 代次 | 每次构建生成的唯一标识 | 对应 U 盘 `os-harbor/<代次>` 目录 |

使用顺序是：准备 U 盘和工具 → 制作并关闭系统镜像 → 登记 → 构建 → 本地校验 → 部署 → U 盘校验 → 手动重启验收。

只想使用 Windows，可以跳过 Omarchy 制作和登记。只使用 Omarchy，可以不装 Windows 启动插件，但要注意 `doctor --target` 仍会检查这个插件，可能因此返回待解决状态。

本工具不提供系统安装、现有系统克隆、在线快照、镜像转换、镜像删除、主机 EFI/BCD 修改、固件设置修改、自动重启。已有 VMware VMDK、WSL 的 ext4.vhdx 和 ISO 不能直接按本说明登记成受支持的已安装系统。

## 2. 环境与目录准备

### 2.1 基本要求

- Windows 主机，Python 3.11 或更高版本，系统自带 Windows PowerShell 可用。
- 本项目以 UEFI 路线进行检查和验收；`doctor` 检测到非 UEFI 会报告 blocked。
- 镜像放在有盘符的本地 NTFS 卷上。当前实现不支持网络路径、无盘符卷或其他文件系统作为镜像登记位置。
- 镜像所在卷和 Ventoy 目标卷必须不同，启动时镜像所在磁盘仍需连接且可访问。
- U 盘必须已经安装 Ventoy：目标磁盘为 USB 总线、不是系统盘或启动盘，数据卷卷标必须为 `Ventoy`，文件系统为 exFAT 或 NTFS，同一磁盘上恰好有一个卷标为 `VTOYEFI` 的卷。
- 镜像制作、离线副本和更新都需要空间。示例建议 Windows 虚拟盘容量 128 GiB、Omarchy 固定盘 96 GiB，这只是本项目的制作建议。固定 VHD 会立即占用接近完整容量；保留一份副本需要另外一份空间。

程序目前不会完整检测镜像是否被虚拟机占用、是否加密、是否依赖差分父盘，也不会预先证明空间足够。开始构建前需要自己确认镜像已经关机且未挂载。

### 2.2 在 PowerShell 中进入项目

下文命令均在 **Windows PowerShell / PowerShell 终端**运行，只有 Omarchy 准备部分特别标明在 Linux 内运行。不要把提示说明或输出 JSON 当作命令执行。

```powershell
Set-Location -LiteralPath 'C:\Example\os-harbor'
python --version
python -m osharbor --help
python -m osharbor --version
```

帮助中应有 `doctor`、`register`、`list`、`build`、`deploy`、`verify` 六个子命令，版本应为 `0.1.0`。

如果 `python` 打开 Microsoft Store、找不到命令或不是所需版本，先试 `py -3 --version`，之后统一用 `py -3 -m osharbor ...`。也可以指定实际解释器：

```powershell
$PythonExe = 'C:\Example\Python\python.exe'
& $PythonExe --version
& $PythonExe -m osharbor --help
```

上面是虚构的解释器路径，不代表任何实际设备；阅读代码示例时应自行解析其含义。后面的 `python` 命令也要统一替换成 `& $PythonExe`。

从源码目录直接运行不需要安装项目依赖，核心仅使用 Python 标准库。希望注册独立命令时可选执行：

```powershell
python -m pip install -e .
osharbor --help
```

安装使用 setuptools 构建环境，首次安装可能需要联网。若 `osharbor` 未加入 PATH，继续使用 `python -m osharbor` 即可。

项目还提供 `osharbor.ps1` 包装脚本，会先切换到项目目录再执行命令：

```powershell
.\osharbor.ps1 -PythonExe $PythonExe --help
```

若脚本执行策略阻止运行，核心 CLI 仍可通过 Python 调用；无需为了使用核心命令更改全局执行策略。

### 2.3 建议目录

```text
D:\Systems\
  Windows11.vhdx
  Omarchy.vhd.vtoy
C:\Example\os-harbor\
  tools\                    官方工具发行包和来源记录
  state\systems.json        首次成功登记后自动生成
  artifacts\build-001\      首次成功构建后生成
  reports\                  自己保存的诊断和验收记录
```

```powershell
New-Item -ItemType Directory -Force -Path 'D:\Systems', '.\tools', '.\reports' | Out-Null
```

`D:\Systems` 可以改成其他本地 NTFS 路径。镜像路径包含中文或空格时加引号。`state` 和构建目录会按需创建，不要预先创建将传给 `build --output` 的最终目录。

直接运行 CLI 时，相对路径基于**终端当前目录**；即便安装了 `osharbor` 命令也一样。为避免误用另一份登记表，下文一直从项目根目录执行。

## 3. 准备 Ventoy U 盘和官方工具

### 3.1 确定 U 盘盘符

先插入 U 盘，用以下只读命令核对卷标、磁盘型号和总线：

```powershell
Get-Volume | Format-Table DriveLetter, FileSystemLabel, FileSystem, SizeRemaining, Size
Get-Disk | Format-Table Number, FriendlyName, BusType, IsBoot, IsSystem, Size
```

下文统一假设数据分区是 `F:\`。**每次插拔后重新核实盘符，所有 `F:\` 都要替换成当次实际数据分区。** 不要使用 `VTOYEFI` 小分区，也不能传 `F:\某个文件夹`。

如果已有可用 Ventoy U 盘，可继续。若尚未安装 Ventoy：从 [Ventoy 官方发行页](https://github.com/ventoy/Ventoy/releases) 下载 Windows 包，完整解压，运行包内 `Ventoy2Disk.exe`，按设备型号和容量确认选中目标 U 盘后执行安装。首次安装会涉及分区和格式化，应先把 U 盘现有文件另存；此操作由 Ventoy 完成，OS Harbor 的 `deploy` 不会安装或格式化 Ventoy。安装结束后重新核对数据卷和 VTOYEFI，再继续。

### 3.2 准备链接生成工具

在官方 Windows 发行包内找到 `VentoyVlnk.exe`。建议保留完整解压目录；示例假设它位于 `tools\VentoyVlnk.exe`，实际在子目录就修改后续路径，别为了匹配示例丢弃发行包伴随文件。

```powershell
$VlnkTool = '.\tools\VentoyVlnk.exe'
Test-Path -LiteralPath $VlnkTool
$ToolHash = (Get-FileHash -LiteralPath $VlnkTool -Algorithm SHA256).Hash
$ToolHash
```

`Test-Path` 应返回 `True`，哈希应为 64 位十六进制字符串。下载时记录发行版本、原始下载链接、日期和 SHA256；若官方提供校验信息，进行比对。本地算出的哈希只能固定文件身份，不能独立证明发布者来源。更换工具文件后需要重新核实并计算哈希。

构建时程序实际执行官方 `VentoyVlnk.exe -i <源镜像> -o <生成链接>`，不会生成占位链接。[官方 vlnk 说明](https://www.ventoy.net/en/doc_vlnk.html) 描述了该命令和链接后缀规则。

### 3.3 安装 Windows 启动插件

有 Windows 镜像时，从 [官方 vhdiso 发行页](https://github.com/ventoy/vhdiso/releases) 下载并解压，找到真正的 `ventoy_vhdboot.img` 文件。不要把压缩包改名为 `.img`。

例如下载解压后的文件位于 `D:\Downloads\vhdiso\ventoy_vhdboot.img`：

```powershell
New-Item -ItemType Directory -Force -Path 'F:\ventoy' | Out-Null
Test-Path -LiteralPath 'F:\ventoy\ventoy_vhdboot.img'
```

如果目标已有插件，先另存旧文件并记录其版本、哈希，再决定更新。目标没有插件时复制：

```powershell
Copy-Item -LiteralPath 'D:\Downloads\vhdiso\ventoy_vhdboot.img' -Destination 'F:\ventoy\ventoy_vhdboot.img'
Get-Item -LiteralPath 'F:\ventoy\ventoy_vhdboot.img' | Select-Object FullName, Length
Get-FileHash -LiteralPath 'F:\ventoy\ventoy_vhdboot.img' -Algorithm SHA256
```

文件长度必须大于 0。该文件用于 Windows 镜像启动，按 [官方 Windows VHD 启动插件说明](https://www.ventoy.net/en/plugin_vhdboot.html) 放置。OS Harbor 不会下载、安装或备份这个插件，部署校验也不会证明插件版本兼容。

## 4. 制作系统镜像

已经拥有符合下列条件的离线镜像，可以直接到第 5 节。只有 ISO 时必须先完成安装；重命名 ISO 或 VMDK 的后缀不会把它变成有效 VHDX / VHD。

以下仅为虚构的安装介质路径，不代表已经获取或验证任何 ISO：

- Windows：`C:\Example\ISO\Windows.iso`
- Omarchy：`C:\Example\ISO\Omarchy.iso`

使用前从对应发行方核对来源与校验信息。下面的镜像制作步骤是待实机验收的路线，不能据此认定具体系统版本已经兼容。

### 4.1 Windows 11：创建全新 VHDX 并安装

1. 打开支持 VHDX 的虚拟机工具，例如已配置好的 Hyper-V 管理器。若没有可用工具，应先完成该工具的安装和环境配置；本项目不自动启用 Hyper-V。
2. 新建一台独立测试虚拟机，选择**第二代 / UEFI**。按实际 Windows 安装器要求配置内存、CPU、网络及虚拟 TPM 等选项，不通过修改主机引导分区解决虚拟机安装问题。
3. 新建虚拟硬盘，路径设为 `D:\Systems\Windows11.vhdx`，建议虚拟容量 128 GiB。使用独立 VHDX，不使用现有宿主系统磁盘、检查点差分文件或依赖父盘的镜像。若工具自动创建检查点，先处理检查点并确认实际使用的完整磁盘文件，不要只拿基础盘登记。
4. 给虚拟机挂载 Windows ISO。只连接新建的测试磁盘和安装 ISO，不直通主机物理磁盘，不把主机 ESP 分区映射进去。
5. 启动虚拟机，进入 Windows 安装流程，选择实际可用的版本，将系统安装在这块新建虚拟硬盘中。虚拟磁盘内的分区操作只影响该文件；先核对安装器列出的容量与预期相符。
6. 完成首次设置并进入桌面，确认安装确实完成。镜像内部不要启用 BitLocker；若自动启用设备加密，应在该测试 Windows 内完成解密再继续。
7. 从虚拟机系统菜单正常关机，确认管理器显示“已关闭”，不是暂停或保存状态。若曾在宿主机挂载 VHDX，在磁盘管理中分离对应虚拟硬盘，分离时不要选择删除文件。关闭可能写入该镜像的程序。
8. 在项目 PowerShell 中检查文件：

```powershell
.\scripts\Inspect-Image.ps1 -Path 'D:\Systems\Windows11.vhdx'
```

有 Hyper-V `Get-VHD` 时输出包含格式、磁盘类型、是否附加和父盘路径：确认格式为 VHDX、`Attached` 为 false、`ParentPath` 没有指向差分父盘。没有 `Get-VHD` 时脚本只提供文件信息和提示，**不代表已检查关机、挂载或差分状态**。

`register` 对 Windows 仅检查 `.vhdx` 后缀和文件开头签名，无法证明其中 Windows 安装正确。虚拟机能开机也只是制作阶段通过，之后仍要用 Ventoy 进行真实硬件验收。

### 4.2 Omarchy：固定 VHD、系统内准备、追加后缀

这条路线尚未完成兼容验证。首轮采用 [Ventoy Linux vDisk 官方说明](https://www.ventoy.net/en/plugin_vtoyboot.html) 中的 VirtualBox 制作思路；官方支持 Linux vDisk 不等于本项目已验证 Omarchy。

1. 在 VirtualBox 中新建独立虚拟机，安装前启用 EFI/UEFI。
2. 新建虚拟硬盘：格式选 **VHD**，存储方式选**固定大小**，建议 96 GiB，保存为 `D:\Systems\Omarchy.vhd`。不要选默认 VDI、动态 VHD、VHDX，也不要建立快照或差分链。
3. 虚拟机仅连接这块新 VHD 和 Omarchy ISO。根据安装器实际要求配置资源和网络，把系统安装到此测试磁盘中。若安装器不支持当前虚拟机环境，停在这里保存错误信息，不能把安装失败的磁盘继续当成可用镜像。
4. 安装完成后进入虚拟机里的 Omarchy，确认系统运行正常。从 [官方 vtoyboot 发行页](https://github.com/ventoy/vtoyboot/releases) 下载发行包并完整解压，核对来源、版本和发行校验信息。
5. 将项目 `scripts/Prepare-Omarchy.sh` 复制到这台虚拟机中。下列命令**只在虚拟机内的 Linux 终端执行**，把路径替换为刚解压的真实脚本路径：

```bash
cd ~/Downloads
sha256sum /实际解压目录/vtoyboot.sh
sudo bash ./Prepare-Omarchy.sh /实际解压目录/vtoyboot.sh 实际的64位SHA256
```

这里的“实际解压目录”和“实际的64位SHA256”都是占位符，不能照原样执行。第一次命令用于取得已核实来源文件的哈希；第二次参数填该值。不要只复制 `vtoyboot.sh` 而漏掉发行包的其他文件。

包装脚本要求 root、校验传入脚本的 SHA256，进入其所在目录调用官方脚本，记录内核、系统和磁盘信息，日志保存到 `/var/log/osharbor-vtoyboot-<时间>.log`。只有出现 `Preparation finished; boot is still pending` 才表示包装流程执行完毕；遇到非零退出或报错先保存日志。脚本不能自动判断自己是否在虚拟机里，执行位置必须自己核对。

6. 正常关闭虚拟机，确认没有保存状态且磁盘未挂载。在 Windows 中为文件**追加** `.vtoy`：

```powershell
Rename-Item -LiteralPath 'D:\Systems\Omarchy.vhd' -NewName 'Omarchy.vhd.vtoy'
Get-Item -LiteralPath 'D:\Systems\Omarchy.vhd.vtoy'
```

7. 之后登记最终路径。Omarchy 登记会检查固定 VHD 页脚、校验和和文件长度，但无法证明已运行 vtoyboot，也不会检测引导器、内核和驱动是否能在真实电脑工作。

再次用虚拟机维护时，如工具无法打开 `.vtoy` 文件，可在离线状态临时改回 `.vhd` 并重新关联；维护完正常关机后恢复登记的原名。内核或相关驱动更新后重新运行准备流程，再从 Windows 重建和部署链接。

## 5. 第一次登记与诊断

### 5.1 登记你已经准备好的镜像

只执行自己实际准备好的系统对应命令：

```powershell
python -m osharbor register 'D:\Systems\Windows11.vhdx' --id win11 --name 'Windows 11' --type windows
python -m osharbor register 'D:\Systems\Omarchy.vhd.vtoy' --id omarchy --name 'Omarchy' --type omarchy
python -m osharbor list
```

参数含义：

| 参数 | 含义与限制 |
|---|---|
| 第一个路径 | 已存在的镜像文件，不是目录或 ISO |
| `--id` | 唯一标识，1–48 字符，以小写字母开头，只能使用小写字母、数字和短横线，例如 `win11-work` |
| `--name` | 菜单显示名称，不能为空，可以使用中文和空格 |
| `--type windows` | 当前只接受带有效文件签名的 `.vhdx` |
| `--type omarchy` | 当前只接受符合固定 VHD 校验的 `.vhd.vtoy` |

成功会打印登记项 JSON，并写入 `state/systems.json`。登记保存卷标识和卷内相对路径，不只是盘符；同一卷盘符改变时能重新解析。镜像移到另一卷或在卷内改名、移动目录后，需要更新登记。

同一 ID 或同一文件不能重复登记；`register` 不是更新命令。`list` 输出 `systems: []` 表示尚未登记，也可能是当前目录或 `--registry` 指向了另一份文件。

### 5.2 运行完整诊断

```powershell
python -m osharbor doctor --target 'F:\' --vlnk-tool '.\tools\VentoyVlnk.exe' --report '.\reports\doctor.json'
$LASTEXITCODE
```

工具路径按实际位置修改。诊断打印 JSON，也保存到指定报告文件。查看 `checks` 中每项的 `status` 和 `detail`：

- `firmware`：是否 UEFI。
- `volumes`：是否能获取 Windows 卷信息。
- 镜像 ID：登记的卷和镜像是否可访问、格式检查是否通过。
- `VentoyVlnk`：是否能读取工具并计算哈希；不会执行工具或校验其发布者。
- `usb`：指定目标是否符合本项目 Ventoy U 盘限制。
- `windows_plugin`：是否能读取插件并计算哈希；不是启动测试。

`passed` 表示该项检查成功，`blocked` 后面的 `detail` 才是需要处理的问题。没有登记镜像、没有提供 `--vlnk-tool`，都会产生 blocked。省略 `--target` 会跳过 U 盘和插件检查，不代表它们通过。

只有 Omarchy 时，`doctor --target` 也会检查 Windows 插件，这是当前诊断实现的限制；而 `deploy` / `verify` 只在 bundle 包含 Windows 时要求插件。不要为了消除这个诊断项就误认为 Omarchy 需要该插件。

## 6. 构建、本地验证、部署到 U 盘

### 6.1 构建

确认所有已登记镜像都处于离线状态。`build` 会处理当前登记表里的**全部**镜像，没有只构建某一个 ID 的参数。

```powershell
$VlnkTool = '.\tools\VentoyVlnk.exe'
$ToolHash = (Get-FileHash -LiteralPath $VlnkTool -Algorithm SHA256).Hash
python -m osharbor build --output '.\artifacts\build-001' --vlnk-tool $VlnkTool --tool-sha256 $ToolHash
$LASTEXITCODE
```

`build-001` 必须是不存在的新目录。成功打印 manifest JSON，目录示意如下，代次值由程序随机生成：

```text
artifacts/build-001/
  manifest.json
  ventoy.fragment.json
  os-harbor/<32位代次>/
    001-win11.vlnk.vhdx
    002-omarchy.vlnk.vtoy
```

只有登记两个系统才会有两个链接。编号按登记顺序生成，具体菜单显示还受 Ventoy 的其他配置影响。Windows 别名会追加 `[待验证]`，Omarchy 追加 `[实验性·待验证]`；当前没有自动摘除这些标记的功能。

manifest 记录源镜像大小、修改时间、首尾指纹、生成链接 SHA256 和工具 SHA256。构建目录不包含整个系统镜像，也不是镜像备份。不要手工改链接文件名或 manifest 内容。

### 6.2 校验本地构建

```powershell
python -m osharbor verify --bundle '.\artifacts\build-001'
$LASTEXITCODE
```

两个镜像成功时输出类似：

```json
{"consistency": "passed", "boot": "pending", "count": 2}
```

`count` 是 bundle 中镜像数量。只有退出码为 0 才继续；失败时按第 10 节处理。

这个检查需要原始镜像仍能访问，不是拿着 bundle 去一台没有源镜像的电脑就能完成。它会检查链接哈希和源镜像指纹，但不解析 vlnk 内部结构，也不检查整个镜像文件系统。指纹使用文件大小、修改时间及首尾各 64 KiB 的哈希，不是整盘 SHA256，因此不能用作完整镜像备份校验。

### 6.3 部署

再次核实 `F:\` 是本次目标。包含 Windows 时先完成第 3.3 节的插件安装。

```powershell
python -m osharbor deploy --bundle '.\artifacts\build-001' --target 'F:\'
$LASTEXITCODE
```

成功输出含 `generation`、`backup` 和 `boot: pending`。记录 `backup` 路径，以便回退。此命令写入 U 盘：

```text
F:\
  os-harbor\<代次>\
    001-win11.vlnk.vhdx
    002-omarchy.vlnk.vtoy
    manifest.json
  ventoy\
    ventoy_vhdboot.img                 之前人工安装的插件
    ventoy.json                       合并后的菜单配置
    os-harbor-backups\<事务ID>\
      recovery.json
      ventoy.json                     仅原配置存在时备份
```

部署会先校验目标和 bundle，建立互斥锁，保存旧配置，再写入本代次文件，最后替换 `ventoy.json`。一般会保留主题等其他插件配置和不属于 `/os-harbor/` 的菜单别名；`/os-harbor/` 下的别名由本工具接管并替换成本次 bundle 的内容。

如果旧配置含 `menu_alias_*`、`image_list*`、`image_blacklist*` 等模式设置或过滤设置，程序会拒绝部署，需要先人工整合。不要直接用 `ventoy.fragment.json` 覆盖原 `ventoy.json`，片段不包含你的完整配置。

同一个 bundle 重复部署不会重复添加菜单别名，但每次仍会产生新的配置备份事务。不同 bundle 会生成不同代次；旧链接目录不会自动删除。

### 6.4 校验 U 盘实际内容

```powershell
python -m osharbor verify --bundle '.\artifacts\build-001' --target 'F:\'
$LASTEXITCODE
```

应返回 `consistency: passed` 和退出码 0。相比本地校验，这一步额外检查目标 U 盘、已部署别名、链接 SHA256，以及包含 Windows 时的插件存在且非空。

程序不会固定插件 SHA256，也不会证明插件能启动当前镜像。`consistency: passed` 的含义是当前检查范围内文件与配置一致，`boot` 仍应是 `pending`。

## 7. 真正开机使用与验收

1. 保存主机上所有工作，保持源镜像所在磁盘连接，确认镜像没有被虚拟机打开。
2. 重启前，在项目目录运行只读报告脚本，保存主机基线：

```powershell
New-Item -ItemType Directory -Force -Path '.\reports' | Out-Null
.\scripts\Inspect-Host.ps1 -OutputPath '.\reports\host-before.json'
```

报告包含卷、分区、固件、Secure Boot 查询结果、BCD 和固件启动项。访问被拒绝时相关内容不算已采集；必要时在管理员 PowerShell 中重跑这个只读脚本。它不会挂载 ESP 或对 ESP 文件做哈希，因此不能用这份报告单独证明 ESP 内容未变化。

3. 通过 Windows 正常重启，在主板临时启动菜单选择该 U 盘的 UEFI 项。临时启动菜单按键取决于机器型号，常见有 F12、F11、Esc，应以电脑开机提示或厂商说明为准。
4. 进入 Ventoy 后，选择对应 Windows / Omarchy 名称或编号链接。菜单能显示不等于系统能启动；如果有错误，记录报错全文或照片、选中条目和工具版本。
5. 第一次进入系统，逐项检查桌面、GPU/显示分辨率、网络、声音、磁盘访问、正常关机和再次冷启动。Omarchy 尤其要记录真实硬件与虚拟机中的差别。
6. 测试完正常关机，拔掉 U 盘，再开机确认原 Windows 能直接启动。
7. 回到原 Windows 后保存第二份报告：

```powershell
.\scripts\Inspect-Host.ps1 -OutputPath '.\reports\host-after.json'
```

比较两份报告中的分区、BCD 和固件启动项，保留错误输出和变化说明。需要核对 ESP 内容时另行只读采集，当前脚本没有覆盖。

每个系统建议保存一份人工验收记录，至少包括：日期、镜像 ID、系统/内核版本、Ventoy 和插件/vtoyboot 版本、冷启动、桌面、GPU、网络、声音、关机、再次启动、拔 U 盘原 Windows 直启、错误日志位置。尚未测试的项目填写“未测试”，失败填写实际错误。

当前程序不会自动读取这些人工记录或把 `boot: pending` 改成已验证。若 Secure Boot、加密卷或硬件驱动阻止启动，保存具体错误后排查对应环节；OS Harbor 不会自动调整固件或解锁镜像存储卷。

## 8. 日常更新、添加系统与管理登记表

### 8.1 系统运行或更新以后

镜像是可写的完整系统。正常运行也可能改变其修改时间和内容；因此旧 bundle 很可能无法再通过校验。按当前工具的工作流程，每次镜像发生变化后，应离线重新构建、校验和部署。

```powershell
# 在原 Windows 中执行，镜像内系统已正常关机且未挂载。
$VlnkTool = '.\tools\VentoyVlnk.exe'
$ToolHash = (Get-FileHash -LiteralPath $VlnkTool -Algorithm SHA256).Hash
python -m osharbor build --output '.\artifacts\build-002' --vlnk-tool $VlnkTool --tool-sha256 $ToolHash
# 上一条退出码为 0 后才继续下一条。
python -m osharbor verify --bundle '.\artifacts\build-002'
python -m osharbor deploy --bundle '.\artifacts\build-002' --target 'F:\'
python -m osharbor verify --bundle '.\artifacts\build-002' --target 'F:\'
```

逐条检查退出码；PowerShell 中外部命令失败后不一定自动停止后续命令，不能无视前面的报错。下一次使用 `build-003` 等新目录。Omarchy 内核/相关驱动更新后先在该系统内重跑 vtoyboot 准备，再执行这里的 Windows 步骤。

### 8.2 添加第三个系统

按相应镜像制作流程创建另一份独立镜像，使用新 ID 登记，再构建整个登记表：

```powershell
python -m osharbor register 'D:\Systems\Windows11-Test.vhdx' --id win11-test --name 'Windows 11 测试' --type windows
python -m osharbor list
```

然后按第 6 节使用新的输出目录构建和部署。系统 ID 没有硬编码为 `win11` 或 `omarchy`，这些只是示例。

### 8.3 改名、调整顺序、移除登记

当前没有 `rename`、`unregister` 或排序子命令，可以在备份后编辑 JSON 登记表：

```powershell
$RegistryBackup = '.\state\systems-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json.bak'
Copy-Item -LiteralPath '.\state\systems.json' -Destination $RegistryBackup
notepad.exe '.\state\systems.json'
```

保留顶层 `schema_version: 1` 和 `systems` 数组，使用 UTF-8 保存，JSON 不允许注释、尾随逗号和重复键。

- 改菜单名称：修改目标对象的 `name`。
- 调整生成编号：移动 `systems` 数组中整个对象的顺序。
- 移除登记：删除对应完整对象并修正相邻逗号；不会删除实际镜像或 U 盘链接。
- 镜像改名、搬目录或换卷：先备份登记表，移除旧登记，再用最终路径重新 `register`，由程序采集卷信息。不要猜测 `volume_id`。

保存后先运行 `python -m osharbor list` 检查格式，再运行带工具和目标参数的 `doctor` 检查实际路径。重新构建、部署后菜单才会更新。若移除了最后一项，`build` 会拒绝空登记表；要完全撤销 U 盘条目，按第 9 节回退配置并清理链接。

### 8.4 使用另一份登记表

全局参数 `--registry` 必须放在子命令**前面**，例如：

```powershell
python -m osharbor --registry '.\state\lab.json' register 'D:\Systems\Windows11-Test.vhdx' --id win11-test --name '实验 Windows' --type windows
python -m osharbor --registry '.\state\lab.json' list
python -m osharbor --registry '.\state\lab.json' build --output '.\artifacts\lab-001' --vlnk-tool $VlnkTool --tool-sha256 $ToolHash
```

`doctor`、`register`、`list`、`build` 使用指定登记表。`deploy` 和 `verify` 根据 bundle 内保存的记录工作，修改登记表不会修改旧 bundle。不同登记表生成的 bundle 部署到同一 U 盘时，会替换该盘全部 OS Harbor 托管别名，不会自动把两份列表合并。

### 8.5 备份与换电脑

备份系统必须在镜像正常关机、解除挂载后复制完整文件，同时保存登记表、使用中的 bundle 和工具来源记录。bundle 和 U 盘只保存链接，不包含镜像内容，不能用于恢复镜像数据。

复制到新卷或换电脑后，重新登记新位置、重建并部署；卷标识和真实硬件环境可能不同。卷 GUID 跟踪用于本机寻找源文件，不能保证旧 vlnk 在磁盘重分区、迁移之后仍能启动。

## 9. 失败回退、旧菜单清理与停用

### 9.1 找到对应部署的配置备份

停止其他部署操作，重新核对目标 U 盘。查看备份事务目录：

```powershell
Get-ChildItem -LiteralPath 'F:\ventoy\os-harbor-backups' -Directory | Sort-Object LastWriteTime -Descending
```

优先使用当时 `deploy` 返回的 `backup` 路径。选中目标事务后读取记录：

```powershell
$RecoveryDir = 'F:\ventoy\os-harbor-backups\替换为实际事务ID'
Get-Content -LiteralPath (Join-Path $RecoveryDir 'recovery.json')
```

`config_existed` 表示部署前有没有配置，`generation` 对应该次新代次，`status` 通常是 `prepared` 或 `committed`。若配置已提交但最后写状态时失败，仍可能显示 prepared，应核对实际 `ventoy.json`，不能只靠状态字段判断。

### 9.2 恢复菜单配置

先把当前配置另存到本机，供比较：

```powershell
$CurrentConfigCopy = '.\reports\ventoy-before-recovery-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'
if (Test-Path -LiteralPath 'F:\ventoy\ventoy.json') {
    Copy-Item -LiteralPath 'F:\ventoy\ventoy.json' -Destination $CurrentConfigCopy
}
```

如果选定记录中 `config_existed` 为 **true**，恢复该事务保存的旧配置：

```powershell
Copy-Item -LiteralPath (Join-Path $RecoveryDir 'ventoy.json') -Destination 'F:\ventoy\ventoy.json' -Force
```

如果为 **false**，说明该次部署前没有配置，应把当前新配置移出原位置，恢复“没有配置”的状态，而不是从别的事务随便复制一份：

```powershell
$RemovedConfigCopy = '.\reports\ventoy-removed-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'
if (Test-Path -LiteralPath 'F:\ventoy\ventoy.json') {
    Move-Item -LiteralPath 'F:\ventoy\ventoy.json' -Destination $RemovedConfigCopy
}
```

两种分支只执行符合 `config_existed` 的一种。以上示例假定仍位于项目目录且 `reports` 已存在。

恢复配置不会回滚镜像内系统数据，也不会自动移除新代次链接。**旧配置未引用的链接仍可能被 Ventoy 扫描显示。** 接着检查第 9.3 节，将不再使用的代次移出 U 盘。

回退后，新 bundle 的目标 `verify` 报别名不匹配或配置缺失是预期结果。若保留了相应旧 bundle 且旧源镜像仍未改变，可用旧 bundle 校验；否则通过检查配置和实际 Ventoy 菜单验收，不能把无法校验当作通过。

### 9.3 清理旧代次和重复菜单

```powershell
Get-ChildItem -LiteralPath 'F:\os-harbor' -Directory
Get-Content -LiteralPath '.\artifacts\build-002\manifest.json'
```

从**当前实际在用的** bundle 清单读取 `generation`，再核对 `F:\ventoy\ventoy.json` 引用的路径。验收当前代次成功后，用资源管理器将确定不再使用的旧代次整个文件夹移到 U 盘之外，例如本机备份目录。保留正在使用或回退需要的代次，不要仅按目录日期判断。

不能只删旧别名而保留链接，也不要把旧代次放到 U 盘另一普通文件夹里期待它消失：Ventoy 仍可能扫描到。不要移动整个 `F:\os-harbor`，否则当前条目也会失效。

### 9.4 遗留部署锁

强制终止可能留下 `F:\ventoy\.osharbor.lock`。先确认其他终端或任务没有正在执行部署，再只删除这个锁文件：

```powershell
Remove-Item -LiteralPath 'F:\ventoy\.osharbor.lock'
```

正常退出通常会自动释放锁。删锁不能修复断电留下的配置或文件问题，之后仍需校验或回退。exFAT 断电情况下不保证多个文件一起持久化，重新连接 U 盘后应核对实际内容。

### 9.5 完全停止使用 OS Harbor

恢复首次部署前的配置；若之后添加了其他用户配置，应先保存并人工合并需要保留的修改。把所有 OS Harbor 代次移到 U 盘外，保留备份供恢复。不要删除其他 Ventoy 文件或其他镜像使用的 Windows 插件。

本地镜像仍是自己的数据，移除登记表或项目并不会删除它们。如果曾通过 pip 安装，可使用相同 Python 的 `python -m pip uninstall os-harbor` 卸载命令入口。

## 10. 常见问题与错误处理

| 现象 / 报错 | 含义与处理 |
|---|---|
| `No module named osharbor` | 先切换到项目根目录，检查解释器；或用同一个解释器执行可编辑安装。 |
| `unrecognized arguments: --registry ...` | 把 `--registry` 放到 `doctor/register/list/build` 等子命令之前。 |
| `No registered images` / `Register at least one image before building` | 登记表为空；完成镜像制作并登记，核对当前目录和登记表路径。 |
| `Prototype image storage requires NTFS` | 把离线镜像放到本地 NTFS 卷再登记；不要用改后缀的方法处理。 |
| `Image must be on a uniquely identified local drive` | 使用有盘符且可被 Windows 唯一识别的本地卷，检查路径是否指向网络或其他挂载位置。 |
| `Windows requires a VHDX with valid file signature` | 文件不是有效签名的 `.vhdx`；ISO、VMDK、WSL 镜像都不能因此当成已安装 Windows。 |
| `Omarchy requires fixed VHD named *.vhd.vtoy` | 核对文件名和格式，最终必须是固定 VHD 并追加 `.vtoy`。 |
| `Omarchy VHD must be fixed` / `Invalid VHD footer checksum` / `Fixed VHD length does not match footer` | 类型错误、文件不完整或页脚不一致；重新检查制作过程或离线备份，不要手改页脚绕过检查。 |
| `System ID or image already registered` | 同一 ID 或路径重复；先 `list` 查看，更新登记按第 8.3 节处理。 |
| `Volume unavailable or ambiguous` / `Image missing` | 源卷未连接、没有盘符或文件已移动；恢复路径，或重新登记新位置。 |
| `VentoyVlnk SHA256 mismatch` | 工具文件与参数哈希不一致；核实实际文件来源和路径后重新计算，不要盲目换成未知文件的哈希。 |
| `Build output must be a new directory` | 换成新的 `build-002` 等路径，不要预建输出目录或覆盖旧构建。 |
| `VentoyVlnk failed` / 执行超时 | 检查官方工具版本、路径和运行权限；调用最多等待 120 秒。必要时在管理员 PowerShell 中重试，保存错误信息。 |
| `Image changed during build` | 有程序正在修改镜像；关闭虚拟机、分离挂载，使用新目录重建。 |
| `Image changed since build; regenerate links` | 镜像自构建后发生变化，包括普通运行；关机后重建并部署。 |
| `Target must be a Windows drive root` | 使用实际数据分区根路径，如 `F:\`，不能用子目录。 |
| `Target must be a non-system USB with Ventoy data label and sibling VTOYEFI` | 核对 USB 总线、系统盘标志、数据卷精确卷标 `Ventoy` 和同盘唯一 VTOYEFI。检测不满足时停止；不能靠给普通磁盘改名伪装成 Ventoy。 |
| `Unsupported Ventoy data filesystem` | 目标数据卷只接受 exFAT 或 NTFS；确认选中了正确分区。 |
| `Source images must be on a different volume from Ventoy` | 镜像需要存放在目标卷之外，迁移离线镜像并重新登记、构建。 |
| `Missing /ventoy/ventoy_vhdboot.img` / `Windows boot plugin missing` | 按第 3.3 节放置官方解压后的非空插件。 |
| `Mode-specific aliases or image filters require manual reconciliation before deployment` | 旧配置有模式专用别名或图像过滤器；备份后使用 VentoyPlugson 或编辑器人工整合，不能用空配置覆盖解决。 |
| `Cannot read JSON` / `Duplicate JSON key` / `Malformed existing menu_alias` | 根据报错路径检查 JSON 语法、重复键或字段类型；恢复备份或修复具体错误。 |
| `Deployment lock exists` | 排查是否另有部署运行，只有确定没有时才按第 9.4 节移除遗留锁。 |
| `Ventoy configuration changed concurrently; retry` | 有其他程序同时编辑配置；结束并发修改，核对实际配置后重试。 |
| `Existing generation differs; refusing overwrite` | U 盘同代次文件与 bundle 不一致；保留现场并检查，使用新的构建代次，别直接覆盖可疑文件。 |
| `Build link checksum mismatch` / `Deployed link checksum mismatch` | 本地构建或 U 盘链接被改动/损坏；核对来源，需要时重新构建部署，并排查存储介质。 |
| `Deployed aliases differ from build` | 当前菜单对应其他 bundle、已回退或被编辑；选正确 bundle 校验，或重新部署期望的代次。 |
| `Access denied` / PowerShell 查询失败 | 检查文件占用、目标写保护和权限；有权限需要时使用管理员终端重试对应操作。 |
| U 盘菜单出现重复系统 | 通常为旧代次仍被扫描；按第 9.3 节移出旧链接目录。 |
| verify 成功但重启失败 | 一致性检查不覆盖真实启动；记录 Ventoy 报错，排查源磁盘可访问性、插件、镜像制作、固件和驱动环节。 |

## 11. 命令参数速查

所有命令支持 `--help`，例如 `python -m osharbor build --help`。

| 命令 | 必填 | 可选 | 数据影响 |
|---|---|---|---|
| `doctor` | 无 | `--target`、`--vlnk-tool`、`--report` | 查询主机/镜像；指定 report 时写报告 |
| `register` | 镜像路径、`--id`、`--name`、`--type` | 无子命令专属可选参数 | 写登记表，不修改镜像 |
| `list` | 无 | 无子命令专属可选参数 | 读取登记表，缺失时返回空列表 |
| `build` | `--output`、`--vlnk-tool`、`--tool-sha256` | 无子命令专属可选参数 | 执行官方工具，生成新 bundle |
| `deploy` | `--bundle`、`--target` | 无子命令专属可选参数 | 写 U 盘链接、配置和恢复备份 |
| `verify` | `--bundle` | `--target` | 校验本地 bundle，可选校验 U 盘 |

全局参数：`--registry <路径>`，默认 `state/systems.json`；`--version` 输出版本；`--help` 输出帮助。

正常业务结果打印为 JSON；输入、校验或执行失败一般打印 `osharbor: <错误原因>` 到标准错误。帮助输出是普通文本。退出码：

- `0`：命令成功，或 doctor 所执行的检查没有 blocked。
- `1`：doctor 至少有一项 blocked，需要阅读报告。
- `2`：参数不合法、输入/校验失败、文件或工具执行异常。

在每条命令之后立即运行 `$LASTEXITCODE` 查看结果，避免之后运行其他外部程序覆盖它。

## 12. 当前验证范围与开发者检查

历史记录仅说明曾有 19 项 Python 单元/流程测试及 CLI 帮助、PowerShell 语法检查通过。此前主机只读检查的设备资料不在公开文档中保留。这些结果不证明任何裸机启动能力。

尚未完成：官方 VentoyVlnk 真实执行、真实 U 盘部署、Windows VHDX 裸机启动、Omarchy 固定 VHD 裸机启动、GPU/网络/更新后启动、拔 U 盘原 Windows 直启和 ESP/BCD 前后验收。测试使用临时目录和链接生成器替身，不能代替这些检查。

开发者可在项目根目录运行：

```powershell
python -m unittest discover -s tests -v
```

该测试验证代码行为，不会使用替身生成正式发布产物。诊断报告包含本机卷标识，报告保存在本地；需要分享排错材料时先检查其内容。
