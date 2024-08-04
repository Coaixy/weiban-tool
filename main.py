# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import WeiBanHelper
import encrypted
from WeiBanHelper import WeibanHelper
import json
import requests
import time
from PIL import Image

if __name__ == "__main__":
    school_name = input("请输入学校名:")
    tenant_code = WeibanHelper.get_tenant_code(school_name=school_name)
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
    ret = encrypted.login(payload)
    request_data = {"data": ret}

    text = requests.post(
        "https://weiban.mycourse.cn/pharos/login/login.do", data=request_data
    ).text
    print(text + "\n")
    json_data = json.loads(text)["data"]

    # 获取所有课的实例
    project_list = WeibanHelper.get_project_id(json_data["userId"], tenant_code, json_data["token"])
    project_index = 0
    for project_info in project_list:
        print(str(project_index) + "." + project_info["projectName"])
        project_index = project_index + 1
    project_index = 0
    project_index = int(input("请输入要刷的课程编号:"))
    project_id = project_list[project_index]["userProjectId"]
    # 实例化对象
    HelperInstance = WeibanHelper(
        tenant_code,
        json_data["userId"],
        json_data["token"],
        project_id,
    )
    print("加群讨论:https://jcdn.lawliet.ren/qrcode.jpg")
    print("开始运行")
    # 初始化
    HelperInstance.init()
    # 获取列表
    for chooseType in [2, 3]:
        finishIdList = HelperInstance.getFinishIdList(chooseType)
        num = len(finishIdList)
        index = 1
        for i in HelperInstance.getCourse(chooseType):
            print(f"{index} / {num}")
            HelperInstance.start(i)
            time.sleep(15)
            HelperInstance.finish(i, finishIdList[i])
            index = index + 1
    print("刷课完成")
    input("按任意键结束")
