import simplejson, urllib, urllib2, re, os, sys
json = simplejson

# Static text. 
APP_NAME = 'Dropbox'
LOGO = 'icon-default.png'

# Image resources.
ART_DEFAULT = R('art-default.jpg')
ICON_FOLDER = R('icon-folder.png')
ICON_PLAY = R('icon-play.png')
ICON_PHOTO = R('icon-photo.png')
ICON_TRACK = R('icon-track.png')
ICON_SEARCH = R('icon-search.png')
ICON_PREFERENCES = R('icon-preferences.png')

# Other definitions.
PLUGIN_PREFIX = '/video/dropbox'
debug = True
debug_raw = True

# Global variables.
cacheDropboxThreadStatus = False
cache = {}

####################################################################################################

def Start():
        Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, APP_NAME, LOGO)
	ObjectContainer.art = R(ART_DEFAULT)

	if Prefs['access_token'] != "":
		ValidatePrefs()

####################################################################################################

@handler(PLUGIN_PREFIX, APP_NAME, art = ART_DEFAULT, thumb = LOGO)
def MainMenu():
	oc = ObjectContainer(no_cache = True)

	if checkConfig():
		if debug == True: Log('Configuration check: OK!')

		oc = getDropboxStructure('Dropbox')

		# Add preferences.
		oc.add(InputDirectoryObject(key=Callback(searchDropbox), title = 'Crawl your dropbox', prompt = 'Search for', thumb = ICON_SEARCH))
		oc.add(PrefsObject(title = L('preferences')))
	else:
		if debug == True: Log('Configuration check: FAILED!')
		oc.title1 = None
		oc.header = L('error')
                oc.message = L('error_no_config')
		oc.add(PrefsObject(title = L('preferences'), thumb = ICON_PREFERENCES))

	return oc

####################################################################################################

def ValidatePrefs():
	if debug == True: Log("Validating preferences")
	global cacheDropboxThreadStatus
	mode = Prefs['access_mode'].lower()

	tmp = apiRequest("https://api.dropbox.com/1/metadata/" + mode + '/')
	if tmp != False:
		if debug == True: Log("Testcall to api finished with success. Preferences valid")
		Dict['PrefsValidated'] = True;
	else:
		if debug == True: Log("Testcall to api failed. Preferences invalid")
		Dict['PrefsValidated'] = False;

	# Handle caching thread.
	if Prefs['cache_use'] == True:
		if cacheDropboxThreadStatus == False:
			Thread.Create(cacheDropboxThread, globalize=True)
	else:
		if cacheDropboxThreadStatus == True:
			cacheDropboxThreadStatus = False
	return True

####################################################################################################

def checkConfig():
	if 'PrefsValidated' in Dict and Dict['PrefsValidated'] == True:
		return True
	else:
		return False

####################################################################################################

def cacheDropboxThread():
	if debug == True: Log("****** Starting cacheDropbox thread ***********")
	global cacheDropboxThreadStatus
	thread_sleep = int(Prefs['cache_update_interval'])*60

	cacheDropboxThreadStatus = True

	while Prefs['cache_use'] == True and cacheDropboxThreadStatus == True:
		if debug == True: Log("cacheDropbox thread() loop...")

		result = cacheDropboxStructure("/")

		# Clear existing cache and move temporary records.
		if result == True:
			clearDropboxCache()
			if debug == True: Log("Copying temporary records to live cache")
			for key in cache:
				if debug == True: Log("Copying cache for: " + key)
				Dict[key] = cache[key] 

		if debug == True: Log("****** cacheDropbox thread sleeping for " + str(thread_sleep) + " seconds ***********")
		Thread.Sleep(float(thread_sleep))

	clearCache()
	if debug == True: Log("Exiting cacheDropbox thread....")
	cacheDropboxThreadStatus = False

####################################################################################################

def clearDropboxCache():
	if debug == True: Log("Clearing existing Dropbox structure cache")
	delkeys = []
	for key in Dict:
		if re.match('\/', key):
			delkeys.append(key)
	for key in delkeys:
		if debug == True: Log("Deleting cache key: " + key)
		del Dict[key]

####################################################################################################

def cacheDropboxStructure(path = '/'):
	if debug == True: Log("Called cacheDropboxStructure(" + path + ")")
	global cache

	# Cache existing Dropbox structure.
	if debug == True: Log("Building cache from existing Dropbox structure")
	# Init temporary cache.
	if path == "/":
		cache = {}

	metadata = getDropboxMetadata(path)
	if debug_raw == True: Log("Got metadata for folder: " + path)
	if debug_raw == True: Log(metadata)
	if metadata == False:
		return False

	if debug == True: Log("Creating cache key: " + path)
	cache[path] = metadata
	for item in metadata['contents']:
		# Check wether it's a folder.
		if item['is_dir'] == True:
			result = cacheDropboxStructure(item['path'])
			if result == False:
				return False
	return True

####################################################################################################

def getFilenameFromPath(path):
	filepath, fileext = os.path.splitext(path)
	fileext = fileext.lower()
	filepatharray = filepath.split('/')
	return [filepatharray[len(filepatharray)-1], fileext]

####################################################################################################

def apiRequest(call):
	if debug == True: Log("apiRequest() - talking to dropbox api: " + call)
        headers = { "Authorization" : "Bearer " + Prefs['access_token'] }

	try:
	        req = urllib2.Request(call, None, headers)
	        response = urllib2.urlopen(req)
	        result = response.read()
	except Exception, e:
		if debug == True: Log("ERROR! apiRequest(): " + str(e))
		return False
        return result

####################################################################################################

def getDropboxMetadata(path, search = False, query = ''):
	mode = Prefs['access_mode'].lower() 
	call = ''
	if search == False:
		call = "https://api.dropbox.com/1/metadata/" + mode + path
	else:
		call = "https://api.dropbox.com/1/search/" + mode + path + "?" + query 
	if debug == True: Log("getDropboxMetadata() url call: " + call)

	tmp = apiRequest(call)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
		except Exception, e:
			if debug == True: Log("ERROR! getDropboxMetadata(): " + str(e))
			return False
		return json_data
	else:
		return False

####################################################################################################

def getDropboxLinkForFile(path):
	if debug == True: Log("Fetching metadata from dropbox for item: " + path)
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api.dropbox.com/1/media/" + mode + path)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
			if debug_raw == True: Log("Got link data for: " + path)
			if debug_raw == True: Log(json_data)
		except Exception, e:
			if debug == True: Log("ERROR! getDropboxLinkForFile(): " + str(e))
			return False
		return json_data
	else:
		return False

####################################################################################################

def getDropboxThumbnailForMedia(path, fallback):
	if debug == True: Log("Fetching thumbnail from dropbox for item: " + path)
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api-content.dropbox.com/1/thumbnails/" + mode + path + "?size=m")
	if debug == True: Log("Got thumbnail url: " + "https://api-content.dropbox.com/1/thumbnails/" + mode + path + "?size=m")

	if tmp != False:
		if debug == True: Log("Got thumbnail data from dropbox api")
		return DataObject(tmp, 'image/jpeg')
	else:
		if debug == True: Log("Could not fetch thumbnail data. Showing default image")
		return Redirect(fallback)

####################################################################################################

def createContentObjectList(metadata):
	dir_objlist = []
	file_objlist = []
	objlist = []
	# Loop through the content.
	for item in metadata:
		# Check wether it's a folder or file.
		if item['is_dir'] == True:
			if debug == True: Log("Adding folder '" + item['path'])
			foldernamearray = item['path'].split('/')
			foldername = foldernamearray[len(foldernamearray)-1]
			dir_objlist.append(DirectoryObject(key=Callback(getDropboxStructure, title=foldername,path=item['path']), title=foldername, thumb=ICON_FOLDER))
		else:
			if debug == True: Log("Evaluating item '" + item['path'])
			obj = createMediaObject(item)
			if obj != False:
				file_objlist.append(obj)
	objlist.extend(dir_objlist)
	objlist.extend(file_objlist)
	return objlist

####################################################################################################

def getDropboxStructure(title, path = '/'):
	oc = ObjectContainer(no_cache = True, art = R('logo.png'), title2 = title)
	if debug == True: Log("Called getDropboxStructure(" + path + ")")

	# Check for existing configured and loaded cache.
	metadata = {}
	if Prefs['cache_use'] == True and path in cache:
		if debug == True: Log("Using metadata from: cache") 
		metadata = cache[path]
	else:
		if debug == True: Log("Using metadata from: Live Dropbox API")
		metadata = getDropboxMetadata(path)

	if metadata == False:
		oc.title1 = None
		oc.header = L('error')
		oc.message = L('error_webrequest_failed')
		return oc 

	if debug_raw == True: Log("Got metadata for folder: " + path)
	if debug_raw == True: Log(metadata)

	objlist = createContentObjectList(metadata['contents'])
	for obj in objlist:
		oc.add(obj)

	return oc

####################################################################################################

def searchDropbox(query):
	oc = ObjectContainer(no_cache = True, art = R('logo.png'))
        if debug == True: Log("Crawling dropbox for: " + query)

	urlquery = {'query' : query }
	metadata = getDropboxMetadata('/', True, urllib.urlencode(urlquery))
	if metadata == False:
		oc.title1 = None
		oc.header = L('error')
		oc.message = L('error_webrequest_failed')
		return oc

	if debug_raw == True: Log("Got metadata for query: " + query)
	if debug_raw == True: Log(metadata)

	objlist = createContentObjectList(metadata)
	for obj in objlist:
		oc.add(obj)

	if len(objlist) == 0:
		
		return ObjectContainer(header = L('text_search_result'), message = L('text_no_search_results_for') + " \"" + query + "\"")
        return oc

####################################################################################################

def createMediaObject(item):
	if debug == True: Log("Checking item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path']) 
	fileext = fileext.lower()

	# Handle movie files.
	if fileext == '.mp4' or fileext == '.mkv' or fileext == '.avi' or fileext == '.mov':
		return createVideoClipObject(item)
	if fileext == '.jpg' or fileext == '.jpeg' or fileext == '.png' or fileext == '.gif' or fileext == '.bmp' or fileext == '.tif' or fileext == '.tiff':
		return createPhotoObject(item)
	if fileext == '.mp3' or fileext == '.wav' or fileext == '.aac' or fileext == '.m4a':
		return createTrackObject(item)
	return False

####################################################################################################

def createVideoClipObject(item, container = False):
	if debug == True: Log("Creating VideoClipObject for item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path'])
	directurl = "https://api-content.dropbox.com/1/files/" + Prefs['access_mode'].lower() + item['path']

	summary = "Size: " + item['size'] + "\n"
	if container:
		summary = summary + "Path: " + item['path'] + "\n"
		summary = summary + "Modified: " +  item['modified'] + "\n"

	vco = VideoClipObject(
		key = Callback(createVideoClipObject, item = item, container = True),
		rating_key = directurl,
		title = filename + fileext,
		summary = summary, 
		thumb = Callback(getDropboxThumbnailForMedia, path = item['path'], fallback = ICON_PLAY),
		items = []
	)
	mo = MediaObject(parts = [PartObject(key = Callback(getUrlForPath, item = item))])

	# Guess the video container type.
	if fileext == ".mp4":
		mo.container = Container.MP4
	elif fileext == ".mkv":
		mo.container = Container.MKV
	elif fileext == ".avi":
		mo.container = Container.AVI
	else:
		mo.container = Container.MOV

	# Define default codec information.
	mo.video_codec = VideoCodec.H264
	mo.audio_codec = AudioCodec.AAC

	# Append mediaobject to clipobject.
	vco.items.append(mo)

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco

####################################################################################################

def createPhotoObject(item):
	if debug == True: Log("Creating PhotoObject for item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path'])
	directurl = "https://api-content.dropbox.com/1/files/" + Prefs['access_mode'].lower() + item['path']

	po = PhotoObject(
		key = Callback(getUrlForPath, item = item),
		rating_key = directurl, 
		title = filename + fileext,
		thumb = Callback(getDropboxThumbnailForMedia, path = item['path'], fallback = ICON_PHOTO)
	)
	return po

####################################################################################################

def createTrackObject(item):
	if debug == True: Log("Creating TrackObject for item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path'])
	directurl = "https://api-content.dropbox.com/1/files/" + Prefs['access_mode'].lower() + item['path']

	to = TrackObject(
		key = Callback(getUrlForPath, item = item),
		rating_key = directurl,
		title = filename + fileext,
		thumb = ICON_TRACK
	)
	return to

####################################################################################################

def getUrlForPath(item):
	urldata = getDropboxLinkForFile(item['path'])
	if debug == True: Log("URL for object " + item['path'] + " : " + urldata['url'] + " (expires: " + urldata['expires'] + ")")
	return Redirect(urldata['url'])
