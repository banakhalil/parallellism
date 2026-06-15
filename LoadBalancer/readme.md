This project uses NGINX as a load balancer
We used least connections algorithm with the following backend instances:

- localhost:8001
- localhost:8002
- localhost:8003

I personally tried Locust as a testing tool

to test the load balancer you need to install NGINX from the following URL: https://nginx.org/en/download.html 
and click on nginx/Windows-1.31.0 to download it

then create a folder called nginx and extract the compressed file you downloaded earlier their
then open nginx\conf\nginx.conf in your notepad or vs code
and replace all the content in that file with the code I provided in nginx.conf


then open 3 separate terminals inside the project folder
in terminal 1, run: python manage.py runserver 8001  
in terminal 2, run: python manage.py runserver 8002  
in terminal 3, run: python manage.py runserver 8003

then go to : nginx\nginx-1.31.0  and open its cmd and run :
nginx.exe

then try to open this on your browser to make sure that its working: 
http://127.0.0.1:8080/api/products/

installing Locust:
run: pip install locust 
then: locust
and open : http://localhost:8089
--------------------------------------------------------------------
IMPORTANT:
try a test using the following host: http://127.0.0.1:8080
--------------------------------------------------------------------