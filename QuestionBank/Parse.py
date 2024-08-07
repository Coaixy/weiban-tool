import json
import os


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


if __name__ == "__main__":
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
    print(f"总题目数量: {len(final_result)}")
    with open("result.json",'w') as f:
        f.write(json.dumps(final_result, indent=4, ensure_ascii=False))
