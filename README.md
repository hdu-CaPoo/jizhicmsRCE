# CVE-2025-69901: JizhiCMS Authentication Bypass Vulnerability

## Overview
- **CVE ID:** CVE-2025-69901
- **Vendor:** JizhiCMS
- **Product:** JizhiCMS
- **Version:** v2.5 and v2.5.4
- **Vulnerability Type:** Incorrect Access Control / Session Poisoning
- **Affected Component:** LoginController.php

## Description
JizhiCMS v2.5 and v2.5.4 contain an Authentication Bypass vulnerability in the LoginController.php component. The vulnerability is caused by insecure usage of session variables (Session Poisoning) combined with PHP weak type comparisons. An unauthenticated remote attacker can exploit this issue to bypass the login mechanism and gain administrative access to the backend dashboard.

## Proof of Concept (PoC)

To exploit the vulnerability, an attacker sends a crafted HTTP request manipulating the session parameters (specifically 'frcode') to bypass the weak type comparison check.
I’ve put the poc in thIS repo.


# Details

这是一个典型的组合漏洞，由 **Session 变量覆盖（Session Poisoning）**  配合 **PHP 弱类型比较（Type Juggling）**  导致。

### 1. 漏洞根源：`LoginController.php` (Session 污染)

漏洞的入口在验证码生成函数中。

在 `LoginController.php`​ 的 `vercode` 方法中：

PHP

```
function vercode(){
    // ...
    // [漏洞点] 攻击者可以通过 GET/POST 参数 'name' 控制 $name 变量
    $name = $this->frparam('name',1,$this->frparam('code_name',1,'frcode'));
    
    // Imagecode 类会将生成的验证码字符串存储在 $_SESSION[$name] 中
    $imagecode=new \Imagecode($w,$h,$n,$name,APP_PATH."frphp/extend/AdobeGothicStd-Bold.ttf");
    $imagecode->imageout();
}
```

- ​**正常情况**​：系统默认调用时，`$name`​ 为 `frcode`​，验证码存入 `$_SESSION['frcode']`。
- ​**攻击情况**​：攻击脚本发送 `name=admin`​，导致 `$name`​ 变为 `admin`。
- ​**结果**​：系统将生成的 ​**验证码字符串**​（例如 `"1a2b"`​）直接赋值给了 ​ **​`$_SESSION['admin']`​** 。

### 2. 鉴权绕过：`CommonController.php` (弱类型检查)

攻击成功后，`$_SESSION['admin']`​ 从一个包含用户信息的**数组**变成了一个​**字符串**。

在 `CommonController.php`​ 的 `_init` 方法中，系统进行了如下权限检查：

PHP

```
function _init(){
    // 检查 admin 是否存在，或者 id 是否为 0
    if(!isset($_SESSION['admin']) || $_SESSION['admin']['id']==0){
        $_SESSION['admin'] = null;
        Redirect(U('Login/index')); // 验证失败，踢出
    }
    // ...
}
```

这里的逻辑有一个致命的缺陷，源于 PHP (特别是 PHP 7.x 版本) 处理字符串偏移量和弱类型比较的方式。

**攻击发生时的逻辑推演：**

1. ​ **​`!isset($_SESSION['admin'])`​** ：

    - 由于我们通过 `vercode`​ 注入了字符串，这个变量是存在的。此条件为 ​**False**（通过）。
2. ​ **​`$_SESSION['admin']['id']`​** ：

    - 此时 `$_SESSION['admin']`​ 是一个字符串（例如 `"1a2b"`）。
    - PHP 尝试访问字符串的 `'id'`​ 偏移量。由于 `'id'`​ 是字符串，PHP 会将其转换为整数 `0`。
    - 所以，代码实际访问的是 `$_SESSION['admin'][0]`​，即验证码字符串的​**第一个字符**。
3. ​ **​`== 0`​**​  **(弱类型比较)** ：

    - 接下来，系统判断 ​ **“验证码的第一个字符” 是否等于 0**。
    - 这里就是脚本需要“碰撞（Brute Force）”的原因：

      - ​**情形 A（失败）** ​：验证码是 `"abcd"`​。第一个字符是 `"a"`​。在 PHP 弱比较中，`"a" == 0`​ 为 ​**True**。

        - 结果：`True || True`​ -\> ​**验证失败，跳转登录页**。
      - ​**情形 B（成功）** ​：验证码是 `"7xyz"`​。第一个字符是 `"7"`​。在 PHP 弱比较中，`"7" == 0`​ 为 ​**False**。

        - 结果：`False || False`​ -\> ​**验证通过，成功进入后台**！

### 3. 总结：

1. ​**利用点**​：攻击者利用 `vercode`​ 接口将 `$_SESSION['admin']` 覆盖为随机的验证码字符串。
2. ​**绕过点**​：`CommonController`​ 错误地对字符串使用了数组操作 `['id']`，导致实际读取的是字符串的第一个字符。
3. ​**碰撞点**​：脚本不断刷新验证码，直到生成的验证码​**以非零数字（1-9）开头**​。此时，PHP 的弱类型比较判定其不等于 0，从而绕过 `if` 判断，成功以管理员身份进入后台。

‍

‍
