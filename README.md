Вступайте в чатик гиттера [![Gitter](https://badges.gitter.im/lolz-autocontest/community.svg)](https://gitter.im/lolz-autocontest/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge) там я буду писать о прогрессе по обновлениям и там можно говорить слова с людьми

## Преимущества
- Работает без эмуляции браузера
- Работает без нейронных сетей с примерно 95% правильных решений
- Бесплатно, в отличии от версии waslost

## Donate
В отличии от некоторых я все таки делаю бесплатно, Задонатьте или помайните на кошельки пж)

Принимаю пока только крипту. Bincoin/btc и Ethereum/eth не подходят из-за конских комиссий.

Могу добавить другие валюты если нужно.

- Monero/xmr: 85s5WnUGQUBYHK5RrfL5DKfazQiCUUaiiDspNMGGVYYj4zKxoUyxcbEheYBSNTAGoReF8VT7iAWAXcfV3YVca6TKBtt5dB4
- Zcash/zec: zs1uym38kghvpy7v0gkruqmg79030qw42xwzttavfxrqd9e8p7kf0v5sk4tdt6x8e8r4tnpztapmjn
- Dash/dash: XkyFZAYpYmjcU72R54EskKKSs8R3iGZ8Vy
- Bitcoin cash/bch: qp2kty2330sd6vgcsu8aggrm3clkydzscgwd29paa8
- vertcoin/vtc: vtc1qe6gjlpaqnlvygnw2xtuf09ph5a66yarng4mhx2

## Перед написанием сообщения в 'issues' Остановись!
В выводе программы находятся личные данные и данные от аккаунта, перед тем как скопировать и вставить лог посмотри нет ли в нем чего либо.

Альтернативно можно мне в [лс в gitter](https://gitter.im/acuifex/) прислать лог. Сразу скажу что мне ваших аккаунтов не нужно, даже если у вас там 20к на балансе

# Установка и запуск

### ubuntu
1. Скачиваем и устанавливаем python3, pip3 и git `sudo apt install python3 python3-pip git`
1. Устанавливаем и запускаем тор `sudo apt install tor; sudo systemctl start tor` (Опционально но чрезвычайно рекомендую т.к. айпишники банят)
1. Скачиваем и переходим в репозиторий `git clone https://github.com/acuifex/lolz-autocontest; cd lolz-autocontest`
1. Устанавливаем пакеты нужные для работы.
`pip3 install -U -r requirements.txt`
1. Переименовываем settings.example.json в settings.json и редактируем в соответствии с секцией [Настройки](#Настройки)
1. Запускаем в заднем фоне `bash ./start-background.sh`

Остановить потом можно с помощью `bash ./stop-background.sh`

### shindows
1. Скачиваем и устанавливаем python3 и pip3 (Не тупые, разберетесь)
1. Нажимаем Code -> Download ZIP чтобы скачать репозиторий
1. Распаковываем куда удобно
1. Открываем cmd
1. Меняем директорию в папку с распакованным репозиторием <br> 
`cd C:\Path\To\repo` <br>
место `C:\Path\To\repo` естественно пишем путь к распакованному репозиторию
1. Устанавливаем пакеты нужные для работы.
`py -m pip install -U -r requirements.txt` <br>
1. Переименовываем settings.example.json в settings.json и редактируем в соответствии с секцией [Настройки](#Настройки)
1. Запускаем `py main.py`

# Обновление

### ubuntu
1. `cd lolz-autocontest`
1. `git pull`
1. `pip3 install -U -r requirements.txt`
1. Проверяем то что ваш `settings.json` совместим с новым `settings.example.json`. Обновляем если не совместим.

### shindows
1. `cd C:\Path\To\repo` <br>
   место `C:\Path\To\repo` естественно пишем путь к распакованному репозиторию
1. Как то получаете новый репозиторий. Например скачиваете и перезаписываете файлы
1. `py -m pip install -U -r requirements.txt`
1. Проверяем то что ваш `settings.json` совместим с новым `settings.example.json`. Обновляем если не совместим.

# Настройки
- `users`: Список объектов пользователей в виде Имя:Параметры, несколько аккаунтов указываются через запятую
  - `User-Agent`: Юзер агент который аккаунт будет использовать ([Получение значения](#Получение-юзер-агента))
  - `monitor_size_x`: Размер монитора по горизонтали
  - `monitor_size_y`: Размер монитора по вертикали
  - `cookies`: Список кук которые аккаунт будет использовать
    - `xf_user`: Кука аккаунта ([Получение значения](#Получение-кук))
    - `xf_tfa_trust`: (опционально) Кука двухфакторной авторизации ([Получение значения](#Получение-кук))
  - `proxy_pool`: Список проксей которые будут использоваться аккаунтом (только при `proxy_type` = 2)
- `proxy_type`: Какой вид проксирования будет использоваться всеми аккаунтами. 0 = отключено, 1 = tor на порте 9050, 2 = индивидуальный список проксей (`proxy_pool`)
- `lolz_domain`: Домен который lolzteam сейчас использует
- `lolz_google_key`: google recaptcha v2 key
- `anti_captcha_key`: Ключ для captcha.guru. Реферал: https://captcha.guru/ru/reg/?ref=109978
- `send_referral_to_creator`: Отправлять ли 1-10% реферала за капчу автору? (Никаких негативных последствий для вас нету) <br> 
  Еще пожалуйста используйте реферал: https://captcha.guru/ru/reg/?ref=109978
- `found_count`: Если есть новый розыгрыш, проверять розыгрыши каждые `low_time` секунд `found_count` раз. Это сделано на случай спама розыгрышами
- `low_time`: Проверять каждые `low_time` секунд если нашелся новый розыгрыш
- `high_time`: Проверять каждые `high_time` секунд если нету новых розыгрышей
- `switch_time`: Подождать `switch_time` секунд между розыгрышами
- `solve_time`: "Проходить" розыгрыш `solve_time` секунд

# Получение юзер агента
1. Заходим на https://www.whatsmyua.info/
1. Копируем свой юзер агент ниже `Enter a user-agent string:` (в моем случае это `Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0`)
1. Изменяем `User-Agent` на свой юзер агент

# Получение кук
Если у вас нету `xf_tfa_trust` то не паникуем, его может не быть, удаляем эту строку и запятую с предыдущей строки.

Для firefox:
1. Нажимаем f12 на вкладке lolz.guru
1. Открываем вкладку Хранилище
1. Раскрываем меню Куки
1. Нажимаем https://lolz.guru
1. Заполняем xf_user и xf_tfa_trust в наших [настройках](#Настройки)

Для chrome:
1. Нажимаем f12 на вкладке lolz.guru
1. Открываем вкладку Application (Она может быть спрятана в ">>")
1. Раскрываем меню Cookies
1. Нажимаем https://lolz.guru
1. Заполняем xf_user и xf_tfa_trust в наших [настройках](#Настройки)

# Known issues
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
* mark это waslost, У него подгорело с того что я свой софт сделал :peka:
![](https://i.imgur.com/cw1O6B8.png)
![](https://i.imgur.com/d4LQBuR.png)
* А ну и еще всех обнулили впизду за просто так :like:
