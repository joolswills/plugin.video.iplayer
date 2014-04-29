#!/usr/bin/python

# Python libs
import re, time, os, string, sys
import urllib, urllib2
import xml.dom.minidom as dom
import md5
import traceback
from socket import timeout as SocketTimeoutError

# XBMC libs
import xbmcgui

# external libs
import listparser
import stations

try:
    # python >= 2.5
    from xml.etree import ElementTree as ET
except:
    # python 2.4 has to use the plugin's version of elementtree
    from elementtree import ElementTree as ET
import httplib2

import utils
__addoninfo__ = utils.get_addoninfo()
__addon__ = __addoninfo__["addon"]

sys.path.append(os.path.join(__addoninfo__["path"], 'lib', 'httplib2'))
import socks

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

re_selfclose = re.compile('<([a-zA-Z0-9]+)( ?.*)/>', re.M | re.S)
re_pips = re.compile('PIPS:([0-9a-z]{8})')
re_concept_id = re.compile('concept_pid:([a-z0-9]{8})')

def get_proxy():
    proxy_server = None
    proxy_type_id = 0
    proxy_port = 8080
    proxy_user = None
    proxy_pass = None
    try:
        proxy_server = __addon__.getSetting('proxy_server')
        proxy_type_id = __addon__.getSetting('proxy_type')
        proxy_port = int(__addon__.getSetting('proxy_port'))
        proxy_user = __addon__.getSetting('proxy_user')
        proxy_pass = __addon__.getSetting('proxy_pass')
    except:
        pass

    if   proxy_type_id == '0': proxy_type = socks.PROXY_TYPE_HTTP_NO_TUNNEL
    elif proxy_type_id == '1': proxy_type = socks.PROXY_TYPE_HTTP
    elif proxy_type_id == '2': proxy_type = socks.PROXY_TYPE_SOCKS4
    elif proxy_type_id == '3': proxy_type = socks.PROXY_TYPE_SOCKS5

    proxy_dns = True

    return (proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)

def get_httplib():
    http = None
    try:
        if __addon__.getSetting('proxy_use') == 'true':
            (proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass) = get_proxy()
            utils.log("Using proxy: type %i rdns: %i server: %s port: %s user: %s pass: %s" % (proxy_type, proxy_dns, proxy_server, proxy_port, "***", "***"),xbmc.LOGINFO)
            http = httplib2.Http(proxy_info = httplib2.ProxyInfo(proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass))
        else:
          http = httplib2.Http()
    except:
        raise
        utils.log('Failed to initialize httplib2 module',xbmc.LOGFATAL)

    return http

http = get_httplib()

def fix_selfclosing(xml):
    return re_selfclose.sub('<\\1\\2></\\1>', xml)

def set_http_cache(dir):
    try:
        cache = httplib2.FileCache(dir, safe=lambda x: md5.new(x).hexdigest())
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
            raise

        sec = time.clock() - start_time
        utils.log('URL Fetch took %2.2f sec for %s' % (sec, url),xbmc.LOGINFO)

        return data
    except:
        traceback.print_exc(file=sys.stdout)
        dialog = xbmcgui.Dialog()
        dialog.ok('Network Error', 'Failed to fetch URL', url)
        utils.log('Network Error. Failed to fetch URL %s' % url,xbmc.LOGINFO)

    return data

# ElementTree addes {namespace} as a prefix for each element tag
# This function removes these prefixes
def xml_strip_namespace(tree):
    for elem in tree.getiterator():
        elem.tag = elem.tag.split('}')[1]

def parse_entry_id(entry_id):
    # tag:bbc.co.uk,2008:PIPS:b00808sc
    matches = re_pips.findall(entry_id)
    if not matches: return None
    return matches[0]

def get_provider():
    provider = None
    try:
        provider_id = __addon__.getSetting('provider')
    except:
        pass

    if   provider_id == '1': provider = 'akamai'
    elif provider_id == '2': provider = 'limelight'
    elif provider_id == '3': provider = 'level3'

    return provider

def get_protocol():
    protocol = "rtmp"
    try:
        protocol_id = __addon__.getSetting('protocol')
    except:
        pass

    if protocol_id == '1': protocol = 'rtmpt'

    return protocol

def get_port():
    port = 1935
    protocol = get_protocol()
    if protocol == 'rtmpt': port = 80
    return port

def get_thumb_dir():
    thumb_dir = os.path.join(__addoninfo__['path'], 'resources', 'media')
    if utils.get_os() == "xbox":
        thumb_dir = os.path.join(thumb_dir, 'xbox')
    return thumb_dir

def get_setting_videostream():

    stream = 'h264 1520'

    stream_prefs = '0'
    try:
        stream_prefs = __addon__.getSetting('video_stream')
    except:
        pass

    # Auto|H.264 (480kb)|H.264 (800kb)|H.264 (1500kb)|H.264 (2800kb)
    if stream_prefs == '0':
        environment = os.environ.get( "OS" )
        # check for xbox as we set a lower default for xbox (although it can do 1500kbit streams)
        if environment == 'xbox':
            stream = 'h264 820'
        else:
            # play full HD if the screen is large enough (not all programmes have this resolution)
            Y = int(xbmc.getInfoLabel('System.ScreenHeight'))
            X = int(xbmc.getInfoLabel('System.ScreenWidth'))
            # if the screen is large enough for HD
            if Y > 832 and X > 468:
                stream = 'h264 2800'
    elif stream_prefs == '1':
        stream = 'h264 480'
    elif stream_prefs == '2':
        stream = 'h264 820'
    elif stream_prefs == '3':
        stream = 'h264 1520'
    elif stream_prefs == '4':
        stream = 'h264 2800'

    utils.log("Video stream prefs %s - %s" % (stream_prefs, stream),xbmc.LOGINFO)
    return stream

def get_setting_audiostream():
    stream = 'Auto'

    stream_prefs = '0'
    try:
        stream_prefs = __addon__.getSetting('audio_stream')
    except:
        pass

    # Auto|AAC (320Kb)|AAC (128Kb)|WMA (128Kb)|AAC (48Kb or 32Kb)
    if stream_prefs == '0':
        # Auto - default to highest bitrate AAC
        stream = 'aac320'
    elif stream_prefs == '1':
        stream = 'aac320'
    elif stream_prefs == '2':
        stream = 'aac128'
    elif stream_prefs == '3':
        # Live feeds have a wma+asx application type
        # In this case the wma9 type is not available, and the plugin should default over to wma+asx
        stream = 'wma9'
    elif stream_prefs == '4':
        # As above, live feeds only have a 32Kb AAC stream, which should be defaulted to after trying 48 bit
        stream = 'aac48'

    utils.log("Audio stream prefs %s - %s" % (stream_prefs, stream),xbmc.LOGINFO)
    return stream

class media(object):
    tep = {
        ('captions', 'application/ttaf+xml', None, 'http', None) : 'captions',
        ('video', 'video/mp4', 'h264', 'rtmp', 2800)   : 'h264 2800',
        ('video', 'video/mp4', 'h264', 'rtmp', 1520)   : 'h264 1520',
        ('video', 'video/mp4', 'h264', 'rtmp', 1500)   : 'h264 1500',
        ('video', 'video/mp4', 'h264', 'rtmp', 816)    : 'h264 820',
        ('video', 'video/mp4', 'h264', 'rtmp', 796)    : 'h264 800',
        ('video', 'video/mp4', 'h264', 'rtmp', 480)    : 'h264 480',
        ('video', 'video/mp4', 'h264', 'rtmp', 396)    : 'h264 400',
        ('video', 'video/x-flv', 'vp6', 'rtmp', 512)   : 'flashmed',
        ('video', 'video/x-flv', 'spark', 'rtmp', 800) : 'flashwii',
        ('video', 'video/mpeg', 'h264', 'http', 184)   : 'mobile',
        ('audio', 'audio/mpeg', 'mp3', 'rtmp', None)   : 'mp3',
        ('audio', 'audio/mp4',  'aac', 'rtmp', None)   : 'aac',
        ('audio', 'audio/wma',  'wma', 'http', None)   : 'wma',
        ('audio', 'audio/mp4', 'aac', 'rtmp', 320)     : 'aac320',
        ('audio', 'audio/mp4', 'aac', 'rtmp', 128)     : 'aac128',
        ('audio', 'audio/wma', 'wma9', 'http', 128)    : 'wma9',
        ('audio', 'audio/x-ms-asf', 'wma', 'http', 128) : 'wma+asx',
        ('audio', 'audio/mp4', 'aac', 'rtmp', 48)      : 'aac48',
        ('audio', 'audio/mp4', 'aac', 'rtmp', 32)      : 'aac32',
        ('video', 'video/mp4', 'h264', 'http', 516)    : 'iphonemp3'}

    def __init__(self, item, media_node, connection):
        self.item      = item
        self.href      = None
        self.kind      = None
        self.method    = None
        self.width, self.height = None, None
        self.bitrate   = None
        self.read_media_node(media_node, connection)

    @staticmethod
    def create_from_media_xml(item, xml):
        result = []
        for c in xml.findall('connection'):
            result.append(media(item, xml, c))
        
        return result
    
    @property
    def url(self):
        # no longer used. will remove later
        if self.connection_method == 'resolve':
            utils.log("Resolving URL %s" % self.connection_href,xbmc.LOGINFO)
            page = urllib2.urlopen(self.connection_href)
            page.close()
            url = page.geturl()
            utils.log("URL resolved to %s" % url,xbmc.LOGINFO)
            return page.geturl()
        else:
            return self.connection_href

    @property
    def application(self):
        """
        The type of stream represented as a string.
        i.e. 'captions', 'flashhd', 'flashhigh', 'flashmed', 'flashwii', 'mobile', 'mp3', 'real', 'aac'
        """
        me = (self.kind, self.mimetype, self.encoding, self.connection_protocol, self.bitrate)
        return self.__class__.tep.get(me, None)

    def read_media_node(self, media, conn):
        """
        Reads media info from a media XML node
        media: media node from BeautifulStoneSoup
        """
        self.kind = media.get('kind')
        self.mimetype = media.get('type')
        self.encoding = media.get('encoding')
        self.width, self.height = media.get('width'), media.get('height')
        self.live = ( media.get('live') == 'true' or self.item.live == True )
        self.service = media.get('service')
        try:
            self.bitrate = int(media.get('bitrate'))
        except:
            if media.get('bitrate') != None:
                utils.log('bitrate = "%s"' % media.get('bitrate'),xbmc.LOGINFO)
            self.bitrate = None

        self.connection_kind = None
        self.connection_live = None
        self.connection_protocol = None
        self.connection_href = None
        self.connection_method = None

        self.connection_kind = conn.get('kind')
        self.connection_protocol = conn.get('protocol')

        # some akamai rtmp streams (radio) don't specify rtmp protocol
        if self.connection_protocol == None and self.connection_kind == 'akamai':
            self.connection_protocol = 'rtmp'

        if self.connection_kind in ['http', 'sis', 'asx']:
            self.connection_href = conn.get('href')
            self.connection_protocol = 'http'
            if self.kind == 'captions':
                self.connection_method = None

        elif self.connection_protocol == 'rtmp':
            server = conn.get('server')
            identifier = conn.get('identifier')
            auth = conn.get('authString')
            application = conn.get('application')
            # sometimes we don't get a rtmp application for akamai
            if application == None and self.connection_kind == 'akamai':
                application = "ondemand"

            timeout = __addon__.getSetting('stream_timeout')
            swfplayer = 'http://www.bbc.co.uk/emp/releases/iplayer/revisions/617463_618125_4/617463_618125_4_emp.swf'
            params = dict(protocol = get_protocol(), port = get_port(), server = server, auth = auth, ident = identifier, app = application)

            if self.connection_kind == 'limelight':
                # note that librtmp has a small issue with constructing the tcurl here. we construct it ourselves for now (fixed in later librtmp)
                self.connection_href = "%(protocol)s://%(server)s:%(port)s/ app=%(app)s?%(auth)s tcurl=%(protocol)s://%(server)s:%(port)s/%(app)s?%(auth)s playpath=%(ident)s" % params
            else:
                # akamai needs the auth string included in the playpath
                self.connection_href = "%(protocol)s://%(server)s:%(port)s/%(app)s?%(auth)s playpath=%(ident)s?%(auth)s" % params

            # swf authention only needed for the ondemand streams
            if self.live:
                self.connection_href += " live=1"
            elif self.kind == 'video':
                self.connection_href += " swfurl=%s swfvfy=1" % swfplayer

            self.connection_href += " timeout=%s" % timeout

        else:
            utils.log("connectionkind %s unknown" % self.connection_kind,xbmc.LOGERROR)

        if self.connection_protocol and __addon__.getSetting('enhanceddebug') == 'true':
            utils.log("protocol: %s - kind: %s - type: %s - encoding: %s, - bitrate: %s" %
                         (self.connection_protocol, self.connection_kind, self.mimetype, self.encoding, self.bitrate),xbmc.LOGINFO)
            utils.log("conn href: %s" % self.connection_href,xbmc.LOGINFO)

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
        utils.log('Found item: %s, %s' % (self.kind, self.identifier),xbmc.LOGINFO)
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

    def get_available_streams(self):
        """ 
        Returns a list of available streams in order of desirability,
        according to provider and bitrate preferences
        """
        if self.is_tv:
            streams = ['h264 2800', 'h264 1520', 'h264 1500', 'h264 820', 'h264 800', 'h264 480', 'h264 400']
            rate = get_setting_videostream()
        else:
            streams = ['aac320', 'aac128', 'wma9', 'wma+asx', 'aac48', 'aac32']
            rate = get_setting_audiostream()
        
        provider = get_provider()

        # Build a list of streams of lower or equal bitrate to the config setting
        if rate not in streams:
            return ([], false)
            
        media = []
        above_limit = False
        for strm in streams[streams.index(rate):]:
            media.extend(self.get_media_list_for(strm, provider))
            
        # If nothing found, get next highest bitrate
        if len(media) == 0:
            above_limit = true
            i = streams.index(rate)
            while len(media) == 0 and i > 0:
                i -= 1
                media = self.get_media_list_for(streams[i], provider)
        
        utils.log("Available streams by preference: %s" % (["%s %s" % (m.connection_kind, m.application) for m in media]),xbmc.LOGINFO)
        
        return (media, above_limit)
    
    def mediaselector_url(self, suffix):
        if suffix == None:
            return "http://open.live.bbc.co.uk/mediaselector/4/mtis/stream/%s" % self.identifier
        return "http://open.live.bbc.co.uk/mediaselector/4/mtis/stream/%s/%s" % (self.identifier, suffix)

    def get_media_list_for(self, stream, provider_pref):
        """
        Returns a list of media objects for the given rate, putting the
        preferred provider first if it exists
        """
        if not self.medias:
            url = self.mediaselector_url(None)
            utils.log("Stream XML URL: %s" % url,xbmc.LOGINFO)
            xml = httpget(url)
            tree = ET.XML(xml)
            xml_strip_namespace(tree)
            self.medias = []
            for m in tree.findall('media'):
                self.medias.extend(media.create_from_media_xml(self, m))

        result = []
        for m in self.medias:
            if m.application == stream:
                if m.connection_kind == provider_pref:
                    result.insert(0, m)
                else:
                    result.append(m)
                    
        return result
        
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
        utils.log('Read playlist for %s...' % self.pid,xbmc.LOGINFO)
        self.parse_playlist(self.playlist)

    def get_playlist_xml(self):
        """ Downloads and returns the XML for a PID from the iPlayer site. """
        try:
            url = self.playlist_url
            xml = httpget(url)
            return xml
        except SocketTimeoutError:
            utils.log("Timed out trying to download programme XML",xbmc.LOGERROR)
            raise

    def parse_playlist(self, xmlstr):
        #utils.log('Parsing playlist XML... %s' % xml,xbmc.LOGINFO)
        #xml.replace('<summary/>', '<summary></summary>')
        #xml = fix_selfclosing(xml)

        #soup = BeautifulStoneSoup(xml, selfClosingTags=self_closing_tags)
        tree = ET.XML(xmlstr)
        xml_strip_namespace(tree)

        self.meta = {}
        self._items = []
        self._related = []

        utils.log('Found programme: %s' % tree.find('title').text,xbmc.LOGINFO)
        self.meta['title'] = tree.find('title').text
        self.meta['summary'] = tree.find('summary').text
        self.meta['thumbnail'] = tree.find("link[@rel='holding']").attrib['href']
        # Live radio feeds have no text node in the summary node
        if self.meta['summary']:
            self.meta['summary'] = string.lstrip(self.meta['summary'], ' ')
        self.meta['updated'] = tree.find('updated').text

        if tree.find('noitems'):
            utils.log('No playlist items: %s' % tree.find('noitems').get('reason'),xbmc.LOGINFO)
            self.meta['reason'] = tree.find('noitems').get('reason')

        self._items = [item(self, i) for i in tree.findall('item')]

        for link in tree.findall('relatedlink'):
            i = {}
            i['title'] = link.find('title').text
            #i['summary'] = item.summary # FIXME looks like a bug in BSS
            i['pid'] = (re_concept_id.findall(link.find('id').text) or [None])[0]
            i['programme'] = programme(i['pid'])
            self._related.append(i)

    def get_thumbnail(self, size='large', tvradio='tv'):
        """
        Returns the URL of a thumbnail.
        size: '640x360'/'biggest'/'largest' or '512x288'/'big'/'large' or None
        """
        newbaseurl = re.findall("^(.*?)_.*?_.*?.jpg", self.meta['thumbnail'], re.DOTALL)[0]
        if size in ['640x360', '640x', 'x360', 'biggest', 'largest']:
            return "%s_640_360.jpg" % newbaseurl
        elif size in ['512x288', '512x', 'x288', 'big', 'large']:
            return "%s_512_288.jpg" % newbaseurl
        elif size in ['178x100', '178x', 'x100', 'small']:
            return "%s_178_100.jpg" % newbaseurl
        elif size in ['150x84', '150x', 'x84', 'smallest']:
            return "%s_150_84.jpg" % newbaseurl
        else:
            return os.path.join(get_thumb_dir(), '%s.png' % tvradio)


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
        self.meta['thumbnail'] = entry.thumbnail
        self.categories = []
        for c in entry.categories:
            #if c != 'TV':
            self.categories.append(c.rstrip())
        self._items = []
        self._related = []
        self.series = entry.series
        self.episode = entry.episode

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
        newbaseurl = re.findall("^(.*?)_.*?_.*?.jpg", self.meta['thumbnail'], re.DOTALL)[0]
        if size in ['640x360', '640x', 'x360', 'biggest', 'largest']:
            return "%s_640_360.jpg" % newbaseurl
        elif size in ['512x288', '512x', 'x288', 'big', 'large']:
            return "%s_512_288.jpg" % newbaseurl
        elif size in ['178x100', '178x', 'x100', 'small']:
            return "%s_178_100.jpg" % newbaseurl
        elif size in ['150x84', '150x', 'x84', 'smallest']:
            return "%s_150_84.jpg" % newbaseurl

        else:
            return os.path.join(get_thumb_dir(), '%s.png' % tvradio)


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
            path += ['?q=%s' % urllib.quote_plus(self.searchterm)]
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
            utils.log("%s doesn\'t have any channels!" % self.channel,xbmc.LOGSEVERE)
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
        utils.log('Read RSS: %s' % url,xbmc.LOGINFO)
        if url not in rss_cache:
            utils.log('Feed URL not in cache, requesting...',xbmc.LOGINFO)
            xml = httpget(url)
            # utils.log("Received xml: %s" % xml,xbmc.LOGDEBUG)
            progs = listparser.parse(xml)
            if not progs: return []
            d = []
            for entry in progs.entries:
                pid = parse_entry_id(entry.id)
                p = programme_simple(pid, entry)
                d.append(p)
            utils.log('Found %d entries' % len(d),xbmc.LOGINFO)
            rss_cache[url] = d
        else:
            utils.log('RSS found in cache',xbmc.LOGINFO)
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

import xbmc
if os.environ.get( "OS" ) != "xbox":
    import threading

class IPlayerLockException(Exception):
    """
    Exception raised when IPlayer fails to obtain a resume lock
    """
    pass

class IPlayer(xbmc.Player):
    """
    An XBMC player object, for supporting iPlayer features suring playback of iPlayer programmes
    """

    # Static constants for resume db and lockfile paths, set by default.py on plugin startup
    RESUME_FILE = None
    RESUME_LOCK_FILE = None

    resume = None
    dates_added = None

    def __init__( self, core_player, pid, live ):
        utils.log("IPlayer initialised (core_player: %d, pid: %s, live: %s)" % (core_player, pid, live),xbmc.LOGINFO)
        self.paused = False
        self.live = live
        self.pid = pid
        if os.environ.get( "OS" ) != "xbox":
            self.cancelled = threading.Event()
        if live:
            # Live feed - no resume
            # Setup scheduling?
            pass
        else:
            if os.environ.get( "OS" ) != "xbox":
                # Acquire the resume lock, store the pid and load the resume file
                self._acquire_lock()

    def __del__( self ):
        utils.log("De-initialising...",xbmc.LOGINFO)
        # If resume is enabled, try to release the resume lock
        if os.environ.get( "OS" ) != "xbox":
            if not self.live:
                try: self.heartbeat.cancel()
                except: utils.log('No heartbeat on destruction',xbmc.LOGSEVERE)
                self._release_lock()
            # Refresh container to ensure '(resumeable)' is added if necessary
            xbmc.executebuiltin('Container.Refresh')


    def _acquire_lock( self ):
        if os.path.isfile(IPlayer.RESUME_LOCK_FILE):
            raise IPlayerLockException("Only one instance of iPlayer can be run at a time. Please stop any other streams you may be watching before opening a new stream")
        else:
            lock_fh = open(IPlayer.RESUME_LOCK_FILE, 'w')
            try:
                lock_fh.write("%s" % self)
            finally:
                lock_fh.close()

    def _release_lock( self ):
        self_has_lock = False
        lock_fh = open(IPlayer.RESUME_LOCK_FILE)
        try:
            self_has_lock = (lock_fh.read() == "%s" % self)
        finally:
            lock_fh.close()

        utils.log("Lock owner test: %s" % self_has_lock,xbmc.LOGDEBUG)
        if self_has_lock:
            utils.log("Removing lock file.",xbmc.LOGINFO)
            try:
                os.remove(IPlayer.RESUME_LOCK_FILE)
            except Exception, e:
                utils.log("Error removing iPlayer resume lock file! (%s)" % e,xbmc.LOGSEVERE)

    @staticmethod
    def force_release_lock():
        """
        If something goes wrong and the lock file is present after the IPlayer object that made it dies,
        it can be force deleted here (accessible from advanced plugin options)
        """
        try:
            os.remove(IPlayer.RESUME_LOCK_FILE)
            dialog = xbmcgui.Dialog()
            dialog.ok('Lock released', 'Successfully released lock')
        except:
            dialog = xbmcgui.Dialog()
            dialog.ok('Failed to force release lock', 'Failed to release lock')

    def run_heartbeat( self ):
        """
        Method is run every second to perform housekeeping tasks, e.g. updating the current seek time of the player.
        Heartbeat will continue until player stops playing.
        """
        utils.log("Heartbeat %d" % time.time(),xbmc.LOGDEBUG)
        self.heartbeat = threading.Timer(1.0, self.run_heartbeat)
        self.heartbeat.setDaemon(True)
        self.heartbeat.start()
        if not self.live and not self.cancelled.is_set():
            self.current_seek_time = self.getTime()
            utils.log("current_seek_time %s" % self.current_seek_time,xbmc.LOGDEBUG)
        elif self.cancelled.is_set():
            self.onPlayBackEnded()

    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing the stream
        utils.log("Begin playback of pid %s" % self.pid,xbmc.LOGINFO)
        self.paused = False
        if os.environ.get( "OS" ) != "xbox":
            self.run_heartbeat()

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing the stream
        if self.heartbeat: self.heartbeat.cancel()
        utils.log("Playback ended.",xbmc.LOGINFO)
        if os.environ.get( "OS" ) != "xbox":
            if not self.live:
                utils.log("Saving resume point for pid %s at %fs." % (self.pid, self.current_seek_time),xbmc.LOGINFO)
                self.save_resume_point( self.current_seek_time )
        self.__del__()

    def onPlayBackStopped( self ):
        if self.heartbeat: self.heartbeat.cancel()
        # Will be called when user stops xbmc playing the stream
        # The player needs to be unloaded to release the resume lock
        utils.log("Playback stopped.",xbmc.LOGINFO)
        if os.environ.get( "OS" ) != "xbox":
            if not self.live:
                utils.log("Saving resume point for pid %s at %fs." % (self.pid, self.current_seek_time),xbmc.LOGINFO)
                self.save_resume_point( self.current_seek_time )
        self.__del__()

    def onPlayBackPaused( self ):
        # Will be called when user pauses playback on a stream
        utils.log("Playback paused.",xbmc.LOGINFO)
        if os.environ.get( "OS" ) != "xbox":
            if not self.live:
                utils.log("Saving resume point for pid %s at %fs." % (self.pid, self.getTime()),xbmc.LOGINFO)
                self.save_resume_point( self.current_seek_time )
        self.paused = True

    def save_resume_point( self, resume_point ):
        """
        Updates the current resume point for the currently playing pid to resume_point, and commits the result to the resume db file
        """
        resume, dates_added = IPlayer.load_resume_file()
        resume[self.pid] = resume_point
        dates_added[self.pid] = time.time()
        utils.log("Saving resume point (pid %s, seekTime %fs, dateAdded %d) to resume file" % (self.pid, resume[self.pid], dates_added[self.pid]),xbmc.LOGNOTICE)
        IPlayer.save_resume_file(resume, dates_added)

    @staticmethod
    def load_resume_file():
        """
        Loads and parses the resume file, and returns a dictionary mapping pid -> resume_point
        Resume file format is three columns, separated by a single space, with platform dependent newlines
        First column is pid (string), second column is resume point (float), third column is date added
        If date added is more than thirty days ago, the pid entry will be ignored for cleanup
        Will only actually load the file once, caching the result for future calls.
        """

        if not IPlayer.resume:
            # Load resume file
            IPlayer.resume = {}
            IPlayer.dates_added = {}
            if os.path.isfile(IPlayer.RESUME_FILE):
                utils.log("Loading resume file: %s" % (IPlayer.RESUME_FILE),xbmc.LOGINFO)
                with open(IPlayer.RESUME_FILE, 'rU') as resume_fh:
                    resume_str = resume_fh.read()
                tokens = resume_str.split()
                # Three columns, pid, seekTime (which is a float) and date added (which is an integer, datetime in seconds), per line
                pids = tokens[0::3]
                seekTimes = [float(seekTime) for seekTime in tokens[1::3]]
                datesAdded = [int(dateAdded) for dateAdded in tokens[2::3]]
                pid_to_resume_point_map = []
                pid_to_date_added_map = []
                # if row was added less than days_to_keep days ago, add it to valid_mappings
                try: days_to_keep = int(__addon__.getSetting('resume_days_to_keep'))
                except: days_to_keep = 40
                limit_time = time.time() - 60*60*24*days_to_keep
                for i in range(len(pids)):
                    if datesAdded[i] > limit_time:
                        pid_to_resume_point_map.append( (pids[i], seekTimes[i]) )
                        pid_to_date_added_map.append( (pids[i], datesAdded[i]) )
                IPlayer.resume = dict(pid_to_resume_point_map)
                IPlayer.dates_added = dict(pid_to_date_added_map)
                utils.log("Found %d resume entries" % (len(IPlayer.resume.keys())),xbmc.LOGINFO)

        return IPlayer.resume, IPlayer.dates_added

    @staticmethod
    def delete_resume_point(pid_to_delete):
        utils.log("Deleting resume point for pid %s" % pid_to_delete,xbmc.LOGNOTICE)
        resume, dates_added = IPlayer.load_resume_file()
        del resume[pid_to_delete]
        del dates_added[pid_to_delete]
        IPlayer.save_resume_file(resume, dates_added)

    @staticmethod
    def save_resume_file(resume, dates_added):
        """
        Saves the current resume dictionary to disk. See load_resume_file for file format
        """

        IPlayer.resume = resume
        IPlayer.dates_added = dates_added

        str = ""
        utils.log("Saving %d entries to %s" % (len(resume.keys()), IPlayer.RESUME_FILE),xbmc.LOGINFO)
        resume_fh = open(IPlayer.RESUME_FILE, 'w')
        try:
            for pid, seekTime in resume.items():
                str += "%s %f %d%s" % (pid, seekTime, dates_added[pid], os.linesep)
            resume_fh.write(str)
        finally:
             resume_fh.close()

    def resume_and_play( self, url, listitem, is_tv, playresume=False ):
        """
        Intended to replace xbmc.Player.play(playlist), this method begins playback and seeks to any recorded resume point.
        XBMC is muted during seeking, as there is often a pause before seeking begins.
        """

        if os.environ.get( "OS" ) != "xbox" and not self.live and playresume:
            resume, dates_added = IPlayer.load_resume_file()
            if self.pid in resume.keys():
                utils.log("Resume point found for pid %s at %f, seeking..." % (self.pid, resume[self.pid]),xbmc.LOGNOTICE)
                listitem.setProperty('StartOffset', '%d' % resume[self.pid])

        if is_tv:
            play = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        else:
            play = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        play.clear()
        play.add(url, listitem)

        self.play(play)

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
