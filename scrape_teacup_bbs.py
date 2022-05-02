# SPDX-License-Identifier: MIT

# Scraping program for teacup. BBS
# © suwasakix 2022
#
# [ Primary Distribution URL ]
#   https://github.com/suwasakix/scrape_teacup_bbs
#
# [ System Requirement ]
#   * Google Chrome + Selenium WebDriver
#   * Python 3.x
#   * Selenium

import argparse
from inspect import currentframe, getframeinfo
import math
import os
import re
import requests
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import string
import sys

# ログファイル (HTML5形式) のHEAD
log_template_head = string.Template('''\
<!DOCTYPE html>
<html>

<head>
    <meta http-equiv="content-language" content="ja">
    <meta charset="utf-8">
    <title>${bbs_title}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
        }
        body {
            background-color: ${bbs_background_color};
            background-image: ${bbs_background_image};
            color: ${bbs_text_color};
            font-family: ${bbs_font_family};
        }
        a:link {
            color: ${link_color}
        }
        a:visited {
            color: ${link_visited_color}
        }
        a:active {
            color: ${link_active_color}
        }
        .bbs_title {
            border-style: none;
            color: ${bbs_title_color};
            font-size: x-large;
            font-weight: bold;
            margin: 0px;
            padding: 1em 1em 1em 1em;
            text-align: center;
        }
        .bbs_info {
            border-style: none;
            font-size: medium;
            margin: 0px;
            padding: 0em 1em 1em 1em;
            text-align: center;
        }
        .bbs_post {
            border-style: none;
            margin: 0px;
            padding: 0em 1em 0em 1em;
        };
        .bbs_hr {
            margin 0em 0em 0em 0em;
            width: 100%;
        }
        .post_pagination {
            margin: 0px 0px 0px 0px;
            padding: 10px 10px 10px 10px;
        }
        .post_pagination p {
            position: relative;
            text-align: center;
        }
        .post_pagination p span {
            border: 1px solid #b2b2b2;
            line-height: 2.5;
            padding: 8px 8px 8px 8px;
        }
        .post_pagination p a {
            border: 1px solid #b2b2b2;
            line-height: 2.5;
            padding: 8px 8px 8px 8px;
        }
        .post_pagination_curr {
            font-size: x-large;
        }
        .post_info {
            margin-top: 0.5em;
        }
        .post_title {
            color: ${post_title_color};
            font-size: large;
            font-weight: bold;
        }
        .post_author {
            color: ${post_author_color};
            font-size: medium;
            font-weight: bold;
        }
        .post_datetime {
            font-size: small;
        }
        .post_number {
            font-size: small;
        }
        .post_parent {
            font-size: small;
        }
        .post_article {
            font-size: medium;
            margin-top: 1em;
            margin-left: 30pt;
            margin-bottom: 1em;
        }
        .post_img {
            margin-top: 1em;
            margin-left: 30pt;
            margin-bottom: 1em;
        }
    </style>
</head>

<body>

''')

# ログファイル (HTML5形式) のBODYに表示するヘッダー  (タイトルのみ)
log_template_header= string.Template('''\
<div class="bbs_title">
${bbs_title}
</div>

<hr class="bbs_hr">

<div class="bbs_post">

''')

# ログファイル (HTML5形式) のBODYに表示するヘッダー  (タイトル + ヘッダー情報)
log_template_header_with_bbs_info = string.Template('''\
<div class="bbs_title">
${bbs_title}
</div>
<div class="bbs_info">
<p>
${bbs_info}
</p>
</div>

<hr class="bbs_hr">

<div class="bbs_post">

''')

# ログファイル (HTML5形式) のBODYに表示するページネーション (上側)
log_template_pagination_top = string.Template('''\
<div class="post_pagination">
<p>
${post_pagination}
</p>
</div>

<hr>

''')

# ログファイル (HTML5形式) のBODYに表示するページネーション (下側)
log_template_pagination_bottom = string.Template('''\

<hr>

<div class="post_pagination">
<p>
${post_pagination}
</p>
</div>

''')

# ログファイル (HTML5形式) のBODYに表示する投稿要素
log_template_post = string.Template('''\

<div class="post_info">
<span class="post_title" id="${post_number}">${post_title}</span>&emsp;投稿者：<span class="post_author">${post_author}</span>&ensp;
<span class="post_datetime">&nbsp;投稿日：${post_datetime}</span>&ensp;<span class="post_number">No.${post_number}</span> <!-- ${post_remotehost} -->
</div>
<div class="post_article">
<span class="post_parent">${post_parent}</span>
${post_article}
</div>

''')

# ログファイル (HTML5形式) のBODYに表示する画像 (元画像+サムネイル画像)
log_template_img = string.Template('''\
<div class="post_img">
<a href="${original_img_path}"><img src="${thumbnail_img_path}"></a>
</div>
''')

# ログファイル (HTML5形式) のBODYに表示する画像 (サムネイル画像のみ)
log_template_img_m = string.Template('''\
<div class="post_img">
<img src="${thumbnail_img_path}">
</div>
''')

# ログファイル (HTML5形式) のフッター
log_template_footer = string.Template('''\
</div>

<hr class="bbs_hr">

</body>

</html>
''')

# ログファイル名を取得
def get_log_file_name(page_no, page_num):
    # ログファイル名 : "bbsXXXX.html" (XXXXはページ番号, 左0埋め)
    return 'bbs' + str(page_no).zfill(len(str(page_num))) + '.html'

# 投稿本文に含まれるハイパーリンクのURL文字列を変更
def modify_href_strings_in_article(article_org, href_header):
    article_new = article_org
    href_iter = re.finditer(r'<a href=".+?" target="_blank" rel="nofollow">', article_org)
    for href in href_iter:
        href_org = href.group()
        # 掲示板投稿時にシステムによって改変されたURL文字列を元に戻す
        # ・URLの先頭に付加される文字列 (ex. "/YYYYYYYY/bbs?M=JU&amp;JUR=") を抹消
        # ・URLエンコードされたASCII文字を元に戻す
        href_new = href_org.replace(href_header, '')\
                           .replace('%20', ' ')\
                           .replace('%21', '!')\
                           .replace('%22', '"')\
                           .replace('%23', '#')\
                           .replace('%24', '$')\
                           .replace('%25', '%')\
                           .replace('%26', '&')\
                           .replace('%27', "'")\
                           .replace('%28', '(')\
                           .replace('%29', ')')\
                           .replace('%2A', '*')\
                           .replace('%2B', '+')\
                           .replace('%2C', ',')\
                           .replace('%2F', '/')\
                           .replace('%3A', ':')\
                           .replace('%3B', ';')\
                           .replace('%3C', '<')\
                           .replace('%3D', '=')\
                           .replace('%3E', '>')\
                           .replace('%3F', '?')\
                           .replace('%40', '@')\
                           .replace('%5B', '[')\
                           .replace('%5D', ']')\
                           .replace('%5E', '^')\
                           .replace('%60', '`')\
                           .replace('%7B', '{')\
                           .replace('%7C', '|')\
                           .replace('%7D', '}')\
                           .replace('%7E', '~')
        #print('href_org="%s", href_new="%s"' % (href_org, href_new))
        article_new = article_new.replace(href_org, href_new)

    return article_new

# ページネーションの作成
def make_pagination(now_page, page_num, log_template_pagination):
    pagenation = ''
    post_pagination = ''

    if page_num <= 1:
        # 総ページ数が1のとき : ページネーションなし
        pass
    elif page_num <= 11:
        # 総ページ数が2〜11のとき : [< Prev][1][2]...[N][Next >]
        post_pagination += ('<span><strong>< Prev</strong></span>') if (now_page == 1) else\
                           ('<a href="%s"><strong>< Prev</strong></a>' % get_log_file_name(now_page - 1, page_num))
        post_pagination += '&nbsp;'

        for i in range(1, page_num + 1):
            post_pagination += ('<span class="post_pagination_curr"><strong>%d</strong></span>' % i) if (i == now_page) else\
                               ('<a href="%s"><strong>%d</strong></a>' % (get_log_file_name(i, page_num), i))
            post_pagination += '&nbsp;'

        post_pagination += ('<span><strong>Next ></strong></span>') if (now_page == page_num) else\
                           ('<a href="%s"><strong>Next ></strong></a>' % get_log_file_name(now_page + 1, page_num))

        pagenation = log_template_pagination.substitute(post_pagination = post_pagination)
    elif page_num <= 100:
        # 総ページ数が12〜100のとき : [<< Prev 10][< Prev][1][2]...[11][Next >][Next 10 >>]
        navi_start = now_page - 5
        navi_end = now_page + 5
        if navi_start <= 0:
            navi_start = 1
            navi_end = 11
        elif navi_end > page_num:
            navi_start = page_num - 10
            navi_end = page_num
        else:
            pass

        post_pagination += ('<span><strong><< Prev 10</strong></span>') if (now_page == 1) else\
                           ('<a href="%s"><strong><< Prev 10</strong></a>' % get_log_file_name(max(1, now_page - 10), page_num))
        post_pagination += '&nbsp;'
        post_pagination += ('<span><strong>< Prev</strong></span>') if (now_page == 1) else\
                           ('<a href="%s"><strong>< Prev</strong></a>' % get_log_file_name(now_page - 1, page_num))
        post_pagination += '&nbsp;'

        for i in range(navi_start, navi_end + 1):
            post_pagination += ('<span class="post_pagination_curr"><strong>%d</strong></span>' % i) if (i == now_page) else\
                               ('<a href="%s"><strong>%d</strong></a>' % (get_log_file_name(i, page_num), i))
            post_pagination += '&nbsp;'

        post_pagination += ('<span><strong>Next ></strong></span>') if (now_page == page_num) else\
                           ('<a href="%s"><strong>Next ></strong></a>' % get_log_file_name(now_page + 1, page_num))
        post_pagination += '&nbsp;'
        post_pagination += ('<span><strong>Next 10 >></strong></span>') if (now_page == page_num) else\
                           ('<a href="%s"><strong>Next 10 >></strong></a>' % get_log_file_name(min(now_page + 10, page_num), page_num))
        pagenation = log_template_pagination.substitute(post_pagination = post_pagination)
    else:
         # 総ページ数が101〜のとき : [<<< Prev 100][<< Prev 10][< Prev][1][2]...[11][Next >][Next 10 >>][Next 100 >>>]
        navi_start = now_page - 5
        navi_end = now_page + 5
        if navi_start <= 0:
            navi_start = 1
            navi_end = 11
        elif navi_end > page_num:
            navi_start = page_num - 10
            navi_end = page_num
        else:
            pass

        post_pagination += ('<span><strong><<< Prev 100</strong></span>') if (now_page == 1) else\
                           ('<a href="%s"><strong><<< Prev 100</strong></a>' % get_log_file_name(max(1, now_page - 100), page_num))
        post_pagination += '&nbsp;'
        post_pagination += ('<span><strong><< Prev 10</strong></span>') if (now_page == 1) else\
                           ('<a href="%s"><strong><< Prev 10</strong></a>' % get_log_file_name(max(1, now_page - 10), page_num))
        post_pagination += '&nbsp;'
        post_pagination += ('<span><strong>< Prev</strong></span>') if (now_page == 1) else\
                           ('<a href="%s"><strong>< Prev</strong></a>' % get_log_file_name(now_page - 1, page_num))
        post_pagination += '&nbsp;'

        for i in range(navi_start, navi_end + 1):
            post_pagination += ('<span class="post_pagination_curr"><strong>%d</strong></span>' % i) if (i == now_page) else\
                               ('<a href="%s"><strong>%d</strong></a>' % (get_log_file_name(i, page_num), i))
            post_pagination += '&nbsp;'

        post_pagination += ('<span><strong>Next ></strong></span>') if (now_page == page_num) else\
                           ('<a href="%s"><strong>Next ></strong></a>' % get_log_file_name(now_page + 1, page_num))
        post_pagination += '&nbsp;'
        post_pagination += ('<span><strong>Next 10 >></strong></span>') if (now_page == page_num) else\
                           ('<a href="%s"><strong>Next 10 >></strong></a>' % get_log_file_name(min(now_page + 10, page_num), page_num))
        post_pagination += '&nbsp;'
        post_pagination += ('<span><strong>Next 100 >>></strong></span>') if (now_page == page_num) else\
                           ('<a href="%s"><strong>Next 100 >>></strong></a>' % get_log_file_name(min(now_page + 100, page_num), page_num))
        pagenation = log_template_pagination.substitute(post_pagination = post_pagination)
    
    return pagenation

# main関数
def main():
    parser = argparse.ArgumentParser(description='teacup. BBS logging program - © suwasakix 2022, licensed under the MIT license.')
    parser.add_argument('url', type=str, help='teacup. BBS URL (ex. https://XXXX.teacup.com/YYYYYYYY/bbs")')
    parser.add_argument('-B', '--background', action='store_true', help='running Selenium with headless Chrome')
    parser.add_argument('-P', '--pages', nargs=1, type=int, default=None, help='the maximum number of pages to load')
    parser.add_argument('-N', '--posts-per-page', nargs=1, type=int, default=None, help='the number of posts per page')
    parser.add_argument('-T', '--bbs-title', nargs=1, type=str, default=None, help='BBS Title')
    parser.add_argument('-I', '--bbs-info-file', nargs=1, type=str, default=None, help='BBS information file (HTML format)')
 
    args = parser.parse_args()

    # 掲示板のURL (ex. "https://XXXX.teacup.com/YYYYYYYY/bbs")
    bbs_url = args.url
    bbs_url = re.sub('/$', '', bbs_url)
    print('BBS URL: %s' % bbs_url)

    # 掲示板のroot URL (ex. "https://XXXX.teacup.com/YYYYYYYY")
    bbs_root_url = bbs_url.rsplit('/', 1)[0]
    print('BBS root URL: %s' % bbs_root_url)

    # 投稿本文に記入されたURLの先頭に付加される文字列 (ex. "/YYYYYYYY/bbs?M=JU&amp;JUR=")
    bbs_article_href_header = '/' + bbs_url.rsplit('/', 2)[1] + '/bbs?M=JU&amp;JUR=' 
    #print('URL Header: %s' % bbs_article_href_header)

    # ロードする最大ページ数 (--pages) が指定されていれば受け付ける
    pages_arg = None
    if args.pages != None:
        pages_arg = args.pages[0]

    # ログファイル (１ページ) あたりの投稿表示件数 (--posts-per-page) が指定されていれば受け付ける
    posts_per_page_arg = None
    if args.posts_per_page != None:
        posts_per_page_arg = args.posts_per_page[0]

    # 掲示板タイトル (--bbs-title) が指定されていれば受け付ける
    bbs_title_arg = None
    if args.bbs_title != None:
        bbs_title_arg = args.bbs_title[0]

    # 掲示板情報ファイル (--bbs-info-file) が指定されていれば読み込む
    bbs_info_arg = None
    if args.bbs_info_file != None:
        bbs_info_file_name = args.bbs_info_file[0]
        print('BBS information file: %s' % bbs_info_file_name)
        try:
            with open(bbs_info_file_name, mode = 'r') as f:
                bbs_info_arg = f.read()
        except OSError as err:
            print('Warning(%d): cannot open BBS information file "%s" - %s' % (getframeinfo(currentframe()).lineno, bbs_info_file_name, err))

    # 画像ファイルの保存先ディレクトリ (img/bbs) を作成
    img_path = "img/bbs"
    if not os.path.exists(img_path): 
        os.makedirs(img_path)

    # WebDriverで操作するブラウザにChromeを指定する
    options = selenium.webdriver.ChromeOptions()
    if args.background == True:
        options.add_argument("--headless")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # 
    options.use_chromium = True
    driver = selenium.webdriver.Chrome(options=options)

    # ブラウザでWebサイトを開く
    driver.get(bbs_url) 

    # ページロードが完了するまで待つ
    WebDriverWait(driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

    # 掲示板タイトル
    bbs_title = driver.title
    if bbs_title_arg == None:
        print('BBS title: %s' % bbs_title)
    else:
        print('BBS title: %s' % bbs_title)
        print('Title of log file: %s' % bbs_title_arg)
        bbs_title = bbs_title_arg

    # 掲示板情報 (掲示板タイトル直下の説明文)
    bbs_info = None
    try:
        bbs_info = driver.find_element(By.XPATH, '//*[@class="bbstitle_margin"]/p').get_attribute('innerHTML')
    except selenium.common.exceptions.NoSuchElementException:
        pass
    if bbs_info_arg != None:
        bbs_info = bbs_info_arg

    # 掲示板の総投稿件数 ("全XXXX件の内、新着の記事からXX件ずつ表示します。" から抽出)
    total_posts = int(re.search(r'全\d+件', driver.find_elements(By.CLASS_NAME, 'pagination')[0].text).group()[1:-1])
    print('The number of posts in BBS: %d' % total_posts)

    # 掲示板1ページあたりの投稿件数 ("全XXXX件の内、新着の記事からXX件ずつ表示します。" から抽出)
    posts_per_page_org = int(re.search(r'\d+件ずつ', driver.find_elements(By.CLASS_NAME, 'pagination')[0].text).group()[0:-3])
    posts_per_page = posts_per_page_org
    if posts_per_page_arg == None:
        print('The number of posts per page: %d' % posts_per_page)
    else:
        print('The number of posts per page: %d' % posts_per_page_org)
        print('The number of posts per page of log file: %d' % posts_per_page_arg)
        posts_per_page = posts_per_page_arg

    # 掲示板の総ページ数 (ページ移動ボタンの左側の数値を抽出)
    total_pages = int(re.search(r'\d+', driver.find_elements(By.CLASS_NAME, 'form_navi')[0].text).group())
    if pages_arg == None:
        print('The number of pages in BBS: %d' % total_pages)
    else:
        print('The number of pages in BBS: %d' % total_pages)
        print('The number of pages to load: %d' % pages_arg)
        total_pages = pages_arg

    # 掲示板の背景色
    bbs_background_color = driver.find_element(By.XPATH, '/html/body').value_of_css_property("background-color")
    #print(bbs_background_color)
    # 掲示板の背景画像
    bbs_background_image = driver.find_element(By.XPATH, '/html/body').value_of_css_property("background-image")
    #print(bbs_background_image)
    # 掲示板のフォント
    bbs_font_family = driver.find_element(By.XPATH, '/html/body').value_of_css_property("font-family")
    #print(bbs_font_family)
    # 掲示板本文の文字色
    bbs_text_color = driver.find_element(By.XPATH, '/html/body').value_of_css_property("color")
    #print(bbs_text_color)
    # 掲示板タイトルの文字色
    bbs_title_color = driver.find_element(By.XPATH, '//*[@class="bbstitle_margin"]/h1/a').value_of_css_property("color")
    #print(bbs_title_color)
    # 投稿タイトルの文字色
    last_post = driver.find_element(By.XPATH, '//*[@id="contents"]/table')
    post_title_color = last_post.find_element(By.CLASS_NAME, 'Kiji_Title').value_of_css_property("color")
    #print(post_title_color)
    # 投稿者の文字色
    post_author_color = last_post.find_element(By.CLASS_NAME, 'Kiji_Author').value_of_css_property("color")
    #print(post_author_color)

    # リンクの色
    css_style = driver.find_element(By.XPATH, '/html/head/style').get_attribute('innerHTML').strip('\r\n !-<>/')
    link_color = re.search(r'#......', re.search(r' i{(.|\s)*?}', css_style).group()).group()
    #print(link_color)
    # 訪問済みリンクの色
    link_visited_color = re.search(r'#......', re.search(r'a:visited{(.|\s)*?}', css_style).group()).group()
    #print(link_visited_color)
    # アクティブリンクの色
    link_active_color = re.search(r'#......', re.search(r'a:active{(.|\s)*?}', css_style).group()).group()
    #print(link_active_color)

    # 背景画像ファイルのURL
    bbs_background_img_url = re.sub(r'^.*url\("', "", re.sub(r'"\).*$', "", bbs_background_image))
    #print(bbs_background_img_url)
    if os.path.splitext(bbs_background_img_url)[1] != '':
        # 背景画像ファイルの保存先パス (ex. "img/bbs/XXXXXXXX.jpg")
        bbs_background_img_path = 'img/bbs/' + os.path.split(bbs_background_img_url)[1]
        #print(bbs_background_img_path)

        # 背景画像ファイルが存在したらダウンロードして保存
        try:
            res = requests.get(bbs_background_img_url)
            res.raise_for_status()
        except requests.exceptions.RequestException as err:
            print('Warning(%d): cannot get background image file "%s" - %s' %\
                  (getframeinfo(currentframe()).lineno, bbs_background_img_url, err))
        else:
            try:
                with open(bbs_background_img_path, mode = "wb") as f:
                    f.write(res.content)
                    bbs_background_image = 'url(' + bbs_background_img_path + ')'
                    print('Saved background image file as %s' % bbs_background_img_path)
            except OSError as err:
                print('Warning(%d): cannot save background image file "%s" - %s' %\
                      (getframeinfo(currentframe()).lineno, bbs_background_img_path, err))

    # 投稿情報の一時保存用配列
    post_info_array = []

    # 投稿読み取り件数カウンタ
    post_scrape_count = 1
    print('')

    # 掲示板の全ページ読み出し
    for i in range(1, total_pages + 1):
        # ページ番号入力ボックス
        PageNumber = driver.find_element(By.XPATH, '//input[@name="page"]')
        # ページ移動ボタン
        PageJump = driver.find_element(By.XPATH, '//input[@value="ページ移動"]')

        # 掲示板投稿項目の抽出
        for element in driver.find_elements(By.XPATH, '//*[@id="contents"]/table'):
            print('\rScraping post... %d / %d' % (post_scrape_count, min(posts_per_page_org * total_pages, total_posts)), end='')

            # 投稿タイトル
            title = element.find_element(By.CLASS_NAME, 'Kiji_Title').text
            #print(title)
            # 投稿番号
            number = int(element.find_element(By.CLASS_NAME, 'Kiji_Title').get_attribute('name'))
            #print(number)
            # 投稿者
            author = element.find_element(By.CLASS_NAME, 'Kiji_Author').text
            #print(author)
            # 投稿日時 ("XXXX年 X月XX日(X)XX時XX分XX秒")
            created = element.find_element(By.CLASS_NAME, 'Kiji_Created').text
            datetime_search = re.search(r'\d{4}年.*秒', created)
            datetime = created if (datetime_search == None) else datetime_search.group()
            #print(datetime)
            # 投稿元ホスト ("XXXX年 X月XX日(X)XX時XX分XX秒" の後ろに存在する場合のみ抽出)
            created_html = element.find_element(By.CLASS_NAME, 'Kiji_Created').get_attribute('innerHTML')
            remotehost_search = re.search(r'秒.*$', created_html)
            remotehost = '' if (remotehost_search == None) else remotehost_search.group().lstrip('秒').strip(' !-<>')
            #print(remotehost)
            # 元記事の投稿番号 (存在する場合のみ抽出)
            #print(element.text)
            parent_search = re.search(r'No\.\d+\[元記事へ\]', element.text)
            parent = None if (parent_search == None) else int(parent_search.group()[3:-6])
            #print(parent)
            # 投稿本文（HTML形式）
            article = element.find_element(By.CLASS_NAME, 'Kiji_Article').get_attribute('innerHTML')
            article = modify_href_strings_in_article(article, bbs_article_href_header)
            #print(article)

            # 画像ファイル情報の一時保存先
            img_info_array = []

            # 添付画像ファイルの抽出
            for image in element.find_elements(By.CLASS_NAME, 'Kiji_Img'):

                # 元画像ファイルのURL (ex. "https://XXXX.teacup.com/YYYYYYYY/img/bbs/NNNNNNNN.jpg") ※ 存在しない場合あり
                original_img = None
                original_img_url = None
                try:
                   original_img = image.find_element(By.TAG_NAME, 'a')
                   original_img_url = original_img.get_attribute('href')
                except selenium.common.exceptions.NoSuchElementException:
                   pass
                #print(original_img_url)
                # サムネイル画像ファイルのURL (ex. "https://XXXX.teacup.com/YYYYYYYY/img/bbs/NNNNNNNN_M.jpg") ※ 存在しない場合あり
                thumbnail_img = None
                thumbnail_img_url = None
                try:
                    thumbnail_img = image.find_element(By.TAG_NAME, 'img')
                    thumbnail_img_url = thumbnail_img.get_attribute('src')
                except selenium.common.exceptions.NoSuchElementException:
                    pass
                #print(thumbnail_img_url)

                # 元画像ファイルの保存先パス (ex. "img/bbs/NNNNNNNN.jpg")
                original_img_path = None
                if original_img_url != None:
                    original_img_path = original_img_url.replace(bbs_root_url + '/', '')
                #print(original_img_path)
                # サムネイル画像ファイルの保存先パス (ex. "img/bbs/NNNNNNNN_M.jpg")
                thumbnail_img_path = None
                if thumbnail_img_url != None:
                    thumbnail_img_path = thumbnail_img_url.replace(bbs_root_url + '/', '')
                #print(thumbnail_img_path)

                if (original_img_path != None) or (thumbnail_img_path != None):
                    img_info = {'original_img_path': original_img_path, 'thumbnail_img_path': thumbnail_img_path}
                    img_info_array.append(img_info)

                # 元画像ファイルをダウンロードして保存
                if original_img_url != None:
                    try:
                        res = requests.get(original_img_url)
                        res.raise_for_status()
                    except requests.exceptions.RequestException as err:
                        print('', end='\n')
                        print('Warning(%d): cannot get image file "%s" - %s' %\
                              (getframeinfo(currentframe()).lineno, original_img_url, err))
                    else:
                        try:
                            with open(original_img_path, mode = "wb") as f:
                                f.write(res.content)
                        except OSError as err:
                            print('', end='\n')
                            print('Warning(%d): cannot save image file "%s" - %s' %\
                                  (getframeinfo(currentframe()).lineno, original_img_path, err))

                # サムネイル画像ファイルをダウンロードして保存
                if thumbnail_img_path != None:
                    try:
                        res = requests.get(thumbnail_img_url)
                        res.raise_for_status()
                    except requests.exceptions.RequestException as err:
                        print('', end='\n')
                        print('Warning(%d): cannot get image file "%s" - %s' %\
                              (getframeinfo(currentframe()).lineno, thumbnail_img_url, err))
                    else:
                        try:
                            with open(thumbnail_img_path, mode = "wb") as f:
                                f.write(res.content)
                        except OSError as err:
                            print('', end='\n')
                            print('Warning(%d): cannot save image file "%s" - %s' %\
                                  (getframeinfo(currentframe()).lineno, thumbnail_img_path, err))

            post_info = {'title': title,\
                         'number': number,\
                         'author': author,\
                         'datetime': datetime,\
                         'remotehost': remotehost,\
                         'parent': parent,\
                         'article': article,\
                         'img_info_array': img_info_array}
            post_info_array.append(post_info)

            post_scrape_count += 1

        # 次のページに移動
        PageNumber.send_keys()
        PageNumber.send_keys(str(i + 1))
        PageJump.click()

    # ページロードが完了するまで待つ
    WebDriverWait(driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

    # 掲示板の全ページ読み出し完了
    print('', end='\n')
    print('Scraping completed.')
    print('')

    # 一時保存した投稿件数
    post_info_num = len(post_info_array)
    print('Scrape %d posts from BBS "%s"' % (post_info_num, bbs_url))

    # 一時保存情報の確認用
    #for i in range(0, post_info_num):
    #    print('Index[%d]' % i)
    #    print('  title: %s' % post_info_array[i]['title'])
    #    print('  number: %d' % post_info_array[i]['number'])
    #    print('  author: %s' % post_info_array[i]['author'])
    #    print('  datetime: %s' % post_info_array[i]['datetime'])
    #    print('  remotehost: %s' % post_info_array[i]['remotehost'])
    #    print('  parent: %d' % post_info_array[i]['parent'])
    #    print('  article: %s' % post_info_array[i]['article'])
    #
    #    img_info_array = post_info_array[i]['img_info_array']
    #    img_info_num = len(img_info_array)
    #    print('  img_info_array_len: %d' % img_info_num)
    #    for k in range (0, img_info_num):
    #        print('  [%d] original_img_path: %s' % (k, img_info_array[k]['original_img_path']))
    #        print('  [%d] thumbnail_img_path: %s' % (k, img_info_array[k]['thumbnail_img_path']))
    #    print('')

    # ログファイルの数
    log_file_num = math.ceil(post_info_num / posts_per_page)
    print('Save the posts to %d log files' % log_file_num)

    # 元記事へのリンクを生成
    for i in range(0, post_info_num):
        parent = post_info_array[i]['parent']
        if parent == None:
            parent_str = ''
        else:
            now_page_no = math.ceil((i + 1) / posts_per_page)
            parent_page_no = None
            for k in range (i, post_info_num):
                n = post_info_array[k]['number']
                if n == parent:
                    # 元記事が見つかった場合
                    parent_page_no = math.ceil((k + 1) / posts_per_page)
                elif n < parent:
                    # 元記事が見つからない (おそらく削除されている)
                    break
                else:
                    pass

            if parent_page_no == None:
                parent_str = ('&gt; No.%d[元記事へ]<br /><br />' % parent)
            else:
                if now_page_no == parent_page_no:
                    href = ('#%d' % parent)
                else:
                    href = ('%s#%d' % (get_log_file_name(parent_page_no, log_file_num), parent))
                parent_str = ('&gt; <a href="%s">No.%d[元記事へ]</a><br /><br />' % (href, parent))

        post_info_array[i]['parent_str'] = parent_str
           

    # 投稿保存件数カウンタ
    post_save_count = 0

    # ログファイルの保存
    for i in range(1, log_file_num + 1):
        log_file_name = get_log_file_name(i, log_file_num);
        print('\rSaving log file... %d / %d' % (i, log_file_num), end='')

        try:
            with open(log_file_name, mode = 'w', encoding = 'utf-8') as f:
                log_text_head = log_template_head.substitute(bbs_title = bbs_title,\
                                                             bbs_background_color = bbs_background_color,\
                                                             bbs_background_image = bbs_background_image,\
                                                             bbs_font_family = bbs_font_family,\
                                                             bbs_text_color = bbs_text_color,\
                                                             bbs_title_color = bbs_title_color,\
                                                             post_title_color = post_title_color,\
                                                             post_author_color = post_author_color,\
                                                             link_color = link_color,\
                                                             link_visited_color = link_visited_color,\
                                                             link_active_color = link_active_color)
                f.write(log_text_head)

                log_text_header = ''
                if bbs_info == None:
                    log_text_header = log_template_header.substitute(bbs_title = bbs_title)
                else:
                    log_text_header = log_template_header_with_bbs_info.substitute(bbs_title = bbs_title, bbs_info = bbs_info)
                f.write(log_text_header)

                log_text_paginaton = make_pagination(i, log_file_num, log_template_pagination_top)
                f.write(log_text_paginaton)
            
                for k in range (0, posts_per_page):
                    post = post_info_array[post_save_count]
                    log_text_post = log_template_post.substitute(post_title = post['title'],\
                                                                 post_number = str(post['number']),\
                                                                 post_author = post['author'],\
                                                                 post_datetime = post['datetime'],\
                                                                 post_remotehost = post['remotehost'],\
                                                                 post_parent = post['parent_str'],\
                                                                 post_article = post['article'])
                    f.write(log_text_post)

                    img_info_array = post['img_info_array']
                    img_info_num = len(img_info_array)
                    for n in range (0, img_info_num):
                        img = img_info_array[n]
                        if img['original_img_path'] == None:
                            log_text_img = log_template_img_m.substitute(thumbnail_img_path = img['thumbnail_img_path'])
                        else:
                            log_text_img = log_template_img.substitute(original_img_path = img['original_img_path'],\
                                                                       thumbnail_img_path = img['thumbnail_img_path'])
                        f.write(log_text_img)

                    post_save_count += 1
                    if post_save_count >= post_info_num:
                        break;

                    if k < (posts_per_page - 1):
                         # 投稿の間は<hr>で区切る
                         f.write('\n<hr>\n\n')

                log_text_paginaton = make_pagination(i, log_file_num, log_template_pagination_bottom)
                f.write(log_text_paginaton)
            
                log_text_footer = log_template_footer.substitute()
                f.write(log_text_footer)
        except OSError as err:
            print('', end='\n')
            print('Warning(%d): cannot save log file "%s" - %s' % (getframeinfo(currentframe()).lineno, log_file_name, err))

    # WebDriverを終了
    driver.close()
    driver.quit()

    print('', end='\n')
    print('All done.')
    print('')

if __name__ == '__main__':
    main()

