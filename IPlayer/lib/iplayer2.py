#!/usr/bin/python

# Python libs
import re, time, os, string, sys
import urllib, urllib2
import logging
import xml.dom.minidom as dom
import md5
import traceback
from pprint import pformat
from socket import timeout as SocketTimeoutError

# XBMC libs
import xbmcgui, xbmcplugin

# external libs
try:
    import httplib2
except:
    pass
import listparser
import stations
try:
    # python >= 2.5
    from xml.etree import ElementTree as ET
except:
    # python 2.4 has to use the plugin's version of elementtree
    from elementtree import ElementTree as ET

IMG_DIR = os.path.join(os.getcwd(), 'resources', 'media')

#print "iplayer2 logging to stdout"
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='iplayer2.py: %(levelname)4s %(message)s',)    
# me want 2.5!!!
def any(iterable):
     for element in iterable:
         if element:
             return True
     return False


# http://colinm.org/blog/on-demand-loading-of-flickr-photo-metadata
# returns immediately for all previously-called functions
def call_once(fn):
    called_by = {}
    def result(self):
        if self in called_by:
            return
        called_by[self] = True
        fn(self)
    return result

# runs loader before decorated function
def loaded_by(loader):
    def decorator(fn):
        def result(self, *args, **kwargs):
            loader(self)
            return fn(self, *args, **kwargs)
        return result
    return decorator

rss_cache = {}

self_closing_tags = ['alternate', 'mediator']

http = None
try:
    http = httplib2.Http()
except:
    logging.error('Failed to initialize httplib2 module')

re_selfclose = re.compile('<([a-zA-Z0-9]+)( ?.*)/>', re.M | re.S)

def fix_selfclosing(xml):
    return re_selfclose.sub('<\\1\\2></\\1>', xml)

def set_http_cache(dir):
    try:
        cache = httplib2.FileCache(HTTP_CACHE_DIR, safe=lambda x: md5.new(x).hexdigest())
        http.cache = cache
    except:
        pass

class NoItemsError(Exception):
    def __init__(self, reason=None):
        self.reason = reason
    
    def __str__(self):
        reason = self.reason or '<no reason given>'
        return "Programme unavailable ('%s')" % (reason)
    

class memoize(object):
    def __init__(self, func):
        self.func = func
        self._cache = {}
    def __call__(self, *args, **kwds):
        key = args
        if kwds:
            items = kwds.items()
            items.sort()
            key = key + tuple(items)
        if key in self._cache:
            return self._cache[key]
        self._cache[key] = result = self.func(*args, **kwds)
        return result

def httpretrieve(url, filename):
    data = httpget(url)    
    f = open(filename, 'wb')
    f.write(data)
    f.close() 

def httpget(url):
    resp = ''
    data = ''
    try:
        start_time = time.clock()
        if http:
            resp, data = http.request(url, 'GET')
        else:
            f = urllib.urlopen(url)
            data = f.read()
            f.close()
        
        sec = time.clock() - start_time
        logging.info('URL Fetch took %2.2f sec for %s', sec, url)            
            
        return data
    except:
        traceback.print_exc(file=sys.stdout)
        try:
            # fallback to urllib to avoid a bug in httplib which often
            # occurs during searches
            f = urllib.urlopen(url)
            data = f.read()
            f.close()
            return data
        except:
            #print "Response for status %s for %s" % (resp.status, data)
            dialog = xbmcgui.Dialog()
            dialog.ok('Network Error', 'Failed to fetch URL', url)
            logging.error( 'Network Error. Failed to fetch URL %s' % url )
            raise
    
    return data

# ElementTree addes {namespace} as a prefix for each element tag
# This function removes these prefixes
def xml_strip_namespace(tree):
    for elem in tree.getiterator():
        elem.tag = elem.tag.split('}')[1]

def parse_entry_id(entry_id):
    # tag:bbc.co.uk,2008:PIPS:b00808sc
    r = re.compile('PIPS:([0-9a-z]{8})')
    matches = r.findall(entry_id)
    if not matches: return None
    return matches[0]


class media(object):
    def __init__(self, item, media_node):
        self.item      = item
        self.href      = None
        self.kind      = None
        self.method    = None
        self.width, self.height = None, None
        self.bitrate   = None
        self.SWFPlayer = None
        self.PlayPath  = None
        #self.tcUrl     = None
        self.PageURL   = None
        self.read_media_node(media_node)

    
    @property
    def url(self):
        if self.connection_method == 'resolve':
            logging.info("Resolving URL %s", self.connection_href)
            page = urllib2.urlopen(self.connection_href)
            page.close()
            url = page.geturl()
            logging.info("URL resolved to %s", url)
            return page.geturl()
        else:
            return self.connection_href


    @property
    def application(self):
        """
        The type of stream represented as a string.
        i.e. 'captions', 'flashhd', 'flashhigh', 'flashmed', 'flashwii', 'mobile', 'mp3', 'real', 'aac'
        """
        tep = {}
        tep['captions', 'application/ttaf+xml', None, 'http', None] = 'captions'
        tep['video', 'video/mp4', 'h264', 'rtmp', 3200]   = 'h264 3200'
        tep['video', 'video/mp4', 'h264', 'rtmp', 1500]   = 'h264 1500'
        tep['video', 'video/mp4', 'h264', 'rtmp', 796]    = 'h264 800'
        tep['video', 'video/mp4', 'h264', 'rtmp', 480]    = 'h264 480'
        tep['video', 'video/x-flv', 'vp6', 'rtmp', 512]   = 'flashmed'
        tep['video', 'video/x-flv', 'spark', 'rtmp', 800] = 'flashwii'
        tep['video', 'video/mpeg', 'h264', 'http', 184]   = 'mobile'
        tep['audio', 'audio/mpeg', 'mp3', 'rtmp', None]   = 'mp3'
        tep['audio', 'audio/real', 'real', 'http', None]  = 'real'
        tep['audio', 'audio/mp4',  'aac', 'rtmp', None]   = 'aac'
        tep['audio', 'audio/wma',  'wma', 'http', None]   = 'wma'
        tep['video', 'video/mp4', 'h264', 'http', 516]    = 'iphonemp3'
        me = (self.kind, self.mimetype, self.encoding, self.connection_protocol, self.bitrate)
        return tep.get(me, None)

    def read_media_node(self, media, resolve=False):
        """
        Reads media info from a media XML node
        media: media node from BeautifulStoneSoup
        """
        self.kind = media.get('kind')
        self.mimetype = media.get('type')
        self.encoding = media.get('encoding')
        self.width, self.height = media.get('width'), media.get('height')
        self.live = media.get('live') == 'true'
        self.service = media.get('service')
        try:
            self.bitrate = int(media.get('bitrate'))
        except:
            if media.get('bitrate') != None:
                logging.info("bitrate = " + '"' + media.get('bitrate') + '"')
            self.bitrate = None

        self.connection_kind = None
        self.connection_live = None
        self.connection_protocol = None
        self.connection_href = None
        self.connection_method = None
        
        # find an akamai stream in preference
        conn = None
        for c in media.findall('connection'):
            if c.get('kind') == 'akamai':
                conn = c
                break     
        if conn == None:
            conn = media.find('connection')
        if conn == None:
            return
            
        self.connection_kind = conn.get('kind')
        self.connection_live = conn.get('live') == 'true'

        if self.mimetype == 'audio/wma':
            self.connection_href = conn.get('href')
            self.connection_protocol = 'http'
            self.kind = 'audio'
            self.bitrate = None
        if self.mimetype == 'audio/real':
            self.connection_href = conn.get('href')
            self.connection_protocol = 'http'
            self.kind = 'audio'
            self.bitrate = None            
        elif self.connection_kind in ['http', 'sis']: # http
            self.connection_href = conn.get('href')
            self.connection_protocol = 'http'
            if self.mimetype == 'video/mp4' and self.encoding == 'h264':
                # iPhone, don't redirect or it goes to license failure page
                self.connection_method = 'iphone'
            elif self.kind == 'captions':
                self.connection_method = None                
            else:
                self.connection_method = 'resolve'
        #elif self.kind == 'video' and self.mimetype == 'video/mp4' and self.encoding == 'h264': #rtmp
        #    
        #    # for h.264 content only level3 connections are supported currently
        #    if self.connection_kind != 'level3':
        #       conn = media.find(name = 'connection', kind="level3")
        #        if not conn:
        #            logging.error("No support for non level3 h264 streams!")  
        #            return
        #        self.connection_kind = conn.get('kind')
        #        self.connection_live = conn.get('live') == 'true'                
        #        
        #    self.connection_protocol = 'rtmp'
        #    hostname = conn.get('server')
        #    application = conn.get('application')
        #    identifier = conn.get('identifier')
        #
        #    if self.connection_live:
        #        logging.error("No support for live streams!")                
        #    else:
        #       auth = conn.get('authstring')
        #       params = dict(ip=hostname, application=application, auth=auth, identifier=identifier)
        #       self.connection_href = "rtmp://%(ip)s:1935/%(application)s?authString=%(auth)s&aifp=v001&slist=%(identifier)s" % params                
        elif self.connection_kind in ['level3', 'akamai', 'limelight']: #rtmp
            self.connection_protocol = 'rtmp'
            server = conn.get('server')
            identifier = conn.get('identifier')
            auth = conn.get('authString')
            application = 'ondemand'
            
            self.SWFPlayer = 'http://www.bbc.co.uk/emp/9player.swf?revision=7276'
            if self.encoding == 'h264':                
                # HD streams drop the leading mp4: in the identifier but not the playpath
                self.PlayPath  = identifier
                p = re.compile('^mp4:')
                identifier = p.sub('', identifier)              
            elif self.connection_kind == 'limelight':
                application    = conn.get('application')
                self.PlayPath  = auth
            elif self.encoding == 'mp3':
                # mp3 streams drop the leading mp3: in the identifier but not the playpath
                self.PlayPath  = identifier
                p = re.compile('^mp3:')
                identifier = p.sub('', identifier)
                self.bitrate = None
            else:
                self.PlayPath  = identifier                

            params = dict(ip=server, server=server, auth=auth, identifier=identifier, application=application)
            
            if self.connection_live:
                logging.error("No support for live streams!")                
            else:
                self.connection_href = "rtmp://%(ip)s:1935/%(application)s?_fcs_vhost=%(server)s&%(auth)s" % params
                #self.tcUrl = "rtmp://%(server)s:1935/%(application)s" % params
        else:
            logging.error("connectionkind %s unknown", self.connection_kind)
        
        if self.connection_protocol and xbmcplugin.getSetting('enhanceddebug') == 'true':
            logging.info("protocol: %s - kind: %s - type: %s - encoding: %s, - bitrate: %s" % 
                         (self.connection_protocol, self.connection_kind, self.mimetype, self.encoding, self.bitrate))
            logging.info("conn href: %s", self.connection_href)

    
    @property 
    def programme(self):
        return self.item.programme

class item(object):
    """
    Represents an iPlayer programme item. Most programmes consist of 2 such items,
    (1) the ident, and (2) the actual programme. The item specifies the properties 
    of the media available, such as whether it's a radio/TV programme, if it's live,
    signed, etc.
    """
    
    def __init__(self, programme, item_node):
        """
        programme: a programme object that represents the 'parent' of this item.
        item_node: an XML &lt;item&gt; node representing this item.
        """
        self.programme = programme
        self.identifier = None
        self.service = None
        self.guidance = None
        self.masterbrand = None
        self.alternate = None
        self.duration = ''
        self.medias = None
        self.read_item_node(item_node)
            
    def read_item_node(self, node):
        """
        Reads the specified XML &lt;item&gt; node and sets this instance's
        properties.
        """
        self.kind = node.get('kind')
        self.identifier = node.get('identifier')
        logging.info('Found item: %s, %s', self.kind, self.identifier)
        if self.kind in ['programme', 'radioProgramme']:
            self.live = node.get('live') == 'true'
            #self.title = node.get('title')
            self.group = node.get('group')
            self.duration = node.get('duration')
            #self.broadcast = node.broadcast
            nf = node.find('service')
            if nf: self.service = nf.text and nf.get('id')
            nf = node.find('masterbrand')
            if nf: self.masterbrand = nf.text and nf.get('id')
            nf = node.find('alternate')
            if nf: self.alternate = nf.text and nf.get('id')
            nf = node.find('guidance')
            if nf: self.guidance = nf.text 
  
        
    @property
    def is_radio(self):
        """ True if this stream is a radio programme. """
        return self.kind == 'radioProgramme'

    @property
    def is_tv(self):
        """ True if this stream is a TV programme. """
        return self.kind == 'programme'

    @property
    def is_ident(self):
        """ True if this stream is an ident. """
        return self.kind == 'ident'

    @property
    def is_programme(self):
        """ True if this stream is a programme (TV or Radio). """
        return self.is_radio or self.is_tv

    @property
    def is_live(self):
        """ True if this stream is being broadcast live. """
        return self.live

    @property
    def is_signed(self):
        """ True if this stream is 'signed' for the hard-of-hearing. """
        return self.alternate == 'signed'
    
    @property
    def mediaselector_url(self):        
        return "http://www.bbc.co.uk/mediaselector/4/mtis/stream/%s" % self.identifier    
        
    @property
    def media(self):
        """
        Returns a list of all the media available for this item.
        """
        if self.medias: return self.medias
        url = self.mediaselector_url
        logging.info("Stream XML URL: %s", url)
        xml = httpget(url)
        tree = ET.XML(xml)
        xml_strip_namespace(tree)
        medias = []
        for m in tree.findall('media'):
            medias.append(media(self, m))
            
        self.medias = medias
        if medias == None or len(medias) == 0:
            d = xbmcgui.Dialog()
            d.ok('Error fetching media info', 'Please check network access to IPlayer by playing iplayer content via a web browser')            
            return
        return medias
    
    def get_media_for(self, application):
        """
        Returns a media object for the given application type.
        """
        medias = [m for m in self.media if m.application == application]
        if not medias:
            return None
        return medias[0]

    def get_medias_for(self, applications):
        """
        Returns a dictionary of media objects for the given application types.
        """
        medias = [m for m in self.media if m.application in applications]
        d = {}.fromkeys(applications)
        for m in medias:
            d[m.application] = m
        return d

class programme(object):
    """
    Represents an individual iPlayer programme, as identified by an 8-letter PID,
    and contains the programme title, subtitle, broadcast time and list of playlist
    items (e.g. ident and then the actual programme.)
    """
    
    def __init__(self, pid):
        self.pid = pid
        self.meta = {}
        self._items = []
        self._related = []

    @call_once
    def read_playlist(self):
        logging.info('Read playlist for %s...', self.pid)
        self.parse_playlist(self.playlist)
    
    def get_playlist_xml(self):
        """ Downloads and returns the XML for a PID from the iPlayer site. """
        try:
            url = self.playlist_url
            xml = httpget(url)
            return xml
        except SocketTimeoutError:
            logging.error("Timed out trying to download programme XML")
            raise

    def parse_playlist(self, xmlstr):
        #logging.info('Parsing playlist XML... %s', xml)
        #xml.replace('<summary/>', '<summary></summary>')
        #xml = fix_selfclosing(xml)
        
        #soup = BeautifulStoneSoup(xml, selfClosingTags=self_closing_tags)
        tree = ET.XML(xmlstr)
        xml_strip_namespace(tree)
        
        self.meta = {}
        self._items = []
        self._related = []

        logging.info('Found programme: %s', tree.find('title').text)
        self.meta['title'] = tree.find('title').text
        self.meta['summary'] = string.lstrip(tree.find('summary').text, ' ')
        self.meta['updated'] = tree.find('updated').text
        
        if tree.find('noitems'):
            logging.info('No playlist items: %s', tree.find('noitems').get('reason'))
            self.meta['reason'] = tree.find('noitems').get('reason')
                        
        self._items = [item(self, i) for i in tree.findall('item')]

        rId = re.compile('concept_pid:([a-z0-9]{8})')
        for link in tree.findall('relatedlink'):
            i = {}
            i['title'] = link.find('title').text
            #i['summary'] = item.summary # FIXME looks like a bug in BSS
            i['pid'] = (rId.findall(link.find('id').text) or [None])[0]
            i['programme'] = programme(i['pid'])
            self._related.append(i)
        
    def get_thumbnail(self, size='large', tvradio='tv'):
        """
        Returns the URL of a thumbnail.
        size: '640x360'/'biggest'/'largest' or '512x288'/'big'/'large' or None
        """
        if size in ['640x360', '640x', 'x360', 'biggest', 'largest']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_640_360.jpg" % (self.pid)
        elif size in ['512x288', '512x', 'x288', 'big', 'large']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_512_288.jpg" % (self.pid)
        elif size in ['178x100', '178x', 'x100', 'small']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_178_100.jpg" % (self.pid)
        elif size in ['150x84', '150x', 'x84', 'smallest']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_150_84.jpg" % (self.pid)
        else:
            return os.path.join(IMG_DIR, '%s.png' % tvradio)
       

    def get_url(self):
        """
        Returns the programmes episode page.
        """
        return "http://www.bbc.co.uk/iplayer/episode/%s" % (self.pid)
    
    @property
    def playlist_url(self):
        return "http://www.bbc.co.uk/iplayer/playlist/%s" % self.pid

    @property
    def playlist(self):
        return self.get_playlist_xml()

    def get_updated(self):
        return self.meta['updated']
    
    @loaded_by(read_playlist)
    def get_title(self):
        return self.meta['title']
    
    @loaded_by(read_playlist)
    def get_summary(self):
        return self.meta['summary']

    @loaded_by(read_playlist)
    def get_related(self):
        return self._related

    @loaded_by(read_playlist)
    def get_items(self):
        if not self._items:
            raise NoItemsError(self.meta['reason'])
        return self._items

    @property
    def programme(self):
        for i in self.items:
            if i.is_programme:
                return i
        return None

    title = property(get_title)
    summary = property(get_summary)
    updated = property(get_updated)
    thumbnail = property(get_thumbnail)    
    related = property(get_related)
    items = property(get_items)

#programme = memoize(programme)


class programme_simple(object):
    """
    Represents an individual iPlayer programme, as identified by an 8-letter PID,
    and contains the programme pid, title, subtitle etc
    """
    
    def __init__(self, pid, entry):
        self.pid = pid
        self.meta = {}
        self.meta['title'] = entry.title
        self.meta['summary'] = string.lstrip(entry.summary, ' ')
        self.meta['updated'] = entry.updated
        self.categories = [] 
        for c in entry.categories:
            #if c != 'TV':
            self.categories.append(c.rstrip())
        self._items = []
        self._related = []

    @call_once
    def read_playlist(self):
        pass
        
    def get_playlist_xml(self):
        pass

    def parse_playlist(self, xml):
        pass
        
    def get_thumbnail(self, size='large', tvradio='tv'):
        """
        Returns the URL of a thumbnail.
        size: '640x360'/'biggest'/'largest' or '512x288'/'big'/'large' or None
        """
        
        if size in ['640x360', '640x', 'x360', 'biggest', 'largest']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_640_360.jpg" % (self.pid)
        elif size in ['512x288', '512x', 'x288', 'big', 'large']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_512_288.jpg" % (self.pid)
        elif size in ['178x100', '178x', 'x100', 'small']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_178_100.jpg" % (self.pid)
        elif size in ['150x84', '150x', 'x84', 'smallest']:
            return "http://www.bbc.co.uk/iplayer/images/episode/%s_150_84.jpg" % (self.pid)
        else:
            return os.path.join(IMG_DIR, '%s.png' % tvradio)


    def get_url(self):
        """
        Returns the programmes episode page.
        """
        return "http://www.bbc.co.uk/iplayer/episode/%s" % (self.pid)
    
    @property
    def playlist_url(self):
        return "http://www.bbc.co.uk/iplayer/playlist/%s" % self.pid

    @property
    def playlist(self):
        return self.get_playlist_xml()

    def get_updated(self):
        return self.meta['updated']
    
    @loaded_by(read_playlist)
    def get_title(self):
        return self.meta['title']
    
    @loaded_by(read_playlist)
    def get_summary(self):
        return self.meta['summary']

    @loaded_by(read_playlist)
    def get_related(self):
        return self._related

    @loaded_by(read_playlist)
    def get_items(self):
        if not self._items:
            raise NoItemsError(self.meta['reason'])
        return self._items

    @property
    def programme(self):
        for i in self.items:
            if i.is_programme:
                return i
        return None

    title = property(get_title)
    summary = property(get_summary)
    updated = property(get_updated)
    thumbnail = property(get_thumbnail)    
    related = property(get_related)
    items = property(get_items)


class feed(object):
    def __init__(self, tvradio=None, channel=None, category=None, searchcategory=None, atoz=None, searchterm=None, radio=None):
        """
        Creates a feed for the specified channel/category/whatever.
        tvradio: type of channel - 'tv' or 'radio'. If a known channel is specified, use 'auto'.
        channel: name of channel, e.g. 'bbc_one'
        category: category name, e.g. 'drama'
        subcategory: subcategory name, e.g. 'period_drama'
        atoz: A-Z listing for the specified letter
        """
        if tvradio == 'auto':
            if not channel and not searchterm:
                raise Exception, "Must specify channel or searchterm when using 'auto'"
            elif channel in stations.channels_tv:
                self.tvradio = 'tv'
            elif channel in stations.channels_radio:
                self.tvradio = 'radio'
            else:
                raise Exception, "TV channel '%s' not recognised." % self.channel
                                
        elif tvradio in ['tv', 'radio']:
            self.tvradio = tvradio
        else:
            self.tvradio = None
        self.channel = channel
        self.category = category            
        self.searchcategory = searchcategory
        self.atoz = atoz
        self.searchterm = searchterm   
        self.radio = radio   
        
    def create_url(self, listing):
        """
        <channel>/['list'|'popular'|'highlights']
        'categories'/<category>(/<subcategory>)(/['tv'/'radio'])/['list'|'popular'|'highlights']
        """
        assert listing in ['list', 'popular', 'highlights'], "Unknown listing type"
        if self.searchcategory:            
            path = ['categories']
            if self.category:
                path += [self.category]
            if self.tvradio:
                path += [self.tvradio]
            path += ['list']
        elif self.category:
            if self.channel:
                path = [self.channel, 'categories', self.category]
            else:
                path = ['categories', self.category, self.tvradio]
            path += ['list']
        elif self.searchterm:
            path = ['search']
            if self.tvradio:
                path += [self.tvradio]
            path += ['?q=%s' % self.searchterm]
        elif self.channel: 
            path = [self.channel]
            if self.atoz:
                path += ['atoz', self.atoz]
            path += [listing]
        elif self.atoz:
            path = ['atoz', self.atoz, listing]
            if self.tvradio:
                path += [self.tvradio]
        else:
            assert listing != 'list', "Can't list at tv/radio level'"
            path = [listing, self.tvradio]
        
        return "http://feeds.bbc.co.uk/iplayer/" + '/'.join(path)

       
    def get_name(self, separator=' '):
        """
        A readable title for this feed, e.g. 'BBC One' or 'TV Drama' or 'BBC One Drama'
        separator: string to separate name parts with, defaults to ' '. Use None to return a list (e.g. ['TV', 'Drama']).
        """
        path = []
        
        # if got a channel, don't need tv/radio distinction
        if self.channel:
            assert self.channel in stations.channels_tv or self.channel in stations.channels_radio, 'Unknown channel'
            #print self.tvradio
            if self.tvradio == 'tv':
                path.append(stations.channels_tv.get(self.channel, '(TV)'))
            else:
                path.append(stations.channels_radio.get(self.channel, '(Radio)'))
        elif self.tvradio: 
            # no channel
            medium = 'TV'
            if self.tvradio == 'radio': medium = 'Radio'
            path.append(medium)
                    
        if self.searchterm:
            path += ['Search results for %s' % self.searchterm]

        if self.searchcategory:
            if self.category:
                path += ['Category %s' % self.category]
            else:                    
                path += ['Categories']
                          
        if self.atoz:
            path.append("beginning with %s" % self.atoz.upper())
        
        if separator != None:
            return separator.join(path)
        else:
            return path
    
    def channels(self):
        """
        Return a list of available channels.
        """
        if self.channel: return None
        if self.tvradio == 'tv': return stations.channels_tv_list
        if self.tvradio == 'radio':
            if radio:
                return channels_radio_type_list[radio]
            else: 
                return stations.channels_radio_list
        return None    
    
    def channels_feed(self):
        """
        Return a list of available channels as a list of feeds.
        """
        if self.channel:
            logging.warning("%s doesn\'t have any channels!", self.channel)
            return None
        if self.tvradio == 'tv': 
            return [feed('tv', channel=ch) for (ch, title) in stations.channels_tv_list]
        if self.tvradio == 'radio':
            if self.radio:
                return [feed('radio', channel=ch) for (ch, title) in stations.channels_radio_type_list[self.radio]]
            else: 
                return [feed('radio', channel=ch) for (ch, title) in stations.channels_radio_list]
        return None

        
    def subcategories(self):
        raise NotImplementedError('Sub-categories not yet supported')
    
    @classmethod
    def is_atoz(self, letter):
        """
        Return False if specified letter is not a valid 'A to Z' directory entry.
        Otherwise returns the directory name.
        
        >>> feed.is_atoz('a'), feed.is_atoz('z')
        ('a', 'z')
        >>> feed.is_atoz('0'), feed.is_atoz('9')
        ('0-9', '0-9')
        >>> feed.is_atoz('123'), feed.is_atoz('abc')
        (False, False)
        >>> feed.is_atoz('big british castle'), feed.is_atoz('')
        (False, False)
        """
        l = letter.lower()
        if len(l) != 1 and l != '0-9': 
            return False
        if l in '0123456789': l = "0-9"
        if l not in 'abcdefghijklmnopqrstuvwxyz0-9':
            return False
        return l
    
    def sub(self, *args, **kwargs):
        """
        Clones this feed, altering the specified parameters.
        
        >>> feed('tv').sub(channel='bbc_one').channel
        'bbc_one'
        >>> feed('tv', channel='bbc_one').sub(channel='bbc_two').channel
        'bbc_two'
        >>> feed('tv', channel='bbc_one').sub(category='drama').category
        'drama'
        >>> feed('tv', channel='bbc_one').sub(channel=None).channel
        >>> 
        """
        d = self.__dict__.copy()
        d.update(kwargs)
        return feed(**d)
    
    def get(self, subfeed):
        """
        Returns a child/subfeed of this feed.
        child: can be channel/cat/subcat/letter, e.g. 'bbc_one'
        """
        if self.channel and subfeed in categories: 
            # no children: channel feeds don't support categories
            return None
        elif self.category:
            # no children: TODO support subcategories
            return None
        elif subfeed in categories:
            return self.sub(category=subfeed)
        elif self.is_atoz(subfeed):
            return self.sub(atoz=self.is_atoz(subfeed))
        else:
            if subfeed in stations.channels_tv: return feed('tv', channel=subfeed)
            if subfeed in stations.channels_radiot: return feed('radio', channel=subfeed)
        # TODO handle properly oh pants
        return None

    @classmethod
    def read_rss(self, url):
        logging.info('Read RSS: %s', url)
        if url not in rss_cache:
            logging.info('Feed URL not in cache, requesting...')
            xml = httpget(url)
            progs = listparser.parse(xml)
            if not progs: return []
            d = []
            for entry in progs.entries: 
                pid = parse_entry_id(entry.id)
                p = programme_simple(pid, entry)
                d.append(p)        
            logging.info('Found %d entries', len(d))
            rss_cache[url] = d
        else:
            logging.info('RSS found in cache')
        return rss_cache[url]
    
    def popular(self):
        return self.read_rss(self.create_url('popular'))

    def highlights(self):
        return self.read_rss(self.create_url('highlights'))
        
    def list(self):
        return self.read_rss(self.create_url('list'))
    
    def categories(self):
        # quick and dirty category extraction and count
        url = self.create_url('list')

        xml = httpget(url)
        categories = []
        doc = dom.parseString(xml)
        root = doc.documentElement
        for entry in root.getElementsByTagName( "entry" ):
            summary = entry.getElementsByTagName( "summary" )[0].firstChild.nodeValue
            title = re.sub('programmes currently available from BBC iPlayer', '', summary, 1)
            url = None
            
            # search for the url for this entry
            for link in entry.getElementsByTagName( "link" ):
                if link.hasAttribute( "rel" ):
                    rel = link.getAttribute( "rel" )
                    if rel == 'self':
                        url = link.getAttribute( "href" )
                        #break
                    
            if url:
                category = re.findall( "iplayer/categories/(.*?)/list", url, re.DOTALL )[0]
                categories.append([title, category])
        
        return categories
        
    @property
    def is_radio(self):
        """ True if this feed is for radio. """
        return self.tvradio == 'radio'

    @property
    def is_tv(self):
        """ True if this feed is for tv. """
        return self.tvradio == 'tv'

    name = property(get_name)


tv = feed('tv')
radio = feed('radio')

def test():
    tv = feed('tv')
    print tv.popular()
    print tv.channels()
    print tv.get('bbc_one')
    print tv.get('bbc_one').list()
    for c in tv.get('bbc_one').categories():
        print c
    #print tv.get('bbc_one').channels()
    #print tv.categories()
    #print tv.get('drama').list()
    #print tv.get('drama').get_subcategory('period').list()

if __name__ == '__main__':
    test()
