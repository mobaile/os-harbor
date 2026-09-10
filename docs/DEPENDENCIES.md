# 依赖和来源记录

| 组件 | 当前状态 | 官方来源 |
|---|---|---|
| Python | 本机 3.12.14 已测试；要求 >=3.11 | https://www.python.org/downloads/ |
| Windows PowerShell | 使用系统版本 | Windows 自带 |
| Ventoy USB | 发现 F: 与同盘 VTOYEFI；本机版本尚未读取；官网最新页为 1.1.17 | https://github.com/ventoy/Ventoy/releases/tag/v1.1.17 |
| VentoyVlnk.exe | 未提供、未执行 | Ventoy 官方 Windows 发行包；https://www.ventoy.net/en/doc_vlnk.html |
| ventoy_vhdboot.img | U盘上缺失；官网最新页为 v3.0 | https://github.com/ventoy/vhdiso/releases/tag/v3.0 |
| vtoyboot | 未取得、未执行 | https://github.com/ventoy/vtoyboot/releases |
| 虚拟机工具 | 不随项目安装 | https://www.virtualbox.org/ 或 Windows Hyper-V |

工具必须从上述官方发行页取得。将版本、原始下载 URL、发布日期、文件 SHA256 记入下面记录模板；未下载不得填造校验值。build manifest 自动记录实际执行的 VentoyVlnk SHA256，官方版本仍需人工从发行包核实。

```json
{"component":"VentoyVlnk","version":null,"source_url":null,"sha256":null,"verified_at":null}
```

本地 `Get-FileHash -Algorithm SHA256` 可以固定文件身份，但只有与可信发布渠道比对才能确认来源。Windows 启动插件包含非开源 Windows 组件，不放入本项目源码。
