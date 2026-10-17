# vzrecon

Protocol-level proxy validator for HTTP, SOCKS4, and SOCKS5.

## Install
pip install vzrecon

## Usage
vzrecon --file proxies.txt --protocol http
vzrecon --file proxies.txt --protocol socks5 --json
vzrecon --self-test
