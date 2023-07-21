# Автоучастие для lolzteam

Вступайте в наш [Discord!](https://discord.gg/ZhzmeVeGT7)

## Donate

Если нужен какой-то другой вариант, то пишите в Discord

- Monero/xmr: 85s5WnUGQUBYHK5RrfL5DKfazQiCUUaiiDspNMGGVYYj4zKxoUyxcbEheYBSNTAGoReF8VT7iAWAXcfV3YVca6TKBtt5dB4
- Zcash/zec: zs1uym38kghvpy7v0gkruqmg79030qw42xwzttavfxrqd9e8p7kf0v5sk4tdt6x8e8r4tnpztapmjn
- Dash/dash: XkyFZAYpYmjcU72R54EskKKSs8R3iGZ8Vy
- Bitcoin cash/bch: qp2kty2330sd6vgcsu8aggrm3clkydzscgwd29paa8
- vertcoin/vtc: vtc1qe6gjlpaqnlvygnw2xtuf09ph5a66yarng4mhx2

## Перед тем как передать логи Остановись!

В выводе программы находятся личные данные и данные от аккаунта.
Перед тем как скопировать и вставить лог, посмотри нет ли в нем данных аккаунта или персональных данных.

## Установка и запуск

### Ubuntu

1. Скачиваем и устанавливаем python3, pip3 и git `sudo apt install python3 python3-pip git`
2. Устанавливаем и запускаем тор `sudo apt install tor; sudo systemctl start tor` (Опционально, но чрезвычайно рекомендую т.к. айпишники банят)
3. Скачиваем и переходим в репозиторий `git clone https://github.com/acuifex/lolz-autocontest; cd lolz-autocontest`
4. Устанавливаем пакеты нужные для работы.
`pip3 install -U -r requirements.txt`
5. Переименовываем `settings.example.yaml` в `settings.yaml` и редактируем в соответствии с секцией [Настройки](#Настройки)
6. Запускаем в заднем фоне `bash ./start.sh`

Так же можно запускать в заднем фоне `bash ./start-background.sh` и останавливать `bash ./stop-background.sh`

### Windows

1. Скачиваем и устанавливаем python3 и pip3 (Не тупые, разберетесь)
2. Нажимаем Code -> Download ZIP чтобы скачать репозиторий
3. Распаковываем куда удобно
4. Открываем cmd
5. Меняем директорию в папку с распакованным репозиторием <br> 
`cd C:\Path\To\repo` <br>
место `C:\Path\To\repo` естественно пишем путь к распакованному репозиторию
6. Устанавливаем пакеты нужные для работы.
`py -m pip install -U -r requirements.txt` <br>
7. Переименовываем `settings.example.yaml` в `settings.yaml` и редактируем в соответствии с секцией [Настройки](#Настройки)
8. Запускаем `py main.py`

## Обновление

### Ubuntu

1. `cd lolz-autocontest`
2. `git pull`
3. `pip3 install -U -r requirements.txt`
4. Проверяем то что ваш `settings.yaml` совместим с новым `settings.example.yaml`. Обновляем если не совместим.

### Windows

1. `cd C:\Path\To\repo` <br>
   место `C:\Path\To\repo` естественно пишем путь к распакованному репозиторию
2. Как то получаете новый репозиторий. Например, скачиваете и перезаписываете файлы
3. `py -m pip install -U -r requirements.txt`
4. Проверяем то что ваш `settings.yaml` совместим с новым `settings.example.yaml`. Обновляем если не совместим.

## Настройки

- `users`: Список аккаунтов которые будут использоваться
  - `name`: Название аккаунта. Это значение никак не передается лолзу
  - `user_agent`: Юзер агент который аккаунт будет использовать ([Получение значения](#Получение-юзер-агента))
  - `cookies`: Список кук которые аккаунт будет использовать
    - `xf_session`: Кука аккаунта ([Получение значения](#Получение-кук))
    - `xf_tfa_trust`: (опционально) Кука двухфакторной авторизации ([Получение значения](#Получение-кук))
  - `proxy_pool`: Список проксей которые будут использоваться аккаунтом (только при `proxy_type` = 2)
- `proxy_type`: Какой вид проксирования будет использоваться всеми аккаунтами. 0 = отключено, 1 = tor на порте 9050, 2 = индивидуальный список проксей (`proxy_pool`)
- `lolz_domain`: Домен который lolzteam сейчас использует
- `found_count`: Если есть новый розыгрыш, проверять розыгрыши каждые `low_time` секунд `found_count` раз. Это сделано на случай спама розыгрышами
- `low_time`: Проверять каждые `low_time` секунд если нашелся новый розыгрыш
- `high_time`: Проверять каждые `high_time` секунд если нет новых розыгрышей
- `switch_time`: Подождать `switch_time` секунд между розыгрышами
- `solve_time`: "Проходить" розыгрыш `solve_time` секунд
- `anti_captcha_key`: Ключ от captcha.guru. Сервис стоит 30р за 1000 решений ( используйте мой реферал! https://captcha.guru/ru/reg/?ref=109978 )
- `site_key`: Turnsile ключ вебсайта для лолза. Если не понимаете зачем это, то не меняйте
- `send_referral_to_creator`: Отсылать ли реферал автору

## Получение юзер агента

1. Заходим на https://www.whatsmyua.info/
2. Копируем свой юзер агент ниже `Enter a user-agent string:` (в моем случае это `Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0`)
3. Изменяем `user_agent` на свой юзер агент

## Получение кук

Если у вас нет `xf_tfa_trust` то не паникуем, его может не быть. Удаляем эту строку

### Firefox

1. Нажимаем f12 на вкладке lolz.guru
2. Открываем вкладку Хранилище
3. Раскрываем меню Куки
4. Нажимаем https://lolz.guru
5. Заполняем `xf_session` и `xf_tfa_trust` в наших [настройках](#Настройки)

### Chrome

1. Нажимаем f12 на вкладке lolz.guru
2. Открываем вкладку Application (Она может быть спрятана в ">>")
3. Раскрываем меню Cookies
4. Нажимаем https://lolz.guru
5. Заполняем `xf_session` и `xf_tfa_trust` в наших [настройках](#Настройки)

## Known issues

- При каком-то стечении обстоятельств лолз после js запроса удаляет xf_users и xf_logged_in. Прога при этом ничего не пишет кроме loop at. Возможно невалид кука?
- Memory leak
- (Now slightly less) shit code

# Разные мемусы

* ![](https://i.imgur.com/0x6tQS2.png)
* ![](https://i.imgur.com/gny8CLz.png)
* ![](https://i.imgur.com/OXg6MzD.png)
* ![](https://i.imgur.com/O54NEHp.png)
* ![](https://i.imgur.com/s5B7O5a.png)
* ![](https://i.imgur.com/HBUGQbo.jpg)
* ![](https://i.imgur.com/7YRO68Z.jpg)
* ![](https://i.imgur.com/Sat30qW.jpg)
* mark это waslost.
![](https://i.imgur.com/cw1O6B8.png)
![](https://i.imgur.com/d4LQBuR.png)
* А ну и еще всех обнулили впизду
