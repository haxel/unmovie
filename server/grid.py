# Part of UNMOVIE
# Copyright (C) 2002 Axel Heide

import flash

from math import floor,ceil
import time
import sys,random,traceback

class GridError(Exception):
	def __init__(self,param):
		self.message = str(param)
	def __str__(self):
		return self.message

class Grid:
	""" a grid is composed of hexagons.
		the only functions called from outside are requestLocation and conformToGrid
		it uses the participants dict in FlashService to keep track of the locations of the users
		it does not store them itself. furthermore the location in the dict is a reference 
		to getLocation in FlashPerspective
		so the location of the users is only stored in their perspective.
		the path and hexagon functions are shamelessly stolen from civil
		
		todo: rip out all the funcs that are participant specific
		 and make it a simple helper class
		requestLocation then could be a lot more elegant be in the flashchatter and overridden in the botchatter
	"""		
		
	def __init__ (self,x=768,y=576):
		item_count_x=16
		item_count_y=16
		self.screen_width=x
		self.screen_height=y
		self.size = ( item_count_x, item_count_y )
		""" now we look how big the griditems are """
		self.item_width = self.screen_width/item_count_x
		self.item_height = self.screen_height/item_count_y
			
	def _pointify(self,unicode_point):
		""" 
		translate u'(x,y)' to tuple(x,y) 
		if its a tuple already it converts the items to int
		so if there is not a complete crap in the tuple, we are ok here
		"""
		if type(unicode_point) == unicode:
			return map(lambda x:int(float(x)),unicode_point[1:-1].split(','))
		else:
			return map(lambda x:int(float(x)),unicode_point)
		
	def conformToGrid(self,point):
		""" 
		input a point on the stage and give back the hex, 
		where the point is in, in screencoordinates. 
		"""
		point = self._pointify(point)
		return self.pointToHexCenter(point)
		
	def requestLocation(self,participant,direction,human = 0,avoid=0):
		""" 
		returns: a screencoordinate
		based on the status of the participant that calls
		a function in service is called then the participant finds another user to talk to
		(or shall i just change the status to FOUND and let the service do the work? 
		or make it at least a callback?)
		"""
		direction = self._pointify(direction)
		participant.client.debug(`direction`)
		try:
			if human:
				if not avoid:
					self.checkNeighbours(participant)
					new_point = self.getLocationByDirection(participant,direction)
				else:
					new_point = self.getUnusedLocation(participant,direction)
			elif participant.status in [flash.ONLINE, flash.AVOID]:
				new_point = self.getUnusedLocation(participant,direction)
			elif participant.status == flash.SEARCH:
				new_point = self.getUsedLocation(participant,direction)
			else:
			 	new_point = self.getLocationByDirection(participant,direction)
			return new_point
		except:
			flash.logger_debug.writeLog(traceback.print_exc())

	def getLocationByDirection(self,participant,direction):
		"""
		 returns: location in screen coordinates
		 tries to give back a location that is not out of stage and not on a used spot 
		"""
		selfloc = self._pointify(participant.getLocation())
		selfhex = self.pointToHex(selfloc)
		#participant.client.debug("%s" % (selfloc))
		def wantedHex(d): return map(lambda a,b:a+b,selfhex,d)
		def usersHex(): return map(lambda x:map(lambda y:y,self.pointToHex(x())),self.participants.values())
		directions = flash.movements.values()
		while 1:
			if not directions: direction = (0,0)
			if not self.in_bounds(wantedHex(direction)) or wantedHex(direction) in usersHex():
				direction = directions.pop()
			else:
				break
		shiftByScreen = map(lambda a,b:a*b,direction,[48,36])
		selfloc = map(lambda l,m:l+m,selfloc,shiftByScreen)
		return selfloc
					
	def checkNeighbours(self,participant):
		"""
		 returns: boolean
		 checks if anyone around might join a conversation
		"""
		talkableClients = self.service.getParticipantByStatus([flash.SEARCH,flash.LISTEN,flash.TALK,flash.ONLINE],participant)
		if not talkableClients: return 0
		users = self.findNeighbours(participant,talkableClients)
		if len(users):
			flash.logger_debug.writeLog(users)
			self.service.makeConversation(participant.name,users)
			return 1
    
	def findNeighbours(self,participant,clients):
		""" 
		 returns: a list of the names of the users around the participant
		"""
		userlist = []
		selfloc = participant.getLocation()
		selfhex = self.pointToHex(selfloc)
		for (user,userhex) in map(lambda x:(x,self.pointToHex(x.getLocation())),clients):
			if userhex in self.getHexAdjacent(selfhex):
				userlist.append(user.name)
				participant.client.debug("hit %s" % (user.name))
		return userlist
		
	def requestDirection(self,participant):
		""" 
		"""
		def vec_sum((x,y),(x1,y1)): return (x+x1,y+y1)
		def vec_sub((x,y),(x1,y1)): return (x-x1,y-y1)
		def global2local((base_x,base_y),(x1,y1)): return vec_sub((base_x,base_y),(x1,y1))
		
		pathlen = 8
		usersHex = map(lambda x:self.pointToHex(x()),self.participants.values())
		usersHex += [(0,0),(16,0),(0,16),(16,16)]
		selfhex = self.pointToHex(participant.getLocation())

		usersHex = filter(lambda x:x!=selfhex,usersHex)
		newVec = (0,0)
		for hex in usersHex:
			path = self.path(selfhex,hex)
			if len(path) < pathlen and len(path) > 1:
				newVec = vec_sum(newVec,global2local(selfhex,hex))
		newVec = global2local(newVec,selfhex)
		flash.logger_debug.writeLog("newVec: %s" % `newVec`)
		if newVec == (0,0): return flash.randomDirection()
		else: 
			tmp = [0,0]
			if newVec[0] != 0: tmp[0] = newVec[0]/abs(newVec[0]) 
			if newVec[1] != 0: tmp[1] = newVec[1]/abs(newVec[1]) 
			return (tmp[0],tmp[1])
			
				
	
	def getUsedLocation(self,participant,direction):
		""" 
		 returns: a screen coordinate
		 checks if a user to talk to is around and gives a coordinate to dock
		 if a user is not in the neighbourhood it generates a path to the next available
		 and returns the first location on that path
		"""
		talkableClients = self.service.getParticipantByStatus([flash.SEARCH,flash.LISTEN,flash.TALK,flash.ONLINE],participant)
		#untalkableClients = self.service.getParticipantByStatus(flash.AVOID,participant)
		hex = self.pointToHex(participant.getLocation())
		Found = "Found"
		try:
			if not talkableClients: 
				participant.client.debug("no talkable clients")
				return self.hexCenter(hex)
			users = self.findNeighbours(participant,talkableClients)
			if len(users):
				#print users
				self.service.makeConversation(participant.name,users)
				return self.hexCenter(hex) 
			check = map(lambda x:(x.name,self.pointToHex(x.getLocation())),talkableClients)
			random.shuffle(check)
			for (name,otherhex) in check:
				if name != participant.name and hex != otherhex:
					path = self.path(hex,otherhex)
					participant.client.debug("%s -- %s -- %s:%s" % (hex,path,name,otherhex))
					if len(path): 
						return self.hexCenter(path[0])
						break
			return self.hexCenter(hex)
		except:
			flash.logger_err.writeLog(traceback.print_exc())
			
			
	def getUnusedLocation(self,participant,direction):
		""" 
		 returns: a screen coordinate
		 checks if the direction leads to a free space and returns the coordinate of it.
		 if it is covered already by someone it searches for an uncovered space in the neighbourhood
		 and returns its location
		"""
		def subtract(a,b): return filter(lambda x:x not in b,a)
		
		active = []
		adjacent = []
		for user,aktive_pos in map(lambda x,y:(x,self.pointToHex(y())),self.participants.keys(),self.participants.values()):
			if user != participant.name:
				active += self.getHexAdjacent(aktive_pos)
				active += ((aktive_pos),)
		newLoc = self.pointToHex(self.getLocationByDirection(participant,direction))
		#participant.client.debug("%s -- %s" % (newLoc,active))
		""" just for the case that my random direction gets in the neighbourhood of another user """
		if newLoc in active:
			check = self.getHexAdjacent(newLoc)
			Found = "Found"		
			try:
				for hex in subtract(check,active):
					if self.in_bounds(hex):
						for x in self.getHexAdjacent(hex):
							if self.in_bounds(x):
								adjacent += self.getHexAdjacent(x)
						random.shuffle(adjacent)
						adjacent = uniq(adjacent)
						for y in adjacent:
							if not y in active: 
								raise Found,y
							check.append(y)
						check.remove(hex)
						random.shuffle(check)
					else: continue
			except Found,e:
				return self.hexCenter(e)
			except:
				self.logdebug("error[getUnusedLocation]:  %s " % (traceback.print_exc()))
		
		return self.hexCenter(newLoc)

		
	def hexCenter ( self, h ):
		"""Given hex coordinates h, what map coordinates are it's center?"""
		#print h
		if h[1] % 2 == 0:
			return [h[0]*self.item_width,h[1]*self.item_height]
		else:
			return [h[0]*self.item_width+self.item_width/2,h[1]*self.item_height]
	
	def pointToHex ( self, P ):
		""" given point, return hex coordinates of that point's hex """
		center = self.pointToHexCenter(P)
		Y = center[1] / self.item_height
		if Y % 2 == 0:
			return ( int ( center[0] / self.item_width) , int (Y) )
		else:
			return ( int ( ((center[0]-(self.item_width/2)) / self.item_width) ), int (Y) )

	def getHexAdjacent(self,point):
		"""lists the hex coords adjacent to hex with hex coord x,y, starting
		at upper right and working clockwise."""
		x, y = point
		if y % 2 == 0:
			return [(x,y-1),(x+1,y),(x,y+1),(x-1,y+1),(x-1,y),(x-1,y-1)]
		else:
			return [(x+1,y-1),(x+1,y),(x+1,y+1),(x,y+1),(x-1,y),(x,y-1)]

	def pointToHexCenter ( self, P ):
		"""Returns center of hex that contains point P.
		We chop all the hexes into triangles with 3 sets of parallel
		lines, find out what triangle it's in, one of the points of
		that is also the center of the hex it's in.  There ought to be
		a simpler way to do this..."""
		
		# as long as the point can be rendered to a float we are ok here

		if (type(P[0]) and type(P[1])) != int: 
			(x,y) = map(lambda t:int(float(t)),P)
		else: 
			(x,y) = P
        
		if x<0: x=0
		if x>self.screen_width: x=self.screen_width
		if y<0 : y=0
		if y>self.screen_height: y=self.screen_height
		
		""" currently assumes hexsizes, fix this later.
		we use floor+1, rather than ceil, because we want
		two lines even if the point is on one exactly."""
		sx = self.item_width
		sy = self.item_height
		A1 = Line2d ( 1, 0, ( floor(x/(sx/2.0)) * ceil(sx/2) ))
		A2 = Line2d ( 1, 0, ( (floor(x/(sx/2.0))+1) * ceil(sx/2) ))
		B1 = Line2d ( 1, 2, ( floor((x+2*y)/(sx*1.0)) * ceil(sx) ))
		B2 = Line2d ( 1, 2, ( (floor((x+2*y)/(sx*1.0))+1) * ceil(sx) ))
		"""one of these four points is the center of our hex"""
		S1 = [ A1.intersect(B1), A1.intersect(B2), A2.intersect(B1), A2.intersect(B2) ]
		S2 = []
		for v in S1:
			if v[1] % sy == 0:  # hex centers are the only triangle vertexes 0 mod 36!
				S2.append(v) # only keep points which are the centers of hexes
		if len(S2) == 1:
			return S2[0]
		elif len(S2) == 2: # two were hex centers.  Which is on the other lines?
			C1 = Line2d ( 1, -2, ( floor((x-2*y)/sx*1.0) * sx ))
			C2 = Line2d ( 1, -2, ((floor((x-2*y)/sx*1.0)+1) * sx ))
			if C1.hasPoint(S2[0]) or C2.hasPoint(S2[0]):
				return S2[0]
			elif C1.hasPoint(S2[1]) or C2.hasPoint(S2[1]):
				return S2[1]
			else:
				raise "impossible point"+`P` # mikee thinks this can't happen.
	
	def path(self,start,end):
		""" constructs the path : a list of points from start to end """ 
		if not self.in_bounds(end): return [start]
		if start == end: return [end]
		
		pointlist = []
		node = start
		partmap = map(lambda x:self.pointToHex(x()),self.participants.values())
		while node != end : # (end[0],end[1]):
			new_points = []
			for n in self.getHexAdjacent(node):
				if self.in_bounds(n):
					new_points.append(n)
			
			if not new_points: 
				pointlist.append(node)
				return pointlist
			probability = 100
			for pN in new_points:
				new_probability = self.distance_cost(pN,end)
				if (new_probability < probability):
					probability = new_probability
					node = pN
			pointlist.append(node)
 
		return filter(lambda x:x not in partmap,pointlist)

	# getHexAdjacent() includes hexes off the edge of the map. 
	def in_bounds(self,(x,y)):
		xedge,yedge = self.size
		return x > -1 and y > -1 and x < xedge and y < yedge

	# Thanks Amit!
	# http://www-cs-students.stanford.edu/~amitp/Articles/HexLOS.html

	# distance cost helper functions
	def same_sign(self,n,n1): return (n > -1) == (n1 > -1)
	def a2h(self,(x,y)): return (int(x - floor(float(y)/2)),int(x+ceil(float(y)/2)))
	def h2a(self,(x,y)): return (int(floor(float(x+y)/2)),y-x)

	# For use with rectangular hex maps - usually a 2D array
	# The a2h and h2a algorithms are transforms needed here and to convert back
	# the path list below (XXX below)
	def distance_cost(self,p,p1):
		x,y = self.a2h(p)
		x1,y1 = self.a2h(p1)
		dx = x1-x
		dy = y1-y
		if self.same_sign(dx,dy):
			return max(abs(dx),abs(dy))
		else:
			return (abs(dx) + abs(dy))

	def logdebug(self,str):
		print str
	
class Line2d: 
	""" really, lines ought to be immutable. """ 


	def __init__(self,a,b,c): 
		"""line ax+by=c 
		normalize xco to 1, unless it's zero, then normalize yco 
		if a and b are zero, we don't handle the error."""
		
		if a == 0:
			self.xco = 0
			self.yco = 1 
			self.constant = c / b 
		else: 
			self.xco = 1 
			self.yco = b / a 
			self.constant = c / a 

	def intersect (self, them):
		"""Intersection of two lines.  We could also do this with the matrix
		class, but this specialized code is already written, and probably faster anyway."""
		# are we parallel? 
		if self.yco == them.yco:
			# we are. We'll give correct answer, more or less
			if self.constant == them.constant:
				return () # same line! should return self instead? 
			else: 
				return ()   # ditto.
		# ok, not parallel .
		if self.xco != 0 and them.xco != 0:  # ok, neither is horizontal.
			Yintersect = (self.constant-them.constant)/(self.yco-them.yco)
			Xintersect = self.constant - self.yco * Yintersect
		elif self.xco == 0: # self horizontal
			Yintersect = self.constant # yco is 1, remember
			Xintersect = them.constant - them.yco*Yintersect
		elif them.xco == 0: # them horizontal
			Yintersect = them.constant
			Xintersect = self.constant - self.yco*Yintersect
		else:
			raise "Invalid lines."
		return (Xintersect, Yintersect)

	def hasPoint (self, P):
		if (self.xco*P[0] + self.yco*P[1]) == self.constant:
			return 1
		else:
			return 0

	def __repr__ (self):
		return "%dx + %dy = %d" % (self.xco, self.yco, self.constant)


''' helper func to delete duplicates in lists'''

def uniq(alist):
	set = {}
	return [set.setdefault(e,e) for e in alist if e not in set]	