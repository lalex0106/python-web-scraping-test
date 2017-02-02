# -*- coding: utf-8 -*-

import csv
import time
import urllib2
import re
import timeit
from bs4 import BeautifulSoup
import lxml.html
# 根据FIELDS生成结果dict，批量获得所需信息
FIELDS= ('area', 'population', 'iso', 'country', 'capital', 'continent', 'tld', 'currency_code', 'currency_name', 'phone', 'postal_code_format', 'postal_code_regex', 'languages', 'neighbours')
# 使用正则表达式对html字符串提取关键信息
def regex_scraper(html):
	results={}
	for field in FIELDS:
		# format的第一个参数是用于替换正则表达式中的{}，因为需要提取的数据外层标签不一样，{}是format的用法
		results[field]=re.search('<tr id="places_{}__row">.*?<td class="w2p_fw">(.*?)</td>'.format(field), html).groups()[0]
	return results
# 使用BeautifulSoup对html字符串提取关键信息
def beautiful_soup_scraper(html):
	soup=BeautifulSoup(html, 'html.parser')
	results={}
	for field in FIELDS:
		results[field]=soup.find('table').find('tr',id='places_{}__row'.format(field)).find('td',class_='w2p_fw').text
	return results
# 使用lxml对html字符串提取关键信息
def lxml_scraper(html):
	tree=lxml.html.fromstring(html)
	results={}
	for field in FIELDS:
		results[field]=tree.cssselect('table > tr#places_{}__row > td.w2p_fw'.format(field))[0].text_content()
	return results

def main():
	times={}
	html=urllib2.urlopen('http://example.webscraping.com/view/United-Kingdom-239').read()
	NUM_ITERATIONS=1000
	# touple循环表达式，将三个函数名依次替换为scraper
	for name, scraper in ('Regular expressions', regex_scraper),('Beautiful Soup', beautiful_soup_scraper), ('Lxml', lxml_scraper):
		times[name]=[]
		# 将当前时间以秒为单位返回一个浮点数
		start=time.time()
		for i in range(NUM_ITERATIONS):
			if scraper == regex_scraper:
				# 正则表达式会缓存结果，需要清空正则表达式的缓存
				re.purge()
			result=scraper(html)
			# 检验结果是否符合预期
			assert(result['area'] == '244,820 square kilometres')
			# 将每次运行的累计耗时写入dict末端
			times[name].append(time.time()- start)
		end= time.time()
		print '{}:{:.2f} seconds'.format(name, end-start)
	# 将三段代码运行用时写入到csv文件中
	writer = csv.writer(open('times.csv','w'))
	header=sorted(times.keys())
	writer.writerow(header)
	# x=[1,2] y=[3,4] zip1=zip(x,y) zip1=[(1,3), (2,4)]，类似于矩阵转置
	# * 用来传递任意个无名字参数(可变参数)，这些参数会一个Tuple的形式访问
	# **用来处理传递任意个有名字的参数(关键字参数)，这些参数用dict来访问
	# tt={'a': [1, 2], 'c': [5, 6], 'b': [3, 4]}
	# hd=sorted(tt.keys())	hd=['a', 'b', 'c']
	# zip(*[tt[i] for i in hd])	zip=[(1, 3, 5), (2, 4, 6)]
	for row in zip(*[times[scraper] for scraper in header]):
		writer.writerow(row)

if __main__ == '__main__':
	main()
