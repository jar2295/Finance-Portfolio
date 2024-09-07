from configparser import ConfigParser

config = ConfigParser()

config.add_section("main")
config.set("main", 'CLIENT_ID', "")
config.set("main", 'HOST', "")
config.set("main", 'JSON_PATH', "")
config.set("main", 'ACCOUNT_NUMBER', "")

with open('config.ini', 'w') as f:
          config.write(f)