import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


def check_url(url, timeout=3):
    """
    单个URL的检测函数，供线程池调用
    只判断是否 < 400，具体丢弃逻辑在上层处理
    """
    try:
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code < 400:
            return url, True, response.status_code, None
        else:
            # 4xx / 5xx 都视为不可用
            return url, False, response.status_code, None
    except requests.exceptions.Timeout:
        return url, False, None, "Timeout"
    except Exception as e:
        return url, False, None, type(e).__name__


def multithread_filter_urls(input_file, output_file, timeout=3, max_workers=20):
    """
    多线程版URL过滤：
    - 只保留状态码 < 400 的 URL
    - 一旦发现可用URL就立即追加写入文件
    """
    try:
        # 读取URL列表
        with open(input_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        if not urls:
            print("输入文件为空！")
            return

        total = len(urls)
        print(f"开始测试 {total} 个URL（多线程）...")

        start_time = time.time()

        # 用于统计，可访问数量
        available_count = 0

        # 文件写入锁，保证多线程写文件时不冲突
        file_lock = threading.Lock()

        # 先清空/创建输出文件
        open(output_file, 'w', encoding='utf-8').close()

        # 使用线程池并发检测
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(check_url, url, timeout): url
                for url in urls
            }

            for i, future in enumerate(as_completed(future_to_url), 1):
                url = future_to_url[future]
                try:
                    url, ok, status_code, err = future.result()
                    # 打印进度
                    print(f"测试 [{i}/{total}]: {url}", end=" ")

                    if ok:
                        # 立即写入文件（追加）
                        with file_lock:
                            with open(output_file, 'a', encoding='utf-8') as f:
                                f.write(url + '\n')
                        available_count += 1
                        print("✓ 可用（已写入文件）")
                    else:
                        if status_code is not None:
                            # 丢弃 4xx / 5xx，只打印状态码
                            print(f"✗ 状态码: {status_code}")
                        else:
                            print(f"❌ 错误: {err}")
                except Exception as e:
                    print(f"测试 [{i}/{total}]: {url} ❌ 未知错误: {e}")

        elapsed = time.time() - start_time
        print("\n测试完成！")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"总URL数: {total}")
        print(f"可访问URL数: {available_count}")
        print(f"可用率: {available_count / total * 100:.1f}%")
        print(f"结果已保存到: {output_file}")

    except FileNotFoundError:
        print(f"错误：找不到文件 '{input_file}'")
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    multithread_filter_urls(
        input_file="target_cleaned.txt",
        output_file="available.txt",
        timeout=3,
        max_workers=20
    )