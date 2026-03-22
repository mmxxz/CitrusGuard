"""
柑橘病虫害环境风险模糊推理引擎 (Mamdani)
==========================================
纯规则推理模块，不含神经网络。
输入：环境条件（温度/湿度/降雨/物候，支持数值或定性描述）
输出：每种病虫害的风险评分(0-100) + 触发规则 + 关键因子解释

设计定位：作为 LangGraph Agent 的环境风险顾问 Tool/Node
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import json


# ============================================================
# 1. 基础数据结构
# ============================================================

@dataclass
class FuzzySet:
    """梯形隶属函数定义的模糊集"""
    name: str
    params: List[float]  # 梯形参数 [a, b, c, d]

    def membership(self, x: float) -> float:
        """计算隶属度"""
        a, b, c, d = self.params
        if x <= a or x >= d:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a + 1e-10)
        elif b < x <= c:
            return 1.0
        elif c < x < d:
            return (d - x) / (d - c + 1e-10)
        return 0.0


@dataclass
class LinguisticVariable:
    """模糊语言变量"""
    name: str
    display_name: str
    universe: Tuple[float, float]
    fuzzy_sets: Dict[str, FuzzySet] = field(default_factory=dict)

    def fuzzify(self, x: float) -> Dict[str, float]:
        """将精确值模糊化为各模糊集的隶属度"""
        x = np.clip(x, self.universe[0], self.universe[1])
        return {name: fs.membership(x) for name, fs in self.fuzzy_sets.items()}


@dataclass
class FuzzyRule:
    """一条模糊规则"""
    rule_id: str
    disease: str
    conditions: Dict[str, str]   # {变量名: 模糊集名}
    consequence: str             # "低风险" / "中风险" / "高风险"
    weight: float = 1.0
    description: str = ""

    def to_text(self) -> str:
        """生成可读规则文本"""
        conds = " 且 ".join(f"{k}={v}" for k, v in self.conditions.items())
        return f"如果 ({conds}) 则 ({self.disease} {self.consequence})"


# ============================================================
# 2. 核心模糊推理引擎
# ============================================================

class CitrusFuzzyEngine:
    """
    柑橘病虫害环境风险 Mamdani 模糊推理引擎

    支持两种输入模式：
    1. 数值输入: predict({"temp": 28, "humidity": 85, ...})
    2. 定性输入: predict_qualitative({"temp": "偏高", "rainfall": "偏多", ...})
    """

    # 目标病虫害列表
    DISEASES = ["炭疽病", "疮痂病", "溃疡病", "脂点黄斑病", "木虱", "潜叶蛾", "锈壁虱", "红蜘蛛"]

    # 风险等级输出的代表值（用于质心解模糊）
    RISK_CENTROIDS = {"低风险": 15.0, "中风险": 50.0, "高风险": 85.0}

    def __init__(self):
        self.variables: Dict[str, LinguisticVariable] = self._define_variables()
        self.rules: List[FuzzyRule] = self._define_rules()
        self._rules_by_disease: Dict[str, List[FuzzyRule]] = {}
        for r in self.rules:
            self._rules_by_disease.setdefault(r.disease, []).append(r)

    # ----------------------------------------------------------
    # 2.1 定义输入变量及隶属函数
    # ----------------------------------------------------------
    def _define_variables(self) -> Dict[str, LinguisticVariable]:
        variables = {}

        # 温度
        temp = LinguisticVariable("temp", "温度", (0, 45))
        temp.fuzzy_sets = {
            "偏低": FuzzySet("偏低", [0, 0, 12, 18]),
            "适宜": FuzzySet("适宜", [15, 20, 28, 32]),
            "偏高": FuzzySet("偏高", [28, 32, 45, 45]),
        }
        variables["temp"] = temp

        # 相对湿度
        humidity = LinguisticVariable("humidity", "湿度", (0, 100))
        humidity.fuzzy_sets = {
            "干燥": FuzzySet("干燥", [0, 0, 45, 60]),
            "湿润": FuzzySet("湿润", [50, 65, 80, 88]),
            "饱和": FuzzySet("饱和", [80, 88, 100, 100]),
        }
        variables["humidity"] = humidity

        # 降雨
        rainfall = LinguisticVariable("rainfall", "降雨", (0, 100))
        rainfall.fuzzy_sets = {
            "无": FuzzySet("无", [0, 0, 3, 8]),
            "小雨": FuzzySet("小雨", [5, 10, 20, 30]),
            "大雨": FuzzySet("大雨", [25, 40, 100, 100]),
        }
        variables["rainfall"] = rainfall

        # 物候期（0=休眠, 0.5=萌芽, 1.0=生长）
        phenology = LinguisticVariable("phenology", "物候期", (0, 1))
        phenology.fuzzy_sets = {
            "休眠期": FuzzySet("休眠期", [0, 0, 0.15, 0.35]),
            "萌芽期": FuzzySet("萌芽期", [0.25, 0.4, 0.55, 0.7]),
            "生长期": FuzzySet("生长期", [0.6, 0.75, 1.0, 1.0]),
        }
        variables["phenology"] = phenology

        return variables

    # ----------------------------------------------------------
    # 2.2 定义专家规则库（按病虫害分组）
    # ----------------------------------------------------------
    def _define_rules(self) -> List[FuzzyRule]:
        rules = []
        idx = 0

        def add(disease, conds, level, desc="", weight=1.0):
            nonlocal idx
            idx += 1
            rules.append(FuzzyRule(
                rule_id=f"R{idx:03d}",
                disease=disease,
                conditions=conds,
                consequence=level,
                weight=weight,
                description=desc
            ))

        # ---------- 炭疽病 ----------
        add("炭疽病", {"temp": "适宜", "humidity": "湿润"},
            "高风险", "温暖湿润环境最利于炭疽菌繁殖")
        add("炭疽病", {"temp": "偏高", "rainfall": "大雨", "phenology": "生长期"},
            "高风险", "高温多雨+生长期嫩叶易感")
        add("炭疽病", {"temp": "适宜", "humidity": "饱和"},
            "高风险", "适温+极高湿度，孢子萌发率极高")
        add("炭疽病", {"temp": "适宜", "rainfall": "小雨"},
            "中风险", "适温有雨，需关注")
        add("炭疽病", {"temp": "偏高", "humidity": "干燥"},
            "中风险", "高温但干燥，风险有限")
        add("炭疽病", {"phenology": "生长期", "rainfall": "无"},
            "中风险", "生长期本身有基础风险")
        add("炭疽病", {"humidity": "干燥", "rainfall": "无"},
            "低风险", "干燥无雨不利于真菌")
        add("炭疽病", {"phenology": "休眠期", "temp": "偏低"},
            "低风险", "冬季低温病菌休眠")
        add("炭疽病", {"temp": "偏低", "humidity": "干燥"},
            "低风险", "低温干燥完全不利")

        # ---------- 疮痂病 ----------
        add("疮痂病", {"temp": "适宜", "rainfall": "小雨", "phenology": "萌芽期"},
            "高风险", "春季萌芽期温暖多雨最易感疮痂")
        add("疮痂病", {"humidity": "湿润", "temp": "适宜", "phenology": "生长期"},
            "高风险", "持续湿润利于疮痂菌侵入新梢")
        add("疮痂病", {"temp": "适宜", "rainfall": "大雨"},
            "高风险", "大雨传播病原")
        add("疮痂病", {"temp": "适宜", "humidity": "湿润", "phenology": "萌芽期"},
            "中风险", "有利条件但未极端")
        add("疮痂病", {"temp": "适宜", "rainfall": "小雨"},
            "中风险", "适温小雨需关注")
        add("疮痂病", {"temp": "偏高"},
            "低风险", "高温抑制疮痂菌（最适15-24℃）")
        add("疮痂病", {"phenology": "休眠期"},
            "低风险", "休眠期不易感染")
        add("疮痂病", {"humidity": "干燥", "rainfall": "无"},
            "低风险", "干燥无雨不利于传播")

        # ---------- 溃疡病 ----------
        add("溃疡病", {"temp": "偏高", "humidity": "饱和", "phenology": "生长期"},
            "高风险", "高温高湿+生长期=溃疡病暴发")
        add("溃疡病", {"temp": "适宜", "rainfall": "大雨"},
            "高风险", "暴雨造成伤口+传播病菌")
        add("溃疡病", {"humidity": "饱和", "temp": "适宜", "phenology": "萌芽期"},
            "高风险", "极高湿度利于溃疡菌侵入")
        add("溃疡病", {"temp": "适宜", "humidity": "湿润", "phenology": "生长期"},
            "中风险", "湿润生长期有基础风险")
        add("溃疡病", {"temp": "偏高", "rainfall": "小雨"},
            "中风险", "高温小雨需关注")
        add("溃疡病", {"phenology": "休眠期"},
            "低风险", "休眠期病菌不活跃")
        add("溃疡病", {"humidity": "干燥", "rainfall": "无"},
            "低风险", "干燥条件抑制溃疡菌")
        add("溃疡病", {"temp": "偏低"},
            "低风险", "低温不利于溃疡菌繁殖")

        # ---------- 脂点黄斑病 ----------
        add("脂点黄斑病", {"temp": "适宜", "rainfall": "大雨", "humidity": "饱和"},
            "高风险", "适温+大雨+极高湿度=暴发条件")
        add("脂点黄斑病", {"temp": "偏高", "humidity": "湿润"},
            "高风险", "高温高湿利于真菌扩展")
        add("脂点黄斑病", {"temp": "偏高", "humidity": "饱和"},
            "高风险", "高温极湿利于脂点黄斑")
        add("脂点黄斑病", {"temp": "适宜", "rainfall": "小雨"},
            "中风险", "适温小雨有一定风险")
        add("脂点黄斑病", {"temp": "偏高", "humidity": "湿润", "phenology": "生长期"},
            "中风险", "生长期高温湿润需关注")
        add("脂点黄斑病", {"humidity": "干燥", "rainfall": "无"},
            "低风险", "干燥无雨不利于真菌")
        add("脂点黄斑病", {"temp": "偏低"},
            "低风险", "低温抑制脂点黄斑菌")

        # ---------- 木虱 ----------
        add("木虱", {"phenology": "生长期", "temp": "适宜"},
            "高风险", "生长期新梢大量抽发，木虱产卵高峰")
        add("木虱", {"phenology": "生长期", "temp": "偏高"},
            "高风险", "高温生长期繁殖快")
        add("木虱", {"phenology": "萌芽期", "temp": "适宜"},
            "中风险", "萌芽期开始活动")
        add("木虱", {"phenology": "萌芽期", "temp": "偏低"},
            "中风险", "萌芽期低温活动受限但仍需关注")
        add("木虱", {"temp": "偏高", "phenology": "休眠期"},
            "中风险", "暖冬导致越冬虫口高")
        add("木虱", {"phenology": "休眠期", "temp": "适宜"},
            "低风险", "休眠期木虱越冬不活跃")
        add("木虱", {"phenology": "休眠期", "temp": "偏低"},
            "低风险", "冬季低温虫口低")

        # ---------- 潜叶蛾 ----------
        add("潜叶蛾", {"phenology": "生长期", "temp": "适宜", "humidity": "湿润"},
            "高风险", "温暖湿润生长期嫩梢大量被害")
        add("潜叶蛾", {"phenology": "生长期", "temp": "偏高"},
            "高风险", "高温生长期繁殖旺盛")
        add("潜叶蛾", {"phenology": "萌芽期", "temp": "适宜"},
            "中风险", "春梢期开始为害")
        add("潜叶蛾", {"phenology": "生长期", "temp": "偏低", "humidity": "湿润"},
            "中风险", "低温限制但湿润仍有风险")
        add("潜叶蛾", {"phenology": "萌芽期", "humidity": "干燥"},
            "中风险", "萌芽期干燥稍有抑制", 0.8)
        add("潜叶蛾", {"phenology": "休眠期"},
            "低风险", "冬季不活动")
        add("潜叶蛾", {"temp": "偏低", "humidity": "干燥"},
            "低风险", "低温干燥完全抑制")

        # ---------- 锈壁虱 ----------
        add("锈壁虱", {"temp": "偏高", "humidity": "干燥", "rainfall": "无"},
            "高风险", "高温干旱无雨=锈壁虱暴发")
        add("锈壁虱", {"temp": "偏高", "humidity": "干燥"},
            "高风险", "高温干燥最利于锈壁虱")
        add("锈壁虱", {"temp": "适宜", "humidity": "干燥", "phenology": "生长期"},
            "中风险", "适温干燥生长期有风险")
        add("锈壁虱", {"temp": "偏高", "rainfall": "小雨"},
            "中风险", "高温但有雨稍抑制")
        add("锈壁虱", {"temp": "偏低"},
            "低风险", "低温不利于繁殖")
        add("锈壁虱", {"humidity": "饱和", "rainfall": "大雨"},
            "低风险", "大雨冲刷+高湿抑制锈壁虱")
        add("锈壁虱", {"phenology": "休眠期"},
            "低风险", "冬季越冬不活跃")

        # ---------- 红蜘蛛 ----------
        add("红蜘蛛", {"temp": "偏高", "humidity": "干燥"},
            "高风险", "高温干燥最利于红蜘蛛暴发")
        add("红蜘蛛", {"temp": "适宜", "humidity": "干燥"},
            "高风险", "适温干燥利于繁殖")
        add("红蜘蛛", {"temp": "适宜", "phenology": "生长期"},
            "高风险", "适温生长期虫口基数高")
        add("红蜘蛛", {"temp": "适宜", "phenology": "萌芽期"},
            "中风险", "春季开始活动")
        add("红蜘蛛", {"temp": "偏低", "humidity": "湿润"},
            "中风险", "低温湿润稍有抑制但仍活动")
        add("红蜘蛛", {"humidity": "饱和", "rainfall": "大雨"},
            "低风险", "暴雨冲刷显著降低虫口")
        add("红蜘蛛", {"phenology": "休眠期", "temp": "偏低"},
            "低风险", "冬季低温越冬")
        add("红蜘蛛", {"temp": "偏低", "humidity": "干燥"},
            "低风险", "低温虫口低")

        return rules

    # ----------------------------------------------------------
    # 2.3 Mamdani 推理核心
    # ----------------------------------------------------------
    def _evaluate_rule(self, rule: FuzzyRule, memberships: Dict[str, Dict[str, float]]) -> float:
        """计算单条规则的触发强度（取最小值 = AND 运算）"""
        strengths = []
        for var_name, set_name in rule.conditions.items():
            if var_name in memberships and set_name in memberships[var_name]:
                strengths.append(memberships[var_name][set_name])
            else:
                return 0.0  # 缺少某个条件则规则不触发
        if not strengths:
            return 0.0
        return min(strengths) * rule.weight

    def _defuzzify(self, rule_activations: List[Tuple[str, float]]) -> float:
        """质心法解模糊：将规则触发结果汇总为 0-100 风险分"""
        numerator = 0.0
        denominator = 0.0
        for consequence, strength in rule_activations:
            centroid = self.RISK_CENTROIDS.get(consequence, 50.0)
            numerator += centroid * strength
            denominator += strength
        if denominator < 1e-10:
            return 25.0  # 无规则触发时返回默认低风险
        return np.clip(numerator / denominator, 0, 100)

    def _risk_level(self, score: float) -> str:
        """风险分 → 等级标签"""
        if score >= 65:
            return "高风险"
        elif score >= 35:
            return "中风险"
        else:
            return "低风险"

    # ----------------------------------------------------------
    # 2.4 数值输入预测
    # ----------------------------------------------------------
    def predict(self, inputs: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        数值输入模式推理

        参数:
            inputs: {"temp": 28.0, "humidity": 85.0, "rainfall": 15.0, "phenology": 0.8}

        返回:
            {
                "炭疽病": {
                    "risk_score": 72.5,
                    "risk_level": "高风险",
                    "fired_rules": [...],
                    "key_factors": [...],
                    "confidence": 0.85
                },
                ...
            }
        """
        # Step 1: 模糊化
        memberships = {}
        for var_name, var in self.variables.items():
            if var_name in inputs:
                memberships[var_name] = var.fuzzify(inputs[var_name])

        return self._infer(memberships, inputs)

    # ----------------------------------------------------------
    # 2.5 定性输入预测（用于验证）
    # ----------------------------------------------------------
    # 定性描述 → 隶属度映射表
    QUALITATIVE_MAPPING = {
        "temp": {
            "偏低":  {"偏低": 0.85, "适宜": 0.15, "偏高": 0.0},
            "正常":  {"偏低": 0.1,  "适宜": 0.85, "偏高": 0.05},
            "适宜":  {"偏低": 0.05, "适宜": 0.85, "偏高": 0.1},
            "偏高":  {"偏低": 0.0,  "适宜": 0.15, "偏高": 0.85},
        },
        "humidity": {
            "干燥":  {"干燥": 0.85, "湿润": 0.15, "饱和": 0.0},
            "正常":  {"干燥": 0.15, "湿润": 0.75, "饱和": 0.1},
            "湿润":  {"干燥": 0.05, "湿润": 0.85, "饱和": 0.1},
            "高湿":  {"干燥": 0.0,  "湿润": 0.2,  "饱和": 0.8},
            "饱和":  {"干燥": 0.0,  "湿润": 0.1,  "饱和": 0.9},
        },
        "rainfall": {
            "无":    {"无": 0.85, "小雨": 0.15, "大雨": 0.0},
            "偏少":  {"无": 0.5,  "小雨": 0.4,  "大雨": 0.1},
            "正常":  {"无": 0.1,  "小雨": 0.7,  "大雨": 0.2},
            "偏多":  {"无": 0.0,  "小雨": 0.25, "大雨": 0.75},
            "大雨":  {"无": 0.0,  "小雨": 0.1,  "大雨": 0.9},
        },
        "phenology": {
            "休眠期": {"休眠期": 0.9, "萌芽期": 0.1, "生长期": 0.0},
            "萌芽期": {"休眠期": 0.05, "萌芽期": 0.9, "生长期": 0.05},
            "生长期": {"休眠期": 0.0, "萌芽期": 0.1, "生长期": 0.9},
        },
    }

    def predict_qualitative(self, qual_inputs: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        定性输入模式推理（用于与监测数据验证）

        参数:
            qual_inputs: {"temp": "偏高", "humidity": "湿润", "rainfall": "偏多", "phenology": "生长期"}

        返回: 同 predict()
        """
        memberships = {}
        for var_name, label in qual_inputs.items():
            if var_name in self.QUALITATIVE_MAPPING:
                mapping = self.QUALITATIVE_MAPPING[var_name]
                if label in mapping:
                    memberships[var_name] = mapping[label]
                else:
                    # 未知标签使用均匀分布
                    sets = list(self.variables[var_name].fuzzy_sets.keys())
                    memberships[var_name] = {s: 1.0 / len(sets) for s in sets}

        return self._infer(memberships, qual_inputs)

    # ----------------------------------------------------------
    # 2.6 通用推理过程
    # ----------------------------------------------------------
    def _infer(self, memberships: Dict[str, Dict[str, float]],
               raw_inputs: Any = None) -> Dict[str, Dict[str, Any]]:
        """通用 Mamdani 推理"""
        results = {}

        for disease in self.DISEASES:
            disease_rules = self._rules_by_disease.get(disease, [])
            fired_rules = []
            rule_activations = []

            # 计算每条规则的触发强度
            for rule in disease_rules:
                strength = self._evaluate_rule(rule, memberships)
                if strength > 0.01:  # 忽略极弱触发
                    fired_rules.append({
                        "rule_id": rule.rule_id,
                        "rule_text": rule.to_text(),
                        "strength": round(strength, 4),
                        "consequence": rule.consequence,
                        "description": rule.description,
                    })
                    rule_activations.append((rule.consequence, strength))

            # 解模糊化
            risk_score = self._defuzzify(rule_activations)
            risk_level = self._risk_level(risk_score)

            # 提取关键因子
            key_factors = self._extract_key_factors(memberships, fired_rules)

            # 计算置信度（基于触发规则数量和强度）
            if fired_rules:
                max_strength = max(r["strength"] for r in fired_rules)
                n_fired = len(fired_rules)
                confidence = min(max_strength * 0.7 + min(n_fired / 5.0, 1.0) * 0.3, 1.0)
            else:
                confidence = 0.2

            # 按触发强度排序
            fired_rules.sort(key=lambda r: r["strength"], reverse=True)

            results[disease] = {
                "risk_score": round(risk_score, 1),
                "risk_level": risk_level,
                "fired_rules": fired_rules[:5],  # 只返回 Top-5
                "key_factors": key_factors,
                "confidence": round(confidence, 3),
                "n_rules_fired": len(fired_rules),
            }

        return results

    def _extract_key_factors(self, memberships: Dict, fired_rules: List) -> List[str]:
        """提取推理中起关键作用的环境因子"""
        factors = []
        display_names = {
            "temp": "温度", "humidity": "湿度",
            "rainfall": "降雨", "phenology": "物候期"
        }
        for var_name, mf_dict in memberships.items():
            # 找隶属度最高的模糊集
            if mf_dict:
                best_set = max(mf_dict, key=mf_dict.get)
                best_val = mf_dict[best_set]
                if best_val > 0.3:
                    dname = display_names.get(var_name, var_name)
                    factors.append(f"{dname}→{best_set}({best_val:.2f})")
        return factors

    # ----------------------------------------------------------
    # 2.7 Agent 接口（标准化调用）
    # ----------------------------------------------------------
    def agent_predict(self, env_features: Dict, host_features: Optional[Dict] = None) -> Dict:
        """
        给 LangGraph Agent 调用的标准接口

        参数:
            env_features: {"temp": 28, "humidity": 85, "rainfall": 15}
                         或 {"temp": "偏高", "humidity": "湿润", "rainfall": "偏多"}
            host_features: {"phenology": 0.8} 或 {"phenology": "生长期"}（可选）

        返回:
            {
                "env_risk": {disease: risk_score, ...},
                "risk_levels": {disease: level, ...},
                "evidence": {disease: [规则解释], ...},
                "top_risk": (disease, score),
                "summary": "当前环境最有利于XXX（风险XX%）..."
            }
        """
        # 合并输入
        inputs = {**env_features}
        if host_features:
            inputs.update(host_features)

        # 判断输入类型
        first_val = next(iter(inputs.values()), None)
        if isinstance(first_val, str):
            results = self.predict_qualitative(inputs)
        else:
            results = self.predict(inputs)

        # 整理为 Agent 友好格式
        env_risk = {d: r["risk_score"] for d, r in results.items()}
        risk_levels = {d: r["risk_level"] for d, r in results.items()}
        evidence = {}
        for d, r in results.items():
            evidence[d] = [fr["description"] for fr in r["fired_rules"][:3] if fr["description"]]

        top_disease = max(env_risk, key=env_risk.get)
        top_score = env_risk[top_disease]

        summary = f"当前环境最有利于{top_disease}发生（风险{top_score:.0f}%）"
        if top_score >= 65:
            summary += "，建议立即采取防控措施"
        elif top_score >= 35:
            summary += "，建议加强监测"
        else:
            summary += "，整体风险可控"

        return {
            "env_risk": env_risk,
            "risk_levels": risk_levels,
            "evidence": evidence,
            "top_risk": (top_disease, top_score),
            "summary": summary,
        }

    # ----------------------------------------------------------
    # 2.8 辅助工具
    # ----------------------------------------------------------
    def get_all_rules_text(self) -> str:
        """导出全部规则的可读文本"""
        text = "柑橘病虫害模糊推理规则库\n" + "=" * 50 + "\n"
        for disease in self.DISEASES:
            text += f"\n【{disease}】\n"
            for r in self._rules_by_disease.get(disease, []):
                text += f"  {r.rule_id}: {r.to_text()}\n"
                if r.description:
                    text += f"         依据: {r.description}\n"
        return text

    def month_to_phenology(self, month: int) -> Tuple[str, float]:
        """月份 → 物候期映射"""
        if month in [12, 1, 2]:
            return "休眠期", 0.1
        elif month in [3, 4]:
            return "萌芽期", 0.45
        elif month in [5, 6, 7, 8, 9, 10]:
            return "生长期", 0.85
        elif month == 11:
            return "休眠期", 0.2
        return "生长期", 0.8

    def get_rule_statistics(self) -> Dict:
        """获取规则库统计信息"""
        stats = {"total_rules": len(self.rules)}
        for disease in self.DISEASES:
            d_rules = self._rules_by_disease.get(disease, [])
            stats[disease] = {
                "n_rules": len(d_rules),
                "高风险规则": sum(1 for r in d_rules if r.consequence == "高风险"),
                "中风险规则": sum(1 for r in d_rules if r.consequence == "中风险"),
                "低风险规则": sum(1 for r in d_rules if r.consequence == "低风险"),
            }
        return stats


# ============================================================
# 3. 便捷调用
# ============================================================

def create_engine() -> CitrusFuzzyEngine:
    """创建模糊推理引擎实例"""
    return CitrusFuzzyEngine()


if __name__ == "__main__":
    engine = create_engine()

    # 快速测试
    print(engine.get_all_rules_text())

    print("\n--- 数值输入测试 ---")
    result = engine.predict({"temp": 28, "humidity": 88, "rainfall": 15, "phenology": 0.85})
    for disease, info in sorted(result.items(), key=lambda x: x[1]["risk_score"], reverse=True):
        print(f"  {disease}: {info['risk_score']:.1f}% ({info['risk_level']}) "
              f"[{info['n_rules_fired']}条规则触发]")

    print("\n--- 定性输入测试 ---")
    result2 = engine.predict_qualitative({
        "temp": "偏高", "humidity": "湿润", "rainfall": "偏多", "phenology": "生长期"
    })
    for disease, info in sorted(result2.items(), key=lambda x: x[1]["risk_score"], reverse=True):
        print(f"  {disease}: {info['risk_score']:.1f}% ({info['risk_level']})")

    print("\n--- Agent 接口测试 ---")
    agent_result = engine.agent_predict(
        {"temp": "偏高", "rainfall": "偏多"},
        {"phenology": "生长期"}
    )
    print(f"  摘要: {agent_result['summary']}")
