# 废弃代码的历史验证与归档检查

> **此页只记录旧 Ventoy 实验代码，不能证明第一版或第二版的完整系统方案可用。旧软件版本保持 `0.1.0`，所有相对命令以 `deprecated/` 为工作目录。**

## 原有历史记录

来源：[第一版验证记录](../../docs/history/v1/VALIDATION.md)中的“历史 Ventoy 代码检查”。以下原文保留当时结果和措辞，不是本次新增的部署或启动结果。


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

## 2026-09-11 目录归档检查

从 `deprecated/` 运行以下检查，全部通过：

| 检查 | 本次结果 |
|---|---|
| 源码、脚本、测试、包配置内容 | 11 个文件的 Git blob 与原提交一致，功能内容未修改 |
| `python -m unittest discover -s tests -v` | 19 项通过，使用临时目录及替身工具 |
| `python -m osharbor --help` | 正常退出，保留旧命令帮助 |
| `python -m osharbor --version` | 输出 `0.1.0` |
| `osharbor.ps1` 帮助与版本入口 | 指定可用 Python 后，两项均正常退出，版本为 `0.1.0` |

检查只证明归档后的目录依赖和旧代码行为仍正常，不构成真实安装或启动验证。未运行真实部署、分区操作、固件修改或重启。

[废弃代码说明](../README.md) · [当前第二版验证状态](../../docs/VALIDATION.md)
