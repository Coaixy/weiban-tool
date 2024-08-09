# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import sys

import WeiBanHelper

if __name__ == "__main__":
    # 基础信息
    account = ""
    password = ""
    school_name = ""

    arguments = sys.argv[1:]
    if len(arguments) == 0:
        account = input("请输入账号: ")
        password = input("请输入密码: ")
        school_name = input("请输入学校名称: ")
    elif len(arguments) == 3:
        account = arguments[0]
        password = arguments[1]
        school_name = arguments[2]

    Instance = WeiBanHelper.WeibanHelper(account=account, password=password, school_name=school_name, auto_verify=False,
                                         class_index=0)

