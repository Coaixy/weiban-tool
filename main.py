# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import json
import sys

import WeiBanHelper

if __name__ == "__main__":
    print("""
                                                                                                         
  _/          _/            _/  _/_/_/                                _/_/_/_/_/                    _/   
 _/          _/    _/_/        _/    _/    _/_/_/  _/_/_/                _/      _/_/      _/_/    _/    
_/    _/    _/  _/_/_/_/  _/  _/_/_/    _/    _/  _/    _/  _/_/_/_/_/  _/    _/    _/  _/    _/  _/     
 _/  _/  _/    _/        _/  _/    _/  _/    _/  _/    _/              _/    _/    _/  _/    _/  _/      
  _/  _/        _/_/_/  _/  _/_/_/      _/_/_/  _/    _/              _/      _/_/      _/_/    _/       
                                                                                                         
                                                                                                         
    """)
    exit(1)
    # 基础信息
    account = ""
    password = ""
    school_name = ""

    arguments = sys.argv[1:]
    if len(arguments) == 0:
        account = input("请输入账号: ")
        password = input("请输入密码: ")
        school_name = input("请输入学校名称: ")
    elif len(arguments) >= 3:
        account = arguments[0]
        password = arguments[1]
        school_name = arguments[2]
    Instance = WeiBanHelper.WeibanHelper(account=account, password=password, school_name=school_name, auto_verify=False,
                                         project_index=0)
    for index, value in enumerate(Instance.project_list):
        print(index, " - ", value['projectName'])
    project_index = 0
    if len(arguments) == 0:
        project_index = int(input("请输入项目编号: "))
        Instance.userProjectId = Instance.project_list[project_index]['userProjectId']
    if len(arguments) == 4:
        project_index = int(arguments[3])
        Instance.userProjectId = Instance.project_list[project_index]['userProjectId']
    print("当前项目名称: ", Instance.project_list[project_index]['projectName'])
    Instance.run()
