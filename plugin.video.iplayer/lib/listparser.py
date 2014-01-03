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
     def __init__(self, title=None, id=None, updated=None, summary=None, categories=None, series=None, episode=None):
         self.title      = title
         self.id         = id
         self.updated    = updated
         self.summary    = summary
         self.categories = categories
         self.series     = series
         self.episode    = episode

class listentries(object):
     def __init__(self):
         self.entries = []
                  
def parse(xmlSource):  
    try:
        encoding = re.findall( "<\?xml version=\"[^\"]*\" encoding=\"([^\"]*)\"\?>", xmlSource )[ 0 ]
    except: return None
    elist=listentries()
    # gather all list entries 
    entriesSrc = re.findall( "<entry>(.*?)</entry>", xmlSource, re.DOTALL)
    datematch = re.compile(':\s+([0-9]+)/([0-9]+)/([0-9]{4})')
    
    episode_exprs = ["<link rel=\"self\" .*title=\".*pisode *([0-9]+?)", "<link rel=\"self\" .*title=\"([0-9]+?)\."]
    
    # enumerate thru the element list and gather info
    for entrySrc in entriesSrc:
        entry={}
        title   = re.findall( "<title[^>]*>(.*?)</title>", entrySrc, re.DOTALL )[0]
        id      = re.findall( "<id[^>]*>(.*?)</id>", entrySrc, re.DOTALL )[0]
        updated = re.findall( "<updated[^>]*>(.*?)</updated>", entrySrc, re.DOTALL )[0]
        summary = re.findall( "<content[^>]*>(.*?)</content>", entrySrc, re.DOTALL )[0].splitlines()[-3]
        categories = re.findall( "<category[^>]*term=\"(.*?)\"[^>]*>", entrySrc, re.DOTALL )

        series = re.findall( "<link rel=\"related\" href=\".*microsite.*title=\"(.*?)\" />", entrySrc, re.DOTALL )
        if len(series):
            series = series[0]
        else:
            series = title
        
        episode = None
        for ex in episode_exprs:
            e = re.findall( ex, entrySrc, re.DOTALL )
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
        elist.entries.append(listentry(xmlunescape(title), xmlunescape(id), xmlunescape(updated), xmlunescape(summary), e_categories, series, episode))

    return elist   
