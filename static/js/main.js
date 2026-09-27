/**
 * 明鉴 — Frontend Logic
 * "Precision Justice" Edition
 */

// ===== State =====
let currentModule = "home";
let selectedContractType = "买卖合同";

const moduleExamples = {
  analyze: `民事起诉状
原告：王某，某大学学生。
被告：李某，某校外兼职中介负责人。
诉讼请求：1. 请求判令被告退还兼职押金2000元；2. 请求判令被告赔偿因虚假招聘造成的交通费、误工损失共计600元；3. 本案诉讼费用由被告承担。
事实与理由：2026年4月，原告通过网络平台看到被告发布的校园兼职招聘信息，被告承诺缴纳押金后即可安排长期兼职。原告转账2000元后，被告未安排任何工作，并多次以培训、名额保留等理由拒绝退款。原告保存了聊天记录、转账凭证及招聘页面截图。`,
  search: "大学生校外兼职被要求先交押金，后来没有安排工作也不退款，能否要求返还押金并主张赔偿？",
  review: `兼职服务协议
甲方：某信息咨询服务部
乙方：学生张某
第一条 乙方向甲方支付岗位保证金2000元，甲方负责推荐兼职岗位。
第二条 乙方缴费后不得以任何理由要求退还保证金。
第三条 甲方不保证岗位数量、工作时长及工资标准，解释权归甲方所有。
第四条 乙方如对岗位安排有异议，应先服从甲方管理，不得向平台投诉或公开发布相关信息。
第五条 本协议发生争议，由甲方所在地人民法院管辖。`,
  generate: {
    type: "起诉状",
    plaintiff: "张某",
    plaintiffAddress: "某市某区某大学学生宿舍",
    legalRepresentative: "",
    representativeDuty: "",
    representativeContact: "13800000000",
    agent: "",
    defendant: "某信息咨询服务部",
    defendantInfo: "经营者李某，住所地某市某区，联系方式：13900000000",
    claims: "请求判令被告退还保证金2000元；赔偿交通费、通讯费等合理损失300元；承担本案诉讼费用。",
    factsAndReasons: "2026年4月，原告通过网络平台看到被告发布的兼职招聘信息。被告要求原告先支付2000元岗位保证金，并承诺一周内安排兼职。原告转账后，被告未安排工作，也拒绝退款。被告行为已损害原告合法权益，故依法提起诉讼。",
    evidence: "招聘页面截图、微信聊天记录、转账凭证、电子协议；证人：王某，住所某市某区。",
    court: "某市某区人民法院",
    copyCount: "1",
    suer: "张某",
    date: "2026年5月26日"
  },
  generateAppeal: {
    type: "上诉状",
    appellant: "张某（一审原告）",
    appellantInfo: "男，2004年3月1日出生，汉族，某大学学生，住某市某区某大学学生宿舍",
    appellantContact: "13800000000",
    legalAgent: "",
    agent: "",
    appellee: "某信息咨询服务部（一审被告）",
    appelleeInfo: "经营者李某，住所地某市某区，联系方式：13900000000",
    caseParties: "张某因与某信息咨询服务部",
    cause: "服务合同纠纷",
    originalCourt: "某市某区人民法院",
    judgmentDate: "2026年5月10日",
    caseNumber: "(2026)某0101民初123号",
    judgmentType: "民事判决",
    appealRequests: "撤销原审判决第一项；依法改判被上诉人返还保证金2000元并赔偿合理损失300元；一、二审诉讼费用由被上诉人承担。",
    appealReasons: "原审判决对被上诉人收取岗位保证金后未履行安排兼职义务的事实认定不充分，对格式条款效力及上诉人损失承担问题适用法律不当。上诉人已提交转账凭证、聊天记录、招聘页面截图等证据，足以证明被上诉人构成违约。",
    court: "某市中级人民法院",
    copyCount: "1",
    date: "2026年5月26日"
  },
  generateDefense: {
    type: "答辩状",
    respondent: "李某",
    respondentInfo: "男，1988年6月1日生，汉族，某信息咨询服务部经营者，住某市某区",
    respondentContact: "13900000000",
    legalAgent: "",
    agent: "",
    originalCourt: "某市某区人民法院",
    caseNumber: "(2026)某0101民初123号",
    caseSummary: "张某诉某信息咨询服务部服务合同纠纷",
    defenseOpinion: "不同意原告全部诉讼请求。答辩人已按照双方约定提供岗位推荐服务，原告主张退还保证金及赔偿损失缺乏事实和法律依据；原告提交的聊天记录不能证明答辩人存在欺诈或根本违约。",
    evidence: "服务协议、岗位推荐记录、沟通记录；证人：王某，住所某市某区。",
    court: "某市某区人民法院",
    copyCount: "1",
    date: "2026年5月27日"
  },
  generateExecution: {
    type: "申请执行书",
    applicant: "张某",
    applicantInfo: "男，2004年3月1日出生，汉族，某大学学生，住某市某区某大学学生宿舍",
    applicantContact: "13800000000",
    legalAgent: "",
    agent: "",
    respondent: "某信息咨询服务部",
    respondentInfo: "经营者李某，住所地某市某区，联系方式：13900000000",
    caseParties: "申请执行人张某与被执行人某信息咨询服务部",
    cause: "服务合同纠纷",
    instrumentMaker: "某市某区人民法院",
    instrumentNumber: "(2026)某0101民初123号",
    instrumentType: "民事判决",
    obligor: "某信息咨询服务部",
    executionRequests: "强制执行被执行人返还保证金2000元；强制执行被执行人支付案件受理费及迟延履行期间的债务利息。",
    court: "某市某区人民法院",
    attachmentCount: "1",
    date: "2026年5月27日"
  },
  generateCounterclaim: {
    type: "反诉状",
    counterPlaintiff: "某信息咨询服务部",
    counterPlaintiffInfo: "经营者李某，男，1988年6月1日生，汉族，住某市某区",
    counterPlaintiffContact: "13900000000",
    legalAgent: "",
    agent: "",
    counterDefendant: "张某",
    counterDefendantInfo: "男，2004年3月1日出生，汉族，某大学学生，住某市某区某大学学生宿舍",
    counterclaimRequests: "请求判令反诉被告支付尚欠服务费用500元；请求判令反诉被告承担本案反诉费用。",
    factsAndReasons: "反诉原告已按照双方约定提供岗位推荐和信息咨询服务，反诉被告仍拖欠部分服务费用。为维护反诉原告合法权益，依法提起反诉。",
    evidence: "服务协议、岗位推荐记录、聊天记录、费用明细。",
    court: "某市某区人民法院",
    copyCount: "1",
    date: "2026年5月27日"
  },
  generateJurisdiction: {
    type: "管辖权异议书",
    objector: "某信息咨询服务部",
    objectorInfo: "经营者李某，男，1988年6月1日出生，汉族，住某市某区",
    objectorContact: "13900000000",
    legalAgent: "",
    agent: "",
    originalCourt: "某市某区人民法院",
    caseNumber: "(2026)某0101民初123号",
    caseSummary: "张某诉某信息咨询服务部服务合同纠纷",
    transferCourt: "某市某县人民法院",
    factsAndReasons: "本案合同履行地及被告住所地均不在原受理法院辖区，原受理法院对本案不具有管辖权。根据民事诉讼法关于地域管辖的规定，本案应移送有管辖权的人民法院审理。",
    court: "某市某区人民法院",
    date: "2026年5月27日"
  },
  generateConfirmation: {
    type: "司法确认申请书",
    applicantPerson: "张某",
    applicantPersonInfo: "男，2004年3月1日生，汉族，居民身份证：110000200403010000，工作单位：无，职业：学生，住某市某区，联系方式：13800000000",
    personAgent1: "",
    personAgent2: "",
    applicantOrg: "某信息咨询服务部",
    applicantOrgInfo: "住所：某市某区。统一社会信用代码：91300000000000000X",
    legalRepresentative: "李某，居民身份证：110000198806010000，职务：经营者，联系方式：13900000000",
    orgAgent1: "",
    orgAgent2: "",
    claims: "请求确认申请人双方于2026年5月20日达成的调解协议有效。",
    factsAndReasons: "申请人双方因服务合同纠纷发生争议，经人民调解委员会主持调解，自愿达成调解协议。协议内容系双方真实意思表示，不违反法律、行政法规的强制性规定，现共同申请司法确认。",
    court: "某市某区人民法院",
    date: "2026年5月27日"
  },
  generateAuthorization: {
    type: "公民授权委托书",
    principal: "张某",
    principalInfo: "男，2004年3月1日出生，汉族，某大学学生，住某市某区，联系方式：13800000000",
    lawyerAgent: "王律师，某某律师事务所律师，联系方式：13700000000",
    citizenAgent: "李某，男，1990年1月1日出生，汉族，某公司职员，住某市某区，联系方式：13600000000。受托人系委托人的近亲属",
    agentNames: "王律师、李某",
    caseSummary: "张某与某信息咨询服务部服务合同纠纷",
    agent1Name: "王律师",
    agent1Authority: "代为提交诉讼材料、参加庭审、进行辩论、签收法律文书。",
    agent2Name: "李某",
    agent2Authority: "代为收集和提交证据、参加调解、签收一般法律文书。",
    date: "2026年5月27日"
  },
  generateSalesContract: {
    type: "合同",
    contractType: "买卖合同",
    partyA: "某商贸有限公司",
    partyB: "张某",
    subject: "甲方向乙方出售笔记本电脑10台，品牌、型号、配置以双方确认的订单为准，质量应符合国家标准及产品说明。",
    price: "人民币50000元",
    payment: "乙方于合同签订后三日内支付全部价款至甲方指定账户。",
    delivery: "甲方应于收到全部价款后五日内将货物送至乙方指定地点；乙方应在收货后三日内完成验收。",
    breach: "任何一方迟延履行的，每逾期一日按合同总价款的万分之五向守约方支付违约金；造成损失的，还应赔偿损失。",
    dispute: "向合同签订地有管辖权的人民法院起诉",
    date: "2026年5月27日"
  },
  generateLeaseContract: {
    type: "合同",
    contractType: "房屋租赁合同",
    partyA: "李某",
    partyB: "张某",
    house: "房屋位于某市某区某路100号1单元101室，建筑面积约80平方米，用途为居住，附属设施以交接清单为准。",
    term: "自2026年6月1日起至2027年5月31日止",
    rent: "月租金人民币3000元，押金人民币3000元，租金按月支付。",
    fees: "租赁期间水、电、燃气、网络等费用由乙方承担；物业费由甲方承担，双方另有约定的除外。",
    breach: "乙方逾期支付租金超过七日的，甲方有权解除合同；任一方提前解除合同的，应提前三十日通知对方并承担相应违约责任。",
    dispute: "向房屋所在地人民法院起诉",
    date: "2026年5月27日"
  },
  generateLoanContract: {
    type: "合同",
    contractType: "借款合同",
    partyA: "张某",
    partyB: "李某",
    amount: "人民币100000元",
    purpose: "用于经营资金周转",
    term: "自2026年6月1日起至2026年12月31日止",
    repayment: "年利率6%，乙方于借款期限届满之日一次性偿还本金及利息。",
    guarantee: "王某自愿为乙方全部债务承担连带保证责任，保证期间为主债务履行期限届满之日起三年。",
    breach: "乙方逾期还款的，应按未还金额每日万分之五支付违约金，并承担甲方实现债权的合理费用。",
    date: "2026年5月27日"
  },
  generateServiceContract: {
    type: "合同",
    contractType: "服务合同",
    partyA: "某科技有限公司",
    partyB: "某咨询有限公司",
    content: "乙方为甲方提供企业合规咨询服务，包括制度梳理、风险清单、整改建议及书面报告。",
    term: "自2026年6月1日起至2026年8月31日止",
    fee: "服务费人民币80000元，甲方分两期支付，合同签订后支付50%，验收合格后支付50%。",
    acceptance: "乙方提交服务成果后，甲方应在七个工作日内完成验收；不合格的，乙方应在合理期限内整改。",
    breach: "乙方逾期交付或服务成果不符合约定的，应承担整改、减收服务费或赔偿损失等责任。",
    dispute: "向甲方所在地人民法院起诉",
    date: "2026年5月27日"
  },
  generateLaborContract: {
    type: "合同",
    contractType: "劳动合同",
    partyA: "某科技有限公司",
    partyB: "张某，居民身份证号码：110000200001010000",
    term: "固定期限，自2026年6月1日起至2029年5月31日止，试用期三个月",
    position: "产品经理，工作地点为某市某区",
    hours: "实行标准工时制度，甲方依法安排乙方休息休假。",
    salary: "月工资人民币12000元，每月10日前支付上月工资。",
    benefits: "甲方依法为乙方缴纳社会保险，福利待遇按甲方规章制度及法律规定执行。",
    breach: "双方解除、终止劳动合同及经济补偿按照法律法规执行；乙方应遵守保密义务。",
    date: "2026年5月27日"
  },
  strategy: {
    parties: "学生张某为维权方，某信息咨询服务部及经营者李某为相对方。",
    facts: "张某因校外兼职向对方支付2000元押金。对方承诺安排工作，但实际未履行，且拒绝退款。张某有招聘页面截图、聊天记录、转账凭证和多名同学类似经历。",
    dispute: "押金条款是否有效；对方是否构成虚假宣传或违约；张某应走消费者投诉、报警还是民事诉讼。",
    status: "已与对方沟通三次，对方只口头承诺处理，没有实际退款。"
  },
  student: {
    scenario: "校外兼职被骗",
    time: "2026年4月下旬",
    place: "校外兼职门店及线上招聘平台",
    opposite: "兼职中介负责人、平台招聘账号",
    facts: "我通过招聘平台看到兼职信息，对方要求先交2000元岗位押金，承诺一周内安排工作。我转账后一直没有被安排上岗，对方后来不回复消息，还说协议写明押金不退。",
    handling: "我已联系平台客服，但平台要求我补充证据；学校辅导员建议先整理材料。",
    evidence: "招聘页面截图、微信聊天记录、转账凭证、电子协议、同学证言。",
    claim: "退还押金，停止继续向学生收取费用，并明确后续投诉或诉讼路径。"
  }
};

function fillExample(module) {
  const ex = moduleExamples[module];
  if (!ex) return;
  switchModule(module);
  if (module === "analyze") {
    switchTab("analyze", "paste");
    document.getElementById("analyze-text").value = ex;
  } else if (module === "search") {
    document.getElementById("search-question").value = ex;
  } else if (module === "review") {
    switchTab("review", "paste");
    document.getElementById("review-text").value = ex;
  } else if (module === "generate") {
    const selectedType = document.getElementById("gen-doc-type").value;
    const activeExample = selectedType === "上诉状"
      ? moduleExamples.generateAppeal
      : selectedType === "答辩状"
        ? moduleExamples.generateDefense
        : selectedType === "申请执行书"
          ? moduleExamples.generateExecution
          : selectedType === "反诉状"
            ? moduleExamples.generateCounterclaim
            : selectedType === "管辖权异议书"
              ? moduleExamples.generateJurisdiction
              : selectedType === "司法确认申请书"
                ? moduleExamples.generateConfirmation
                : selectedType === "公民授权委托书"
                  ? moduleExamples.generateAuthorization
                  : selectedType === "合同"
                    ? contractExampleByType(selectedContractType)
        : ex;
    document.getElementById("gen-doc-type").value = activeExample.type;
    onGenerateDocTypeChange();
    if (activeExample.type === "上诉状") {
      fillAppealExample(activeExample);
      return;
    }
    if (activeExample.type === "答辩状") {
      fillDefenseExample(activeExample);
      return;
    }
    if (activeExample.type === "申请执行书") {
      fillExecutionExample(activeExample);
      return;
    }
    if (activeExample.type === "反诉状") {
      fillCounterclaimExample(activeExample);
      return;
    }
    if (activeExample.type === "管辖权异议书") {
      fillJurisdictionExample(activeExample);
      return;
    }
    if (activeExample.type === "司法确认申请书") {
      fillConfirmationExample(activeExample);
      return;
    }
    if (activeExample.type === "公民授权委托书") {
      fillAuthorizationExample(activeExample);
      return;
    }
    if (activeExample.type === "合同") {
      chooseContractType(activeExample.contractType || selectedContractType, false);
      fillContractExample(activeExample);
      return;
    }
    document.getElementById("gen-plaintiff").value = ex.plaintiff;
    document.getElementById("gen-plaintiff-address").value = ex.plaintiffAddress;
    document.getElementById("gen-legal-representative").value = ex.legalRepresentative;
    document.getElementById("gen-representative-duty").value = ex.representativeDuty;
    document.getElementById("gen-representative-contact").value = ex.representativeContact;
    document.getElementById("gen-agent").value = ex.agent;
    document.getElementById("gen-defendant").value = ex.defendant;
    document.getElementById("gen-defendant-info").value = ex.defendantInfo;
    document.getElementById("gen-claims").value = ex.claims;
    document.getElementById("gen-facts-reasons").value = ex.factsAndReasons;
    document.getElementById("gen-evidence").value = ex.evidence;
    document.getElementById("gen-court").value = ex.court;
    document.getElementById("gen-copy-count").value = ex.copyCount;
    document.getElementById("gen-suer").value = ex.suer;
    document.getElementById("gen-date").value = ex.date;
  } else if (module === "strategy") {
    document.getElementById("strategy-parties").value = ex.parties;
    document.getElementById("strategy-facts").value = ex.facts;
    document.getElementById("strategy-dispute").value = ex.dispute;
    document.getElementById("strategy-status").value = ex.status;
  } else if (module === "student") {
    document.getElementById("student-scenario").value = ex.scenario;
    document.getElementById("student-time").value = ex.time;
    document.getElementById("student-place").value = ex.place;
    document.getElementById("student-opposite").value = ex.opposite;
    document.getElementById("student-facts").value = ex.facts;
    document.getElementById("student-handling").value = ex.handling;
    document.getElementById("student-evidence").value = ex.evidence;
    document.getElementById("student-claim").value = ex.claim;
  }
}

function fillAppealExample(ex) {
  document.getElementById("appeal-appellant").value = ex.appellant;
  document.getElementById("appeal-appellant-info").value = ex.appellantInfo;
  document.getElementById("appeal-appellant-contact").value = ex.appellantContact;
  document.getElementById("appeal-legal-agent").value = ex.legalAgent;
  document.getElementById("appeal-agent").value = ex.agent;
  document.getElementById("appeal-appellee").value = ex.appellee;
  document.getElementById("appeal-appellee-info").value = ex.appelleeInfo;
  document.getElementById("appeal-case-parties").value = ex.caseParties;
  document.getElementById("appeal-cause").value = ex.cause;
  document.getElementById("appeal-original-court").value = ex.originalCourt;
  document.getElementById("appeal-judgment-date").value = ex.judgmentDate;
  document.getElementById("appeal-case-number").value = ex.caseNumber;
  document.getElementById("appeal-judgment-type").value = ex.judgmentType;
  document.getElementById("appeal-requests").value = ex.appealRequests;
  document.getElementById("appeal-reasons").value = ex.appealReasons;
  document.getElementById("appeal-court").value = ex.court;
  document.getElementById("appeal-copy-count").value = ex.copyCount;
  document.getElementById("appeal-date").value = ex.date;
}

function fillDefenseExample(ex) {
  document.getElementById("defense-respondent").value = ex.respondent;
  document.getElementById("defense-respondent-info").value = ex.respondentInfo;
  document.getElementById("defense-respondent-contact").value = ex.respondentContact;
  document.getElementById("defense-legal-agent").value = ex.legalAgent;
  document.getElementById("defense-agent").value = ex.agent;
  document.getElementById("defense-original-court").value = ex.originalCourt;
  document.getElementById("defense-case-number").value = ex.caseNumber;
  document.getElementById("defense-case-summary").value = ex.caseSummary;
  document.getElementById("defense-opinion").value = ex.defenseOpinion;
  document.getElementById("defense-evidence").value = ex.evidence;
  document.getElementById("defense-court").value = ex.court;
  document.getElementById("defense-copy-count").value = ex.copyCount;
  document.getElementById("defense-date").value = ex.date;
}

function fillExecutionExample(ex) {
  document.getElementById("execution-applicant").value = ex.applicant;
  document.getElementById("execution-applicant-info").value = ex.applicantInfo;
  document.getElementById("execution-applicant-contact").value = ex.applicantContact;
  document.getElementById("execution-legal-agent").value = ex.legalAgent;
  document.getElementById("execution-agent").value = ex.agent;
  document.getElementById("execution-respondent").value = ex.respondent;
  document.getElementById("execution-respondent-info").value = ex.respondentInfo;
  document.getElementById("execution-case-parties").value = ex.caseParties;
  document.getElementById("execution-cause").value = ex.cause;
  document.getElementById("execution-instrument-maker").value = ex.instrumentMaker;
  document.getElementById("execution-instrument-number").value = ex.instrumentNumber;
  document.getElementById("execution-instrument-type").value = ex.instrumentType;
  document.getElementById("execution-obligor").value = ex.obligor;
  document.getElementById("execution-requests").value = ex.executionRequests;
  document.getElementById("execution-court").value = ex.court;
  document.getElementById("execution-attachment-count").value = ex.attachmentCount;
  document.getElementById("execution-date").value = ex.date;
}

function fillCounterclaimExample(ex) {
  document.getElementById("counterclaim-plaintiff").value = ex.counterPlaintiff;
  document.getElementById("counterclaim-plaintiff-info").value = ex.counterPlaintiffInfo;
  document.getElementById("counterclaim-plaintiff-contact").value = ex.counterPlaintiffContact;
  document.getElementById("counterclaim-legal-agent").value = ex.legalAgent;
  document.getElementById("counterclaim-agent").value = ex.agent;
  document.getElementById("counterclaim-defendant").value = ex.counterDefendant;
  document.getElementById("counterclaim-defendant-info").value = ex.counterDefendantInfo;
  document.getElementById("counterclaim-requests").value = ex.counterclaimRequests;
  document.getElementById("counterclaim-facts-reasons").value = ex.factsAndReasons;
  document.getElementById("counterclaim-evidence").value = ex.evidence;
  document.getElementById("counterclaim-court").value = ex.court;
  document.getElementById("counterclaim-copy-count").value = ex.copyCount;
  document.getElementById("counterclaim-date").value = ex.date;
}

function fillJurisdictionExample(ex) {
  document.getElementById("jurisdiction-objector").value = ex.objector;
  document.getElementById("jurisdiction-objector-info").value = ex.objectorInfo;
  document.getElementById("jurisdiction-objector-contact").value = ex.objectorContact;
  document.getElementById("jurisdiction-legal-agent").value = ex.legalAgent;
  document.getElementById("jurisdiction-agent").value = ex.agent;
  document.getElementById("jurisdiction-original-court").value = ex.originalCourt;
  document.getElementById("jurisdiction-case-number").value = ex.caseNumber;
  document.getElementById("jurisdiction-case-summary").value = ex.caseSummary;
  document.getElementById("jurisdiction-transfer-court").value = ex.transferCourt;
  document.getElementById("jurisdiction-facts-reasons").value = ex.factsAndReasons;
  document.getElementById("jurisdiction-court").value = ex.court;
  document.getElementById("jurisdiction-date").value = ex.date;
}

function fillConfirmationExample(ex) {
  document.getElementById("confirm-applicant-person").value = ex.applicantPerson;
  document.getElementById("confirm-applicant-person-info").value = ex.applicantPersonInfo;
  document.getElementById("confirm-person-agent-1").value = ex.personAgent1;
  document.getElementById("confirm-person-agent-2").value = ex.personAgent2;
  document.getElementById("confirm-applicant-org").value = ex.applicantOrg;
  document.getElementById("confirm-applicant-org-info").value = ex.applicantOrgInfo;
  document.getElementById("confirm-legal-representative").value = ex.legalRepresentative;
  document.getElementById("confirm-org-agent-1").value = ex.orgAgent1;
  document.getElementById("confirm-org-agent-2").value = ex.orgAgent2;
  document.getElementById("confirm-claims").value = ex.claims;
  document.getElementById("confirm-facts-reasons").value = ex.factsAndReasons;
  document.getElementById("confirm-court").value = ex.court;
  document.getElementById("confirm-date").value = ex.date;
}

function fillAuthorizationExample(ex) {
  document.getElementById("auth-principal").value = ex.principal;
  document.getElementById("auth-principal-info").value = ex.principalInfo;
  document.getElementById("auth-lawyer-agent").value = ex.lawyerAgent;
  document.getElementById("auth-citizen-agent").value = ex.citizenAgent;
  document.getElementById("auth-agent-names").value = ex.agentNames;
  document.getElementById("auth-case-summary").value = ex.caseSummary;
  document.getElementById("auth-agent-1-name").value = ex.agent1Name;
  document.getElementById("auth-agent-1-authority").value = ex.agent1Authority;
  document.getElementById("auth-agent-2-name").value = ex.agent2Name;
  document.getElementById("auth-agent-2-authority").value = ex.agent2Authority;
  document.getElementById("auth-date").value = ex.date;
}

function contractExampleByType(contractType) {
  return {
    "买卖合同": moduleExamples.generateSalesContract,
    "房屋租赁合同": moduleExamples.generateLeaseContract,
    "借款合同": moduleExamples.generateLoanContract,
    "服务合同": moduleExamples.generateServiceContract,
    "劳动合同": moduleExamples.generateLaborContract,
  }[contractType] || moduleExamples.generateSalesContract;
}

function fillContractExample(ex) {
  const t = ex.contractType || selectedContractType;
  if (t === "买卖合同") {
    document.getElementById("sales-party-a").value = ex.partyA;
    document.getElementById("sales-party-b").value = ex.partyB;
    document.getElementById("sales-subject").value = ex.subject;
    document.getElementById("sales-price").value = ex.price;
    document.getElementById("sales-payment").value = ex.payment;
    document.getElementById("sales-delivery").value = ex.delivery;
    document.getElementById("sales-breach").value = ex.breach;
    document.getElementById("sales-dispute").value = ex.dispute;
    document.getElementById("sales-date").value = ex.date;
  } else if (t === "房屋租赁合同") {
    document.getElementById("lease-party-a").value = ex.partyA;
    document.getElementById("lease-party-b").value = ex.partyB;
    document.getElementById("lease-house").value = ex.house;
    document.getElementById("lease-term").value = ex.term;
    document.getElementById("lease-rent").value = ex.rent;
    document.getElementById("lease-fees").value = ex.fees;
    document.getElementById("lease-breach").value = ex.breach;
    document.getElementById("lease-dispute").value = ex.dispute;
    document.getElementById("lease-date").value = ex.date;
  } else if (t === "借款合同") {
    document.getElementById("loan-party-a").value = ex.partyA;
    document.getElementById("loan-party-b").value = ex.partyB;
    document.getElementById("loan-amount").value = ex.amount;
    document.getElementById("loan-purpose").value = ex.purpose;
    document.getElementById("loan-term").value = ex.term;
    document.getElementById("loan-repayment").value = ex.repayment;
    document.getElementById("loan-guarantee").value = ex.guarantee;
    document.getElementById("loan-breach").value = ex.breach;
    document.getElementById("loan-date").value = ex.date;
  } else if (t === "服务合同") {
    document.getElementById("service-party-a").value = ex.partyA;
    document.getElementById("service-party-b").value = ex.partyB;
    document.getElementById("service-content").value = ex.content;
    document.getElementById("service-term").value = ex.term;
    document.getElementById("service-fee").value = ex.fee;
    document.getElementById("service-acceptance").value = ex.acceptance;
    document.getElementById("service-breach").value = ex.breach;
    document.getElementById("service-dispute").value = ex.dispute;
    document.getElementById("service-date").value = ex.date;
  } else if (t === "劳动合同") {
    document.getElementById("labor-party-a").value = ex.partyA;
    document.getElementById("labor-party-b").value = ex.partyB;
    document.getElementById("labor-term").value = ex.term;
    document.getElementById("labor-position").value = ex.position;
    document.getElementById("labor-hours").value = ex.hours;
    document.getElementById("labor-salary").value = ex.salary;
    document.getElementById("labor-benefits").value = ex.benefits;
    document.getElementById("labor-breach").value = ex.breach;
    document.getElementById("labor-date").value = ex.date;
  }
}

function openContractPicker() {
  document.getElementById("contract-picker").classList.remove("hidden");
}

function closeContractPicker() {
  document.getElementById("contract-picker").classList.add("hidden");
}

function chooseContractType(contractType, closePicker = true) {
  selectedContractType = contractType || "买卖合同";
  document.getElementById("gen-doc-type").value = "合同";
  document.getElementById("contract-selected-name").textContent = selectedContractType;
  document.getElementById("contract-selected-bar").classList.remove("hidden");
  onGenerateDocTypeChange(false);
  if (closePicker) closeContractPicker();
}

function onGenerateDocTypeChange() {
  const docType = document.getElementById("gen-doc-type").value;
  const hadContractSelected = !document.getElementById("contract-selected-bar").classList.contains("hidden");
  document.getElementById("complaint-form").classList.toggle("hidden", docType !== "起诉状");
  document.getElementById("appeal-form").classList.toggle("hidden", docType !== "上诉状");
  document.getElementById("defense-form").classList.toggle("hidden", docType !== "答辩状");
  document.getElementById("execution-form").classList.toggle("hidden", docType !== "申请执行书");
  document.getElementById("counterclaim-form").classList.toggle("hidden", docType !== "反诉状");
  document.getElementById("jurisdiction-form").classList.toggle("hidden", docType !== "管辖权异议书");
  document.getElementById("judicial-confirmation-form").classList.toggle("hidden", docType !== "司法确认申请书");
  document.getElementById("citizen-authorization-form").classList.toggle("hidden", docType !== "公民授权委托书");
  document.getElementById("contract-selected-bar").classList.toggle("hidden", docType !== "合同");
  document.getElementById("sales-contract-form").classList.toggle("hidden", docType !== "合同" || selectedContractType !== "买卖合同");
  document.getElementById("lease-contract-form").classList.toggle("hidden", docType !== "合同" || selectedContractType !== "房屋租赁合同");
  document.getElementById("loan-contract-form").classList.toggle("hidden", docType !== "合同" || selectedContractType !== "借款合同");
  document.getElementById("service-contract-form").classList.toggle("hidden", docType !== "合同" || selectedContractType !== "服务合同");
  document.getElementById("labor-contract-form").classList.toggle("hidden", docType !== "合同" || selectedContractType !== "劳动合同");
  if (docType === "合同") {
    document.getElementById("contract-selected-name").textContent = selectedContractType;
    if (!hadContractSelected) openContractPicker();
  }
}

// ===== Module Navigation =====
document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", function() {
    switchModule(this.dataset.module);
  });
});

function switchModule(module) {
  currentModule = module;
  document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
  const professionalModules = new Set(["analyze", "search", "review", "generate", "strategy", "student"]);
  const navTarget = professionalModules.has(module) ? "tools" : module;
  const navBtn = document.querySelector(`[data-module="${navTarget}"]`);
  if (navBtn) navBtn.classList.add("active");

  document.querySelectorAll(".module").forEach(m => {
    m.classList.remove("active");
    m.classList.add("hidden");
  });
  const el = document.getElementById(`module-${module}`);
  if (el) { el.classList.remove("hidden"); el.classList.add("active"); }

  const backButton = document.getElementById("professional-back");
  if (backButton) backButton.classList.toggle("hidden", !professionalModules.has(module));
  if (module === "home") loadAgentConversations();
  if (module === "community" && typeof initCommunity === "function") initCommunity();
  if (module === "cases" && typeof initCases === "function") initCases();

  document.querySelector(".content").scrollTop = 0;
}

function openWorkspaceTask(module, withExample = false) {
  switchModule(module);
  if (withExample) fillExample(module);
}

function workspaceModuleLabel(module) {
  const labels = {
    analyze: "文书分析",
    search: "法规检索",
    review: "合同审查",
    generate: "文书生成",
    strategy: "策略分析",
    student_legal: "学生法律",
  };
  return labels[module] || "法律任务";
}

async function loadWorkspaceOverview() {
  const recentEl = document.getElementById("workspace-recent-list");
  if (!recentEl || !window._user) return;

  document.getElementById("workspace-username").textContent = window._user.username || "用户";
  updateWorkspaceQuota();

  try {
    const [statusResp, historyResp] = await Promise.all([
      fetch("/api/status"),
      fetch("/api/history"),
    ]);
    if (statusResp.ok) {
      const status = await statusResp.json();
      document.getElementById("workspace-kb-provisions").textContent = Number(status.kb_provisions || 0).toLocaleString("zh-CN");
      document.getElementById("workspace-kb-risks").textContent = Number(status.kb_risks || 0).toLocaleString("zh-CN");
    }
    if (historyResp.ok) {
      const history = await historyResp.json();
      const records = (history.records || []).slice(0, 3);
      recentEl.innerHTML = records.length ? records.map(record => {
        const label = workspaceModuleLabel(record.module_type);
        const target = record.module_type === "student_legal" ? "student" : record.module_type;
        const summary = (record.input_text || "未命名任务").replace(/\s+/g, " ").slice(0, 58);
        return `<button type="button" class="workspace-recent-item" onclick="openWorkspaceTask('${escapeHtml(target)}')">
          <span><b>${escapeHtml(label)}</b><time>${escapeHtml(record.created_at || "")}</time></span>
          <p>${escapeHtml(summary)}</p>
        </button>`;
      }).join("") : '<p class="workspace-empty">完成一次分析后，任务会出现在这里。</p>';
    }
  } catch (e) {
    recentEl.innerHTML = '<p class="workspace-empty">最近任务暂时无法加载。</p>';
  }
}

function updateWorkspaceQuota() {
  const el = document.getElementById("workspace-quota");
  const u = window._user;
  if (!el || !u) return;
  if (u.is_admin || u.is_approved || u.has_llm_api_key) {
    el.textContent = "不限";
  } else {
    const remaining = Number.isFinite(Number(u.free_api_remaining)) ? Number(u.free_api_remaining) : 10;
    el.textContent = remaining;
  }
}

// ===== MingJian Legal Agent =====
const legalAgentState = {
  conversationId: null,
  messages: [],
  file: null,
  action: "",
  sending: false,
  lastResult: null,
  welcomeMarkup: "",
};

document.addEventListener("DOMContentLoaded", () => {
  const list = document.getElementById("agent-message-list");
  if (list) legalAgentState.welcomeMarkup = list.innerHTML;
});

function resizeAgentComposer(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
}

function handleAgentComposerKey(event) {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    submitLegalAgent();
  }
}

function setAgentAction(action, button = null) {
  const next = legalAgentState.action === action ? "" : action;
  legalAgentState.action = next;
  document.querySelectorAll("[data-agent-action]").forEach(el => {
    el.classList.toggle("active", el.dataset.agentAction === next);
  });
  if (button && next) document.getElementById("agent-input")?.focus();
}

function useAgentStarter(message, action = "") {
  const input = document.getElementById("agent-input");
  if (!input) return;
  input.value = message;
  resizeAgentComposer(input);
  if (action) setAgentAction(action, document.querySelector(`[data-agent-action="${action}"]`));
  input.focus();
}

function formatFileSize(size) {
  if (!Number.isFinite(Number(size))) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function onAgentFileSelected(input, fromCamera = false) {
  const file = input && input.files && input.files[0];
  if (!file) return;
  if (file.size > 15 * 1024 * 1024) {
    alert("附件不能超过 15 MB");
    input.value = "";
    return;
  }
  legalAgentState.file = file;
  const box = document.getElementById("agent-attachment");
  document.getElementById("agent-attachment-name").textContent = file.name || "现场照片";
  document.getElementById("agent-attachment-meta").textContent = `${fromCamera ? "拍照" : "附件"} · ${formatFileSize(file.size)} · 将自动识别并脱敏`;
  const suffix = (file.name || "IMG").split(".").pop().slice(0, 4).toUpperCase();
  document.getElementById("agent-attachment-thumb").textContent = suffix || "FILE";
  box.classList.remove("hidden");
  document.getElementById("agent-input")?.focus();
}

function clearAgentAttachment() {
  legalAgentState.file = null;
  ["agent-file", "agent-camera"].forEach(id => {
    const input = document.getElementById(id);
    if (input) input.value = "";
  });
  document.getElementById("agent-attachment")?.classList.add("hidden");
}

function formatAgentText(text) {
  const safe = escapeHtml(String(text || ""));
  const lines = safe.split(/\r?\n/);
  let html = "";
  let inList = false;
  for (const line of lines) {
    const bullet = line.match(/^\s*[-•]\s+(.+)/);
    if (bullet) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${bullet[1]}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (line.trim()) html += `<p>${line}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html || "<p>暂无内容</p>";
}

function scrollAgentToBottom() {
  const list = document.getElementById("agent-message-list");
  if (list) requestAnimationFrame(() => { list.scrollTop = list.scrollHeight; });
}

function appendAgentMessage(role, content, options = {}) {
  const list = document.getElementById("agent-message-list");
  if (!list) return null;
  const article = document.createElement("article");
  article.className = `agent-message ${role}`;
  const attachment = options.attachment
    ? `<div class="agent-attachment-inline">附件：${escapeHtml(options.attachment.name || options.attachment.filename || "材料")}</div>`
    : "";
  article.innerHTML = `<div class="agent-message-avatar">${role === "user" ? "我" : "明"}</div>
    <div class="agent-message-body">
      <div class="agent-message-name">${role === "user" ? "你" : "明鉴法律智能体"}</div>
      <div class="agent-message-content${options.error ? " agent-error" : ""}">${formatAgentText(content)}${attachment}</div>
      <div class="agent-result-details"></div>
      <div class="agent-message-tools"></div>
    </div>`;
  list.appendChild(article);
  scrollAgentToBottom();
  return article;
}

function appendAgentPending() {
  const article = appendAgentMessage("assistant", "");
  if (!article) return null;
  const content = article.querySelector(".agent-message-content");
  content.innerHTML = '<div class="agent-stage">正在理解问题与识别任务</div>';
  return article;
}

function renderAgentResultDetails(result) {
  let html = "";
  if (result.document && result.document.body) {
    const doc = result.document;
    html += `<div class="result-section-title">${escapeHtml(doc.title || "法律文书初稿")}</div>
      <div class="document-preview"><pre>${escapeHtml(doc.body)}</pre></div>`;
  }
  return html;
}

function finishAgentMessage(article, result) {
  const content = article.querySelector(".agent-message-content");
  const details = article.querySelector(".agent-result-details");
  const tools = article.querySelector(".agent-message-tools");
  if (result.error) {
    content.classList.add("agent-error");
    content.innerHTML = formatAgentText(result.error);
    return;
  }
  content.innerHTML = formatAgentText(result.answer || "已完成处理。");
  details.innerHTML = renderAgentResultDetails(result);
  const followUps = Array.isArray(result.suggested_follow_ups) ? result.suggested_follow_ups.slice(0, 4) : [];
  tools.innerHTML = "";
  followUps.forEach(value => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(value);
    button.addEventListener("click", () => useAgentStarter(String(value)));
    tools.appendChild(button);
  });
  if (result.document && result.can_export) {
    const documentButton = document.createElement("button");
    documentButton.type = "button";
    documentButton.textContent = "导出 Word";
    documentButton.addEventListener("click", exportAgentDocument);
    tools.appendChild(documentButton);
  }
  if (result.conversation_id || legalAgentState.conversationId) {
    const communityButton = document.createElement("button");
    communityButton.type = "button";
    communityButton.textContent = "整理为匿名求助";
    communityButton.addEventListener("click", openAiCommunityDraft);
    tools.appendChild(communityButton);
  }
  const exportButton = document.createElement("button");
  exportButton.type = "button";
  exportButton.textContent = "导出本次会话";
  exportButton.addEventListener("click", exportAgentConversation);
  tools.appendChild(exportButton);
  scrollAgentToBottom();
}

async function submitLegalAgent() {
  if (legalAgentState.sending) return;
  const input = document.getElementById("agent-input");
  let message = (input?.value || "").trim();
  if (!message && !legalAgentState.file) return;
  if (!message) message = "请分析这份附件，并告诉我关键问题和下一步建议。";

  const file = legalAgentState.file;
  appendAgentMessage("user", message, { attachment: file ? { name: file.name } : null });
  legalAgentState.messages.push({ role: "user", content: message });
  if (input) { input.value = ""; resizeAgentComposer(input); }

  const pending = appendAgentPending();
  const send = document.getElementById("agent-send");
  legalAgentState.sending = true;
  if (send) send.disabled = true;

  const form = new FormData();
  form.append("message", message);
  if (legalAgentState.conversationId) form.append("conversation_id", legalAgentState.conversationId);
  if (legalAgentState.action) form.append("action", legalAgentState.action);
  form.append("client_messages", JSON.stringify(legalAgentState.messages.slice(-16)));
  if (file) form.append("file", file, file.name);

  try {
    const response = await fetch("/api/legal-agent-stream", { method: "POST", body: form });
    syncFreeQuotaFromResponse(response);
    if (response.status === 401) { showAuth(); throw new Error("请先登录"); }
    if (!response.ok || !response.body) {
      const type = response.headers.get("content-type") || "";
      const body = type.includes("application/json") ? await response.json() : {};
      throw new Error(body.error || `服务异常 (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let streamed = "";
    let finalResult = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        const line = block.split("\n").find(item => item.startsWith("data: "));
        if (!line) continue;
        let event;
        try { event = JSON.parse(line.slice(6)); } catch (_) { continue; }
        if (event.stage) {
          const stageEl = pending.querySelector(".agent-message-content");
          stageEl.innerHTML = `<div class="agent-stage">${escapeHtml(event.status || "正在处理")}</div>`;
        } else if (event.chunk) {
          streamed += event.chunk;
          pending.querySelector(".agent-message-content").innerHTML = `<div class="agent-cursor">${formatAgentText(streamed)}</div>`;
          scrollAgentToBottom();
        } else if (event.done) {
          finalResult = event.result || {};
        }
      }
    }
    if (!finalResult) throw new Error("流式响应异常结束");
    finishAgentMessage(pending, finalResult);
    if (finalResult.conversation_id) legalAgentState.conversationId = finalResult.conversation_id;
    legalAgentState.lastResult = finalResult;
    legalAgentState.messages.push({ role: "assistant", content: finalResult.answer || "", result: finalResult });
    clearAgentAttachment();
    setAgentAction("");
    updateQuotaHint();
    loadAgentConversations();
  } catch (error) {
    finishAgentMessage(pending, { error: error.message || "请求失败" });
  } finally {
    legalAgentState.sending = false;
    if (send) send.disabled = false;
  }
}

async function loadAgentConversations() {
  const rail = document.getElementById("agent-session-list");
  const drawer = document.getElementById("agent-history-content");
  if (!rail || !window._user) return;
  try {
    const response = await fetch("/api/legal-agent/conversations");
    if (!response.ok) throw new Error("会话加载失败");
    const data = await response.json();
    const rows = Array.isArray(data.conversations) ? data.conversations : [];
    rail.innerHTML = rows.length ? rows.map(item => `<button type="button" class="agent-session-item ${item.id === legalAgentState.conversationId ? "active" : ""}" onclick="openAgentConversation('${escapeHtml(item.id)}')"><b>${escapeHtml(item.title || "新法律咨询")}</b><time>${escapeHtml(item.updated_at || "")}</time></button>`).join("") : '<p class="agent-session-empty">还没有历史会话</p>';
    if (drawer) {
      drawer.innerHTML = rows.length ? rows.map(item => `<div class="agent-history-row"><button type="button" onclick="openAgentConversation('${escapeHtml(item.id)}');toggleAgentHistory(true)"><b>${escapeHtml(item.title || "新法律咨询")}</b><time>${escapeHtml(item.updated_at || "")}</time></button><button type="button" class="agent-history-delete" onclick="deleteAgentConversation('${escapeHtml(item.id)}')">删除</button></div>`).join("") : '<p class="agent-session-empty">还没有历史会话</p>';
    }
  } catch (_) {
    rail.innerHTML = '<p class="agent-session-empty">会话暂时无法加载</p>';
    if (drawer) drawer.innerHTML = '<p class="agent-session-empty">会话暂时无法加载</p>';
  }
}

function toggleAgentHistory(forceClose = false) {
  const overlay = document.getElementById("agent-history-overlay");
  const panel = document.getElementById("agent-history-panel");
  if (!overlay || !panel) return;
  if (forceClose) {
    overlay.classList.add("hidden");
    panel.classList.add("hidden");
    return;
  }
  overlay.classList.toggle("hidden");
  panel.classList.toggle("hidden");
  if (!panel.classList.contains("hidden")) loadAgentConversations();
}

function startNewAgentConversation() {
  legalAgentState.conversationId = null;
  legalAgentState.messages = [];
  legalAgentState.lastResult = null;
  clearAgentAttachment();
  setAgentAction("");
  const list = document.getElementById("agent-message-list");
  if (list) list.innerHTML = legalAgentState.welcomeMarkup || '<article class="agent-message assistant"><div class="agent-message-avatar">明</div><div class="agent-message-body"><div class="agent-message-content"><p>新会话已开始，请描述你的法律问题。</p></div></div></article>';
  document.querySelectorAll(".agent-session-item").forEach(el => el.classList.remove("active"));
  switchModule("home");
  document.getElementById("agent-input")?.focus();
}

async function openAgentConversation(conversationId) {
  try {
    const response = await fetch(`/api/legal-agent/conversations/${encodeURIComponent(conversationId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "会话加载失败");
    legalAgentState.conversationId = data.id;
    legalAgentState.messages = Array.isArray(data.messages) ? data.messages : [];
    legalAgentState.lastResult = [...legalAgentState.messages].reverse().find(item => item.result && Object.keys(item.result).length)?.result || null;
    const list = document.getElementById("agent-message-list");
    list.innerHTML = "";
    legalAgentState.messages.forEach(item => {
      const article = appendAgentMessage(item.role === "user" ? "user" : "assistant", item.content || "", { attachment: item.attachment });
      if (item.role === "assistant" && item.result && Object.keys(item.result).length) finishAgentMessage(article, { ...item.result, answer: item.content || item.result.answer });
    });
    if (!legalAgentState.messages.length) startNewAgentConversation();
    switchModule("home");
    loadAgentConversations();
  } catch (error) {
    alert(error.message || "会话加载失败");
  }
}

async function deleteAgentConversation(conversationId) {
  if (!confirm("确定删除这段智能体会话吗？")) return;
  const response = await fetch(`/api/legal-agent/conversations/${encodeURIComponent(conversationId)}`, { method: "DELETE" });
  if (!response.ok) { alert("删除失败"); return; }
  if (legalAgentState.conversationId === conversationId) startNewAgentConversation();
  loadAgentConversations();
}

function exportAgentConversation() {
  if (!legalAgentState.messages.length) { alert("当前会话还没有可导出的内容"); return; }
  const lines = ["# 明鉴法律智能体会话", "", `导出时间：${new Date().toLocaleString("zh-CN")}`, ""];
  legalAgentState.messages.forEach(item => {
    lines.push(`## ${item.role === "user" ? "用户" : "明鉴"}`, "", item.content || "", "");
  });
  lines.push("> 提示：本记录不替代律师正式法律意见，法条效力状态请到官方数据库核验。");
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `明鉴法律智能体_${new Date().toISOString().slice(0, 10)}.md`;
  link.click();
  URL.revokeObjectURL(url);
}

async function exportAgentDocument() {
  const doc = legalAgentState.lastResult && legalAgentState.lastResult.document;
  if (!doc || !doc.body) return;
  try {
    const response = await fetch("/api/download-docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: doc.title || "法律文书", body: doc.body, header: doc.header || {}, doc_type: doc.document_type || "" }),
    });
    if (!response.ok) throw new Error("文书导出失败");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${doc.title || "法律文书"}.docx`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message || "文书导出失败");
  }
}

// ===== Tab Switching =====
function switchTab(module, tab) {
  const section = document.getElementById(`module-${module}`);
  section.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
  section.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const tabs = section.querySelectorAll(".tab");
  if (tab === "upload" && tabs.length > 1) tabs[1].classList.add("active");
  else if (tabs.length > 0) tabs[0].classList.add("active");

  const pane = document.getElementById(`${module}-${tab}`);
  if (pane) pane.classList.add("active");
}

// ===== File Selection =====
const selectedUploadFiles = new Map();
const uploadPreviewUrls = new Map();

function updateUploadSelection(module, file, source = "file") {
  if (!file) return;
  selectedUploadFiles.set(module, file);

  const badge = document.getElementById(`${module}-file-name`);
  if (badge) {
    badge.textContent = `${source === "camera" ? "已拍摄" : "已选择"}：${file.name || "现场照片"}`;
    badge.classList.remove("hidden");
  }

  const preview = document.getElementById(`${module}-capture-preview`);
  if (!preview) return;
  const previousUrl = uploadPreviewUrls.get(module);
  if (previousUrl) URL.revokeObjectURL(previousUrl);
  uploadPreviewUrls.delete(module);

  if (file.type && file.type.startsWith("image/")) {
    const previewUrl = URL.createObjectURL(file);
    uploadPreviewUrls.set(module, previewUrl);
    const image = preview.querySelector("img");
    const label = preview.querySelector("span");
    if (image) image.src = previewUrl;
    if (label) label.textContent = source === "camera" ? "照片已就绪，可直接开始识别" : "图片已就绪，可直接开始识别";
    preview.classList.remove("hidden");
  } else {
    preview.classList.add("hidden");
  }
}

function onFileSelected(inputId, nameId) {
  const input = document.getElementById(inputId);
  const module = inputId.replace(/-file$/, "");
  if (input && input.files.length > 0) updateUploadSelection(module, input.files[0], "file");
}

function openCameraCapture(module) {
  const cameraInput = document.getElementById(`${module}-camera`);
  if (!cameraInput) return;
  cameraInput.value = "";
  cameraInput.click();
}

function onCameraSelected(module) {
  const cameraInput = document.getElementById(`${module}-camera`);
  if (cameraInput && cameraInput.files.length > 0) {
    updateUploadSelection(module, cameraInput.files[0], "camera");
  }
}

function getSelectedUploadFile(module) {
  const remembered = selectedUploadFiles.get(module);
  if (remembered) return remembered;
  const input = document.getElementById(`${module}-file`);
  return input && input.files.length > 0 ? input.files[0] : null;
}

// ===== Drag & Drop =====
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".drop-zone").forEach(zone => {
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => { zone.classList.remove("drag-over"); });
    zone.addEventListener("drop", e => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const input = zone.querySelector("input[type='file']");
      if (input && e.dataTransfer.files.length > 0) {
        input.files = e.dataTransfer.files;
        const module = input.id.replace(/-file$/, "");
        updateUploadSelection(module, e.dataTransfer.files[0], "file");
      }
    });
    zone.addEventListener("click", () => {
      const input = zone.querySelector("input[type='file']");
      if (input) input.click();
    });
  });
});

// ===== Loading =====
function showLoading() { document.getElementById("loading-overlay").classList.remove("hidden"); }
function hideLoading() { document.getElementById("loading-overlay").classList.add("hidden"); }

// ===== API Helpers =====
async function apiPost(url, body, formData = null) {
  showLoading();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300000);
  try {
    let resp;
    if (formData) {
      resp = await fetch(url, { method: "POST", body: formData, signal: controller.signal });
    } else {
      resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    }
    clearTimeout(timeoutId);
    syncFreeQuotaFromResponse(resp);
    if (resp.status === 401) {
      hideLoading();
      showAuth();
      return { error: "请先登录" };
    }
    if (resp.status === 403) {
      hideLoading();
      const ct = resp.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        updateQuotaHint();
        return { error: "服务暂时不可用，请稍后重试" };
      }
      const data = await resp.json();
      syncFreeQuotaFromData(data);
      return { error: data.error || "权限不足" };
    }
    const ct = resp.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      hideLoading();
      return { error: "服务暂时不可用（服务器返回异常），请稍后重试或检查 API 配置是否正确" };
    }
    const data = await resp.json();
    hideLoading();
    return data;
  } catch (e) {
    hideLoading();
    if (e.name === "AbortError") {
      return { error: "请求超时，模型响应较慢，请稍后重试或检查 API 配置" };
    }
    return { error: `请求失败: ${e.message}` };
  }
}

async function apiPostStream(url, body, formData, onChunk, onDone) {
  showLoading();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300000);
  try {
    let resp;
    if (formData) {
      resp = await fetch(url, { method: "POST", body: formData, signal: controller.signal });
    } else {
      resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    }
    syncFreeQuotaFromResponse(resp);

    if (resp.status === 401) { hideLoading(); showAuth(); onDone({ error: "请先登录" }); return; }
    if (resp.status === 403) {
      hideLoading();
      updateQuotaHint();
      const ct = resp.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const data = await resp.json();
        syncFreeQuotaFromData(data);
        onDone({ error: data.error || "权限不足" });
      } else {
        onDone({ error: "权限不足" });
      }
      return;
    }
    if (resp.status !== 200 && resp.status !== 201) {
      hideLoading();
      const ct = resp.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const data = await resp.json();
        syncFreeQuotaFromData(data);
        onDone({ error: data.error || `服务异常 (${resp.status})` });
      } else {
        onDone({ error: `服务异常 (${resp.status})` });
      }
      return;
    }

    // 读取 SSE 流
    hideLoading();
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE 消息以 \n\n 分隔
      const parts = buffer.split("\n\n");
      buffer = parts.pop();  // 保留不完整的最后一段
      for (const part of parts) {
        const lines = part.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const msg = JSON.parse(line.slice(6));
              if (msg.chunk) {
                onChunk(msg.chunk);
              } else if (msg.done) {
                onDone(msg.result);
                return;
              }
            } catch (e) { /* skip malformed */ }
          }
        }
      }
    }
    // 处理缓冲区残留
    if (buffer.trim()) {
      const lines = buffer.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const msg = JSON.parse(line.slice(6));
            if (msg.done) { onDone(msg.result); return; }
          } catch (e) { /* skip */ }
        }
      }
    }
    onDone({ error: "流式响应异常结束" });
  } catch (e) {
    hideLoading();
    if (e.name === "AbortError") {
      onDone({ error: "请求超时，模型响应较慢，请稍后重试" });
    } else {
      onDone({ error: `请求失败: ${e.message}` });
    }
  } finally {
    clearTimeout(timeoutId);
  }
}

async function apiGet(url) {
  try {
    const resp = await fetch(url);
    if (resp.status === 401) {
      showAuth();
      return { error: "请先登录" };
    }
    const ct = resp.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      return { error: "服务暂时不可用，请稍后重试" };
    }
    return await resp.json();
  } catch (e) {
    return { error: `请求失败: ${e.message}` };
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function syncFreeQuotaFromResponse(resp) {
  if (!window._user || window._user.is_admin) return;
  const remaining = resp.headers.get("X-Free-Api-Remaining");
  const limit = resp.headers.get("X-Free-Api-Limit");
  if (remaining !== null) window._user.free_api_remaining = Number(remaining);
  if (limit !== null) window._user.free_api_limit = Number(limit);
  updateQuotaHint();
}

function syncFreeQuotaFromData(data) {
  if (!window._user || window._user.is_admin || !data) return;
  if (data.free_api_remaining !== undefined) {
    window._user.free_api_remaining = Number(data.free_api_remaining);
  }
  if (data.free_api_limit !== undefined) {
    window._user.free_api_limit = Number(data.free_api_limit);
  }
  updateQuotaHint();
}

// ===== Result Display =====
function showResult(moduleId, html, isDemo = false) {
  const el = document.getElementById(`${moduleId}-result`);
  let finalHtml = "";
  if (isDemo) {
    finalHtml += `<div class="demo-notice">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <span>演示模式 — 显示模拟数据。请配置 API Key 以获取 AI 真实分析结果。</span>
    </div>`;
  }
  finalHtml += html;
  finalHtml += `<div class="legal-disclaimer">提示：本系统输出仅供学习、检索和初步风险识别参考，不构成正式法律意见；具体案件仍应结合完整证据、最新法律法规及专业人士意见判断。</div>`;
  el.innerHTML = finalHtml;
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function showError(moduleId, msg) {
  showResult(moduleId, `<div style="padding:16px;color:var(--danger);background:var(--danger-bg);border-radius:var(--radius-md);border:1px solid rgba(168,54,75,0.25);">${escapeHtml(msg)}</div>`);
}

// ===== Risk Level Helpers =====
function riskClass(level) {
  const l = (level || "").toLowerCase();
  if (l.includes("高") || l.includes("high")) return "high";
  if (l.includes("低") || l.includes("low")) return "low";
  return "medium";
}
function badgeClass(level) { return "badge-" + riskClass(level); }
// ============================================================================
//  Module 1: Legal Document Analysis
// ============================================================================
function renderAnalyzeResult(result) {
  let html = "";
  html += `<div class="stat-grid">
    <div class="stat-cell"><div class="stat-value">${escapeHtml(result.document_type || "-")}</div><div class="stat-label">文书类型</div></div>
    <div class="stat-cell"><div class="stat-value">${(result.key_clauses || []).length}</div><div class="stat-label">核心条款</div></div>
    <div class="stat-cell"><div class="stat-value">${(result.risk_points || []).length}</div><div class="stat-label">风险点</div></div>
  </div>`;

  if (result.parties && result.parties.length) {
    html += `<div class="result-section-title">涉及各方</div><p>${result.parties.map(escapeHtml).join(" &nbsp;·&nbsp; ")}</p>`;
  }

  if (result.key_clauses && result.key_clauses.length) {
    html += `<div class="result-section-title">核心条款分析</div><div class="risk-list">`;
    for (const c of result.key_clauses) {
      const lv = riskClass(c.risk_level);
      html += `<div class="risk-card ${lv}">
        <div class="risk-card-header"><span class="risk-card-title">${escapeHtml(c.clause || "")}</span><span class="badge badge-${lv}">${escapeHtml(c.risk_level || "中")}</span></div>
        <p>${escapeHtml(c.summary || "")}</p>
        ${c.note ? `<p style="font-size:12px;color:var(--text-muted);margin-top:4px;">${escapeHtml(c.note)}</p>` : ""}
      </div>`;
    }
    html += `</div>`;
  }

  if (result.risk_points && result.risk_points.length) {
    html += `<div class="result-section-title">风险提示</div><div class="risk-list">`;
    for (const r of result.risk_points) {
      const lv = riskClass(r.level);
      html += `<div class="risk-card ${lv}">
        <div class="risk-card-header"><span class="risk-card-title">${escapeHtml(r.point || "")}</span><span class="badge badge-${lv}">${escapeHtml(r.level || "中")}</span></div>
        ${r.suggestion ? `<p style="color:var(--success);">建议：${escapeHtml(r.suggestion)}</p>` : ""}
      </div>`;
    }
    html += `</div>`;
  }

  if (result.legal_basis && result.legal_basis.length) {
    html += `<div class="result-section-title">法律依据</div><ul>${result.legal_basis.map(b => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`;
  }
  if (result.revision_suggestions && result.revision_suggestions.length) {
    html += `<div class="result-section-title">修改建议</div><ul>${result.revision_suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ul>`;
  }
  if (result.overall_assessment) {
    html += `<div class="result-section-title">综合评估</div><p>${escapeHtml(result.overall_assessment)}</p>`;
  }
  return html;
}

async function submitAnalyze() {
  const section = document.getElementById("module-analyze");
  const activeTab = section.querySelector(".tab.active");
  const isUpload = activeTab && activeTab.textContent.includes("上传");

  let url, body, fd;
  if (isUpload) {
    const selectedFile = getSelectedUploadFile("analyze");
    if (!selectedFile) return showError("analyze", "请选择文件或拍照");
    fd = new FormData();
    fd.append("file", selectedFile);
    url = "/api/analyze-stream";
  } else {
    const text = document.getElementById("analyze-text").value.trim();
    if (text.length < 20) return showError("analyze", "请至少输入20字的文书内容");
    body = { text };
    url = "/api/analyze-stream";
  }

  // 流式容器
  const el = document.getElementById("analyze-result");
  el.innerHTML = renderModuleProgress("analyze");
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });

  let progressText = "";
  await apiPostStream(url, body, fd,
    (chunk) => {
      progressText += chunk;
      updateModuleProgress("analyze", progressText);
    },
    (result) => {
      if (result.error) { showError("analyze", result.error); return; }
      const html = renderAnalyzeResult(result);
      showResult("analyze", html, !!result.demo_mode);
    }
  );
}

// ============================================================================
//  Module 2: Legal Provision Search
// ============================================================================
function renderSearchResult(result) {
  let html = "";

  if (result.legal_analysis) {
    html += `<div class="result-section-title">法律分析</div><p>${escapeHtml(result.legal_analysis)}</p>`;
  }

  const provisions = result.provisions || [];
  if (provisions.length) {
    html += `<div class="result-section-title">法规线索 <span class="section-note">请以官方最新文本为准</span></div>`;
    for (const p of provisions) {
      html += `<div class="provision-card model-source">
        <div class="provision-source-row"><span class="source-badge model">法规线索</span><span class="validity-pending">请核验</span></div>
        <div class="law-title">《${escapeHtml(p.law_name || "")}》${escapeHtml(p.article || "")}</div>
        <div class="law-text">${escapeHtml(p.content || "")}</div>
        ${p.effective_date ? `<div class="provision-meta"><span>参考日期：${escapeHtml(p.effective_date)}</span></div>` : ""}
        ${p.applicability ? `<p class="provision-applicability">适用场景：${escapeHtml(p.applicability)}</p>` : ""}
      </div>`;
    }
  }

  if (result.practical_advice) {
    html += `<div class="result-section-title">实务建议</div><p>${escapeHtml(result.practical_advice)}</p>`;
  }
  return html;
}

async function copyLegalCitation(index, button) {
  const citation = (window._legalCitations || [])[index];
  if (!citation) return;
  let copied = false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(citation);
      copied = true;
    }
  } catch (e) {}
  if (!copied) {
    const textarea = document.createElement("textarea");
    textarea.value = citation;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    copied = document.execCommand("copy");
    textarea.remove();
  }
  if (button && copied) {
    const original = button.textContent;
    button.textContent = "已复制";
    setTimeout(() => { button.textContent = original; }, 1400);
  }
}

async function submitSearch() {
  const question = document.getElementById("search-question").value.trim();
  if (!question) return showError("search", "请输入法律问题");

  const el = document.getElementById("search-result");
  el.innerHTML = renderModuleProgress("search");
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });

  let progressText = "";
  await apiPostStream("/api/search-provision-stream", { question }, null,
    (chunk) => {
      progressText += chunk;
      updateModuleProgress("search", progressText);
    },
    (result) => {
      if (result.error) { showError("search", result.error); return; }
      const html = renderSearchResult(result);
      showResult("search", html, !!result.demo_mode);
    }
  );
}

// ============================================================================
//  Module 3: Contract Review
// ============================================================================
function renderReviewResult(result) {
  let html = "";
  const score = Number.isFinite(Number(result.overall_risk_score)) ? Number(result.overall_risk_score) : 0;
  const level = riskClass(result.overall_risk_level);

  html += `<div class="score-hero">
    <div class="score-ring ${level}">${score}</div>
    <div class="score-meta">
      <h4>${escapeHtml(result.overall_risk_level || "中")}风险 · ${escapeHtml(result.contract_type || "")}</h4>
      <p style="color:var(--text-muted);font-size:13px;">综合风险评分</p>
    </div>
  </div>`;

  const items = result.risk_items || [];
  if (items.length) {
    html += `<div class="result-section-title">风险项 (${items.length})</div><div class="risk-list">`;
    for (const item of items) {
      const lv = riskClass(item.risk_level);
      html += `<div class="risk-card ${lv}">
        <div class="risk-card-header">
          <span class="risk-card-title">${escapeHtml(item.risk_type || "")}</span>
          <span class="badge badge-${lv}">${escapeHtml(item.risk_level || "中")} · ${escapeHtml(Number.isFinite(Number(item.risk_score)) ? String(Number(item.risk_score)) : "-")}分</span>
        </div>
        <div class="clause-original">原文：${escapeHtml((item.clause_text || "").substring(0, 150))}</div>
        <p>${escapeHtml(item.explanation || "")}</p>
        ${item.revised_text ? `<div class="revision">修改建议：${escapeHtml(item.revised_text.substring(0, 250))}</div>` : ""}
        ${item.legal_basis ? `<div class="legal-ref">法律依据：${escapeHtml(item.legal_basis)}</div>` : ""}
      </div>`;
    }
    html += `</div>`;
  }

  if (result.missing_clauses && result.missing_clauses.length) {
    html += `<div class="result-section-title">应补充条款</div><ul>${result.missing_clauses.map(c => `<li>${escapeHtml(c)}</li>`).join("")}</ul>`;
  }
  if (result.summary) {
    html += `<div class="result-section-title">审查小结</div><p>${escapeHtml(result.summary)}</p>`;
  }
  return html;
}

async function submitReview() {
  const section = document.getElementById("module-review");
  const activeTab = section.querySelector(".tab.active");
  const isUpload = activeTab && activeTab.textContent.includes("上传");

  let url, body, fd;
  if (isUpload) {
    const selectedFile = getSelectedUploadFile("review");
    if (!selectedFile) return showError("review", "请选择合同文件或拍照");
    fd = new FormData();
    fd.append("file", selectedFile);
    url = "/api/review-contract-stream";
  } else {
    const text = document.getElementById("review-text").value.trim();
    if (text.length < 50) return showError("review", "请至少输入50字的合同内容");
    body = { contract: text };
    url = "/api/review-contract-stream";
  }

  const el = document.getElementById("review-result");
  el.innerHTML = renderModuleProgress("review");
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });

  let progressText = "";
  await apiPostStream(url, body, fd,
    (chunk) => {
      progressText += chunk;
      updateModuleProgress("review", progressText);
    },
    (result) => {
      if (result.error) { showError("review", result.error); return; }
      const html = renderReviewResult(result);
      showResult("review", html, !!result.demo_mode);
    }
  );
}

// ============================================================================
//  Module 4: Document Generation
// ============================================================================
const MODULE_PROGRESS = {
  analyze: {
    title: "正在分析法律文书",
    steps: ["识别文书类型", "提取关键内容", "整理风险建议"],
    messages: ["正在识别文书类型和当事人信息...", "正在提取关键条款和法律风险...", "正在整理分析结论和修改建议..."],
  },
  search: {
    title: "正在检索法律依据",
    steps: ["理解问题", "检索相关法条", "整理实务建议"],
    messages: ["正在理解你的法律问题...", "正在检索相关法条和法律依据...", "正在整理法规解读和实务建议..."],
  },
  review: {
    title: "正在审查合同风险",
    steps: ["读取合同", "识别风险条款", "生成审查意见"],
    messages: ["正在读取合同内容和交易结构...", "正在识别高风险条款和缺失条款...", "正在生成风险等级和修改建议..."],
  },
  generate: {
    title: "正在生成法律文书",
    steps: ["整理事实", "生成正文", "校对格式"],
    messages: ["正在梳理当事人、事实经过和核心诉求...", "正在生成文书正文和诉求表述...", "正在校对格式、证据材料和注意事项..."],
  },
  strategy: {
    title: "正在分析案件策略",
    steps: ["梳理事实", "判断法律关系", "生成行动建议"],
    messages: ["正在梳理案件事实和争议焦点...", "正在判断法律关系、证据风险和时效问题...", "正在生成诉讼策略和下一步建议..."],
  },
  student: {
    title: "正在分析学生法律问题",
    steps: ["识别场景", "检索相关法条", "生成维权路径"],
    messages: ["正在识别校园或校外争议场景...", "正在检索相关法条和证据要点...", "正在生成沟通文本和维权路径..."],
  },
};

function renderModuleProgress(moduleId) {
  const cfg = MODULE_PROGRESS[moduleId] || MODULE_PROGRESS.analyze;
  return `<div class="stream-box progress-box" data-progress-module="${escapeHtml(moduleId)}">
    <div class="stream-spinner"></div>
    <div class="progress-content">
      <strong id="${moduleId}-progress-title">${escapeHtml(cfg.title)}</strong>
      <span id="${moduleId}-progress-text">${escapeHtml(cfg.messages[0])}</span>
      <div class="progress-steps" id="${moduleId}-progress-steps">
        ${cfg.steps.map((step, idx) => `<span class="${idx === 0 ? "active" : ""}">${escapeHtml(step)}</span>`).join("")}
      </div>
    </div>
  </div>`;
}

function updateModuleProgress(moduleId, chunkText) {
  const cfg = MODULE_PROGRESS[moduleId] || MODULE_PROGRESS.analyze;
  const text = document.getElementById(`${moduleId}-progress-text`);
  const steps = document.querySelectorAll(`#${moduleId}-progress-steps span`);
  if (!text || !steps.length) return;
  const len = (chunkText || "").length;
  let stepIndex = 0;
  if (len > 160) stepIndex = 1;
  if (len > 520) stepIndex = 2;
  text.textContent = cfg.messages[Math.min(stepIndex, cfg.messages.length - 1)];
  steps.forEach((el, idx) => el.classList.toggle("active", idx <= stepIndex));
}

function docHeaderLabel(key) {
  const labels = {
    court: "管辖法院",
    parties: "当事人",
    plaintiff: "原告",
    plaintiff_address: "住所",
    legal_representative: "法定代表人/主要负责人",
    representative_duty: "职务",
    representative_contact: "联系方式",
    agent: "委托诉讼代理人",
    defendant: "被告",
    defendant_info: "被告基本信息",
    claims: "诉讼请求",
    facts_and_reasons: "事实和理由",
    evidence: "证据和证据来源，证人姓名和住所",
    copy_count: "副本份数",
    suer: "起诉人",
    date: "日期",
    appellant: "上诉人(原审诉讼地位)",
    appellant_info: "上诉人基本信息",
    appellant_contact: "联系方式",
    legal_agent: "法定代理人/指定代理人",
    appellee: "被上诉人(原审诉讼地位)",
    appellee_info: "被上诉人基本信息",
    case_parties: "案由当事人",
    cause: "案由",
    original_court: "原审人民法院",
    judgment_date: "原审裁判日期",
    case_number: "原审裁判文号",
    judgment_type: "裁判类型",
    appeal_requests: "上诉请求",
    appeal_reasons: "上诉理由",
    respondent: "答辩人",
    respondent_info: "答辩人基本信息",
    respondent_contact: "联系方式",
    original_court: "受理人民法院",
    case_number: "案号",
    case_summary: "当事人和案由",
    defense_opinion: "答辩意见",
    applicant: "申请执行人",
    applicant_info: "申请执行人基本信息",
    applicant_contact: "联系方式",
    instrument_maker: "生效法律文书作出机关",
    instrument_number: "生效法律文书文号",
    instrument_type: "生效法律文书类型",
    obligor: "未履行义务人",
    execution_requests: "请求事项",
    attachment_count: "生效法律文书份数",
    counter_plaintiff: "反诉原告(本诉被告)",
    counter_plaintiff_info: "反诉原告基本信息",
    counter_plaintiff_contact: "联系方式",
    counter_defendant: "反诉被告(本诉原告)",
    counter_defendant_info: "反诉被告基本信息",
    counterclaim_requests: "反诉请求",
    objector: "异议人(被告)",
    objector_info: "异议人基本信息",
    objector_contact: "联系方式",
    transfer_court: "移送人民法院",
    applicant_person: "自然人申请人",
    applicant_person_info: "自然人申请人基本信息",
    person_agent_1: "自然人代理人一",
    person_agent_2: "自然人代理人二",
    applicant_org: "单位申请人",
    applicant_org_info: "单位申请人基本信息",
    org_agent_1: "单位代理人一",
    org_agent_2: "单位代理人二",
    principal: "委托人",
    principal_info: "委托人基本信息",
    lawyer_agent: "律师受委托人",
    citizen_agent: "公民受委托人",
    agent_names: "委托代理人姓名",
    agent_1_name: "代理人一姓名",
    agent_1_authority: "代理人一事项和权限",
    agent_2_name: "代理人二姓名",
    agent_2_authority: "代理人二事项和权限",
    contract_type: "合同类型",
    party_a: "甲方",
    party_b: "乙方",
    subject: "标的/商品信息",
    price: "价款",
    payment: "付款方式",
    delivery: "交付与验收",
    breach: "违约责任",
    dispute: "争议解决",
    house: "房屋位置及状况",
    term: "期限",
    rent: "租金及押金",
    fees: "费用承担",
    amount: "借款金额",
    purpose: "借款用途",
    repayment: "利息及还款",
    guarantee: "担保/保证",
    content: "服务内容",
    fee: "服务费用",
    acceptance: "验收标准",
    position: "工作岗位和地点",
    hours: "工作时间和休息休假",
    salary: "劳动报酬",
    benefits: "社会保险和福利",
  };
  return labels[String(key).toLowerCase()] || key;
}

function formatDocHeaderValue(value) {
  if (!value || typeof value !== "object") return escapeHtml(String(value || ""));
  return Object.entries(value)
    .map(([key, val]) => `${escapeHtml(docHeaderLabel(key))}：${escapeHtml(String(val || ""))}`)
    .join("<br>");
}

function renderGenerateResult(result) {
  let html = "";
  if (result.title) {
    html += `<h3 style="text-align:center;font-family:var(--font-display);font-size:22px;color:var(--accent-light);margin-bottom:20px;">${escapeHtml(result.title)}</h3>`;
  }
  if (result.header) {
    html += `<div class="result-section-title">文书信息</div>`;
    html += `<div style="background:var(--bg-surface);padding:16px;border-radius:var(--radius-md);margin-bottom:16px;">`;
    for (const [k, v] of Object.entries(result.header)) {
      html += `<p style="margin-bottom:4px;"><strong style="color:var(--text-muted);">${escapeHtml(docHeaderLabel(k))}</strong> &nbsp;${formatDocHeaderValue(v)}</p>`;
    }
    html += `</div>`;
  }
  if (result.body) {
    html += `<div class="result-section-title">文书正文</div>`;
    html += `<div class="doc-preview">${escapeHtml(result.body)}</div>`;
  }
  if (result.attachments && result.attachments.length) {
    html += `<div class="result-section-title">需附证据材料</div><ul>${result.attachments.map(a => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`;
  }
  if (result.notes && result.notes.length) {
    html += `<div class="result-section-title">注意事项</div><ul>${result.notes.map(n => `<li>${escapeHtml(n)}</li>`).join("")}</ul>`;
  }
  if (result.body) {
    html += `<button class="btn-primary" style="width:auto;margin-top:20px;" onclick="downloadDoc()">下载文书</button>`;
  }
  return html;
}

async function submitGenerate() {
  const docType = document.getElementById("gen-doc-type").value;
  const complaintFields = docType === "起诉状" ? getComplaintFields() : {};
  const appealFields = docType === "上诉状" ? getAppealFields() : {};
  const defenseFields = docType === "答辩状" ? getDefenseFields() : {};
  const executionFields = docType === "申请执行书" ? getExecutionFields() : {};
  const counterclaimFields = docType === "反诉状" ? getCounterclaimFields() : {};
  const jurisdictionObjectionFields = docType === "管辖权异议书" ? getJurisdictionObjectionFields() : {};
  const judicialConfirmationFields = docType === "司法确认申请书" ? getJudicialConfirmationFields() : {};
  const citizenAuthorizationFields = docType === "公民授权委托书" ? getCitizenAuthorizationFields() : {};
  const contractFields = docType === "合同" ? getContractFields() : {};
  const templateFields = docType === "上诉状"
    ? appealFields
    : docType === "答辩状"
      ? defenseFields
      : docType === "申请执行书"
        ? executionFields
        : docType === "反诉状"
          ? counterclaimFields
          : docType === "管辖权异议书"
            ? jurisdictionObjectionFields
            : docType === "司法确认申请书"
              ? judicialConfirmationFields
              : docType === "公民授权委托书"
                ? citizenAuthorizationFields
                : docType === "合同"
                  ? contractFields
          : complaintFields;
  const description = Object.entries(templateFields)
    .filter(([, value]) => value)
    .map(([key, value]) => `${documentFieldLabel(docType, key)}：${value}`)
    .join("\n");
  const requirements = docType === "上诉状"
      ? "严格按照民事上诉状模板生成"
      : docType === "答辩状"
        ? "严格按照民事答辩状模板生成"
        : docType === "申请执行书"
          ? "严格按照申请执行书模板生成"
          : docType === "反诉状"
            ? "严格按照民事反诉状模板生成"
            : docType === "管辖权异议书"
              ? "严格按照管辖权异议书模板生成"
              : docType === "司法确认申请书"
                ? "严格按照司法确认申请书模板生成"
                : docType === "公民授权委托书"
                  ? "严格按照公民授权委托书模板生成"
                  : docType === "合同"
                    ? `严格按照${selectedContractType}模板生成`
      : "严格按照民事起诉状模板生成";

  if (!description) {
    return showError("generate", docType === "上诉状"
      ? "请至少填写上诉人、被上诉人、上诉请求、上诉理由等信息"
      : docType === "答辩状"
        ? "请至少填写答辩人、案号、答辩意见等信息"
        : docType === "申请执行书"
          ? "请至少填写申请执行人、被执行人、生效法律文书和请求事项等信息"
          : docType === "反诉状"
            ? "请至少填写反诉原告、反诉被告、反诉请求、事实和理由等信息"
            : docType === "管辖权异议书"
              ? "请至少填写异议人、案号、移送法院、事实和理由等信息"
              : docType === "司法确认申请书"
                ? "请至少填写申请人、诉讼请求、事实和理由、法院等信息"
                : docType === "公民授权委托书"
                  ? "请至少填写委托人、受委托人、委托事项和权限等信息"
                  : docType === "合同"
                    ? "请至少填写甲方、乙方、合同主要内容和日期等信息"
        : "请至少填写原告、被告、诉讼请求、事实和理由等信息");
  }

  const el = document.getElementById("generate-result");
  el.innerHTML = renderModuleProgress("generate");
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });

  let progressText = "";
  await apiPostStream("/api/generate-document-stream", { doc_type: docType, description, requirements, complaint_fields: complaintFields, appeal_fields: appealFields, defense_fields: defenseFields, execution_fields: executionFields, counterclaim_fields: counterclaimFields, jurisdiction_objection_fields: jurisdictionObjectionFields, judicial_confirmation_fields: judicialConfirmationFields, citizen_authorization_fields: citizenAuthorizationFields, contract_fields: contractFields, contract_type: selectedContractType }, null,
    (chunk) => {
      progressText += chunk;
      updateModuleProgress("generate", progressText);
    },
    (result) => {
      if (result.error) { showError("generate", result.error); return; }
      const html = renderGenerateResult(result);
      showResult("generate", html, !!result.demo_mode);
      window._generatedDoc = { title: result.title, body: result.body, header: result.header, docType, complaintFields, appealFields, defenseFields, executionFields, counterclaimFields, jurisdictionObjectionFields, judicialConfirmationFields, citizenAuthorizationFields, contractFields, contractType: selectedContractType };
    }
  );
}

function getComplaintFields() {
  return {
    plaintiff: document.getElementById("gen-plaintiff").value.trim(),
    plaintiff_address: document.getElementById("gen-plaintiff-address").value.trim(),
    legal_representative: document.getElementById("gen-legal-representative").value.trim(),
    representative_duty: document.getElementById("gen-representative-duty").value.trim(),
    representative_contact: document.getElementById("gen-representative-contact").value.trim(),
    agent: document.getElementById("gen-agent").value.trim(),
    defendant: document.getElementById("gen-defendant").value.trim(),
    defendant_info: document.getElementById("gen-defendant-info").value.trim(),
    claims: document.getElementById("gen-claims").value.trim(),
    facts_and_reasons: document.getElementById("gen-facts-reasons").value.trim(),
    evidence: document.getElementById("gen-evidence").value.trim(),
    court: document.getElementById("gen-court").value.trim(),
    copy_count: document.getElementById("gen-copy-count").value.trim(),
    suer: document.getElementById("gen-suer").value.trim(),
    date: document.getElementById("gen-date").value.trim(),
  };
}

function complaintFieldLabel(key) {
  return {
    plaintiff: "原告",
    plaintiff_address: "住所",
    legal_representative: "法定代表人/主要负责人",
    representative_duty: "职务",
    representative_contact: "联系方式",
    agent: "委托诉讼代理人",
    defendant: "被告",
    defendant_info: "被告基本信息",
    claims: "诉讼请求",
    facts_and_reasons: "事实和理由",
    evidence: "证据和证据来源，证人姓名和住所",
    court: "受诉人民法院",
    copy_count: "副本份数",
    suer: "起诉人",
    date: "日期",
  }[key] || key;
}

function getAppealFields() {
  return {
    appellant: document.getElementById("appeal-appellant").value.trim(),
    appellant_info: document.getElementById("appeal-appellant-info").value.trim(),
    appellant_contact: document.getElementById("appeal-appellant-contact").value.trim(),
    legal_agent: document.getElementById("appeal-legal-agent").value.trim(),
    agent: document.getElementById("appeal-agent").value.trim(),
    appellee: document.getElementById("appeal-appellee").value.trim(),
    appellee_info: document.getElementById("appeal-appellee-info").value.trim(),
    case_parties: document.getElementById("appeal-case-parties").value.trim(),
    cause: document.getElementById("appeal-cause").value.trim(),
    original_court: document.getElementById("appeal-original-court").value.trim(),
    judgment_date: document.getElementById("appeal-judgment-date").value.trim(),
    case_number: document.getElementById("appeal-case-number").value.trim(),
    judgment_type: document.getElementById("appeal-judgment-type").value.trim(),
    appeal_requests: document.getElementById("appeal-requests").value.trim(),
    appeal_reasons: document.getElementById("appeal-reasons").value.trim(),
    court: document.getElementById("appeal-court").value.trim(),
    copy_count: document.getElementById("appeal-copy-count").value.trim(),
    date: document.getElementById("appeal-date").value.trim(),
  };
}

function appealFieldLabel(key) {
  return {
    appellant: "上诉人(原审诉讼地位)",
    appellant_info: "上诉人基本信息",
    appellant_contact: "联系方式",
    legal_agent: "法定代理人/指定代理人",
    agent: "委托诉讼代理人",
    appellee: "被上诉人(原审诉讼地位)",
    appellee_info: "被上诉人基本信息",
    case_parties: "案由当事人",
    cause: "案由",
    original_court: "原审人民法院",
    judgment_date: "原审裁判日期",
    case_number: "原审裁判文号",
    judgment_type: "裁判类型",
    appeal_requests: "上诉请求",
    appeal_reasons: "上诉理由",
    court: "受诉人民法院",
    copy_count: "副本份数",
    date: "日期",
  }[key] || key;
}

function documentFieldLabel(docType, key) {
  if (docType === "上诉状") return appealFieldLabel(key);
  if (docType === "答辩状") return defenseFieldLabel(key);
  if (docType === "申请执行书") return executionFieldLabel(key);
  if (docType === "反诉状") return counterclaimFieldLabel(key);
  if (docType === "管辖权异议书") return jurisdictionObjectionFieldLabel(key);
  if (docType === "司法确认申请书") return judicialConfirmationFieldLabel(key);
  if (docType === "公民授权委托书") return citizenAuthorizationFieldLabel(key);
  if (docType === "合同") return contractFieldLabel(key);
  return complaintFieldLabel(key);
}

function getDefenseFields() {
  return {
    respondent: document.getElementById("defense-respondent").value.trim(),
    respondent_info: document.getElementById("defense-respondent-info").value.trim(),
    respondent_contact: document.getElementById("defense-respondent-contact").value.trim(),
    legal_agent: document.getElementById("defense-legal-agent").value.trim(),
    agent: document.getElementById("defense-agent").value.trim(),
    original_court: document.getElementById("defense-original-court").value.trim(),
    case_number: document.getElementById("defense-case-number").value.trim(),
    case_summary: document.getElementById("defense-case-summary").value.trim(),
    defense_opinion: document.getElementById("defense-opinion").value.trim(),
    evidence: document.getElementById("defense-evidence").value.trim(),
    court: document.getElementById("defense-court").value.trim(),
    copy_count: document.getElementById("defense-copy-count").value.trim(),
    date: document.getElementById("defense-date").value.trim(),
  };
}

function defenseFieldLabel(key) {
  return {
    respondent: "答辩人",
    respondent_info: "答辩人基本信息",
    respondent_contact: "联系方式",
    legal_agent: "法定代理人/指定代理人",
    agent: "委托诉讼代理人",
    original_court: "受理人民法院",
    case_number: "案号",
    case_summary: "当事人和案由",
    defense_opinion: "答辩意见",
    evidence: "证据和证据来源，证人姓名和住所",
    court: "受诉人民法院",
    copy_count: "副本份数",
    date: "日期",
  }[key] || key;
}

function getExecutionFields() {
  return {
    applicant: document.getElementById("execution-applicant").value.trim(),
    applicant_info: document.getElementById("execution-applicant-info").value.trim(),
    applicant_contact: document.getElementById("execution-applicant-contact").value.trim(),
    legal_agent: document.getElementById("execution-legal-agent").value.trim(),
    agent: document.getElementById("execution-agent").value.trim(),
    respondent: document.getElementById("execution-respondent").value.trim(),
    respondent_info: document.getElementById("execution-respondent-info").value.trim(),
    case_parties: document.getElementById("execution-case-parties").value.trim(),
    cause: document.getElementById("execution-cause").value.trim(),
    instrument_maker: document.getElementById("execution-instrument-maker").value.trim(),
    instrument_number: document.getElementById("execution-instrument-number").value.trim(),
    instrument_type: document.getElementById("execution-instrument-type").value.trim(),
    obligor: document.getElementById("execution-obligor").value.trim(),
    execution_requests: document.getElementById("execution-requests").value.trim(),
    court: document.getElementById("execution-court").value.trim(),
    attachment_count: document.getElementById("execution-attachment-count").value.trim(),
    date: document.getElementById("execution-date").value.trim(),
  };
}

function executionFieldLabel(key) {
  return {
    applicant: "申请执行人",
    applicant_info: "申请执行人基本信息",
    applicant_contact: "联系方式",
    legal_agent: "法定代理人/指定代理人",
    agent: "委托诉讼代理人",
    respondent: "被执行人",
    respondent_info: "被执行人基本信息",
    case_parties: "执行案件当事人",
    cause: "案由",
    instrument_maker: "生效法律文书作出机关",
    instrument_number: "生效法律文书文号",
    instrument_type: "生效法律文书类型",
    obligor: "未履行义务人",
    execution_requests: "请求事项",
    court: "受诉人民法院",
    attachment_count: "生效法律文书份数",
    date: "日期",
  }[key] || key;
}

function getCounterclaimFields() {
  return {
    counter_plaintiff: document.getElementById("counterclaim-plaintiff").value.trim(),
    counter_plaintiff_info: document.getElementById("counterclaim-plaintiff-info").value.trim(),
    counter_plaintiff_contact: document.getElementById("counterclaim-plaintiff-contact").value.trim(),
    legal_agent: document.getElementById("counterclaim-legal-agent").value.trim(),
    agent: document.getElementById("counterclaim-agent").value.trim(),
    counter_defendant: document.getElementById("counterclaim-defendant").value.trim(),
    counter_defendant_info: document.getElementById("counterclaim-defendant-info").value.trim(),
    counterclaim_requests: document.getElementById("counterclaim-requests").value.trim(),
    facts_and_reasons: document.getElementById("counterclaim-facts-reasons").value.trim(),
    evidence: document.getElementById("counterclaim-evidence").value.trim(),
    court: document.getElementById("counterclaim-court").value.trim(),
    copy_count: document.getElementById("counterclaim-copy-count").value.trim(),
    date: document.getElementById("counterclaim-date").value.trim(),
  };
}

function counterclaimFieldLabel(key) {
  return {
    counter_plaintiff: "反诉原告(本诉被告)",
    counter_plaintiff_info: "反诉原告基本信息",
    counter_plaintiff_contact: "联系方式",
    legal_agent: "法定代理人/指定代理人",
    agent: "委托诉讼代理人",
    counter_defendant: "反诉被告(本诉原告)",
    counter_defendant_info: "反诉被告基本信息",
    counterclaim_requests: "反诉请求",
    facts_and_reasons: "事实和理由",
    evidence: "证据和证据来源，证人姓名和住所",
    court: "受诉人民法院",
    copy_count: "副本份数",
    date: "日期",
  }[key] || key;
}

function getJurisdictionObjectionFields() {
  return {
    objector: document.getElementById("jurisdiction-objector").value.trim(),
    objector_info: document.getElementById("jurisdiction-objector-info").value.trim(),
    objector_contact: document.getElementById("jurisdiction-objector-contact").value.trim(),
    legal_agent: document.getElementById("jurisdiction-legal-agent").value.trim(),
    agent: document.getElementById("jurisdiction-agent").value.trim(),
    original_court: document.getElementById("jurisdiction-original-court").value.trim(),
    case_number: document.getElementById("jurisdiction-case-number").value.trim(),
    case_summary: document.getElementById("jurisdiction-case-summary").value.trim(),
    transfer_court: document.getElementById("jurisdiction-transfer-court").value.trim(),
    facts_and_reasons: document.getElementById("jurisdiction-facts-reasons").value.trim(),
    court: document.getElementById("jurisdiction-court").value.trim(),
    date: document.getElementById("jurisdiction-date").value.trim(),
  };
}

function jurisdictionObjectionFieldLabel(key) {
  return {
    objector: "异议人(被告)",
    objector_info: "异议人基本信息",
    objector_contact: "联系方式",
    legal_agent: "法定代理人/指定代理人",
    agent: "委托诉讼代理人",
    original_court: "原受理人民法院",
    case_number: "案号",
    case_summary: "案件当事人和案由",
    transfer_court: "移送人民法院",
    facts_and_reasons: "事实和理由",
    court: "受诉人民法院",
    date: "日期",
  }[key] || key;
}

function getJudicialConfirmationFields() {
  return {
    applicant_person: document.getElementById("confirm-applicant-person").value.trim(),
    applicant_person_info: document.getElementById("confirm-applicant-person-info").value.trim(),
    person_agent_1: document.getElementById("confirm-person-agent-1").value.trim(),
    person_agent_2: document.getElementById("confirm-person-agent-2").value.trim(),
    applicant_org: document.getElementById("confirm-applicant-org").value.trim(),
    applicant_org_info: document.getElementById("confirm-applicant-org-info").value.trim(),
    legal_representative: document.getElementById("confirm-legal-representative").value.trim(),
    org_agent_1: document.getElementById("confirm-org-agent-1").value.trim(),
    org_agent_2: document.getElementById("confirm-org-agent-2").value.trim(),
    claims: document.getElementById("confirm-claims").value.trim(),
    facts_and_reasons: document.getElementById("confirm-facts-reasons").value.trim(),
    court: document.getElementById("confirm-court").value.trim(),
    date: document.getElementById("confirm-date").value.trim(),
  };
}

function judicialConfirmationFieldLabel(key) {
  return {
    applicant_person: "自然人申请人",
    applicant_person_info: "自然人申请人基本信息",
    person_agent_1: "自然人代理人一",
    person_agent_2: "自然人代理人二",
    applicant_org: "单位申请人",
    applicant_org_info: "单位申请人基本信息",
    legal_representative: "法定代表人/主要负责人",
    org_agent_1: "单位代理人一",
    org_agent_2: "单位代理人二",
    claims: "诉讼请求",
    facts_and_reasons: "事实和理由",
    court: "受诉人民法院",
    date: "日期",
  }[key] || key;
}

function getCitizenAuthorizationFields() {
  return {
    principal: document.getElementById("auth-principal").value.trim(),
    principal_info: document.getElementById("auth-principal-info").value.trim(),
    lawyer_agent: document.getElementById("auth-lawyer-agent").value.trim(),
    citizen_agent: document.getElementById("auth-citizen-agent").value.trim(),
    case_summary: document.getElementById("auth-case-summary").value.trim(),
    agent_names: document.getElementById("auth-agent-names").value.trim(),
    agent_1_name: document.getElementById("auth-agent-1-name").value.trim(),
    agent_1_authority: document.getElementById("auth-agent-1-authority").value.trim(),
    agent_2_name: document.getElementById("auth-agent-2-name").value.trim(),
    agent_2_authority: document.getElementById("auth-agent-2-authority").value.trim(),
    date: document.getElementById("auth-date").value.trim(),
  };
}

function citizenAuthorizationFieldLabel(key) {
  return {
    principal: "委托人",
    principal_info: "委托人基本信息",
    lawyer_agent: "律师受委托人",
    citizen_agent: "公民受委托人",
    case_summary: "当事人和案由",
    agent_names: "委托代理人姓名",
    agent_1_name: "代理人一姓名",
    agent_1_authority: "代理人一事项和权限",
    agent_2_name: "代理人二姓名",
    agent_2_authority: "代理人二事项和权限",
    date: "日期",
  }[key] || key;
}

function getContractFields() {
  const t = selectedContractType;
  if (t === "买卖合同") {
    return {
      contract_type: t,
      party_a: document.getElementById("sales-party-a").value.trim(),
      party_b: document.getElementById("sales-party-b").value.trim(),
      subject: document.getElementById("sales-subject").value.trim(),
      price: document.getElementById("sales-price").value.trim(),
      payment: document.getElementById("sales-payment").value.trim(),
      delivery: document.getElementById("sales-delivery").value.trim(),
      breach: document.getElementById("sales-breach").value.trim(),
      dispute: document.getElementById("sales-dispute").value.trim(),
      date: document.getElementById("sales-date").value.trim(),
    };
  }
  if (t === "房屋租赁合同") {
    return {
      contract_type: t,
      party_a: document.getElementById("lease-party-a").value.trim(),
      party_b: document.getElementById("lease-party-b").value.trim(),
      house: document.getElementById("lease-house").value.trim(),
      term: document.getElementById("lease-term").value.trim(),
      rent: document.getElementById("lease-rent").value.trim(),
      fees: document.getElementById("lease-fees").value.trim(),
      breach: document.getElementById("lease-breach").value.trim(),
      dispute: document.getElementById("lease-dispute").value.trim(),
      date: document.getElementById("lease-date").value.trim(),
    };
  }
  if (t === "借款合同") {
    return {
      contract_type: t,
      party_a: document.getElementById("loan-party-a").value.trim(),
      party_b: document.getElementById("loan-party-b").value.trim(),
      amount: document.getElementById("loan-amount").value.trim(),
      purpose: document.getElementById("loan-purpose").value.trim(),
      term: document.getElementById("loan-term").value.trim(),
      repayment: document.getElementById("loan-repayment").value.trim(),
      guarantee: document.getElementById("loan-guarantee").value.trim(),
      breach: document.getElementById("loan-breach").value.trim(),
      date: document.getElementById("loan-date").value.trim(),
    };
  }
  if (t === "服务合同") {
    return {
      contract_type: t,
      party_a: document.getElementById("service-party-a").value.trim(),
      party_b: document.getElementById("service-party-b").value.trim(),
      content: document.getElementById("service-content").value.trim(),
      term: document.getElementById("service-term").value.trim(),
      fee: document.getElementById("service-fee").value.trim(),
      acceptance: document.getElementById("service-acceptance").value.trim(),
      breach: document.getElementById("service-breach").value.trim(),
      dispute: document.getElementById("service-dispute").value.trim(),
      date: document.getElementById("service-date").value.trim(),
    };
  }
  return {
    contract_type: t,
    party_a: document.getElementById("labor-party-a").value.trim(),
    party_b: document.getElementById("labor-party-b").value.trim(),
    term: document.getElementById("labor-term").value.trim(),
    position: document.getElementById("labor-position").value.trim(),
    hours: document.getElementById("labor-hours").value.trim(),
    salary: document.getElementById("labor-salary").value.trim(),
    benefits: document.getElementById("labor-benefits").value.trim(),
    breach: document.getElementById("labor-breach").value.trim(),
    date: document.getElementById("labor-date").value.trim(),
  };
}

function contractFieldLabel(key) {
  return {
    contract_type: "合同类型",
    party_a: "甲方",
    party_b: "乙方",
    subject: "商品信息",
    price: "价款",
    payment: "付款方式",
    delivery: "交付与验收",
    breach: "违约责任",
    dispute: "争议解决",
    house: "房屋位置及状况",
    term: "期限",
    rent: "租金及押金",
    fees: "费用承担",
    amount: "借款金额",
    purpose: "借款用途",
    repayment: "利息及还款",
    guarantee: "担保/保证",
    content: "服务内容",
    fee: "服务费用",
    acceptance: "验收标准",
    position: "工作岗位和地点",
    hours: "工作时间和休息休假",
    salary: "劳动报酬",
    benefits: "社会保险和福利",
    date: "日期",
  }[key] || key;
}

async function downloadDoc() {
  if (!window._generatedDoc || !window._generatedDoc.body) return;
  const title = window._generatedDoc.title || "法律文书";
  const body = window._generatedDoc.body || "";
  const header = window._generatedDoc.header || {};

  try {
    const resp = await fetch("/api/download-docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        body,
        header,
        doc_type: window._generatedDoc.docType || "",
        complaint_fields: window._generatedDoc.complaintFields || {},
        appeal_fields: window._generatedDoc.appealFields || {},
        defense_fields: window._generatedDoc.defenseFields || {},
        execution_fields: window._generatedDoc.executionFields || {},
        counterclaim_fields: window._generatedDoc.counterclaimFields || {},
        jurisdiction_objection_fields: window._generatedDoc.jurisdictionObjectionFields || {},
        judicial_confirmation_fields: window._generatedDoc.judicialConfirmationFields || {},
        citizen_authorization_fields: window._generatedDoc.citizenAuthorizationFields || {},
        contract_fields: window._generatedDoc.contractFields || {},
        contract_type: window._generatedDoc.contractType || "",
      }),
    });
    if (!resp.ok) throw new Error("生成失败");
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}.docx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert("DOCX 下载失败: " + e.message);
  }
}

// ============================================================================
//  Module 5: Case Strategy
// ============================================================================
function renderStrategyResult(result) {
  let html = "";
  html += `<div class="stat-grid">
    <div class="stat-cell"><div class="stat-label">案件类型</div><div class="stat-value" style="font-size:18px;">${escapeHtml(result.case_type || "-")}</div></div>
    <div class="stat-cell"><div class="stat-label">案由</div><div class="stat-value" style="font-size:18px;">${escapeHtml(result.cause_of_action || "-")}</div></div>
    <div class="stat-cell"><div class="stat-label">胜诉评估</div><div class="stat-value" style="font-size:18px;">${escapeHtml(result.success_probability || "-")}</div></div>
    <div class="stat-cell"><div class="stat-label">下一步建议</div><div class="stat-value" style="font-size:18px;">${(result.next_steps || []).length} 项</div></div>
  </div>`;

  if (result.applicable_laws && result.applicable_laws.length) {
    html += `<div class="result-section-title">适用法律法规</div><ul>${result.applicable_laws.map(l => `<li>${escapeHtml(l)}</li>`).join("")}</ul>`;
  }
  if (result.legal_strategy) {
    html += `<div class="result-section-title">诉讼策略</div><div class="strategy-block">`;
    const s = result.legal_strategy;
    if (s.primary) html += `<div class="strategy-item"><strong>主攻策略</strong><p>${escapeHtml(s.primary)}</p></div>`;
    if (s.alternative) html += `<div class="strategy-item"><strong>备选策略</strong><p>${escapeHtml(s.alternative)}</p></div>`;
    if (s.settlement_advice) html += `<div class="strategy-item"><strong>调解 / 和解建议</strong><p>${escapeHtml(s.settlement_advice)}</p></div>`;
    html += `</div>`;
  }
  if (result.key_evidence && result.key_evidence.length) {
    html += `<div class="result-section-title">关键证据</div><ul>${result.key_evidence.map(e => `<li>${escapeHtml(e)}</li>`).join("")}</ul>`;
  }
  if (result.evidence_risks && result.evidence_risks.length) {
    html += `<div class="result-section-title">证据风险</div><ul style="color:var(--danger);">${result.evidence_risks.map(e => `<li>${escapeHtml(e)}</li>`).join("")}</ul>`;
  }
  if (result.jurisdiction_analysis) {
    html += `<div class="result-section-title">管辖分析</div><div class="strategy-item"><p>${escapeHtml(result.jurisdiction_analysis)}</p></div>`;
  }
  if (result.statute_of_limitation) {
    html += `<div class="result-section-title">诉讼时效</div><div class="strategy-item"><p>${escapeHtml(result.statute_of_limitation)}</p></div>`;
  }
  if (result.similar_cases && result.similar_cases.length) {
    html += `<div class="result-section-title">类案参考</div><ul>${result.similar_cases.map(c => `<li>${escapeHtml(c)}</li>`).join("")}</ul>`;
  }
  if (result.next_steps && result.next_steps.length) {
    html += `<div class="result-section-title">建议下一步</div><ol>${result.next_steps.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>`;
  }
  return html;
}

async function submitStrategy() {
  const parties = document.getElementById("strategy-parties").value.trim();
  const facts = document.getElementById("strategy-facts").value.trim();
  const dispute = document.getElementById("strategy-dispute").value.trim();
  const status = document.getElementById("strategy-status").value.trim();

  let caseDescription = "";
  if (parties) caseDescription += `当事人：${parties}\n`;
  if (facts) caseDescription += `事实经过：${facts}\n`;
  if (dispute) caseDescription += `争议焦点：${dispute}\n`;
  if (status) caseDescription += `当前进展：${status}`;
  caseDescription = caseDescription.trim();

  if (!caseDescription) return showError("strategy", "请至少填写当事人、事情经过或争议焦点");

  const text = caseDescription;

  const el = document.getElementById("strategy-result");
  el.innerHTML = renderModuleProgress("strategy");
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });

  let progressText = "";
  await apiPostStream("/api/strategy-stream", { case_description: text }, null,
    (chunk) => {
      progressText += chunk;
      updateModuleProgress("strategy", progressText);
    },
    (result) => {
      if (result.error) { showError("strategy", result.error); return; }
      const html = renderStrategyResult(result);
      showResult("strategy", html, !!result.demo_mode);
    }
  );
}

// ============================================================================
//  Module 6: Student Legal Issues
// ============================================================================
function renderStudentLegalResult(result) {
  let html = "";
  html += `<div class="stat-grid">
    <div class="stat-cell"><div class="stat-label">问题类型</div><div class="stat-value" style="font-size:18px;">${escapeHtml(result.issue_type || "-")}</div></div>
    <div class="stat-cell"><div class="stat-label">风险提醒</div><div class="stat-value" style="font-size:18px;">${(result.risk_points || []).length} 项</div></div>
    <div class="stat-cell"><div class="stat-label">证据清单</div><div class="stat-value" style="font-size:18px;">${(result.evidence_checklist || []).length} 项</div></div>
    <div class="stat-cell"><div class="stat-label">处理步骤</div><div class="stat-value" style="font-size:18px;">${(result.action_plan || []).length} 步</div></div>
    <div class="stat-cell"><div class="stat-label">可联系渠道</div><div class="stat-value" style="font-size:18px;">${(result.authority_channels || []).length} 项</div></div>
  </div>`;

  html += `<div class="student-report-intro">
    <strong>校园法律专题报告</strong>
    <span>围绕事实、证据、校规边界、外部救济和沟通文本形成可执行建议。</span>
  </div>`;

  if (result.legal_relationship) {
    html += `<div class="result-section-title">法律关系</div><div class="strategy-item"><p>${escapeHtml(result.legal_relationship)}</p></div>`;
  }
  if (result.school_rule_boundary) {
    html += `<div class="result-section-title">校规边界</div><div class="strategy-item"><p>${escapeHtml(result.school_rule_boundary)}</p></div>`;
  }
  if (result.applicable_laws && result.applicable_laws.length) {
    html += `<div class="result-section-title">可能适用的法律依据</div><ul>${result.applicable_laws.map(l => `<li>${escapeHtml(l)}</li>`).join("")}</ul>`;
  }
  if (result.rights_and_obligations && result.rights_and_obligations.length) {
    html += `<div class="result-section-title">权利义务</div><ul>${result.rights_and_obligations.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
  }
  if (result.evidence_checklist && result.evidence_checklist.length) {
    html += `<div class="result-section-title">证据清单</div><ul>${result.evidence_checklist.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
  }
  if (result.risk_points && result.risk_points.length) {
    html += `<div class="result-section-title">风险提醒</div><div class="risk-list">`;
    for (const r of result.risk_points) {
      const lv = riskClass(r.level);
      html += `<div class="risk-card ${lv}">
        <div class="risk-card-header"><span class="risk-card-title">${escapeHtml(r.point || "")}</span><span class="badge badge-${lv}">${escapeHtml(r.level || "中")}</span></div>
        ${r.suggestion ? `<p style="color:var(--success);">建议：${escapeHtml(r.suggestion)}</p>` : ""}
      </div>`;
    }
    html += `</div>`;
  }
  if (result.action_plan && result.action_plan.length) {
    html += `<div class="result-section-title">处理路径</div><ol>${result.action_plan.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>`;
  }
  if (result.communication_template) {
    html += `<div class="result-section-title">沟通文本</div><div class="doc-preview">${escapeHtml(result.communication_template)}</div>`;
  }
  if (result.authority_channels && result.authority_channels.length) {
    html += `<div class="result-section-title">可联系渠道</div><ul>${result.authority_channels.map(c => `<li>${escapeHtml(c)}</li>`).join("")}</ul>`;
  }
  if (result.disclaimer) {
    html += `<div class="result-section-title">提示</div><p style="color:var(--text-muted);font-size:13px;">${escapeHtml(result.disclaimer)}</p>`;
  }
  return html;
}

async function submitStudentLegal() {
  const scenario = document.getElementById("student-scenario").value;
  const time = document.getElementById("student-time").value.trim();
  const place = document.getElementById("student-place").value.trim();
  const opposite = document.getElementById("student-opposite").value.trim();
  const facts = document.getElementById("student-facts").value.trim();
  const handling = document.getElementById("student-handling").value.trim();
  const evidence = document.getElementById("student-evidence").value.trim();
  const claim = document.getElementById("student-claim").value.trim();

  let description = "";
  if (time) description += `发生时间：${time}\n`;
  if (place) description += `发生地点：${place}\n`;
  if (opposite) description += `涉及对象：${opposite}\n`;
  if (facts) description += `具体事实：${facts}\n`;
  if (handling) description += `已有处理：${handling}\n`;
  if (evidence) description += `已有证据：${evidence}\n`;
  if (claim) description += `学生诉求：${claim}`;
  description = description.trim();

  if (description.length < 10) return showError("student", "请至少输入10字的问题描述");

  const el = document.getElementById("student-result");
  el.innerHTML = renderModuleProgress("student");
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });

  let progressText = "";
  await apiPostStream("/api/student-legal-stream", { scenario, description }, null,
    (chunk) => {
      progressText += chunk;
      updateModuleProgress("student", progressText);
    },
    (result) => {
      if (result.error) { showError("student", result.error); return; }
      const html = renderStudentLegalResult(result);
      showResult("student", html, !!result.demo_mode);
    }
  );
}

// ===== History =====
const moduleLabels = {
  analyze: "文书分析",
  search: "法规检索",
  review: "合同审查",
  generate: "文书生成",
  strategy: "策略分析",
  student_legal: "学生法律"
};
let historyRecords = [];

function toggleHistoryPanel() {
  const overlay = document.getElementById("history-overlay");
  const panel = document.getElementById("history-panel");
  overlay.classList.toggle("hidden");
  panel.classList.toggle("hidden");
  if (!panel.classList.contains("hidden")) {
    loadHistory();
  }
}

async function loadHistory() {
  const el = document.getElementById("history-content");
  el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">加载中...</p>';
  try {
    const resp = await fetch("/api/history");
    if (resp.status === 401) {
      el.innerHTML = '<p style="color:var(--danger);font-size:13px;">请先登录后查看历史记录</p>';
      return;
    }
    const data = await resp.json();
    const records = data.records || [];
    if (!records.length) {
      el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">暂无历史记录</p>';
      return;
    }
    historyRecords = records;
    el.innerHTML = `<div class="history-list">${records.map(renderHistoryItem).join("")}</div>`;
  } catch (e) {
    el.innerHTML = '<p style="color:var(--danger);font-size:13px;">历史记录加载失败</p>';
  }
}

function renderHistoryItem(record, index) {
  const label = moduleLabels[record.module_type] || record.module_type || "记录";
  const text = (record.input_text || "").replace(/\s+/g, " ").slice(0, 140);
  return `<div class="history-item" id="history-item-${record.id}">
    <div class="history-item-head">
      <span class="badge badge-info">${escapeHtml(label)}</span>
      <span>${escapeHtml(record.created_at || "")}</span>
    </div>
    <p class="history-question">${escapeHtml(text || "无输入摘要")}</p>
    <div class="history-actions">
      <button class="btn-history-action" onclick="toggleHistoryAnswer(${index})">查看回答</button>
      <button class="btn-history-action danger" onclick="deleteHistoryRecord(${record.id})">删除</button>
    </div>
    <div class="history-answer hidden" id="history-answer-${record.id}">${renderHistoryAnswer(record.result)}</div>
  </div>`;
}

function toggleHistoryAnswer(index) {
  const record = historyRecords[index];
  if (!record) return;
  const answer = document.getElementById(`history-answer-${record.id}`);
  if (!answer) return;
  answer.classList.toggle("hidden");
}

async function deleteHistoryRecord(recordId) {
  if (!confirm("确定删除这条历史记录吗？")) return;
  try {
    const resp = await fetch(`/api/history/${recordId}`, { method: "DELETE" });
    if (!resp.ok) {
      alert("删除失败");
      return;
    }
    loadHistory();
  } catch (e) {
    alert("删除失败");
  }
}

function renderHistoryAnswer(result) {
  if (!result || typeof result !== "object") {
    return `<p>${escapeHtml(String(result || "暂无回答内容"))}</p>`;
  }
  if (result.raw) {
    return `<pre>${escapeHtml(result.raw)}</pre>`;
  }
  const hiddenKeys = new Set(["demo_mode", "local_references", "llm_error"]);
  const rows = Object.entries(result).filter(([key]) => !hiddenKeys.has(key));
  if (!rows.length) {
    return `<p>暂无回答内容</p>`;
  }
  return rows.map(([key, value]) => `<div class="history-answer-row">
    <strong>${escapeHtml(historyFieldLabel(key))}</strong>
    <div>${formatHistoryValue(value)}</div>
  </div>`).join("");
}

function formatHistoryValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) {
    return `<ul>${value.map(item => `<li>${formatHistoryValue(item)}</li>`).join("")}</ul>`;
  }
  if (typeof value === "object") {
    return Object.entries(value).map(([key, val]) => `<p><b>${escapeHtml(historyFieldLabel(key))}：</b>${formatHistoryValue(val)}</p>`).join("");
  }
  return escapeHtml(String(value));
}

function historyFieldLabel(key) {
  const labels = {
    document_type: "文书类型",
    parties: "涉及各方",
    key_clauses: "核心条款",
    risk_points: "风险提示",
    legal_basis: "法律依据",
    revision_suggestions: "修改建议",
    overall_assessment: "综合评估",
    legal_analysis: "法律分析",
    provisions: "检索法条",
    practical_advice: "实务建议",
    contract_type: "合同类型",
    overall_risk_level: "整体风险",
    overall_risk_score: "风险评分",
    risk_items: "风险项",
    missing_clauses: "缺失条款",
    summary: "小结",
    title: "标题",
    header: "文书信息",
    body: "正文",
    attachments: "证据材料",
    notes: "注意事项",
    case_type: "案件类型",
    cause_of_action: "案由",
    success_probability: "胜诉评估",
    applicable_laws: "适用法律",
    legal_strategy: "法律策略",
    key_evidence: "关键证据",
    evidence_risks: "证据风险",
    jurisdiction_analysis: "管辖分析",
    statute_of_limitation: "诉讼时效",
    similar_cases: "类案参考",
    next_steps: "下一步",
    issue_type: "问题类型",
    legal_relationship: "法律关系",
    school_rule_boundary: "校规边界",
    rights_and_obligations: "权利义务",
    evidence_checklist: "证据清单",
    action_plan: "处理路径",
    communication_template: "沟通文本",
    authority_channels: "可联系渠道",
    disclaimer: "提示"
  };
  return labels[key] || key;
}

// ===== API Configuration =====
const API_PROVIDER_MODELS = {
  "https://api.deepseek.com/v1": [
    ["deepseek-flash", "DeepSeek V4.1 Flash（推荐）"],
    ["deepseek-v4-pro", "DeepSeek V4 Pro"],
    ["deepseek-chat", "DeepSeek Chat（兼容）"],
  ],
  "https://dashscope.aliyuncs.com/compatible-mode/v1": [
    ["qwen-plus", "qwen-plus"],
    ["qwen-turbo", "qwen-turbo"],
    ["qwen-max", "qwen-max"],
  ],
  "https://open.bigmodel.cn/api/paas/v4": [
    ["glm-5.1", "glm-5.1"],
    ["glm-5-turbo", "glm-5-turbo"],
    ["glm-4.7-flash", "glm-4.7-flash"],
  ],
  "https://api.moonshot.cn/v1": [
    ["kimi-k2.6", "kimi-k2.6"],
    ["moonshot-v1-8k", "moonshot-v1-8k"],
    ["moonshot-v1-32k", "moonshot-v1-32k"],
  ],
};
const API_PROVIDER_META = {
  "https://api.deepseek.com/v1": { name: "DeepSeek", docs: "https://api-docs.deepseek.com/" },
  "https://dashscope.aliyuncs.com/compatible-mode/v1": { name: "通义千问", docs: "https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope" },
  "https://open.bigmodel.cn/api/paas/v4": { name: "GLM 智谱", docs: "https://docs.bigmodel.cn/cn/api/introduction" },
  "https://api.moonshot.cn/v1": { name: "Kimi", docs: "https://platform.moonshot.cn/docs/api/quickstart" },
};

function syncProviderModels(selectedModel = "") {
  const urlEl = document.getElementById("cfg-url");
  const modelEl = document.getElementById("cfg-model");
  const linkEl = document.getElementById("cfg-provider-link");
  const models = API_PROVIDER_MODELS[urlEl.value] || API_PROVIDER_MODELS["https://api.deepseek.com/v1"];
  const meta = API_PROVIDER_META[urlEl.value] || API_PROVIDER_META["https://api.deepseek.com/v1"];
  modelEl.innerHTML = models.map(([value, label]) =>
    `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`
  ).join("");
  modelEl.value = selectedModel && models.some(([value]) => value === selectedModel)
    ? selectedModel
    : models[0][0];
  if (linkEl) {
    linkEl.href = meta.docs;
    linkEl.textContent = `获取 ${meta.name} API Key`;
  }
  updateConfigCurrent();
}

function updateConfigCurrent(hasKey = null) {
  const currentEl = document.getElementById("cfg-current");
  const urlEl = document.getElementById("cfg-url");
  const modelEl = document.getElementById("cfg-model");
  if (!currentEl || !urlEl || !modelEl) return;
  const meta = API_PROVIDER_META[urlEl.value] || API_PROVIDER_META["https://api.deepseek.com/v1"];
  const keyText = hasKey === null ? "" : ` · ${hasKey ? "已保存 Key" : "未保存 Key"}`;
  currentEl.textContent = `当前配置：${meta.name} / ${modelEl.value || "-"}${keyText}`;
}

function toggleConfig() {
  document.getElementById("config-overlay").classList.toggle("hidden");
  document.getElementById("config-panel").classList.toggle("hidden");
  if (!document.getElementById("config-panel").classList.contains("hidden")) {
    loadConfig();
  }
}

async function loadConfig() {
  syncProviderModels();
  try {
    const resp = await fetch("/api/config");
    const data = await resp.json();
    if (data.base_url && API_PROVIDER_MODELS[data.base_url]) {
      document.getElementById("cfg-url").value = data.base_url;
    }
    syncProviderModels(data.model);
    document.getElementById("cfg-key").placeholder = data.has_api_key ? "已保存，可输入新 Key 覆盖" : "请输入 API Key";
    updateConfigCurrent(data.has_api_key);
  } catch (e) {
    syncProviderModels();
    updateConfigCurrent(false);
  }
}

function saveConfig() {
  const key = document.getElementById("cfg-key").value.trim();
  const url = document.getElementById("cfg-url").value.trim();
  const model = document.getElementById("cfg-model").value.trim();
  const msgEl = document.getElementById("config-msg");

  if (!key) {
    msgEl.textContent = "请输入 API Key";
    msgEl.style.color = "var(--danger)";
    return;
  }

  fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: key, base_url: url, model: model }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.status === "ok") {
        msgEl.textContent = data.message || "配置已保存";
        msgEl.style.color = "var(--success)";
        document.getElementById("cfg-key").value = "";
        document.getElementById("cfg-key").placeholder = "已保存，可输入新 Key 覆盖";
        updateConfigCurrent(true);
        updateStatusBadge(false);
      } else {
        msgEl.textContent = data.error || "保存失败";
        msgEl.style.color = "var(--danger)";
      }
    })
    .catch(() => {
      msgEl.textContent = "网络错误";
      msgEl.style.color = "var(--danger)";
    });
}

async function testConfig() {
  const key = document.getElementById("cfg-key").value.trim();
  const url = document.getElementById("cfg-url").value.trim();
  const model = document.getElementById("cfg-model").value.trim();
  const msgEl = document.getElementById("config-msg");
  msgEl.textContent = "正在测试连接...";
  msgEl.style.color = "var(--text-muted)";
  try {
    const resp = await fetch("/api/config/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key, base_url: url, model }),
    });
    const data = await resp.json();
    msgEl.textContent = data.message || (resp.ok ? "连接测试成功" : "连接测试失败");
    msgEl.style.color = resp.ok ? "var(--success)" : "var(--danger)";
  } catch (e) {
    msgEl.textContent = "网络错误";
    msgEl.style.color = "var(--danger)";
  }
}

function updateStatusBadge(isDemo) {
  const pulse = document.getElementById("status-pulse");
  const label = document.getElementById("api-status-label");
  if (isDemo) {
    pulse.classList.remove("live");
    label.textContent = "演示模式";
  } else {
    pulse.classList.add("live");
    label.textContent = "AI 已连接";
  }
}

// ===== Auth =====
function showAuth() {
  document.getElementById("auth-overlay").classList.remove("hidden");
}

function hideAuth() {
  document.getElementById("auth-overlay").classList.add("hidden");
}

function switchAuth(type) {
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const tabs = document.querySelectorAll(".auth-tab");
  const switchText = document.getElementById("auth-switch-text");
  if (type === "register") {
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");
    tabs[0].classList.remove("active");
    tabs[1].classList.add("active");
    if (switchText) switchText.innerHTML = '已有账号？<a href="#" onclick="switchAuth(\'login\');return false;">去登录</a>';
  } else {
    registerForm.classList.add("hidden");
    loginForm.classList.remove("hidden");
    tabs[0].classList.add("active");
    tabs[1].classList.remove("active");
    if (switchText) switchText.innerHTML = '还没有账号？<a href="#" onclick="switchAuth(\'register\');return false;">立即注册</a>';
  }
  document.getElementById("login-error").textContent = "";
  document.getElementById("register-error").textContent = "";
}

function applyUserUI(u) {
  document.getElementById("header-username").textContent = u.username;
  document.getElementById("header-user").classList.remove("hidden");
  window._user = u;
  const workspaceName = document.getElementById("workspace-username");
  if (workspaceName) workspaceName.textContent = u.username;

  // 全部先隐藏
  document.getElementById("admin-status-group").style.display = "none";
  document.getElementById("btn-admin-panel").style.display = "none";
  document.getElementById("btn-config-gear").style.display = "";
  document.getElementById("approval-hint").classList.add("hidden");

  if (u.is_admin) {
    document.getElementById("admin-status-group").style.display = "";
    document.getElementById("btn-admin-panel").style.display = "";
    document.getElementById("btn-config-gear").style.display = "";
  } else {
    updateQuotaHint();
  }
  loadAgentConversations();
  if (typeof initMingjianChat === "function") initMingjianChat();
}

function updateQuotaHint() {
  const u = window._user;
  const hint = document.getElementById("approval-hint");
  const text = document.getElementById("free-quota-text");

  if (!u || u.is_admin) {
    hint.classList.add("hidden");
    return;
  }

  text.classList.remove("quota-exhausted");
  if (u.has_llm_api_key) {
    text.textContent = "个人 API 已启用";
  } else if (u.is_approved) {
    text.textContent = "AI 权限已开通";
  } else {
    const limit = Number.isFinite(Number(u.free_api_limit)) ? Number(u.free_api_limit) : 10;
    const remaining = Number.isFinite(Number(u.free_api_remaining)) ? Number(u.free_api_remaining) : limit;
    text.textContent = `免费额度 ${remaining}/${limit}`;
    if (remaining <= 0) text.classList.add("quota-exhausted");
  }
  hint.classList.remove("hidden");
  updateWorkspaceQuota();
}

async function doLogin() {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errEl = document.getElementById("login-error");

  if (!username) { errEl.textContent = "请输入用户名"; return false; }
  if (!password) { errEl.textContent = "请输入密码"; return false; }

  try {
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      hideAuth();
      applyUserUI(data.user);
      initApp();
    } else {
      errEl.textContent = data.error || "登录失败";
    }
  } catch (e) {
    errEl.textContent = "网络错误";
  }
  return false;
}

async function doRegister() {
  const username = document.getElementById("register-username").value.trim();
  const password = document.getElementById("register-password").value.trim();
  const errEl = document.getElementById("register-error");

  if (username.length < 3) { errEl.textContent = "用户名至少3个字符"; return false; }
  if (password.length < 6) { errEl.textContent = "密码至少6个字符"; return false; }

  try {
    const resp = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      hideAuth();
      applyUserUI(data.user);
      initApp();
    } else {
      errEl.textContent = data.error || "注册失败";
    }
  } catch (e) {
    errEl.textContent = "网络错误";
  }
  return false;
}

async function doLogout() {
  if (typeof disconnectMingjianChat === "function") disconnectMingjianChat();
  await fetch("/api/auth/logout", { method: "POST" });
  if (typeof closeCommunityComposer === "function") closeCommunityComposer();
  if (typeof closeCommunityDetail === "function") closeCommunityDetail();
  if (typeof closeCaseDetail === "function") closeCaseDetail();
  if (typeof closeChatDrawer === "function") closeChatDrawer();
  document.getElementById("header-user").classList.add("hidden");
  document.getElementById("admin-status-group").style.display = "none";
  document.getElementById("btn-admin-panel").style.display = "none";
  document.getElementById("btn-config-gear").style.display = "none";
  document.getElementById("approval-hint").classList.add("hidden");
  document.getElementById("history-overlay").classList.add("hidden");
  document.getElementById("history-panel").classList.add("hidden");
  document.getElementById("agent-history-overlay")?.classList.add("hidden");
  document.getElementById("agent-history-panel")?.classList.add("hidden");
  startNewAgentConversation();
  window._user = null;
  switchModule("home");
  showAuth();
}

async function initApp() {
  try {
    const data = await apiGet("/api/status");
    if (!data.error) {
      updateStatusBadge(data.demo_mode);
    }
  } catch (e) {}

  try {
    const resp = await fetch("/api/auth/status");
    const data = await resp.json();
    if (data.authenticated && data.user) {
      window._user = data.user;
      if (data.user.is_admin) {
        document.getElementById("admin-status-group").style.display = "";
        document.getElementById("btn-admin-panel").style.display = "";
        document.getElementById("btn-config-gear").style.display = "";
      } else {
        document.getElementById("btn-config-gear").style.display = "";
        updateQuotaHint();
      }
    }
  } catch (e) {}
}

// ===== Admin Panel =====
function toggleAdminPanel() {
  document.getElementById("admin-overlay").classList.toggle("hidden");
  document.getElementById("admin-panel").classList.toggle("hidden");
  if (!document.getElementById("admin-panel").classList.contains("hidden")) {
    loadAllUsers();
  }
}

function formatApprovalTime(value) {
  if (!value) return "申请时间未知";
  const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return "申请时间未知";
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

async function loadAllUsers() {
  const el = document.getElementById("admin-content");
  el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">加载中...</p>';
  try {
    const [userResp, metricResp] = await Promise.all([
      fetch("/api/admin/all-users"),
      fetch("/api/admin/metrics"),
    ]);
    const data = await userResp.json();
    const metrics = metricResp.ok ? await metricResp.json() : null;
    if (!data.users || !data.users.length) {
      el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">暂无用户</p>';
      return;
    }
    let html = renderAdminMetrics(metrics);
    html += '<div class="admin-subtitle">用户管理</div><div class="admin-user-list">';
    for (const u of data.users) {
      const approved = u.is_admin ? '<span class="badge badge-admin">管理员</span>' :
        (u.has_llm_api_key ? '<span class="badge badge-low">个人 API</span>' :
        (u.is_approved ? '<span class="badge badge-low">不限次数</span>' :
        `<span class="badge ${u.free_api_remaining > 0 ? 'badge-medium' : 'badge-high'}">免费 ${u.free_api_remaining}/${u.free_api_limit}</span>`));
      const modelVal = u.llm_model || 'deepseek-v4-pro';
      const approvalTime = u.approval_requested || u.is_approved
        ? `<span class="admin-request-time">申请时间：${formatApprovalTime(u.approval_requested_at)}</span>`
        : '';
      html += `<div class="admin-user-row">
        <div class="admin-user-info">
          <span class="admin-user-name">${escapeHtml(u.username)}</span>
          ${approved}
          ${approvalTime}
        </div>
        <div class="admin-user-model">
          <select class="model-input" id="model-${u.id}" ${u.is_admin ? 'disabled' : ''}>
            <option value="deepseek-v4-pro" ${modelVal === 'deepseek-v4-pro' ? 'selected' : ''}>deepseek-v4-pro</option>
            <option value="deepseek-v4-flash" ${modelVal === 'deepseek-v4-flash' ? 'selected' : ''}>deepseek-v4-flash</option>
          </select>
          <button class="btn-save-model" onclick="setUserModel(${u.id})" ${u.is_admin ? 'disabled' : ''}>保存</button>
        </div>
        <div class="admin-user-actions">
          ${!u.is_admin && u.approval_requested && !u.is_approved ? `<button class="btn-approve" onclick="approveUser(${u.id})">通过</button><button class="btn-reject" onclick="rejectUser(${u.id})">驳回</button>` : ''}
          ${!u.is_admin ? `<button class="btn-delete-user" onclick="deleteUser(${u.id})">删除</button>` : ''}
          ${!u.is_admin && u.is_approved ? `<button class="btn-reject" onclick="revokeUser(${u.id})">取消使用</button>` : ''}
        </div>
      </div>`;
    }
    html += "</div>";
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<p style="color:var(--danger);font-size:13px;">加载失败</p>';
  }
}

async function setUserModel(userId) {
  const input = document.getElementById(`model-${userId}`);
  const val = input.value.trim();
  try {
    const resp = await fetch(`/api/admin/set-model/${userId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ llm_model: val }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      input.style.borderColor = "var(--success)";
      setTimeout(() => { input.style.borderColor = ""; }, 1500);
    } else {
      alert(data.error || "操作失败");
    }
  } catch (e) {
    alert("网络错误");
  }
}

async function approveUser(userId) {
  try {
    const resp = await fetch(`/api/admin/approve/${userId}`, { method: "POST" });
    const data = await resp.json();
    if (data.status === "ok") {
      loadAllUsers();
    } else {
      alert(data.error || "操作失败");
    }
  } catch (e) {
    alert("网络错误");
  }
}

async function rejectUser(userId) {
  try {
    const resp = await fetch(`/api/admin/reject/${userId}`, { method: "POST" });
    const data = await resp.json();
    if (data.status === "ok") {
      loadAllUsers();
    } else {
      alert(data.error || "操作失败");
    }
  } catch (e) {
    alert("网络错误");
  }
}

function renderAdminMetrics(metrics) {
  if (!metrics) return "";
  const moduleLabels = {
    analyze: "文书分析",
    search: "法规检索",
    review: "合同审查",
    generate: "文书生成",
    strategy: "策略分析",
    student_legal: "学生法律",
  };
  const modules = Object.entries(metrics.usage.by_module || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([name, count]) => `<span>${escapeHtml(moduleLabels[name] || name)} ${count}</span>`)
    .join("");
  return `<div class="admin-metrics">
    <div class="admin-metric"><strong>${metrics.users.total}</strong><span>用户总数</span></div>
    <div class="admin-metric"><strong>${metrics.users.quota_exhausted || 0}</strong><span>额度已用完</span></div>
    <div class="admin-metric"><strong>${metrics.users.personal_api}</strong><span>自配 API</span></div>
    <div class="admin-metric"><strong>${metrics.usage.today}</strong><span>今日调用</span></div>
    <div class="admin-metric"><strong>${metrics.usage.last_7_days}</strong><span>近7日调用</span></div>
    <div class="admin-module-rank">${modules || "<span>暂无调用</span>"}</div>
  </div>`;
}

async function deleteUser(userId) {
  if (!confirm("确定删除该用户吗？该操作会同时删除他的历史记录。")) return;
  try {
    const resp = await fetch(`/api/admin/delete-user/${userId}`, { method: "POST" });
    const data = await resp.json();
    if (data.status === "ok") {
      loadAllUsers();
    } else {
      alert(data.error || "操作失败");
    }
  } catch (e) {
    alert("网络错误");
  }
}


async function revokeUser(userId) {
  try {
    const resp = await fetch(`/api/admin/revoke/${userId}`, { method: "POST" });
    const data = await resp.json();
    if (data.status === "ok") {
      loadAllUsers();
    } else {
      alert(data.error || "操作失败");
    }
  } catch (e) {
    alert("网络错误");
  }
}

// ===== Initialization =====
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const resp = await fetch("/api/auth/status");
    const data = await resp.json();
    if (data.authenticated) {
      hideAuth();
      applyUserUI(data.user);
      initApp();
    } else {
      showAuth();
    }
  } catch (e) {
    showAuth();
  }
});
