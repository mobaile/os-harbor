# 依赖和来源记录

> **历史实验资料，未经端到端验证，仅供源码与思路参考。本文描述较早的 Ventoy 路线，不实现当前 RAW 构想，不是推荐执行的安装教程。项目目前没有继续开发计划。文中路径与盘符均为虚构示例；实际执行可能修改磁盘或配置。当前项目定位见 [README](../README.md)，设计思路见 [CONCEPT](CONCEPT.md)。**

| 组件 | 历史状态／约束 | 官方来源 |
|---|---|---|
| Python | 旧实验要求 >=3.11 | https://www.python.org/downloads/ |
| Windows PowerShell | 使用系统版本 | Windows 自带 |
| Ventoy USB | 历史参考版本 1.1.17；不代表当前版本或本项目兼容性 | https://github.com/ventoy/Ventoy/releases/tag/v1.1.17 |
| VentoyVlnk.exe | 未提供、未执行 | Ventoy 官方 Windows 发行包；https://www.ventoy.net/en/doc_vlnk.html |
| ventoy_vhdboot.img | 历史参考版本 v3.0；本项目未验证 | https://github.com/ventoy/vhdiso/releases/tag/v3.0 |
| vtoyboot | 未取得、未执行 | https://github.com/ventoy/vtoyboot/releases |
| 虚拟机工具 | 不随项目安装 | https://www.virtualbox.org/ 或 Windows Hyper-V |

工具必须从上述官方发行页取得。将版本、原始下载 URL、发布日期、文件 SHA256 记入下面记录模板；未下载不得填造校验值。build manifest 自动记录实际执行的 VentoyVlnk SHA256，官方版本仍需人工从发行包核实。

```json
{"component":"VentoyVlnk","version":null,"source_url":null,"sha256":null,"verified_at":null}
```

本地 `Get-FileHash -Algorithm SHA256` 可以固定文件身份，但只有与可信发布渠道比对才能确认来源。Windows 启动插件包含非开源 Windows 组件，不放入本项目源码。
