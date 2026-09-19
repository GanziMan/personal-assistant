from assistant.config import ModelConfig
from assistant.llm.router import ModelRouter, Provider, TaskKind


def test_heavy_tasks_go_to_cloud():
    r = ModelRouter(ModelConfig())
    for kind in (TaskKind.CODE, TaskKind.PLAN, TaskKind.CHAT):
        assert r.route(kind).provider is Provider.CLOUD


def test_cheap_tasks_stay_local():
    r = ModelRouter(ModelConfig())
    for kind in (TaskKind.EMBED, TaskKind.CLASSIFY, TaskKind.SUMMARIZE_SHORT):
        assert r.route(kind).provider is Provider.LOCAL


def test_sensitive_overrides_policy():
    r = ModelRouter(ModelConfig())
    route = r.route(TaskKind.CODE, sensitive=True)
    assert route.provider is Provider.LOCAL, "민감 작업은 정책을 무시하고 로컬"


def test_force_cloud_moves_local_tasks_out():
    r = ModelRouter(ModelConfig(force_cloud=True))
    assert r.route(TaskKind.CLASSIFY).provider is Provider.CLOUD
    # 민감 표시는 force_cloud 보다 강해야 한다
    assert r.route(TaskKind.CLASSIFY, sensitive=True).provider is Provider.LOCAL


def test_every_task_kind_has_a_policy():
    r = ModelRouter(ModelConfig())
    for kind in TaskKind:
        assert r.route(kind).reason, f"{kind} 에 라우팅 근거가 없다"
