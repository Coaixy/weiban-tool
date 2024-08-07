import time
import requests
import json
import datetime
import random


class WeibanHelper:
    tenantCode = 0
    userId = ""
    x_token = ""
    userProjectId = ""
    headers = {
        "X-Token": "",
        "ContentType": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82",
    }

    tempUserCourseId = ""

    def __init__(self, code, id, token, projectId):
        self.tenantCode = code
        self.userId = id
        self.x_token = token
        self.userProjectId = projectId

    def init(self):
        self.headers["X-Token"] = self.x_token

    # 以下俩个方法来自https://github.com/Sustech-yx/WeiBanCourseMaster

    # js里的时间戳似乎都是保留了三位小数的.
    def __get_timestamp(self):
        return str(round(datetime.datetime.now().timestamp(), 3))

    # Magic: 用于构造、拼接"完成学习任务"的url
    # js: (jQuery-3.2.1.min.js)
    # f = '3.4.1'
    # expando = 'jQuery' + (f + Math.random()).replace(/\D/g, "")
    def __gen_rand(self):
        return ("3.4.1" + str(random.random())).replace(".", "")

    def getProgress(self):
        url = "https://weiban.mycourse.cn/pharos/project/showProgress.do"
        data = {
            "userProjectId": self.userProjectId,
            "tenantCode": self.tenantCode,
            "userId": self.userId,
        }
        response = requests.post(url, data=data, headers=self.headers)
        text = response.text
        data = json.loads(text)
        return data["data"]["progressPet"]

    def getAnswerList(self):
        answer_list = []
        url = "https://weiban.mycourse.cn/pharos/exam/reviewPaper.do?timestamp=" + self.__get_timestamp()
        exam_id_list = self.listHistory()
        for exam_id in exam_id_list:
            data = {
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamId": exam_id,
                "isRetake": "2"
            }
            response = requests.post(url, data=data, headers=self.headers)
            answer_list.append(response.text)
        return answer_list

    def listHistory(self):
        dataList = {}
        result = []
        url = "https://weiban.mycourse.cn/pharos/exam/listHistory.do?timestamp=" + self.__get_timestamp()
        exam_plan_id_list = self.listExamPlan()
        for exam_plan_id in exam_plan_id_list:
            dataList = {
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "examPlanId": exam_plan_id
            }
            response = requests.post(url, headers=self.headers, data=dataList)
            dataList = json.loads(response.text)['data']
        for data in dataList:
            result.append(data['id'])
        return result

    def listExamPlan(self):
        url = "https://weiban.mycourse.cn/pharos/record/project/listExamPlanStat.do?timestamp=" + self.__get_timestamp()
        data = {
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userProjectId": self.userProjectId
        }
        response = requests.post(url, headers=self.headers, data=data)
        exam_plan_id_list = []
        for exam_plan in json.loads(response.text)['data']:
            exam_plan_id_list.append(exam_plan['examPlanId'])
        return exam_plan_id_list

    def getCategory(self, chooseType):
        result = []
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCategory.do"
        data = {
            "userProjectId": self.userProjectId,
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "chooseType": chooseType,
        }
        response = requests.post(url, data=data, headers=self.headers)
        text = response.text
        data = json.loads(text)
        list = data["data"]
        for i in list:
            if i["totalNum"] > i["finishedNum"]:
                result.append(i["categoryCode"])
        return result

    def getCourse(self, chooseType):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do"
        result = []
        for i in self.getCategory(chooseType):
            data = {
                "userProjectId": self.userProjectId,
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "chooseType": chooseType,
                "name": "",
                "categoryCode": i,
            }
            response = requests.post(url, data=data, headers=self.headers)
            text = response.text
            data = json.loads(text)["data"]
            for i in data:
                if i["finished"] == 2:
                    result.append(i["resourceId"])
        return result

    def getFinishIdList(self, chooseType):
        url = "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do"
        result = {}
        for i in self.getCategory(chooseType):
            data = {
                "userProjectId": self.userProjectId,
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "chooseType": chooseType,
                "categoryCode": i,
            }
            response = requests.post(url, data=data, headers=self.headers)
            text = response.text
            data = json.loads(text)["data"]
            for i in data:
                if i["finished"] == 2:
                    if "userCourseId" in i:
                        result[i["resourceId"]] = i["userCourseId"]
                        print(i['resourceName'])
                        self.tempUserCourseId = i["userCourseId"]
                    else:
                        result[i["resourceId"]] = self.tempUserCourseId
        return result

    def start(self, courseId):
        data = {
            "userProjectId": self.userProjectId,
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "courseId": courseId,
        }
        headers = {"x-token": self.x_token}
        res = requests.post(
            "https://weiban.mycourse.cn/pharos/usercourse/study.do",
            data=data,
            headers=headers,
        )
        while json.loads(res.text)["code"] == -1:
            time.sleep(5)
            res = requests.post(
                "https://weiban.mycourse.cn/pharos/usercourse/study.do",
                data=data,
                headers=headers,
            )

    # 感谢以下项目的思路
    # https://github.com/Sustech-yx/WeiBanCourseMaster
    def finish(self, courseId, finishId):
        get_url_url = "https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do"
        finish_url = "https://weiban.mycourse.cn/pharos/usercourse/v2/{}.do"
        data = {
            "userProjectId": self.userProjectId,
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "courseId": courseId,
        }
        requests.post(get_url_url, data=data, headers=self.headers)
        token = self.get_method_token(finishId)
        finish_url = finish_url.format(token)
        ts = self.__get_timestamp().replace(".", "")
        param = {
            "callback": "jQuery{}_{}".format(self.__gen_rand(), ts),
            "userCourseId": finishId,
            "tenantCode": self.tenantCode,
            "_": str(int(ts) + 1),
        }
        text = requests.get(finish_url, params=param, headers=self.headers).text
        print(text)
        return text

    def get_method_token(self, course_id):
        url = "https://weiban.mycourse.cn/pharos/usercourse/getCaptcha.do"
        params = {
            "userCourseId": course_id,
            "userProjectId": self.userProjectId,
            "userId": self.userId,
            "tenantCode": "32101701"
        }
        text = requests.get(url, headers=self.headers, params=params).text
        question_id = json.loads(text)['captcha']['questionId']
        url = "https://weiban.mycourse.cn/pharos/usercourse/checkCaptcha.do"
        params = {
            "userCourseId": course_id,
            "userProjectId": self.userProjectId,
            "userId": self.userId,
            "tenantCode": self.tenantCode,
            "questionId": question_id
        }
        data = {
            "coordinateXYs": "[{\"x\":199,\"y\":448},{\"x\":241,\"y\":466},{\"x\":144,\"y\":429}]"
        }
        text = requests.post(url, headers=self.headers, params=params, data=data).text
        return json.loads(text)['data']['methodToken']

    @staticmethod
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
            return data

    @staticmethod
    def get_tenant_code(school_name: str) -> str:
        tenant_list = requests.get(
            "https://weiban.mycourse.cn/pharos/login/getTenantListWithLetter.do"
        ).text
        data = json.loads(tenant_list)["data"]
        for i in data:
            for j in i["list"]:
                if j["name"] == school_name:
                    return j["code"]
