import time
import requests
import json


class main:
    tenantCode = 0
    userId = ""
    x_token = ""
    userProjectId = ""
    headers = {'x-token': "",
               "User-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Mobile Safari/537.36 Edg/103.0.1264.77"
               }

    def __init__(self, code, id, token,projectId):
        self.tenantCode = code
        self.userId = id
        self.x_token = token
        self.userProjectId = projectId

    def init(self):
        self.headers['x-token'] = self.x_token

    def getProgress(self):
        url = "https://weiban.mycourse.cn/pharos/project/showProgress.do"
        data = {
            'userProjectId': self.userProjectId,
            'tenantCode': self.tenantCode,
            'userId': self.userId
        }
        response = requests.post(url, data=data, headers=self.headers)
        text = response.text
        data = json.loads(text)
        return data['data']['progressPet']

    def getCategory(self):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCategory.do"
        data = {
            'userProjectId': self.userProjectId,
            'tenantCode': self.tenantCode,
            'userId': self.userId,
            'chooseType': 3
        }
        response = requests.post(url, data=data, headers=self.headers)
        text = response.text
        data = json.loads(text)
        list = data['data']
        result = []
        for i in list:
            if i['totalNum'] > i['finishedNum']:
                result.append(i['categoryCode'])
        return result

    def getCourse(self):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do"
        result = []
        for i in self.getCategory():
            data = {
                'userProjectId': self.userProjectId,
                'tenantCode': self.tenantCode,
                'userId': self.userId,
                'chooseType': 3,
                'name': "",
                'categoryCode': i
            }
            response = requests.post(url, data=data, headers=self.headers)
            text = response.text
            data = json.loads(text)['data']
            for i in data:
                if i['finished'] == 2:
                    result.append(i['resourceId'])
        return result

    def getFinishIdList(self):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do"
        result = {}
        for i in self.getCategory():
            data = {
                'userProjectId': self.userProjectId,
                'tenantCode': self.tenantCode,
                'userId': self.userId,
                'chooseType': 3,
                'name': "",
                'categoryCode': i
            }
            response = requests.post(url, data=data, headers=self.headers)
            text = response.text
            data = json.loads(text)['data']
            for i in data:
                if i['finished'] == 2:
                    result[i['resourceId']] = i['userCourseId']
        return result


    def start(self,courseId):
        data = {
            'userProjectId': self.userProjectId,
            'tenantCode': self.tenantCode,
            'userId': self.userId,
            'courseId': courseId
        }
        headers = {
            "x-token":self.x_token
        }
        res = requests.post("https://weiban.mycourse.cn/pharos/usercourse/study.do",data=data,headers=headers)
        while json.loads(res.text)['code'] == -1:
            time.sleep(5)
            res = requests.post("https://weiban.mycourse.cn/pharos/usercourse/study.do",data=data,headers=headers)
        print("start:"+courseId)

    def finish(self,finishId):
        params = {
            "callback":"",
            "userCourseId":finishId,
            "tenantCode":self.tenantCode
        }
        url = "https://weiban.mycourse.cn/pharos/usercourse/finish.do"
        requests.get(url=url,params=params)
        print("finish:"+finishId)
