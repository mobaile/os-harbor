# OS Harbor 0.1.0

Windows 上运行的 Ventoy 镜像管理命令行原型。项目位置：`D:\CodeProjects\os-harbor`。
系统在 SSD 上，U盘保存链接与菜单。**软件测试通过不代表系统能够裸机启动；Omarchy 始终为实验性，实机验收待完成。**

## 启动

需要 Python 3.11+，核心无第三方依赖。从项目目录运行：

```powershell
python -m osharbor --help
python -m osharbor doctor --target F:\ --report reports/doctor.json
python -m unittest discover -s tests -v
```

也可 `python -m pip install -e .` 注册 `osharbor` 命令。若 Windows 的 python 是商店占位符，使用实际 Python 路径；本机已验证的解释器为 `C:\Users\mobai\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`。

## 使用流程

1. 按 `docs/IMAGE-PREPARATION.md` 制作独立测试镜像，关机并解除挂载。
2. 从官方发行页取得 VentoyVlnk 和 Windows 插件，记录版本及 SHA256；不随源码分发二进制。
3. 登记镜像，构建到新的目录。以下路径为示例，不会自动创建镜像：

```powershell
python -m osharbor register D:\Systems\Windows11.vhdx --id win11 --name 'Windows 11' --type windows
python -m osharbor register D:\Systems\Omarchy.vhd.vtoy --id omarchy --name 'Omarchy' --type omarchy
$toolHash = (Get-FileHash -LiteralPath .\tools\VentoyVlnk.exe -Algorithm SHA256).Hash
python -m osharbor build --output artifacts/build-001 --vlnk-tool tools/VentoyVlnk.exe --tool-sha256 $toolHash
python -m osharbor verify --bundle artifacts/build-001
```

SHA256 参数用于固定你已核实来源的文件，不代表工具自动证明供应链来源。build 调用官方 `VentoyVlnk.exe -i ... -o ...`，不生成伪链接。命令参数通过独立参数数组传递，支持空格和中文。

4. 将官方 `ventoy_vhdboot.img` 放到U盘数据分区 `/ventoy/`，再执行：

```powershell
python -m osharbor deploy --bundle artifacts/build-001 --target F:\
python -m osharbor verify --bundle artifacts/build-001 --target F:\
```

部署检查 USB 总线、非系统盘、Ventoy 数据卷和同盘 VTOYEFI。仅接受已安装好的 Ventoy U盘，不格式化。`F:` 是本次检测盘符，每次部署仍须指定实际目标。

## 行为说明

- registry 默认 `state/systems.json`，全局 `--registry` 应放在子命令之前。记录卷 GUID 和卷内路径，按登记顺序生成编号菜单。
- build 输出 manifest、配置片段和官方 vlnk。镜像时间/大小/首尾指纹变化后必须重建；普通系统运行也会修改镜像，因此运行后重新构建再部署。
- `verify` 校验生成链接的 SHA256、源镜像指纹、部署配置与插件存在性；不解析 vlnk 内部格式，不证明插件兼容性或镜像文件系统完整性。不能代替重启测试。
- 菜单使用编号文件名排序，保留用户的其他插件配置。若现有配置有 image_list/blacklist 或按模式覆盖别名，则停止部署，避免生成不可见条目。
- `/os-harbor/` 为项目保留命名空间。每次构建创建独立代次；旧代次不自动删除，可能仍在 Ventoy 扫描菜单中出现，按恢复文档清理。
- 退出码：0 成功；1 doctor 有待解决条件；2 输入、校验或执行失败。
- 无自动安装、克隆、快照、镜像删除、主机 EFI/BCD 写入、固件设置修改或自动重启。

## 当前验证

本机 UEFI 和 Ventoy USB 检查通过。找到 Windows 11 与 Omarchy ISO；尚未登记可启动镜像，未执行真实 vlnk 构建或 USB 部署，未进行裸机启动验证。详情见 `docs/VALIDATION.md`。测试替身仅存在于 tests，绝不用于生成发布产物。

文档：`docs/IMAGE-PREPARATION.md`、`docs/RECOVERY.md`、`docs/DEPENDENCIES.md`。
