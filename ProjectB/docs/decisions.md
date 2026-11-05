# Project B 决策记录

格式：选了什么 / 为什么 / 放弃了什么

- 派工工具用 Field Maps Tasks，不用 Workforce：Workforce 2026 年底退役，Esri 推荐 Tasks 替代
- 资产选消火栓：和 Project A 的给水主题一致；只做目测项目，不碰设施
- 试点区选 Montgomery + Parkdale + Point McKay（114 个消火栓）：Bearspaw 南干管（South Feeder Main）2024、2026 年两次爆管，boil-water advisory 覆盖了这三个社区的部分区域（见 GIS in Action 图 1）；能接上 Project A 和 GIS in Action 的故事线
- 数据只用 City of Calgary Open Data 的真实字段（位置、globalid（表里改名 city_globalid，避开 AGOL 系统字段 GlobalID）、owner、status、rotation）：City 没公开安装年份、型号，不编造属性
- 巡检优先级（inspect_priority）按周边爆管次数定：200 m 内 2016 年以来爆管 ≥3 次 = High，1–2 次 = Medium，0 次 = Low（结果 High 26 / Medium 48 / Low 40）。理由：爆管多说明附近管网老化、压力波动大，消火栓及其支管受影响的可能性更高。局限：只是代理指标（proxy），没用管材、管龄
- 演示数据用模拟巡检（2026-11-02）：每条都标 data_origin = Simulated，notes 以 "SIMULATED" 开头，模拟完成的任务备注也同样标注，仪表盘上写明；实地测试记录用 Field test，两类数据不混用。放弃了"只等实地数据再做仪表盘"：那样 QC、工单流程没法完整演示
- Montgomery 的 20 个 High 任务留给实地测试（B5）；其他两个社区的 6 个 High 任务用模拟数据完成
- QC 规则 R1–R6（见 SOP 第 6 节）：只有通过 QC 的记录才回写资产表、生成工单；失败的记录保留并写 qc_notes，不删除，方便复核
- 回写规则：每个消火栓取最新一条通过 QC 的记录，更新 insp_status、last_condition、last_inspect_date、last_insp_origin
- 工单优先级：状况 5 或有渗漏（Leaking）= Urgent；状况 4 = High；其他缺陷 = Normal。渗漏可能影响消防可用性，冬天还会结冰，所以优先
- 用 hosted table（AM_WorkOrders）模拟 CMMS（如 Cityworks、Maximo）的工单：作品集没有真实 CMMS，表里保留工单号、来源巡检、优先级、状态，演示"巡检 → 工单"的衔接
- 文档语言：README、SOP、数据字典用英文（给雇主看）；决策记录和工作日志保持中文
- 实地测试样本（2026-11-03）：5 个 Montgomery High 任务，按一条步行路线挑选，不是随机抽样；README 里写明它只用来验证流程，不代表社区整体状况
- 时区（2026-11-03）：Alberta 从 2026-11-01 起用永久 Alberta Time（UTC-6）。ArcGIS Notebook 的时区数据库还没更新，所以 QC 脚本不用 ZoneInfo("America/Edmonton")，改用固定 UTC-6。项目数据都在 2026 年 10 月之后，固定偏移对全部数据都对
- 【已决定 2026-11-04：保持现规则，不改】工单优先级 v1.1 讨论：实地测试发现只是漆面问题的记录（028、035）因为评 4 被排成 High。方案：外观类缺陷（Paint_markings、Obstructed）一律 Normal；功能类（Leaking、Damaged、Missing_caps、Leaning、停用）沿用现规则。如果以后采用，要同步改 SOP 第 8 节、QC 脚本，并重排未关闭的工单
