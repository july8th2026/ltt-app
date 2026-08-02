from platform_core.agent import metrics


def test_agent_live_metrics_latency_and_approval_rate():
    metrics.reset_for_tests()
    metrics.record_planning(success=True, latency_ms=20)
    metrics.record_planning(success=False, latency_ms=10)
    metrics.record_approval(success=True)
    metrics.record_approval(success=False)
    result = metrics.snapshot()
    assert result["planning_latency_ms_avg"] == 15
    assert result["planning_errors"] == 1
    assert result["approval_rate"] == 0.5
