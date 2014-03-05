import simplejson, urllib, urllib2, os
json = simplejson

# Static text. 
APP_NAME = 'Dropbox'
LOGO = 'logo.png'

# Image resources.
ICON_FOLDER = R('folder.png')
ICON_PLAY = R('play.png')
ICON_PHOTO = R('photo.png')
ICON_TRACK = R('track.png')
ICON_SEARCH = R('search.png')
ICON_PREFERENCES = R('preferences.png')

# Other definitions.
PLUGIN_PREFIX = '/video/dropbox'
debug = True
debug_raw = True

####################################################################################################

@handler(PLUGIN_PREFIX, APP_NAME, art = R('logo.png'), thumb = LOGO)
def MainMenu():
	oc = ObjectContainer(no_cache = True, art = 'logo.png')

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
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api.dropbox.com/1/metadata/" + mode + '/')
	if tmp != False:
		if debug == True: Log("Testcall to api finished with success. Preferences valid")
		Dict['PrefsValidated'] = True;
	else:
		if debug == True: Log("Testcall to api failed. Preferences invalid")
		Dict['PrefsValidated'] = False;
	return True

####################################################################################################

def checkConfig():
	if 'PrefsValidated' in Dict and Dict['PrefsValidated'] == True:
		return True
	else:
		return False

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

def getDropboxThumbnailForPicture(path):
	if debug == True: Log("Fetching thumbnail from dropbox for item: " + path)
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api-content.dropbox.com/1/thumbnails/" + mode + path)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
			if debug_raw == True: Log("Got thumbnail data for: " + path)
			if debug_raw == True: Log(json_data)
		except Exception, e:
			if debug == True: Log("ERROR! getDropboxThumbnail(): " + str(e))
			return False
		return json_data
	else:
		return False

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
	if fileext == '.jpg' or fileext == '.png' or fileext == '.gif' or fileext == '.bmp' or fileext == '.tif':
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
		thumb = ICON_PLAY,
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
		thumb = ICON_PHOTO
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
