## Donate
В отличии от некоторых я все таки делаю бесплатно, Задонатьте пж)

Принимаю только крипту. Bincoin/btc и Ethereum/eth не подходят из-за конских комиссий.

Могу добавить другие валюты если нужно.

monero/xmr: 85s5WnUGQUBYHK5RrfL5DKfazQiCUUaiiDspNMGGVYYj4zKxoUyxcbEheYBSNTAGoReF8VT7iAWAXcfV3YVca6TKBtt5dB4
## Установка и запуск

#### ubuntu
1. Скачиваем и устанавливаем python3, pip3 и git `sudo apt install python3 python3-pip git`
1. Устанавливаем и запускаем тор `sudo apt install tor; sudo systemctl start tor` (Опционально но черезвычайно рекомендую т.к. айпишники банят)
1. Скачиваем и переходим в репозиторий `git clone https://github.com/acuifex/lolz-autocontest; cd lolz-autocontest`
1. Устанавливаем пакеты нужные для работы.
`pip3 install -r requirements.txt`
1. Редактируем tor_based.py в соответствии с секцией [Настройка](#Настройка)
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
1. Редактируем tor_based.py в соответствии с секцией [Настройка](#Настройка)
1. Запускаем `python tor_based.py`

## Настройка
`found_count`, `low_time` и `high_time` пояснены на месте. Если не понимаете то не трогайте.
#### Tor
`torproxy` Оставляем на `True` если запущен тор на порту 9050.

Если не запущен или вы шиндофс юзер то меняем на `False`

#### Куки
Прошу заметить что куки живут где то месяц. Если перестало работать - меняем куки

Для firefox:
1. Нажимаем f12 на вкладке lolz.guru
1. Открываем вкладку Хранилище
1. Раскрываем меню Куки
1. Нажимаем https://lolz.guru
1. Заполняем `users` в соответствии Имя: Значение

Для chrome:
1. Нажимаем f12 на вкладке lolz.guru
1. Открываем вкладку Application (Она может быть спрятана в ">>")
1. Раскрываем меню Cookies
1. Нажимаем https://lolz.guru
1. Заполняем `users` в соответствии Name: Value


##### И ДОБАВЛЯЕМ СВОЙ ЮЗЕР АГЕНТ (ВАЖНО!!)
1. Заходим на https://www.whatsmyua.info/
1. Копируем свой юзер агент ниже `Enter a user-agent string:` (в моем случае это `Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0`)
1. Заменяем строку правее `User-Agent` на свой юзер агент


## Разные мемусы

* капча
* ![](https://i.imgur.com/HBUGQbo.jpg)
* ![](https://i.imgur.com/7YRO68Z.jpg)
* ![](https://i.imgur.com/Sat30qW.jpg)
* mark это waslost, У него подгорело с того что я свой софт сделал :peka:
![](https://i.imgur.com/cw1O6B8.png)
![](https://i.imgur.com/d4LQBuR.png)
* А ну и еще всех обнулили впизду за просто так :like:
