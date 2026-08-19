import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROVISION = ROOT / "demo" / "provision_keycloak.sh"


class ProvisionKeycloakTest(unittest.TestCase):
    def test_enables_demo_audience_for_web_and_scheduler_clients(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            curl_log = tmp_path / "curl.jsonl"
            mock_curl = tmp_path / "curl"
            mock_curl.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    url=
                    method=GET
                    data=
                    previous=
                    for argument in "$@"; do
                        if [[ "$previous" == "-X" ]]; then method="$argument"; fi
                        if [[ "$previous" == "-d" ]]; then data="$argument"; fi
                        if [[ "$argument" == http://* || "$argument" == https://* ]]; then
                            url="$argument"
                        fi
                        previous="$argument"
                    done
                    jq -nc --arg method "$method" --arg url "$url" --arg data "$data" \
                        '{method:$method,url:$url,data:$data}' >> "$CURL_LOG"
                    case "$url" in
                        */realms/master/protocol/openid-connect/token)
                            echo '{"access_token":"admin-token"}' ;;
                        *'/clients?clientId=backend-web')
                            echo '[{"id":"web-uuid"}]' ;;
                        *'/clients?clientId=calendar-scheduler')
                            echo '[{"id":"scheduler-uuid"}]' ;;
                        */clients/web-uuid/client-secret)
                            echo '{"value":"web-secret"}' ;;
                        */clients/scheduler-uuid/client-secret)
                            echo '{"value":"scheduler-secret"}' ;;
                        */protocol-mappers/models)
                            echo '[]' ;;
                        *'/users?username=service-account-calendar-scheduler&exact=true')
                            echo '[{"id":"service-account-uuid"}]' ;;
                        *'/users?username='*)
                            echo '[{"id":"user-uuid"}]' ;;
                    esac
                    """
                )
            )
            mock_curl.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{tmp}{os.pathsep}{env['PATH']}",
                    "CURL_LOG": str(curl_log),
                    "KEYCLOAK_ADMIN_PASSWORD": "test-only",
                    "OZON_TOKEN_AUDIENCE": "demo",
                }
            )
            result = subprocess.run(
                ["bash", str(PROVISION)],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("KEYCLOAK_CLIENT_SECRET=web-secret", result.stdout)
            self.assertIn(
                "SCHEDULER_OAUTH_CLIENT_SECRET=scheduler-secret", result.stdout
            )
            requests = [
                json.loads(line) for line in curl_log.read_text().splitlines()
            ]
            mapper_requests = [
                request
                for request in requests
                if request["method"] == "POST"
                and request["url"].endswith("/protocol-mappers/models")
            ]
            self.assertEqual(2, len(mapper_requests))
            self.assertEqual(
                {"web-uuid", "scheduler-uuid"},
                {
                    request["url"].split("/clients/", 1)[1].split("/", 1)[0]
                    for request in mapper_requests
                },
            )
            for request in mapper_requests:
                payload = json.loads(request["data"])
                self.assertEqual("oidc-audience-mapper", payload["protocolMapper"])
                self.assertEqual(
                    "demo", payload["config"]["included.custom.audience"]
                )
                self.assertEqual("true", payload["config"]["access.token.claim"])


if __name__ == "__main__":
    unittest.main()
