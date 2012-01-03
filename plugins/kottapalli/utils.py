from xml.etree import ElementTree as etree 
import urllib
import datetime
import time
import web
import traceback

def memoize(f, timeout):
    cache = {}
    def g():
        # cache the value for timeout seconds
        t = time.time() / timeout
        if cache.get('time')  != t:
            cache['time'] = t
            cache['value'] = f()
        return cache['value']
    return g

def _get_blog_feeds():
    url = "http://blog.kottapalli.in/feeds/posts/default?alt=rss"
    try:
        tree = etree.parse(urllib.urlopen(url))
    except IOError:
        # Handle error gracefully.
        print >> web.debug, "Failed to fetch blog feeds"
        traceback.print_exc()
        return []
    
    def parse_item(item):
        pubdate = datetime.datetime.strptime(item.find("pubDate").text, '%a, %d %b %Y %H:%M:%S +0000')
        return web.storage(
            title=item.find("title").text,
            url=item.find("link").text,
            pubdate=pubdate,
            categories=[cat.text for cat in item.findall("category")]
        )
    return [parse_item(item) for item in tree.findall("//item")]

get_blog_feeds = memoize(_get_blog_feeds, 3600)

if __name__ == "__main__":
    print _get_blog_feeds()