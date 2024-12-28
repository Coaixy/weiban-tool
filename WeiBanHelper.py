import difflib
import os.path
import time
import uuid

import ddddocr
import requests
import json
import datetime
from datetime import datetime
import random

from PIL import Image
from requests.exceptions import SSLError, Timeout, ConnectionError, HTTPError, RequestException, ProxyError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import encrypted

from openai import OpenAI
import configparser

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
        verify_time = time.time()
        self.session = self.create_session()

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
            self.lab_info = WeibanHelper.get_lab_id(
                login_data["userId"], tenant_code, login_data["token"]
            )
            if self.lab_info:  # 检查是否成功获取到实验课信息
                print(f"实验课程名称: {self.lab_info['projectName']}")
                print(f"实验课程ID: {self.lab_info['userProjectId']}")
            else:
                print("当前账户没有实验课程。")
        else:
            # 如果 'data' 键不存在，输出提示信息
            print("登录失败，可能是学校名称输入错误。\n")
            print(f"返回的错误信息: {login_data}\n")

        if self.project_list is None and self.lab_info is not None:
            self.init(tenant_code, login_data["userId"], login_data["token"], self.lab_info["userProjectId"])
            self.project_list = []
        elif self.project_list is not None:
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
        启动课程学习的请求方法，包含错误处理和重试机制。
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
        retry_count = 0
        max_retries = 5  # 最大重试次数
        timeout = 10

        while retry_count < max_retries:
            try:
                print(f"尝试启动课程 (第 {retry_count + 1} 次) ...")

                # 发起请求
                response = self.session.post(
                    url,
                    data=data,
                    headers=headers,
                    proxies={"http": None, "https": None},  # 禁用代理
                    timeout=timeout,  # 设置超时时间
                    verify=False  # 如果需要跳过 SSL 证书验证
                )

                # 检查状态码
                if response.status_code != 200:
                    print(f"请求失败，状态码: {response.status_code}，响应内容: {response.text}")
                    retry_count += 1
                    time.sleep(5)  # 等待5秒后重试
                    continue

                # 检查返回内容是否为空
                if not response.text:
                    print(f"请求返回了空内容，URL: {url}")
                    retry_count += 1
                    time.sleep(5)  # 等待5秒后重试
                    continue

                # 解析返回的 JSON 数据
                try:
                    response_json = response.json()
                except json.JSONDecodeError as e:
                    print(f"[JSON 解析错误] 错误信息: {e}")  # ，响应内容: {response.text}
                    retry_count += 1
                    time.sleep(5)  # 等待5秒后重试
                    continue

                # 打印服务器完整响应
                print(f"服务器返回完整的响应: {response_json}")

                # 检查请求是否成功
                code = response_json.get("code")
                detail_code = response_json.get("detailCode")

                if code == '0' and detail_code == '0':
                    # 课程启动成功
                    print("课程启动成功")
                    print(f" - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    return  # 成功后退出重试循环
                else:
                    # 课程启动失败
                    print(
                        f"启动课程失败，错误代码: {code}，详细代码: {detail_code}，消息: {response_json.get('message', '无消息内容')}")
                    retry_count += 1
                    time.sleep(5)  # 等待5秒后重试

            except (ProxyError, SSLError, Timeout, ConnectionError, HTTPError, RequestException) as e:
                # 网络错误处理
                print(f"[网络错误] [{type(e).__name__}]: {e}，URL: {url}")
                retry_count += 1
                time.sleep(5)  # 等待5秒后重试

        print(f"已达到最大重试次数 ({max_retries})，启动课程失败。")

    def run(self):
        # 遍历 chooseType 2 和 3 进行刷课
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
                time.sleep(random.randint(15, 20))  # 刷课时间区间
                self.retry_request(self.finish, i, finishIdList[i])
                index += 1
            print(f"chooseType={chooseType} 的课程刷课完成")

    # js里的时间戳似乎都是保留了三位小数的.
    def __get_timestamp(self):
        return str(round(time.time(), 3))

    # Magic: 用于构造、拼接"完成学习任务"的url
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
        data = json.loads(response.text)
        return data["data"]["progressPet"]

    def getAnswerList(self):
        """
        获取答题记录的列表，通过逐条获取的方式处理多个记录
        """
        answer_list = []
        url = "https://weiban.mycourse.cn/pharos/exam/reviewPaper.do?timestamp=" + self.__get_timestamp()
        exam_id_list = self.listHistory()  # 调用 listHistory 来获取多个考试ID
        for exam_id in exam_id_list:
            data = {
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamId": exam_id,
                "isRetake": "2"
            }
            response = self.session.post(url, data=data, headers=self.headers)
            if response.status_code == 200:
                answer_list.append(response.text)  # 存储每条考试的答题记录
        return answer_list

    def listHistory(self):
        """
        获取用户的历史考试记录，并返回多个考试ID
        """
        result = []
        url = "https://weiban.mycourse.cn/pharos/exam/listHistory.do?timestamp=" + self.__get_timestamp()
        exam_plan_id_list = self.listExamPlan()  # 获取考试计划ID列表
        for exam_plan_id in exam_plan_id_list:
            dataList = {
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "examPlanId": exam_plan_id
            }
            response = self.session.post(url, headers=self.headers, data=dataList)
            data = json.loads(response.text)
            if data['code'] == '-1':
                return result
            else:
                for history in data['data']:  # 遍历历史考试记录
                    result.append(history['id'])
        return result

    def listExamPlan(self):
        """
        获取用户的考试计划ID列表
        """
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
        list = json.loads(response.text)["data"]
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
                    print(
                        f"网络错误:Request failed: {e}. 正在重试:Attempt {attempt + 1} / {max_retries}次. Retrying...")
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
        
        def ai_response(input, type):
            client = OpenAI(base_url = config['AI']['API_ENDPOINT'],api_key = config['AI']['API_KEY'])

            if type == 1:
                completion = client.chat.completions.create(
                    model = config['AI']['MODEL'],
                    messages=[
                        {
                            "role": "system", 
                            "content": "本题为单选题，你只能选择一个选项，请根据题目和选项回答问题，以json格式输出正确的选项对应的id（即正确选项'id'键对应的值）和内容（即正确选项'content'键对应的值），示例回答：{\"id\":\"0196739f-f8b7-4d5e-b8c7-6a31eaf631eb\",\"content\":\"回答一\"}除此之外不要输出任何多余的内容。"
                        },
                        {
                            "role": "user",
                            "content": input
                        }
                    ]
                )
            if type == 2:
                completion = client.chat.completions.create(
                    model = config['AI']['MODEL'],
                    messages=[
                        {
                            "role": "system", 
                            "content": "本题为多选题，你必须选择两个或以上选项，请根据题目和选项回答问题，以json格式输出正确的选项对应的id（即正确选项'id'键对应的值）和内容（即正确选项'content'键对应的值），回答只应该包含两个键，你需要使用逗号连接多个值，示例回答：{\"id\":\"0196739f-f8b7-4d5e-b8c7-6a31eaf631eb,b434e65e-8aa8-4b36-9fa9-224273efb6b0\",\"content\":\"回答一，回答二\"}除此之外不要输出任何多余的内容。"
                        },
                        {
                            "role": "user",
                            "content": input
                        }
                    ]
                )

            response = completion.choices[0].message.content
            data = json.loads(response)

            id_value = data['id']
            content_value = data['content']

            return id_value, content_value

        # 获取当前系统时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 获取所有计划
        plan_data = retry_request_2("POST", list_plan_url, headers=self.headers, data={
            "tenantCode": self.tenantCode,
            "userId": self.userId,
            "userProjectId": self.userProjectId
        }).json()

        if plan_data['code'] != '0':
            print("获取考试计划失败")
            return

        # 遍历所有考试计划
        for plan in plan_data['data']:
            plan_id = plan['id']
            exam_plan_id = plan['examPlanId']
            exam_plan_name = plan['examPlanName']
            exam_time_state = plan['examTimeState']
            can_not_exam_info = plan.get("canNotExamInfo", "")
            start_Time = plan['startTime']
            end_Time = plan['endTime']

            # Before
            print(retry_request_2("POST", before_paper_url, headers=self.headers, data={
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamPlanId": plan_id
            }).text)

            # 检查是否能够参加考试
            if exam_time_state != 2:
                print(f"考试计划 '{exam_plan_name}' 无法参加考试: '{can_not_exam_info}' \n")
                continue  # 跳过这个考试，继续下一个

            print(f"开始执行 '{exam_plan_name}' 考试开放为时间: {start_Time} 到 {end_Time}\n")
            # Prepare
            print(retry_request_2("POST", f"https://weiban.mycourse.cn/pharos/exam/preparePaper.do?timestamp",
                                  headers=self.headers, data={
                    "tenantCode": self.tenantCode,
                    "userId": self.userId,
                    "userExamPlanId": plan_id,
                }).text)

            # 验证码校验
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

            # 开始考试
            paper_data = retry_request_2("POST", start_paper_url, headers=self.headers, data={
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamPlanId": plan_id,
            }).json()['data']

            # 提取题目列表
            question_list = paper_data['questionList']
            match_count = 0
            ai_count = 0
            answerIds = None

            for question in question_list:
                question_title = question['title']
                question_type = question['type'] # 1是单选，2是多选
                question_type_name = question['typeLabel']
                option_list = question['optionList']
                submit_answer_id_list = []

                # 获取答案列表和初始的匹配标志
                answer_list, _ = get_answer_list(question_title)

                print(f"题目: {question_title}")

                config = configparser.ConfigParser()
                config.read('ai.conf')
                # 检查题目标题是否匹配
                if answer_list:
                    found_match = False
                    for answer in answer_list:
                        matched_option = next((option for option in option_list if option['content'] == answer), None)
                        if matched_option:
                            submit_answer_id_list.append(matched_option['id'])
                            print(f"答案: {answer}")
                            found_match = True

                    if found_match:
                        match_count += 1
                        print("<===答案匹配成功===>\n")
                    else:
                        print("<——————————!!!题目匹配但选项未找到匹配项!!!——————————>\n")
                elif not config['AI'].get('API_ENDPOINT') or not config['AI'].get('API_KEY') or not config['AI'].get('MODEL'):
                    print("<——————————!!!未匹配到答案，可配置ai.conf文件通过大模型答题!!!——————————>\n")
                else:
                    print("<——————————未匹配到答案，将使用AI获取答案——————————>\n")
                    problemInput = f"{question_title}\n{option_list}"
                    answerIds, content = ai_response(problemInput, question_type)
                    print(f"{question_type_name}，AI获取的答案: {content}")
                    ai_count += 1

                # 记录答案
                record_data = {
                    "answerIds": answerIds if answerIds is not None else ",".join(submit_answer_id_list),
                    "questionId": question['id'],
                    "tenantCode": self.tenantCode,
                    "userId": self.userId,
                    "userExamPlanId": plan_id,
                    "examPlanId": exam_plan_id,
                    "useTime": random.randint(60, 90)
                }
                retry_request_2("POST",
                                f"https://weiban.mycourse.cn/pharos/exam/recordQuestion.do?timestamp={time.time()}",
                                headers=self.headers, data=record_data)

            # 输出匹配度
            print("答案匹配度: ", match_count+ai_count, " / ", len(question_list))
            print("，其中 AI 作答有", ai_count, "题")
            print(f" - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            if len(question_list) - match_count > self.exam_threshold:
                print(f"题库匹配度过低, '{exam_plan_name}' 暂未提交,请再次打开程序别修改设置")
                return

            print("请耐心等待考试完成（等待时长为你填写的考试时间 默人300秒）\n")

            # 提交考试
            submit_data = {
                "tenantCode": self.tenantCode,
                "userId": self.userId,
                "userExamPlanId": plan_id,
            }
            time.sleep(self.finish_exam_time)
            print(retry_request_2("POST", submit_url + str(int(time.time()) + 600), headers=self.headers,
                                  data=submit_data).text)
            print(" - 考试已完成 \n")
            print(f" - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

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
            print(f" - 当前时间: {current_time} \n")
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
                print(f" - 当前时间: {current_time} \n")
                # 返回响应文本
                return second_attempt_response
            else:
                # 输出第二个函数请求失败的消息
                print("finish_second_attempt函数请求失败🗵")
                # 输出第二个函数的响应文本
                print(second_attempt_response)
                # 输出指定文本和当前系统时间
                print(f" - 当前时间: {current_time} \n")
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
    def get_project_id(user_id, tenant_code, token: str):
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
            # exit(1)
        else:
            return data

    def get_lab_id(user_id, tenant_code, token: str):
        """
        获取用户的实验课程信息。
        """
        url = f"https://weiban.mycourse.cn/pharos/lab/index.do?timestamp={int(time.time())}"
        headers = {
            "X-Token": token,
            "ContentType": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82",
        }
        data = {"tenantCode": tenant_code, "userId": user_id}
        response = requests.get(url, headers=headers, params=data)
        response_data = response.json()  # 解析JSON响应

        if response_data['code'] == '0' and response_data['detailCode'] == '0':
            # 检查 'current' 键是否存在于响应数据中
            if 'current' in response_data['data']:
                # 提取实验课程的信息
                lab_info = response_data['data']['current']
                return lab_info
            else:
                print("没有找到实验课程信息。")
                return None
        else:
            print("获取实验课程信息失败")
            return None

    # Todo(状态输出用于Web对接)
    # def generate_finish(self):
    #

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
