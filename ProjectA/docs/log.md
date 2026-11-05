# Project A 工作日志：Calgary 给水管网 Mini AMP

每天一条：日期 / 今天目标 / 做了什么 / 工具 / 问题和解决 / 截图编号

## 2026-11-04
- 目标：A0 数据和工具就绪检查
- 做了什么：
  - 从 Open Calgary 下载全量 CSV（9 个数据集）放到 data/raw/opendata_calgary；OSM 护理院/医院（Overpass）放到 data/raw/osm；从原 GEOG 588 项目备份里抽出社区年龄脆弱性图层放到 data/raw/legacy_588
  - 参考资料放 refs/：2020 Infrastructure Status Report、2026 CAMP Appendix B、Folkman 2018 爆管率研究
  - 全部原始数据转成一个 GeoPackage（data/interim，EPSG:4326，不做任何清洗），QGIS 里直接拖进去就能看
  - 初步检查结果写在 data/README.md（材质和爆管类型编码待解码、P_ZONE 空 1,466、管径 ≤0 有 14 条、年份 1900 待核实）
- 工具：Python（geopandas）
- 问题和解决：GeoPackage 不能直接写进同步文件夹（SQLite 锁）→ 先写本地再复制
