# 直接测试动态引擎状态返回
from app.agents.dynamic_engine.executor import dynamic_engine_executor
from app.core.orchard_state import OrchardState

def test_direct_state_passing():
    """直接测试动态引擎函数的状态返回"""
    print("=== 直接测试动态引擎状态返回 ===")

    # 创建测试状态
    test_state = OrchardState(
        messages=[],
        user_query="What should I be concerned about today?",
        image_urls=None,
        intent="general_qa",
        session_id="test-session",
        orchard_profile={"id": "test-orchard-id"},
        is_profile_fetched=True,  # 跳过获取步骤
        realtime_weather={"temp": 25, "humidity": 70, "condition": "sunny"},
        historical_cases_retrieved=[
            {"case": "citrus_canker", "treatment": "copper_fungicide"},
            {"case": "magnesium_deficiency", "treatment": "foliar_spray"}
        ],
        initial_diagnosis_suggestion=None,
        intermediate_reasoning=None,
        working_diagnosis=None,
        decision=None,
        clarification_needed=False,
        clarification_count=0,
        clarification_question=None,
        final_diagnosis_report=None,
        final_report=None,
        confidence_score=None,
        workflow_step="test_start"
    )

    print(f"输入状态键: {list(test_state.keys())}")
    print(f"输入final_report: {test_state.get('final_report')}")

    try:
        # 直接调用动态引擎函数
        result_state = dynamic_engine_executor(test_state)

        print(f"\n输出状态键: {list(result_state.keys())}")
        print(f"输出final_report: {result_state.get('final_report')}")
        print(f"输出workflow_step: {result_state.get('workflow_step')}")

        # 验证状态返回
        if result_state.get('final_report'):
            print("✅ SUCCESS: final_report成功生成并返回!")
            briefing = result_state['final_report'].get('briefing', '')
            print(f"简报内容预览: {briefing[:100]}...")
            return True
        else:
            print("❌ FAILED: final_report未生成!")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_direct_state_passing()
    print(f"\n测试结果: {'通过' if result else '失败'}")