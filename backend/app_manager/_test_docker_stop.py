from python_on_whales import DockerClient


module_name = "app2"
docker = DockerClient(
    compose_project_name=f"logistica",
    compose_env_file=f"/apps/web-client/inrim/{module_name}/docker/.env",
    compose_files=[
        f"/apps/web-client/inrim/{module_name}/docker/docker-compose.yml"
    ],
)
docker.compose.stop()
