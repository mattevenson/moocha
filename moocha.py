from flask import Flask, request, render_template
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import MultiMatch, Match
from urllib.parse import urlencode
import math

app = Flask(__name__)

es = Elasticsearch()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error='404 — Page Not Found'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error='500 — Internal Server Error'), 500

@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    partner = request.args.get('partner', '')
    platform = request.args.get('platform', '')
    page_num = int(request.args.get('page', '1'))

    s = Search(using=es, index='platforms')

    if partner:
        m = Match(partners={"query": partner, 
                            "type": "phrase", 
                            "minimum_should_match": "100%"})
        s = s.query(m)

    if platform:
        m = Match(platform={"query": platform, 
                            "type": "phrase", 
                            "minimum_should_match": "100%"})
        s = s.query(m)

    if query:
        m = MultiMatch(query=query, 
                       fields=['title', 'description', 'tags', 'partners', 'platform'], 
                       type='most_fields', 
                       fuzziness='AUTO',
                       minimum_should_match= "100%")
        s = s.query(m)
    
    _from = 10 * (page_num - 1)
    to = _from + 10

    s = s[_from:to]

    res = s.execute()

    total_hits = res.hits.total
    if total_hits == 0:
        return render_template('error.html', error='No courses')

    pages = paginate(request.args.to_dict(), total_hits, page_num)
    courses = res.hits

    return render_template('courses.html', 
                            courses=courses, 
                            total=total_hits, 
                            pages=pages,
                            query=query)

def which_interval(page_num, page_ct):
    interval_ct = math.ceil(page_ct / 5)
    intervals = [[(i * 5) + 1, (i * 5) + 6] for i in range(interval_ct)]

    for interval in intervals:
        if page_num >= interval[0] and page_num < interval[1]:
            start = interval[0]
            end = interval[1]
            
    if page_ct < end:
        end = page_ct + 1
    
    return start, end

def page_url(params, page):
    params['page'] = page
    return '?' + urlencode(params)

def paginate(params, total_hits, page_num):
    page_ct = math.ceil(total_hits / 10)
    if total_hits > 0:
        start, end = which_interval(page_num, page_ct)
    else: 
        start, end = 1, 2

    pages = []

    if start >= 5:
        prev = {'num': '<',
                'selected': False,
                'url': page_url(params, start - 1)}
        pages.append(prev)

    for i in range(start, end):
        page = {'num': i,
                'selected': True if i == page_num else False,
                'url': page_url(params, i)}
        pages.append(page)

    if end <= page_ct:
        next = {'num': '>',
                'selected': False,
                ''
                'url': page_url(params, end)}
        pages.append(next)
    
    return pages

if __name__ == "__main__":
    app.run(host='0.0.0.0')