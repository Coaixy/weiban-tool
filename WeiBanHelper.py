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
from requests.exceptions import SSLError, Timeout, ConnectionError, HTTPError, RequestException, ProxyError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import encrypted


class WeibanHelper:
    tenantCode = 0
    userId = ""
    x_token = ""
    userProjectId = ""
    project_list = {}
    ocr = None
    finish_exam_time = 0
    exam_threshold = 1
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
        self.session = self.create_session()

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
        # 假设login_data是从某个请求返回的JSON数据中获取的
        if 'data' in login_data:
            login_data = login_data['data']
            self.project_list = WeibanHelper.get_project_id(
                login_data["userId"], tenant_code, login_data["token"]
            )
        else:
            # 如果 'data' 键不存在，输出提示信息
            print("登录失败，可能是学校名称输入错误。\n")
            print(f"返回的错误信息: {login_data}\n")

        project_id = self.project_list[project_index]["userProjectId"]
        self.init(tenant_code, login_data["userId"], login_data["token"], project_id)

    def init(self, code, id, token, projectId):
        self.tenantCode = code
        self.userId = id
        self.x_token = token
        self.userProjectId = projectId
        self.headers["X-Token"] = self.x_token

    def create_session(self):
        """
        创建一个带有重试策略的会话对象。
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],  # 替换 `method_whitelist`
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def retry_request(self, func, *args, retry_count=5, wait_time=3):
        """
        封装的重试请求方法。
        """
        for attempt in range(retry_count):
            try:
                return func(*args)  # 调用传入的函数并返回其结果
            except (SSLError, Timeout, ConnectionError, HTTPError, RequestException, ProxyError) as e:
                print(f"网络错误 [{type(e).__name__}]: {e}，URL: {args[0]}，正在重试 {attempt + 1} / {retry_count} 次...")
                time.sleep(wait_time)  # 等待指定时间后重试
                if attempt == retry_count - 1:
                    print("达到最大重试次数，跳过此操作。")
                    return None  # 如果最终失败，返回 None

    def start(self, courseId):
        """
        启动课程学习的请求方法，包含重试机制和网络错误处理。
        :param courseId: 课程ID，用于启动指定的课程学习。
        """
        url = "https://weiban.mycourse.cn/pharos/usercourse/study.do"
        data = {
            "userProjectId": self.userProjectId,
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "courseId": courseId,
        }
        headers = {"x-token": self.x_token}

        try:
            # 初始请求
            response = self.session.post(
                url,
                data=data,
                headers=headers,
                proxies={"http": None, "https": None},  # 禁用代理
                timeout=10,  # 设置超时时间
                verify=False  # 如果需要跳过 SSL 证书验证
            )

            # 重试机制，直到请求成功
            while json.loads(response.text).get("code") == -1:
                print("请求未成功，继续等待并重试...")
                time.sleep(5)  # 等待5秒后重试
                response = self.session.post(
                    url,
                    data=data,
                    headers=headers,
                    proxies={"http": None, "https": None},  # 禁用代理
                    timeout=30,
                    verify=False
                )

            # 检查请求状态码
            if response.status_code == 200:
                print("课程启动成功")
            else:
                print(f"请求失败，状态码: {response.status_code}，URL: {url}")

        except (ProxyError, SSLError, Timeout, ConnectionError, HTTPError, RequestException) as e:
            print(f"网络错误 [{type(e).__name__}]: {e}，URL: {url}")
            # 进一步处理或记录错误

    def run(self):
        for chooseType in [2, 3]:
            finishIdList = self.retry_request(self.getFinishIdList, chooseType)

            if finishIdList is None:
                print(f"无法获取 finishIdList，跳过 chooseType={chooseType} 的课程处理。")
                continue

            course_list = self.retry_request(self.getCourse, chooseType)

            if course_list is None:
                print(f"无法获取课程列表，跳过 chooseType={chooseType} 的课程处理。")
                continue

            num = len(course_list)
            index = 1
            for i in course_list:
                print(f"{index} / {num}")
                self.start(i)
                time.sleep(random.randint(15, 20)) #刷课时间区间
                self.retry_request(self.finish, i, finishIdList[i])
                index += 1
            print(f"chooseType={chooseType} 的课程刷课完成")

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
        check_verify_code_url = f"https://weiban.mycourse.cn/pharos/exam/checkVerifyCode.do?timestamp"
        start_paper_url = f"https://weiban.mycourse.cn/pharos/exam/startPaper.do?"
        submit_url = f"https://weiban.mycourse.cn/pharos/exam/submitPaper.do?timestamp="
        answer_data = None

        with open("QuestionBank/result.json", 'r', encoding='utf8') as f:
            answer_data = json.loads(f.read())

        def retry_request_2(method, url, headers=None, data=None, max_retries=5, retry_delay=5):
            for attempt in range(max_retries):
                try:
                    if method == "GET":
                        response = requests.get(url, headers=headers, data=data)
                    elif method == "POST":
                        response = requests.post(url, headers=headers, data=data)
                    else:
                        raise ValueError("Invalid method type")
                    response.raise_for_status()  # 检查是否返回了错误的状态码
                    return response
                except (requests.exceptions.RequestException, ValueError) as e:
                    print(f"网络错误:Request failed: {e}. 正在重试:Attempt {attempt + 1} / {max_retries}次. Retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        print("Max retries reached. Request failed.")
                        raise
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
            content = retry_request_2("GET", get_verify_code_url + str(now), headers=self.headers).content
            return self.ocr.classification(content), now

        from datetime import datetime
        # 获取当前系统时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 获取考试计划
        plan_data = retry_request_2("POST", list_plan_url, headers=self.headers, data={
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
        print(retry_request_2("POST", before_paper_url, headers=self.headers, data={
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userExamPlanId": plan_id
        }).text)

        # Prepare
        print(retry_request_2("POST", f"https://weiban.mycourse.cn/pharos/exam/preparePaper.do?timestamp",
                              headers=self.headers, data={
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamPlanId": plan_id,
            }).text)

        # Check
        verify_count = 0
        while True:
            verify_code, verify_time = get_verify_code()
            verify_data = retry_request_2("POST", check_verify_code_url, headers=self.headers, data={
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
        paper_data = retry_request_2("POST", start_paper_url, headers=self.headers, data={
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userExamPlanId": plan_id,
        }).json()['data']

        # 提取题目列表
        question_list = paper_data['questionList']
        match_count = 0

        for question in question_list:
            question_title = question['title']
            option_list = question['optionList']
            submit_answer_id_list = []

            # 获取答案列表和初始的匹配标志
            answer_list, _ = get_answer_list(question_title)

            print(f"题目: {question_title}")

            # 检查题目标题是否匹配
            if answer_list:
                # 查找是否有至少一个答案在选项中匹配
                found_match = False
                for answer in answer_list:
                    matched_option = next((option for option in option_list if option['content'] == answer), None)
                    if matched_option:
                        submit_answer_id_list.append(matched_option['id'])
                        print(f"答案: {answer}")
                        found_match = True

                # 判断是否找到匹配的答案
                if found_match:
                    match_count += 1
                    print("<===答案匹配成功===>\n")
                else:
                    print("<——————————!!!题目匹配但选项未找到匹配项!!!——————————>\n")
            else:
                print("<——————————!!!未匹配到答案，题库暂未收录此题!!!——————————>\n")

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
            retry_request_2("POST", f"https://weiban.mycourse.cn/pharos/exam/recordQuestion.do?timestamp={time.time()}",
                            headers=self.headers, data=record_data)

        # Submit
        print("答案匹配度: ", match_count, " / ", len(question_list))
        # 输出指定文本和当前系统时间
        print(f" - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if len(question_list) - match_count > self.exam_threshold:
            print("题库匹配度过低")
            print("暂未提交,请重新考试")
            return

        submit_data = {
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userExamPlanId": plan_id,
        }
        time.sleep(self.finish_exam_time)
        print(retry_request_2("POST", submit_url + str(int(time.time()) + 600), headers=self.headers,
                              data=submit_data).text)
        # 输出指定文本和当前系统时间
        print(f" - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

    # 感谢以下项目的思路
    def finish(self, courseId, finishId):
        from datetime import datetime
        # 获取当前系统时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        def get_mid_text(text, start, end):
            """
            从文本中提取位于 start 和 end 之间的子字符串。

            参数:
            text: 原始文本
            start: 起始标记
            end: 结束标记

            返回:
            子字符串
            """
            start_index = text.index(start) + len(start)
            end_index = text.index(end, start_index)
            return text[start_index:end_index]

        def finish_first_attempt():
            """
            尝试首次请求以完成任务。

            请求过程:
            1. 发送 POST 请求获取课程的 URL。
            2. 使用返回的数据生成完成任务的 URL。
            3. 发送 GET 请求尝试完成任务，并返回响应文本。

            返回:
            响应文本
            """
            # 获取课程 URL 的接口
            get_url_url = "https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do"
            # 完成任务的接口（模板）
            finish_url = "https://weiban.mycourse.cn/pharos/usercourse/v2/{}.do"
            # 请求数据
            data = {
                "userProjectId": self.userProjectId,
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "courseId": courseId,
            }
            # 发送 POST 请求获取课程 URL
            response = requests.post(get_url_url, data=data, headers=self.headers)
            # 获取任务完成的令牌
            token = self.get_method_token(finishId)
            # 格式化完成任务的 URL
            finish_url = finish_url.format(token)
            # 获取当前时间戳并处理
            ts = self.__get_timestamp().replace(".", "")
            # 生成请求参数
            param = {
                "callback": "jQuery{}_{}".format(self.__gen_rand(), ts),
                "userCourseId": finishId,
                "tenantCode": self.tenantCode,
                "_": str(int(ts) + 1),
            }
            # 发送 GET 请求完成任务，并返回响应文本
            text = requests.get(finish_url, params=param, headers=self.headers).text
            return text

        def finish_second_attempt():
            """
            当第一次尝试失败时，使用备选方法进行第二次尝试。

            请求过程:
            1. 发送 POST 请求获取课程的 URL 和 userCourseId。
            2. 使用返回的数据生成完成任务的 URL。
            3. 发送 GET 请求尝试完成任务，并返回响应文本。

            返回:
            响应文本
            """
            # 获取课程 URL 的接口
            get_url_url = "https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do"
            # 完成任务的接口（模板）
            finish_url = "https://weiban.mycourse.cn/pharos/usercourse/v2/{}.do"
            # 请求数据
            data = {
                "userProjectId": self.userProjectId,
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "courseId": courseId,
            }
            # 发送 POST 请求获取课程 URL 和 userCourseId
            text = json.loads(requests.post(get_url_url, data=data, headers=self.headers).text)['data']
            # 从返回的数据中提取 userCourseId
            token = get_mid_text(text, "userCourseId=", "&tenantCode")
            # 格式化完成任务的 URL
            finish_url = finish_url.format(token)
            # 获取当前时间戳并处理
            ts = self.__get_timestamp().replace(".", "")
            # 生成请求参数
            param = {
                "callback": "jQuery{}_{}".format(self.__gen_rand(), ts),
                "userCourseId": finishId,
                "tenantCode": self.tenantCode,
                "_": str(int(ts) + 1),
            }
            # 发送 GET 请求完成任务，并返回响应文本
            text = requests.get(finish_url, params=param, headers=self.headers).text
            return text

        # 尝试使用第一个函数逻辑请求
        first_attempt_response = finish_first_attempt()

        # 检查第一个函数的响应是否成功
        if ('{"msg":"ok"' in first_attempt_response
                and '"code":"0"' in first_attempt_response
                and '"detailCode":"0"' in first_attempt_response):
            # 输出第一个函数请求成功的消息
            print("finish_first_attempt函数请求成功🗹")
            # 输出响应文本
            print(first_attempt_response)
            # 输出指定文本和当前系统时间
            print(f" - 当前时间: {current_time}")
            # 返回响应文本
            return first_attempt_response
        else:
            # 如果第一个函数请求失败，先输出失败信息
            print("finish_first_attempt函数请求失败🗵，尝试使用finish_second_attempt函数请求")
            # 输出第一个函数的响应文本
            print(first_attempt_response)
            print(" ҉ ҉ ҉ ҉ ҉ ҉ ҉ ҉ ҉ ҉ ")

            # 尝试使用第二个函数逻辑请求
            second_attempt_response = finish_second_attempt()

            # 检查第二个函数的响应是否成功
            if ('{"msg":"ok"' in second_attempt_response
                    and '"code":"0"' in second_attempt_response
                    and '"detailCode":"0"' in second_attempt_response):
                # 输出第二个函数请求成功的消息
                print("finish_second_attempt函数请求成功🗹")
                # 输出响应文本
                print(second_attempt_response)
                # 输出指定文本和当前系统时间
                print(f" - 当前时间: {current_time}")
                # 返回响应文本
                return second_attempt_response
            else:
                # 输出第二个函数请求失败的消息
                print("finish_second_attempt函数请求失败🗵")
                # 输出第二个函数的响应文本
                print(second_attempt_response)
                # 输出指定文本和当前系统时间
                print(f" - 当前时间: {current_time}")
                # 返回响应文本
                return second_attempt_response

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
