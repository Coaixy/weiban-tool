# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import json
import os
import sys
import uuid
import re

import requests


import QuestionBank.QuestionBank as Questio
import WeiBanHelper


def print_help_info():
    print("使用方法: python main.py [account] [password] [school_name] [auto_verify] [project_index] [auto_exam]")
    print("使用方法: python main.py 进入纯手动输入模式")
    print("account: 账号")
    print("password: 密码")
    print("school_name: 学校名称")
    print("auto_verify: 是否自动验证, 0: 不自动验证, 1: 自动验证")
    print("project_index: 课程编号")
    print("auto_exam: 是否自动考试 0: 不自动考试, >0 : 考试时间(单位秒)：")
    print("exam_threshold: 允许错的题目数：")
    print()


if __name__ == "__main__":
    print("""
                                                                                                         
  _/          _/            _/  _/_/_/                                _/_/_/_/_/                    _/   
 _/          _/    _/_/        _/    _/    _/_/_/  _/_/_/                _/      _/_/      _/_/    _/    
_/    _/    _/  _/_/_/_/  _/  _/_/_/    _/    _/  _/    _/  _/_/_/_/_/  _/    _/    _/  _/    _/  _/     
 _/  _/  _/    _/        _/  _/    _/  _/    _/  _/    _/              _/    _/    _/  _/    _/  _/      
  _/  _/        _/_/_/  _/  _/_/_/      _/_/_/  _/    _/              _/      _/_/      _/_/    _/       
                                                                                                         
                                                                                                         
    """)
    if len(sys.argv) == 2 and sys.argv[1] == "help":
        print_help_info()
    # 基础信息
    account = ""
    password = ""
    school_name = ""
    auto_verify = True
    auto_exam = False
    exam_threshold = 1

    arguments = sys.argv[1:]
    if len(arguments) == 0:
        account = input("请输入账号: ")
        password = input("请输入密码: ")
        while True:
            school_name = input("请输入学校名称：")
            if re.fullmatch(r'[\u4e00-\u9fa5]+', school_name):
                break
            else:
                print("学校名称无效，仅允许中文字符，如果终端无法输入，请在外面输入，并复制粘贴到这里")

    Instance = WeiBanHelper.WeibanHelper(account=account, password=password, school_name=school_name,
                                         auto_verify=auto_verify,
                                         project_index=0)
    print("\n编号 -  课程\n-----------------------")
    for index, value in enumerate(Instance.project_list):
        print(index, "   - ", value['projectName'])
    print("\n")
    project_index = 0
    if len(arguments) == 0:
        if len(Instance.project_list) == 1:
            project_index = int(input("已经识别到唯一项目, 请直接输入“0”开始执行: "))
        else:
            project_index = int(input("请输入项目编号: "))
        Instance.userProjectId = Instance.project_list[project_index]['userProjectId']
        auto_exam = int(input("是否自动考试: 0: 不自动考试, >0 : 考试时间(单位秒)"))
        if auto_exam >= 1:
            exam_threshold = int(input("允许错的题目数（如填0是一题不错，填1是可以错一题）: "))
    if 0 < len(arguments) < 6:
        print_help_info()
        exit(0)
    if len(arguments) == 7:
        account = arguments[0]
        password = arguments[1]
        school_name = arguments[2]
        auto_verify = bool(arguments[3])
        project_index = int(arguments[4])
        auto_exam = int(arguments[5])
        exam_threshold = int(arguments[6])

    print("当前项目名称: ", Instance.project_list[project_index]['projectName'])
    Instance.run()
    if auto_exam > 0:
        index = 0
        tenant_code = Instance.get_tenant_code(school_name)
        answer_list = Instance.getAnswerList()
        if len(answer_list) == 0 or answer_list is None:
            print("未获取到答案")
        else:
            for answer in answer_list:
                index = index + 1
                with open(f"QuestionBank/{tenant_code}-{account}-{str(index)}.json", 'w',
                          encoding='utf-8') as f:
                    f.write(answer)
            print("答案已保存到QuestionBank文件夹")
        QuestionBank.generate_bank(directory=os.getcwd() + "/QuestionBank")
        print("开始自动考试")
        Instance.finish_exam_time = auto_exam
        Instance.exam_threshold = exam_threshold
        Instance.autoExam()
