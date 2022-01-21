# Методы решения распространенных проблем
### ERROR: MICROSOFT VISUAL C++ 14.0 IS REQUIRED
https://stackoverflow.com/questions/44951456/pip-error-microsoft-visual-c-14-0-is-required

### ПРОБЛЕМЫ С БИБЛИОТЕКОЙ CRYPTO
`py -m pip uninstall crypto`
`py -m pip uninstall pycrypto`
`py -m pip install --force-reinstall pycryptodome`

### REQUESTS TIMEOUT
1. Убедиться в том, что https://lolz.guru не лежит
1. Зайти в файл settings.json и проверить значение поля `proxy type`

   `proxy type = 0`
   - Меняем айпи адрес машины, на которой находится скрипт вашего бота (подключение Proxy/TOR'a/VPN)

   `proxy type = 1`
   - Вероятнее всего, лолз перебанил генерируемые выходные ноды. Подключаем (`proxy_pool`) или выключаем режим проксирования.
 
   `proxy type = 2`
   - Подключаем в пул новые прокси или выключаем режим проксирования
