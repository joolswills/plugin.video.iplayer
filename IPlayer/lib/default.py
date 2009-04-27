#/bin/python

import sys, os, os.path
import urllib, cgi
from string import ascii_lowercase
from socket import setdefaulttimeout
from time import time
import traceback
import md5
import logging

try:
    import xbmc, xbmcgui, xbmcplugin
except ImportError:
    pass # for PC debugging

sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))

try: 
    import iplayer2 as iplayer
    import httplib2
except ImportError, error:
    print error
    print sys.path
    d = xbmcgui.Dialog()
    d.ok(str(error), 'Please check you installed this plugin correctly.')
    raise

try:
    logging.basicConfig(
        filename='iplayer2.log', 
        filemode='w',
        format='%(asctime)s %(levelname)4s %(message)s',
        level=logging.DEBUG
    )
except IOError:
    print "iplayer2 logging to stdout"
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format='iplayer2.py: %(asctime)s %(levelname)4s %(message)s',
    )
    
HTTP_CACHE_DIR = os.path.join(os.getcwd(), 'iplayer_http_cache')
CACHE_DIR = os.path.join(os.getcwd(), 'iplayer_cache')
THUMB_DIR = os.path.join(os.getcwd(), 'resources', 'media')

for d in [CACHE_DIR, HTTP_CACHE_DIR]:
    if not os.path.isdir(d):
        try:
            print "%s doesn't exist, creating" % d
            os.mkdir(d)
        except IOError, e:
            print "Couldn't create %s, %s" % (d, str(e))
            raise


def get_thumbnail_filename(programme):
    thumbfn = "%s.jpg" % (programme.pid)
    fn = os.path.join(CACHE_DIR, thumbfn)
    return str(fn)

def download_thumbnail(programme):
    fn = get_thumbnail_filename(programme)
    if not os.path.exists(fn):
        #url = programme.get_thumbnail()
        #urllib.urlretrieve(url, fn)
        programme.retrieve_thumbnail(fn)
    return os.path.exists(fn)

def clear_thumbnail_cache(max_age_days=7):
    thumbs = [t for t in os.listdir(CACHE_DIR) if t.endswith('.jpg')]
    max_age_time = max_age_days * 60 * 60 * 24
    delete = []
    for t in thumbs:
        filename = os.path.join(CACHE_DIR, t)
        statinfo = os.stat(filename)
        mtime = statinfo.st_mtime
        age = time() - mtime
        if age > max_age_time:
            delete += [filename]
    for d in delete:
        os.remove(d)
    return len(delete)
    
def get_feed_thumbnail(feed):
    thumbfn = ''
    if feed.tvradio == 'radio':
        url = "http://www.bbc.co.uk/iplayer/img/radio/%s.gif" % feed.channel
        thumbfn = os.path.join(CACHE_DIR, feed.channel + '.gif')
    else:
        url = "http://www.bbc.co.uk/iplayer/img/tv/%s.jpg" % feed.channel
        thumbfn = os.path.join(CACHE_DIR, feed.channel + '.jpg')
    print url

    if not os.path.exists(thumbfn):
        urllib.urlretrieve(url, thumbfn)
    
    return thumbfn
    
def make_url(feed=None, listing=None, pid=None, tvradio=None, category=None):
    base = sys.argv[0]
    d = {}
    if feed:
        if feed.channel: 
            d['feed_channel'] = feed.channel
        if feed.atoz: 
            d['feed_atoz'] = feed.atoz
    if category: d['category'] = category
    if listing: d['listing'] = listing
    if pid: d['pid'] = pid
    if tvradio: d['tvradio'] = tvradio
    params = urllib.urlencode(d, True)
    return base + '?' + params

def read_url():
    args = cgi.parse_qs(sys.argv[2][1:])
    feed_channel = args.get('feed_channel', [None])[0]
    feed_atoz = args.get('feed_atoz', [None])[0]
    listing = args.get('listing', [None])[0]
    pid = args.get('pid', [None])[0]
    tvradio = args.get('tvradio', [None])[0]
    
    feed = None
    if feed_channel:
        feed = iplayer.feed('auto', channel=feed_channel, atoz=feed_atoz)
    elif feed_atoz:
        feed = iplayer.feed(tvradio or 'auto', atoz=feed_atoz)
    return (feed, listing, pid, tvradio)

def list_atoz(feed=None):
    handle = int(sys.argv[1])
    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED)
    
    letters = list(ascii_lowercase) + ['0']
        
    feed = feed or iplayer.tv
    feeds = [feed.get(l) for l in letters]
    for f in feeds:
        listitem = xbmcgui.ListItem(label=f.name)
        listitem.setThumbnailImage(get_feed_thumbnail(f))
        url = make_url(feed=f, listing='list')
        ok = xbmcplugin.addDirectoryItem(
            handle=handle,
            url=url,
            listitem=listitem,
            isFolder=True,
        )

    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)
    
def list_feeds(feeds):
    handle = int(sys.argv[1])
    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_TRACKNUM)

    folders = []
    folders.append(('A to Z', 'popular.png', make_url(listing='atoz')))
    folders.append(('Highlights', 'highlights.png', make_url(listing='highlights')))
    folders.append(('Popular', 'popular.png', make_url(listing='popular')))
    folders.append(('Search', '', make_url(listing='search')))
    folders.append(('Categories', '', make_url(listing='categories')))

    i = 0        
    for j, (label, tn, url) in enumerate(folders):
        listitem = xbmcgui.ListItem(label=label)
        listitem.setIconImage('defaultFolder.png')
        listitem.setThumbnailImage(os.path.join(THUMB_DIR, tn))
        listitem.setProperty('tracknumber', str(i + j))
        ok = xbmcplugin.addDirectoryItem(
            handle=handle, 
            url=url,
            listitem=listitem,
            isFolder=True,
        )

    i = len(folders)
    for j, f in enumerate(feeds):
        listitem = xbmcgui.ListItem(label=f.name)
        listitem.setIconImage('defaultFolder.png')
        listitem.setThumbnailImage(get_feed_thumbnail(f))
        listitem.setProperty('tracknumber', str(i + j))
        url = make_url(feed=f)
        ok = xbmcplugin.addDirectoryItem(
            handle=handle,
            url=url,
            listitem=listitem,
            isFolder=True,
        )
    """
    listitem = xbmcgui.ListItem(label='BBC Three Live (test)')
    url = iplayer.programme('bbc_three').items[0].get_media_for('flashmed').url
    ok = xbmcplugin.addDirectoryItem(
        handle=handle,
        url=url,
        listitem=listitem
    )
    """
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)


def list_tvradio():
    """
    Lists five folders - one for TV and one for Radio, plus A-Z, highlights and popular
    """
    handle = int(sys.argv[1])
    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_TRACKNUM)
        
    folders = []
    folders.append(('TV', 'defaultVideo.png', make_url(tvradio='tv')))
    folders.append(('Radio', 'defaultAudio.png', make_url(tvradio='radio')))
    #folders.append(('Popular', 'popular.png', make_url(listing='popular'))
    #folders.append(('Highlights', 'highlights.png', make_url(listing='highlights'))
    #folders.append(('A to Z', 'atoz.png', make_url(listing='atoz'))
        
    for i, (label, tn, url) in enumerate(folders):
        listitem = xbmcgui.ListItem(label=label)
        listitem.setIconImage(tn) #os.path.join(THUMB_DIR, tn)
        ok = xbmcplugin.addDirectoryItem(
            handle=handle, 
            url=url,
            listitem=listitem,
            isFolder=True,
        )
    
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

def get_setting_videostream(default='flashmed'):
    videostream = xbmcplugin.getSetting('video_stream')
    d = {
        'Auto': default,
        'Flash VP6': 'flashmed', 
        'Flash Wii': 'flashwii',
        0: default,
        1: 'flashmed', 
        2: 'flashwii'
    }
    pref = d.get(videostream, default)
    return pref

def add_programme(programme, totalItems=None):
    handle = int(sys.argv[1])

    title = programme.title
        
    print handle
    print title

    title = programme.title
    listitem = xbmcgui.ListItem(label=title, label2=programme.summary)
    datestr = programme.updated[:10]
    date=datestr[8:10] + '/' + datestr[5:7] + '/' +datestr[:4]#date ==dd/mm/yyyy
    
    listitem.setInfo('video', {
        'Title': programme.title,
        'Plot': programme.summary,
        "Date": date,
    })
    listitem.setProperty('Title', str(title))
        
    if xbmcplugin.getSetting('thumbnails') == 'true':
        print "Getting thumbnail for %s ..." % (programme.title)
        thumb = get_thumbnail_filename(programme)
        try:
            if download_thumbnail(programme):
                listitem.setThumbnailImage(thumb)
                listitem.setIconImage('defaultVideo.png')
        except:
            #TODO handle this properly!
            print "Couldn't save %s to %s" % (programme.get_thumbnail(), thumb)
            raise
    
    print "Getting URL for %s ..." % (programme.title)

    url=make_url(pid=programme.pid)
    xbmcplugin.addDirectoryItem(
        handle=handle, 
        url=url,
        listitem=listitem,
        totalItems=totalItems
    )

    return True


def list_feed(feed):
    handle = int(sys.argv[1])
    c = 0

    name = feed.name
    sub = {}
    sub[name + ' - A-Z'] = make_url(feed=feed, listing='atoz')
    sub[name + ' - All'] = make_url(feed=feed, listing='list')
    sub[name + ' - Popular'] = make_url(feed=feed, listing='popular')
    sub[name + ' - Highlights'] = make_url(feed=feed, listing='highlights')
    
    for (title, url) in sub.items():
        listitem = xbmcgui.ListItem(label=title)
        listitem.setThumbnailImage(get_feed_thumbnail(feed))
        ok = xbmcplugin.addDirectoryItem(
            handle=handle, 
            url=url,
            listitem=listitem,
            isFolder=True,
        )
        c += 1

    for category in feed.categories():
        url = make_url(feed=feed, category=category)
        listitem = xbmcgui.ListItem(label=name + ' - ' + category)
        ok = xbmcplugin.addDirectoryItem(            
            handle=handle, 
            url=url,
            listitem=listitem,
            isFolder=True,
        )
        c += 1        
        
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)
    
    
def search():
    handle = int(sys.argv[1])
    
    kb = xbmc.Keyboard('', 'Search for')
    kb.doModal()
    if not kb.isConfirmed():
        xbmcplugin.endOfDirectory(handle=handle, succeeded=False)

    searchterm = kb.getText()
    
    feed = iplayer.feed(searchterm=searchterm)
    list_feed_listings(feed, 'list')
    
        
def list_feed_listings(feed, listing):
    handle = int(sys.argv[1])
    
    d = {}
    d['list'] = feed.list
    d['popular'] = feed.popular
    d['highlights'] = feed.highlights
    programmes = d[listing]()
    
    total = len(programmes)
    for p in programmes:
        try:
            if not add_programme(p, total):
                total = total - 1
        except:
            traceback.print_exc()
            total = total - 1
    if not programmes:
        listitem = xbmcgui.ListItem(label="(no programmes found)")
        ok = xbmcplugin.addDirectoryItem(
            url="",
            handle=handle, 
            listitem=listitem
        )

    if feed.is_tv:
        xbmcplugin.setContent(handle=handle, content='episodes')
    elif feed.is_radio:
        xbmcplugin.setContent(handle=handle, content='songs')
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)


def get_item(pid): 
    print "Getting %s" % (pid)
    p = iplayer.programme(pid)
    print "%s is %s" % (pid, p.title)
      
    #for i in p.items:
    #    if i.kind in ['programme', 'radioProgrammme']:
    #        return i
    return p.programme


def watch(pid):
  
    item = get_item(pid)
    logging.info('watching pid=%s' % pid)

    listitem = xbmcgui.ListItem(label=item.programme.title, label2=item.programme.summary)
    
    if item.is_tv:
        
        pref = get_setting_videostream()
        media = item.get_media_for(pref)
        url = media.url
        logging.info('watching url=%s' % url)

        play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        
    else:

        media = item.get_media_for('real')
        if not media:
            return false
        try:
            url = iplayer.httpget(media.url)
        except:
            print "Couldn't get realplayer stream for %s" % pid
            raise

        play=xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

    play.clear()
    play.add(url,item.programme.title)
    xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(play)

    
if __name__ == "__main__":
    print sys.argv
    
    print "Settings:"
    for s in ['video_stream', 'thumbnails', 'thumbnail_life', 'socket_timeout']:
        print "    %s: %s" % (s, xbmcplugin.getSetting(s))
    
    cache = httplib2.FileCache(HTTP_CACHE_DIR, safe=lambda x: md5.new(x).hexdigest())
    iplayer.set_http_cache(cache)

    thumbnail_life = int(xbmcplugin.getSetting('thumbnail_life'))    
    if thumbnail_life > 0:
        print "Deleting old thumbnails (max: %d days)" % (thumbnail_life)
        try:
            deleted = clear_thumbnail_cache(thumbnail_life)
            print "Deleted %d thumbnails" % (deleted)
        except e:
            print "Could not delete thumbnails: " + e
    else:
        print "Not deleting old thumbnails"

    environment = os.environ.get( "OS", "xbox" )
    try:
        timeout = int(xbmcplugin.getSetting('socket_timeout'))
    except:
        timeout = 5
    if environment in ['Linux', 'xbox'] and timeout > 0:
        setdefaulttimeout(timeout)
    
    (feed, listing, pid, tvradio) = read_url()
    print (feed, listing, pid, tvradio)
    if feed:
        print feed.name
    else:
        print "no feed"

    if pid:
        watch(pid)
    elif not (feed or listing):
        if not tvradio:
            list_tvradio()
        elif tvradio:
            #feeds = iplayer.tv.channels_feed()
            #feeds += iplayer.radio.channels_feed()
            feed = iplayer.feed(tvradio).channels_feed()
            list_feeds(feed)
    elif feed and not listing:
        list_feed(feed)
    elif listing == 'search':
        search()
    elif listing == 'atoz':
        list_atoz(feed)
    elif listing == 'categories':
        list_categories(feed)
    elif listing:
        feed = feed or iplayer.feed(tvradio or 'tv')
        list_feed_listings(feed, listing)
    

