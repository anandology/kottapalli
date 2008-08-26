import web
from infogami.utils import delegate, types
from infogami.utils.storage import OrderedDict
from infogami.utils.template import render
from infogami.utils.view import public, thingview, thingrepr, require_login
from infogami import config
from telugu_months import months as te_months
import datetime

import re
import os

types.register_type('^/[0-9][0-9][0-9][0-9]/[0-9][0-9]$',  '/type/issue')
types.register_type('^/[0-9][0-9][0-9][0-9]/[0-9][0-9]/.*$',  '/type/article')

@public
def getPlainText(text):
    """It takes a text(Body of page, it might have macros) and remove macros and html tags, returns new text.
    """
    return re.sub('<.[^>]*>', '', re.sub('{{.[^}]*}}', '', text))

@public
def string_slice(text, letters):
    head = text[:letters]
    tail = text[letters:].split()
    tail.append('')
    return head + tail[0]

@public
def get_objects(type=None):
    site = web.ctx.site
    if type:
        return [site.get(key) for key in site.things({"type":type, 'sort': '-created'})]
    return [site.get(key) for key in site.things({})]

@public
def get_categories():
    cats = get_objects('/type/category')
    return [(c.key, c.name) for c in cats]

@public
def get_issues(published=True):
    obj = get_objects('/type/issue')
    if published:
        return [o for o in obj if o.published]
    return [o for o in obj if not o.published]

@public
def get_current_issue():
    import urllib
    path = urllib.unquote(web.ctx.path)
    filter_path = re.match('(/\d{4}/\d{2})', path)
    if filter_path:
        path = filter_path.groups()[0]
    thing = web.ctx.site.get(path)
    if not thing:
        return None
    elif thing.type.key == '/type/issue':
        return thing
    elif thing.type.key == '/type/article':
        return thing.issue
    else:
        return None

@public
def url_to_object(url):
    site = web.ctx.site
    return site.get(url)

@public
def categorize_articles(articles):
    cats = dict((a.category.key, a.category) for a in articles)
    cats = sorted(cats.values(), key=lambda c: c.ordering or 10000)

    res = OrderedDict()
    for c in cats:
        res[c.name] = []
    
    for a in articles:
        res[a.category.name].append(a)

    return res

def month_conversion(string, months=te_months):
    y, m = string.strip('/').split('/')
    return months[str(m)]+" "+str(y)

def make_issue_key(month, year):
    month = ''.join(['0' for i in range(2-len(str(month)))])+str(month)
    return '/'+str(year)+'/'+month
    
@public
def sortComments(seq):
    return sorted(seq, key=lambda x:x['last_modified'])

@public
def date_format(timedate, type="rss"):
    if type == "atom":
        return timedate.strftime("%Y-%m-%dT%H:%M:%SZ")
    return timedate.strftime("%a, %d %b %Y %H:%M:%S GMT")

def get_random_string():
    import string
    import random
    return "".join(random.choice(string.letters + string.digits) for i in range(10))

@public
def next_issue_my(recentIssue):
    """Returns a next issues month and year
    """
    y, m = recentIssue.strip('/').split('/')
    nextIssue = datetime.datetime(int(y), int(m), 1) + datetime.timedelta(days=31)
    return [nextIssue.month, nextIssue.year]

@public
def get_files(path):
    path = os.path.join("static/", path.lstrip('/'))
    try:
        return os.listdir(path)
    except OSError:
        return []

class addComment(delegate.page):
    def POST(self):
        i = web.input(_method='post')
        i['type.key'] = '/type/comment'
        i['_comment'] = ''
        path = '/c/'+ str(get_random_string())
           
        query = {
            'create': 'unless_exists', 
            'key': path,
            'type': {'key': "/type/comment"},
            'article': {"key": i["article.key"]},
            'comment': {'type': '/type/text', 'value': i['comment']},
            'author': i['author'],
            'website': i['website'],
            'email': i['email'],
            'permission':  {'key': '/permission/restricted'} 
        }

        web.ctx.site.write(query, comment='new comment')

        c = web.ctx.site.get(path)
        msg = render.comment_email(c)
        try:
            web.sendmail(config.from_address, config.comment_recipients, web.utf8(msg.subject).strip(), web.utf8(msg))
        except:
            import traceback
            traceback.print_exc()
        web.seeother(i['article.key']+"#comments")

class upload(delegate.page):
    path = "/admin/upload"
    def GET(self):
        return  render.upload()
    def POST(self):
        x = web.input(myfile={}, overwrite=0)
        filename = '_'.join(x['myfile'].filename.lstrip('/').split())#Replace space with underscore
        path = os.path.join('static', x['fileType'].lstrip('/'), x['fileIssue'].lstrip('/'), filename) #Path is a directory where we save particular file. 
        filedata = x['myfile'].value
        
        if not int(x.overwrite) and os.path.isfile(path):
            msg = "File with this name already exists. Check overwrite and try again"
            return render.upload(msg, False)
        else:
            f = open(path, 'w')
            f.write(filedata)
            f.close()
            msg = "File is saved."
            return render.upload(msg, True)

class feed(delegate.page):
    def GET(self):
        type = web.input().get('type', '')
        if type == 'atom':
            print render.atomfeed(web.ctx.home)
        else:
            print render.rssfeed(web.ctx.home)

class search(delegate.page):
    def GET(self):
        print render.site(render.searchResults(web.ctx.home))

class download(delegate.page):
    """Enable download of static files 
    """
    path = "/download/(.*)"

    def GET(self, path):
        path = "/var/www/kottapalli.in/static/" + path
        assert ".." not in path
        web.header("Content-Disposition", 'attachment; filename="%s"' % os.path.basename(path))
        if os.path.exists(path):
            data = open(path).read()
            print data
        else:
            web.notfound()

class test_print(delegate.page):
    path = "(/\d{4}/\d{2})/print"
    def GET(self, path):
        issue = web.ctx.site.get(path)
        print render.issue_print(issue)

class comments(delegate.page):
    path = "(/\d{4}/\d{2})/comments"
    def GET(self, path):
        issue = web.ctx.site.get(path)
        comments = []
        for article in issue.articles:
            comments.extend(article.comments)
        return render.display_comments(issue, comments)

class issues_list(delegate.page):
    path = '/dashboard'
    def GET(self):
        issues = get_objects('/type/issue')
        return render.show_issues(issues)

class articles_list(delegate.page):
    path = '/dashboard(/\d{4}/\d{2})'
    def GET(self, path):
        issue = web.ctx.site.get(path)
        if issue:
            categories = categorize_articles(issue.articles)
            articles = []
            for a in categories.values():
                articles.extend(list(a))
            return render.show_articles(issue, articles)
        else:
            return ""

class images_list(delegate.page):
    path = '/dashboard(/\d{4}/\d{2})/images'
    def GET(self, path):
            issue = web.ctx.site.get(path)
            images = get_files('images'+issue.key)
            return render.show_images(issue, images)
    def POST(self, path):
        issue = web.ctx.site.get(path)
        images = get_files('images'+issue.key)
        x = web.input(image={}, overwrite=0)
        file = '_'.join(x['image'].filename.lstrip('/').split())#Replace space with underscore
        if not file:
            return render.show_images(issue, images, 'Please select a file to upload')
        dir_path = os.path.join('static/images', x['issue.key'].lstrip('/')) #Path is a directory where we save particular file. 
        file_path = os.path.join(dir_path, file.lstrip('/'))
        filedata = x['image'].value
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        if not int(x['overwrite']) and os.path.isfile(file_path):
            msg = "NOTE: File with this name already exists. Check overwrite and try again"
            return render.show_images(issue, images, msg)
        else:
            f = open(file_path, 'w')
            f.write(filedata)
            f.close()
            msg = "File is saved."
            return web.seeother('/dashboard'+path+'/images')

class audio_list(delegate.page):
    path = '/dashboard(/\d{4}/\d{2})/audio'
    def GET(self, path):
            issue = web.ctx.site.get(path)
            audios = get_files('music'+issue.key)
            return render.show_audios(issue, audios)
    def POST(self, path):
        issue = web.ctx.site.get(path)
        audios = get_files('music'+issue.key)
        x = web.input(audio={}, overwrite=0)
        file = '_'.join(x['audio'].filename.lstrip('/').split())#Replace space with underscore
        if not file:
            return render.show_audios(issue, audios, 'Please select a file to upload')
        dir_path = os.path.join('static/music', x['issue.key'].lstrip('/')) #Path is a directory where we save particular file. 
        file_path = os.path.join(dir_path, file.lstrip('/'))
        filedata = x['audio'].value
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        if not int(x['overwrite']) and os.path.isfile(file_path):
            msg = "NOTE: File with this name already exists. Check overwrite and try again"
            return render.show_audios(issue, audios, msg)
        else:
            f = open(file_path, 'w')
            f.write(filedata)
            f.close()
            msg = "File is saved."
            return web.seeother('/dashboard'+path+'/audio')

class publishIssue(delegate.page):
    def POST(self):
        i = web.input(_method='post')
        query = {
            'key': i['issue.key'],
            'published': {
                'connect': 'update',
                'value': True
            }
        }
        web.ctx.site.write(query, comment='issue is published')
        web.seeother('/dashboard')

class addIssue(delegate.page):
    def POST(self):
        i = web.input(_method='post')
        issue_key = make_issue_key(i['month'], i['year'])
        issue_name = month_conversion(issue_key, te_months)
        query={
            'create': 'unless_exists', 
            'key': issue_key,
            'type': {'key': "/type/issue"},
            'name': issue_name,
            'published': False
        }
        web.ctx.site.write(query, comment='New issue is added')
        web.seeother('/dashboard')

class rename(delegate.mode):
    @require_login
    def GET(self, key):
        page = web.ctx.site.get(key)
        return render.rename(page)

    @require_login
    def POST(self, key):
        i = web.input('key', _method='POST')
        page = web.ctx.site.get(key)

        web.transact()
	id = web.query('SELECT id FROM thing WHERE site_id=1 and key=$key', vars=locals())[0].id
        web.query("update thing set key=$i.key where id=$id", vars=locals())
        web.query("update datum set value=$i.key where thing_id=$id and key='key' and datatype=1", vars=locals())
        web.commit()

# disable register
del delegate.pages['/account/register']

