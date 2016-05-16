docker stop Nurevam_Bot && docker rm Nurevam_Bot
docker run --name Nurevam_Bot -d --restart="always" -v /docker/host/ --env-file envfile.list --link redis:redis bot
docker stop Nurevam_Web && docker rm Nurevam_Web
docker run -d --restart="always" --name Nurevam_Web --link redis:redis --env-file envfile.list web