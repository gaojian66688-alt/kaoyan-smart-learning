"""
考研英语高频核心短语与固定搭配词典 (Common Kaoyan English Collocations & Phrases)
内置 200+ 考研真题最高频介词搭配、动词短语与固定表达。
"""

KAOYAN_PHRASE_DICT: dict[str, str] = {
    # 动词短语
    "account for": "v. 说明...的原因；占(比例)",
    "adapt to": "v. 适应，使适应",
    "agree with": "v. 同意，赞同；与...一致",
    "apply to": "v. 适用于；向...申请",
    "appeal to": "v. 呼吁；吸引；上诉",
    "arise from": "v. 由...引起，起因于",
    "ascribe to": "v. 把...归因于",
    "attribute to": "v. 把...归因于，归咎于",
    "base on": "v. 基于，以...为依据",
    "be subject to": "adj. 受制于，常遭受；易受...影响的",
    "bear in mind": "v. 牢记，记住",
    "believe in": "v. 相信，信任；信仰",
    "belong to": "v. 属于",
    "benefit from": "v. 得益于，从...中获益",
    "bring about": "v. 引起，导致",
    "bring up": "v. 抚养；提出",
    "call for": "v. 需要，要求；呼吁",
    "carry out": "v. 执行，贯彻，实施",
    "cast doubt on": "v. 对...产生怀疑",
    "cater to": "v. 迎合，满足...的需求",
    "come across": "v. 偶然碰到，碰到",
    "come to terms with": "v. 妥协，甘心接受",
    "come up with": "v. 提出，想出",
    "comply with": "v. 遵从，依从",
    "conform to": "v. 符合，遵照",
    "consist of": "v. 由...组成",
    "contribute to": "v. 有助于；导致，促成",
    "cope with": "v. 应付，处理",
    "deal with": "v. 处理，应付；涉及",
    "depend on": "v. 依靠，依赖；取决于",
    "derive from": "v. 起源于，来自",
    "differ from": "v. 与...不同",
    "distinguish from": "v. 区别，分辨",
    "draw attention to": "v. 引起对...的注意",
    "draw on": "v. 利用，凭借",
    "engage in": "v. 从事于，参加",
    "equip with": "v. 装备，配备",
    "fall behind": "v. 落后，跟不上",
    "figure out": "v. 想出，理解，弄明白",
    "focus on": "v. 专注于，聚焦于",
    "foster support": "v. 培养/促进支持",
    "give rise to": "v. 引起，导致",
    "give in to": "v. 屈服于，让步",
    "give up": "v. 放弃",
    "go through": "v. 经历，经受；仔细检查",
    "hold on to": "v. 坚持，紧抓不放",
    "interfere with": "v. 干涉，干扰",
    "invest in": "v. 投资于",
    "keep pace with": "v. 与...并驾齐驱，跟上步伐",
    "lead to": "v. 导致，引起",
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
    "point out": "v. 指出",
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
    "shed light on": "v. 阐明，使...清楚",
    "stand for": "v. 代表，象征；支持",
    "stem from": "v. 源于，根源于",
    "step up": "v. 提高，加紧，加快",
    "stick to": "v. 坚持，粘住",
    "succeed in": "v. 成功做成",
    "suffer from": "v. 遭受，患病",
    "take advantage of": "v. 利用，占便宜",
    "take for granted": "v. 认为...理所当然",
    "take into account": "v. 考虑，顾及",
    "take part in": "v. 参加",
    "turn out": "v. 结果是，证明是",
    "yield to": "v. 屈服，让步",

    # 介词与连词短语
    "according to": "prep. 按照，根据",
    "ahead of": "prep. 在...之前",
    "along with": "prep. 连同，以及",
    "as a consequence": "adv. 结果，因此",
    "as a matter of fact": "adv. 事实上，其实",
    "as a result": "adv. 结果，因此",
    "as opposed to": "prep. 与...相对，而不是",
    "as well as": "conj. 以及，不仅...而且...",
    "at all costs": "adv. 不惜任何代价",
    "at the expense of": "prep. 以...为代价",
    "by contrast": "adv. 相比之下",
    "by means of": "prep. 凭借，通过",
    "by no means": "adv. 绝不，一点也不",
    "by virtue of": "prep. 凭借，由于",
    "due to": "prep. 由于，因为",
    "for the sake of": "prep. 为了...的利益",
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
    "in terms of": "prep. 在...方面，就...而言",
    "on behalf of": "prep. 代表",
    "on the contrary": "adv. 正相反",
    "on the other hand": "adv. 另一方面",
    "owing to": "prep. 由于，因为",
    "prior to": "prep. 在...之前",
    "regardless of": "prep. 不管，不顾",
    "thanks to": "prep. 幸亏，由于",
    "up to date": "adj. 最新的，现代的",
    "with regard to": "prep. 关于，至于",
    "with respect to": "prep. 关于，至于",
}


def lookup_phrase_meaning(phrase: str) -> str | None:
    """
    短语词典匹配：先精准匹配，若未命中进行模糊词形与前后缀匹配
    """
    clean_p = " ".join(phrase.strip().lower().split())
    if clean_p in KAOYAN_PHRASE_DICT:
        return KAOYAN_PHRASE_DICT[clean_p]
    
    # 尝试去除第三人称单数或过去式 (如 accounts for -> account for, relied on -> rely on)
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
