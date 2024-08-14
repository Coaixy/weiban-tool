import json
import os
import difflib

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # 允许的源
    allow_credentials=True,
    allow_methods=["*"],  # 允许的方法，如：GET, POST, OPTIONS 等
    allow_headers=["*"],  # 允许的头
)


def get_all_json_files_content(directory):
    json_files_content = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json") and filename != "result.json":
            file_path = os.path.join(directory, filename)
            try:
                print(file_path)
                with open(file_path, 'r', encoding='utf-8') as file:
                    json_files_content[filename] = json.load(file)
            except Exception as e:
                print(f"读取文件 {filename} 时发生错误: {e}")
    return json_files_content


def generate_bank(directory='.'):
    final_result = {}
    json_contents = get_all_json_files_content(directory)
    json_data_list = {}
    for filename, content in json_contents.items():
        json_data_list[filename] = content['data']['questions']
    for filename, data in json_data_list.items():
        print(f"文件 {filename} 中的题目数量: {len(data)}")
        for item in data:
            if final_result.get(item['title']) is None:
                final_result[item['title']] = {
                    'typeLabel': item['typeLabel'],
                    'right': item['isRight'],
                    'optionList': item['optionList']
                }
        print()
    with open(f"{directory}/result.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(final_result, indent=4, ensure_ascii=False))
    # return json.dumps(final_result, indent=4, ensure_ascii=False)


bank_obj = {}


@app.get("/answer/{question}")
async def get_answer(question: str):
    for i in bank_obj:
        if question in i:
            return {'question': i, 'msg': bank_obj[i]}
    closest_match = difflib.get_close_matches(question, bank_obj.keys(), n=1, cutoff=0.6)
    if closest_match:
        return {'question': closest_match[0], 'msg': bank_obj[closest_match[0]]}
    else:
        return {'msg': '题目不存在'}
    # return {'code': 200, 'msg': bank_obj.get(question, "题目不存在")}


def main():
    generate_bank()
    with open("result.json", 'r') as f:
        global bank_obj
        bank_obj = json.load(f)
        print(bank_obj)
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == '__main__':
    main()
