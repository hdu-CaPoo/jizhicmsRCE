def add_http_prefix(input_file, output_file):
    """
    检查文件每一行开头是否有 http，如果没有则自动补上 http://
    
    参数:
        input_file: 输入文件名
        output_file: 输出文件名
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f_in:
            lines = f_in.readlines()
        
        processed_lines = []
        for line in lines:
            line = line.strip()
            if line:  # 跳过空行
                # 检查开头是否有 http (不区分大小写)
                if not line.lower().startswith('http'):
                    line = 'http://' + line
                processed_lines.append(line)
        
        with open(output_file, 'w', encoding='utf-8') as f_out:
            for line in processed_lines:
                f_out.write(line + '\n')
        
        print(f"处理完成！已保存到: {output_file}")
        print(f"共处理了 {len(processed_lines)} 行")
        
    except FileNotFoundError:
        print(f"错误：找不到文件 '{input_file}'")
    except Exception as e:
        print(f"发生错误: {e}")

# 使用方法
if __name__ == "__main__":
    input_file = "target.txt"  # 输入文件名
    output_file = "target_cleaned.txt"  # 输出文件名
    
    add_http_prefix(input_file, output_file)