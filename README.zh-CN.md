# YuAudit
### 本地智能单据审查与差异核对工作台

英文副标题：Local AI Document Reconciliation Studio。首版 **v0.1.0**，面向采购、供应链、财务与贸易业务人员，默认离线处理。

[English](README.md) · [更新记录](CHANGELOG.md) · [第三方许可证](THIRD_PARTY_NOTICES.md)

![真实运行界面：中文浅色核对结果](docs/screenshots/zh-light-2.png)

截图来自实际运行的桌面程序。[英文深色界面](docs/screenshots/en-dark-2.png)。

## 安装与使用
解压 `YuAudit-Windows-x64.zip` 的完整目录，双击 `YuAudit-Windows-x64/YuAudit.exe`。不需要 Python、Node.js、API Key、登录或订阅。目标系统为 Windows 10/11 x64；实际验证环境见 `docs/VERIFICATION.md`。EXE 暂未代码签名。

1. 首页点击“加载演示数据”，或选择/拖入多个 Excel、CSV、文本表格 PDF。
2. 在“单据与映射”确认 PO / Invoice / Packing List 类型，调整列映射，双击预览单元格修正。不会修改原文件。Excel 编号若需保留前导零，请保存为文本。
3. 只有整个文件业务范围属于部分开票或出货时，勾选部分批次。一个文件可含多个发票编号。
4. 开始核对；任务在后台执行，可取消。结果可按严重程度筛选、按列排序、搜索编号，查看字段来源，打开原文件，记录人工审核备注。
5. 导出 Excel 多工作表报告、UTF-8 BOM CSV 异常清单或 JSON。Excel 包含汇总、异常、结构化数据和来源证据。数值以精确文本保存，避免 Excel 浮点精度损失。

界面默认中文，可即时切换英文以及浅色/深色主题。预览前 500 行，核对完整数据；单文件上限十万行。超出预览范围的修正，请编辑源文件副本后重新导入。

核对前检查同类单据内（包括不同文件）的 PO 编号、发票编号和 SKU 标准化碰撞。不同原始编号归一为同一个键时，提示歧义并阻止受影响的匹配及汇总；不会把 PO-1 与 PO1 两张订单静默合并。两侧各自只有一种无歧义写法时，保留正常标准化匹配。仅含符号的编号（如“-”）即使关闭标准化也不能匹配，必须人工修正。

## 核对规则
- 编号显式对应：PO 号限定比较范围；装箱单还需关联发票号。不猜测缺失编号。
- 精确、标准化标识符优先；受限模糊匹配只提供候选，必须人工修正后重跑。多个候选或标准化碰撞进入人工审核。
- 检查数量、单价、行金额计算、声明总金额、重复行、跨文件重复发票号、缺失/多出商品及编号关系。
- 金额使用 Decimal、64 位工作精度；输入最多 20 位有效数字和 8 位小数。金额与数量容差可配置。
- 币种缺失或不同会阻止金额比较；没有隐式汇率换算。
- 同 PO/SKU 的分批发票累加核对，装箱按 PO/发票/SKU 汇总。声明部分批次的短缺标为“余额待核实”，不是异常通过；超量仍报错。
- 重复行或价格依据不明确时，显示无法核实，不可靠地合并。
- 人工审核备注只记录审核，不改写原检测事实。“未发现异常”只针对已经核对的范围。

## 本地 AI
默认关闭。自行安装 Ollama 与模型后，在本地模型页填写已安装模型名称并启用。只接受本机回环 HTTP 地址，不自动下载模型，不连接远程业务服务。支持列名语义映射建议和摘要/解释草稿，Pydantic Schema 验证后展示。映射需人工应用；AI 不参与金额、数量计算与最终检测结论。报告中 AI 内容明确标为未核实草稿。没有 Ollama 仍可完整使用核心流程。

## 隐私与恢复
不发送遥测，不修改原始文件。设置、上次完整审查会话和有大小上限的错误日志保存在 `%LOCALAPPDATA%\YuAudit`。上次会话含业务字段和路径；删除此目录即可清除本地缓存。导出报告也包含业务数据。可用 `YUAUDIT_DATA_DIR` 指定独立数据目录。

## 架构与技术栈
采用 Python 3.12 + PySide6 原生桌面 UI，避免浏览器服务依赖；QThread 后台执行耗时任务；PyInstaller 目录式打包保证 Qt 与 Python 运行库一同交付。

| 层 | 模块 |
|---|---|
| 界面与任务管理 | `yuaudit/ui.py` |
| 文件解析 | `yuaudit/parsers.py` |
| 严格数据模型与来源 | `yuaudit/models.py` |
| 字段映射与标准化 | `yuaudit/normalize.py` |
| 独立核对引擎 | `yuaudit/engine.py` |
| AI Provider / Ollama | `yuaudit/ai.py` |
| 本地存储、日志 | `yuaudit/storage.py` |
| 报告导出 | `yuaudit/reports.py` |
| 中英文资源 | `yuaudit/i18n.py` |

## 开发与构建
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/create_assets.py
.venv\Scripts\python -m yuaudit
./scripts/build.ps1 -Python .venv\Scripts\python.exe
```

构建脚本执行测试、图标生成、依赖许可证收集、PyInstaller 打包，再真实启动 EXE，经 UI 完成演示导入、核对、报告和截图，成功后生成 ZIP。GitHub Actions 工作流在 Windows 重复此流程。尚未发布至 GitHub，不能视为已执行云端 CI。

```powershell
$env:YUAUDIT_DATA_DIR = "$PWD/build/test-profile"
dist/YuAudit-Windows-x64/YuAudit.exe --smoke-test build/manual-smoke --language en
```

## 演示与已知限制
演示供应商、商品和编号完全虚构。`demo/EXPECTED.md` 给出预期结果；正常商品和累计分批出货无异常，数量、单价、缺失、多出、重复和模糊匹配有明确结果。

首版文本 PDF 仅支持带表头、可识别边框的表格，每页/每表需要表头；扫描 PDF 明确提示未安装 OCR。未实现 OCR、自由排版 PDF 提取、应用内渲染式 PDF 阅读器、自动税费/折扣推断、贷项单、计量单位转换、汇率换算、任意 Excel 表头行选择、完整 GUI 分页编辑和自动 AI 配对。逗号只解释为千位分隔符，不支持小数逗号。Excel 公式需要已保存计算缓存；空值保持缺失。供应商、日期可提取但不独立校验。取消为协作式，单次底层 PDF/Excel 调用可能需等待，本地 AI 请求最长 60 秒。

## 许可证与发布
项目代码 MIT；Qt/PySide6 使用其自身许可证并以动态库分发。保留第三方声明及 `THIRD_PARTY_LICENSES` 文本目录；模型不随软件交付，需要独立检查许可证。

验收后创建空 GitHub 仓库，将本源码目录按 `.gitignore` 提交并推送；检查 Windows Actions 运行，创建 `v0.1.0` Release，上传 ZIP 与 SHA-256 校验值。不要提交业务文件、用户缓存、日志、模型权重或凭据。
