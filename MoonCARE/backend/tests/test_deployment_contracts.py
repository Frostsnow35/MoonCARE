import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))


class DeploymentContractsTests(unittest.TestCase):
    def test_compose_includes_local_only_redis_and_drops_legacy_memory_env(self):
        compose_text = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("redis:", compose_text)
        self.assertIn("container_name: mooncare-redis", compose_text)
        self.assertIn('${REDIS_BIND_ADDR:-127.0.0.1}:${REDIS_PORT:-6379}:6379', compose_text)
        self.assertIn("REDIS_URL: ${REDIS_URL:-redis://redis:6379}", compose_text)
        self.assertNotIn("AWARENESS_MEMORY_ENABLED", compose_text)
        self.assertNotIn("AWARENESS_BASE_URL", compose_text)

    def test_env_examples_keep_redis_and_remove_legacy_memory_variables(self):
        root_env = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        backend_env = (BACKEND_ROOT / ".env.example").read_text(encoding="utf-8")

        for content in (root_env, backend_env):
            self.assertIn("REDIS_URL=", content)
            self.assertNotIn("AWARENESS_", content)

        self.assertIn("REDIS_BIND_ADDR=127.0.0.1", root_env)
        self.assertIn("REDIS_PORT=6379", root_env)
        self.assertIn("REDIS_URL=redis://redis:6379", root_env)
        self.assertIn("REDIS_URL=redis://localhost:6379", backend_env)

    def test_active_docs_and_guides_reflect_local_memory_and_redis_infra(self):
        deployment_doc = (PROJECT_ROOT / "docs" / "deployment-docker-server.md").read_text(encoding="utf-8")
        technical_doc = (
            PROJECT_ROOT / "docs" / "技术文档-MoonCARE女性PMS情绪陪伴.md"
        ).read_text(encoding="utf-8")
        inner_agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        outer_agents = (WORKSPACE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        android_plan = (
            PROJECT_ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-06-02-android-capacitor-railway-plan.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Redis 基础设施已加入 Compose", deployment_doc)
        self.assertIn("不再纳入外部记忆服务", deployment_doc)
        self.assertIn("仅组合本地数据库记忆与健康上下文", technical_doc)
        self.assertNotIn("Awareness Local", technical_doc)
        self.assertNotIn("Awareness daemon", technical_doc)
        self.assertIn("mooncare-redis", inner_agents)
        self.assertIn("mooncare-redis", outer_agents)
        self.assertNotIn("awareness:start", inner_agents)
        self.assertNotIn("awareness:start", outer_agents)
        self.assertNotIn("Awareness", android_plan)
        self.assertIn("Redis/后端环境变量基线", android_plan)

    def test_nginx_sample_blocks_internal_surfaces_and_keeps_streaming_routes(self):
        nginx_conf = (PROJECT_ROOT / "deploy" / "nginx" / "mooncare-ip.conf").read_text(encoding="utf-8")

        for blocked_path in ("/docs", "/redoc", "/openapi.json", "/metrics"):
            self.assertIn(f"location = {blocked_path}", nginx_conf)
            self.assertIn("return 404;", nginx_conf)

        self.assertIn("location /api/v1/chat/ws/", nginx_conf)
        self.assertIn("proxy_set_header Upgrade $http_upgrade;", nginx_conf)
        self.assertIn("location = /api/v1/chat/stream", nginx_conf)
        self.assertIn("proxy_buffering off;", nginx_conf)

    def test_server_ops_artifacts_exist_and_reference_real_commands(self):
        runbook = (PROJECT_ROOT / "docs" / "server-deployment-runbook.md")
        server_env = (PROJECT_ROOT / "deploy" / "env" / "server.env.example")
        backup_script = (PROJECT_ROOT / "deploy" / "scripts" / "backup_postgres.sh")
        restore_script = (PROJECT_ROOT / "deploy" / "scripts" / "restore_postgres.sh")
        smoke_script = (PROJECT_ROOT / "deploy" / "scripts" / "smoke_check.sh")

        for path in (runbook, server_env, backup_script, restore_script, smoke_script):
            self.assertTrue(path.exists(), f"Missing deployment artifact: {path}")

        runbook_text = runbook.read_text(encoding="utf-8")
        server_env_text = server_env.read_text(encoding="utf-8")
        backup_text = backup_script.read_text(encoding="utf-8")
        restore_text = restore_script.read_text(encoding="utf-8")
        smoke_text = smoke_script.read_text(encoding="utf-8")

        self.assertIn("docker compose --env-file", runbook_text)
        self.assertIn("backup_postgres.sh", runbook_text)
        self.assertIn("restore_postgres.sh", runbook_text)
        self.assertIn("smoke_check.sh", runbook_text)
        self.assertIn("NVIDIA_API_KEY=", server_env_text)
        self.assertIn("REDIS_URL=redis://redis:6379", server_env_text)
        self.assertIn("pg_dump", backup_text)
        self.assertIn("docker compose", backup_text)
        self.assertIn("psql", restore_text)
        self.assertIn("--yes", restore_text)
        self.assertIn("/healthz", smoke_text)
        self.assertIn("/api/v1/auth/login", smoke_text)
        self.assertIn("/api/v1/chat/session", smoke_text)


if __name__ == "__main__":
    unittest.main()
