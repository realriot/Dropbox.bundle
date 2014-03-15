import simplejson, urllib, urllib2, datetime, re, os, sys
from mod_tmdb import *
json = simplejson

# Static text. 
APP_NAME = 'Dropbox'
ICON_DEFAULT = 'icon-default.png'
ART_DEFAULT = 'art-default.jpg'

# Image resources.
ICON_FOLDER = R('icon-folder.png')
ICON_PLAY = R('icon-play.png')
ICON_PHOTO = R('icon-photo.png')
ICON_TRACK = R('icon-track.png')
ICON_SEARCH = R('icon-search.png')
ICON_PREFERENCES = R('icon-preferences.png')

# Other definitions.
PLUGIN_PREFIX = '/video/dropbox'

# Global variables.
cacheDropboxThreadStatus = False
cache = {}

####################################################################################################

def Start():
	ObjectContainer.art = R(ART_DEFAULT)

	if Prefs['access_token'] != "":
		ValidatePrefs()

####################################################################################################

@handler(PLUGIN_PREFIX, APP_NAME, ICON_DEFAULT, ART_DEFAULT)
def MainMenu():
	oc = ObjectContainer(no_cache = True)

	if checkConfig():
		if Prefs['debug_log'] == True: Log('Configuration check: OK!')

		oc = getDropboxStructure('Dropbox')

		# Add preferences.
		oc.add(InputDirectoryObject(key=Callback(searchDropbox), title = 'Crawl your dropbox', prompt = 'Search for', thumb = ICON_SEARCH))
		oc.add(PrefsObject(title = L('preferences')))
	else:
		if Prefs['debug_log'] == True: Log('Configuration check: FAILED!')
		oc.title1 = None
		oc.header = L('error')
                oc.message = L('error_no_config')
		oc.add(PrefsObject(title = L('preferences'), thumb = ICON_PREFERENCES))

	return oc

####################################################################################################

def ValidatePrefs():
	if Prefs['debug_log'] == True: Log("Validating preferences")
	global cacheDropboxThreadStatus
	mode = Prefs['access_mode'].lower()

	tmp = apiRequest("https://api.dropbox.com/1/metadata/" + mode + '/')
	if tmp != False:
		if Prefs['debug_log'] == True: Log("Testcall to api finished with success. Preferences valid")
		Dict['PrefsValidated'] = True;
	else:
		if Prefs['debug_log'] == True: Log("Testcall to api failed. Preferences invalid")
		Dict['PrefsValidated'] = False;

	# Handle caching thread.
	if Prefs['cache_use'] == True:
		if cacheDropboxThreadStatus == False:
			Thread.Create(cacheDropboxThread, globalize=True)
	else:
		if cacheDropboxThreadStatus == True:
			cacheDropboxThreadStatus = False
		else:
			clearDropboxCache()

	# Handle TMDb configuration.
	if Prefs['tmdb_use'] == False:
		clearTMDBCache()

	return True

####################################################################################################

def checkConfig():
	if 'PrefsValidated' in Dict and Dict['PrefsValidated'] == True:
		return True
	else:
		return False

####################################################################################################

def cacheDropboxThread():
	if Prefs['debug_log'] == True: Log("****** Starting cacheDropbox thread ***********")
	global cacheDropboxThreadStatus
	thread_sleep = int(Prefs['cache_update_interval'])*60

	cacheDropboxThreadStatus = True

	while Prefs['cache_use'] == True and cacheDropboxThreadStatus == True:
		if Prefs['debug_log'] == True: Log("cacheDropbox thread() loop...")

		result = cacheDropboxStructure("/")

		# Clear existing cache and move temporary records.
		if result == True:
			clearDropboxCache()
			if Prefs['debug_log'] == True: Log("Copying temporary records to live cache")
			for key in cache:
				if Prefs['debug_log'] == True: Log("Copying cache for: " + key)
				Dict[key] = cache[key] 

		if Prefs['debug_log'] == True: Log("****** cacheDropbox thread sleeping for " + str(thread_sleep) + " seconds ***********")
		Thread.Sleep(float(thread_sleep))

	clearDropboxCache()
	if Prefs['debug_log'] == True: Log("Exiting cacheDropbox thread....")
	cacheDropboxThreadStatus = False

####################################################################################################

def clearDropboxCache():
	if Prefs['debug_log'] == True: Log("Clearing existing Dropbox structure cache")
	delkeys = []
	for key in Dict:
		if re.match('\/', key):
			delkeys.append(key)
	for key in delkeys:
		if Prefs['debug_log'] == True: Log("Deleting cache key: " + key)
		del Dict[key]

####################################################################################################

def clearTMDBCache():
	if Prefs['debug_log'] == True: Log("Clearing existing TMDb cache")
	delkeys = []
	for key in Dict:
		if re.match('tmdb', key):
			delkeys.append(key)
	for key in delkeys:
		if Prefs['debug_log'] == True: Log("Deleting cache key: " + key)
		del Dict[key]

####################################################################################################

def cacheDropboxStructure(path = '/'):
	if Prefs['debug_log'] == True: Log("Called cacheDropboxStructure(" + path + ")")
	global cache

	# Cache existing Dropbox structure.
	if Prefs['debug_log'] == True: Log("Building cache from existing Dropbox structure")
	# Init temporary cache.
	if path == "/":
		cache = {}

	metadata = getDropboxMetadata(path)
	if Prefs['debug_log_raw'] == True: Log("Got metadata for folder: " + path)
	if Prefs['debug_log_raw'] == True: Log(metadata)
	if metadata == False:
		return False

	if Prefs['debug_log'] == True: Log("Creating cache key: " + path)
	cache[path] = metadata
	for item in metadata['contents']:
		# Check wether it's a folder.
		if item['is_dir'] == True:
			result = cacheDropboxStructure(item['path'])
			if result == False:
				return False
		else:
			if Prefs['tmdb_use'] == True and Prefs['tmdb_apikey'] != "" and getMediaTypeForFile(item) == "video":
				if "tmdb_" + item['path'] not in Dict:
					if Prefs['debug_log'] == True: Log("No TMDb data in cache. Looking up: " + item['path'])
					filename, fileext = getFilenameFromPath(item['path'])
					tmdbdata = tmdbSearchMovie(Prefs['tmdb_apikey'], Prefs['tmdb_language'], filename.lower())
					if tmdbdata != False:
						Dict["tmdb_" + item['path']] = tmdbdata
				else:
					if Prefs['debug_log'] == True: Log("TMDb data already in cache for: " + item['path'])
	return True

####################################################################################################

def getFilenameFromPath(path):
	filepath, fileext = os.path.splitext(path)
	fileext = fileext.lower()
	filepatharray = filepath.split('/')
	return [filepatharray[len(filepatharray)-1], fileext]

####################################################################################################

def apiRequest(call):
	if Prefs['debug_log'] == True: Log("apiRequest() - talking to dropbox api: " + call)
        headers = { "Authorization" : "Bearer " + Prefs['access_token'] }

	try:
	        req = urllib2.Request(call, None, headers)
	        response = urllib2.urlopen(req)
	        result = response.read()
	except Exception, e:
		if Prefs['debug_log'] == True: Log("ERROR! apiRequest(): " + str(e))
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
	if Prefs['debug_log'] == True: Log("getDropboxMetadata() url call: " + call)

	tmp = apiRequest(call)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
		except Exception, e:
			if Prefs['debug_log'] == True: Log("ERROR! getDropboxMetadata(): " + str(e))
			return False
		return json_data
	else:
		return False

####################################################################################################

def getDropboxLinkForFile(path):
	if Prefs['debug_log'] == True: Log("Fetching metadata from dropbox for item: " + path)
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api.dropbox.com/1/media/" + mode + path)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
			if Prefs['debug_log_raw'] == True: Log("Got link data for: " + path)
			if Prefs['debug_log_raw'] == True: Log(json_data)
		except Exception, e:
			if Prefs['debug_log'] == True: Log("ERROR! getDropboxLinkForFile(): " + str(e))
			return False
		return json_data
	else:
		return False

####################################################################################################

def getDropboxThumbnailForMedia(path, fallback):
	if Prefs['debug_log'] == True: Log("Fetching thumbnail from dropbox for item: " + path)
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api-content.dropbox.com/1/thumbnails/" + mode + path + "?size=m")
	if Prefs['debug_log'] == True: Log("Got thumbnail url: " + "https://api-content.dropbox.com/1/thumbnails/" + mode + path + "?size=m")

	if tmp != False:
		if Prefs['debug_log'] == True: Log("Got thumbnail data from dropbox api")
		return DataObject(tmp, 'image/jpeg')
	else:
		if Prefs['debug_log'] == True: Log("Could not fetch thumbnail data. Showing default image")
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
			if Prefs['debug_log'] == True: Log("Adding folder '" + item['path'])
			foldernamearray = item['path'].split('/')
			foldername = foldernamearray[len(foldernamearray)-1]
			dir_objlist.append(DirectoryObject(key=Callback(getDropboxStructure, title=foldername,path=item['path']), title=foldername, thumb=ICON_FOLDER))
		else:
			if Prefs['debug_log'] == True: Log("Creating object for item '" + item['path'])

			obj = False
			# Create video object.
			if getMediaTypeForFile(item) == "video":
				obj = createVideoObject(item)
			# Create picture object.
			if getMediaTypeForFile(item) == "picture":
				obj = createPhotoObject(item)
			# Create track (audio) object.
			if getMediaTypeForFile(item) == "track":
				obj = createTrackObject(item)
			if obj != False:
				file_objlist.append(obj)
	objlist.extend(dir_objlist)
	objlist.extend(file_objlist)
	return objlist

####################################################################################################

def getDropboxStructure(title, path = '/'):
	oc = ObjectContainer(no_cache = True, art = R('logo.png'), title2 = title)
	if Prefs['debug_log'] == True: Log("Called getDropboxStructure(" + path + ")")

	# Check for existing configured and loaded cache.
	metadata = {}
	if Prefs['cache_use'] == True and path in cache:
		if Prefs['debug_log'] == True: Log("Using metadata from: cache") 
		metadata = cache[path]
	else:
		if Prefs['debug_log'] == True: Log("Using metadata from: Live Dropbox API")
		metadata = getDropboxMetadata(path)

	if metadata == False:
		oc.title1 = None
		oc.header = L('error')
		oc.message = L('error_webrequest_failed')
		return oc 

	if Prefs['debug_log_raw'] == True: Log("Got metadata for folder: " + path)
	if Prefs['debug_log_raw'] == True: Log(metadata)

	objlist = createContentObjectList(metadata['contents'])
	for obj in objlist:
		oc.add(obj)

	return oc

####################################################################################################

def searchDropbox(query):
	oc = ObjectContainer(no_cache = True, art = R('logo.png'))
        if Prefs['debug_log'] == True: Log("Crawling dropbox for: " + query)

	urlquery = {'query' : query }
	metadata = getDropboxMetadata('/', True, urllib.urlencode(urlquery))
	if metadata == False:
		oc.title1 = None
		oc.header = L('error')
		oc.message = L('error_webrequest_failed')
		return oc

	if Prefs['debug_log_raw'] == True: Log("Got metadata for query: " + query)
	if Prefs['debug_log_raw'] == True: Log(metadata)

	objlist = createContentObjectList(metadata)
	for obj in objlist:
		oc.add(obj)

	if len(objlist) == 0:
		
		return ObjectContainer(header = L('text_search_result'), message = L('text_no_search_results_for') + " \"" + query + "\"")
        return oc

####################################################################################################

def createVideoObject(item, container = False):
	if Prefs['debug_log'] == True: Log("Creating VideoClipObject for item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path'])
	directurl = "https://api-content.dropbox.com/1/files/" + Prefs['access_mode'].lower() + item['path']

	# Standard clip informations.
	title = filename + fileext
	summary = "Size: " + item['size'] + "\n"
	if container:
		summary = summary + "Path: " + item['path'] + "\n"
		summary = summary + "Modified: " +  item['modified'] + "\n"

	# Create standard VideoClipObject.
	vo = VideoClipObject(
		key = Callback(createVideoObject, item = item, container = True),
		rating_key = directurl,
		items = []
	)

	# Run tmdb lookup if configured.
	tmdbdata = False
	if Prefs['tmdb_use'] == True and Prefs['tmdb_apikey'] != "":
		if "tmdb_" + item['path'] in Dict:
			if Prefs['debug_log'] == True: Log("Found TMDb data in cache for: " + item['path'])
			tmdbdata = Dict["tmdb_" + item['path']]
		else:
			if Prefs['debug_log'] == True: Log("Looking up TMDb data for: " + item['path'])
			tmdbdata = tmdbSearchMovie(Prefs['tmdb_apikey'], Prefs['tmdb_language'], filename.lower())
			if tmdbdata != False:
				Dict["tmdb_" + item['path']] = tmdbdata

		# Use TMDb data to enrich video clip metadata.
		if tmdbdata != False:
			if Prefs['debug_log_raw'] == True: Log("TMDb data: " + str(tmdbdata))

			vo = MovieObject(
				key = Callback(createVideoObject, item = item, container = True),
				rating_key = directurl,
				items = []
			)

			# Prepare genres.
			genres = []
			for genre in tmdbdata['genres']:
				genres.append(genre['name'])

			# Prepare production countries.
			countries = []
			for country in tmdbdata['production_countries']:
				countries.append(country['name'])

			vo.title = "title" + tmdbdata['title']
			vo.summary = tmdbdata['overview']
			vo.duration = int(tmdbdata['runtime'])*60000
			vo.tagline = "tagline " + tmdbdata['tagline']
			vo.rating = float(tmdbdata['vote_average'])
			vo.original_title = "Orig title " + tmdbdata['original_title']
			vo.year = datetime.datetime.strptime(tmdbdata['release_date'], '%Y-%m-%d').year
			vo.originally_available_at = datetime.datetime.strptime(tmdbdata['release_date'], '%Y-%m-%d')
			vo.genres = genres
			vo.countries = countries
			vo.thumb = "http://image.tmdb.org/t/p/w342" + tmdbdata['poster_path']
			vo.art = "http://image.tmdb.org/t/p/w500" + tmdbdata['backdrop_path']

			vo.tags.add("tag1")
			vo.tags.add("tag2")

			vo.source_title = "YouTube"

			vo.studio = "My Studio"

			vo.trivia = "Trivia Text"

			vo.quotes = "Quotes text"

			vo.content_rating = "Content rating"

			vo.content_rating_age = 16

			vo.writers.add("Writer1")
			vo.writers.add("Writer2")

			vo.directors.add("Director1")
			vo.directors.add("Director2")

			vo.producers.add("Producer1")
			vo.producers.add("Producer2")

	# Add standard clip informations if there wasn't a successfull TMDb lookup.
	if tmdbdata == False:
		vo.title = title
		vo.summary = summary
		vo.thumb = Callback(getDropboxThumbnailForMedia, path = item['path'], fallback = ICON_PLAY)

	# Add MediaObject and lookup url.
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
	vo.items.append(mo)

	if container:
		return ObjectContainer(objects = [vo])
	else:
		return vo

####################################################################################################

def createPhotoObject(item):
	if Prefs['debug_log'] == True: Log("Creating PhotoObject for item: " + item['path'])
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
	if Prefs['debug_log'] == True: Log("Creating TrackObject for item: " + item['path'])
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
	if Prefs['debug_log'] == True: Log("URL for object " + item['path'] + " : " + urldata['url'] + " (expires: " + urldata['expires'] + ")")
	return Redirect(urldata['url'])

####################################################################################################

def getMediaTypeForFile(item):
	filename, fileext = getFilenameFromPath(item['path'])
	fileext = fileext.lower()

	# Handle movie files.
	if fileext == '.mp4' or fileext == '.mkv' or fileext == '.avi' or fileext == '.mov':
		return "video" 
	if fileext == '.jpg' or fileext == '.jpeg' or fileext == '.png' or fileext == '.gif' or fileext == '.bmp' or fileext == '.tif' or fileext == '.tiff':
		return "picture" 
	if fileext == '.mp3' or fileext == '.wav' or fileext == '.aac' or fileext == '.m4a':
		return "track" 
	return False
