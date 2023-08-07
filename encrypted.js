const CryptoJS = require('./crypto-js.min.js');
const initKey = 'xie2gg';
const keySize = 128;

/**
 * 生成密钥字节数组, 原始密钥字符串不足128位, 补填0.
 * @param {string} key - 原始 key 值
 * @return Buffer
 */
const fillKey = (key) => {
    const filledKey = Buffer.alloc(keySize / 8);
    const keys = Buffer.from(key);
    if (keys.length < filledKey.length) {
        filledKey.forEach((b, i) => { filledKey[i] = keys[i]; });
    }

    return filledKey;
};

/**
 * 定义加密函数
 * @param {string} data - 需要加密的数据, 传过来前先进行 JSON.stringify(data);
 * @param {string} key - 加密使用的 key
 */
const aesEncrypt = (data, key) => {
    /**
     * CipherOption, 加密的一些选项:
     *   mode: 加密模式, 可取值(CBC, CFB, CTR, CTRGladman, OFB, ECB), 都在 CryptoJS.mode 对象下
     *   padding: 填充方式, 可取值(Pkcs7, AnsiX923, Iso10126, Iso97971, ZeroPadding, NoPadding), 都在 CryptoJS.pad 对象下
     *   iv: 偏移量, mode === ECB 时, 不需要 iv
     * 返回的是一个加密对象
     */
    const cipher = CryptoJS.AES.encrypt(data, key, {
        mode: CryptoJS.mode.ECB,
        padding: CryptoJS.pad.Pkcs7,
        iv: ''
    });

    // 将加密后的数据转换成 Base64
    const base64Cipher = cipher.ciphertext.toString(CryptoJS.enc.Base64);

    // 处理 Android 某些低版的BUG
    const resultCipher = base64Cipher.replace(/\+/g, '-').replace(/\//g, '_');

    // 返回加密后的经过处理的 Base64
    return resultCipher;
};

// 获取填充后的key
const key = CryptoJS.enc.Utf8.parse(fillKey(initKey));


function getKey(keyNumber, password, tenantCode, time, verifyCode) {
    return aesEncrypt(JSON.stringify({
        keyNumber: keyNumber,
        password: password,
        tenantCode: tenantCode,
        time: time,
        verifyCode: verifyCode
    }), key);
}