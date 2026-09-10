# 验证记录 · 2026-09-10

> **历史实验资料，未经端到端验证，仅供源码与思路参考。本文描述较早的 Ventoy 路线，不实现当前 RAW 构想，不是推荐执行的安装教程。项目目前没有继续开发计划。文中路径与盘符均为虚构示例；实际执行可能修改磁盘或配置。当前项目定位见 [README](../README.md)，设计思路见 [CONCEPT](CONCEPT.md)。**

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

后续每次实机运行使用以下字段追加独立记录，不用格式检查的通过状态覆盖 boot=pending：

```json
{"system_id":"omarchy","result":"pending","tested_at":null,"os_version":null,"kernel":null,"ventoy_version":null,"vtoyboot_version":null,"plugin_sha256":null,"gpu":null,"network":null,"cold_boot":null,"after_update_boot":null,"original_windows_boot":null,"evidence_paths":[]}
```
