from mojo.events import EditingTool, BaseEventTool, installTool, addObserver, removeObserver, extractNSEvent
import mojo.drawingTools as dt
from mojo.UI import getGlyphViewDisplaySettings, setGlyphViewDisplaySettings, CurrentGlyphWindow
from lib.tools.defaults import getDefaultColor, getDefault
from mojo.extensions import ExtensionBundle
from mojo.subscriber import Subscriber, registerRoboFontSubscriber
import AppKit
from merz import MerzPen

"""
Blue Zone Editor
by Andy Clymer, October 2018

updated for RF4.4 by Connor Davenport, October 2023
"""


BLUEKEYS = ["postscriptBlueValues", "postscriptOtherBlues"]

c = getDefaultColor("glyphViewSelectionMarqueColor")
MARQUECOLOR = (c.redComponent(), c.greenComponent(), c.blueComponent(), c.alphaComponent())

c = getDefaultColor("glyphViewBluesColor")
BLUESCOLOR = (c.redComponent(), c.greenComponent(), c.blueComponent(), c.alphaComponent())

c = getDefaultColor("glyphViewOtherBluesColor")
OTHERBLUESCOLOR = (c.redComponent(), c.greenComponent(), c.blueComponent(), c.alphaComponent())

VIEWWIDTH = getDefault("glyphViewArtBoardHorizontalBorder") * 2

KEY = "com.andyclymer.blueZoneEditor"
    
class BlueZone(object):
    
    """
    Manages a pair of blue zone locations as one solid zone
    Has helper functions for selecting zone edges and moving the selection
    """
    
    def __init__(self, startPosition, endPosition, layer, index, isOther=False):
        self.alwaysShowLabels = getDefault(f"{KEY}.alwaysShowLabels", defaultValue=False)
        self.startPosition = startPosition
        self.startSelected = False # and the mouse offset if it is selected
        self.endPosition = endPosition
        self.endSelected = False # and the mouse offset if it is selected
        self.isOther = isOther
        self.layer = layer
        self.color = BLUESCOLOR if not self.isOther else OTHERBLUESCOLOR
        self.index = index
        
        self.blue = self.layer.appendRectangleSublayer() 
        self.arrow = self.layer.appendPathSublayer()
    
    
        self.startText = self.layer.appendTextLineSublayer()
        self.endText = self.layer.appendTextLineSublayer()

        for c in [self.startText, self.endText]:
            c.setPointSize(12)
            c.setFillColor((0,0,0,.5))
            c.setHorizontalAlignment("right")
            c.setVerticalAlignment("center")

    def __repr__(self):
        o = " (Other)" if self.isOther else ""
        return f"<BlueZone{o} {self.startPosition} {self.endPosition}>"
        
    def moveSelection(self, delta, isKeyed=False):
        xOffset, yOffset = delta    
        
        if isKeyed:
            if (AppKit.NSEvent.modifierFlags() & AppKit.NSAlternateKeyMask):
                self.startSelected -= xOffset
                self.startPosition += yOffset
            else:
                self.endSelected -= xOffset
                self.endPosition += yOffset
        else:
            if self.startSelected and self.endSelected:
                pass
            else:
                if self.startSelected:
                    self.startSelected += xOffset
                    self.startPosition -= yOffset
                if self.endSelected:
                    self.endSelected += xOffset
                    self.endPosition -= yOffset
                
        # Keep the start lower than the end
        if self.startPosition > self.endPosition:
            self.startPosition, self.endPosition = self.endPosition, self.startPosition
            # And move the selection
            if self.startSelected and not self.endSelected:
                self.startSelected = False
                self.endSelected = True
            elif self.endSelected and not self.startSelected:
                self.startSelected = True
                self.endSelected = False
                                
        self.startPosition = int(round(self.startPosition))
        self.endPosition = int(round(self.endPosition))
        
        w,h = self.blue.getSize()
        nh = (5 * round(int(self.endPosition - self.startPosition)/5)) if (AppKit.NSEvent.modifierFlags() & AppKit.NSShiftKeyMask) else int(self.endPosition - self.startPosition)
        if self.startSelected:
            self.blue.setPosition((-VIEWWIDTH,self.startPosition))
        
        self.blue.setSize((w,nh))
        self.draw()
        
            
    @property
    def selected(self):
        return self.startSelected or self.endSelected
    
    def deselect(self):
        self.startSelected = False
        self.endSelected = False
    
    def select(self, point):
        # Select whichever edge is closest to the point location
        self.startSelected = False
        self.endSelected = False
        if abs(self.startPosition - point[1]) < abs(self.endPosition - point[1]):
            self.startSelected = point[0]
        else: self.endSelected = point[0]   
        
    def distance(self, location):
        # Return the distance to either edge (whichever is closest) to the point
        distances = [abs(self.startPosition - location), abs(self.endPosition - location)]
        distances.sort()
        return distances[0]
        
    def pointInside(self, location):
        positions = [self.startPosition, self.endPosition]
        positions.sort()
        if positions[0] < location < positions[1]:
            return True
        else: return False
        
    def draw(self):
        # Draw the zone
        self.blue.setPosition((-VIEWWIDTH, self.startPosition))
        self.blue.setSize((VIEWWIDTH*4, self.endPosition-self.startPosition))
        self.blue.setFillColor(self.color)
        
        # See if any edges are selected
        selectedPoints = []
        if self.startSelected:
            selectedPoints += [(self.startSelected, self.startPosition)]
        if self.endSelected:
            selectedPoints += [(self.endSelected, self.endPosition)]
        # Draw the zone type
        if not self.isOther and self.index != 0:
            fill=(1, 1, 1, 1)
            bottom, top = self.startPosition+10, self.startPosition
        elif self.index == 0 or self.isOther:
            fill=(0.2, 0.2, 0.8, 1)
            bottom, top = self.endPosition-10, self.endPosition
                
        pen = MerzPen()
        pen.moveTo((0, top))
        pen.lineTo((-5, bottom))
        pen.lineTo((5, bottom))
        pen.closePath()
        
        self.arrow.setFillColor(fill)
        self.arrow.setPath(pen.path)
            
        # Draw the zone locations and its type
        positions = [self.startPosition, self.endPosition]
        positions.sort()
        size = dt.textSize(str(0), align=None)
        zoneHeight = positions[1] - positions[0]
        if zoneHeight < 10:
            offset = 10 - zoneHeight
        else: offset = 5

        self.startText.setPosition((-50, positions[0]-20))
        self.startText.setText(str(positions[0]))
        
        self.endText.setPosition((-50, positions[1]+20))
        self.endText.setText(str(positions[1]))

    def flip(self):
        self.color = BLUESCOLOR if not self.isOther else OTHERBLUESCOLOR
        self.blue.setFillColor(self.color) 
        self.endSelected = self.startSelected = False
        self.highlight()
        self.draw()        
        
    def highlight(self):
        r,g,b,a = self.color
        strokeColor = (r,g,b,1)
        
        if self.endSelected and self.startSelected:
            self.blue.setStrokeWidth(2)
            self.blue.setStrokeColor(strokeColor)
        else:
            self.blue.setStrokeWidth(None)
            self.blue.setStrokeColor(None)
                                
    def animate(self):
        x,y =(-VIEWWIDTH, self.startPosition)
        w,h =(VIEWWIDTH*4, self.endPosition-self.startPosition)
        
        pathLayer = self.layer.appendBaseSublayer(
            position=(x, y),
            size=(w, h))
        
        r,g,b,a = self.color
        strokeColor = (r,g,b,1)
        ani = pathLayer.appendRectangleSublayer(
            size=(w, h),
            fillColor=None,
            strokeColor=strokeColor,
            strokeWidth=2)

        h *= 1.5
        
        d = .8
        with ani.propertyGroup(
                duration=d
            ):
            ani.setStrokeWidth(1)
            ani.setSize((w,h))

        with pathLayer.propertyGroup(
                duration=d,
                animationFinishedCallback=self.removePointAnimation
            ):
            pathLayer.setOpacity(0)
            x,y = pathLayer.getPosition()
            pathLayer.setPosition((x,y-(h/6)))
            
    def removePointAnimation(self, layer):
        self.layer.removeSublayer(layer)
        

debug = True
class BlueEdit(BaseEventTool):
    
    def becomeActive(self):
        # Remember the current display settings, and turn the blues off (I'll draw them myself)
        self.previousDisplaySettings = {"Blues": getGlyphViewDisplaySettings()["Blues"], "FamilyBlues": getGlyphViewDisplaySettings()["FamilyBlues"]}
        setGlyphViewDisplaySettings({"Blues":False, "FamilyBlues":False})
        # Attributes
        self.font = CurrentFont()
        self.zones = []
        self.currentlyUpdatingInfo = False
        
        self.container = self.extensionContainer(
            identifier=f"{KEY}.foreground",
            location="foreground",
            clear=True
        )

        self.fontBecameCurrent(None)
    
    def becomeInactive(self):
        # Reset the display settings
        setGlyphViewDisplaySettings(self.previousDisplaySettings)
        # Observers
        self.container.clearSublayers()

        if not self.font == None:
            self.applyZones()


    def getToolbarIcon(self):
        extBundle = ExtensionBundle("BlueZoneEditor")
        toolbarIcon = extBundle.get("BlueZoneToolIcon-2x")
        return toolbarIcon

    def getToolbarTip(self):
        return "Blue Zones"
        
        
    # Observer callbacks
    def fontBecameCurrent(self, info):
        # Forget any font-specific settings and observe on the font info
        cf = CurrentFont()
        # If there really is a new font
        if not self.font == cf:
            # If there was an old font
            if not self.font == None:
                # Apply the zones before switching
                self.applyZones()
            self.font = cf
        if not self.font == None:
            self.collectZones()
        
        
    def currentFontInfoDidChange(self, info):
        # The font info changed
        # Cache the blue zone data because it may have changed,
        # but only if this tool is not currently editing the font info.
        if not self.currentlyUpdatingInfo:
            self.collectZones()
    
    def mouseDown(self, point, count):
        yLoc = int(round(point[1]))
        if count == 2:
            # Double click in a zone: flip it between "blues" and "otherBlues"
            didFlipZone = False
            for zone in self.zones:
                if zone.pointInside(yLoc):
                    didFlipZone = True
                    zone.isOther = not zone.isOther
                    zone.flip()
                    zone.animate()
                    
            if not didFlipZone:
                # Double click not on a zone: add a new zone
                self.addZone(yLoc-10, yLoc+10)
        elif count == 1:
            # Single click: find the closest zone *edge* in a range and select it
            selected = self.selectClosestZoneEdge((point.x, point.y))
            if not selected:
                # Didn't select an edge, select both edges if the click happened within a zone
                for zone in self.zones:
                    if zone.pointInside(yLoc):
                        zone.startSelected = True
                        zone.endSelected = True
                        zone.highlight()

            
    def mouseDragged(self, point, delta):
        # If the mouse is dragging, move selected zones
        for zone in self.zones:
            zone.moveSelection(delta)
    
    def mouseUp(self, point):
        # If any zones are selected, update the font info, they may have changed
        wasSelected = False
        for zone in self.zones:
            if zone.selected:
                wasSelected = True
        if wasSelected:
            self.applyZones()
    
    def keyDown(self, event):
        e = extractNSEvent(event)
        # Arrow keys to move
        moveValue = 0
        if ord(e["keyDown"]) == 63232: # Up
            if e["shiftDown"]:
                moveValue = 10
            else: moveValue = 1
        elif ord(e["keyDown"]) == 63233: # Down
            if e["shiftDown"]:
                moveValue = -10
            else: moveValue = -1
        if moveValue:
            for zone in self.zones:
                if zone.selected:
                    zone.moveSelection((0, moveValue),True)
        # Delete to remove zones
        if ord(e["keyDown"]) == 127: # Delete
            self.removeSelectedZones()
        # Return to flip zones
        if ord(e["keyDown"]) == 13: # Return
            for zone in self.zones:
                if zone.selected:
                    zone.isOther = not zone.isOther
                    zone.flip()
    
    def collectZones(self):
        self.zones = []
        for k in BLUEKEYS:
            isOther = False
            if "Other" in k:
                isOther = True
            zoneValues = getattr(self.font.info, k)
            index = 0
            for i in range(0, len(zoneValues), 2):
                z = BlueZone(zoneValues[i], zoneValues[i+1], self.container, index=index, isOther=isOther)
                self.zones += [z]                
                index += 1
        for zone in self.zones:
            zone.draw()
    
    def applyZones(self):
        for k in BLUEKEYS:
            isOther = False
            if "Other" in k:
                isOther = True
            newZoneRanges = []
            for zone in self.zones:
                if zone.isOther == isOther:
                    thisZoneRange = [int(round(zone.startPosition)), int(round(zone.endPosition))]
                    thisZoneRange.sort()
                    newZoneRanges.append(thisZoneRange)
            if len(newZoneRanges):
                # Sort and combine overlapping zones
                newZoneRanges.sort(key=lambda x: x[0])
                newZones = [list(newZoneRanges[0])]
                for z in newZoneRanges:
                    if z[0] < newZones[-1][1]:
                        if z[1] > newZones[-1][1]:
                            newZones[-1][1] = z[1]
                    else: newZones += [list(z)]
                # Flatten the pairs into a single list
                newZoneRanges = [int(round(v)) for r in newZones for v in r]
            # Apply
            self.currentlyUpdatingInfo = True
            self.font.info.prepareUndo("Zone change")
            setattr(self.font.info, k, newZoneRanges)
            self.font.info.performUndo()
            self.currentlyUpdatingInfo = False

    
    def selectClosestZoneEdge(self, point, keepSelection=False, distance=6):
        # Find the closest zone edge to the location and select it
        # Optionally, keep the current selection of zones
        if not self.font == None:
            closestZone = None
            closestDist = distance
            for zone in self.zones:
                if not keepSelection:
                    zone.deselect()
                    zone.highlight()
                thisDist = zone.distance(point[1])
                if thisDist < closestDist:
                    closestDist = thisDist
                    closestZone = zone
            if closestZone:
                closestZone.select(point)
                return True
        return False
                
                
    def countZones(self):
        # Return a count of the blues and otherBlues
        zoneCount = {"postscriptBlueValues": 0, "postscriptOtherBlues": 0}
        for zone in self.zones:
            if zone.isOther:
                zoneCount["postscriptOtherBlues"] += 1
            else: zoneCount["postscriptBlueValues"] += 1
        return zoneCount
        
        
    def addZone(self, startPos, endPos, isOther=False):
        blueKey = "postscriptOtherBlues" if isOther else "postscriptBlueValues"
        if not self.font == None:
            if self.countZones()[blueKey] < 7:
                z = BlueZone(startPos, endPos, self.container, index=(self.countZones()[blueKey]+1), isOther=isOther)
                z.startSelected = True
                z.endSelected = True
                z.draw()
                z.animate()
                self.zones += [z]
                
    def removeSelectedZones(self):
        newZones = []
        for zIdx, zone in enumerate(self.zones):
            if not zone.selected:
                newZones.append(zone)
        self.zones = newZones
        self.applyZones()
    

installTool(BlueEdit())