import cgi, os, sys, urllib, re
import xml.dom.minidom as dom
import logging
import xbmcplugin, xbmcgui, xbmc
from datetime import date

from iplayer2 import get_provider, httpget, get_protocol, get_port

# it would be nice to scrape what's on now - at least when the items are first created.

THUMB_DIR      = os.path.join(os.getcwd(), 'resources', 'media')

live_tv_channels = [
                    ('bbc_one_london', 'BBC One', 'bbc_one.png'),
                    ('bbc_two_england','BBC Two', 'bbc_two.png'),
                    ('bbc_three','BBC Three', 'bbc_three.png'),
                    ('bbc_four','BBC Four', 'bbc_four.png'),
                    ('cbbc','CBBC', 'cbbc.png'),
                    ('cbeebies','Cbeebies', 'cbeebies.png'),
                    ('bbc_news24','BBC News', 'bbc_news24.png'),
                    ('bbc_parliament','BBC Parliament', 'bbc_parliament.png'),
                    ('bbc_alba','BBC ALBA', 'bbc_alba.png'),
                    ('bbc_redbutton','BBC Red Button', 'bbc_one.png')
                    ]

def parseXML(url):
    xml = httpget(url)
    doc = dom.parseString(xml)
    root = doc.documentElement
    return root

def fetch_stream_info_old(channel):
    # read the simulcast xml
    cxml = 'http://www.bbc.co.uk/emp/simulcast/' + channel + '.xml'
    root = parseXML(cxml)
    surl = ''
    mbitrate = 0

    for media in root.getElementsByTagName( "media" ):
        conn  = media.getElementsByTagName( "connection" )[0]
        simulcast   = conn.attributes['identifier'].nodeValue
        server      = conn.attributes['server'].nodeValue
        kind        = conn.attributes['kind'].nodeValue
        application = conn.attributes['application'].nodeValue
        
        surl = 'http://www.bbc.co.uk/mediaselector/4/gtis/?server=%s&identifier=%s&kind=%s&application=%s&cb=62605' % (server , simulcast, kind, application)        
    
    # read the media selector xml
    root = parseXML(surl)
    token  = root.getElementsByTagName( "token" )[0].firstChild.nodeValue
    kind   = root.getElementsByTagName( "kind" )[0].firstChild.nodeValue
    server = root.getElementsByTagName( "server" )[0].firstChild.nodeValue
    identifier  = root.getElementsByTagName( "identifier" )[0].firstChild.nodeValue
    application = root.getElementsByTagName( "application" )[0].firstChild.nodeValue
    
    print 'token: ' + token, 'kind: ' + kind, 'server: ' + server, 'identifier: ' + identifier, 'application: ' + application
    url = "rtmp://%s:1935/%s/%s?auth=%s&aifp=xxxxxx" % (server, application, identifier, token)
    playpath = "%s?auth=%s&aifp=xxxxxx" % (identifier, token)
    url = "%s playpath=%s live=1" % (url, playpath)
    return (url)

def fetch_stream_info(streamchannel, bitrate, req_provider):
    # bbc seem to be changing the XML format - force new style
    if streamchannel=='bbc_one_london'  : streamchannel='bbc_one'
    if streamchannel=='bbc_two_england' : streamchannel='bbc_two'
    if streamchannel=='cbbc' : streamchannel='bbc_three'
    if streamchannel=='cbeebies' : streamchannel='bbc_four'

    identifier = streamchannel + '_live_rtmp'
    
    # red button doesn't have an _rtmp page (and therefore no akamai rtmp stream either) 
    if streamchannel == 'bbc_redbutton' :
        identifier = 'bbc_redbutton_live'
        req_provider = 'limelight'

    # experimental - cb seems to increase - but by how much? assume 1 per day for now
    # seems to be more random than that. However changing the number seems beneficial atm
    cbadd = date.today() - date(2010,6,17)
    cb = str(26512 + cbadd.days)

    if bitrate == 480: quality = 'iplayer_streaming_h264_flv_lo_live'
    elif bitrate == 800: quality = 'iplayer_streaming_h264_flv_live'
    elif bitrate >= 1500: quality = 'iplayer_streaming_h264_flv_high_live'
    
    surl = 'http://www.bbc.co.uk/mediaselector/4/mtis/stream/%s/%s/%s?cb=%s' % (identifier, quality, req_provider, cb)
    logging.info("getting media information from %s" % surl)
    root = parseXML(surl)
    mbitrate = 0
    url = ""
    media = root.getElementsByTagName( "media" )[0]

    conn  = media.getElementsByTagName( "connection" )[0]

    # rtmp streams
    identifier  = conn.attributes['identifier'].nodeValue
    server      = conn.attributes['server'].nodeValue
    auth        = conn.attributes['authString'].nodeValue
    supplier    = conn.attributes['supplier'].nodeValue

    # not always listed for some reason
    try: 
        application = conn.attributes['application'].nodeValue
    except:
        application = 'live'

    params = dict(protocol = get_protocol(), port = get_port(), server = server, auth = auth, ident = identifier, app = application)

    if supplier == "akamai" or supplier == "limelight":
        if supplier == "akamai":
            url = "%(protocol)s://%(server)s:%(port)s/%(app)s/?%(auth)s playpath=%(ident)s?%(auth)s" % params
        if supplier == "limelight":
            url = "%(protocol)s://%(server)s:%(port)s/ app=%(app)s?%(auth)s tcurl=%(protocol)s://%(server)s:%(port)s/%(app)s?%(auth)s playpath=%(ident)s" % params
        url += " swfurl=http://www.bbc.co.uk/emp/10player.swf swfvfy=1 live=1"

    return (url)


def play_stream(channel, bitrate, showDialog):
    bitrate = int(bitrate)
    # check to see if bbcthree/cbbc or bbcfour/cbeebies is on the air?    
    if channel == 'bbc_three' or channel == 'bbc_four' or channel == 'cbeebies' or channel == 'cbbc':
        surl = 'http://www.bbc.co.uk/iplayer/tv/'+channel
        cstr = httpget(surl)
        off_air_message = re.compile('<p class="off-air">(.*?)</p>').findall(cstr)
        if off_air_message:
            pDialog = xbmcgui.Dialog()
            pDialog.ok('IPlayer', off_air_message[0])
            return

    provider = get_provider()
    
    if channel=='bbc_parliament' or channel=='bbc_news24' or channel=='bbc_alba':
        url = fetch_stream_info_old(channel)
    else:
        # check for red button usage
        if channel == 'bbc_redbutton':
            pDialog = xbmcgui.Dialog()
            if pDialog.yesno("BBC Red Button Live Stream", "This will only work when the stream is broadcasting.", "If it is not on, xbmc will retry indefinately (crash)", "Do you want to try anyway?"):
                url = fetch_stream_info(channel, bitrate, provider)
            else:
                return
        else:
            url = fetch_stream_info(channel, bitrate, provider)

    if url == "":
        Dialog = xbmcgui.Dialog()
        pDialog.ok('IPlayer', "Sorry, stream is currently unavailable")

    if showDialog:
        pDialog = xbmcgui.DialogProgress()
        pDialog.create('IPlayer', 'Loading live stream info')
        xbmc.sleep(50)

    if showDialog: pDialog.update(50, 'Starting Stream')
    # build listitem to display whilst playing
    for j, (id, label, thumb) in enumerate(live_tv_channels):
        if id == channel:
            listitem = xbmcgui.ListItem(label=label+' - Live')
            listitem.setIconImage('defaultVideo.png')
            listitem.setThumbnailImage(os.path.join(THUMB_DIR, thumb))
                   
    play = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    play.clear()
    play.add(url,listitem)
    player = xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER)
    player.play(play)
    if showDialog: pDialog.close()
    
def make_url(channel=None):
    base = sys.argv[0]
    d = {}
    if channel: d['label'] = channel
    d['pid'] = 0       
    params = urllib.urlencode(d, True)
    return base + '?' + params    

def list_channels():
    handle = int(sys.argv[1])
    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_NONE )   
     
    for j, (id, label, thumb) in enumerate(live_tv_channels):
        url = make_url(channel=id)
        listitem = xbmcgui.ListItem(label=label)
        listitem.setIconImage('defaultVideo.png')
        listitem.setThumbnailImage(os.path.join(THUMB_DIR, thumb))        
        ok = xbmcplugin.addDirectoryItem(
            handle = handle, 
            url = url,
            listitem = listitem,
            isFolder = False,
        )

    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

##############################################
if __name__ == '__main__':
    args = cgi.parse_qs(sys.argv[2][1:])
    channel = args.get('label', [None])[0]
    if channel and channel != '':
        play_stream(channel,800)
    else:
        list_channels()
