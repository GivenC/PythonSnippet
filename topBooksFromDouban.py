#!/usr/bin/env python
#! encoding=utf-8

# Author        : kesalin@gmail.com
# Blog          : http://kesalin.github.io
# Date          : 2016/07/13
# Description   : 抓取豆瓣上指定标签的书籍并导出为 Markdown 文件，多线程版本. 
# Version       : 1.0.0.0
# Python Version: Python 2.7.3
# Python Queue  : https://docs.python.org/2/library/queue.html
# Beautiful Soup: http://beautifulsoup.readthedocs.io/zh_CN/v4.4.0/#

import os
import time
import timeit
import datetime
import re
import string
import urllib2
import math

from threading import Thread
from Queue import Queue
from bs4 import BeautifulSoup

gHeader = {"User-Agent": "Mozilla-Firefox5.0"}

# 书籍信息类
class BookInfo:
    name = ''
    url = ''
    icon = ''
    ratingNum = 0.0
    ratingPeople = 0
    comment = ''
    compositeRating = 0.0

    def __init__(self, name, url, icon, num, people, comment):
        self.name = name
        self.url = url
        self.icon = icon
        self.ratingNum = num
        self.ratingPeople = people
        self.comment = comment 

    def __sortByRating(self, other):
        val = self.ratingNum - other.ratingNum
        if val < 0:
            return 1
        elif val > 0:
            return -1
        else:
            val = self.ratingPeople - other.ratingPeople
            if val < 0:
                return 1
            elif val > 0:
                return -1
            else:
                return 0

    def getCompositeRating(self):
        if self.compositeRating == 0.0:
            k = 0.25
            people = max(5, min(5000, self.ratingPeople))
            peopleWeight = math.pow(people, k)
            if people < 50:
                self.compositeRating = (self.ratingNum * 40 + peopleWeight * 60) / 100.0
            elif people < 100:
                self.compositeRating = (self.ratingNum * 50 + peopleWeight * 50) / 100.0
            elif people < 200:
                self.compositeRating = (self.ratingNum * 60 + peopleWeight * 40) / 100.0
            elif people < 400:
                self.compositeRating = (self.ratingNum * 70 + peopleWeight * 30) / 100.0
            elif people < 800:
                self.compositeRating = (self.ratingNum * 80 + peopleWeight * 20) / 100.0
            else:
                self.compositeRating = (self.ratingNum * 90 + peopleWeight * 10) / 100.0

        return self.compositeRating

    def __sortByCompositeRating(self, other):
        rhs = other.getCompositeRating()
        val = self.getCompositeRating() - other.getCompositeRating()
        if val < 0:
            return 1
        elif val > 0:
            return -1
        else:
            return 0

    def __cmp__(self, other):
        return self.__sortByCompositeRating(other)

# 获取 url 内容
def getHtml(url):
    try :
        request = urllib2.Request(url, None, gHeader)
        response = urllib2.urlopen(request)
        data = response.read().decode('utf-8')
        return data
    except urllib2.URLError, e :
        if hasattr(e, "code"):
            print "The server couldn't fulfill the request: " + url
            print "Error code: %s" % e.code
        elif hasattr(e, "reason"):
            print "We failed to reach a server. Please check your url: " + url + ", and read the Reason."
            print "Reason: %s" % e.reason
    return None

# 导出为 Markdown 格式文件
def exportToMarkdown(gTag, books):
    path = "{0}.md".format(gTag)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('## {0}\n\n'.format(gTag))
    file.write('## 图书列表\n\n')
    file.write('### 总计 {0} 本，更新时间：{1}\n'.format(len(books), todayStr))
    i = 0
    for book in books:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **图书名称**：[{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**：[{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **豆瓣评分**：{0}  \n'.format(book.ratingNum))
        file.write(' > **评分人数**：{0}  \n'.format(book.ratingPeople))
        file.write(' > **内容简介**：{0}  \n'.format(book.comment))
        i = i + 1
    file.close()

# 解析图书信息
def parseItemInfo(page, bookInfos):
    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("li", "subject-item")
    for item in items:
        #print item.prettify().encode('utf-8')

        # get book name
        bookName = ''
        content = item.find("h2")
        if content != None:
            href = content.find("a")
            if href != None:
                bookName = href['title'].strip().encode('utf-8')
                span = href.find("span")
                if span != None and span.string != None:
                    subTitle = span.string.strip().encode('utf-8')
                    bookName = '{0}{1}'.format(bookName, subTitle)
        #print " > name: {0}".format(bookName)

        # get description
        description = ''
        content = item.find("p")
        if content != None:
            description = content.string.strip().encode('utf-8')
        #print " > description: {0}".format(description)

        # get book url and image
        bookUrl = ''
        bookImage = ''
        content = item.find("div", "pic")
        if content != None:
            tag = content.find('a')
            if tag != None:
                bookUrl = tag['href'].encode('utf-8')
            tag = content.find('img')
            if tag != None:
                bookImage = tag['src'].encode('utf-8')
        #print " > url: {0}, image: {1}".format(bookUrl, bookImage)

        # get rating
        ratingNum = 0.0
        ratingPeople = 0
        content = item.find("span", "rating_nums")
        if content != None:
            ratingStr = content.string.strip().encode('utf-8')
            if len(ratingStr) > 0:
                ratingNum = float(ratingStr)
        content = item.find("span", "pl")
        if content != None:
            ratingStr = content.string.strip().encode('utf-8')
            pattern = re.compile(r'(\()([0-9]*)(.*)(\))')
            match = pattern.search(ratingStr)
            if match:
                ratingStr = match.group(2).strip()
                if len(ratingStr) > 0:
                    ratingPeople = int(ratingStr)
        #print " > ratingNum: {0}, ratingPeople: {1}".format(ratingNum, ratingPeople)

        # add book info to list
        bookInfo = BookInfo(bookName, bookUrl, bookImage, ratingNum, ratingPeople, description)
        bookInfo.getCompositeRating()
        bookInfos.append(bookInfo)

#=============================================================================
# 生产者-消费者模型
#=============================================================================
gQueue = Queue(20)
gBookInfos = []

class Producer(Thread):
    url = ''
    
    def __init__(self, t_name, url):  
        Thread.__init__(self, name=t_name)
        self.url = url

    def run(self):
        global gQueue

        page = getHtml(self.url)
        if page != None:
            # block util a free slot available
            gQueue.put(page, True)

class Consumer(Thread):
    running = True

    def __init__(self, t_name):  
        Thread.__init__(self, name=t_name)

    def stop(self):
        self.running = False

    def run(self):
        global gQueue
        global gBookInfos

        while True:
            if self.running == False and gQueue.empty():
                break;

            page = gQueue.get()
            if page != None:
                parseItemInfo(page, gBookInfos)
            gQueue.task_done()
 

#=============================================================================
# 程序入口：抓取指定标签的书籍
#=============================================================================
gTag = "心理学"
gTagUrl = "https://book.douban.com/tag/{0}".format(gTag)

if __name__ == '__main__': 
    print ' > getting books of {0} ...'.format(gTag)
    start = timeit.default_timer()

    # all producers
    producers = []

    # get first page of doulist
    page = getHtml(gTagUrl)
    if page == None:
        print ' > invalid url {0}'.format(gTagUrl)
    else:
        # get url of other pages in doulist
        soup = BeautifulSoup(page, 'html.parser')
        content = soup.find("div", "paginator")
        #print content.prettify().encode('utf-8')

        nextPageStart = 100000
        lastPageStart = 0
        for child in content.children:
            if child.name == 'a':
                pattern = re.compile(r'(start=)([0-9]*)(.*)(&type=)')
                match = pattern.search(child['href'].encode('utf-8'))
                if match:
                    index = int(match.group(2))
                    if nextPageStart > index:
                        nextPageStart = index
                    if lastPageStart < index:
                        lastPageStart = index

        # process current page
        print " > process page:{0}".format(gTagUrl)
        gQueue.put(page)

        # create consumer
        consumer = Consumer('Consumer')
        consumer.start()

        # create producers
        producers = []
        for pageStart in range(nextPageStart, lastPageStart + nextPageStart, nextPageStart):
            pageUrl = "{0}?start={1:d}&type=T".format(gTagUrl, pageStart)
            producer = Producer('Producer_{0:d}'.format(pageStart), pageUrl)
            producer.start()
            producers.append(producer)
            print " > process page:{0}".format(pageUrl)
            time.sleep(0.1)         # slow down a little

        # wait for all producers
        for producer in producers:
            producer.join()

        # wait for consumer
        consumer.stop()
        gQueue.put(None)
        consumer.join()

        # sort
        books = sorted(gBookInfos)

        # export to markdown
        exportToMarkdown(gTag, books)

        # summrise
        total = len(books)
        elapsed = timeit.default_timer() - start
        print " > 共获取 {0} 本图书信息，耗时 {1} 秒".format(total, elapsed)
