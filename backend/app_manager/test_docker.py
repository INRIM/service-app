from python_on_whales import DockerClient


app_name = "app2"
prj_name = "mci-service"
docker = DockerClient(
    compose_project_name=prj_name,
    compose_env_file=f"/apps/web-client/inrim/{app_name}/docker/.env",
    compose_files=[f"/apps/web-client/inrim/{app_name}/docker/docker-compose.yml"])
docker.compose.up(detach=True, build=True)
