## Преимущества
- Работает на запросах без браузерного мусора
- Чистая логика - никаких нейронок а значит практически 0 цп нагрузки
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

## Установка и запуск

#### ubuntu
1. Скачиваем и устанавливаем python3, pip3 и git `sudo apt install python3 python3-pip git`
1. Устанавливаем и запускаем тор `sudo apt install tor; sudo systemctl start tor` (Опционально но черезвычайно рекомендую т.к. айпишники банят)
1. Скачиваем и переходим в репозиторий `git clone https://github.com/acuifex/lolz-autocontest; cd lolz-autocontest`
1. Устанавливаем пакеты нужные для работы.
`pip3 install -r requirements.txt`
1. Переименовываем settings.example.json в settings.json и редактируем в соответствии с секцией [Настройка](#Настройка)
1. Запускаем в заднем фоне `nohup python3 -u tor_based.py > /dev/null 2>lolzautocontest-errors.log&`

Остановить потом можно с помощью `kill -n SIGKILL $(pgrep -f "python3 -u tor_based.py")`

#### shindows
`Python` возможно нужно поменять на `py`, я точно не помню как там у вас
1. Скачиваем и устанавливаем python3 и pip3 (Не тупые, разберетесь)
1. Нажимаем Code -> Download ZIP что бы скачать репозиторий
1. Распаковываем куда удобно
1. Открываем cmd
1. Меняем дерикторию в папку с распакованным репозиторием <br> 
`cd C:\Path\To\repo` <br>
место `C:\Path\To\repo` естественно пишем путь к распакованному репозиторию
1. Устанавливаем пакеты нужные для работы.
`python -m pip install -r requirements.txt` <br>
1. Переименовываем settings.example.json в settings.json и редактируем в соответствии с секцией [Настройка](#Настройка)
1. Запускаем `python tor_based.py`

## Настройка
### Аккаунты
Все аккаунты находятся в `users`, Несколько аккаунтов добавляем через запятую.

`"Название аккаунта": {*Данные*}`

#### ДОБАВЛЯЕМ СВОЙ ЮЗЕР АГЕНТ (ВАЖНО!!)
1. Заходим на https://www.whatsmyua.info/
1. Копируем свой юзер агент ниже `Enter a user-agent string:` (в моем случае это `Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0`)
1. Заменяем `User-Agent` внутри `"Название аккаунта"` на свой юзер агент

#### Куки
Прошу заметить что куки живут где то месяц (на деле может и больше). Если перестало работать - меняем куки

Если у вас нету `xf_tfa_trust` то не паникуем, его может не быть, удаляем эту строку и запятую с предыдущей строки.

Для firefox:
1. Нажимаем f12 на вкладке lolz.guru
1. Открываем вкладку Хранилище
1. Раскрываем меню Куки
1. Нажимаем https://lolz.guru
1. Заполняем `*Данные*` в `Название аккаунта` в соответствии Имя: Значение 

Для chrome:
1. Нажимаем f12 на вкладке lolz.guru
1. Открываем вкладку Application (Она может быть спрятана в ">>")
1. Раскрываем меню Cookies
1. Нажимаем https://lolz.guru
1. Заполняем `*Данные*` в `Название аккаунта` в соответствии Name: Value

### Тайминги
- `found_count` Если нашелся розыгрыш чекать розыгрыши каждые `low_time` секунд `found_count` раз
- `low_time` Чекать каждые `low_time` Секунд если нашелся новый розыгрыш
- `high_time` Чекать каждые `high_time` секунд если нету новых розыгрышей

### Tor
- `use_tor` `true` если запущен тор на порту `9050`, иначе (Вам скорее всего так и надо) меняем на `false`


## Разные мемусы

* ![](https://i.imgur.com/OXg6MzD.png)
* ![](https://i.imgur.com/O54NEHp.png)
* ![](https://i.imgur.com/s5B7O5a.png)
* капча
* ![](https://i.imgur.com/HBUGQbo.jpg)
* ![](https://i.imgur.com/7YRO68Z.jpg)
* ![](https://i.imgur.com/Sat30qW.jpg)
* mark это waslost, У него подгорело с того что я свой софт сделал :peka:
![](https://i.imgur.com/cw1O6B8.png)
![](https://i.imgur.com/d4LQBuR.png)
* А ну и еще всех обнулили впизду за просто так :like:
