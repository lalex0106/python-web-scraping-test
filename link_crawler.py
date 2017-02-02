# -*- coding: utf-8 -*-
# link_crawler
# modified by lalex0106 @ 2017.1.30
# 主函数为link_crawler，根据规则爬取某主页下的网页超链接
import re
import urlparse
import urllib2
import time
from datetime import datetime
import robotparser
import Queue
import csv
import lxml.html

# 处理写入文件时是中文字符的错误
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

def link_crawler(seed_url, link_regex= None, delay =5, max_depth=-1, max_urls=-1, headers={}, user_agent='lining', proxy=None, num_retries =1, scrape_callback=None):
	# 利用seed_url生成双端队列，后文仅在右侧操作,[]将字符串转换为list
	# crawl_queue = Queue.deque([seed_url])
	crawl_queue = [seed_url]
	# 初始化seen为dict，其中seed_url不能为list，可以是tuple,string
	seen = {seed_url:0}
	num_urls = 0
	# 自定义函数，利用robotparser获得网站的robots.txt文件，生成RobotFileParser对象
	rp = get_robots(seed_url)
	# 初始化限制下载速度的Throttle类实例
	throttle = Throttle(delay)
	headers = headers or {}
	if user_agent:
		headers['User-agent'] = user_agent
	# 当queue非空时一直处理
	while crawl_queue:
		url = crawl_queue.pop()
		if rp.can_fetch(user_agent, url):
			# 默认下载时间限制为5秒
			throttle.wait(url)
			# 自定义函数，用url获取返回的html内容
			html = download(url, headers, proxy=proxy, num_retries=num_retries)
			links = []
			# depth临时存放了本次循环的url的访问次数，通常最大访问次数为1
			depth = seen[url]
			# 自定义回调函数或回调类，通常是为了保存和分析下载的数据
			# 本函数传入url是为了只处理特定url的html数据，目的是分解保存国家的各种数据到csv中
			if scrape_callback:
				links.extend(scrape_callback(url, html) or [])
			if depth != max_depth:
				if link_regex:
					html = get_links(html)
					# 将所有绝对链接转化为相对链接
					html = [link.replace(seed_url,'') for link in html]
					# 获取html文档中所有符合link_regex规则的url链接（间接地址）
					links.extend(link for link in html if re.match(link_regex,link))
				for link in links:
					# 自定义函数，去除片段标识符并转化为绝对地址					
					link = normalize(seed_url, link)
					if link not in seen:
						seen[link] = depth +1
						# 只有当link与主页的netloc相同时才下载
						if same_domain(seed_url, link):
							crawl_queue.append(link)
			# 测试是否达到最大下载数
			num_urls +=1
			if num_urls == max_urls:
				break
		else:
			print 'Blocked by robots.txt', url

# 使用回调类而不是回调函数，以保持csv中writer属性的状态
class ScrapeCallback:
	# 本类实现的功能是将view标签下的国家页面需要提取的信息保存到csv中
	def __init__(self):
		self.writer = csv.writer(open('countries.csv', 'w'))
		self.fields = ('area', 'population', 'iso', 'country', 'capital', 'continent', 'tld', 'currency_code', 'currency_name', 'phone', 'postal_code_format', 'postal_code_regex', 'languages', 'neighbours')
		self.writer.writerow(self.fields)
	def __call__(self, url, html):
		if re.search('/view/', url):
			tree = lxml.html.fromstring(html)
			row =[]
			for field in self.fields:
				row.append(tree.cssselect('table > tr#places_{}__row > td.w2p_fw'.format(field))[0].text_content())
			self.writer.writerow(row)

# sublime多行注释为command+/，为使代码复用，移植到类中
# def scrape_callback(url, html):
# 	if re.search('/view/', url):
# 		tree= lxml.html.fromstring(html)
# 		row= [tree.cssselect('table>tr#places_%s__row>td.w2p_fw' % field)[0].text_content() for field in FIELDS]
# 		print url, row
class ScrapeDoubanBook:
	# 自定义豆瓣图书爬取数据，还不能正常工作
	def __init__(self):
		self.writer = csv.writer(open('douban_book.csv', 'w'))
		# self.fields = ('作者','出版社','出版年','页数','定价','装帧','ISBN')
		self.fields = ('Author','Press','Publication_year','Pages','Price','Binding','ISBN')
		self.writer.writerow(self.fields)
	def __call__(self,url, html):
		if re.search('/subject/', url):
			tree=lxml.html.fromstring(html)
			row=[]
			# 获取作者姓名
			row.append(tree.xpath('//*[@id="info"]/span[1]/a/text()')[0])
			for i in range(1,7):
				# 依次获取出版社、出版年、页数、定价、装帧、ISBN
				row.append(tree.xpath('//*[@id="info"]/text()[%d]' % (i*2+1))[0])
			self.writer.writerow(row)

class Throttle:
	def __init__(self, delay):
		# tt=Throttle(5)
		self.delay =delay
		# domain存放某主页地址上次访问的datetime
		self.domains ={}
	def wait(self, url):
		# 一个URL由六部分组成，scheme://netloc/path;parameters?query#fragment
		# urlparse.urlparse('http://www.netloc.com:8000/%7.html;abc?que#frag')返回6-tuple
		# domain获得了主页网址
		domain = urlparse.urlparse(url).netloc
		# dict.get('key')根据查询的key返回value，如果不存在key，返回None
		last_accessed = self.domains.get(domain)
		if self.delay >0 and last_accessed is not None:
			# datetime(year, month, day[,hour[,minute[,second[,microsecond]]]])
			# 两个datetime相减是timedelta，可查询days,seconds,microseconds等
			sleep_secs = self.delay - (datetime.now() - last_accessed).seconds
			if sleep_secs >0:
				time.sleep(sleep_secs)
		self.domains[domain] = datetime.now()


def get_robots(url):
	rp = robotparser.RobotFileParser()
	rp.set_url(urlparse.urljoin(url, '/robots.txt'))
	rp.read()
	return rp

def get_links(html):
	# [^>]+ 表示至少一个非>的字符，通常为空格，即\s
	# ["\']表示匹配一个双引号或单引号
	# (.*?)表示匹配任意字符串存放到groups中
	# 本句匹配了以<a href=开头，包含在两个双引号或单引号之间的任意长度字符串
	webpage_regex = re.compile('<a[^>]+href=["\'](.*?)["\']',re.IGNORECASE)
	return webpage_regex.findall(html)

def normalize(seed_url, link):
	# urldefrag返回一个tuple，将url地址按#分段，主要是分离出fragment
	# http://example.com/document.txt#line=10,20 
	link, _ = urlparse.urldefrag(link) # remove hash to avoid duplicate
	return urlparse.urljoin(seed_url, link)

def same_domain(url1, url2):
	return urlparse.urlparse(url1).netloc == urlparse.urlparse(url2).netloc

def download(url, headers, proxy, num_retries =2, data = None):
	print 'Downloading:', url
	# data是个特定格式的字符串，不为空时，HTTP request调用Post而不是GET
	# 比如豆瓣的登陆request
	# urllib.urlencode({'source':'index_nav','form_email':'lgstala@163.com','form_password':'ln123456'})
	# urllib.urlencode((('source','index_nav'), ('form_email','lgstala@163.com'), ('form_password','ln123456')))
	# 经编码为source=index_nav&form_email=lgstala%40163.com&form_password=ln123456
	# headers是个dict，通常包括Cookie，Referer，User-agent等内容
	# 比如谷歌浏览器的代理为User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36
	# 注意headers是个dict，比如{}或者{'User-agent':'lalex'}
	request = urllib2.Request(url, data, headers)
	# build_opener()返回一个OpenerDirector类实例，可以捕获URLError或HTTPError
	opener = urllib2.build_opener()
	if proxy:
		proxy_params = {urlparse.urlparse(url).scheme: proxy}
		opener.add_handler(urllib2.ProxyHandler(proxy_params))
	try:
		# 使用open(request)获得response，
		response = opener.open(request)
		html = response.read()
		# 正常是200，5xx错误可以尝试重连
		code = response.code
	except urllib2.URLError as e:
		print 'Download error:', e.reason
		html = ''
		if hasattr(e, 'code'):
			code = e.code
			if num_retries>0 and 500 <= code <600:
				return download(url, headers, proxy, num_retries-1, data)
		else:
			code = None
	return html

if __name__ == '__main__':
	link_crawler('http://example.webscraping.com', '/(index|view)', delay=0, num_retries=1, user_agent='BadCrawler')
	link_crawler('http://example.webscraping.com', '/(index|view)', delay=0, num_retries=1, max_depth=1, user_agent='GoodCrawler')
	# 由于国家页面没有返回到超链接，只能爬取一次
	link_crawler('http://example.webscraping.com/view/Belarus-21', '/(index|view)', scrape_callback=ScrapeCallback())
	# 注意：上述link_regex只能获取href对应的是相对链接,下面示意的是绝对链接的提取
	link_crawler('https://book.douban.com','/subject', delay=0, num_retries=1, user_agent='lalex')
	link_crawler('https://book.douban.com','/subject', delay=0, num_retries=1, user_agent='lalex', scrape_callback=ScrapeDoubanBook())