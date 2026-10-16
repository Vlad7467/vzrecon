# vzrecon

```

██╗   ██╗███████╗██╗      ██████╗ ██╗
██║   ██║╚══███╔╝██║     ██╔═══██╗██║
██║   ██║  ███╔╝ ██║     ██║   ██║██║
╚██╗ ██╔╝ ███╔╝  ██║     ██║   ██║██║
╚████╔╝ ███████╗███████╗╚██████╔╝██║
╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝
VZLOI GROUP // ops
no gods, no masters, no logs

```

Валидатор прокси на уровне протокола. HTTP, SOCKS4, SOCKS5.
Без зависимостей. Работает в Termux.

Сборка: **VZLOI GROUP**, дивизион ops, Москва.

## Установка

    pip install vzrecon

    vzrecon --self-test

## Использование

    vzrecon                          # скан папки на *_proxies.txt
    vzrecon -d ./lists -o ./out      # явные пути
    vzrecon --preset stealth         # 200 воркеров
    vzrecon --preset turbo           # 2400 воркеров
    vzrecon --only http,socks5
    vzrecon --verify                 # реальный запрос через туннель
    vzrecon --plain

## Протоколы

- **HTTP** — RFC 7231 §4.3.6, CONNECT, откат на forward-GET
- **SOCKS5** — RFC 1928, no-auth приветствие, доменный ATYP
- **SOCKS4** — оригинал, IPv4, резолв на клиенте

## --verify

Handshake недостаточно: прокси может принять CONNECT и не
форвардить трафик. Whitelist, auth на первом пакете, rate-limit.

С `--verify` после handshake идёт реальный HTTP через туннель.
Отсеивает 30-70% от того, что handshake пропустил как живое.

## Вывод

- `<протокол>_alive.txt` — endpoint на строку
- `<протокол>_alive.json` — с `signed_by`, `motto`, `origin`
- `<протокол>_alive.csv` — endpoint, latency_ms

## Коды выхода

    0  скан завершён
    1  self-test упал
    2  ошибка конфига
    3  нет исходных файлов

## Termux

- Wake-lock на старте, релиз в finally
- Уведомление по завершению через termux-notification
- Пресеты под процессор телефона и батарею

`pkg install termux-api` для уведомлений.

## VZLOI GROUP

`docs/VZLOI.md`.

Не пиши нам. Не ищи нас. Мы найдём первыми.

## Лицензия

MIT. Copyright (c) 2026 VZLOI GROUP.
