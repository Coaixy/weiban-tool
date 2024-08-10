# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import json
import sys
import uuid

import requests

import WeiBanHelper

if __name__ == "__main__":
    print("""
                                                                                                         
  _/          _/            _/  _/_/_/                                _/_/_/_/_/                    _/   
 _/          _/    _/_/        _/    _/    _/_/_/  _/_/_/                _/      _/_/      _/_/    _/    
_/    _/    _/  _/_/_/_/  _/  _/_/_/    _/    _/  _/    _/  _/_/_/_/_/  _/    _/    _/  _/    _/  _/     
 _/  _/  _/    _/        _/  _/    _/  _/    _/  _/    _/              _/    _/    _/  _/    _/  _/      
  _/  _/        _/_/_/  _/  _/_/_/      _/_/_/  _/    _/              _/      _/_/      _/_/    _/       
                                                                                                         
                                                                                                         
    """)
    if len(sys.argv) == 2 and sys.argv[1] == "help":
        print("使用方法: python main.py [account] [password] [school_name] [auto_verify] [project_index] [auto_exam]")
        print("使用方法: python main.py 进入纯手动输入模式")
        print("account: 账号")
        print("password: 密码")
        print("school_name: 学校名称")
        print("auto_verify: 是否自动验证, 0: 不自动验证, 1: 自动验证")
        print("project_index: 课程编号")
        print("auto_exam: 是否自动考试 0: 不自动考试, 1: 自动考试")
        print()
    # 基础信息
    account = ""
    password = ""
    school_name = ""
    auto_verify = False
    auto_exam = False

    arguments = sys.argv[1:]
    if len(arguments) == 0:
        account = input("请输入账号: ")
        password = input("请输入密码: ")
        school_name = input("请输入学校名称: ")
    elif len(arguments) >= 4:
        account = arguments[0]
        password = arguments[1]
        school_name = arguments[2]
        auto_verify = True if int(arguments[3]) == 1 else False

    Instance = WeiBanHelper.WeibanHelper(account=account, password=password, school_name=school_name,
                                         auto_verify=auto_verify,
                                         project_index=0)
    for index, value in enumerate(Instance.project_list):
        print(index, " - ", value['projectName'])
    project_index = 0
    if len(arguments) == 0:
        project_index = int(input("请输入项目编号: "))
        Instance.userProjectId = Instance.project_list[project_index]['userProjectId']
        auto_exam = True if int(input("是否自动考试: 0: 不自动考试, 1: 自动考试")) == 1 else False
    if len(arguments) == 5:
        project_index = int(arguments[4])
        Instance.userProjectId = Instance.project_list[project_index]['userProjectId']
    if len(arguments) == 6:
        auto_exam = True if int(arguments[5]) == 1 else False
    print("当前项目名称: ", Instance.project_list[project_index]['projectName'])
    Instance.run()
    # for answer in Instance.getAnswerList():
    #     with open(f"QuestionBank/{uuid.uuid4()}.json", 'w') as f:
    #         f.write(answer)
    if auto_exam:
        print("开始自动考试")
        Instance.autoExam()
