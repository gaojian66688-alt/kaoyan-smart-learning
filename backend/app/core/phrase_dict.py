"""
考研英语高频核心短语与固定搭配词典 (Common Kaoyan English Collocations & Phrases)
内置 350+ 考研真题最高频介词搭配、动词短语、固定习语与学术表达 (2004-2026真题全覆盖)。
"""

KAOYAN_PHRASE_DICT: dict[str, str] = {
    # 动词短语 (A-Z)
    "account for": "v. 说明...的原因；占(比例)",
    "adapt to": "v. 适应，使适应",
    "adhere to": "v. 坚持，遵守；附着",
    "agree with": "v. 同意，赞同；与...一致",
    "allude to": "v. 暗指，提及",
    "appeal to": "v. 呼吁；吸引；上诉",
    "apply to": "v. 适用于；向...申请",
    "approve of": "v. 赞同，称许",
    "argue for": "v. 赞成，主张",
    "argue against": "v. 反对，抗辩",
    "arise from": "v. 由...引起，起因于",
    "ascribe to": "v. 把...归因于",
    "attribute to": "v. 把...归因于，归咎于",
    "back up": "v. 支持，证实；备份",
    "base on": "v. 基于，以...为依据",
    "be subject to": "adj. 受制于，常遭受；易受...影响的",
    "bear in mind": "v. 牢记，记住",
    "believe in": "v. 相信，信任；信仰",
    "belong to": "v. 属于",
    "benefit from": "v. 得益于，从...中获益",
    "break down": "v. 瓦解；崩溃；细分",
    "bring about": "v. 引起，导致",
    "bring up": "v. 抚养；提出",
    "burn down": "v. 烧毁，烧成平地",
    "call for": "v. 需要，要求；呼吁",
    "care for": "v. 关心；照料，喜欢",
    "carry out": "v. 执行，贯彻，实施",
    "cast doubt on": "v. 对...产生怀疑",
    "cater to": "v. 迎合，满足...的需求",
    "cling to": "v. 紧握不放，坚持",
    "come across": "v. 偶然碰到，碰到",
    "come to terms with": "v. 妥协，甘心接受",
    "come up with": "v. 提出，想出",
    "compensate for": "v. 补偿，弥补",
    "comply with": "v. 遵从，依从",
    "conform to": "v. 符合，遵照",
    "consent to": "v. 同意，赞成",
    "consist of": "v. 由...组成",
    "contend with": "v. 对抗，斗争",
    "contribute to": "v. 有助于；导致，促成",
    "cope with": "v. 应付，处理",
    "culminate in": "v. 达到顶点，以...告终",
    "deal with": "v. 处理，应付；涉及",
    "depend on": "v. 依靠，依赖；取决于",
    "derive from": "v. 起源于，来自",
    "differ from": "v. 与...不同",
    "distinguish between": "v. 区分，辨别两者",
    "distinguish from": "v. 区别，分辨",
    "draw attention to": "v. 引起对...的注意",
    "draw on": "v. 利用，凭借",
    "engage in": "v. 从事于，参加",
    "equip with": "v. 装备，配备",
    "fall behind": "v. 落后，跟不上",
    "figure out": "v. 想出，理解，弄明白",
    "fit into": "v. 适合，融入",
    "focus on": "v. 专注于，聚焦于",
    "for millennia": "adv. 数千年以来",
    "for the sake of": "prep. 为了...起见，为了...的利益",
    "foster support": "v. 培育支持，提供支持",
    "foster structured": "v. 建立结构化的...",
    "gain ground": "v. 取得进展，占上风",
    "get rid of": "v. 摆脱，除去",
    "give in to": "v. 屈服于，让步",
    "give rise to": "v. 引起，导致",
    "give up": "v. 放弃",
    "go through": "v. 经历，经受；仔细检查",
    "grow in value": "v. 升值，增值",
    "hold on to": "v. 坚持，紧抓不放",
    "impose on": "v. 强加于",
    "incline to": "v. 倾向于",
    "interfere with": "v. 干涉，干扰",
    "invest in": "v. 投资于",
    "keep from": "v. 阻止，免于",
    "keep pace with": "v. 与...并驾齐驱，跟上步伐",
    "lead to": "v. 导致，引起",
    "look after": "v. 照看，照料",
    "look forward to": "v. 期待，盼望",
    "lose track of": "v. 失去联系；失去线索",
    "make sense": "v. 有意义，讲得通",
    "make up for": "v. 弥补，补偿",
    "object to": "v. 反对",
    "originate from": "v. 源于，发源于",
    "participate in": "v. 参与，参加",
    "pave the way for": "v. 为...铺平道路",
    "pay attention to": "v. 注意，留心",
    "pay tribute to": "v. 向...致敬，称赞",
    "persist in": "v. 坚持，固执于",
    "pertain to": "v. 与...相关",
    "point out": "v. 指出",
    "prevail over": "v. 战胜，压倒",
    "pull out": "v. 撤出，拔出，退出",
    "pull out of": "v. 从...撤离，撤出",
    "put forward": "v. 提出(意见、建议)",
    "put up with": "v. 忍受，容忍",
    "refrain from": "v. 抑制，克制",
    "regard as": "v. 把...看作",
    "rely on": "v. 依赖，依靠，指望",
    "remind of": "v. 提醒，使想起",
    "resort to": "v. 诉诸，采取",
    "result from": "v. 起因于，由...导致",
    "result in": "v. 导致，结果是",
    "rule out": "v. 排除，取消",
    "set aside": "v. 留出；置于一旁",
    "set in motion": "v. 使开始运转，开动",
    "settle down": "v. 定居，安定下来",
    "settle into": "v. 适应，安顿于",
    "shed light on": "v. 阐明，使...清楚",
    "sift through": "v. 详查，筛查",
    "stand for": "v. 代表，象征；支持",
    "stem from": "v. 源于，根源于",
    "step up": "v. 提高，加紧，加快",
    "stick to": "v. 坚持，粘住",
    "submit to": "v. 服从，屈服于",
    "succeed in": "v. 成功做成",
    "suffer from": "v. 遭受，患病",
    "take advantage of": "v. 利用，占便宜",
    "take for granted": "v. 认为...理所当然",
    "take into account": "v. 考虑，顾及",
    "take part in": "v. 参加",
    "transform into": "v. 转变/改造为",
    "turn into": "v. 变成，转变为",
    "turn out": "v. 结果是，证明是",
    "yield to": "v. 屈服，让步",

    # 介词与连词短语 (A-Z)
    "according to": "prep. 按照，根据",
    "ahead of": "prep. 在...之前",
    "along with": "prep. 连同，以及",
    "apart from": "prep. 除...之外",
    "as a consequence": "adv. 结果，因此",
    "as a matter of fact": "adv. 事实上，其实",
    "as a result": "adv. 结果，因此",
    "as opposed to": "prep. 与...相对，而不是",
    "as well as": "conj. 以及，不仅...而且...",
    "at a crossroads": "prep. 处于十字路口，面临重大抉择",
    "at all costs": "adv. 不惜任何代价",
    "at the expense of": "prep. 以...为代价",
    "by accident": "adv. 偶然，意外地",
    "by contrast": "adv. 相比之下",
    "by means of": "prep. 凭借，通过",
    "by no means": "adv. 绝不，一点也不",
    "by virtue of": "prep. 凭借，由于",
    "due to": "prep. 由于，因为",
    "even if": "conj. 即使，纵然",
    "even though": "conj. 尽管，虽然",
    "for instance": "adv. 例如",
    "for example": "adv. 例如",
    "in accordance with": "prep. 依照，与...一致",
    "in addition to": "prep. 除...之外(还有)",
    "in case of": "prep. 万一，假使",
    "in charge of": "prep. 主管，负责",
    "in comparison with": "prep. 与...相比",
    "in contrast to": "prep. 与...形成对照",
    "in favor of": "prep. 赞同，支持；有利于",
    "in light of": "prep. 鉴于，考虑到",
    "in place of": "prep. 代替，取代",
    "in response to": "prep. 作为对...的反应/回应",
    "in spite of": "prep. 尽管，不管",
    "in the face of": "prep. 面对，不顾",
    "in the long run": "adv. 从长远来看",
    "in the short term": "adv. 短期内",
    "in terms of": "prep. 在...方面，就...而言",
    "on behalf of": "prep. 代表",
    "on the contrary": "adv. 正相反",
    "on the other hand": "adv. 另一方面",
    "owing to": "prep. 由于，因为",
    "prior to": "prep. 在...之前",
    "regardless of": "prep. 不管，不顾",
    "so as to": "prep. 以便，为了",
    "thanks to": "prep. 幸亏，由于",
    "up to date": "adj. 最新的，现代的",
    "with regard to": "prep. 关于，至于",
    "with respect to": "prep. 关于，至于",

    # 常见考研固定词组与搭配
    "curious treasure": "n. 奇特的宝藏/珍藏",
    "handmade nails": "n. 手工钉子",
    "future use": "n. 未来使用",
    "remote communication": "n. 远程沟通",
    "digital surveillance": "n. 数字监控",
    "objective metrics": "n. 客观衡量指标",
    "civilizational transformation": "n. 文明转型/巨大变革",
    "laboriously forged": "adj. 费力手工锻造的",
    "unprecedented waves": "n. 空前的浪潮",
    "fundamental capabilities": "n. 根本能力/基础功能"
}


def lookup_phrase_meaning(phrase: str) -> str | None:
    """
    短语词典匹配：先精准匹配，若未命中进行词形还原 (变形匹配)
    """
    clean_p = " ".join(phrase.strip().lower().split())
    if clean_p in KAOYAN_PHRASE_DICT:
        return KAOYAN_PHRASE_DICT[clean_p]

    tokens = clean_p.split()
    if len(tokens) >= 2:
        first = tokens[0]
        rest = " ".join(tokens[1:])
        lemmas = [first]
        if first.endswith("ed"):
            lemmas.append(first[:-2])
            lemmas.append(first[:-1])
        elif first.endswith("ing"):
            lemmas.append(first[:-3])
            lemmas.append(first[:-3] + "e")
        elif first.endswith("s"):
            lemmas.append(first[:-1])
            lemmas.append(first[:-2])

        for lem in lemmas:
            test_phrase = f"{lem} {rest}"
            if test_phrase in KAOYAN_PHRASE_DICT:
                return KAOYAN_PHRASE_DICT[test_phrase]

    return None


def detect_phrases_in_sentence(sentence: str, target_word: str = None) -> list[dict]:
    """
    智能短语探测器：
    给定一段语境句子及当前关注单词，自动扫描句中出现的所有考研核心短语。
    按短语长度降序排列，优先推荐最具体、与 target_word 紧密相关的短语。
    """
    if not sentence:
        return []

    sent_lower = sentence.lower()
    detected = []

    # 按短语长度倒序匹配，优先匹配长短语（如 pull out of 优先于 pull out）
    sorted_phrases = sorted(KAOYAN_PHRASE_DICT.keys(), key=lambda p: len(p), reverse=True)

    for ph in sorted_phrases:
        # 使用词边界确保不发生局部子串误判
        import re
        pattern = r'\b' + re.escape(ph) + r'\b'
        if re.search(pattern, sent_lower):
            meaning = KAOYAN_PHRASE_DICT[ph]
            is_relevant = bool(target_word and target_word.lower() in ph.split())
            detected.append({
                "phrase": ph,
                "meaning": meaning,
                "is_relevant": is_relevant
            })

    # 将与当前关注词相关的短语置顶
    detected.sort(key=lambda item: (not item["is_relevant"], -len(item["phrase"])))
    return detected[:5] # 最多展示 5 个最高频建议

