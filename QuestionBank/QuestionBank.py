import json
import os
import difflib

import uvicorn
from fastapi import FastAPI

app = FastAPI()


def get_all_json_files_content(directory):
    json_files_content = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json") and filename != "result.json":
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    json_files_content[filename] = json.load(file)
            except Exception as e:
                print(f"读取文件 {filename} 时发生错误: {e}")
    return json_files_content


async def generate_bank():
    final_result = {}
    directory = '.'  # 当前目录
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
    with open("result.json", 'w') as f:
        f.write(json.dumps(final_result, indent=4, ensure_ascii=False))
    # return json.dumps(final_result, indent=4, ensure_ascii=False)
    print(final_result)


bank_obj = {}
with open("result.json", 'r') as f:
    bank_obj = json.load(f)


@app.get("/answer/{question}")
async def get_answer(question: str):
    closest_match = difflib.get_close_matches(question, bank_obj.keys(), n=1, cutoff=0.6)
    if closest_match:
        return {'question':closest_match[0],'msg': bank_obj[closest_match[0]]}
    else:
        return {'msg': '题目不存在'}
    # return {'code': 200, 'msg': bank_obj.get(question, "题目不存在")}


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8080)
