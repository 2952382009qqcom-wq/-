import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from core.models import db
from core.taxonomy import CASE_CATEGORIES, COMMUNITY_CATEGORIES, classify_case_content
from core.community.models import CommunityCategory
from core.search.indexing import enqueue_index, process_outbox

from .models import CaseCategory, CaseLawReference, CaseTag, LegalCase, LegalCaseCategory, LegalCaseTag
from .student_cases import RECENT_STUDENT_CASES


VERIFIED_CASES = (
    {
        "slug": "guiding-case-38-tian-yong-v-ustb",
        "title": "田永诉北京科技大学拒绝颁发毕业证、学位证案",
        "case_number": "（1999）一中行终字第73号",
        "guiding_case_number": "指导案例38号",
        "court_name": "北京市第一中级人民法院",
        "case_type": "行政",
        "cause": "教育行政管理",
        "legal_domain": "campus",
        "decision_date": date(1999, 4, 26),
        "published_at": datetime(2014, 12, 25, 10, 15, 0),
        "summary": "学生因考试违纪被学校按退学处理，但学校未依法送达决定，之后又持续为其注册并安排完成学业。毕业时学校拒绝颁发毕业证并拒绝启动学位审核，学生提起行政诉讼。",
        "dispute_focus": "高校学籍处分是否符合法律和正当程序；学生能否就毕业证、学位资格审核等涉及基本受教育权的学校管理行为提起行政诉讼。",
        "judgment_result": "二审驳回学校上诉，维持一审判决；学校应颁发毕业证、依法组织学位资格审核并办理毕业派遣手续。",
        "judgment_reasoning": "高校虽有教育自主权和学生管理权，但校规及处分必须符合法律规范并保障学生陈述、申辩和送达等程序权利。学校之后恢复注册并允许完成学业的行为也产生相应法律后果。",
        "ai_plain_language": "学校可以管理和处分学生，但不能只凭内部规定任意剥夺学籍、毕业资格。涉及退学、毕业证和学位等重大权益时，处理依据和程序都必须合法。",
        "keywords": "高校处分,学籍,毕业证,学位,正当程序,受教育权",
        "source_external_id": "court-13222",
        "source_url": "https://www.court.gov.cn/shenpan/xiangqing/13222.html",
        "categories": ("student-daily", "campus-rights"),
        "tags": ("学籍", "高校处分", "毕业证", "正当程序"),
        "laws": (("中华人民共和国教育法", "", "高校颁发学业证书的职责"),),
    },
    {
        "slug": "guiding-case-39-he-xiaoqiang-v-hust",
        "title": "何小强诉华中科技大学拒绝授予学位案",
        "case_number": "（2009）武行终字第61号",
        "guiding_case_number": "指导案例39号",
        "court_name": "湖北省武汉市中级人民法院",
        "case_type": "行政",
        "cause": "学位授予",
        "legal_domain": "campus",
        "decision_date": date(2009, 5, 31),
        "published_at": datetime(2014, 12, 25, 10, 15, 35),
        "summary": "本科毕业生因未达到学校制定的学位授予学术标准而未被推荐授予学士学位，之后起诉具有学位授予权的高校。",
        "dispute_focus": "高校不授予学位的决定是否可诉；法院应如何审查高校在学术自治范围内制定并适用的学位标准。",
        "judgment_result": "二审驳回上诉，维持驳回授予学位诉求的判决。",
        "judgment_reasoning": "不授予学位的决定可以接受司法审查；但高校在法律授权和学术自治范围内制定的学术水平标准具有正当依据，法院尊重其专业判断。",
        "ai_plain_language": "学生可以要求法院审查学校拒发学位是否合法，但法院通常不会代替学校作学术判断。关键是学校的标准是否有法律依据、是否提前明确、适用是否一致。",
        "keywords": "学位,学术自治,高校,行政诉讼,学位标准",
        "source_external_id": "court-13223",
        "source_url": "https://www.court.gov.cn/shenpan/xiangqing/13223.html",
        "categories": ("student-daily", "campus-rights"),
        "tags": ("学位", "学术自治", "行政诉讼"),
        "laws": (("中华人民共和国学位条例", "第四条、第八条", "学士学位授予条件"),),
    },
    {
        "slug": "guiding-case-180-sun-xianfeng-labor-termination",
        "title": "孙贤锋诉淮安西区人力资源开发有限公司劳动合同纠纷案",
        "case_number": "（2019）苏07民终658号",
        "guiding_case_number": "指导案例180号",
        "court_name": "江苏省连云港市中级人民法院",
        "case_type": "民事",
        "cause": "劳动合同纠纷",
        "legal_domain": "labor",
        "decision_date": date(2019, 4, 22),
        "published_at": datetime(2022, 7, 6, 14, 43, 52),
        "summary": "用人单位以劳动者旷工为由解除劳动合同，诉讼中又补充提出其他违纪事实。劳动者主张解除违法并请求赔偿。",
        "dispute_focus": "判断单方解除是否合法时，法院能否采纳解除通知中没有载明、由单位在诉讼中补充的其他理由。",
        "judgment_result": "判令用人单位支付违法解除劳动合同赔偿金，二审维持。",
        "judgment_reasoning": "解除通知对用人单位具有约束力，合法性审查应以通知当时载明的理由及证据为限；单位未证明通知所称旷工事实，不能事后更换解除理由。",
        "ai_plain_language": "公司辞退员工时写在解除通知里的理由很重要。打官司后再临时补充其他理由，通常不能用来挽救原本证据不足的辞退决定。",
        "keywords": "劳动合同,违法解除,解除通知,举证责任,赔偿金",
        "source_external_id": "court-364641",
        "source_url": "https://www.court.gov.cn/fabu/xiangqing/364641.html",
        "categories": ("student-daily", "daily-life", "labor"),
        "tags": ("违法解除", "解除通知", "赔偿金"),
        "laws": (("中华人民共和国劳动合同法", "第三十九条", "用人单位单方解除条件"),),
    },
    {
        "slug": "guiding-case-185-yan-jialin-equal-employment",
        "title": "闫佳琳诉浙江喜来登度假村有限公司平等就业权纠纷案",
        "case_number": "（2020）浙01民终736号",
        "guiding_case_number": "指导案例185号",
        "court_name": "杭州市中级人民法院",
        "case_type": "民事",
        "cause": "平等就业权纠纷",
        "legal_domain": "labor",
        "decision_date": date(2020, 5, 15),
        "published_at": datetime(2022, 7, 6, 14, 50, 10),
        "summary": "求职者投递岗位后，被招聘方以其户籍地域为由标记不合适。求职者主张平等就业权受到侵害。",
        "dispute_focus": "用人单位能否使用与工作内在要求没有必然联系的地域因素筛选求职者；就业歧视应承担何种民事责任。",
        "judgment_result": "判令招聘方赔偿精神抚慰金及合理维权费用，并公开赔礼道歉；二审维持。",
        "judgment_reasoning": "地域属于个人难以选择的先赋因素，与岗位内在要求没有关联时，以此差别对待求职者缺乏正当性，侵害人格尊严和平等就业机会。",
        "ai_plain_language": "招聘可以看能力、学历和岗位经验，但不能用与工作无关的籍贯、性别等标签随意拒绝求职者。遇到明确歧视时应保存招聘页面、平台记录和沟通证据。",
        "keywords": "招聘,就业歧视,地域歧视,平等就业权,求职",
        "source_external_id": "court-364691",
        "source_url": "https://www.court.gov.cn/fabu/xiangqing/364691.html",
        "categories": ("student-daily", "daily-life", "labor"),
        "tags": ("招聘", "就业歧视", "人格权"),
        "laws": (("中华人民共和国就业促进法", "第三条、第二十六条", "平等就业与禁止就业歧视"),),
    },
    {
        "slug": "guiding-case-23-sun-yinshan-food-safety",
        "title": "孙银山诉南京欧尚超市有限公司江宁店买卖合同纠纷案",
        "case_number": "（2012）江宁开民初字第646号",
        "guiding_case_number": "指导案例23号",
        "court_name": "江苏省南京市江宁区人民法院",
        "case_type": "民事",
        "cause": "买卖合同纠纷",
        "legal_domain": "consumer",
        "decision_date": date(2012, 9, 10),
        "published_at": datetime(2014, 1, 29, 14, 31, 49),
        "summary": "消费者在超市购买到超过保质期的食品，协商未果后起诉要求适用食品安全法规定的惩罚性赔偿。",
        "dispute_focus": "购买者在购买时是否明知食品过期，会不会影响其消费者身份和依法请求惩罚性赔偿的权利。",
        "judgment_result": "判令销售者按照当时适用的食品安全法支付价款十倍赔偿金，判决生效。",
        "judgment_reasoning": "购买商品用于个人、家庭生活而非经营即属于消费行为；销售者负有保障食品安全并及时清理过期食品的法定义务，购买者是否事先明知不影响法定赔偿请求。",
        "ai_plain_language": "发现过期或不符合食品安全标准的食品时，要保留购物小票、商品包装、保质期照片和与商家的沟通记录，再根据现行食品安全法核对可主张的赔偿标准。",
        "keywords": "食品安全,过期食品,消费者,惩罚性赔偿,购物凭证",
        "source_external_id": "court-13326",
        "source_url": "https://www.court.gov.cn/shenpan/xiangqing/13326.html",
        "categories": ("student-daily", "daily-life", "consumer"),
        "tags": ("食品安全", "消费赔偿", "过期食品"),
        "laws": (("中华人民共和国食品安全法", "", "不符合食品安全标准食品的赔偿责任，具体条号应按现行法核验"),),
    },
    {
        "slug": "guiding-case-170-rao-guoli-house-lease",
        "title": "饶国礼诉某物资供应站等房屋租赁合同纠纷案",
        "case_number": "指导案例170号所涉生效裁判",
        "guiding_case_number": "指导案例170号",
        "court_name": "最高人民法院",
        "case_type": "民事",
        "cause": "房屋租赁合同纠纷",
        "legal_domain": "housing",
        "decision_date": None,
        "published_at": datetime(2021, 11, 11, 10, 50, 51),
        "summary": "出租房屋在订约前已被鉴定为存在严重结构隐患、应尽快拆除的危房，双方仍约定用于经营酒店，之后就合同效力、损失和保证金返还发生争议。",
        "dispute_focus": "出租危及公共安全的房屋是否导致租赁合同无效；合同无效后保证金和双方损失如何处理。",
        "judgment_result": "确认租赁合同无效；出租方退还基于无效合同取得的保证金，双方损失按各自过错承担。",
        "judgment_reasoning": "将严重危房出租用于公众经营活动危及不特定公众安全，违反公序良俗和公共利益；无效合同取得的财产应当返还。",
        "ai_plain_language": "租房不只是价格和押金问题，房屋本身必须安全。若房屋存在严重安全隐患，合同可能无效，已付押金原则上应返还，但损失还会结合双方是否明知等过错判断。",
        "keywords": "房屋租赁,危房,合同无效,保证金,押金,公共安全",
        "source_external_id": "court-331211",
        "source_url": "https://www.court.gov.cn/fabu/xiangqing/331211.html",
        "categories": ("student-daily", "daily-life", "housing"),
        "tags": ("租赁安全", "押金", "合同无效"),
        "laws": (("中华人民共和国民法典", "第一百五十三条、第一百五十七条", "违背公序良俗及民事法律行为无效后的处理"),),
    },
    {
        "slug": "guiding-case-195-phone-code-personal-information",
        "title": "罗文君、瞿小珍侵犯公民个人信息刑事附带民事公益诉讼案",
        "case_number": "（2021）湘0212刑初149号",
        "guiding_case_number": "指导案例195号",
        "court_name": "湖南省株洲市渌口区人民法院",
        "case_type": "刑事附带民事公益诉讼",
        "cause": "侵犯公民个人信息",
        "legal_domain": "cyber",
        "decision_date": date(2021, 11, 30),
        "published_at": datetime(2022, 12, 28, 10, 17, 7),
        "summary": "行为人收集并出售手机号及对应验证码，用于批量注册网络平台账号并获利，检察机关同时提起附带民事公益诉讼。",
        "dispute_focus": "发送给特定手机号码的验证码是否属于公民个人信息；出售手机号与验证码是否构成侵犯公民个人信息犯罪。",
        "judgment_result": "相关行为人被判犯侵犯公民个人信息罪，并承担删除涉案个人信息、公开赔礼道歉等民事责任。",
        "judgment_reasoning": "验证码具有独特性和隐秘性，能够单独或结合手机号识别、验证特定自然人身份，属于受保护的个人信息；出售、提供并达到严重程度应承担刑事责任。",
        "ai_plain_language": "短信验证码不是普通数字，它相当于临时身份钥匙。不要向兼职中介、所谓拉新人员或陌生客服提供验证码；一旦泄露，应及时冻结账号、修改密码并保留证据。",
        "keywords": "验证码,手机号,个人信息,网络账号,拉新,信息安全",
        "source_external_id": "court-384441",
        "source_url": "https://www.court.gov.cn/shenpan/xiangqing/384441.html",
        "categories": ("student-daily", "social-hotspots", "daily-life", "cyber"),
        "tags": ("验证码", "个人信息", "账号安全"),
        "laws": (("中华人民共和国刑法", "第二百五十三条之一", "侵犯公民个人信息罪"),),
    },
)


CASE_LIBRARY_PATH = Path(__file__).resolve().parents[2] / "data" / "legal_cases_500.json"


def _load_bundled_cases():
    """Load the generated, reviewable case data without any runtime crawling."""
    payload = json.loads(CASE_LIBRARY_PATH.read_text(encoding="utf-8"))
    rows = payload.get("cases", [])
    if payload.get("schema_version") != 1 or len(rows) != 493:
        raise RuntimeError("bundled legal case library is missing or has an unexpected schema")
    normalized = []
    for raw in rows:
        item = dict(raw)
        if item.get("decision_date"):
            item["decision_date"] = date.fromisoformat(item["decision_date"])
        else:
            item["decision_date"] = None
        if item.get("published_at"):
            item["published_at"] = datetime.fromisoformat(item["published_at"])
        else:
            item["published_at"] = None
        item["categories"] = tuple(item.get("categories") or ())
        item["tags"] = tuple(item.get("tags") or ())
        item["laws"] = tuple(
            (law["law_name"], law.get("article", ""), law.get("note", ""))
            for law in item.get("laws") or ()
        )
        normalized.append(item)
    return tuple(normalized)


BUNDLED_CASES = _load_bundled_cases()

LEGACY_AGGREGATE_TAGS = {
    "大学生高频", "社会热点", "日常生活", "校园权益", "实习就业",
    "租房居住", "消费维权", "网络安全", "婚姻家庭", "金融借贷",
    "交通出行", "生命健康", "知识产权", "环境生态", "行政法治",
    "刑事风险", "民商事",
}


def _precise_definition(raw):
    """Replace the old broad/contaminated taxonomy with one precise domain."""
    definition = dict(raw)
    clean_keyword_parts = [
        value.strip() for value in str(definition.get("keywords", "")).split(",")
        if value.strip() and value.strip() not in LEGACY_AGGREGATE_TAGS
    ]
    case_type = str(definition.get("case_type", ""))
    fallback = "criminal" if "刑" in case_type else "public" if "行政" in case_type else "civil"
    category_slug, legal_domain = classify_case_content(
        title=definition.get("title", ""),
        cause=definition.get("cause", ""),
        keywords=clean_keyword_parts,
        dispute_focus=definition.get("dispute_focus", ""),
        case_type=case_type,
        fallback=fallback,
    )
    definition["legal_domain"] = legal_domain
    definition["categories"] = (category_slug,)
    definition["tags"] = tuple(
        tag for tag in definition.get("tags", ()) if tag not in LEGACY_AGGREGATE_TAGS
    )
    definition["keywords"] = ",".join(clean_keyword_parts)
    return definition


def seed_reference_data():
    for index, (slug, name, description, icon) in enumerate(COMMUNITY_CATEGORIES, 1):
        row = CommunityCategory.query.filter_by(slug=slug).first()
        if row is None:
            db.session.add(CommunityCategory(slug=slug, name=name, description=description, icon=icon, sort_order=index))
    active_case_slugs = {item[0] for item in CASE_CATEGORIES}
    CaseCategory.query.filter(~CaseCategory.slug.in_(active_case_slugs)).update(
        {CaseCategory.is_active: False}, synchronize_session=False
    )
    for index, (slug, name, description) in enumerate(CASE_CATEGORIES, 1):
        row = CaseCategory.query.filter_by(slug=slug).first()
        if row is None:
            db.session.add(CaseCategory(slug=slug, name=name, description=description, sort_order=index))
        else:
            row.name = name
            row.description = description
            row.sort_order = index
            row.is_active = True
    db.session.flush()

    for raw_definition in VERIFIED_CASES + RECENT_STUDENT_CASES + BUNDLED_CASES:
        definition = _precise_definition(raw_definition)
        row = LegalCase.query.filter_by(slug=definition["slug"]).first()
        public_fields = {key: value for key, value in definition.items() if key not in {"categories", "tags", "laws"}}
        digest_source = "|".join(str(public_fields.get(key, "")) for key in ("title", "case_number", "summary", "judgment_result", "source_url"))
        public_fields.setdefault("source_publisher", "中华人民共和国最高人民法院")
        public_fields.setdefault("source_type", "official_court")
        public_fields.setdefault("source_hash", hashlib.sha256(digest_source.encode("utf-8")).hexdigest())
        public_fields.update({
            "source_checked_at": None,
            "verification_status": "verified",
            "status": "published",
        })
        if row is None:
            row = LegalCase(**public_fields)
            db.session.add(row)
            db.session.flush()
            needs_index = True
        else:
            needs_index = row.legal_domain != public_fields["legal_domain"] or row.keywords != public_fields["keywords"]
            row.legal_domain = public_fields["legal_domain"]
            row.keywords = public_fields["keywords"]
            row.verification_status = "verified"
            row.status = "published"

        desired_categories = set(definition["categories"])
        existing_categories = {
            item.slug for item in CaseCategory.query.join(
                LegalCaseCategory, LegalCaseCategory.category_id == CaseCategory.id
            ).filter(LegalCaseCategory.case_id == row.id).all()
        }
        if existing_categories != desired_categories:
            LegalCaseCategory.query.filter_by(case_id=row.id).delete(synchronize_session=False)
            for category_slug in definition["categories"]:
                category = CaseCategory.query.filter_by(slug=category_slug).one()
                db.session.add(LegalCaseCategory(case_id=row.id, category_id=category.id))
            needs_index = True

        desired_tags = set(definition["tags"])
        existing_tags = {
            item.name for item in CaseTag.query.join(
                LegalCaseTag, LegalCaseTag.tag_id == CaseTag.id
            ).filter(LegalCaseTag.case_id == row.id).all()
        }
        if existing_tags != desired_tags:
            LegalCaseTag.query.filter_by(case_id=row.id).delete(synchronize_session=False)
            for tag_name in definition["tags"]:
                tag_slug = hashlib.sha1(tag_name.encode("utf-8")).hexdigest()[:20]
                tag = CaseTag.query.filter_by(name=tag_name).first()
                if tag is None:
                    tag = CaseTag(name=tag_name, slug=tag_slug)
                    db.session.add(tag)
                    db.session.flush()
                db.session.add(LegalCaseTag(case_id=row.id, tag_id=tag.id))

        if not CaseLawReference.query.filter_by(case_id=row.id).first():
            for law_name, article, note in definition["laws"]:
                db.session.add(CaseLawReference(case_id=row.id, law_name=law_name, article=article, note=note))
        if needs_index:
            enqueue_index("legal_case", row.id, {
                "title": row.title, "summary": row.summary, "dispute_focus": row.dispute_focus,
                "judgment_reasoning": row.judgment_reasoning, "keywords": row.keywords,
                "case_number": row.case_number, "legal_domain": row.legal_domain,
                "status": row.status, "verification_status": row.verification_status,
            })
    db.session.commit()
    process_outbox(limit=600)
