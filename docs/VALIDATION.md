# 验证记录 · 2026-09-10

| 项目 | 结果 |
|---|---|
| Python 单元/流程测试 | 19 项通过，使用临时目录与官方链接生成器替身 |
| CLI 帮助与 PowerShell 脚本语法 | 通过 |
| 主机 UEFI | doctor 检测通过 |
| F: Ventoy 数据分区与同盘 VTOYEFI | 只读检测通过；未写入 |
| Windows 与 Omarchy 安装 ISO | 文件存在；版本仅据文件名 |
| 官方 VentoyVlnk 实际执行 | 待验证，工具未提供 |
| Windows VHDX 裸机启动 | 待验证，无已登记镜像 |
| Omarchy 固定 VHD 裸机启动 | 实验性、待验证 |
| GPU/网络/内核更新后重启 | 待验证 |
| 拔U盘原 Windows 直启 | 待验证，未重启 |
| ESP/BCD 前后对比 | 待验证，未进行镜像部署/启动 |

本次没有修改系统分区、固件、BCD 或真实U盘。完整诊断存放在本地 reports/doctor.json；包含本机卷标识，不自动上传。

后续每次实机运行使用以下字段追加独立记录，不用格式检查的通过状态覆盖 boot=pending：

```json
{"system_id":"omarchy","result":"pending","tested_at":null,"os_version":null,"kernel":null,"ventoy_version":null,"vtoyboot_version":null,"plugin_sha256":null,"gpu":null,"network":null,"cold_boot":null,"after_update_boot":null,"original_windows_boot":null,"evidence_paths":[]}
```
