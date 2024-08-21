import difflib
import os.path
import time
import uuid

import ddddocr
import requests
import json
import datetime
import random

from PIL import Image

import encrypted


class WeibanHelper:
    tenantCode = 0
    userId = ""
    x_token = ""
    userProjectId = ""
    project_list = {}
    ocr = None
    finish_exam_time = 0
    headers = {
        "X-Token": "",
        "ContentType": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82",
    }

    tempUserCourseId = ""

    def __init__(self, account, password, school_name, auto_verify=False, project_index=0):
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        tenant_code = self.get_tenant_code(school_name=school_name)
        img_file_uuid = ""
        verify_time = time.time()

        login_data = {}
        # 验证码处理
        verify_code = ''
        if not auto_verify:
            img_file_uuid = self.get_verify_code(get_time=verify_time, download=True)
            Image.open(f"code/{img_file_uuid}.jpg").show()
            verify_code = input("请输入验证码: ")
        else:
            verify_code = self.ocr.classification(self.get_verify_code(get_time=verify_time, download=False))
        login_data = self.login(account, password, tenant_code, verify_code, verify_time)

        if auto_verify:
            while login_data['code'] == '-1' and str(login_data).find("验证码") != -1:
                verify_time = time.time()
                verify_code = self.ocr.classification(self.get_verify_code(get_time=verify_time, download=False))
                login_data = self.login(account, password, tenant_code, verify_code, verify_time)
                time.sleep(5)
        login_data = login_data['data']
        self.project_list = WeibanHelper.get_project_id(login_data["userId"], tenant_code, login_data["token"])

        project_id = self.project_list[project_index]["userProjectId"]
        self.init(tenant_code, login_data["userId"], login_data["token"], project_id)

    def init(self, code, id, token, projectId):
        self.tenantCode = code
        self.userId = id
        self.x_token = token
        self.userProjectId = projectId
        self.headers["X-Token"] = self.x_token

    def run(self):
        for chooseType in [2, 3]:
            finishIdList = self.getFinishIdList(chooseType)
        num = len(finishIdList)
        index = 1
        for i in self.getCourse(chooseType):
            print(f"{index} / {num}")
            self.start(i)
            time.sleep(random.randint(15,20))
            self.finish(i, finishIdList[i])
            index = index + 1
        print("刷课完成")

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

            data = json.loads(response.text)
            if data['code'] == '-1':
                return result
            else:
                dataList = data['data']
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

    def autoExam(self):

        list_plan_url = f"https://weiban.mycourse.cn/pharos/exam/listPlan.do"
        before_paper_url = f"https://weiban.mycourse.cn/pharos/exam/beforePaper.do"
        get_verify_code_url = f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time="
        check_verify_code_url = f" https://weiban.mycourse.cn/pharos/exam/checkVerifyCode.do?timestamp"
        start_paper_url = f"https://weiban.mycourse.cn/pharos/exam/startPaper.do?"
        submit_url = f"https://weiban.mycourse.cn/pharos/exam/submitPaper.do?timestamp="
        answer_data = None
        with open("QuestionBank/result.json", 'r', encoding='utf8') as f:
            answer_data = json.loads(f.read())

        def get_answer_list(question_title):
            closest_match = difflib.get_close_matches(question_title, answer_data.keys(), n=1, cutoff=1)
            answer_list = []
            if closest_match:
                data = answer_data[closest_match[0]]
                for i in data['optionList']:
                    if i['isCorrect'] == 1:
                        answer_list.append(i['content'])
                return answer_list, True
            else:
                return answer_list, False

        def get_verify_code():
            now = time.time()
            content = requests.get(get_verify_code_url + str(now), headers=self.headers).content
            return self.ocr.classification(content), now

        # 获取考试计划
        plan_data = requests.post(list_plan_url, headers=self.headers, data={
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userProjectId": self.userProjectId
        }).json()
        if plan_data['code'] != '0':
            print("获取考试计划失败")
            return
        plan_id = plan_data['data'][0]['id']
        exam_plan_id = plan_data['data'][0]['examPlanId']
        # Before
        print(requests.post(before_paper_url, headers=self.headers, data={
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userExamPlanId": plan_id
        }).text)
        # Prepare
        print(requests.post(f" https://weiban.mycourse.cn/pharos/exam/preparePaper.do?timestamp",
                            headers=self.headers, data={
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamPlanId": plan_id,
            }).text)
        # Check
        verify_count = 0
        while True:
            verify_code, verify_time = get_verify_code()
            verify_data = requests.post(check_verify_code_url, headers=self.headers, data={
                "tenantCode": self.tenantCode,
                "time": verify_time,
                "userId": self.userId,
                "verifyCode": verify_code,
                "userExamPlanId": plan_id
            }).json()
            if verify_data['code'] == '0':
                break
            verify_count += 1
            if verify_count > 3:
                print("验证码识别失败")
                return
        # Start
        paper_data = requests.post(start_paper_url, headers=self.headers, data={
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userExamPlanId": plan_id,
        }).json()['data']
        question_list = paper_data['questionList']
        match_count = 0
        for question in question_list:
            question_title = question['title']
            option_list = question['optionList']
            submit_answer_id_list = []
            answer_list, is_match = get_answer_list(question_title)
            print(f"题目: {question_title}")
            if is_match:
                match_count = match_count + 1
                for answer in answer_list:
                    for option in option_list:
                        if option['content'] == answer:
                            submit_answer_id_list.append(option['id'])
                            print(f"答案: {answer}")
                print("\n")
            else:
                print("——————————!!!未匹配到答案，题库暂未收录此题!!!——————————")
                print("\n")

            # Record
            record_data = {
                "answerIds": ",".join(submit_answer_id_list),
                "questionId": question['id'],
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamPlanId": plan_id,
                "examPlanId": exam_plan_id,
                "useTime": random.randint(60, 90)
            }
            requests.post(f"https://weiban.mycourse.cn/pharos/exam/recordQuestion.do?timestamp={time.time()}",
                          headers=self.headers, data=record_data)
        # SubMit
        print("答案匹配度: ", match_count, " / ", len(question_list))
        if len(question_list) - match_count >= 1:
            print("题库匹配度过低")
            print("暂未提交,请重新考试")
            return
        submit_data = {
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userExamPlanId": plan_id,
        }
        time.sleep(self.finish_exam_time)
        print(requests.post(submit_url + str(int(time.time()) + 600), headers=self.headers, data=submit_data).text)

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
                        # print(i['resourceName'])
                        self.tempUserCourseId = i["userCourseId"]
                    else:
                        result[i["resourceId"]] = self.tempUserCourseId
            print(f"加载章节 : {i['categoryName']}")
        print("\n资源加载完成")
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
            "tenantCode": self.tenantCode
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

    @staticmethod
    def get_verify_code(get_time, download=False):
        img_uuid = uuid.uuid4()
        img_data = requests.get(
            f"https://weiban.mycourse.cn/pharos/login/randLetterImage.do?time={get_time}"
        ).content
        if img_data is None:
            print("验证码获取失败")
            exit(1)
        # 如果code目录不存在则创建
        if download:
            if not os.path.exists("code"):
                os.mkdir("code")
            with open(f"code/{img_uuid}.jpg", "wb") as file:
                file.write(img_data)
            return img_uuid
        else:
            return img_data

    @staticmethod
    def login(account, password, tenant_code, verify_code, verify_time):
        url = "https://weiban.mycourse.cn/pharos/login/login.do"
        payload = {
            "userName": account,
            "password": password,
            "tenantCode": tenant_code,
            "timestamp": verify_time,
            "verificationCode": verify_code,
        }
        ret = encrypted.login(payload)
        response = requests.post(url, data={"data": ret})
        text = response.text
        data = json.loads(text)
        print(data)
        if data['code'] == '-1':
            if str(data).find("不匹配") != -1:
                exit(1)
        return data
