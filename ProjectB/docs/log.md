# Project B 工作日志：从巡检到工单

每天一条：日期 / 今天目标 / 做了什么 / 工具 / 问题和解决 / 截图编号

---

## 2026-10-31
- 目标：B1 准备资产表
- 做了什么：用 SODA API 从 Calgary Open Data 下载消火栓（5qgc-b482）、水管爆管（dpcu-jr23）、社区边界（surr-xmvs）；Python 点在多边形内筛选出试点区 114 个消火栓，按 200 m 内爆管次数算巡检优先级，输出 data/AM_Hydrants.csv
- 工具：Socrata SODA API（SoQL: within_box、$where）、Python（scripts/build_am_hydrants.py）
- 问题和解决：（1）CSV 里 last_inspect_date、last_condition 是空列，发布时被识别成 String 且不能改，发布后也不能改字段类型 → 发布时不导入这两列，发布后在 Data → Fields 里按 Date / Integer 新建；（2）within_box 是矩形，会带进周边社区的 437 个点 → 再用社区边界做点在多边形内（point-in-polygon）筛到 114 个

## 2026-11-01
- 目标：B1 收尾；B2 Survey123 巡检表单
- 做了什么：B1 发布 AM_Hydrants，设置下拉选项、编辑权限（只改属性）、附件；B2 用 Survey123 网页设计器做巡检表单，在 Modify schema 里统一改字段名
- 工具：ArcGIS Online、Survey123 web designer
- 问题和解决：（1）字段名 condition 是保留字 → 改成 cond_rating；（2）多道题都有 "Other" 选项，选项值重复报错 → 每题用不同的值（access_other / obstr_other / defect_other）；（3）多选题的选项值不用空格，改用下划线（如 snow_ice）

## 2026-11-02
- 目标：B3 收尾；B4 派工；B6 QC 与工单；B7 仪表盘；B8 文档
- 做了什么：
  - B3：消火栓弹窗用 Arcade（FeatureSetByName）显示最近一次巡检，加 Survey123 链接；截图 B3_01、B3_02
  - B4：新建任务图层 AM_Hydrant_Tasks（Field Maps Tasks），加 asset_id 字段；脚本给 26 个 High 消火栓建任务（Assigned，截止 2026-11-20），资产表同步改成 Assigned；任务弹窗里的 "▶ Start inspection" 链接预填 asset_id、task_id 和位置
  - B6：生成带标注的模拟巡检（data_origin = Simulated）；QC 脚本跑规则 R1–R6，通过的记录回写资产表，有缺陷或状况 ≥4 的生成工单（AM_WorkOrders）。结果：32 条记录，通过 30，失败 2（故意放的测试用例），工单 7 张（Urgent 5 / High 2）
  - B7：用脚本生成 Dashboard（3 个指标、2 个图表、地图、工单列表、数据说明）
  - B8：写 README、SOP、数据字典、QC 报告
- 工具：Field Maps Designer、Survey123、ArcGIS Notebook（ArcGIS API for Python）、ArcGIS Dashboards
- 问题和解决：
  1. Survey123 链接的 center 参数要经纬度，任务图层坐标是 Web Mercator → 弹窗里加 Arcade 表达式换算成经纬度
  2. R4 测试用例没触发（随机走到了"不可达"分支）→ 另加一条固定的测试记录（HYD-PKD-020）
  3. 仪表盘指标不显示数值 → 中间文字要写 {calculated/value}
  4. 仪表盘两个条形图报错 "Cannot read properties of undefined (reading 'enabled')" → 看浏览器控制台，错误出在数字前缀（SI prefix）格式化；脚本写的 numberPrefixOverrides 是空列表，Dashboards 5.1 要求 14 个前缀都有条目 → 对照一个公开的 5.1.0 仪表盘 JSON，补全前缀列表并把版本号改成 5.1.0，图表恢复正常；b7 脚本已同步修改
  5. Field Maps Designer 里改标签时输入被截断成 "R" → 先点进框 cmd+A 全选再重新输入
- 截图：B3_01_popup、B3_02_form_prefilled、B7_01_dashboard

## 2026-11-03
- 目标：B5 实地测试；重跑 QC；更新仪表盘和文档
- 做了什么：
  - B5：步行做了 Montgomery 的 5 个 High 任务（017、021、028、032、035），17:06–17:34（Alberta Time）。每个点都从 Field Maps 任务的 "▶ Start inspection" 打开 Survey123，提交后把任务改成 Completed
  - QC：新 Notebook 重跑 b6_qc_workorders.py。5 条实地记录全部通过（R5 第一次用真实照片验证，能识别 defect_photo 附件）；资产表回写 35 个；新增工单 3 张（WO-2026-0008 High、0009 Urgent、0010 High）
  - 仪表盘刷新：巡检 37 条、工单 10 张；截图 B7_02；现场照片整理成 B5_01–B5_06
  - 文档：qc_report_2026-11-03.md；README 加实地测试结果和发现
- 发现：
  1. 017、021 铸件年份 2024（几乎全新），028 是 1987 年的 Concord D-67M（漆面分层剥落）。City 开放数据没有安装年份，只有实地巡检能补上
  2. 两个 2024 年的新消火栓都在"200 m 内 4 次爆管"的区域，可能是近年维修时更换的——只是推测，待核实
  3. 032 侧面出水口挂着牌子，记为停用（out-of-order），按 SOP 评 5，生成 Urgent 工单
  4. 优先级规则偏粗：028、035 只是漆面问题，因为评 4 就成了 High，和倾斜、损坏同级 → 考虑 v1.1（外观问题降为 Normal）
- 问题和解决：
  1. 第一次从 Survey123 首页点 Collect 打开表单，不会带 asset_id/task_id → 改成必须从 Field Maps 任务弹窗进入（SOP 已写明）
  2. Notebook 换算出的时间比手机慢 1 小时：Alberta 从 2026-11-01 起改用永久 Alberta Time（UTC-6），Notebook 的时区数据库还按旧规则把 America/Edmonton 算成 MST（UTC-7）→ QC 脚本改用固定 UTC-6 偏移。本次只影响报告抬头的时间，不影响 R2 同日判断
  3. 028、035 没填 Notes；032 的 Notes 里留着占位符 "___"（牌子原文没填）；表单的通用照片题还是默认名 field_17 → 记入待办
- 截图：B5_01–B5_06、B7_02_dashboard_field_test

## 2026-11-04
- 目标：整理实地测试记录；确定优先级规则
- 做了什么：
  - 032 的牌子原文确认是 "OUT OF ORDER"，Notes 里的占位符换成原文；"Out-of -order" 多余的空格改掉
  - 028、035 的 Notes 按现场照片补上，结尾标注 "[Office note added 2026-11-04 from site photos]"，区分现场记录和事后补充
  - 优先级规则：决定保持现规则，不改（decisions.md 已更新）
- 工具：ArcGIS Notebook（edit_features）
- 问题和解决：Notebook 会话闲置几小时后断开 → 重新开一个 Notebook 继续
