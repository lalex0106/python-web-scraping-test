# python-web-scraping-test
基于python2.7的爬虫练习，主要根据Richard Lawson的《Web scraping with python》一书改写，加入大量中文注释

link_crawler的功能逐步添加，目前具有的功能有：
1、根据正则表达式规则访问某主页下的链接
2、下载限速
3、网页访问次数限制
4、某网站最大访问次数限制
5、自定义Request头文件，主要包括user-agent和proxy
6、访问失败（5xx）时重复访问
7、回调函数（保存数据到csv中）
使用说明：
link_crawler('http://example.webscraping.com', '/(index|view)', delay=0, num_retries=1, user_agent='BadCrawler')
link_crawler('http://example.webscraping.com', '/(index|view)', delay=0, num_retries=1, max_depth=1, user_agent='GoodCrawler')
link_crawler('http://example.webscraping.com/view/Belarus-21', '/(index|view)', scrape_callback=ScrapeCallback())
link_crawler('https://book.douban.com','/subject', delay=0, num_retries=1, user_agent='lalex')

performance的功能是测试正则表达式、Beautiful Soup和lxml解析html的效率。
使用说明：main()
