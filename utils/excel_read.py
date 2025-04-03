from numpy import mod
import pandas as pd

def parse_excel_to_list(file_path):
    # 读取 Excel 文件，并将第一行作为表头
    df = pd.read_excel(file_path)
    
    # 初始化变量
    result = []
    current_port = None
    current_module = None
    port_count = 0
    module_count = 0
    
    # 遍历每一行数据
    for index, row in df.iterrows():
        # 使用 pd.isna() 的反向判断来避免类型问题
        port_value = row.get("项目模块")
        port = port_value.strip() if isinstance(port_value, str) and not pd.isna(port_value) else None
        module_value = row.get("功能模块")
        module = module_value.strip() if isinstance(module_value, str) and not pd.isna(module_value) else None
        feature_value = row.get("功能细分")
        feature = feature_value.strip() if isinstance(feature_value, str) and not pd.isna(feature_value) else None
        description_value = row.get("功能描述")
        description = description_value.strip() if isinstance(description_value, str) and not pd.isna(description_value) else None
        work_time = row.get("工时")
        work_time = work_time if isinstance(work_time, str) and not pd.isna(work_time) else None
        work_price = row.get("报价")
        work_price = work_price if isinstance(work_price, str) and not pd.isna(work_price) else None

        # 处理端口（大标题）
        if port:
            port_count += 1
            module_count = 0  # 重置模块计数
            current_port = port
            result.append(f"\n{port_count}：项目模块：{current_port}")
        
        # 处理模块（小标题）
        if module:
            module_count += 1
            current_module = module
            result.append(f"  {port_count}.{module_count} ：功能模块{module_count}：{current_module}")
        
        # 处理功能（子标题）
        if feature:
            if current_module:
                result.append(f"    {port_count}.{module_count} ：功能细分:{feature}")
            else:
                result.append(f"    {port_count} ：功能细分:{feature}")
        
        # 处理描述（如果有）
        if description:
            indented_description = "\n      ".join(description.split("\n"))
            result[-1] += f"\n      - {indented_description}"

        # 处理工时和报价（如果有）
        if work_time and work_price:
            result[-1] += f"\n      - 工时：{work_time}小时  报价：{work_price}元"
    
    # 输出结果
    res = file_path.split(".")[0] + "\n" + "\n".join(result)
    # 保存结果到word文件
    with open(file_path.split(".")[0] + ".md", "wb", encoding="utf-8") as f:
        f.write(res)
    return res

# 调用函数并打印结果
if __name__ == "__main__":
    file_path = "docs/社区信息公示项目需求.xls"  # 替换为您的文件路径
    output = parse_excel_to_list(file_path)
    print(output)