# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import WeiBanHelper
import json
import requests
import time
from PIL import Image

import encrypted


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
        # return data[0]["userProjectId"]
        return data


def get_tenant_code(school_name: str) -> str:
    tenant_list = requests.get(
        "https://weiban.mycourse.cn/pharos/login/getTenantListWithLetter.do"
    ).text
    data = json.loads(tenant_list)["data"]
    for i in data:
        for j in i["list"]:
            if j["name"] == school_name:
                return j["code"]


if __name__ == "__main__":
    school_name = input("请输入学校名:")
    tenant_code = get_tenant_code(school_name=school_name)
    user_key = input("请输入账号:")
    user_pwd = input("请输入密码:")
    now = time.time()
    print("验证码链接:")
    print(f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}")
    # 打开验证码
    img_data = requests.get(
        f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={now}"
    ).content
    with open("code.jpg", "wb") as file:
        file.write(img_data)
    file.close()
    Image.open("code.jpg").show()
    # 获取验证码
    verity_code = input("请输入验证码:")
    # 调用js方法
    payload = {
        "userName": user_key,
        "password": user_pwd,
        "tenantCode": tenant_code,
        "timestamp": now,
        "verificationCode": verity_code,
    }
    ret = enco.login(payload)
    request_data = {"data": ret}

    text = requests.post(
        "https://weiban.mycourse.cn/pharos/login/login.do", data=request_data
    ).text
    print(text + "\n")
    json_data = json.loads(text)["data"]

    # 获取所有课的实例
    project_list = get_project_id(json_data["userId"], tenant_code, json_data["token"])
    project_index = 0
    for project_info in project_list:
        print(str(project_index) + "." + project_info["projectName"])
        project_index = project_index + 1
    project_index = 0
    project_index = int(input("请输入要刷的课程编号:"))
    project_id = project_list[project_index]["userProjectId"]
    # 实例化对象
    main = Utils.WeibanHelper(
        tenant_code,
        json_data["userId"],
        json_data["token"],
        project_id,
    )
    print("加群讨论:https://jcdn.lawliet.ren/qrcode.jpg")
    print("开始运行")
    # 初始化
    main.init()
    # 获取列表
    for chooseType in [2, 3]:
        finishIdList = main.getFinishIdList(chooseType)
        num = len(finishIdList)
        index = 1
        for i in main.getCourse(chooseType):
            print(f"{index} / {num}")
            main.start(i)
            time.sleep(15)
            main.finish(i, finishIdList[i])
            index = index + 1
    print("刷课完成")
    input("按任意键结束")
