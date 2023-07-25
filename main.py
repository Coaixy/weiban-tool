# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import Utils
import time
import json
import pyperclip

#通过Wrathion获取参数
data = json.loads(pyperclip.paste())
tenantCode = data['tenantCode']
userId = data['userId']
x_token = data['token']
userProjectId = data['userProjectId']
#实例化对象
main = Utils.main(tenantCode, userId, x_token, userProjectId)
#初始化
main.init()
#获取列表
finishIdList = main.getFinishIdList()
print("加群讨论:https://jcdn.lawliet.ren/qrcode.jpg")
print("开始运行")
for i in main.getCourse():
    main.start(i)
    time.sleep(15)
    main.finish(i,finishIdList[i])
print("刷课完成")
