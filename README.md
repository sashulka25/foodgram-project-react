# Foodgram - Продуктовый помощник

### Адрес веб-приложения:
```
https://litefoodgram.ddns.net/
```

### Описание проекта
Foodgram - веб-приложение, разработанное для удобной организации и управления рецептами, а также создания списков покупок на основе выбранных блюд. Пользователи могут публиковать свои рецепты, подписываться на рецепты других пользователей, добавлять рецепты в избранное и создавать и скачивать список продуктов для приготовления блюд.

### Запуск проекта: 
<i>Примечание: Все примеры указаны для Linux</i><br>
1. Склонируйте репозиторий на свой компьютер:
    ```
    git clone git@github.com:sashulka25/foodgram-project-react.git
    ```
2. Создайте файл `.env` и заполните его своими данными. Все необходимые переменные перечислены в файле `.env.example`, находящемся в корневой директории проекта.

### Создание Docker-образов

1. Замените `YOUR_USERNAME` на свой логин на DockerHub:

    ```
    cd frontend
    docker build -t YOUR_USERNAME/foodgram_frontend .
    cd ../backend
    docker build -t YOUR_USERNAME/foodgram_backend . 
    ```

2. Загрузите образы на DockerHub:

    ```
    docker push YOUR_USERNAME/foodgram_frontend
    docker push YOUR_USERNAME/foodgram_backend
    ```

### Деплой на сервере

1. Подключитесь к удаленному серверу

    ```
    ssh -i PATH_TO_SSH_KEY/SSH_KEY_NAME YOUR_USERNAME@SERVER_IP_ADDRESS 
    ```
    
    Где:
    - `PATH_TO_SSH_KEY` - путь к файлу с вашим SSH-ключом
    - `SSH_KEY_NAME` - имя файла с вашим SSH-ключом
    - `YOUR_USERNAME` - ваше имя пользователя на сервере
    - `SERVER_IP_ADDRESS` - IP-адрес вашего сервера

    Например: ssh -i D:/Dev/vm_access/yc-yakovlevstepan yc-user@153.0.2.10

2. Создайте на сервере директорию `foodgram`:

    ```
    mkdir foodgram
    ```

3. Установите Docker Compose на сервер:

    ```
    sudo apt update
    sudo apt install curl
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo apt install docker-compose
    ```

4. Скопируйте файлы `docker-compose.production.yml`, `nginx.conf` и `.env` в директорию `foodgram/` на сервере:

    ```
    scp -i PATH_TO_SSH_KEY/SSH_KEY_NAME <имя-файла> YOUR_USERNAME@SERVER_IP_ADDRESS:/home/YOUR_USERNAME/foodgram/<имя-файла>
    ```

5. Отредактируйте файл конфигурации Nginx и замените его настройки следующими (требуются права root):

    ```
    sudo nano /etc/nginx/sites-enabled/default 
    ```

    ```
    server {
        server_tokens off;

        server_name <доменное-имя>;

        location / {
            proxy_set_header Host $http_host;
            proxy_pass http://127.0.0.1:8000;
        }

    }
    ```

6. Проверьте файл конфигурации Nginx и перезагрузите его, если проверка прошла успешно:

    ```bash
    sudo nginx -t
    sudo systemctl reload nginx
    ```

7. Получите SSL-сертификат для вашего доменного имени с помощью Certbot:

    ```bash
    sudo apt install snapd
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot 
    sudo certbot --nginx
    ```

8. Запустите Docker Compose в режиме демона:

    ```
    sudo docker compose -f /home/YOUR_USERNAME/foodgram/docker-compose.production.yml up -d
    ```

9. Выполните миграции, создайте суперюзера и соберите статические файлы бэкенда:

    ```
    sudo docker compose -f /home/YOUR_USERNAME/foodgram/docker-compose.production.yml exec backend python manage.py migrate
    sudo docker compose exec backend python manage.py createsuperuser
    sudo docker compose -f /home/YOUR_USERNAME/foodgram/docker-compose.production.yml exec backend python manage.py collectstatic --noinput
    ```

10. Скопируйте предустановленные данные csv:

    ```
    sudo docker compose exec backend python manage.py import_ingredients recipes/   data/ingredients.csv
    ```

8. Данные суперпользователя:

    ```
    email: admin@admin.ru
    password: admin@admin.ru
    ```

### Настройка CI/CD

1. Файл workflow уже написан и находится в директории:

    ```
    foodgram/.github/workflows/main.yml
    ```

2. Для адаптации его к вашему серверу добавьте секреты в GitHub Actions:

    ```
    DOCKER_USERNAME                # имя пользователя в DockerHub
    DOCKER_PASSWORD                # пароль пользователя в DockerHub
    HOST                           # IP-адрес сервера
    USER                           # имя пользователя
    SSH_KEY                        # содержимое приватного SSH-ключа (cat ~/.ssh/id_rsa)
    SSH_PASSPHRASE                 # пароль для SSH-ключа

    TELEGRAM_TO                    # ID вашего телеграм-аккаунта (можно узнать у @userinfobot, команда /start)
    TELEGRAM_TOKEN                 # токен вашего бота (получить токен можно у @BotFather, команда /token, имя бота)
    ```

### Стек:
- Python 3.9.6
- Django 3.2.20
- Django REST Framework 3.14.0 
- PostgreSQL 13.0
- Nginx 1.21.3
- Gunicorn 21.2.0
- Docker

### Автор:
[Александра Ижетникова](https://github.com/sashulka25)
