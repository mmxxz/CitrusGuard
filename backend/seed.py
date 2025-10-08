import uuid
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.alert import Alert
from app.models.user import User
from app.models.orchard import Orchard
from app.models.diagnosis import DiagnosisSession, Diagnosis

def seed_data():
    db = SessionLocal()
    try:
        # Find the first user and their first orchard
        user = db.query(User).first()
        if not user:
            print("No user found. Please register a user first.")
            return
        
        orchard = db.query(Orchard).filter(Orchard.user_id == user.id).first()
        if not orchard:
            print(f"No orchard found for user {user.email}. Please create an orchard first.")
            return

        # Check if alerts already exist for this orchard
        existing_alerts = db.query(Alert).filter(Alert.orchard_id == orchard.id).count()
        if existing_alerts > 0:
            print("Alerts already exist for this orchard. Skipping seed.")
        else:
            # Add mock alerts
            alerts_to_add = [
                Alert(
                    orchard_id=orchard.id,
                    type="病害",
                    risk_item="溃疡病",
                    risk_level="high",
                    confidence=0.85,
                    reason="基于未来72小时高温高湿天气预报"
                ),
                Alert(
                    orchard_id=orchard.id,
                    type="虫害",
                    risk_item="红蜘蛛",
                    risk_level="medium",
                    confidence=0.70,
                    reason="根据近期叶片黄化历史记录"
                ),
            ]
            
            db.add_all(alerts_to_add)
            db.commit()
            print(f"Successfully seeded {len(alerts_to_add)} alerts for orchard {orchard.name}.")

        # Check if diagnosis cases already exist for this orchard
        existing_cases = db.query(DiagnosisSession).filter(
            DiagnosisSession.orchard_id == orchard.id,
            DiagnosisSession.status == "completed"
        ).count()
        
        if existing_cases > 0:
            print("Diagnosis cases already exist for this orchard. Skipping seed.")
        else:
            # Add mock diagnosis cases
            now = datetime.now()
            
            # Create completed diagnosis sessions
            session1 = DiagnosisSession(
                id=uuid.uuid4(),
                orchard_id=orchard.id,
                user_id=user.id,
                start_time=now - timedelta(days=5),
                end_time=now - timedelta(days=5, hours=1),
                status="completed",
                initial_query="我的橘子树叶子发黄了",
                initial_image_urls=["http://example.com/leaf1.jpg"]
            )
            
            session2 = DiagnosisSession(
                id=uuid.uuid4(),
                orchard_id=orchard.id,
                user_id=user.id,
                start_time=now - timedelta(days=3),
                end_time=now - timedelta(days=3, hours=2),
                status="completed",
                initial_query="发现叶片上有黑色斑点",
                initial_image_urls=["http://example.com/spot1.jpg"]
            )
            
            db.add_all([session1, session2])
            db.commit()
            
            # Create diagnosis results
            diagnosis1 = Diagnosis(
                id=uuid.uuid4(),
                session_id=session1.id,
                primary_diagnosis="柑橘缺镁症",
                confidence=0.88,
                secondary_diagnoses=[{"name": "柑橘黄化病", "confidence": 0.12}],
                prevention_advice="定期施用镁肥，保持土壤pH值在6.0-6.5之间",
                treatment_advice="立即喷施硫酸镁叶面肥，浓度为0.2%",
                follow_up_plan="7天后观察新叶生长情况并反馈效果",
                original_image_urls=["http://example.com/leaf1.jpg"],
                generated_at=now - timedelta(days=5, hours=1)
            )
            
            diagnosis2 = Diagnosis(
                id=uuid.uuid4(),
                session_id=session2.id,
                primary_diagnosis="柑橘溃疡病",
                confidence=0.92,
                secondary_diagnoses=[{"name": "柑橘疮痂病", "confidence": 0.08}],
                prevention_advice="加强通风透光，避免叶片湿润时间过长",
                treatment_advice="喷施波尔多液或铜制剂，每7-10天一次",
                follow_up_plan="14天后检查病斑是否停止扩展",
                original_image_urls=["http://example.com/spot1.jpg"],
                generated_at=now - timedelta(days=3, hours=2)
            )
            
            db.add_all([diagnosis1, diagnosis2])
            db.commit()
            
            print(f"Successfully seeded 2 diagnosis cases for orchard {orchard.name}.")

    finally:
        db.close()

if __name__ == "__main__":
    print("Seeding database with mock alert data...")
    seed_data()
