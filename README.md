# redmine_wiki_assistant

## prepare project files and install docker
cp .env.example .env
chmod +x setup.sh entrypoint.sh traefik/entrypoint.sh
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
## in case there is no repo for docker compose plugin v.2.x - add it
echo "setting up docker repository keys and sources for package installation"
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee \
/etc/apt/sources.list.d/docker.list > /dev/null
## update and install docker compose plugin
sudo apt-get update
sudo apt-get install -y docker-compose-plugin
## create letsencrypt volume
mkdir -p letsencrypt
chmod 600 letsencrypt
## build
docker compose -f docker-compose.prod.yml --env-file .env build --build-arg ENV=prod
## run
docker compose -f docker-compose.prod.yml up
