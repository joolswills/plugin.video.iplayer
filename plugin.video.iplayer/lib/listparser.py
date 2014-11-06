#
# Provides a simple and very quick way to parse list feeds
#

import re

def xmlunescape(data):
    data = data.replace('&amp;', '&')
    data = data.replace('&gt;', '>')
    data = data.replace('&lt;', '<')
    return data

class listentry(object):
     def __init__(self, title=None, id=None, updated=None, summary=None, categories=None, series=None, episode=None, thumbnail=None):
         self.title      = title
         self.id         = id
         self.updated    = updated
         self.summary    = summary
         self.categories = categories
         self.series     = series
         self.episode    = episode
         self.thumbnail  = thumbnail

class listentries(object):
     def __init__(self):
         self.entries = []

def parse(xmlSource):
    try:
        encoding = re.findall( "<\?xml version=\"[^\"]*\" encoding=\"([^\"]*)\"\?>", xmlSource )[ 0 ]
    except:
        return None

    elist=listentries()
    # gather all list entries
    entriesSrc = re.findall("<episode>(.*?)</episode>", xmlSource, re.DOTALL)
    datematch = re.compile(':\s+([0-9]+)/([0-9]+)/([0-9]{4})')

    re_title = re.compile("<complete_title>(.*?)</complete_title>", re.DOTALL)
    re_id = re.compile("<id>(.*?)</id>", re.DOTALL)
    re_updated = re.compile("<updated>(.*?)</updated>", re.DOTALL)
    re_summary = re.compile("<synopsis>(.*?)</synopsis>", re.DOTALL)
    re_categories = re.compile("<category.*?</short_name><text>(.*?)</text>", re.DOTALL)
    re_thumbnail = re.compile("<my_image_base_url>(.*?)</my_image_base_url>", re.DOTALL)
    re_series = re.compile("<link rel=\"related\" href=\".*microsite.*title=\"(.*?)\" />", re.DOTALL)

    episode_exprs = [ re.compile("<link rel=\"self\" .*title=\".*pisode *([0-9]+)", re.DOTALL),
                      re.compile("<link rel=\"self\" .*title=\"([0-9]+)\.", re.DOTALL) ]

    # enumerate thru the element list and gather info
    for entrySrc in entriesSrc:
        entry={}
        title   = re_title.findall(entrySrc)[0]
        id      = re_id.findall(entrySrc)[-1]
        updated = re_updated.findall(entrySrc)[0]
        summary = re_summary.findall(entrySrc)[0]
        categories = re_categories.findall(entrySrc)
        thumbnail = re_thumbnail.findall(entrySrc)[0]
        thumbnail += id + "_640_360.jpg"



        series = re_series.findall(entrySrc)
        if len(series):
            series = series[0]
        else:
            series = title

        episode = None
        for ex in episode_exprs:
            e = ex.findall(entrySrc)
            if len(e):
                episode = "%s:%02d" % (series, int(e[0]))
                break;
        episode = episode or title

        match = datematch.search(title)
        if match:
            # if the title contains a data at the end use that as the updated date YYYY-MM-DD
            updated = "%s-%s-%s" % ( match.group(3), match.group(2), match.group(1)  )

        e_categories=[]
        for c in categories: e_categories.append(xmlunescape(c))
        elist.entries.append(listentry(xmlunescape(title), xmlunescape(id), xmlunescape(updated), xmlunescape(summary), e_categories, series, episode, xmlunescape(thumbnail)))

    return elist
