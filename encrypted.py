# From https://github.com/JefferyHcool/weibanbot/blob/main/enco.py
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad
import base64


def fill_key(key):
    key_size = 128
    filled_key = key.ljust(key_size // 8, b'\x00')
    return filled_key


def aes_encrypt(data, key):
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    base64_cipher = base64.b64encode(ciphertext).decode('utf-8')
    result_cipher = base64_cipher.replace('+', '-').replace('/', '_')
    return result_cipher


def login(payload):
    init_key = 'xie2gg'
    key = fill_key(init_key.encode('utf-8'))

    encrypted = aes_encrypt(
        f'{{"keyNumber":"{payload["userName"]}","password":"{payload["password"]}","tenantCode":"{payload["tenantCode"]}","time":{payload["timestamp"]},"verifyCode":"{payload["verificationCode"]}"}}',
        key
    )

    # returned_encrypted = aes_encrypt(
    #     f'{{"keyNumber":"{payload["userName"]}","password":"{payload["password"]}","time":{payload["timestamp"]},"verifyCode":"{payload["captchaCode"]}"}}',
    #     key
    # )

    return encrypted
    # You can add logic for different payload.entry values here
