# @Author : Coaixy
# @repo : https://www.github.com/coaixy/weiban-tool
import Utils
import time

# tenantCode UserId x-token userProjectId
tenantCode = 0
userId = ""
x_token = ""
userProjectId = ""
main = Utils.main(tenantCode, userId, x_token, userProjectId)
main.init()
finishIdList = main.getFinishIdList()
for i in main.getCourse():
    main.start(i)
    time.sleep(20)
    main.finish(finishIdList[i])
