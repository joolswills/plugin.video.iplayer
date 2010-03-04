##
## Data on TV Channels, Radio Stations & Programme Categories
##
##

channels_tv_list = [
    ('bbc_one', 'BBC One'), 
    ('bbc_two', 'BBC Two'), 
    ('bbc_three', 'BBC Three'), 
    ('bbc_four', 'BBC Four'),
    ('cbbc', 'CBBC'),
    ('cbeebies', 'CBeebies'),
    ('bbc_hd', 'BBC HD'), 
    ('bbc_news24', 'BBC News Channel'),
    ('bbc_parliament', 'BBC Parliament'),
    ('bbc_alba', 'BBC Alba'),
]

channels_tv = dict(channels_tv_list)

radio_station_info = [   
    {'id': 'bbc_radio_one',
     'name': 'Radio 1',
     'logo': None,
     'type': 'national',
     'webcam' : 'http://www.bbc.co.uk/radio1/webcam/images/live/webcam.jpg',
     'stream': 'http://www.bbc.co.uk/radio1/wm_asx/aod/radio1_hi.asx'},
 
    {'id': 'bbc_1xtra',
     'name': 'Radio 1 Xtra',
     'logo': None,
     'type': 'national',
     'webcam': 'http://www.bbc.co.uk/1xtra/webcam/live/1xtraa.jpg',
     'stream': 'http://www.bbc.co.uk/1xtra/realmedia/1xtra_hi.asx'},

    {'id': 'bbc_radio_two',
     'name': 'Radio 2',
     'logo': None,
     'type': 'national',
     'webcam': 'http://www.bbc.co.uk/radio2/webcam/live/radio2.jpg',
     'stream': 'http://www.bbc.co.uk/radio2/wm_asx/aod/radio2_hi.asx'},

    {'id': 'bbc_radio_three',
     'name': 'Radio 3',
     'logo': None,
     'type': 'national',
     'stream': 'http://www.bbc.co.uk/radio3/wm_asx/aod/radio3_hi.asx'},

    {'id': 'bbc_radio_four',
     'name': 'Radio 4',
     'logo': None,
     'type': 'national',
     'stream': 'http://www.bbc.co.uk/radio4/wm_asx/aod/radio4.asx'},

    {'id': 'bbc_radio_five_live',
     'name': 'Radio 5 Live',
     'logo': None,
     'type': 'national',
     'webcam': 'http://www.bbc.co.uk/fivelive/inside/webcam/5Lwebcam1.jpg',
     'stream': 'http://www.bbc.co.uk/fivelive/live/live.asx'},

    {'id': 'bbc_radio_five_live_sports_extra',
     'name': 'Radio 5 Live Sports Extra',
      'logo': None,
     'type': 'national',
     'stream': 'http://www.bbc.co.uk/fivelive/live/live_sportsextra.asx'},

    {'id': 'bbc_6music',
     'name': 'Radio 6 Music',
      'logo': None,
     'type': 'national',
     'webcam': 'http://www.bbc.co.uk/6music/webcam/live/6music.jpg',
     'stream': 'http://bbc.co.uk/radio/listen/live/r6.asx'},

    {'id': 'bbc_7',
     'name': 'Radio 7',
     'logo': None,
     'type': 'national',
     'stream': 'http://www.bbc.co.uk/bbc7/realplayer/bbc7_hi.asx'},

    {'id': 'bbc_asian_network',
     'name': 'Asian Network',
     'logo': None,
     'type': 'national',
     'webcam': 'http://www.bbc.co.uk/asiannetwork/webcams/birmingham.jpg',
     'stream': 'http://www.bbc.co.uk/asiannetwork/rams/asiannet_hi.asx'},

    {'id': 'bbc_radio_scotland',
     'name': 'BBC Scotland',
     'logo': None,
     'type': 'regional',
     'stream': 'http://wmlive.bbc.co.uk/wms/nations/scotland'},

    {'id': 'bbc_radio_ulster',
     'name': 'BBC Ulster',
     'logo': None,
     'type': 'regional',
     'stream': 'http://wmlive.bbc.co.uk/wms/nations/ulster'},

    {'id': 'bbc_radio_foyle',
     'name': 'Radio Foyle',
     'logo': None,
     'type': 'regional',
     'stream': 'http://wmlive.bbc.co.uk/wms/nations/foyle'},

    {'id': 'bbc_radio_wales',
     'name': 'BBC Wales',
     'logo': None,
     'type': 'regional',
     'stream': 'http://wmlive.bbc.co.uk/wms/nations/wales'},

    {'id': 'bbc_radio_cymru',
     'name': 'BBC Cymru',
     'logo': None,
     'type': 'regional',
     'stream': 'http://wmlive.bbc.co.uk/wms/nations/cymru'},

    {'id': 'bbc_world_service',
     'name': 'World Service',
     'logo': None,
     'type': 'national',
     'stream': 'http://www.bbc.co.uk/worldservice/meta/tx/nb/live/www15.asx'},

    {'id': 'bbc_radio_nan_gaidheal',
     'name': 'BBC nan Gaidheal',
     'logo': None,
     'type': 'regional',
     'stream': 'http://wmlive.bbc.co.uk/wms/nations/nangaidheal'},

    {'id': 'bbc_radio_berkshire',
     'name': 'BBC Berkshire',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_berks.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrberkshire'},

    {'id': 'bbc_radio_bristol',
     'name': 'BBC Bristol',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/bristol.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrbristol'},

    {'id': 'bbc_radio_cambridge',
     'name': 'BBC Cambridge',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/cambridgeshire.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrcambridgeshire'},

    {'id': 'bbc_radio_cornwall',
     'name': 'BBC Cornwall',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/cornwall.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrcornwall'},

    {'id': 'bbc_radio_coventry_warwickshire',
     'name': 'BBC Coventry Warwickshire',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/cov_warks.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrcoventryandwarwickshire'},

    {'id': 'bbc_radio_cumbria',
     'name': 'BBC Cumbria',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/cumbria.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrcumbria'},

    {'id': 'bbc_radio_derby',
     'name': 'BBC Derby',
     'logo': 'http://www.bbc.co.uk/englandcms/derby/images/rh_nav170_derby.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrderby'},

    {'id': 'bbc_radio_devon',
     'name': 'BBC Devon',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_devon.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrdevon'},

    {'id': 'bbc_radio_essex',
     'name': 'BBC Essex',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_essex.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lressex'},

    {'id': 'bbc_radio_gloucestershire',
     'name': 'BBC Gloucestershire',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/gloucestershire.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrgloucestershire'},

    {'id': 'bbc_radio_guernsey',
     'name': 'BBC Guernsey',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/guernsey.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrguernsey'},

    {'id': 'bbc_radio_hereford_worcester',
     'name': 'BBC Hereford/Worcester',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/hereford_worcester.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrherefordandworcester'},

    {'id': 'bbc_radio_humberside',
     'name': 'BBC Humberside',
     'logo': 'http://www.bbc.co.uk/radio/images/home/r-home-nation-regions.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrhumberside'},

    {'id': 'bbc_radio_jersey',
     'name': 'BBC Jersey',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/jersey.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrjersey'},

    {'id': 'bbc_radio_kent',
     'name': 'BBC Kent',
     'logo': 'http://www.bbc.co.uk/radio/images/home/r-home-nation-regions.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrkent'},

    {'id': 'bbc_radio_lancashire',
     'name': 'BBC Lancashire',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_lancs.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrlancashire'},

    {'id': 'bbc_radio_leeds',
     'name': 'BBC Leeds',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_leeds.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrleeds'},

    {'id': 'bbc_radio_leicester',
     'name': 'BBC Leicester',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/leicester.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrleicester'},

    {'id': 'bbc_radio_lincolnshire',
     'name': 'BBC Lincolnshire',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/lincs.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrlincolnshire'},

    {'id': 'bbc_london',
     'name': 'BBC London',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrlondon'},

    {'id': 'bbc_radio_manchester',
     'name': 'BBC Manchester',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrmanchester'},

    {'id': 'bbc_radio_merseyside',
     'name': 'BBC Merseyside',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/merseyside.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrmerseyside'},

    {'id': 'bbc_radio_newcastle',
     'name': 'BBC Newcastle',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/newcastle.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrnewcastle'},

    {'id': 'bbc_radio_norfolk',
     'name': 'BBC Norfolk',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/norfolk.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrnorfolk'},

    {'id': 'bbc_radio_northampton',
     'name': 'BBC Northampton',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/northampton.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrnorthampton'},

    {'id': 'bbc_radio_nottingham',
     'name': 'BBC Nottingham',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrnottingham'},

    {'id': 'bbc_radio_oxford',
     'name': 'BBC Oxford',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_oxford.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lroxford'},

    {'id': 'bbc_radio_sheffield',
     'name': 'BBC Sheffield',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_sheffield.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrsheffield'},

    {'id': 'bbc_radio_shropshire',
     'name': 'BBC Shropshire',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/shropshire.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrshropshire'},

    {'id': 'bbc_radio_solent',
     'name': 'BBC Solent',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/solent.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrsolent'},

    {'id': 'bbc_radio_somerset_sound',
     'name': 'BBC Somerset',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_somerset.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrsomerset'},

    {'id': 'bbc_radio_stoke',
     'name': 'BBC Stoke',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/stoke.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrstoke'},

    {'id': 'bbc_radio_suffolk',
     'name': 'BBC Suffolk',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/suffolk.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrsuffolk'},

    {'id': 'bbc_radio_surrey',
     'name': 'BBC Surrey',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrsurrey'},

    {'id': 'bbc_radio_sussex',
     'name': 'BBC Sussex',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrsussex'},

    {'id': 'bbc_radio_wiltshire',
     'name': 'BBC Wiltshire',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrwiltshire'},

    {'id': 'bbc_radio_york',
     'name': 'BBC York',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/york.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lryork'},

    {'id': 'bbc_tees',
     'name': 'BBC Tees',
     'logo': 'http://www.bbc.co.uk/englandcms/localradio/images/tees.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrtees'},

    {'id': 'bbc_three_counties_radio',
     'name': 'BBC Three Counties Radio',
     'logo': 'http://www.bbc.co.uk/englandcms/images/rh_nav170_3counties.gif',
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrthreecounties'},

    {'id': 'bbc_wm',
     'name': 'BBC WM',
     'logo': None,
     'type': 'local',
     'stream': 'http://wmlive.bbc.co.uk/wms/england/lrwm'},
]

# build a list of radio channel IDs
channels_radio_list = []  
channels_radio_type_list = {}
for i in radio_station_info:
    channels_radio_list.append((i['id'], i['name']))
    rtype = i['type']
    if rtype != None:
        if not channels_radio_type_list.has_key(rtype):
            # initialize radio type list
            channels_radio_type_list[rtype] = []
        channels_radio_type_list[rtype].append((i['id'], i['name']))
        
# list of live stations 
live_radio_stations_list = []
for i in radio_station_info:
    live_radio_stations_list.append((i['name'], i['stream']))
live_radio_stations = dict(live_radio_stations_list)

channels = dict(channels_tv_list + channels_radio_list)
channels_tv = dict(channels_tv_list)
channels_radio = dict(channels_radio_list)

# build a dict of available logos
channels_logos = {}
for i in radio_station_info:
    channels_logos[i['id']] = i['logo']

live_webcams_list = []
for i in radio_station_info:
    if i.has_key('webcam'):
        live_webcams_list.append((i['name'], i['webcam']))
live_webcams = dict(live_webcams_list)

categories_list = [
    ('childrens', 'Children\'s'),
    ('comedy', 'Comedy'),
    ('drama', 'Drama'),
    ('entertainment', 'Entertainment'),
    ('factual', 'Factual'),
    ('music', 'Music'),
    ('news', 'News'),
    ('religion_and_ethics', 'Religion & Ethics'),
    ('sport', 'Sport'),
    ('olympics', 'Olympics'),
    ('wales', 'Wales'),
    ('signed', 'Sign Zone')
]
categories = dict(categories_list)


