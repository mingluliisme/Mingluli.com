#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mingluli.com 一键发布

做四件事：
  1. 运行 build.py，把 content/ 里的 Markdown 生成到 index.html
  2. 显示将要提交的改动
  3. 提交（会先问提交说明，直接回车用默认值）
  4. 推送；直连失败时自动改用 Clash 的 7897 代理重试

用法：
    双击 publish.bat
或  python publish.py            # 完整流程
    python publish.py --no-push  # 只构建并显示改动，不提交不推送
"""

import os
import subprocess
import sys
from functools import partial

# 保证 print 与子进程输出按顺序出现
print = partial(print, flush=True)

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = 'http://127.0.0.1:7897'
CLEAN_VARS = ('http_proxy', 'https_proxy', 'HTTP_PROXY',
              'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY')


def git(*args, proxy=False):
    """跑一条 git 命令，返回 (退出码, 输出)。"""
    cmd = ['git', '-c', 'core.quotepath=false']
    if proxy:
        cmd += ['-c', 'http.proxy=' + PROXY, '-c', 'https.proxy=' + PROXY]
    cmd += list(args)

    env = os.environ.copy()
    for k in CLEAN_VARS:
        env.pop(k, None)

    p = subprocess.run(cmd, cwd=HERE, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', errors='replace').strip()


def main():
    print('=' * 50)
    print(' Mingluli.com 一键发布')
    print('=' * 50)

    # 1. 构建
    print('\n[1/4] 构建页面 ...')
    r = subprocess.run([sys.executable, 'build.py'], cwd=HERE)
    if r.returncode != 0:
        print('\n构建失败，已中止。上面有具体报错。')
        return 1

    # 2. 看改动
    print('\n[2/4] 将要提交的改动：')
    code, out = git('status', '--short')
    if not out:
        print('  （没有改动）')
        print('\n没有需要提交的内容，结束。')
        return 0
    print(out)

    if '--no-push' in sys.argv:
        print('\n--no-push 模式：到此为止，未提交也未推送。')
        return 0

    # 3. 提交
    print('\n[3/4] 提交 ...')
    try:
        msg = input('提交说明（直接回车用「更新内容」）: ').strip()
    except EOFError:
        msg = ''
    if not msg:
        msg = '更新内容'

    git('add', 'content', 'index.html', 'build.py', 'build.bat',
        'publish.py', 'publish.bat', '.vercelignore')
    code, out = git('commit', '-m', msg)
    print(out)
    if code != 0:
        print('\n提交失败，已中止。')
        return 1

    # 4. 推送
    print('\n[4/4] 推送 ...')
    code, out = git('push', 'origin', 'main')
    print(out)
    if code != 0:
        print('\n直连失败，改用 Clash 代理（127.0.0.1:7897）重试 ...')
        code, out = git('push', 'origin', 'main', proxy=True)
        print(out)

    if code != 0:
        print('\n推送失败。请检查：')
        print('  1. Clash 是否在运行、节点是否能测出延迟')
        print('  2. 网络恢复后重新双击 publish.bat（已提交的不会丢）')
        return 1

    print('\n' + '=' * 50)
    print(' 完成。约 1 分钟后 Vercel 自动部署。')
    print(' 验证：https://mingluli.com')
    print('=' * 50)
    return 0


if __name__ == '__main__':
    sys.exit(main())
