#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mingluli.com 内容构建脚本

把 content/ 目录下的 Markdown 渲染成 HTML，写进 index.html 的自动生成区。

用法：
    python build.py

它只改 index.html 里这三段注释之间的内容：

    <!-- AUTO-GENERATED:notes:START ... -->   ... <!-- AUTO-GENERATED:notes:END -->
    <!-- AUTO-GENERATED:life:START ... -->    ... <!-- AUTO-GENERATED:life:END -->
    <!-- AUTO-GENERATED:writing:START ... --> ... <!-- AUTO-GENERATED:writing:END -->

标记之外的任何 HTML 都原样保留，可以照常手改。
不依赖任何第三方库。
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, 'index.html')
CONTENT = os.path.join(HERE, 'content')

IND_ARTICLE = ' ' * 10   # <article>
IND_INNER = ' ' * 12     # .note 里的 <p>；.post-item 里的 <div> / <a>
IND_TEXT = ' ' * 14      # .note 里的文字；.post-item 里的 <p> / <h3>
IND_DEEP = ' ' * 16      # .post-item 里 <p> / <h3> 的文字


# ---------------------------------------------------------------- 文本工具

def escape(text):
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))


def render_inline(text):
    """极简 Markdown 行内语法：**粗体**、*斜体*、[文字](链接)"""
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text


def join_lines(lines):
    """段落内的多行合并成一行。

    中文之间直接相连，ASCII 字母数字之间补一个空格，
    避免"中文 中间 冒出空格"的观感问题。
    """
    if not lines:
        return ''
    out = lines[0]
    for nxt in lines[1:]:
        a, b = out[-1:], nxt[:1]
        sep = ' ' if (a.isascii() and a.isalnum()
                      and b.isascii() and b.isalnum()) else ''
        out += sep + nxt
    return out


def render_paragraphs(body):
    """按空行切段，每段包一个 <p>，段间空一行。"""
    blocks, cur = [], []
    for line in body.split('\n'):
        if line.strip() == '':
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line.strip())
    if cur:
        blocks.append(cur)

    parts = []
    for blk in blocks:
        parts.append('%s<p>\n%s%s\n%s</p>' % (
            IND_INNER, IND_TEXT, render_inline(join_lines(blk)), IND_INNER))
    return '\n\n'.join(parts)


# ---------------------------------------------------------------- 日期

def parse_date(raw):
    """2026-09-10 / 2026-09 / 2026-9-1 -> (2026, 9, 10)，缺日为 0。"""
    m = re.match(r'^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?', (raw or '').strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def fmt_date(d, with_day=True):
    """-> 2026 年 9 月 10 日 / 2026 年 9 月"""
    if d is None:
        return ''
    y, m, day = d
    if with_day and day:
        return '%d 年 %d 月 %d 日' % (y, m, day)
    return '%d 年 %d 月' % (y, m)


# ---------------------------------------------------------------- Markdown

def parse_file(path):
    """解析一个 md，返回 (meta, title, body)。"""
    with io.open(path, encoding='utf-8') as f:
        text = f.read().replace('\r\n', '\n')

    meta = {}
    if text.startswith('---\n'):
        end = text.find('\n---', 4)
        if end != -1:
            for line in text[4:end].split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            text = text[end + 4:]

    title, kept = None, []
    for line in text.split('\n'):
        if title is None and line.startswith('# '):
            title = line[2:].strip()
            continue
        kept.append(line)
    body = '\n'.join(kept).strip('\n')

    stem = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r'^(\d{4}-\d{1,2}(?:-\d{1,2})?)-(.+)$', stem)
    if m:
        meta.setdefault('date', m.group(1))
        meta.setdefault('slug', m.group(2))
    else:
        meta.setdefault('slug', stem)
        print('  ! 文件名缺少日期前缀：%s' % os.path.basename(path))

    return meta, title or meta.get('slug', ''), body


def load(folder):
    """读 content/<folder>/*.md，按日期倒序。"""
    d = os.path.join(CONTENT, folder)
    if not os.path.isdir(d):
        return []

    entries = []
    for name in sorted(os.listdir(d)):
        if not name.lower().endswith('.md'):
            continue
        meta, title, body = parse_file(os.path.join(d, name))
        dt = parse_date(meta.get('date')) or parse_date(name)
        if dt is None:
            print('  ! 无法识别日期，已跳过：%s' % name)
            continue
        meta['_dt'] = dt
        meta['_title'] = title
        meta['_body'] = body
        entries.append(meta)

    entries.sort(key=lambda e: e['_dt'], reverse=True)
    return entries


# ---------------------------------------------------------------- 渲染

def render_note_entries(entries):
    """随想 / 生活共用：日期 + 正文。"""
    out = []
    for e in entries:
        parts = [
            '%s<article class="note">' % IND_ARTICLE,
            '%s<p class="note-date">' % IND_INNER,
            '%s%s' % (IND_TEXT, fmt_date(e['_dt'])),
            '%s</p>' % IND_INNER,
        ]
        body = render_paragraphs(e['_body'])
        if body:
            parts.append('')
            parts.append(body)
        parts.append('%s</article>' % IND_ARTICLE)
        out.append('\n'.join(parts))
    return '\n\n\n'.join(out)


def render_post_entries(entries):
    """写作：日期(+状态) + 标题 + 简介 + 链接。"""
    out = []
    for e in entries:
        status = e.get('status', '').strip()
        date_text = fmt_date(e['_dt'], with_day=False)
        if status:
            date_text = '%s · %s' % (status, date_text)

        summary = e.get('summary', '').strip()
        if not summary:
            summary = e['_body'].split('\n\n')[0].strip()

        link = e.get('link', '').strip()
        if link and link != '#':
            href = '<a href="%s" target="_blank" rel="noopener noreferrer">' % escape(link)
        else:
            href = '<a href="#">'

        out.append('\n'.join([
            '%s<article class="post-item">' % IND_ARTICLE,
            '%s<div>' % IND_INNER,
            '%s<p class="post-date">%s</p>' % (IND_TEXT, date_text),
            '',
            '%s<h3>' % IND_TEXT,
            '%s%s' % (IND_DEEP, render_inline(e['_title'])),
            '%s</h3>' % IND_TEXT,
            '',
            '%s<p>' % IND_TEXT,
            '%s%s' % (IND_DEEP, render_inline(summary)),
            '%s</p>' % IND_TEXT,
            '%s</div>' % IND_INNER,
            '',
            '%s%s' % (IND_INNER, href),
            '%s阅读 →' % IND_TEXT,
            '%s</a>' % IND_INNER,
            '%s</article>' % IND_ARTICLE,
        ]))
    return '\n\n\n'.join(out)


# ---------------------------------------------------------------- 注入

def inject(html, key, block):
    pattern = re.compile(
        r'(<!-- AUTO-GENERATED:%s:START[^>]*-->)'
        r'.*?'
        r'(\n[ \t]*<!-- AUTO-GENERATED:%s:END -->)' % (key, key), re.S)

    if not pattern.search(html):
        print('  × 找不到标记 AUTO-GENERATED:%s，已中止' % key)
        sys.exit(1)

    def repl(m):
        middle = '\n' + block if block else ''
        return m.group(1) + middle + '\n' + m.group(2)

    return pattern.sub(repl, html, count=1)


# ---------------------------------------------------------------- 主流程

def main():
    if not os.path.isfile(INDEX):
        print('找不到 index.html：%s' % INDEX)
        sys.exit(1)

    print('读取内容：')
    notes = load('notes')
    life = load('life')
    writing = load('writing')
    print('  随想 %d 条 / 生活 %d 条 / 写作 %d 条' % (len(notes), len(life), len(writing)))

    html = io.open(INDEX, encoding='utf-8').read()
    html = inject(html, 'notes', render_note_entries(notes))
    html = inject(html, 'life', render_note_entries(life))
    html = inject(html, 'writing', render_post_entries(writing))

    io.open(INDEX, 'w', encoding='utf-8', newline='\r\n').write(html)
    print('已写入 index.html：%d 字节' % len(html.encode('utf-8')))


if __name__ == '__main__':
    main()
