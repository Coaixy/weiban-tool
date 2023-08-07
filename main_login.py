# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import Utils
import time
import json
import execjs
import requests
import time
from PIL import Image


def get_project_id(user_id, tenant_code, token: str) -> str:
    url = "https://weiban.mycourse.cn/pharos/index/listMyProject.do"
    headers = {
        "X-Token": token,
        "ContentType": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82",
    }
    data = {"tenantCode": tenant_code, "userId": user_id, "ended": 2}
    text = requests.post(url=url, headers=headers, data=data).text
    data = json.loads(text)["data"]
    if len(data) <= 0:
        print("已完成全部")
        exit(1)
    else:
        return data[0]["userProjectId"]


def read_js_file() -> str:
    f = open("encrypted.js", "r", encoding="utf-8")  # 打开JS文件
    line = f.readline()
    htmlstr = ""
    while line:
        htmlstr = htmlstr + line
        line = f.readline()
    return htmlstr


def get_tenant_code(school_name: str) -> str:
    tenant_list = requests.get(
        "https://weiban.mycourse.cn/pharos/login/getTenantListWithLetter.do"
    ).text
    data = json.loads(tenant_list)["data"]
    for i in data:
        for j in i["list"]:
            if j["name"] == school_name:
                return j["code"]


school_name = input("请输入学校名:")
tenant_code = get_tenant_code(school_name=school_name)
user_key = input("请输入账号:")
user_pwd = input("请输入密码:")
now = time.time()
print("验证码链接:")
print(f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}")
#打开验证码
img_data = requests.get(f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}").content
with open("code.jpg", "wb") as file:
    file.write(img_data)
file.close()
Image.open("code.jpg").show()
# 读取JS文件
jsstr = read_js_file()
# cwd需要替换为自己的Node modules目录
JsObj = execjs.compile(jsstr)  # 加载JS文件
# 获取验证码
verity_code = input("请输入验证码:")
# 调用js方法
ret = JsObj.call("getKey", user_key, user_pwd, tenant_code, now, verity_code)
request_data = {"data": ret}

text = requests.post(
    "https://weiban.mycourse.cn/pharos/login/login.do", data=request_data
).text
print(text)
json_data = json.loads(text)["data"]


# 实例化对象
main = Utils.main(
    tenant_code,
    json_data["userId"],
    json_data["token"],
    get_project_id(json_data["userId"], tenant_code, json_data["token"]),
)
# 初始化
main.init()
# 获取列表
finishIdList = main.getFinishIdList()
print("加群讨论:https://jcdn.lawliet.ren/qrcode.jpg")
print("开始运行")
for i in main.getCourse():
    main.start(i)
    time.sleep(15)
    main.finish(i, finishIdList[i])
print("刷课完成")
input("按任意键结束")
