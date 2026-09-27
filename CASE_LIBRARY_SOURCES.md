# 案例库数据来源与校验说明

## 数据范围

内置案例共 **200 件**：

- 7 件人工精校的校园、就业、消费、租赁和个人信息指导性案例；
- 193 件由 `data/legal_cases_200.json` 提供的结构化指导性案例，主体为第 86—278 号，另补充居间、汽车消费、劳动合同和电信服务等早期日常生活案例。

案例来自不同层级、不同地区人民法院的生效裁判，经最高人民法院发布为指导性案例。内容覆盖校园权益、实习就业、租房、消费、网络安全、婚姻家庭、金融、交通、生命健康、知识产权、环境生态、行政法治、刑事风险和民商事。其中数据标注了 42 件“大学生高频”、131 件“社会热点”和 57 件“日常生活”相关案例（标签可交叉）。

## 权威性与可追溯性

- 主来源：[最高人民法院指导性案例](https://www.court.gov.cn/fabu/gengduo/151.html)。
- 结构化辅助来源：[`lttxzmj/chinese-law-corpus`](https://github.com/lttxzmj/chinese-law-corpus)，整理版本日期 2026-08-14，整理成果为 CC0-1.0。
- 每件案例保留 `source_url`、`source_external_id`、`source_hash` 和核验时间；界面的“查看官方原文”直接指向 `court.gov.cn`。
- 关联法条优先采用最高法原页列明的条文；原页未单列条号时，只给出法律名称和“需结合现行法核验”提示，不猜测条号。

## 图片策略

数据模型支持 `image_url`、`image_alt` 和 `image_source_url`。采集时只接受官方原页中与具体案例直接相关的正文图片，并排除网站 Logo、分享占位图、二维码、领导照片和来源不明图片。本批指导性案例原页为文本型页面，没有符合条件的案件图片，因此界面使用领域化视觉占位，不用无关图片冒充案件素材。

## 重建与检查

```powershell
python scripts/build_case_library.py `
  --source ..\_source_chinese_law_corpus\guiding-cases `
  --output data\legal_cases_200.json
python scripts/validate_case_library.py
```

生产环境不会在请求时爬取网站；已校验的快照随版本发布，避免官方页面临时不可用导致应用失效。
