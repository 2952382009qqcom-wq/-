# 案例库数据来源与校验说明

## 数据范围

内置案例共 **710 件**：

- 7 件人工精校的校园、就业、消费、租赁及个人信息指导性案例；
- 271 件由 `data/legal_cases_500.json` 提供的其他最高人民法院指导性案例；
- 222 件由同一文件提供的《最高人民法院公报》裁判文书选登案例。
- 10 件从最高人民法院 2025—2026 年典型案例发布原页人工整理的近年案例，见 `core/cases/recent_2026.py`。
- 200 件从最高人民法院 2023—2026 年 38 个典型案例发布原页整理的学生相关问题案例，见 `data/legal_cases_student_200.json`。涉及校园、求职劳动、网络信息、消费、住房、交通、家庭及刑事风险等。

222 件公报案例中，176 件刊于 2015 年及以后，其中 88 件刊于 2020 年及以后；其余 46 件为较早的典型裁判。这里的年份是**公报期次年份**，不是判决日期，也不是网站发布日。案例覆盖校园、就业、租房、消费、网络、家事、金融、交通、健康、知识产权、环境、行政、刑事及民商事等 14 个领域。个别领域的公开公报样本较少，不能把分类数量理解为真实案件发生率。

## 来源、摘录与局限

- 一手来源：[最高人民法院指导性案例](https://www.court.gov.cn/fabu/gengduo/151.html)、[《最高人民法院公报》裁判文书选登](https://gongbao.court.gov.cn/ArticleList.html?serial_no=cpwsxd)。
- 本轮 10 件直接来自最高人民法院的[网络法治典型案例](https://www.court.gov.cn/zixun/xiangqing/512041.html)、[平台经营与消费者权益典型案例](https://www.court.gov.cn/zixun/xiangqing/507691.html)、[涉民生诈骗典型案例](https://www.court.gov.cn/zixun/xiangqing/482861.html)。网页发布日期分别为 2026 年 9 月、2026 年 8 月、2025 年 12 月，不能当作各案判决日。每个案例保留独立的来源编号；同一批次的多个案例共享官方发布页 URL。
- 新增 200 件均保留对应最高人民法院原页链接及发布页内的独立案例编号。代表性来源包括[校园管理典型案例](https://www.court.gov.cn/zixun/xiangqing/463111.html)、[预付式消费典型案例](https://www.court.gov.cn/zixun/xiangqing/459331.html)和[网络食品安全典型案例](https://www.court.gov.cn/zixun/xiangqing/512551.html)。`published_at` 是网站发布日，不是判决日；未见明确裁判日的记录不填写 `decision_date`。
- 结构化辅助来源：[`lttxzmj/chinese-law-corpus`](https://github.com/lttxzmj/chinese-law-corpus)，本次使用提交 `ce5e48b4be0cccae3445dfeb9f0d2a94588208fe`，其整理成果标注为 CC0-1.0。
- 每件案例保留 `source_url`、`source_external_id` 和结构化内容的 `source_hash`。指导性案例保留官方摘要、要点、结果及理由；公报案例从公开裁判文书提取短段落，优先要求有事实、法院说理、裁判结果和法院明确提及的法律依据。自动摘录可能遗漏上下文，使用时应点击官方原文核对。
- 公报案例不把期次年份伪装成精确发布日期，也不猜测裁判日期。提及的法律可能是**裁判当时的历史版本**，不能直接作为今天的法律建议。前端只展示已核实的具体条号；没有条号时明确提示查看原文，不再以笼统法律名称充数。
- 新增案例的“关联法条”给出具体法律名称、条号、条文要点和与本案事实的联系，但属于**学习关联**，不表示原裁判一定直接援引该条；现行与案发时法条可能不同。部分案例的案情、处理结果及理由是从官方发布页提取或概括的短摘要，可能遗漏上下文。
- `verification_status=verified` 表示收录来源和结构化校验通过，**不代表全部 710 件均已人工逐字核验**。新增案例的来源域名、编号、日期、必需字段与条号经过批量检查；法律适用仍需结合官方原文复核。法院网站偶尔不可用，不影响离线快照查看，但会影响跳转原文。

## 图片策略

模型支持 `image_url`、`image_alt` 和 `image_source_url`。只收录官方原页中与具体案件直接相关、可核实来源的正文图片。这批案例未附加可确认属于特定案件的图片，不使用无关新闻图冒充案件素材。

## 重建与检查

在项目相邻目录取得上述语料库后：

```powershell
python scripts/build_case_library.py `
  --source ..\_source_chinese_law_corpus\guiding-cases `
  --gazette-source ..\_source_chinese_law_corpus\gazette-cases `
  --output data\legal_cases_500.json
python scripts/validate_case_library.py
python scripts/validate_student_cases.py
```

生产请求不会临时爬取法院网站；通过检查的快照随版本发布。更新案例时应重新运行校验、抽样人工核对，并核验现行法。此案例库只用于学习与检索，不替代专业法律意见。
