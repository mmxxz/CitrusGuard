"""
柑橘病虫害预测系统的核心预测器模块。
"""
import numpy as np

# ===== 疾病症状知识库 =====
DISEASE_SYMPTOMS = {
    "炭疽病": "主要危害果实、叶片和嫩枝。果实上出现圆形、褐色、略凹陷的病斑，后期病斑上出现黑色小点。叶片上病斑呈圆形、暗褐色。",
    "疮痂病": "主要危害嫩叶、嫩梢和幼果。叶片上出现木栓化的瘤状突起，呈黄褐色，果实上病斑相似，导致果实畸形、硬化。",
    "溃疡病": "危害叶、枝、果，产生近圆形的木栓化病斑，中央凹陷开裂，周围有黄色晕圈，感觉像火山口。",
    "脂点黄斑病": "主要危害叶片。叶片正面出现针头大小的黄色小点，背面则对应有黑褐色或黄褐色的小突起，像油脂点。",
    "木虱": "成虫和若虫吸食嫩梢汁液，导致嫩叶卷曲、畸形，并分泌白色蜡质物。更严重的是，它是柑橘黄龙病的传播媒介。",
    "潜叶蛾": "幼虫在叶片表皮下潜食叶肉，形成银白色的弯曲隧道（鬼画符），导致叶片卷缩，影响光合作用。",
    "锈壁虱": "危害果实和叶片，吸食汁液。果皮受害后变黑褐色，表面粗糙，称为“黑皮果”。叶片受害则失去光泽。",
    "红蜘蛛": "主要在叶片背面吸食汁液，导致叶片出现密集的灰白色小点，严重时叶片失绿、黄化，甚至脱落。可看到细小红色虫体和蛛网。"
}

# ===== 疾病名称映射 =====
DISEASE_MAPPING = {
    "炭疽病",
    "疮痂病", 
    "溃疡病",
    "脂点黄斑病",
    "木虱",
    "潜叶蛾",
    "锈壁虱",
    "红蜘蛛"
}
OUTPUT_DISEASES = list(DISEASE_MAPPING)

class CitrusDiseasePredictor:
    """基于专家规则的柑橘病虫害预测器"""
    
    def __init__(self):
        self.history = []
        self.accumulated = {
            'eat': 0.0,   # 有效积温
            'chd': 0,     # 连续高湿天数
            'rcr': 0.0    # 近期累计降雨
        }
        
        # 英文到中文的映射
        self.english_to_chinese = {
            "anthracnose": "炭疽病",
            "scab": "疮痂病", 
            "canker": "溃疡病",
            "greasy_spot": "脂点黄斑病",
            "psyllid": "木虱",
            "leaf_miner": "潜叶蛾",
            "rust_mite": "锈壁虱",
            "red_spider": "红蜘蛛"
        }
    
    def add_daily_data(self, data):
        """添加每日数据并更新累积变量"""
        self.history.append(data.copy())
        
        daily_eat = max(data['avg_temp'] - 12, 0)
        self.accumulated['eat'] += daily_eat
        
        if data['avg_rh'] >= 85:
            self.accumulated['chd'] += 1
        else:
            self.accumulated['chd'] = 0
        
        if len(self.history) >= 3:
            self.accumulated['rcr'] = sum(d['rainfall'] for d in self.history[-3:])
        else:
            self.accumulated['rcr'] = sum(d['rainfall'] for d in self.history)
        
        self.accumulated['eat'] = min(self.accumulated['eat'], 400)
        self.accumulated['chd'] = min(self.accumulated['chd'], 14)
        self.accumulated['rcr'] = min(self.accumulated['rcr'], 150)
    
    def predict_disease_risk(self, disease, data):
        """基于规则预测特定疾病的风险，并返回依据"""
        avg_temp = data['avg_temp']
        avg_rh = data['avg_rh']
        lwd = data['lwd']
        rainfall = data['rainfall']
        wind_speed = data['wind_speed']
        host_susceptibility = data.get('host_susceptibility', 0.7)
        host_phenology = data.get('host_phenology', 0.7)
        eat = self.accumulated['eat']
        chd = self.accumulated['chd']
        rcr = self.accumulated['rcr']
        
        risk_score = 0.0
        basis = []
        
        if disease == "炭疽病":
            if 18 <= avg_temp <= 30 and avg_rh >= 70 and host_susceptibility >= 0.7:
                risk_score += 0.8
                basis.append(f"温度适宜({avg_temp}°C)且高湿({avg_rh}%)，感病性高")
            if avg_temp >= 28 and rainfall >= 15 and host_phenology >= 0.6:
                risk_score += 0.7
                basis.append(f"高温({avg_temp}°C)伴随大雨({rainfall}mm)，处于生长期")
            if avg_temp <= 20 and chd >= 5 and host_susceptibility >= 0.7:
                risk_score += 0.6
                basis.append(f"低温({avg_temp}°C)但连续高湿({chd}天)，感病性高")
        
        elif disease == "疮痂病":
            if 18 <= avg_temp <= 30 and 5 <= rainfall <= 15 and 0.4 <= host_phenology <= 0.6:
                risk_score += 0.8
                basis.append(f"温和({avg_temp}°C)有雨({rainfall}mm)，处于萌芽期")
            if lwd >= 12 and 18 <= avg_temp <= 30:
                risk_score += 0.7
                basis.append(f"叶面长时间湿润({lwd}h)且温度适宜({avg_temp}°C)")
        
        elif disease == "溃疡病":
            if avg_temp >= 28 and avg_rh >= 90 and host_phenology >= 0.6:
                risk_score += 0.8
                basis.append(f"高温({avg_temp}°C)高湿({avg_rh}%)，处于生长期")
            if 18 <= avg_temp <= 30 and rainfall >= 20 and wind_speed <= 5:
                risk_score += 0.7
                basis.append(f"大雨({rainfall}mm)微风，利于病菌传播")

        elif disease == "脂点黄斑病":
            if 18 <= avg_temp <= 30 and rainfall >= 20 and avg_rh >= 90:
                risk_score += 0.8
                basis.append(f"温和({avg_temp}°C)有大雨({rainfall}mm)且高湿({avg_rh}%) ")
            if avg_temp >= 28 and lwd >= 12:
                risk_score += 0.7
                basis.append(f"高温({avg_temp}°C)且叶面长时间湿润({lwd}h)")

        elif disease == "木虱":
            if host_phenology >= 0.6 and 18 <= avg_temp <= 30:
                risk_score += 0.8
                basis.append(f"果树处于生长期，温度({avg_temp}°C)适宜木虱繁殖")
            if host_phenology >= 0.6 and eat >= 200:
                risk_score += 0.6
                basis.append(f"果树处于生长期，有效积温({eat:.0f})充足")

        elif disease == "潜叶蛾":
            if host_phenology >= 0.6 and 18 <= avg_temp <= 30 and avg_rh >= 60:
                risk_score += 0.8
                basis.append(f"生长期、温度适宜({avg_temp}°C)、湿度较高({avg_rh}%) ")
            if host_phenology >= 0.6 and eat >= 200:
                risk_score += 0.7
                basis.append(f"果树处于生长期，有效积温({eat:.0f})充足")

        elif disease == "锈壁虱":
            if avg_temp >= 28 and avg_rh <= 50 and rainfall <= 2:
                risk_score += 0.8
                basis.append(f"高温({avg_temp}°C)、干燥({avg_rh}%)且无雨")
            if eat >= 200 and avg_rh <= 50:
                risk_score += 0.6
                basis.append(f"有效积温({eat:.0f})高且环境干燥({avg_rh}%) ")

        elif disease == "红蜘蛛":
            if 18 <= avg_temp <= 30 and avg_rh >= 90:
                risk_score += 0.8
                basis.append(f"温度适宜({avg_temp}°C)且湿度极高({avg_rh}%) ")
            if 18 <= avg_temp <= 30 and eat >= 100:
                risk_score += 0.7
                basis.append(f"温度({avg_temp}°C)适宜且有效积温({eat:.0f})充足")
        
        risk_score = min(1.0, risk_score * host_susceptibility)
        noise = np.random.normal(0, 0.02)
        final_risk = np.clip(risk_score + noise, 0, 1) * 100
        
        # 如果没有触发任何规则，但仍有基础风险，则提供通用依据
        if not basis and final_risk > 5:
            basis.append(f"基于当前综合环境因素（温度 {avg_temp}°C, 湿度 {avg_rh}%）的潜在风险。")

        return {
            "risk": final_risk,
            "basis": basis,
            "symptoms": DISEASE_SYMPTOMS.get(disease, "暂无详细症状信息。 ")
        }

    def predict(self, data):
        """预测所有疾病风险"""
        risk_results = {}
        for disease in OUTPUT_DISEASES:
            risk_info = self.predict_disease_risk(disease, data)
            risk_results[disease] = risk_info
        return risk_results
    
    def predict_multi_days(self, weather_forecast):
        """多天预测"""
        predictions = []
        temp_predictor = CitrusDiseasePredictor()
        temp_predictor.history = self.history.copy()
        temp_predictor.accumulated = self.accumulated.copy()
        
        for day_data in weather_forecast:
            full_data = {
                **day_data,
                'host_susceptibility': day_data.get('host_susceptibility', 0.7),
                'host_phenology': day_data.get('host_phenology', 0.7)
            }
            
            temp_predictor.add_daily_data(full_data)
            risk_predictions = temp_predictor.predict(full_data)
            predictions.append(risk_predictions)
        
        return predictions
    
    def generate_report(self, risk_results):
        """生成风险评估报告"""
        report = "柑橘病虫害风险评估报告\n"
        report += "=" * 50 + "\n"
        
        # 按风险等级分类
        high_risk = [(d, r) for d, r in risk_results.items() if r['risk'] >= 70]
        med_risk = [(d, r) for d, r in risk_results.items() if 40 <= r['risk'] < 70]
        low_risk = [(d, r) for d, r in risk_results.items() if r['risk'] < 40]
        
        if high_risk:
            report += "🔴 高风险疾病 (≥70%):\n"
            for disease, data in sorted(high_risk, key=lambda x: x[1]['risk'], reverse=True):
                report += f"  - {disease}: {data['risk']:.1f}%\n"
        
        if med_risk:
            report += "\n🟡 中风险疾病 (40-70%):\n"
            for disease, data in sorted(med_risk, key=lambda x: x[1]['risk'], reverse=True):
                report += f"  - {disease}: {data['risk']:.1f}%\n"
        
        if low_risk:
            report += "\n🟢 低风险疾病 (<40%):\n"
            for disease, data in sorted(low_risk, key=lambda x: x[1]['risk'], reverse=True):
                report += f"  - {disease}: {data['risk']:.1f}%\n"
        
        report += "\n📊 关键环境因素:\n"
        report += f"  - 有效积温(EAT): {self.accumulated['eat']:.1f}℃·日\n"
        report += f"  - 连续高湿天数(CHD): {self.accumulated['chd']}天\n"
        report += f"  - 近期累计降雨(RCR): {self.accumulated['rcr']:.1f}mm\n"
        
        return report
    
