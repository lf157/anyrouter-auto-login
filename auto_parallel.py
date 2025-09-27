import time
import random
import os
import asyncio
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def load_accounts(filename='accounts.txt'):
    """从文件加载账号列表"""
    accounts = []
    if not os.path.exists(filename):
        print(f"错误: 账号文件 {filename} 不存在！")
        return accounts

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue

                # 解析账号密码
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        username, password = parts[0].strip(), parts[1].strip()
                        if username and password:
                            accounts.append({'username': username, 'password': password})
                        else:
                            print(f"警告: 第 {line_num} 行格式不正确，已跳过")
                    else:
                        print(f"警告: 第 {line_num} 行格式不正确，已跳过")
                else:
                    print(f"警告: 第 {line_num} 行缺少逗号分隔符，已跳过")

        print(f"成功加载 {len(accounts)} 个账号")
        return accounts

    except Exception as e:
        print(f"读取账号文件失败: {e}")
        return accounts

# 从文件加载账号列表
accounts = load_accounts('accounts.txt')

login_url = 'https://anyrouter.top/login'

async def get_balance_info(page):
    """获取账户余额信息"""
    try:
        balance_info = {}

        # 获取余额数据
        balance_data = await page.evaluate('''
            () => {
                const result = {};

                // 查找所有包含美元符号的元素
                const dollarElements = Array.from(document.querySelectorAll('*')).filter(el =>
                    el.textContent &&
                    el.textContent.match(/\\$[0-9,]+\\.?[0-9]*/) &&
                    el.children.length === 0
                );

                dollarElements.forEach(el => {
                    const text = el.textContent.trim();
                    const parent = el.parentElement;
                    const grandParent = parent ? parent.parentElement : null;

                    let context = '';
                    if (parent) context += parent.textContent;
                    if (grandParent) context += ' | ' + grandParent.textContent;

                    if (context.includes('当前余额')) {
                        result.currentBalance = text;
                    } else if (context.includes('历史消耗')) {
                        result.historicalUsage = text;
                    }
                });

                return result;
            }
        ''')

        if balance_data:
            balance_info.update(balance_data)

        # 格式化输出
        if balance_info:
            result_parts = []
            if 'currentBalance' in balance_info:
                result_parts.append(f"💰 余额: {balance_info['currentBalance']}")
            if 'historicalUsage' in balance_info:
                result_parts.append(f"📊 消耗: {balance_info['historicalUsage']}")
            return " | ".join(result_parts) if result_parts else None

        return None

    except Exception as e:
        print(f"[*] 获取余额信息时出错: {e}")
        return None

async def async_login_and_sign(account, browser_num):
    """异步版浏览器自动登录和签到"""
    thread_id = threading.current_thread().name
    print(f"[浏览器{browser_num}] [{thread_id}] 正在处理账号: {account['username']}")

    balance_info = None

    try:
        async with async_playwright() as p:
            # 每个浏览器实例完全独立
            browser = await p.chromium.launch(
                headless=True,
                channel="chrome",
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                ]
            )

            # 创建独立的浏览器上下文（完全隔离的环境）
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(10000)

            print(f"[浏览器{browser_num}] 访问登录页面...")
            await page.goto(login_url, wait_until='domcontentloaded')

            # 关闭弹窗
            try:
                close_button = page.locator('button:has-text("关闭公告")')
                if await close_button.is_visible(timeout=2000):
                    await close_button.click()
                    print(f"[浏览器{browser_num}] 关闭了系统公告")
            except:
                pass

            # 检查邮箱登录选项
            try:
                email_login_button = page.locator('button:has-text("使用 邮箱或用户名 登录")')
                if await email_login_button.is_visible(timeout=2000):
                    await email_login_button.click()
                    print(f"[浏览器{browser_num}] 点击了邮箱登录选项")
                    await asyncio.sleep(1)
            except:
                pass

            # 填写登录信息
            print(f"[浏览器{browser_num}] 填写登录信息...")
            username_input = page.locator('#username, input[placeholder*="用户名"], input[placeholder*="邮箱"]').first
            await username_input.fill(account['username'])

            password_input = page.locator('#password, input[type="password"]').first
            await password_input.fill(account['password'])

            print(f"[浏览器{browser_num}] 提交登录...")
            login_button = page.locator('button:has-text("继续"), button[type="submit"], button:has-text("登录")').first
            await login_button.click()

            # 等待登录结果
            try:
                await page.wait_for_url('**/console**', timeout=8000)
                print(f"[浏览器{browser_num}] ✅ 账号 {account['username']} 登录成功！")
            except:
                print(f"[浏览器{browser_num}] ⏳ 等待页面加载...")

            await asyncio.sleep(2)

            # 获取余额信息
            balance_info = await get_balance_info(page)
            if balance_info:
                print(f"[浏览器{browser_num}] 💰 {balance_info}")

            await context.close()  # 关闭上下文
            await browser.close()   # 关闭浏览器

            print(f"[浏览器{browser_num}] ✓ 账号 {account['username']} 处理完成")
            return {'success': True, 'balance_info': balance_info, 'username': account['username']}

    except Exception as e:
        print(f"[浏览器{browser_num}] ❌ 账号 {account['username']} 处理失败: {e}")
        return {'success': False, 'balance_info': None, 'username': account['username']}

def run_async_login(account, browser_num):
    """在新的事件循环中运行异步函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_login_and_sign(account, browser_num))
    finally:
        loop.close()

def main_parallel(max_browsers=2):
    """并发处理多个账号"""
    print("=" * 70)
    print(f"并发登录脚本 (最多同时运行 {max_browsers} 个浏览器)")
    print("=" * 70)

    start_time = time.time()
    results = []

    # 使用线程池并发执行
    with ThreadPoolExecutor(max_workers=max_browsers) as executor:
        # 提交所有任务
        future_to_account = {}
        for i, account in enumerate(accounts):
            browser_num = (i % max_browsers) + 1
            future = executor.submit(run_async_login, account, browser_num)
            future_to_account[future] = account

            # 如果还有更多账号，稍微延迟提交，避免同时启动太多
            if (i + 1) % max_browsers == 0 and i < len(accounts) - 1:
                time.sleep(1)

        # 收集结果
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"账号 {account['username']} 执行出错: {e}")
                results.append({'success': False, 'username': account['username'], 'balance_info': None})

    end_time = time.time()
    total_time = end_time - start_time

    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)

    print("\n" + "=" * 70)
    print("📊 处理结果统计")
    print("=" * 70)
    print(f"✅ 成功: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    print(f"❌ 失败: {total_count - success_count}/{total_count}")
    print(f"⏱️  总耗时: {total_time:.1f} 秒")
    print(f"📈 平均每账号: {total_time/total_count:.1f} 秒")
    print(f"🚀 并发加速: 相比串行节省约 {(total_count - 1) * (total_time/total_count) / max_browsers:.1f} 秒")

    # 显示账号详情
    print(f"\n💰 账号处理详情:")
    print("-" * 70)
    for result in results:
        username_short = result['username'].split('@')[0]
        status = "✅" if result['success'] else "❌"
        balance = result.get('balance_info', '无余额信息')
        print(f"{status} {username_short:20} | {balance}")

    print("=" * 70)

def main_sequential():
    """串行处理（原始方式）- 用于对比"""
    from auto_optimized import optimized_login_and_sign

    print("=" * 70)
    print("串行登录脚本 (逐个处理)")
    print("=" * 70)

    start_time = time.time()
    results = []

    for i, account in enumerate(accounts):
        print(f"\n📋 处理账号 {i+1}/{len(accounts)}: {account['username']}")
        result = optimized_login_and_sign(account)
        results.append(result)

        if i < len(accounts) - 1:
            time.sleep(random.randint(1, 2))

    end_time = time.time()
    print(f"\n⏱️ 串行处理总耗时: {end_time - start_time:.1f} 秒")

if __name__ == '__main__':
    print("\n请选择运行模式:")
    print("1. 并发模式 (2个浏览器同时运行)")
    print("2. 并发模式 (3个浏览器同时运行)")
    print("3. 串行模式 (逐个处理，用于对比)")

    # 默认选择1
    print("\n默认使用选项1 (2个浏览器)")
    main_parallel(max_browsers=2)