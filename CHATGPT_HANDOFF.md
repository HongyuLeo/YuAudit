# YuAudit 发布前修复交接

日期：2026-10-08。版本：v0.1.0。状态：用户已授权发布到 `HongyuLeo/YuAudit`；远端发布结果以 GitHub 页面为准。完整项目交接见 `PROJECT_HANDOFF.md`。

## 修改内容

### 编号标准化歧义

`yuaudit/engine.py` 在建立匹配组之前检查 PO 编号、发票编号及 SKU。同类单据的检查范围包含所有已导入文件；不同原始编号映射到同一匹配键时输出 `ambiguous_match`，保留所有冲突原值及来源证据，阻止涉及该键的匹配、数量/价格比较和声明总额汇总。发票编号歧义不会被当作已证实的重复开票。不受影响的商品继续核对。

仅含符号、标准化后为空的编号进入人工审核，即使关闭标准化也不匹配。两侧各自仅有一种无歧义写法时，仍可正常标准化匹配。策略偏保守：同类单据里的不同写法不会自动被解释为同一个业务实体，需要用户确认并修正后重跑。

原始复现 PO-1 数量 10 + PO1 数量 20、发票/装箱均指向 PO-1 数量 30：现在结果为 `review_required`，包含 PO 编号歧义，阻止错误合并。仅执行可独立核实的发票行金额计算，未执行跨单据汇总。`__main__.py` 的 EXE 冒烟流程也直接运行这个复现，确保打包引擎含修复。

### 实际分发许可证正文

`licenses/upstream/` 保存真实官方正文及 `manifest.json` 来源记录：

- openpyxl 3.1.5：官方 PyPI sdist 的 `LICENCE.rst`（MIT）。
- et_xmlfile 2.0.0：官方 PyPI sdist 的 `LICENCE.rst` 和 `LICENCE.python`。
- PySide6_Essentials / shiboken6 6.8.3：官方 Qt for Python `v6.8.3` 源码标签的 `LGPL-3.0-only.txt` 和 `GPL-3.0-only.txt`，各一份。

共 7 个补充正文。下载脚本 `scripts/fetch_official_licenses.py` 校验 PyPI 官方 archive SHA-256，并记录 URL、源码包成员、标签和正文 SHA-256。正常构建无需联网获取正文；`scripts/licenses.py` 从受版本及校验和约束的本地资源收集，必需文件缺失、版本不符或正文被改动时立即失败。保留原有商业许可证及其余第三方声明，同时补齐上述 LGPL 分发正文。

运行包内的 `THIRD_PARTY_LICENSES` 和 `_internal/THIRD_PARTY_LICENSES` 均含官方正文与来源记录。`scripts/verify_package_licenses.py` 检查最终 ZIP 的真实文件、完整性及正文 SHA-256，而不是只看元数据中的名称。

## 真实运行结果

环境：Windows 11 Pro x64 10.0.26200，Python 3.12.14 x64，PySide6 Essentials 6.8.3，PyInstaller 6.16.0。

- 全部 **62 tests passed in 1.89 s**，比此前新增 23 项回归/许可证测试。XML：`docs/test-results.xml`。
- 原始 PO 编号复现、三种字段在三种单据类型及跨文件的碰撞、空键、正常标准化匹配、无关组继续核对、声明总额阻断均通过。
- 许可证正文收集及缺失/篡改/版本不符失败测试通过；`pip check` 无依赖损坏。
- 真实 Windows EXE 重新构建成功。中文和英文冒烟均通过：3 份单据、32 项检查、8 条预期审查事项；CSV/XLSX/文本 PDF 解析及 JSON/XLSX/CSV 导出通过；打包引擎编号碰撞复现通过。
- ZIP 解压至 `build/中文 空格解压验证-20261008-183617`；清空 PYTHONHOME/PYTHONPATH，PATH 仅保留 Windows 目录，使用新建本地数据目录运行 EXE，英文完整冒烟通过。
- ZIP 许可证审计：31 个依赖包，两个许可证目录合计 180 次文件检查，每个目录 7 个官方补充正文与 Python 运行时正文全部通过。
- 大文件基准重新运行：3×5,000 行、30,000 项检查、0 异常；启用 tracemalloc 时 3.905 秒，Python 分配峰值 254.61 MB。此数值不是整个进程的总内存。

证据位于 `docs/verification/`：`final-smoke-zh/`、`final-smoke-en/`、`extracted-zip/`、`windows-build.txt`、`package-audit.json`。截图来自真实运行；报告仅包含虚构演示数据。此前的 39 项测试记录已由本轮结果更新。

## 发布文件准确位置

工作区交付根目录：

```text
C:\Users\PUBLIC_BUILD_USER\Documents\Codex\2026-10-08\codex-yuaudit-ai-windows-qa-windows\outputs
```

根目录文件：`YuAudit-Windows-x64.zip`、`YuAudit-Source-v0.1.0.zip`、`SHA256SUMS.txt`、`CHATGPT_HANDOFF.md`。

源码 Git 工作目录：根目录下 `YuAudit`。Git 源码将提交至 `HongyuLeo/YuAudit`，二进制通过 Release 分发。运行程序：

```text
C:\Users\PUBLIC_BUILD_USER\Documents\Codex\2026-10-08\codex-yuaudit-ai-windows-qa-windows\outputs\YuAudit\dist\YuAudit-Windows-x64\YuAudit.exe
```

源码 ZIP 排除 `.git`、构建目录、运行包、缓存和本地用户数据，包含源码、测试、官方许可证、双语文档、Windows CI、真实验证证据及本交接文件。最终两个 ZIP 的校验值以根目录 `SHA256SUMS.txt` 为准。

## 已知限制及未执行验证

- Windows 10 尚未实测；GitHub Actions 流程尚未在远端执行。
- 未安装真实 Ollama 模型；本地接口以 HTTP fixture 测试，AI 为可选辅助。
- EXE 未签名；目录式 ZIP，不提供安装器。
- OCR、自由排版 PDF、汇率换算、贷项、单位转换未实现；PDF 需要可识别的真实文本表格。
- UI 预览编辑前 500 行，其余行仍参与核对；每文件最多十万行。
- 默认本地保存会话和日志；人工修正不修改源文件。无遥测，不自动下载模型。

## 下次接手与发布

先阅读 `README.zh-CN.md`、`docs/VERIFICATION.md`，核验 `SHA256SUMS.txt`，完整解压运行包启动 EXE 并加载演示。若修改运行逻辑，重新执行全部测试和 `scripts/build.ps1`，重新生成两个 ZIP 及校验值；构建前移走旧目标目录，避免覆盖现有验收包。

用户最新指令已明确授权推送并发布 v0.1.0 Release，取代此前暂不发布的要求。需确认 GitHub 登录为 HongyuLeo、检查远程历史和 CI 结果，再验证上传资产。
