"""Deterministic redaction of common Chinese personally identifiable data.

The module deliberately has no process-global redaction state.  A
``RedactionSession`` may be shared across several strings (or a nested JSON
value) when identical values must receive the same placeholder.  Its public
summary contains counts only; the original values are never included.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable


_KIND_LABELS = {
    "phone": "手机号",
    "email": "邮箱",
    "id_card": "身份证",
    "bank_card": "银行卡",
    "passport": "护照",
    "uscc": "统一社会信用代码",
    "name": "姓名",
    "address": "地址",
}

_ID_CARD_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CARD_CHECK_CODES = "10X98765432"

_USCC_ALPHABET = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
_USCC_VALUES = {character: index for index, character in enumerate(_USCC_ALPHABET)}

_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9.!#$%&'*+/=?^_`{|}~-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}(?![A-Za-z0-9-])"
)
_ID_CARD_RE = re.compile(r"(?<![0-9A-Za-z])\d{17}[0-9Xx](?![0-9A-Za-z])")
_LABELED_ID_CARD_RE = re.compile(
    r"(?:居民身份证(?:号码|号)?|公民身份号码|身份证(?:号码|号)?)"
    r"\s*(?:为|是)?\s*[:：]?\s*"
    r"(?P<value>\d{17}[0-9Xx])(?![0-9A-Za-z])"
)
_USCC_RE = re.compile(
    r"(?<![0-9A-Za-z])"
    r"[0-9ABCDEFGHJKLMNPQRTUWXY]{18}"
    r"(?![0-9A-Za-z])",
    re.IGNORECASE,
)
_BANK_CARD_RE = re.compile(r"(?<!\d)\d(?:[ -]?\d){15,18}(?!\d)")
_LABELED_BANK_CARD_RE = re.compile(
    r"(?:银行卡(?:号码|号)?|银行(?:账户|账号)|卡号)"
    r"\s*(?:为|是)?\s*[:：]?\s*"
    r"(?P<value>\d(?:[ -]?\d){15,18})(?!\d)"
)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[ -]?)?1[3-9]\d(?:[ -]?\d){8}(?!\d)")
_LABELED_PHONE_RE = re.compile(
    r"(?:联系电话号码|联系电话|联系号码|联系方式|手机号码|手机号|手机|"
    r"电话号码|电话|座机号码|座机)"
    r"\s*(?:为|是)?\s*[:：]?\s*"
    r"(?P<value>[+（(]?\d[\d（）() \-]{5,24}\d)"
)
_PASSPORT_RE = re.compile(
    r"(?<![0-9A-Za-z])(?:[EGDSP]\d{8}|(?:PE|DE|SE)\d{7})(?![0-9A-Za-z])",
    re.IGNORECASE,
)
_LABELED_PASSPORT_RE = re.compile(
    r"(?:护照号码|护照号|护照)\s*[:：]\s*"
    r"(?P<value>[A-Z]{1,2}\d{7,8})(?![0-9A-Z])",
    re.IGNORECASE,
)

_NAME_RE = re.compile(
    r"(?:当事人姓名|联系人姓名|收件人姓名|姓名|联系人|当事人|原告|被告|"
    r"申请人|被申请人|委托人|受托人|收件人)\s*(?:为|是)?\s*[:：]\s*"
    r"(?P<value>[\u3400-\u9fff·•]{2,20})"
    r"(?=$|[\s,，;；。.!！？|/()（）]|(?:身份证|手机|电话|邮箱|住址|住所|地址)\s*[:：])"
)
_ADDRESS_RE = re.compile(
    r"(?:联系地址|户籍地址|送达地址|通讯地址|家庭地址|地址|住址|住所)"
    r"\s*[:：]\s*"
    r"(?P<value>[^\r\n,，;；。.!！？]{5,120}?)"
    r"(?=$|[\r\n,，;；。.!！？]|\s*(?:联系电话|手机|电话|邮箱|身份证|姓名)\s*[:：])"
)
_STRUCTURED_INFO_ADDRESS_RE = re.compile(
    r"(?:联系地址|户籍地址|送达地址|通讯地址|家庭地址|住所地?|住址|地址|住)"
    r"\s*(?:为|是)?\s*[:：]?\s*"
    r"(?P<value>[^\r\n,，;；。.!！？]{5,120}?)"
    r"(?=$|[\r\n,，;；。.!！？]|\s*(?:联系电话|联系方式|手机|电话|邮箱|"
    r"身份证|护照|银行卡|姓名)\s*[:：])"
)

_ORGANISATION_MARKERS = (
    "公司",
    "大学",
    "学院",
    "学校",
    "法院",
    "检察院",
    "委员会",
    "事务所",
    "中心",
    "银行",
    "政府",
    "机关",
    "集团",
)
_ADDRESS_MARKERS = "省市区县旗乡镇街道路巷村号室栋幢楼园"

_NAME_FIELD_NAMES = {
    "姓名",
    "当事人姓名",
    "联系人姓名",
    "联系人",
    "收件人姓名",
    "原告姓名",
    "被告姓名",
    "申请人姓名",
    "被申请人姓名",
    "委托人姓名",
}
_ADDRESS_FIELD_NAMES = {
    "地址",
    "住址",
    "住所",
    "联系地址",
    "户籍地址",
    "送达地址",
    "通讯地址",
    "家庭地址",
}

# These are the actual structured keys used by the document-generation
# endpoints.  A role key is treated as a name only when its value really
# resembles a natural person's name, so an organisation used as a plaintiff
# or applicant remains intact.
_ROLE_NAME_FIELDS = {
    "name",
    "full_name",
    "person_name",
    "plaintiff",
    "defendant",
    "appellant",
    "appellee",
    "respondent",
    "applicant",
    "obligor",
    "principal",
    "agent",
    "suer",
    "counter_plaintiff",
    "counter_defendant",
    "objector",
    "legal_agent",
    "lawyer_agent",
    "citizen_agent",
    "representative",
    "legal_representative",
    "applicant_person",
    "person_agent_1",
    "person_agent_2",
    "org_agent_1",
    "org_agent_2",
    "agent_names",
    "agent_1_name",
    "agent_2_name",
}
_PERSON_INFO_ROOTS = {
    "plaintiff",
    "defendant",
    "appellant",
    "appellee",
    "respondent",
    "applicant",
    "obligor",
    "principal",
    "agent",
    "suer",
    "counter_plaintiff",
    "counter_defendant",
    "objector",
    "applicant_person",
    "applicant_org",
}
_PHONE_FIELD_NAMES = {
    "contact",
    "contact_number",
    "phone",
    "phone_number",
    "mobile",
    "mobile_number",
    "telephone",
    "tel",
}
_ID_CARD_FIELD_NAMES = {
    "id_card",
    "id_card_number",
    "idcard",
    "identity_card",
    "identity_card_number",
    "identity_number",
    "citizen_id",
    "national_id",
}
_PASSPORT_FIELD_NAMES = {"passport", "passport_number", "passport_no"}
_BANK_CARD_FIELD_NAMES = {
    "bank_card",
    "bank_card_number",
    "bank_account",
    "bank_account_number",
    "card_number",
}
_USCC_FIELD_NAMES = {"uscc", "unified_social_credit_code", "credit_code"}
_NON_PII_FIELD_NAMES = {
    "amount",
    "price",
    "fee",
    "total",
    "balance",
    "compensation",
    "claim_amount",
    "case_amount",
    "date",
    "time",
    "article",
    "article_number",
    "provision_number",
    "law_article",
    "case_number",
    "document_number",
    "instrument_number",
}
_NON_PII_CHINESE_FIELDS = {
    "金额",
    "价款",
    "费用",
    "合计",
    "余额",
    "标的额",
    "赔偿额",
    "日期",
    "时间",
    "法条号",
    "条文号",
    "案号",
    "文号",
}
_EMPTY_OR_TEMPLATE_VALUES = {
    "",
    "无",
    "暂无",
    "未知",
    "不详",
    "未填写",
    "未提供",
    "……",
    "...",
    "×××",
    "xxx",
    "none",
    "null",
}
_ROLE_ONLY_VALUES = {
    "原告",
    "被告",
    "上诉人",
    "被上诉人",
    "申请人",
    "被申请人",
    "答辩人",
    "委托人",
    "代理人",
    "法定代理人",
    "委托诉讼代理人",
}


@dataclass(frozen=True)
class PIIMatch:
    """A validated PII span returned by :func:`detect_pii`."""

    kind: str
    start: int
    end: int
    value: str


@dataclass(frozen=True)
class RedactedEntity:
    """Safe metadata about one unique redacted value.

    ``placeholder`` is safe to display.  The original value is intentionally
    absent from this public object.
    """

    kind: str
    placeholder: str
    occurrences: int


def _compact_digits(value: str) -> str:
    return re.sub(r"[ -]", "", value)


def is_valid_id_card(value: str) -> bool:
    """Validate an 18-character PRC resident identity card number.

    Besides the official MOD 11-2 check character, the embedded birth date is
    checked so a checksum-compatible arbitrary 18-digit number is not treated
    as an identity card.
    """

    candidate = value.strip().upper()
    if not re.fullmatch(r"\d{17}[0-9X]", candidate):
        return False
    if candidate[:6] == "000000":
        return False

    birth_date = candidate[6:14]
    try:
        year = int(birth_date[:4])
        month = int(birth_date[4:6])
        day = int(birth_date[6:8])
        # Importing datetime is unnecessary here; this rejects impossible
        # dates, including non-leap-year February 29, deterministically.
        import datetime as _datetime

        _datetime.date(year, month, day)
    except (TypeError, ValueError):
        return False

    checksum_index = sum(
        int(number) * weight for number, weight in zip(candidate[:17], _ID_CARD_WEIGHTS)
    ) % 11
    return candidate[-1] == _ID_CARD_CHECK_CODES[checksum_index]


def is_valid_bank_card(value: str) -> bool:
    """Validate a 16--19 digit payment card number with the Luhn algorithm."""

    digits = _compact_digits(value)
    if not re.fullmatch(r"\d{16,19}", digits):
        return False
    if len(set(digits)) == 1 or digits[0] == "0":
        return False

    total = 0
    parity = len(digits) % 2
    for index, character in enumerate(digits):
        number = int(character)
        if index % 2 == parity:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _looks_like_id_card_body(value: str) -> bool:
    """Return whether an 18-digit value has the structure of an ID card.

    This is used only to stop an ID card with a mistyped check character from
    being reclassified as a Luhn-valid bank card.
    """

    candidate = _compact_digits(value)
    if not re.fullmatch(r"\d{18}", candidate) or candidate[:6] == "000000":
        return False
    try:
        import datetime as _datetime

        _datetime.date(
            int(candidate[6:10]),
            int(candidate[10:12]),
            int(candidate[12:14]),
        )
    except ValueError:
        return False
    return True


def is_valid_uscc(value: str) -> bool:
    """Validate an 18-character Unified Social Credit Identifier."""

    candidate = value.strip().upper()
    if len(candidate) != 18 or any(character not in _USCC_VALUES for character in candidate):
        return False
    if len(set(candidate)) == 1:
        return False

    weighted_sum = sum(
        _USCC_VALUES[character] * weight
        for character, weight in zip(candidate[:17], _USCC_WEIGHTS)
    )
    check_value = (31 - weighted_sum % 31) % 31
    return candidate[-1] == _USCC_ALPHABET[check_value]


def _looks_like_non_pii_number(text: str, start: int, end: int) -> bool:
    """Reject valid-looking numeric sequences in obvious legal/amount context."""

    before = text[max(0, start - 20) : start]
    after = text[end : min(len(text), end + 12)]
    if re.search(r"(?:金额|价款|费用|合计|余额|标的额|赔偿额|人民币|¥|￥)\s*[:：]?\s*$", before):
        return True
    if re.match(r"\s*(?:[.．]\d{1,2})?\s*(?:元|万元|亿元|人民币|¥|￥)(?:\b|整|$)", after):
        return True
    if re.search(r"第\s*$", before) and re.match(r"\s*(?:条|款|项|章|节|编)", after):
        return True
    if re.search(r"(?:法条号|条文号|案号|文号|日期|时间)\s*[:：]?\s*$", before):
        return True
    return False


def _normalise_field_name(field_name: str) -> tuple[str, str]:
    """Return snake-case and compact forms for English/Chinese JSON keys."""

    snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", field_name.strip())
    snake = re.sub(r"(?<=[A-Za-z])(?=\d)", "_", snake)
    snake = re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "_", snake).strip("_").lower()
    compact = re.sub(r"[\s_\-]", "", field_name.strip()).lower()
    return snake, compact


def _is_empty_or_template_value(value: str) -> bool:
    return value.strip().lower() in _EMPTY_OR_TEMPLATE_VALUES


def _is_person_name(value: str) -> bool:
    compact = value.strip()
    if _is_empty_or_template_value(compact) or compact in _ROLE_ONLY_VALUES:
        return False
    if any(marker in compact for marker in _ORGANISATION_MARKERS):
        return False

    if re.fullmatch(r"[\u3400-\u9fff·•]{2,20}", compact):
        plain_length = len(compact.replace("·", "").replace("•", ""))
        return 2 <= plain_length <= 15

    # English personal names are accepted only in an explicitly named JSON
    # field.  Requiring alphabetic tokens prevents numeric placeholders and
    # document identifiers from being treated as names.
    if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,79}", compact):
        return len(re.findall(r"[A-Za-z]", compact)) >= 2
    return False


def _is_address(value: str) -> bool:
    compact = value.strip()
    if _is_empty_or_template_value(compact) or not 5 <= len(compact) <= 120:
        return False
    return any(marker in compact for marker in _ADDRESS_MARKERS)


def _looks_like_phone_value(value: str) -> bool:
    compact = value.strip()
    if _is_empty_or_template_value(compact):
        return False
    if not re.fullmatch(r"[+（()）\d\s-]+", compact):
        return False
    digit_count = len(re.sub(r"\D", "", compact))
    return 7 <= digit_count <= 15


def _looks_like_explicit_id_card(value: str) -> bool:
    compact = re.sub(r"[\s-]", "", value.strip()).upper()
    return bool(re.fullmatch(r"(?:\d{15}|\d{17}[0-9X])", compact))


def _looks_like_explicit_bank_card(value: str) -> bool:
    compact = _compact_digits(value.strip())
    return bool(re.fullmatch(r"\d{12,19}", compact)) and len(set(compact)) > 1


def _looks_like_explicit_passport(value: str) -> bool:
    compact = re.sub(r"[\s-]", "", value.strip()).upper()
    return (
        bool(re.fullmatch(r"[A-Z0-9]{5,20}", compact))
        and any(character.isdigit() for character in compact)
        and not _is_empty_or_template_value(value)
    )


def _looks_like_explicit_uscc(value: str) -> bool:
    compact = value.strip().upper()
    return bool(re.fullmatch(r"[0-9ABCDEFGHJKLMNPQRTUWXY]{18}", compact))


def _labeled_phone_candidate(value: str) -> bool:
    """Use label context to accept mobile or landline-like digit strings."""

    return _looks_like_phone_value(value)


def _candidate_matches(text: str) -> Iterable[tuple[int, PIIMatch]]:
    """Yield ``(priority, match)`` pairs before overlap resolution."""

    # An explicit semantic label is a stronger privacy signal than a checksum.
    # This deliberately masks mistyped document/card numbers rather than
    # leaking them, while the unlabeled patterns below remain strict.
    for match in _LABELED_ID_CARD_RE.finditer(text):
        start, end = match.span("value")
        yield 110, PIIMatch("id_card", start, end, match.group("value"))

    for match in _ID_CARD_RE.finditer(text):
        if is_valid_id_card(match.group()):
            yield 100, PIIMatch("id_card", match.start(), match.end(), match.group())

    for match in _LABELED_BANK_CARD_RE.finditer(text):
        start, end = match.span("value")
        yield 98, PIIMatch("bank_card", start, end, match.group("value"))

    for match in _USCC_RE.finditer(text):
        if is_valid_uscc(match.group()):
            yield 95, PIIMatch("uscc", match.start(), match.end(), match.group())

    for match in _EMAIL_RE.finditer(text):
        yield 90, PIIMatch("email", match.start(), match.end(), match.group())

    for match in _LABELED_PHONE_RE.finditer(text):
        value = match.group("value")
        if _labeled_phone_candidate(value):
            start, end = match.span("value")
            yield 88, PIIMatch("phone", start, end, value)

    for match in _BANK_CARD_RE.finditer(text):
        if (
            is_valid_bank_card(match.group())
            and not _looks_like_id_card_body(match.group())
            and not _looks_like_non_pii_number(text, match.start(), match.end())
        ):
            yield 85, PIIMatch("bank_card", match.start(), match.end(), match.group())

    for match in _PHONE_RE.finditer(text):
        if not _looks_like_non_pii_number(text, match.start(), match.end()):
            yield 80, PIIMatch("phone", match.start(), match.end(), match.group())

    for match in _LABELED_PASSPORT_RE.finditer(text):
        start, end = match.span("value")
        yield 76, PIIMatch("passport", start, end, match.group("value"))

    for match in _PASSPORT_RE.finditer(text):
        before = text[max(0, match.start() - 12) : match.start()]
        if not re.search(r"(?:日期|时间)\s*[:：]?\s*$", before):
            yield 75, PIIMatch("passport", match.start(), match.end(), match.group())

    for match in _ADDRESS_RE.finditer(text):
        start, end = match.span("value")
        value = match.group("value").strip()
        start += len(match.group("value")) - len(match.group("value").lstrip())
        end -= len(match.group("value")) - len(match.group("value").rstrip())
        if _is_address(value):
            yield 70, PIIMatch("address", start, end, value)

    for match in _NAME_RE.finditer(text):
        start, end = match.span("value")
        value = match.group("value")
        if _is_person_name(value):
            yield 65, PIIMatch("name", start, end, value)


def detect_pii(text: str) -> list[PIIMatch]:
    """Return validated, non-overlapping PII spans in textual order."""

    if not isinstance(text, str) or not text:
        return []

    candidates = list(_candidate_matches(text))
    # Select higher-confidence/longer candidates first.  This prevents the
    # phone-number pattern from claiming a substring of a validated card.
    candidates.sort(key=lambda item: (-item[0], -(item[1].end - item[1].start), item[1].start))
    selected: list[PIIMatch] = []
    for _priority, candidate in candidates:
        if any(candidate.start < current.end and current.start < candidate.end for current in selected):
            continue
        selected.append(candidate)
    return sorted(selected, key=lambda item: (item.start, item.end))


def _normalise_value(kind: str, value: str) -> str:
    if kind == "phone":
        compact = re.sub(r"\D", "", value)
        if compact.startswith("86") and len(compact) > 11:
            compact = compact[2:]
        return compact
    if kind == "bank_card":
        return re.sub(r"\D", "", value)
    if kind == "id_card":
        return re.sub(r"[\s-]", "", value.strip()).upper()
    if kind in {"email", "passport", "uscc"}:
        compact = value.strip()
        return compact.lower() if kind == "email" else compact.upper()
    return re.sub(r"\s+", "", value.strip())


def _is_person_info_field(field_name: str) -> bool:
    if not field_name.endswith("_info"):
        return False
    return field_name[: -len("_info")] in _PERSON_INFO_ROOTS


def _is_non_pii_field(field_name: str, compact_field: str) -> bool:
    if field_name in _NON_PII_FIELD_NAMES or compact_field in _NON_PII_CHINESE_FIELDS:
        return True
    return field_name.endswith(
        (
            "_amount",
            "_price",
            "_fee",
            "_balance",
            "_date",
            "_time",
            "_article_number",
            "_case_number",
            "_document_number",
            "_instrument_number",
        )
    )


def _is_name_field(field_name: str, compact_field: str) -> bool:
    return (
        compact_field in _NAME_FIELD_NAMES
        or field_name in _ROLE_NAME_FIELDS
        or field_name.endswith("_name")
        or field_name.endswith("_names")
    )


def _is_address_field(field_name: str, compact_field: str) -> bool:
    return compact_field in _ADDRESS_FIELD_NAMES or field_name.endswith("_address")


def _is_phone_field(field_name: str) -> bool:
    return field_name in _PHONE_FIELD_NAMES or field_name.endswith(
        ("_contact", "_phone", "_mobile", "_telephone")
    )


def _is_id_card_field(field_name: str) -> bool:
    return field_name in _ID_CARD_FIELD_NAMES or field_name.endswith("_id_card")


def _is_passport_field(field_name: str) -> bool:
    return field_name in _PASSPORT_FIELD_NAMES or field_name.endswith("_passport")


def _is_bank_card_field(field_name: str) -> bool:
    return field_name in _BANK_CARD_FIELD_NAMES or field_name.endswith("_bank_card")


def _is_uscc_field(field_name: str) -> bool:
    return field_name in _USCC_FIELD_NAMES or field_name.endswith("_uscc")


class RedactionSession:
    """State container that gives repeated PII stable placeholders."""

    def __init__(self) -> None:
        self._placeholder_by_value: dict[tuple[str, str], str] = {}
        self._occurrences_by_value: Counter[tuple[str, str]] = Counter()
        self._counts: Counter[str] = Counter()

    def _replace_value(self, kind: str, value: str) -> str:
        normalised = _normalise_value(kind, value)
        key = (kind, normalised)
        placeholder = self._placeholder_by_value.get(key)
        if placeholder is None:
            sequence = 1 + sum(1 for existing_kind, _ in self._placeholder_by_value if existing_kind == kind)
            placeholder = f"[{_KIND_LABELS[kind]}_{sequence}]"
            self._placeholder_by_value[key] = placeholder
        self._occurrences_by_value[key] += 1
        self._counts[kind] += 1
        return placeholder

    def _redact_matches(self, text: str, matches: Iterable[PIIMatch]) -> str:
        ordered = sorted(matches, key=lambda match: (match.start, match.end))
        if not ordered:
            return text

        parts: list[str] = []
        cursor = 0
        for match in ordered:
            if match.start < cursor:
                continue
            parts.append(text[cursor : match.start])
            parts.append(self._replace_value(match.kind, match.value))
            cursor = match.end
        parts.append(text[cursor:])
        return "".join(parts)

    def _replace_whole_value(self, kind: str, value: str) -> str:
        leading_length = len(value) - len(value.lstrip())
        trailing_length = len(value) - len(value.rstrip())
        leading = value[:leading_length]
        trailing = value[len(value) - trailing_length :] if trailing_length else ""
        return leading + self._replace_value(kind, value.strip()) + trailing

    def _redact_name_field(self, value: str) -> str:
        if _is_person_name(value):
            return self._replace_whole_value("name", value)

        stripped = value.strip()
        pieces = re.split(r"([、/,，;；]\s*)", stripped)
        possible_names = pieces[0::2]
        if len(possible_names) >= 2 and all(_is_person_name(item) for item in possible_names):
            redacted_pieces = [
                self._replace_value("name", item.strip()) if index % 2 == 0 else item
                for index, item in enumerate(pieces)
            ]
            leading = value[: len(value) - len(value.lstrip())]
            trailing_length = len(value) - len(value.rstrip())
            trailing = value[len(value) - trailing_length :] if trailing_length else ""
            return leading + "".join(redacted_pieces) + trailing

        # Role fields sometimes contain "张三，某律师事务所律师，电话……".
        # Redact only the leading name, then let ordinary detectors handle the
        # remaining contact details instead of hiding the whole descriptive
        # string.
        leading_match = re.match(
            r"(?P<space>\s*)(?P<name>[^、/,，;；]{2,80})(?P<separator>\s*[,，;；])",
            value,
        )
        if leading_match and _is_person_name(leading_match.group("name")):
            start, end = leading_match.span("name")
            value = (
                value[:start]
                + self._replace_value("name", leading_match.group("name"))
                + value[end:]
            )
        return self._redact_structured_info(value)

    def _redact_structured_info(self, value: str) -> str:
        leading_match = re.match(
            r"(?P<space>\s*)(?P<name>[^、/,，;；]{2,80})(?P<separator>\s*[,，;；])",
            value,
        )
        if leading_match and _is_person_name(leading_match.group("name")):
            start, end = leading_match.span("name")
            value = (
                value[:start]
                + self._replace_value("name", leading_match.group("name"))
                + value[end:]
            )

        address_matches: list[PIIMatch] = []
        for match in _STRUCTURED_INFO_ADDRESS_RE.finditer(value):
            raw_value = match.group("value")
            address = raw_value.strip()
            if not _is_address(address):
                continue
            start, end = match.span("value")
            start += len(raw_value) - len(raw_value.lstrip())
            end -= len(raw_value) - len(raw_value.rstrip())
            address_matches.append(PIIMatch("address", start, end, address))
        return self.redact(self._redact_matches(value, address_matches))

    def redact(self, text: str) -> str:
        """Redact one string, retaining non-PII text byte-for-byte."""

        if not isinstance(text, str) or not text:
            return text
        matches = detect_pii(text)
        if not matches:
            return text

        return self._redact_matches(text, matches)

    def redact_labeled_value(self, field_name: str, value: str) -> str:
        """Redact a JSON string whose field name explicitly identifies PII."""

        normalised_field, compact_field = _normalise_field_name(field_name)

        # Numeric values in explicit legal/document fields must not become PII
        # merely because their digits happen to satisfy a checksum.
        if _is_non_pii_field(normalised_field, compact_field):
            return value

        if _is_name_field(normalised_field, compact_field):
            return self._redact_name_field(value)
        if _is_address_field(normalised_field, compact_field) and _is_address(value):
            return self._replace_whole_value("address", value)

        if _is_id_card_field(normalised_field) and _looks_like_explicit_id_card(value):
            return self._replace_whole_value("id_card", value)
        if _is_passport_field(normalised_field) and _looks_like_explicit_passport(value):
            return self._replace_whole_value("passport", value)
        if _is_bank_card_field(normalised_field) and _looks_like_explicit_bank_card(value):
            return self._replace_whole_value("bank_card", value)
        if _is_uscc_field(normalised_field) and _looks_like_explicit_uscc(value):
            return self._replace_whole_value("uscc", value)
        if _is_phone_field(normalised_field) and _looks_like_phone_value(value):
            return self._replace_whole_value("phone", value)

        if _is_person_info_field(normalised_field):
            return self._redact_structured_info(value)
        return self.redact(value)

    @property
    def has_pii(self) -> bool:
        return bool(self._counts)

    @property
    def counts(self) -> dict[str, int]:
        """Occurrence counts by machine-readable category."""

        return {
            kind: self._counts[kind]
            for kind in _KIND_LABELS
            if self._counts.get(kind, 0)
        }

    @property
    def entities(self) -> tuple[RedactedEntity, ...]:
        """Safe unique-entity metadata, in placeholder creation order."""

        return tuple(
            RedactedEntity(
                kind=kind,
                placeholder=placeholder,
                occurrences=self._occurrences_by_value[(kind, normalised)],
            )
            for (kind, normalised), placeholder in self._placeholder_by_value.items()
        )

    def public_summary(self) -> dict[str, Any]:
        """Return display-safe aggregate data with no original PII values."""

        counts = self.counts
        return {
            "enabled": True,
            "has_pii": self.has_pii,
            "masked_count": sum(counts.values()),
            "unique_masked_count": len(self._placeholder_by_value),
            "categories": list(counts),
            "counts": counts,
        }


def redact_text(text: str, session: RedactionSession | None = None) -> str:
    """Redact one text value and return a string.

    Supply a session when placeholders must remain stable across multiple
    calls.  Without one, a fresh deterministic session is used.
    """

    active_session = session if session is not None else RedactionSession()
    return active_session.redact(text)


def redact_nested_json(value: Any, session: RedactionSession | None = None) -> Any:
    """Return a recursively redacted copy of a JSON-compatible value.

    String dictionary keys are redacted too, preventing an email address or
    similar identifier used as a key from bypassing the privacy boundary.
    """

    active_session = session if session is not None else RedactionSession()

    def walk(item: Any, field_name: str | None = None) -> Any:
        if isinstance(item, str):
            if field_name:
                return active_session.redact_labeled_value(field_name, item)
            return active_session.redact(item)
        if isinstance(item, dict):
            redacted: dict[Any, Any] = {}
            for key, child in item.items():
                safe_key = active_session.redact(key) if isinstance(key, str) else key
                context = key if isinstance(key, str) else None
                redacted[safe_key] = walk(child, context)
            return redacted
        if isinstance(item, list):
            return [walk(child, field_name) for child in item]
        if isinstance(item, tuple):
            return tuple(walk(child, field_name) for child in item)
        return item

    return walk(value)


def public_redaction_summary(session: RedactionSession) -> dict[str, Any]:
    """Return a non-sensitive summary for API/UI responses."""

    if not isinstance(session, RedactionSession):
        raise TypeError("session must be a RedactionSession")
    return session.public_summary()


__all__ = [
    "PIIMatch",
    "RedactedEntity",
    "RedactionSession",
    "detect_pii",
    "is_valid_bank_card",
    "is_valid_id_card",
    "is_valid_uscc",
    "public_redaction_summary",
    "redact_nested_json",
    "redact_text",
]
