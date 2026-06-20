Docker Desktop -> Settings -> Docker Engine
نحط هاد بعدين apply & restart
{
"registry-mirrors": [
"https://mirror.gcr.io",
"https://dockerhub.azk8s.cn"
],
"dns": ["8.8.8.8", "8.8.4.4"]
}

اول مرة رح ياخد وقت وبدو نت منيح لانو رح ينزل باكجات يفضل تفعلو باقة ساعية، اسفة

تيرمنال المشروع، لنشغلو

docker compose up -d

لنعبي الداتابيز يوزرات ومنتجات وكارت ، وبيعمل reset للداتابيز
docker compose --profile seed run --rm seed

لنعيد تعباية الكارت بس
docker compose run --rm migrate python manage.py shell -c "exec(open('seed_carts.py', encoding='utf-8').read())"

تيست الكاش
locust -f locustfile_cache_test.py --host=http://127.0.0.1:8080

redis-cli CONFIG RESETSTAT
redis-cli INFO stats (or -n 1)

docker compose restart nginx

الطلب 4
docker compose --profile batch run --rm batch

docker compose ps
http://localhost:9090/targets

بس بدنا نطفيه
docker compose down

The API is available through NGINX at:

```text
http://localhost:8080/api/products/
```

Prometheus is available at:

```text
http://localhost:9090
```

Run the batch benchmark job:

```powershell
docker compose --profile batch run --rm batch
```

Stop the stack:

```powershell
docker compose down
```

من اجل الطلب الثاني
pip install waitress
waitress-serve --threads=100 --connection-limit=2000 --backlog=2048 --port=8000 core.wsgi:application

#seeding
python manage.py shell -c "exec(open('seed.py', encoding='utf-8').read())"

python manage.py shell -c "exec(open('seed_carts.py', encoding='utf-8').read())"

pip install django-prometheus

ننزل بروميثيوس 3.5.3 ونغير فايل اليامل
Download | Prometheus
cd C:\prometheus
.\prometheus.exe

http://localhost:9090

Download Grafana

من اجل الطلب الثالث
1-Install Redis on your machine and start the redis server
Run each command in a separate terminal window
1-celery -A core worker -l info
2-run python server
3-run : locust
Watch the celery window while pushing notifications
